"""Runs on the GPU machine that has the Laya model; the web server never loads it. Polls the API
for queued CSVs, analyses them, and posts the results back. Nothing connects in to this
machine, so it can sit behind NAT or a firewall with no open ports.

Setup on the GPU machine (torch with CUDA first, see pytorch.org):
    pip install -e "apps/api[worker]"
    set ADA_API_URL=https://ad-campaign-analyser.onrender.com
    set TASK_WORKER_KEY=<same value as on the API server>
    python -m ada.workers.task_poller

Env: ADA_API_URL, TASK_WORKER_KEY (required); POLL_SECONDS (default 10);
LAYA_MODEL (default convaiinnovations/laya-typed-decisions); HF_HOME (weights cache).
Keep the key in the machine's environment or a secrets manager, never in a committed file.
"""
import logging
import os
import random
import signal
import sys
import time
from urllib.parse import urlparse

import httpx

from ada.pipeline.youtube_insights import analyse_csv

log = logging.getLogger("ada.task_poller")
DEFAULT_MODEL = "convaiinnovations/laya-typed-decisions"
_stop = False


def _on_signal(signum, _frame) -> None:
    global _stop
    _stop = True
    log.info("signal %s: finishing the current task, then stopping", signum)


def _check_url(url: str) -> str:
    """The worker key travels in a header, so only send it over HTTPS (or to this machine)."""
    u = urlparse(url)
    if u.scheme == "https" or (u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1")):
        return url.rstrip("/")
    sys.exit(f"ADA_API_URL must be https:// (got {url!r})")


def _sleep(seconds: float) -> None:
    end = time.monotonic() + seconds
    while not _stop and time.monotonic() < end:
        time.sleep(min(1.0, end - time.monotonic()))


def _post(client: httpx.Client, task_id: str, body: dict) -> None:
    """Deliver a result; retried because losing it means the whole analysis runs again."""
    for attempt in range(5):
        try:
            r = client.post(f"/api/v1/taskoutput/{task_id}", json=body)
            if r.status_code == 204:
                return
            if r.status_code in (409, 422):           # lease lost / output rejected: don't retry
                log.error("task %s: API refused result (%s): %s", task_id, r.status_code, r.text[:500])
                return
            r.raise_for_status()
        except httpx.HTTPError as e:
            log.warning("task %s: posting result failed (%s), retrying", task_id, e)
        _sleep(2 ** attempt)
    log.error("task %s: gave up posting the result; it will be retried after the lease ends", task_id)


def load_model():
    """Load Laya once. Heavy import (torch), so only the worker pays for it."""
    import laya

    model = os.environ.get("LAYA_MODEL", DEFAULT_MODEL)
    t0 = time.monotonic()
    agent = laya.load(model)
    log.info("loaded %s in %.1fs", model, time.monotonic() - t0)
    return agent


def process(client: httpx.Client, task: dict, agent) -> None:
    task_id, token = task["task_id"], task["lease_token"]
    log.info("task %s: started (attempt %s)", task_id, task["attempt"])
    t0 = time.monotonic()
    try:
        report = analyse_csv(task["task_input"], agent)
    except ValueError as e:                            # the CSV itself is bad: retrying won't help
        _post(client, task_id, {"lease_token": token, "error": f"Couldn't read that CSV: {e}"[:500]})
        return
    except Exception as e:                             # model trouble: let the API retry it
        log.exception("task %s: analysis failed", task_id)
        _post(client, task_id, {"lease_token": token, "retry": True,
                                "error": f"Model error ({e.__class__.__name__})"})
        return
    _post(client, task_id, {"lease_token": token, "output": report})
    log.info("task %s: done in %.1fs", task_id, time.monotonic() - t0)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    url = _check_url(os.environ.get("ADA_API_URL", "http://localhost:8000"))
    key = os.environ.get("TASK_WORKER_KEY", "")
    if len(key) < 32:
        sys.exit("Set TASK_WORKER_KEY (32+ chars, the same value as on the API server)")
    poll = max(2.0, float(os.environ.get("POLL_SECONDS", "10")))
    signal.signal(signal.SIGINT, _on_signal)
    signal.signal(signal.SIGTERM, _on_signal)

    log.info("loading the Laya model…")
    agent = load_model()
    log.info("polling %s every %ss", url, poll)

    headers = {"Authorization": f"Bearer {key}", "User-Agent": "ada-task-poller/1"}
    failures = 0
    with httpx.Client(base_url=url, headers=headers, timeout=httpx.Timeout(30.0, connect=10.0),
                      follow_redirects=False) as client:
        while not _stop:
            try:
                r = client.get("/api/v1/taskoutput")
                if r.status_code == 401:
                    sys.exit("API rejected TASK_WORKER_KEY")
                if r.status_code == 204:
                    failures = 0
                    _sleep(poll)
                    continue
                r.raise_for_status()
                failures = 0
                process(client, r.json(), agent)       # then ask again at once: drain the queue
            except httpx.HTTPError as e:
                failures += 1
                wait = min(300, poll * 2 ** min(failures, 5)) + random.uniform(0, 3)
                log.warning("API unreachable (%s); retrying in %.0fs", e, wait)
                _sleep(wait)
    log.info("stopped")


if __name__ == "__main__":
    main()

from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from ada.config import settings
from ada.db.models import AnalysisTask, Membership, utcnow
from ada.main import app
from ada.pipeline.youtube_insights import analyse_csv
from tests.unit.test_auth import signup
from tests.unit.test_workspaces import ws_id
from tests.unit.test_youtube_insights import CSV, HEAD, FakeLaya

KEY = "k" * 40
AUTH = {"Authorization": f"Bearer {KEY}"}


@pytest.fixture(autouse=True)
def worker_key(monkeypatch):
    monkeypatch.setattr(settings, "task_worker_key", KEY)


def queue(c, wid, csv=CSV):
    return c.post(f"/api/v1/workspaces/{wid}/taskinput",
                  files={"file": ("yt.csv", csv.encode(), "text/csv")})


def status_of(c, wid, task_id):
    return c.get(f"/api/v1/workspaces/{wid}/taskinput/{task_id}")


def claim(c):
    return c.get("/api/v1/taskoutput", headers=AUTH)


def submit(c, task_id, body):
    return c.post(f"/api/v1/taskoutput/{task_id}", json=body, headers=AUTH)


def test_full_flow(client):
    c, Session = client
    signup(c)
    wid = ws_id(c)
    r = queue(c, wid)
    assert r.status_code == 202, r.text
    tid = r.json()["task_id"]
    assert status_of(c, wid, tid).json()["status"] == "queued"

    job = claim(c)
    assert job.status_code == 200
    job = job.json()
    assert job["task_id"] == tid and job["task_input"].startswith("video_id,")
    assert status_of(c, wid, tid).json()["status"] == "processing"
    assert claim(c).status_code == 204                       # nobody else gets it

    report = analyse_csv(job["task_input"], FakeLaya())
    assert submit(c, tid, {"lease_token": "x" * 40, "output": report}).status_code == 409
    assert submit(c, tid, {"lease_token": job["lease_token"], "output": report}).status_code == 204
    assert submit(c, tid, {"lease_token": job["lease_token"], "output": report}).status_code == 409

    done = status_of(c, wid, tid).json()
    assert done["status"] == "done" and done["task_complete"] == 1
    assert done["output"]["summary"]["videos"] == 3
    with Session() as s:
        assert s.get(AnalysisTask, tid).task_input is None    # CSV dropped once processed
    dash = c.get(f"/api/v1/workspaces/{wid}/dashboard").json()
    assert dash["viewer_interest"] is not None


def test_worker_auth(client, monkeypatch):
    c, _ = client
    assert c.get("/api/v1/taskoutput").status_code == 401
    assert c.get("/api/v1/taskoutput", headers={"Authorization": "Bearer wrong"}).status_code == 401
    assert claim(c).status_code == 204
    monkeypatch.setattr(settings, "task_worker_key", "")
    assert claim(c).status_code == 503                       # queue off, never open


def test_bad_csv_rejected_up_front(client):
    c, _ = client
    signup(c)
    wid = ws_id(c)
    assert queue(c, wid, "a,b\n1,2\n").status_code == 422
    assert queue(c, wid, "").status_code == 422
    bad_id = CSV.replace("aaaaaaaaaa1", "javascript:alert(1)")
    assert queue(c, wid, bad_id).status_code == 422
    r = c.post(f"/api/v1/workspaces/{wid}/taskinput",
               files={"file": ("x.csv", b"\xff\xfe\x00bad", "text/csv")})
    assert r.status_code == 422


def test_only_creator_sees_task(client):
    c, _ = client
    signup(c)
    wid = ws_id(c)
    tid = queue(c, wid).json()["task_id"]
    other = TestClient(app)
    signup(other, "b@example.com")
    assert status_of(other, wid, tid).status_code == 404           # not their workspace
    assert status_of(other, ws_id(other), tid).status_code == 404  # their workspace, not their task
    assert status_of(c, wid, "not-a-uuid").status_code == 422


def test_expired_lease_is_reclaimed_and_old_token_refused(client):
    c, Session = client
    signup(c)
    tid = queue(c, ws_id(c)).json()["task_id"]
    first = claim(c).json()
    with Session() as s:
        s.get(AnalysisTask, tid).claimed_at = utcnow() - timedelta(seconds=settings.task_lease_seconds + 5)
        s.commit()
    second = claim(c).json()
    assert second["task_id"] == tid and second["attempt"] == 2
    report = analyse_csv(CSV, FakeLaya())
    assert submit(c, tid, {"lease_token": first["lease_token"], "output": report}).status_code == 409
    assert submit(c, tid, {"lease_token": second["lease_token"], "output": report}).status_code == 204


def test_worker_error_retry_then_fail(client):
    c, _ = client
    signup(c)
    wid = ws_id(c)
    tid = queue(c, wid).json()["task_id"]
    job = claim(c).json()
    r = submit(c, tid, {"lease_token": job["lease_token"], "error": "oom", "retry": True})
    assert r.status_code == 204
    assert status_of(c, wid, tid).json()["status"] == "queued"
    job = claim(c).json()
    assert submit(c, tid, {"lease_token": job["lease_token"], "error": "bad csv"}).status_code == 204
    s = status_of(c, wid, tid).json()
    assert s["status"] == "failed" and s["error"] == "bad csv"


def test_gives_up_after_max_attempts(client, monkeypatch):
    c, Session = client
    signup(c)
    wid = ws_id(c)
    monkeypatch.setattr(settings, "task_max_attempts", 1)
    tid = queue(c, wid).json()["task_id"]
    claim(c)
    with Session() as s:
        s.get(AnalysisTask, tid).claimed_at = utcnow() - timedelta(days=1)
        s.commit()
    assert claim(c).status_code == 204
    assert status_of(c, wid, tid).json()["status"] == "failed"


def test_output_is_validated_and_links_rebuilt(client):
    c, _ = client
    signup(c)
    wid = ws_id(c)
    tid = queue(c, wid).json()["task_id"]
    job = claim(c).json()
    report = analyse_csv(CSV, FakeLaya())
    assert submit(c, tid, {"lease_token": job["lease_token"], "output": {"videos": "x"}}).status_code == 422
    assert submit(c, tid, {"lease_token": job["lease_token"]}).status_code == 422
    report["videos"][0]["url"] = "javascript:alert(1)"
    report["videos"][0]["extra"] = "<script>"
    assert submit(c, tid, {"lease_token": job["lease_token"], "output": report}).status_code == 204
    row = status_of(c, wid, tid).json()["output"]["videos"][0]
    assert row["url"] == "https://www.youtube.com/watch?v=aaaaaaaaaa1" and "extra" not in row


def test_pending_limit_and_expiry(client, monkeypatch):
    c, Session = client
    signup(c)
    wid = ws_id(c)
    monkeypatch.setattr(settings, "task_max_pending_per_user", 2)
    t1 = queue(c, wid).json()["task_id"]
    queue(c, wid)
    assert queue(c, wid).status_code == 429
    with Session() as s:
        s.get(AnalysisTask, t1).created_at = utcnow() - timedelta(minutes=settings.task_expire_minutes + 1)
        s.commit()
    s1 = status_of(c, wid, t1).json()
    assert s1["status"] == "failed" and "too long" in s1["error"]
    assert queue(c, wid).status_code == 202                  # the expired one no longer counts


def test_poller_processes_a_task_end_to_end(client):
    from ada.workers.task_poller import process
    c, _ = client
    signup(c)
    wid = ws_id(c)
    tid = queue(c, wid).json()["task_id"]
    worker = TestClient(app, headers=AUTH)                     # the model machine
    process(worker, worker.get("/api/v1/taskoutput").json(), FakeLaya())
    assert status_of(c, wid, tid).json()["status"] == "done"


def analyse(c, wid, csv=CSV):
    """Queue a CSV and let a fake worker finish it, the way the GPU machine would."""
    tid = queue(c, wid, csv).json()["task_id"]
    job = claim(c).json()
    report = analyse_csv(job["task_input"], FakeLaya())
    assert submit(c, tid, {"lease_token": job["lease_token"], "output": report}).status_code == 204
    return status_of(c, wid, tid).json()


def viewer_interest(c, wid):
    return c.get(f"/api/v1/workspaces/{wid}/dashboard").json()["viewer_interest"]


def test_dashboard_shows_latest_analysis(client):
    c, _ = client
    signup(c)
    wid = ws_id(c)
    assert viewer_interest(c, wid) is None
    analyse(c, wid)
    v = viewer_interest(c, wid)
    assert v["video_count"] == 2 and v["interested_people"] == 1205       # quiet ad left out
    assert [t["interested_people"] for t in v["top_videos"]] == [1205, 0]
    top = v["top_videos"][0]
    assert top["title"] == "Hit ad" and top["comments_read"] == 2
    assert top["url"] == "https://www.youtube.com/watch?v=aaaaaaaaaa1"

    analyse(c, wid, "﻿" + HEAD + '"dddddddddd4","u","New ad","Nike","2026-01-01",20,10,1,0,0.1,'
                    '"Love it — @ed (4 likes)","",""\n')
    v = viewer_interest(c, wid)                                           # replaced, not added up
    assert v["video_count"] == 1 and v["interested_people"] == 5


def test_viewers_get_results_but_dont_change_dashboard(client):
    c, Session = client
    signup(c)
    wid = ws_id(c)
    with Session() as s:
        s.scalar(select(Membership)).role = "viewer"
        s.commit()
    assert analyse(c, wid)["status"] == "done"
    assert viewer_interest(c, wid) is None

"""Turn the YouTube page's 'Download CSV' export into ad insights with the Laya model.

Per video: did it reach a million views, engagement, how its top comments read (good / bad /
neutral and what they're about), the best and worst comment, an age-group guess, and how many
people signalled interest in the product.
Across videos: the best ads, the worst received, top complaints, engagement by ad length.

Limits: the CSV only holds public data. Real viewer ages and watch time are in YouTube
Analytics, which only the channel owner can read. The age group here is what commenters say
about themselves ("my kids", "in college"), so it is a hint from a few comments, not demographics.
Interested people = commenters showing interest + the likes on those comments, from the top
comments only. It is a rough signal of visible interest, not a count of interested viewers:
silent viewers are missed, and one person may like several comments.

Run:  python -m ada.pipeline.youtube_insights youtube-nike.csv -o nike-insights.csv
"""
import argparse
import csv
import io
import json
import re
from collections import Counter
from typing import Any, Protocol

MILLION = 1_000_000
AGE_MIN_CONFIDENCE = 0.35      # 5 options spread the odds; below this Laya is guessing -> "unknown"
INTEREST_MIN_CONFIDENCE = 0.6  # 2 options start at 0.5; a weak yes shouldn't count all its likes
LENGTH_BUCKETS = [(15, "0-15s"), (30, "16-30s"), (60, "31-60s"), (10**9, "60s+")]
_COMMENT = re.compile(r"^(?P<text>.*) — (?P<author>.*?) \((?P<likes>[\d,]+) likes\)$", re.DOTALL)

COMMENT_QUESTIONS: dict[str, dict] = {
    "sentiment": {
        "type": "choice",
        "instructions": "How does this YouTube commenter feel about the ad or the product?",
        "criteria": {
            "positive": "likes the ad or product: praise, excitement, wants to buy",
            "negative": "dislikes the ad or product: complaint, annoyed, mocking",
            "neutral": "neither: a plain question, a fact, or off-topic",
        },
    },
    "topic": {
        "type": "choice",
        "instructions": "What is the comment mainly about?",
        "criteria": {
            "ad_creative": "the ad itself: music, actors, story, editing, humour",
            "product": "the product: quality, features, price, wanting to buy",
            "annoyance": "seeing the ad too often, skipping it, ads in general",
            "question": "asking where to buy, the price, or other details",
            "other": "off-topic, spam, or jokes unrelated to the ad",
        },
    },
    "age_group": {
        "type": "choice",
        "instructions": "Judging only by what the commenter says about themselves, "
                        "which age group are they in?",
        "criteria": {
            "under_18": "school, exams, my parents won't let me",
            "18_24": "college, hostel, first job",
            "25_44": "my kids, my wife or husband, office, career",
            "45_plus": "grandchildren, retirement, back in the 80s",
            "unknown": "nothing in the comment says how old they are",
        },
    },
    "product_interest": {
        "type": "choice",
        "instructions": "Does this YouTube commenter show interest in buying or trying the "
                        "product in the video?",
        "criteria": {
            "interested": "wants to buy or try it, asks the price or where to get it, "
                          "or already owns it and recommends it",
            "not_interested": "no sign of wanting it: only about the ad, a joke, "
                              "a complaint, or off-topic",
        },
    },
}


class Predictor(Protocol):
    """The slice of laya's Agent we use, so tests can pass a fake."""

    def predict_batch(self, states: list[str], questions: dict, batch_size: int | None = None
                      ) -> list[dict[str, Any]]: ...


def parse_comment(cell: str) -> dict | None:
    """'Great ad! — @ana (1,204 likes)' -> {text, author, likes}. None for empty/turned off."""
    cell = cell.strip()
    if not cell or cell == "Comments turned off":
        return None
    m = _COMMENT.match(cell)
    if not m:
        return {"text": cell, "author": "", "likes": 0}
    return {"text": m["text"], "author": m["author"], "likes": int(m["likes"].replace(",", ""))}


def read_csv(content: str) -> list[dict]:
    rows = list(csv.DictReader(io.StringIO(content.lstrip("﻿"))))
    if rows and not {"video_id", "views"} <= rows[0].keys():
        raise ValueError("Not a YouTube export: expected video_id and views columns.")
    videos = []
    for r in rows:
        cells = [r[k] for k in r if k and k.startswith("top_comment_") and r[k]]
        videos.append({
            "video_id": r["video_id"], "url": r.get("url", ""), "title": r.get("title", ""),
            "channel": r.get("channel", ""), "views": int(r["views"] or 0),
            "duration_seconds": int(r.get("duration_seconds") or 0),
            "engagement_rate": float(r.get("engagement_rate") or 0),
            "comments": [c for cell in cells if (c := parse_comment(cell))],
        })
    return videos


def _pct(comments: list[dict], sentiment: str) -> int:
    """Share of comments with this sentiment, weighted by 1 + likes: a liked comment speaks for
    everyone who liked it."""
    total = sum(1 + c["likes"] for c in comments)
    return round(100 * sum(1 + c["likes"] for c in comments if c["sentiment"] == sentiment) / total)


def _reception(net: int) -> str:
    return "loved" if net >= 50 else "liked" if net >= 15 else "mixed" if net > -15 else "disliked"


def video_row(v: dict) -> dict:
    cs = v["comments"]
    row = {k: v[k] for k in ("video_id", "title", "channel", "url", "views", "duration_seconds",
                             "engagement_rate")}
    row["million_views"] = v["views"] >= MILLION
    row["comments_read"] = len(cs)
    if not cs:
        return row | {"positive_pct": None, "negative_pct": None, "reception": "no comments",
                      "best_comment": "", "worst_comment": "", "main_complaint": "",
                      "age_group_guess": "unknown", "age_hints": 0,
                      "interested_comments": 0, "interested_people": None}
    pos = [c for c in cs if c["sentiment"] == "positive"]
    neg = [c for c in cs if c["sentiment"] == "negative"]
    interested = [c for c in cs if c["interested"]]
    ages = Counter(c["age_group"] for c in cs if c["age_group"] != "unknown")
    complaints = Counter(c["topic"] for c in neg)
    row["positive_pct"], row["negative_pct"] = _pct(cs, "positive"), _pct(cs, "negative")
    row["reception"] = _reception(row["positive_pct"] - row["negative_pct"])
    row["best_comment"] = max(pos, key=lambda c: c["likes"])["text"] if pos else ""
    row["worst_comment"] = max(neg, key=lambda c: c["likes"])["text"] if neg else ""
    row["main_complaint"] = complaints.most_common(1)[0][0] if complaints else ""
    row["age_group_guess"] = ages.most_common(1)[0][0] if ages else "unknown"
    row["age_hints"] = sum(ages.values())       # how many comments revealed an age
    row["interested_comments"] = len(interested)
    row["interested_people"] = sum(1 + c["likes"] for c in interested)  # commenter + their likes
    return row


def _brief(r: dict) -> dict:
    return {k: r[k] for k in ("video_id", "title", "views", "engagement_rate", "reception")}


def summarise(rows: list[dict]) -> dict:
    million = [r for r in rows if r["million_views"]]
    best = sorted((r for r in million if r["reception"] in ("loved", "liked")),
                  key=lambda r: r["engagement_rate"], reverse=True)
    worst = sorted((r for r in rows if r["reception"] == "disliked"),
                   key=lambda r: r["negative_pct"], reverse=True)
    by_length: dict[str, list[float]] = {}
    for r in rows:
        label = next(lbl for limit, lbl in LENGTH_BUCKETS if r["duration_seconds"] <= limit)
        by_length.setdefault(label, []).append(r["engagement_rate"])
    ages = Counter(r["age_group_guess"] for r in rows if r["age_group_guess"] != "unknown")
    return {
        "videos": len(rows),
        "million_view_ads": len(million),
        "best_ads": [_brief(r) for r in best[:5]],
        "worst_received": [_brief(r) for r in worst[:5]],
        "top_complaints": dict(Counter(r["main_complaint"] for r in rows
                                       if r["main_complaint"]).most_common()),
        "engagement_by_length": {
            lbl: {"ads": len(v), "avg_engagement_rate": round(sum(v) / len(v), 4)}
            for _, lbl in LENGTH_BUCKETS if (v := by_length.get(lbl))},
        "age_groups_from_comments": dict(ages.most_common()),
    }


def analyse_csv(content: str, agent: Predictor, batch_size: int = 32) -> dict:
    """All comments of all videos go through Laya in shared batches, then roll up per video.
    Each comment costs ~0.5-1.5s on CPU, so repeated texts (spam, "first!") are asked once."""
    videos = read_csv(content)
    comments = [c for v in videos for c in v["comments"]]
    texts = list(dict.fromkeys(c["text"] for c in comments))
    results = agent.predict_batch(texts, COMMENT_QUESTIONS, batch_size=batch_size) if texts else []
    by_text = dict(zip(texts, results, strict=True))
    for c in comments:
        a = by_text[c["text"]]["answers"]
        c["sentiment"], c["topic"] = a["sentiment"]["choice"], a["topic"]["choice"]
        age = a["age_group"]
        sure = age["answer_confidence"] >= AGE_MIN_CONFIDENCE
        c["age_group"] = age["choice"] if sure else "unknown"
        interest = a["product_interest"]
        c["interested"] = (interest["choice"] == "interested"
                           and interest["answer_confidence"] >= INTEREST_MIN_CONFIDENCE)
    rows = [video_row(v) for v in videos]
    return {"videos": rows, "summary": summarise(rows)}


def main() -> None:
    from ada.workers.task_poller import load_model  # needs laya: run this on the GPU machine

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("csv", help="file from the YouTube page's Download CSV button")
    ap.add_argument("-o", "--out", help="write one row per video here (CSV)")
    args = ap.parse_args()
    with open(args.csv, encoding="utf-8-sig") as f:
        report = analyse_csv(f.read(), load_model())
    if args.out and report["videos"]:
        with open(args.out, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(report["videos"][0]))
            w.writeheader()
            w.writerows(report["videos"])
    print(json.dumps(report["summary"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

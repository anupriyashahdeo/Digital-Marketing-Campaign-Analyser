from ada.pipeline.youtube_insights import analyse_csv, parse_comment

HEAD = ("video_id,url,title,channel,published_at,duration_seconds,views,likes,comments,"
        "engagement_rate,top_comment_1,top_comment_2,top_comment_3\n")
CSV = "﻿" + HEAD + (
    '"aaaaaaaaaa1","u","Hit ad","Nike","2026-01-01",20,2500000,90000,4000,0.0376,'
    '"Love this ad, my kids sing it — @ana (1,204 likes)","Too loud — @bo (3 likes)",""\n'
    '"bbbbbbbbbb2","u","Flop ad","Nike","2026-01-01",90,40000,100,50,0.0037,'
    '"Worst ad ever, skip — @cy (500 likes)","Annoying — @di (20 likes)",""\n'
    '"cccccccccc3","u","Quiet ad","Nike","2026-01-01",10,1200000,10,0,0.0001,'
    '"Comments turned off","",""\n'
)


def answer(choice, conf=0.9):
    return {"type": "choice", "choice": choice, "answer_confidence": conf}


class FakeLaya:
    """Keyword stand-in for the model: 'love' is positive and interested, 'kids' reveals 25-44,
    'worst' is an unsure yes on interest."""

    def __init__(self):
        self.calls = []

    def predict_batch(self, states, questions, batch_size=None):
        self.calls.append(states)
        return [{"answers": {
            "sentiment": answer("positive" if "love" in s.lower() else "negative"),
            "topic": answer("ad_creative" if "love" in s.lower() else "annoyance"),
            "age_group": answer("25_44") if "kids" in s else answer("18_24", conf=0.3),
            "product_interest": (answer("interested") if "love" in s.lower()
                                 else answer("interested", conf=0.55) if "worst" in s.lower()
                                 else answer("not_interested")),
        }} for s in states]


def test_parse_comment():
    assert parse_comment("Great ad! — @ana (1,204 likes)") == {
        "text": "Great ad!", "author": "@ana", "likes": 1204}
    assert parse_comment("no suffix") == {"text": "no suffix", "author": "", "likes": 0}
    assert parse_comment("Comments turned off") is None
    assert parse_comment("") is None


def test_analyse_csv_rolls_up_per_video():
    fake = FakeLaya()
    report = analyse_csv(CSV, fake)
    assert len(fake.calls) == 1 and len(fake.calls[0]) == 4      # one batch, all comments
    hit, flop, quiet = report["videos"]
    assert hit["million_views"] and hit["reception"] == "loved"
    assert hit["best_comment"].startswith("Love this ad")
    assert hit["age_group_guess"] == "25_44" and hit["age_hints"] == 1
    assert flop["reception"] == "disliked" and flop["main_complaint"] == "annoyance"
    assert flop["age_group_guess"] == "unknown"                  # low-confidence guess dropped
    assert quiet["reception"] == "no comments" and quiet["comments_read"] == 0
    assert hit["interested_comments"] == 1 and hit["interested_people"] == 1205  # 1 + 1,204 likes
    assert flop["interested_comments"] == 0 and flop["interested_people"] == 0   # unsure yes dropped
    assert quiet["interested_people"] is None
    s = report["summary"]
    assert s["million_view_ads"] == 2
    assert [b["video_id"] for b in s["best_ads"]] == ["aaaaaaaaaa1"]
    assert [w["video_id"] for w in s["worst_received"]] == ["bbbbbbbbbb2"]
    assert s["engagement_by_length"]["60s+"]["ads"] == 1

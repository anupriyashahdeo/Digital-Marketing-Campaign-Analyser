from ada.domain.scoring.labeler import AdFacts, label


def test_organic_is_never_winner_or_dog():
    assert label(AdFacts("organic_only", engagement_z=3.0)).name == "Unrated"
    assert label(AdFacts("organic_only", engagement_z=-3.0)).name == "Unrated"


def test_winner_needs_long_run_variants_and_engagement():
    assert label(AdFacts("paid_confirmed", run_days=60, variants=3, engagement_z=1.0)).name == "Winner"
    assert label(AdFacts("paid_confirmed", run_days=60, variants=1, engagement_z=1.0)).name == "Promising"


def test_dog_needs_short_run_and_weak_engagement():
    assert label(AdFacts("paid_confirmed", run_days=3, engagement_z=-1.0)).name == "Dog"
    assert label(AdFacts("paid_confirmed", run_days=3, rerun=True, engagement_z=-1.0)).name == "Watch"


def test_own_account_uses_real_results():
    assert label(AdFacts("own_account_verified", own_results_vs_benchmark=1.5)).name == "Winner"
    assert label(AdFacts("own_account_verified", own_results_vs_benchmark=0.5)).name == "Dog"


def test_unknown_dates_are_watch():
    assert label(AdFacts("paid_confirmed")).name == "Watch"

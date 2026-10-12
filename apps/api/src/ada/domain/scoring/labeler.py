"""Winner/Promising/Watch/Dog/Unrated with reasons. Never labels from views alone."""
from dataclasses import dataclass, field

from ada.domain.scoring.evidence import EvidenceLevel

LONG_RUN_DAYS = 30
SHORT_RUN_DAYS = 7


@dataclass
class AdFacts:
    evidence_level: EvidenceLevel
    run_days: int | None = None
    variants: int = 1
    rerun: bool = False
    engagement_z: float | None = None
    own_results_vs_benchmark: float | None = None   # e.g. 1.2 = 20% better than benchmark


@dataclass
class Label:
    name: str
    confidence: str = "low"
    reasons: list[str] = field(default_factory=list)


def label_from_real_results(ad: AdFacts) -> Label:
    r = ad.own_results_vs_benchmark
    if r is None:
        return Label("Watch", "low", ["Own account connected but no results yet"])
    if r >= 1.2:
        return Label("Winner", "high", [f"Own results {r:.2f}x benchmark"])
    if r <= 0.7:
        return Label("Dog", "high", [f"Own results {r:.2f}x benchmark"])
    return Label("Watch", "high", [f"Own results {r:.2f}x benchmark"])


def label(ad: AdFacts) -> Label:
    if ad.evidence_level == "organic_only":
        return Label("Unrated", "none", ["No paid evidence found; organic views cannot prove ad success"])
    if ad.evidence_level == "own_account_verified":
        return label_from_real_results(ad)

    days, z = ad.run_days, ad.engagement_z
    if days is None:
        return Label("Watch", "low", ["Paid, but run dates unknown"])
    long_run = days >= LONG_RUN_DAYS
    if long_run and ad.variants >= 2 and z is not None and z > 0:
        return Label("Winner", "medium", [
            f"Ran {days} days", f"{ad.variants} creative variants", f"Engagement {z:+.1f} SD vs own channel"])
    if days <= SHORT_RUN_DAYS and not ad.rerun and z is not None and z < 0:
        return Label("Dog", "medium", [
            f"Ran only {days} days, not re-run", f"Engagement {z:+.1f} SD vs own channel"])
    if long_run or (z is not None and z > 0.5):
        return Label("Promising", "low", ["Some positive signals but not enough for Winner"])
    return Label("Watch", "low", ["Mixed or insufficient evidence"])

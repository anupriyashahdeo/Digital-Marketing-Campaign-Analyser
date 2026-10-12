from typing import Literal

EvidenceLevel = Literal["organic_only", "paid_confirmed", "own_account_verified"]


def evidence_level(paid_confirmed: bool, own_account: bool) -> EvidenceLevel:
    if own_account:
        return "own_account_verified"
    return "paid_confirmed" if paid_confirmed else "organic_only"

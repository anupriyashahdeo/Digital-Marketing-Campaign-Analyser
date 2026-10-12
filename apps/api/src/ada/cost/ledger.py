class SpendCapExceeded(Exception):
    pass


class CostLedger:
    def __init__(self, cap_usd: float):
        self.cap, self.spent, self.entries = cap_usd, 0.0, []

    def charge(self, provider: str, usd: float):
        if self.spent + usd > self.cap:
            raise SpendCapExceeded(f"cap ${self.cap} would be exceeded by {provider}")
        self.spent += usd
        self.entries.append((provider, usd))

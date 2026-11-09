from dataclasses import dataclass
from .models import Bar

@dataclass
class Strategy:
    strategy_id: str
    fast: int
    slow: int
    threshold_bps: float

    def signal(self, history: list[Bar]) -> str | None:
        if len(history) < self.slow:
            return None
        closes = [x.close for x in history[-self.slow:]]
        fast_avg = sum(closes[-self.fast:]) / self.fast
        slow_avg = sum(closes) / self.slow
        move_bps = (fast_avg / slow_avg - 1) * 10000
        if move_bps > self.threshold_bps:
            return "BUY"
        if move_bps < -self.threshold_bps:
            return "SELL"
        return None

def build_strategies() -> list[Strategy]:
    strategies = []
    for i in range(50):
        strategies.append(Strategy(
            strategy_id=f"strategy_{i + 1:03d}",
            fast=3 + (i % 8),
            slow=12 + (i % 20),
            threshold_bps=2 + (i % 10),
        ))
    return strategies

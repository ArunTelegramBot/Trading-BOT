from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any

@dataclass
class Bar:
    timestamp: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

@dataclass
class Trade:
    strategy_id: str
    version: str
    timestamp: str
    symbol: str
    side: str
    quantity: int
    price: float
    turnover_inr: float
    cost_inr: float
    pnl_inr: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

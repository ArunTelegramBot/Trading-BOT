import csv
from datetime import datetime
from pathlib import Path
from .models import Bar

def load_bars(path: str) -> list[Bar]:
    file = Path(path)
    if not file.exists():
        return []
    bars = []
    with file.open(newline="") as fh:
        for row in csv.DictReader(fh):
            bars.append(Bar(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                symbol=row["symbol"], open=float(row["open"]), high=float(row["high"]),
                low=float(row["low"]), close=float(row["close"]), volume=float(row["volume"])))
    return sorted(bars, key=lambda b: b.timestamp)

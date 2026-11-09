from datetime import datetime, timedelta, timezone
from pathlib import Path
import csv, math

def create(path: str):
    file = Path(path); file.parent.mkdir(parents=True, exist_ok=True)
    start = datetime(2026, 11, 10, 9, 15, tzinfo=timezone.utc)
    with file.open("w", newline="") as fh:
        writer = csv.writer(fh); writer.writerow(["timestamp", "symbol", "open", "high", "low", "close", "volume"])
        price = 22000.0
        for i in range(120):
            ts = start + timedelta(minutes=5 * i)
            price += math.sin(i / 7) * 8 + 2
            writer.writerow([ts.isoformat(), "NIFTY", price - 2, price + 5, price - 5, price, 100000 + i * 10])

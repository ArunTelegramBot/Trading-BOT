from datetime import datetime, time
from zoneinfo import ZoneInfo

def is_open(ts: datetime, cfg: dict) -> bool:
    local = ts.astimezone(ZoneInfo(cfg["timezone"]))
    if local.weekday() >= 5:
        return False
    start = time.fromisoformat(cfg["session_start"])
    end = time.fromisoformat(cfg["session_end"])
    return start <= local.time() <= end

def trading_date(ts: datetime, cfg: dict) -> str:
    return ts.astimezone(ZoneInfo(cfg["timezone"])).date().isoformat()

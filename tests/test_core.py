from datetime import datetime
from zoneinfo import ZoneInfo
from bot.market_hours import is_open
from bot.strategies import build_strategies

CFG = {"timezone": "Asia/Kolkata", "session_start": "09:15", "session_end": "15:30"}

def test_market_hours():
    assert is_open(datetime(2026, 11, 10, 10, 0, tzinfo=ZoneInfo("Asia/Kolkata")), CFG)
    assert not is_open(datetime(2026, 11, 10, 16, 0, tzinfo=ZoneInfo("Asia/Kolkata")), CFG)

def test_has_fifty_strategies():
    assert len(build_strategies()) == 50

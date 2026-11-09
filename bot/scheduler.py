import time
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import ROOT, load_config
from .engine import run_once
from .hermes import create_review, send_to_hermes

def run_scheduler():
    cfg = load_config()
    state = ROOT / "data" / "last_report_date.txt"
    state.parent.mkdir(parents=True, exist_ok=True)
    while True:
        now = datetime.now(ZoneInfo(cfg["timezone"]))
        today = now.date().isoformat()
        if now.strftime("%H:%M") == cfg["report_time"] and state.read_text().strip() != today if state.exists() else True:
            run_once(cfg)
            review = create_review(str(ROOT / cfg["observations_file"]), str(ROOT / "data"))
            if cfg["hermes_url"]:
                send_to_hermes(review, cfg["hermes_url"], cfg["hermes_api_key"])
            state.write_text(today)
        time.sleep(30)

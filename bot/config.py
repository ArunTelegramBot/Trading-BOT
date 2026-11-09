import json
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

def load_config() -> dict:
    cfg = json.loads((ROOT / "config.json").read_text())
    cfg["mode"] = os.getenv("BOT_MODE", cfg["mode"])
    cfg["timezone"] = os.getenv("TIMEZONE", cfg["timezone"])
    cfg["initial_capital_inr"] = float(os.getenv("PAPER_CAPITAL_INR", cfg["initial_capital_inr"]))
    cfg["report_time"] = os.getenv("REPORT_TIME", cfg["report_time"])
    cfg["max_daily_loss_inr"] = float(os.getenv("MAX_DAILY_LOSS_INR", cfg["max_daily_loss_inr"]))
    cfg["max_orders_per_day"] = int(os.getenv("MAX_ORDERS_PER_DAY", cfg["max_orders_per_day"]))
    cfg["data_file"] = os.getenv("DATA_FILE", "data/market_data.csv")
    cfg["observations_file"] = os.getenv("OBSERVATIONS_FILE", "data/hermes_observations.json")
    cfg["workbook_file"] = os.getenv("WORKBOOK_FILE", "data/trading_performance_tracker.xlsx")
    cfg["telegram_bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN", "")
    cfg["telegram_chat_id"] = os.getenv("TELEGRAM_CHAT_ID", "")
    cfg["hermes_url"] = os.getenv("HERMES_URL", "")
    cfg["hermes_api_key"] = os.getenv("HERMES_API_KEY", "")
    return cfg

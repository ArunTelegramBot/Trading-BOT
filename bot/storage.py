import json
from datetime import datetime
from pathlib import Path
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill

def ensure_parent(path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)

def append_observation(path: str, observation: dict):
    ensure_parent(path)
    file = Path(path)
    if file.exists():
        data = json.loads(file.read_text())
    else:
        data = {"schema_version": "1.0.0", "timezone": "Asia/Kolkata", "mode": "paper", "daily_observations": [], "decision_log": []}
    data.setdefault("daily_observations", []).append(observation)
    file.write_text(json.dumps(data, indent=2, default=str))

def create_or_update_workbook(path: str, daily: dict, strategy_rows: list[dict]):
    ensure_parent(path)
    file = Path(path)
    wb = load_workbook(file) if file.exists() else Workbook()
    if "Sheet" in wb.sheetnames and len(wb.sheetnames) == 1:
        wb.remove(wb["Sheet"])
    for name in ["Daily Performance", "Strategy Daily Log", "Monthly Summary"]:
        if name not in wb.sheetnames:
            wb.create_sheet(name)
    headers = ["Date", "Orders Submitted", "Orders Filled", "Completed Trades", "Winning Trades", "Losing Trades", "Win Rate", "Turnover (INR)", "Gross P&L (INR)", "Costs (INR)", "Net P&L (INR)", "Notes"]
    ws = wb["Daily Performance"]
    if ws.max_row == 1 and ws["A1"].value is None:
        ws.append(headers)
    ws.append([daily.get("date"), daily.get("orders_submitted", 0), daily.get("orders_filled", 0), daily.get("completed_trades", 0), daily.get("winning_trades", 0), daily.get("losing_trades", 0), daily.get("win_rate"), daily.get("turnover_inr", 0), daily.get("gross_profit_loss_inr", 0), daily.get("costs_inr", 0), daily.get("net_profit_loss_inr", 0), daily.get("notes", "")])
    sws = wb["Strategy Daily Log"]
    sheaders = ["Date", "Strategy ID", "Version", "Orders", "Completed Trades", "Wins", "Losses", "Win Rate", "Turnover (INR)", "Gross P&L (INR)", "Costs (INR)", "Net P&L (INR)", "Notes"]
    if sws.max_row == 1 and sws["A1"].value is None:
        sws.append(sheaders)
    for row in strategy_rows:
        sws.append([row.get(k) for k in ["date", "strategy_id", "version", "orders", "completed_trades", "wins", "losses", "win_rate", "turnover_inr", "gross_profit_loss_inr", "costs_inr", "net_profit_loss_inr", "notes"]])
    for sheet in [ws, sws]:
        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
        sheet.freeze_panes = "A2"
    wb.save(file)

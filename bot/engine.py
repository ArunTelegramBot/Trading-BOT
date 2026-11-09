from collections import defaultdict
from datetime import datetime
from .config import ROOT
from .data_provider import load_bars
from .market_hours import is_open, trading_date
from .paper_broker import PaperBroker
from .strategies import build_strategies
from .storage import append_observation, create_or_update_workbook
from .telegram import send_message

def run_once(cfg: dict, bars=None) -> dict:
    bars = bars if bars is not None else load_bars(str(ROOT / cfg["data_file"]))
    broker = PaperBroker(cfg["initial_capital_inr"], cfg)
    strategies = build_strategies()
    histories = defaultdict(list)
    strategy_rows = []
    for bar in bars:
        if not is_open(bar.timestamp, cfg):
            continue
        histories[bar.symbol].append(bar)
        for strategy in strategies:
            signal = strategy.signal(histories[bar.symbol])
            if signal:
                broker.order(strategy.strategy_id, "v1", bar.timestamp.isoformat(), bar.symbol, signal, bar.close)
    by_strategy = defaultdict(list)
    for trade in broker.trades:
        by_strategy[trade.strategy_id].append(trade)
    report_date = trading_date(bars[-1].timestamp, cfg) if bars else datetime.now().date().isoformat()
    for strategy in strategies:
        trades = by_strategy[strategy.strategy_id]
        wins = sum(1 for t in trades if t.pnl_inr > 0)
        losses = sum(1 for t in trades if t.pnl_inr < 0)
        strategy_rows.append({
            "date": report_date, "strategy_id": strategy.strategy_id, "version": "v1",
            "orders": len(trades), "completed_trades": len(trades), "wins": wins, "losses": losses,
            "win_rate": wins / len(trades) if trades else None,
            "turnover_inr": sum(t.turnover_inr for t in trades),
            "gross_profit_loss_inr": sum(t.pnl_inr for t in trades),
            "costs_inr": sum(t.cost_inr for t in trades),
            "net_profit_loss_inr": sum(t.pnl_inr - t.cost_inr for t in trades), "notes": ""
        })
    daily = {
        "date": report_date, "orders_submitted": broker.orders, "orders_filled": len(broker.trades),
        "completed_trades": len(broker.trades), "winning_trades": sum(1 for t in broker.trades if t.pnl_inr > 0),
        "losing_trades": sum(1 for t in broker.trades if t.pnl_inr < 0),
        "win_rate": None, "turnover_inr": sum(t.turnover_inr for t in broker.trades),
        "gross_profit_loss_inr": sum(t.pnl_inr for t in broker.trades),
        "costs_inr": sum(t.cost_inr for t in broker.trades),
        "net_profit_loss_inr": sum(t.pnl_inr - t.cost_inr for t in broker.trades),
        "ending_paper_capital_inr": broker.cash, "max_drawdown_inr": 0,
        "strategy_results": strategy_rows, "mistakes": [], "data_quality_issues": [],
        "hermes_review": {"status": "pending", "approval_required": True}
    }
    daily["win_rate"] = daily["winning_trades"] / daily["completed_trades"] if daily["completed_trades"] else None
    append_observation(str(ROOT / cfg["observations_file"]), {"date": report_date, **daily})
    create_or_update_workbook(str(ROOT / cfg["workbook_file"]), daily, strategy_rows)
    text = (f"Paper report {report_date}\nOrders: {daily['orders_submitted']}\n"
            f"Trades: {daily['completed_trades']}\nWins/Losses: {daily['winning_trades']}/{daily['losing_trades']}\n"
            f"Turnover: ₹{daily['turnover_inr']:.2f}\nNet P&L: ₹{daily['net_profit_loss_inr']:.2f}")
    send_message(cfg["telegram_bot_token"], cfg["telegram_chat_id"], text)
    return daily

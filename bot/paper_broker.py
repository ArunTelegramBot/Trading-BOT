from collections import defaultdict
from .models import Trade

class PaperBroker:
    def __init__(self, capital: float, cfg: dict):
        self.initial_capital = capital
        self.cash = capital
        self.cfg = cfg
        self.positions = defaultdict(int)
        self.avg_entry = defaultdict(float)
        self.trades: list[Trade] = []
        self.orders = 0

    def order(self, strategy_id: str, version: str, ts: str, symbol: str, side: str, price: float) -> Trade | None:
        if self.orders >= self.cfg["max_orders_per_day"]:
            return None
        qty = max(1, int((self.initial_capital / 50) / price))
        slip = price * self.cfg["slippage_bps"] / 10000
        fill = price + slip if side == "BUY" else price - slip
        turnover = qty * fill
        cost = turnover * self.cfg["fee_bps"] / 10000
        if side == "BUY" and turnover + cost > self.cash:
            return None
        if side == "BUY":
            self.cash -= turnover + cost
            key = (strategy_id, symbol)
            old_qty = self.positions[key]
            old_value = old_qty * self.avg_entry[key]
            self.positions[key] += qty
            self.avg_entry[key] = (old_value + turnover) / self.positions[key]
        else:
            key = (strategy_id, symbol)
            held = self.positions[key]
            qty = min(qty, held)
            if qty == 0:
                return None
            pnl = (fill - self.avg_entry[key]) * qty
            self.positions[key] -= qty
            if self.positions[key] == 0:
                self.avg_entry[key] = 0.0
            self.cash += turnover - cost
        self.orders += 1
        trade = Trade(strategy_id, version, ts, symbol, side, qty, fill, turnover, cost, pnl if side == "SELL" else 0.0)
        self.trades.append(trade)
        return trade

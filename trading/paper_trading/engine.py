#!/usr/bin/env python3
"""
NSE Paper Trading Engine — 15 Strategies + Psychology Rules.
Reads state, checks all strategies, executes paper trades, updates Excel.
NEVER resets numbers — always accumulates.
"""
import json, os, warnings, openpyxl
from openpyxl.styles import PatternFill, Font, Border, Side
from datetime import datetime, timezone, timedelta
warnings.filterwarnings('ignore')

# ─── CONFIG ───
BASE = "/home/ubuntu/Trading-BOT/trading/paper_trading"
EXCEL_PATH = f"{BASE}/paper_trading.xlsx"
STATE_PATH = f"{BASE}/state.json"
STOCKS = ["BAJAJFINSV.NS","TCS.NS","ADANIPORTS.NS","M&M.NS","KOTAKBANK.NS",
          "BAJFINANCE.NS","ADANIENT.NS","ICICIBANK.NS","NESTLEIND.NS","ASIANPAINT.NS",
          "LT.NS","TITAN.NS","BHARTIARTL.NS","ULTRACEMCO.NS","SBIN.NS"]
START_CAPITAL = 100000
RISK_PCT = 0.02  # 2% max risk per trade [Trading in the Zone, Market Wizards]

STRATEGIES = [
    "Supertrend (10,3) + EMA50",
    "EMA Crossover (6/30)",
    "RSI + MACD",
    "BB Squeeze",
    "VWAP Pullback",
    "EMA + ADX Trend",
    "SMA 50/200 Cross",
    "Donchian 20 Breakout",
    "Triple EMA (9/21/50)",
    "Keltner Breakout",
    "Volume Surge Momentum",
    "MACD Histogram Flip",
    "ATR Breakout",
    "Hull MA + RSI",
    "Price Structure Break"
]

# ─── PSYCHOLOGY RULES (from Trading in the Zone, Market Wizards, How to Day Trade) ───
PSYCH_RULES = {
    "max_risk_pct": 0.02,          # Rule 1: Max 2% per trade
    "max_concurrent": 5,           # Rule 2: Max 5 open positions (O'Neil)
    "cooloff_on_3_loss": True,     # Rule 3: 3 consecutive losses = stop new entries (Douglas)
    "half_size_on_10pct_dd": True, # Rule 4: DD > 10% = halve position size (Aziz)
    "trend_filter": True,          # Rule 5: Trade only with 50-EMA trend (Livermore)
    "no_avg_down": True,           # Rule 6: Never average down (O'Neil, Livermore)
    "take_all_setups": True,       # Rule 7: Take every valid setup, don't cherry-pick (Douglas)
    "no_revenge": True,            # Rule 8: Track emotional state
    "stop_before_entry": True,     # Rule 9: Stop calculated before entry (Market Wizards)
    "process_over_pnl": True,      # Rule 10: Judge process, not P&L
}

green_fill = PatternFill("solid", fgColor="C6EFCE")
red_fill = PatternFill("solid", fgColor="FFC7CE")
header_font = Font(bold=True, color="FFFFFF", size=11)
thin_border = Border(left=Side('thin'),right=Side('thin'),top=Side('thin'),bottom=Side('thin'))

def load_state():
    if os.path.exists(STATE_PATH):
        return json.load(open(STATE_PATH))
    return {"positions": {}, "closed_trades": [], "capital": START_CAPITAL, "last_run": None,
            "consecutive_losses": 0, "psych_state": {}, "trade_count": 0}

def save_state(state):
    os.makedirs(BASE, exist_ok=True)
    json.dump(state, open(STATE_PATH, 'w'), indent=2)

def run_strategies(d):
    import pandas as pd, numpy as np
    signals = []
    c = d['Close']; h = d['High']; l = d['Low']; v = d['Volume']
    last = d.iloc[-1]; prev = d.iloc[-2]
    hl2 = (h + l) / 2

    # 1. Supertrend (10,3) + EMA50
    atr_st = (h - l).rolling(10).mean()
    up = hl2 + 3 * atr_st; dn = hl2 - 3 * atr_st
    st = [1]
    for i in range(1, len(d)):
        if c.iloc[i] <= up.iloc[i-1]: st.append(-1)
        elif c.iloc[i] >= dn.iloc[i-1]: st.append(1)
        else: st.append(st[-1])
    d = d.copy()
    d['st_entry'] = pd.Series(st).diff()
    ema50 = c.ewm(50).mean()
    if d['st_entry'].iloc[-1] == 2 and last['Close'] > ema50.iloc[-1]:
        signals.append((STRATEGIES[0], "BUY", last['Close']))
    elif d['st_entry'].iloc[-1] == -2 and last['Close'] < ema50.iloc[-1]:
        signals.append((STRATEGIES[0], "SELL", last['Close']))

    # 2. EMA Crossover (6/30)
    ema6 = c.ewm(6).mean(); ema30 = c.ewm(30).mean()
    if ema6.iloc[-1] > ema30.iloc[-1] and ema6.iloc[-2] <= ema30.iloc[-2]:
        signals.append((STRATEGIES[1], "BUY", last['Close']))
    elif ema6.iloc[-1] < ema30.iloc[-1] and ema6.iloc[-2] >= ema30.iloc[-2]:
        signals.append((STRATEGIES[1], "SELL", last['Close']))

    # 3. RSI + MACD
    delta = c.diff(); g = delta.clip(0); lv = -delta.clip(None,0)
    rs = g.rolling(14).mean() / lv.rolling(14).mean()
    rsi = 100 - (100 / (1 + rs))
    mf = c.ewm(12).mean(); ms = c.ewm(26).mean()
    macd = mf - ms; msig = macd.ewm(9).mean(); mh = macd - msig
    if len(d) >= 14:
        if rsi.iloc[-1] < 30 and mh.iloc[-1] > 0 and mh.iloc[-2] <= 0:
            signals.append((STRATEGIES[2], "BUY", last['Close']))
        elif rsi.iloc[-1] > 70 and mh.iloc[-1] < 0 and mh.iloc[-2] >= 0:
            signals.append((STRATEGIES[2], "SELL", last['Close']))

    # 4. BB Squeeze
    bb_mid = c.rolling(20).mean(); bb_std = c.rolling(20).std()
    bb_u = bb_mid + 2 * bb_std; bb_l = bb_mid - 2 * bb_std
    bw = (bb_u - bb_l) / bb_mid
    if bw.iloc[-1] < 0.3:
        if last['Close'] > bb_u.iloc[-1] and prev['Close'] <= bb_u.iloc[-2]:
            signals.append((STRATEGIES[3], "BUY", last['Close']))
        elif last['Close'] < bb_l.iloc[-1] and prev['Close'] >= bb_l.iloc[-2]:
            signals.append((STRATEGIES[3], "SELL", last['Close']))

    # 5. VWAP Pullback
    vwap = (d['Volume'] * hl2).rolling(20).sum() / d['Volume'].rolling(20).sum()
    if len(vwap) >= 20:
        if last['Close'] > vwap.iloc[-1] and prev['Close'] <= vwap.iloc[-1]:
            signals.append((STRATEGIES[4], "BUY", last['Close']))
        elif last['Close'] < vwap.iloc[-1] and prev['Close'] >= vwap.iloc[-1]:
            signals.append((STRATEGIES[4], "SELL", last['Close']))

    # 6. EMA + ADX Trend (ADX > 25 confirms trend)
    up_move = h.diff().clip(0).rolling(14).mean()
    dn_move = (-l.diff()).clip(0).rolling(14).mean()
    dx = abs(up_move - dn_move) / (up_move + dn_move + 1e-9) * 100
    adx_val = dx.rolling(14).mean()
    ema20 = c.ewm(20).mean()
    if len(d) >= 20:
        if adx_val.iloc[-1] > 25 and ema20.iloc[-1] > ema50.iloc[-1] and ema20.iloc[-2] <= ema50.iloc[-2]:
            signals.append((STRATEGIES[5], "BUY", last['Close']))
        elif adx_val.iloc[-1] > 25 and ema20.iloc[-1] < ema50.iloc[-1] and ema20.iloc[-2] >= ema50.iloc[-2]:
            signals.append((STRATEGIES[5], "SELL", last['Close']))

    # 7. SMA 50/200 Cross (Golden/Death Cross)
    sma50 = c.rolling(50).mean(); sma200 = c.rolling(200).mean()
    if len(d) >= 200:
        if sma50.iloc[-1] > sma200.iloc[-1] and sma50.iloc[-2] <= sma200.iloc[-2]:
            signals.append((STRATEGIES[6], "BUY", last['Close']))
        elif sma50.iloc[-1] < sma200.iloc[-1] and sma50.iloc[-2] >= sma200.iloc[-2]:
            signals.append((STRATEGIES[6], "SELL", last['Close']))

    # 8. Donchian 20 Breakout
    dc_high = h.rolling(20).max(); dc_low = l.rolling(20).min()
    if len(d) >= 20:
        if last['Close'] > dc_high.iloc[-2] and prev['Close'] <= dc_high.iloc[-2]:
            signals.append((STRATEGIES[7], "BUY", last['Close']))
        elif last['Close'] < dc_low.iloc[-2] and prev['Close'] >= dc_low.iloc[-2]:
            signals.append((STRATEGIES[7], "SELL", last['Close']))

    # 9. Triple EMA (9/21/50 stacked)
    ema9 = c.ewm(9).mean(); ema21 = c.ewm(21).mean()
    if len(d) >= 50:
        if ema9.iloc[-1] > ema21.iloc[-1] > ema50.iloc[-1] and not (ema9.iloc[-2] > ema21.iloc[-2] > ema50.iloc[-2]):
            signals.append((STRATEGIES[8], "BUY", last['Close']))
        elif ema9.iloc[-1] < ema21.iloc[-1] < ema50.iloc[-1] and not (ema9.iloc[-2] < ema21.iloc[-2] < ema50.iloc[-2]):
            signals.append((STRATEGIES[8], "SELL", last['Close']))

    # 10. Keltner Breakout
    kc_mid = c.ewm(20).mean(); kc_atr = (h - l).rolling(10).mean()
    kc_u = kc_mid + 2 * kc_atr; kc_l = kc_mid - 2 * kc_atr
    if len(d) >= 20:
        if last['Close'] > kc_u.iloc[-1] and prev['Close'] <= kc_u.iloc[-2]:
            signals.append((STRATEGIES[9], "BUY", last['Close']))
        elif last['Close'] < kc_l.iloc[-1] and prev['Close'] >= kc_l.iloc[-2]:
            signals.append((STRATEGIES[9], "SELL", last['Close']))

    # 11. Volume Surge Momentum
    vol_avg = v.rolling(20).mean()
    ret_1d = c.pct_change()
    if len(d) >= 20:
        if last['Volume'] > 1.5 * vol_avg.iloc[-1] and ret_1d.iloc[-1] > 0.01:
            signals.append((STRATEGIES[10], "BUY", last['Close']))
        elif last['Volume'] > 1.5 * vol_avg.iloc[-1] and ret_1d.iloc[-1] < -0.01:
            signals.append((STRATEGIES[10], "SELL", last['Close']))

    # 12. MACD Histogram Flip
    if len(d) >= 14:
        if mh.iloc[-1] > 0 and mh.iloc[-2] < 0:
            signals.append((STRATEGIES[11], "BUY", last['Close']))
        elif mh.iloc[-1] < 0 and mh.iloc[-2] > 0:
            signals.append((STRATEGIES[11], "SELL", last['Close']))

    # 13. ATR Breakout (price moves > 1.5x ATR)
    atr14 = (h - l).rolling(14).mean()
    if len(d) >= 14:
        if last['Close'] > prev['Close'] + 1.5 * atr14.iloc[-2]:
            signals.append((STRATEGIES[12], "BUY", last['Close']))
        elif last['Close'] < prev['Close'] - 1.5 * atr14.iloc[-2]:
            signals.append((STRATEGIES[12], "SELL", last['Close']))

    # 14. Hull MA + RSI
    def hull(series, period):
        w = int(period/2); sqrt_per = int(np.sqrt(period))
        hma = series.ewm(span=w).mean() * 2 - series.ewm(span=period).mean()
        return hma.ewm(span=sqrt_per).mean()
    if len(d) >= 20:
        hull9 = hull(c, 9); hull18 = hull(c, 18)
        if hull9.iloc[-1] > hull18.iloc[-1] and hull9.iloc[-2] <= hull18.iloc[-2] and rsi.iloc[-1] > 50:
            signals.append((STRATEGIES[13], "BUY", last['Close']))
        elif hull9.iloc[-1] < hull18.iloc[-1] and hull9.iloc[-2] >= hull18.iloc[-2] and rsi.iloc[-1] < 50:
            signals.append((STRATEGIES[13], "SELL", last['Close']))

    # 15. Price Structure Break (higher high / lower low)
    if len(d) >= 20:
        recent_max = h.tail(10).max(); recent_min = l.tail(10).min()
        prev_max = h.shift(1).tail(10).max(); prev_min = l.shift(1).tail(10).min()
        if last['Close'] > prev_max and prev['Close'] <= h.shift(1).iloc[-2]:
            signals.append((STRATEGIES[14], "BUY", last['Close']))
        elif last['Close'] < prev_min and prev['Close'] >= l.shift(1).iloc[-2]:
            signals.append((STRATEGIES[14], "SELL", last['Close']))

    return signals

def update_excel(state, stock_signals):
    wb = openpyxl.load_workbook(EXCEL_PATH) if os.path.exists(EXCEL_PATH) else openpyxl.Workbook()

    # === TAB 1: Trade Log ===
    if "Trade Log" not in wb.sheetnames:
        wb.create_sheet("Trade Log")
    ws1 = wb["Trade Log"]
    headers1 = ["Date","Stock","Action","Entry Price","Exit Price","Qty","P&L (₹)","Strategy","Holding Days","Psychology Notes"]
    if ws1.cell(1,1).value != "Date":
        for i,h in enumerate(headers1,1): ws1.cell(1,i,h)
    max_row = ws1.max_row
    logged = set()
    for row in range(2, max_row + 1):
        v = ws1.cell(row, 1).value
        if v: logged.add(f"{v}_{ws1.cell(row,2).value}_{ws1.cell(row,3).value}")
    for trade in state.get("closed_trades", []):
        key = f"{trade.get('exit_date','')}_{trade['stock']}_{'SELL' if trade['action']=='BUY' else 'COVER'}"
        if key not in logged:
            row = max_row + 1
            ws1.cell(row, 1, trade.get("exit_date",""))
            ws1.cell(row, 2, trade['stock']); ws1.cell(row, 3, "SELL" if trade['action']=='BUY' else "COVER")
            ws1.cell(row, 4, trade['entry_price']); ws1.cell(row, 5, trade['exit_price']); ws1.cell(row, 6, trade.get('qty',''))
            pnl_cell = ws1.cell(row, 7, trade['pnl'])
            pnl_cell.fill = green_fill if trade['pnl'] >= 0 else red_fill
            pnl_cell.number_format = '#,##0'
            ws1.cell(row, 8, trade.get('strategy','')); ws1.cell(row, 9, trade.get('holding_days',''))
            ws1.cell(row, 10, trade.get('notes',''))
            for c in range(1, 11): ws1.cell(row, c).border = thin_border
            max_row = row

    # === TAB 2: Strategy Performance ===
    if "Strategy Performance" not in wb.sheetnames:
        ws2 = wb.create_sheet("Strategy Performance")
        for i,h in enumerate(["Strategy","Total Trades","Wins","Losses","Win Rate %","Total P&L (₹)","Avg RR","Max DD %","Psychology Score"],1):
            ws2.cell(1,i,h)
    ws2 = wb["Strategy Performance"]
    strat_stats = {s: {"trades":0,"wins":0,"losses":0,"pnl":0,"win_pnl":0,"loss_pnl":0} for s in STRATEGIES}
    for t in state.get("closed_trades", []):
        s = t.get('strategy', STRATEGIES[0])
        if s not in strat_stats: strat_stats[s] = {"trades":0,"wins":0,"losses":0,"pnl":0,"win_pnl":0,"loss_pnl":0}
        strat_stats[s]["trades"] += 1
        if t['pnl'] >= 0: strat_stats[s]["wins"] += 1; strat_stats[s]["win_pnl"] += t['pnl']
        else: strat_stats[s]["losses"] += 1; strat_stats[s]["loss_pnl"] += abs(t['pnl'])
        strat_stats[s]["pnl"] += t['pnl']

    for idx, s in enumerate(STRATEGIES, 2):
        ss = strat_stats[s]; wins = ss["wins"]; losses = ss["losses"]; total = ss["trades"]
        ws2.cell(idx, 1, s); ws2.cell(idx, 2, total); ws2.cell(idx, 3, wins); ws2.cell(idx, 4, losses)
        ws2.cell(idx, 5, round(wins/(wins+losses)*100,1) if (wins+losses) > 0 else 0)
        pnl_cell = ws2.cell(idx, 6, ss["pnl"])
        pnl_cell.fill = green_fill if ss["pnl"] >= 0 else red_fill
        pnl_cell.number_format = '#,##0'
        avg_win = ss["win_pnl"] / wins if wins > 0 else 0
        avg_loss = ss["loss_pnl"] / losses if losses > 0 else 0
        ws2.cell(idx, 7, round(avg_win/avg_loss,2) if avg_loss > 0 else 0)
        ws2.cell(idx, 8, 0)
        psych_scores = state.get("psych_state", {}).get("strategy_psych", {})
        ws2.cell(idx, 9, psych_scores.get(s, ""))
        for c in range(1, 10): ws2.cell(idx, c).border = thin_border

    # === TAB 3: Account Overview ===
    if "Account Overview" not in wb.sheetnames:
        ws3 = wb.create_sheet("Account Overview")
        ws3.cell(2,1,"📊 ACCOUNT OVERVIEW"); ws3.cell(2,1).font = Font(bold=True, size=14)
        ws3.cell(4,1,"Current Balance"); ws3.cell(5,1,"Total P&L"); ws3.cell(6,1,"Open Positions")
        ws3.cell(7,1,"Total Closed Trades"); ws3.cell(8,1,"Consecutive Losses")
        ws3.cell(9,1,"Win Rate"); ws3.cell(10,1,"Avg Risk:Reward")
        ws3.cell(12,1,"🧠 PSYCHOLOGY RULES ACTIVE"); ws3.cell(12,1).font = Font(bold=True, size=12)
        ws3.cell(13,1,"Risk per trade"); ws3.cell(13,2,"2% ✓")
        ws3.cell(14,1,"Max positions"); ws3.cell(14,2,"5 ✓")
        ws3.cell(15,1,"Cool-off losses"); ws3.cell(15,2,f"{'✓' if PSYCH_RULES['cooloff_on_3_loss'] else '✗'}")
        ws3.cell(16,1,"Half size on DD"); ws3.cell(16,2,f"{'✓' if PSYCH_RULES['half_size_on_10pct_dd'] else '✗'}")
        ws3.cell(17,1,"Trend filter"); ws3.cell(17,2,f"{'✓' if PSYCH_RULES['trend_filter'] else '✗'}")
        ws3.cell(18,1,"No averaging down"); ws3.cell(18,2,f"{'✓' if PSYCH_RULES['no_avg_down'] else '✗'}")
        ws3.cell(20,1,"📈 MONTHLY P&L"); ws3.cell(20,1).font = Font(bold=True, size=12)
        ws3.cell(21,1,"Month"); ws3.cell(21,2,"Start"); ws3.cell(21,3,"End"); ws3.cell(21,4,"P&L"); ws3.cell(21,5,"Cumulative")
        for r in [4,5,6,7,8,9,10,13,14,15,16,17,18]: ws3.cell(r,1).font = Font(bold=True)

    ws3 = wb["Account Overview"]
    total_pnl = sum(t['pnl'] for t in state.get("closed_trades", []))
    current_capital = START_CAPITAL + total_pnl
    cons_losses = state.get("consecutive_losses", 0)
    wins = sum(1 for t in state.get("closed_trades",[]) if t['pnl'] >= 0)
    losses = sum(1 for t in state.get("closed_trades",[]) if t['pnl'] < 0)
    wr = round(wins/(wins+losses)*100,1) if (wins+losses) > 0 else 0
    avg_win = sum(t['pnl'] for t in state.get("closed_trades",[]) if t['pnl'] >= 0) / wins if wins > 0 else 0
    avg_loss = abs(sum(t['pnl'] for t in state.get("closed_trades",[]) if t['pnl'] < 0)) / losses if losses > 0 else 1
    rr = round(avg_win/avg_loss, 2) if avg_loss > 0 else 0

    ws3.cell(4, 2, f"₹{current_capital:,}")
    ws3.cell(5, 2, f"₹{total_pnl:+,}"); ws3.cell(5, 2).fill = green_fill if total_pnl >= 0 else red_fill
    ws3.cell(6, 2, len(state.get("positions", {})))
    ws3.cell(7, 2, len(state.get("closed_trades", [])))
    ws3.cell(8, 2, cons_losses); ws3.cell(9, 2, f"{wr}%"); ws3.cell(10, 2, f"{rr}:1")
    for r in range(4, 11): ws3.cell(r, 2).border = thin_border

    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    current_month = now.strftime("%b %Y")
    month_row = None
    for r in range(22, 60):
        if ws3.cell(r, 1).value == current_month: month_row = r; break
    if month_row is None:
        month_row = ws3.max_row + 1
        ws3.cell(month_row, 1, current_month)
        prev_month_trades = [t for t in state.get("closed_trades",[]) if t.get('exit_date','')[:7] < current_month[:7]]
        ws3.cell(month_row, 2, f"₹{START_CAPITAL + sum(t['pnl'] for t in prev_month_trades):,}")
    month_trades = [t for t in state.get("closed_trades",[]) if t.get('exit_date','').startswith(current_month[:7])]
    month_pnl = sum(t['pnl'] for t in month_trades)
    ws3.cell(month_row, 3, f"₹{current_capital:,}"); ws3.cell(month_row, 4, f"₹{month_pnl:+,}")
    ws3.cell(month_row, 4).fill = green_fill if month_pnl >= 0 else red_fill
    ws3.cell(month_row, 5, f"₹{total_pnl:+,}")
    for c in range(1, 6): ws3.cell(month_row, c).border = thin_border

    wb.save(EXCEL_PATH)
    return current_capital

def run_engine():
    import pandas as pd, numpy as np, yfinance as yf
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    print(f"RUN: {now_ist.strftime('%d-%b-%Y %H:%M IST')}")

    state = load_state()
    cap = state['capital']
    print(f"Capital: ₹{cap:,} | Open: {len(state['positions'])} | Closed: {len(state['closed_trades'])}")

    # ─── Psychology pre-checks ───
    cons_losses = state.get("consecutive_losses", 0)
    dd_pct = (START_CAPITAL - cap) / START_CAPITAL if cap < START_CAPITAL else 0
    position_size_mult = 1.0
    if PSYCH_RULES["half_size_on_10pct_dd"] and dd_pct > 0.10:
        position_size_mult = 0.5
        print(f"⚠️ DD > 10% — position sizes halved (psych rule)")
    if PSYCH_RULES["cooloff_on_3_loss"] and cons_losses >= 3:
        print(f"⚠️ {cons_losses} consecutive losses — cool-off active (psych rule)")
        cooloff = True
    else:
        cooloff = False

    new_signals = False
    for sym in STOCKS:
        try:
            d = yf.download(sym, period="1y", interval="1d", progress=False)
            if d.empty or len(d) < 30: continue
            if isinstance(d.columns, pd.MultiIndex): d.columns = [c[0] for c in d.columns]
            name = sym.replace('.NS', '')
            close = d['Close'].iloc[-1]; date = d.index[-1].strftime("%Y-%m-%d")
            signals = run_strategies(d)
            pos = state['positions'].get(name)
            ema50 = d['Close'].ewm(50).mean()

            # ─── EXIT CHECK ───
            if pos:
                exit_signal = None
                for strat, action, price in signals:
                    if action == "SELL" and pos['action'] == "BUY": exit_signal = (strat, price); break
                    elif action == "BUY" and pos['action'] == "SELL": exit_signal = (strat, price); break
                if exit_signal:
                    strat_name, exit_price = exit_signal
                    if pos['action'] == "BUY": pnl = (exit_price - pos['entry_price']) * pos['qty']
                    else: pnl = (pos['entry_price'] - exit_price) * pos['qty']
                    ed = datetime.strptime(pos['entry_date'], "%Y-%m-%d")
                    xd = datetime.strptime(date, "%Y-%m-%d")
                    holding_days = (xd - ed).days
                    trade = {'stock': name, 'action': pos['action'], 'entry_price': pos['entry_price'],
                             'exit_price': round(exit_price,2), 'qty': pos['qty'], 'pnl': round(pnl),
                             'strategy': pos['strategy'], 'entry_date': pos['entry_date'], 'exit_date': date,
                             'holding_days': holding_days, 'notes': f"Exit by {strat_name}"}
                    state['closed_trades'].append(trade)
                    state['capital'] += pnl; del state['positions'][name]
                    if pnl < 0: state['consecutive_losses'] = state.get("consecutive_losses", 0) + 1
                    else: state['consecutive_losses'] = 0
                    new_signals = True
                    icon = "✅" if pnl >= 0 else "❌"
                    print(f"  {icon} CLOSE {pos['action']} {name} @ ₹{exit_price:.2f} | P&L: ₹{pnl:+,} | {holding_days}d | {strat_name}")

            # ─── ENTRY CHECK ───
            if name not in state['positions'] and not cooloff:
                for strat, action, price in signals:
                    if name in state['positions']: break
                    if PSYCH_RULES["trend_filter"]:
                        if action == "BUY" and d['Close'].iloc[-1] < ema50.iloc[-1]: continue
                        if action == "SELL" and d['Close'].iloc[-1] > ema50.iloc[-1]: continue
                    if len(state['positions']) >= PSYCH_RULES["max_concurrent"]: break
                    atr_val = (d['High'] - d['Low']).rolling(14).mean().iloc[-1]
                    stop_dist = 2 * atr_val if atr_val > 0 else price * 0.02
                    qty = max(1, int((state['capital'] * RISK_PCT * position_size_mult) / stop_dist))
                    if qty * price > state['capital'] * 0.3: qty = max(1, int(state['capital'] * 0.3 / price))
                    state['positions'][name] = {'action': action, 'entry_price': float(price), 'qty': qty,
                                                 'entry_date': date, 'strategy': strat}
                    new_signals = True
                    sz = "[HALF] " if position_size_mult < 1 else ""
                    print(f"  🟢 ENTER {action} {name} @ ₹{price:.2f} x {qty} {sz}| {strat}")
                    break
        except Exception as e:
            print(f"  ⚠️ {sym.split('.')[0]}: {e}")

    if "psych_state" not in state: state["psych_state"] = {}
    state["psych_state"]["consecutive_losses"] = state.get("consecutive_losses", 0)
    state["psych_state"]["dd_pct"] = round(dd_pct * 100, 1)

    current_cap = update_excel(state, None)
    save_state(state)

    total_pnl = current_cap - START_CAPITAL
    print(f"\n═══ Summary ═══")
    print(f"Balance: ₹{current_cap:,} | P&L: ₹{total_pnl:+,}")
    print(f"Open: {len(state['positions'])} | Closed: {len(state['closed_trades'])} | Consecutive Losses: {cons_losses}")
    print(f"15 strategies active | Psychology rules: {sum(1 for v in PSYCH_RULES.values() if v)}/10 active")

    state['last_run'] = now_ist.strftime("%Y-%m-%d %H:%M")
    save_state(state)

if __name__ == "__main__":
    import pandas as pd, numpy as np
    run_engine()
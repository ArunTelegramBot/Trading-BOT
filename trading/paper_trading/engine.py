#!/usr/bin/env python3
"""
NSE Paper Trading Engine — runs daily after market close.
Reads state, checks all strategies, executes paper trades, updates Excel.
NEVER resets numbers — always accumulates.
"""
import json, os, warnings, openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from datetime import datetime, timezone, timedelta
from copy import copy
warnings.filterwarnings('ignore')

# ─── CONFIG ────────────────────────────────────────────────
PYTHON = "/home/ubuntu/.hermes/tools/python-3.14.7+202****0901-linux-x64/bin/python3"
BASE = "/home/ubuntu/Trading-BOT/trading/paper_trading"
EXCEL_PATH = f"{BASE}/paper_trading.xlsx"
STATE_PATH = f"{BASE}/state.json"
STOCKS = ["BAJAJFINSV.NS","TCS.NS","ADANIPORTS.NS","M&M.NS","KOTAKBANK.NS",
          "BAJFINANCE.NS","ADANIENT.NS","ICICIBANK.NS","NESTLEIND.NS","ASIANPAINT.NS",
          "LT.NS","TITAN.NS","BHARTIARTL.NS","ULTRACEMCO.NS","SBIN.NS"]
START_CAPITAL = 100000
RISK_PCT = 0.02  # 2% risk per trade
STRATEGIES = ["Supertrend (10,3)", "EMA Crossover (6/30)", "RSI + MACD", "BB Squeeze", "VWAP Pullback"]

# ─── STYLES ────────────────────────────────────────────────
green_fill = PatternFill("solid", fgColor="C6EFCE")
red_fill = PatternFill("solid", fgColor="FFC7CE")
header_fill = PatternFill("solid", fgColor="4472C4")
header_font = Font(bold=True, color="FFFFFF", size=11)
thin_border = Border(left=Side('thin'),right=Side('thin'),top=Side('thin'),bottom=Side('thin'))

# ─── STATE ─────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_PATH):
        return json.load(open(STATE_PATH))
    return {"positions": {}, "closed_trades": [], "capital": START_CAPITAL, "last_run": None}

def save_state(state):
    os.makedirs(BASE, exist_ok=True)
    json.dump(state, open(STATE_PATH, 'w'), indent=2)

# ─── STRATEGIES ────────────────────────────────────────────
def run_strategies(df):
    """Run all strategies on a stock. Returns list of signals."""
    signals = []
    d = df.copy()
    c = d['Close']; h = d['High']; l = d['Low']
    
    # 1. Supertrend (10,3) + EMA50 filter
    hl2 = (h + l) / 2
    atr = (h - l).rolling(10).mean()
    up = hl2 + 3 * atr
    dn = hl2 - 3 * atr
    st = [1]
    for i in range(1, len(d)):
        if c.iloc[i] <= up.iloc[i-1]: st.append(-1)
        elif c.iloc[i] >= dn.iloc[i-1]: st.append(1)
        else: st.append(st[-1])
    d['st'] = st
    d['st_entry'] = d['st'].diff()
    ema50 = c.ewm(50).mean()
    
    last = d.iloc[-1]
    prev = d.iloc[-2]
    
    if last['st_entry'] == 2 and last['Close'] > ema50.iloc[-1]:
        signals.append(("Supertrend (10,3)", "BUY", last['Close']))
    elif last['st_entry'] == -2 and last['Close'] < ema50.iloc[-1]:
        signals.append(("Supertrend (10,3)", "SELL", last['Close']))
    
    # 2. EMA Crossover (6/30)
    ema6 = c.ewm(6).mean()
    ema30 = c.ewm(30).mean()
    if ema6.iloc[-1] > ema30.iloc[-1] and ema6.iloc[-2] <= ema30.iloc[-2]:
        signals.append(("EMA Crossover (6/30)", "BUY", last['Close']))
    elif ema6.iloc[-1] < ema30.iloc[-1] and ema6.iloc[-2] >= ema30.iloc[-2]:
        signals.append(("EMA Crossover (6/30)", "SELL", last['Close']))
    
    # 3. RSI + MACD
    delta = c.diff()
    g = delta.clip(0); lv = -delta.clip(None,0)
    rs = g.rolling(14).mean() / lv.rolling(14).mean()
    rsi = 100 - (100 / (1 + rs))
    mf = c.ewm(12).mean(); ms = c.ewm(26).mean()
    macd = mf - ms; msig = macd.ewm(9).mean(); mh = macd - msig
    
    if len(d) >= 14:
        if rsi.iloc[-1] < 30 and mh.iloc[-1] > 0 and mh.iloc[-2] <= 0:
            signals.append(("RSI + MACD", "BUY", last['Close']))
        elif rsi.iloc[-1] > 70 and mh.iloc[-1] < 0 and mh.iloc[-2] >= 0:
            signals.append(("RSI + MACD", "SELL", last['Close']))
    
    # 4. BB Squeeze
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    bb_u = bb_mid + 2 * bb_std
    bb_l = bb_mid - 2 * bb_std
    bw = (bb_u - bb_l) / bb_mid
    squeeze = bw < 0.3
    
    if squeeze.iloc[-1]:
        if last['Close'] > bb_u.iloc[-1] and prev['Close'] <= bb_u.iloc[-2]:
            signals.append(("BB Squeeze", "BUY", last['Close']))
        elif last['Close'] < bb_l.iloc[-1] and prev['Close'] >= bb_l.iloc[-2]:
            signals.append(("BB Squeeze", "SELL", last['Close']))
    
    # 5. VWAP Pullback
    vwap = (d['Volume'] * hl2).rolling(20).sum() / d['Volume'].rolling(20).sum()
    if len(vwap) >= 20:
        if last['Close'] > vwap.iloc[-1] and prev['Close'] <= vwap.iloc[-1]:
            signals.append(("VWAP Pullback", "BUY", last['Close']))
        elif last['Close'] < vwap.iloc[-1] and prev['Close'] >= vwap.iloc[-1]:
            signals.append(("VWAP Pullback", "SELL", last['Close']))
    
    return signals

def download_data(sym, period="2mo", interval="1d"):
    """Download stock data via subprocess call to yfinance."""
    import subprocess
    script = f"""
import yfinance as yf, json, sys
d = yf.download("{sym}", period="{period}", interval="{interval}", progress=False)
if d.empty: print("[]"); sys.exit(0)
if isinstance(d.columns.droplevel(0)): pass
data = {{"date": d.index[-1].strftime("%Y-%m-%d"), "open": float(d['Open'].iloc[-1]),
        "high": float(d['High'].iloc[-1]), "low": float(d['Low'].iloc[-1]),
        "close": float(d['Close'].iloc[-1]), "volume": float(d['Volume'].iloc[-1])}}
# Also dump full df for strategy calc
import base64, pickle
buf = pickle.dumps(d)
print(base64.b64encode(buf).decode())
"""
    return script

# ─── UPDATE EXCEL ──────────────────────────────────────────
def update_excel(state, stock_signals):
    """Update all 3 tabs in the Excel file."""
    wb = openpyxl.load_workbook(EXCEL_PATH) if os.path.exists(EXCEL_PATH) else openpyxl.Workbook()
    
    # === TAB 1: Trade Log ===
    if "Trade Log" not in wb.sheetnames:
        wb.create_sheet("Trade Log")
    ws1 = wb["Trade Log"]
    if ws1.cell(1,1).value != "Date":
        ws1.cell(1,1,"Date"); ws1.cell(1,2,"Stock"); ws1.cell(1,3,"Action")
        ws1.cell(1,4,"Entry Price"); ws1.cell(1,5,"Exit Price"); ws1.cell(1,6,"Qty")
        ws1.cell(1,7,"P&L (₹)"); ws1.cell(1,8,"Strategy"); ws1.cell(1,9,"Holding Days"); ws1.cell(1,10,"Notes")
    max_row = ws1.max_row
    
    # Write closed trades that aren't already logged
    logged = set()
    for row in range(2, max_row + 1):
        v = ws1.cell(row, 1).value
        if v:
            logged.add(f"{v}_{ws1.cell(row,2).value}_{ws1.cell(row,3).value}")
    
    for trade in state.get("closed_trades", []):
        key = f"{trade.get('exit_date','')}_{trade['stock']}_{'SELL' if trade['action']=='BUY' else 'COVER'}"
        if key not in logged:
            row = max_row + 1
            ws1.cell(row, 1, trade.get("exit_date",""))
            ws1.cell(row, 2, trade['stock'])
            ws1.cell(row, 3, "SELL" if trade['action']=='BUY' else "COVER")
            ws1.cell(row, 4, trade['entry_price'])
            ws1.cell(row, 5, trade['exit_price'])
            ws1.cell(row, 6, trade.get('qty', ''))
            
            pnl_cell = ws1.cell(row, 7, trade['pnl'])
            if trade['pnl'] >= 0:
                pnl_cell.fill = green_fill
            else:
                pnl_cell.fill = red_fill
            pnl_cell.number_format = '#,##0'
            
            ws1.cell(row, 8, trade.get('strategy', ''))
            ws1.cell(row, 9, trade.get('holding_days', ''))
            ws1.cell(row, 10, trade.get('notes', ''))
            
            for c in range(1, 11):
                ws1.cell(row, c).border = thin_border
            max_row = row
    
    # === TAB 2: Strategy Performance ===
    if "Strategy Performance" not in wb.sheetnames:
        ws2 = wb.create_sheet("Strategy Performance")
        for i,h in enumerate(["Strategy","Total Trades","Wins","Losses","Win Rate %","Total P&L (₹)","Avg RR","Max DD %"],1):
            ws2.cell(1,i,h)
    ws2 = wb["Strategy Performance"]
    
    # Calculate per-strategy stats
    strat_stats = {s: {"trades":0, "wins":0, "losses":0, "pnl":0, "win_pnl":0, "loss_pnl":0} for s in STRATEGIES}
    for t in state.get("closed_trades", []):
        s = t.get('strategy', "Supertrend (10,3)")
        if s not in strat_stats:
            strat_stats[s] = {"trades":0, "wins":0, "losses":0, "pnl":0, "win_pnl":0, "loss_pnl":0}
        strat_stats[s]["trades"] += 1
        if t['pnl'] >= 0:
            strat_stats[s]["wins"] += 1
            strat_stats[s]["win_pnl"] += t['pnl']
        else:
            strat_stats[s]["losses"] += 1
            strat_stats[s]["loss_pnl"] += abs(t['pnl'])
        strat_stats[s]["pnl"] += t['pnl']
    
    for idx, s in enumerate(STRATEGIES, 2):
        ss = strat_stats[s]
        ws2.cell(idx, 1, s)
        ws2.cell(idx, 2, ss["trades"])
        wins = ss["wins"]; losses = ss["losses"]
        ws2.cell(idx, 3, wins); ws2.cell(idx, 4, losses)
        ws2.cell(idx, 5, round(wins/(wins+losses)*100,1) if (wins+losses) > 0 else 0)
        pnl_cell = ws2.cell(idx, 6, ss["pnl"])
        pnl_cell.fill = green_fill if ss["pnl"] >= 0 else red_fill
        pnl_cell.number_format = '#,##0'
        avg_win = ss["win_pnl"] / wins if wins > 0 else 0
        avg_loss = ss["loss_pnl"] / losses if losses > 0 else 0
        ws2.cell(idx, 7, round(avg_win/avg_loss,2) if avg_loss > 0 else 0)
        ws2.cell(idx, 8, 0)
    
    # === TAB 3: Account Overview ===
    if "Account Overview" not in wb.sheetnames:
        ws3 = wb.create_sheet("Account Overview")
    ws3 = wb["Account Overview"]
    
    total_pnl = sum(t['pnl'] for t in state.get("closed_trades", []))
    current_capital = START_CAPITAL + total_pnl
    open_positions = len(state.get("positions", {}))
    
    ws3.cell(4, 2, f"₹{current_capital:,}")  # Current Balance
    pnl_label = ws3.cell(5, 2, f"₹{total_pnl:+,}")  # Total P&L
    pnl_label.fill = green_fill if total_pnl >= 0 else red_fill
    ws3.cell(6, 2, open_positions)  # Open Positions
    ws3.cell(7, 2, len(state.get("closed_trades", [])))  # Total Closed Trades
    
    # Monthly P&L
    now = datetime.now(timezone(timedelta(hours=5, minutes=30)))  # IST
    current_month = now.strftime("%b %Y")
    
    month_row = None
    for r in range(12, 50):
        if ws3.cell(r, 1).value == current_month:
            month_row = r
            break
    
    if month_row is None:
        month_row = ws3.max_row + 1
        ws3.cell(month_row, 1, current_month)
        ws3.cell(month_row, 2, f"₹{START_CAPITAL + sum(t['pnl'] for t in state.get('closed_trades',[]) if t.get('exit_date','')[:7] < current_month[:7]):,}")
    
    # Calculate month P&L
    month_trades = [t for t in state.get("closed_trades",[]) if t.get('exit_date','').startswith(current_month[:7])]
    month_pnl = sum(t['pnl'] for t in month_trades)
    
    ws3.cell(month_row, 3, f"₹{current_capital:,}")
    mpnl = ws3.cell(month_row, 4, f"₹{month_pnl:+,}")
    mpnl.fill = green_fill if month_pnl >= 0 else red_fill
    ws3.cell(month_row, 5, f"₹{total_pnl:+,}")
    for c in range(1, 6):
        ws3.cell(month_row, c).border = thin_border
    
    wb.save(EXCEL_PATH)
    return current_capital

# ─── TRADING ENGINE ────────────────────────────────────────
def run_engine():
    print(f"═══ NSE Paper Trading Engine ═══")
    now_ist = datetime.now(timezone(timedelta(hours=5, minutes=30)))
    print(f"Run: {now_ist.strftime('%d-%b-%Y %H:%M IST')}")
    
    state = load_state()
    print(f"Capital: ₹{state['capital']:,} | Open positions: {len(state['positions'])} | Closed trades: {len(state['closed_trades'])}")
    
    import base64, pickle, subprocess, yfinance as yf
    new_signals_generated = False
    
    for sym in STOCKS:
        try:
            d = yf.download(sym, period="3mo", interval="1d", progress=False)
            if d.empty or len(d) < 30:
                continue
            if isinstance(d.columns, type(pd.Index([])) if hasattr(pd,'Index') else tuple):
                try: d.columns = [c[0] for c in d.columns]
                except: pass
            
            name = sym.replace('.NS', '')
            close = d['Close'].iloc[-1]
            date = d.index[-1].strftime("%Y-%m-%d")
            
            # Run strategies
            signals = run_strategies(d)
            
            # Check if we have an open position
            pos = state['positions'].get(name)
            
            # ===== EXIT CHECK =====
            if pos:
                exit_signal = None
                for strat, action, price in signals:
                    if action == "SELL" and pos['action'] == "BUY":
                        exit_signal = (strat, price)
                        break
                    elif action == "BUY" and pos['action'] == "SELL":
                        exit_signal = (strat, price)
                        break
                
                if exit_signal:
                    strat_name, exit_price = exit_signal
                    if pos['action'] == "BUY":
                        pnl = (exit_price - pos['entry_price']) * pos['qty']
                    else:
                        pnl = (pos['entry_price'] - exit_price) * pos['qty']
                    
                    entry_date = pos['entry_date']
                    ed = datetime.strptime(entry_date, "%Y-%m-%d")
                    xd = datetime.strptime(date, "%Y-%m-%d")
                    holding_days = (xd - ed).days
                    
                    trade = {
                        'stock': name, 'action': pos['action'], 'entry_price': pos['entry_price'],
                        'exit_price': round(exit_price,2), 'qty': pos['qty'], 'pnl': round(pnl),
                        'strategy': pos['strategy'], 'entry_date': entry_date, 'exit_date': date,
                        'holding_days': holding_days,
                        'notes': f"Exit by {strat_name}"
                    }
                    state['closed_trades'].append(trade)
                    state['capital'] += pnl
                    del state['positions'][name]
                    new_signals_generated = True
                    print(f"  ✅ CLOSED {pos['action']} {name} @ ₹{exit_price:.2f} | P&L: ₹{pnl:+,} | Held: {holding_days}d | {strat_name}")
            
            # ===== ENTRY CHECK =====
            if name not in state['positions']:
                for strat, action, price in signals:
                    # Check open positions for this stock
                    if name in state['positions']:
                        break
                    
                    # Calculate position size
                    atr = (d['High'] - d['Low']).rolling(14).mean().iloc[-1]
                    stop_dist = 2 * atr if atr > 0 else price * 0.02
                    qty = max(1, int((state['capital'] * RISK_PCT) / stop_dist))
                    if qty * price > state['capital'] * 0.3:
                        qty = max(1, int(state['capital'] * 0.3 / price))
                    
                    state['positions'][name] = {
                        'action': action, 'entry_price': float(price), 'qty': qty,
                        'entry_date': date, 'strategy': strat
                    }
                    new_signals_generated = True
                    print(f"  🟢 ENTER {action} {name} @ ₹{price:.2f} x {qty} | Capital: ₹{state['capital']:,} | {strat}")
                    break
        
        except Exception as e:
            print(f"  ⚠️ {sym.split('.')[0]}: {e}")
    
    # Update Excel
    current_cap = update_excel(state, None)
    save_state(state)
    
    print(f"\n═══ Summary ═══")
    print(f"Balance: ₹{current_cap:,} | P&L: ₹{current_cap - START_CAPITAL:+,}")
    print(f"Open: {len(state['positions'])} | Closed: {len(state['closed_trades'])}")
    
    # Output for cron
    print("\n---CRON_OUTPUT---")
    changes = []
    for t in state.get("closed_trades", []):
        if t.get('exit_date','') >= state.get('last_run', '') or not state.get('last_run'):
            icon = "✅" if t['pnl'] >= 0 else "❌"
            changes.append(f"{icon} {t['stock']}: {t['action']} @ ₹{t['entry_price']} → ₹{t['exit_price']} | P&L: ₹{t['pnl']:+,}")
    if changes:
        print(f"📊 Paper Trading Update — {now_ist.strftime('%d-%b')}")
        for c in changes:
            print(c)
        print(f"Total P&L: ₹{current_cap - START_CAPITAL:+,} | Balance: ₹{current_cap:,}")
        print(f"Excel: github.com/ArunTelegramBot/Trading-BOT/tree/main/trading/paper_trading")
    
    state['last_run'] = now_ist.strftime("%Y-%m-%d %H:%M")
    save_state(state)

if __name__ == "__main__":
    import pandas as pd
    run_engine()
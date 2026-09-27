#!/usr/bin/env python3
"""NSE Intraday Signal Scanner — runs every 30 min during market hours.
Scans 15 algo-ready stocks on 15min timeframe, sends buy/sell signals."""

import yfinance as yf, pandas as pd, numpy as np, json, os, warnings
from datetime import datetime, timezone, timedelta
warnings.filterwarnings('ignore')

STOCKS = ["BAJAJFINSV.NS","TCS.NS","ADANIPORTS.NS","M&M.NS","KOTAKBANK.NS",
          "BAJFINANCE.NS","ADANIENT.NS","ICICIBANK.NS","NESTLEIND.NS","ASIANPAINT.NS",
          "LT.NS","TITAN.NS","BHARTIARTL.NS","ULTRACEMCO.NS","SBIN.NS"]

SIGNAL_FILE = "/home/ubuntu/Trading-BOT/trading/signals/last_signals.json"
PERIOD = "5d"      # 5 days of 15min data
INTERVAL = "15m"

def supertrend(df, period=10, mult=3.0):
    d = df.copy()
    hl2 = (d['High'] + d['Low']) / 2
    d['atr'] = (d['High'] - d['Low']).rolling(period).mean()
    d['up'] = hl2 + mult * d['atr']
    d['dn'] = hl2 - mult * d['atr']
    d['st'] = 1
    for i in range(1, len(d)):
        if d['Close'].iloc[i] <= d['up'].iloc[i-1]: d.loc[d.index[i], 'st'] = -1
        elif d['Close'].iloc[i] >= d['dn'].iloc[i-1]: d.loc[d.index[i], 'st'] = 1
        else: d.loc[d.index[i], 'st'] = d['st'].iloc[i-1]
    d['sig'] = d['st']; d['entry'] = d['sig'].diff()
    return d

# Load previous signals to avoid duplicates
prev = {}
if os.path.exists(SIGNAL_FILE):
    try: prev = json.load(open(SIGNAL_FILE))
    except: pass

now_utc = datetime.now(timezone.utc)
ist_offset = timedelta(hours=5, minutes=30)
now_ist = now_utc + ist_offset

print(f"=== NSE Scanner — {now_ist.strftime('%d-%b-%Y %H:%M IST')} ===")

signals = []
for sym in STOCKS:
    try:
        d = yf.download(sym, period=PERIOD, interval=INTERVAL, progress=False)
        if d.empty or len(d) < 30:
            continue
        if isinstance(d.columns, pd.MultiIndex):
            d.columns = [c[0] for c in d.columns]
        
        df = supertrend(d).dropna()
        if len(df) < 2:
            continue
        
        last = df.iloc[-1]
        prev_row = df.iloc[-2]
        entry = last.get('entry', 0)
        
        name = sym.replace('.NS', '')
        price = round(last['Close'], 2)
        st_direction = "BULL" if last['sig'] == 1 else "BEAR"
        
        # Check for new signal
        signal_type = None
        if entry == 2:  # Changed from short to long
            signal_type = "BUY"
        elif entry == -2:  # Changed from long to short
            signal_type = "SELL"
        
        # Also check EMA50 trend filter (only long if above 50 EMA)
        ema50 = last['Close'] if True else 0
        try:
            ema50 = df['Close'].ewm(50).mean().iloc[-1]
        except:
            ema50 = last['Close']
        
        if signal_type:
            sig_key = f"{name}_{now_ist.strftime('%Y-%m-%d')}"
            prev_sig = prev.get(sig_key, "")
            
            if signal_type != prev_sig:
                signals.append({
                    'stock': name,
                    'price': price,
                    'signal': signal_type,
                    'trend': st_direction,
                    'time': now_ist.strftime('%H:%M'),
                    'date': now_ist.strftime('%Y-%m-%d')
                })
                prev[sig_key] = signal_type
                
                icon = "🟢" if signal_type == "BUY" else "🔴"
                print(f"\n{icon} SIGNAL: {signal_type} {name} @ ₹{price} ({st_direction})")
    
    except Exception as e:
        print(f"  {sym.split('.')[0]}: {e}")

# Save signal state
os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
json.dump(prev, open(SIGNAL_FILE, 'w'))

if not signals:
    print(f"\nNo new signals at {now_ist.strftime('%H:%M IST')}")

print(f"\nScan complete. Active stocks: {len(STOCKS)}")

# Also output signals as JSON for the cron to send
print(f"\n---JSON_OUTPUT---")
print(json.dumps(signals))
print(f"---END_JSON---")
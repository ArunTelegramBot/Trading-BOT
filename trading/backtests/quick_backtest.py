#!/usr/bin/env python3
"""Quick NSE backtest for user — runs on this server."""
import pandas as pd
import numpy as np
import yfinance as yf
warnings.filterwarnings('ignore')
import warnings

CAPITAL = 100000

def ema_crossover(df, fast=6, slow=30):
    df = df.copy()
    df['f'] = df['Close'].ewm(span=fast).mean()
    df['s'] = df['Close'].ewm(span=slow).mean()
    df['sig'] = 0
    df.loc[df['f'] > df['s'], 'sig'] = 1
    df.loc[df['f'] < df['s'], 'sig'] = -1
    df['entry'] = df['sig'].diff()
    return df

def supertrend(df, period=10, mult=3.0):
    df = df.copy()
    hl2 = (df['High'] + df['Low']) / 2
    df['atr'] = (df['High'] - df['Low']).rolling(period).mean()
    df['up'] = hl2 + mult * df['atr']
    df['dn'] = hl2 - mult * df['atr']
    df['st'] = 1
    for i in range(1, len(df)):
        if df['Close'].iloc[i] <= df['up'].iloc[i-1]:
            df.loc[df.index[i], 'st'] = -1
        elif df['Close'].iloc[i] >= df['dn'].iloc[i-1]:
            df.loc[df.index[i], 'st'] = 1
        else:
            df.loc[df.index[i], 'st'] = df['st'].iloc[i-1]
    df['sig'] = df['st']
    df['entry'] = df['sig'].diff()
    df['ema'] = df['Close'].ewm(span=50).mean()
    return df

def rsi_macd(df, rsi_len=14):
    df = df.copy()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    ag = gain.rolling(rsi_len).mean()
    al = loss.rolling(rsi_len).mean()
    rs = ag / al
    df['rsi'] = 100 - (100 / (1 + rs))
    df['mf'] = df['Close'].ewm(span=12).mean()
    df['ms'] = df['Close'].ewm(span=26).mean()
    df['macd'] = df['mf'] - df['ms']
    df['msig'] = df['macd'].ewm(span=9).mean()
    df['mh'] = df['macd'] - df['msig']
    df['sig'] = 0
    df.loc[(df['rsi'] < 30) & (df['mh'] > 0), 'sig'] = 1
    df.loc[(df['rsi'] > 70) & (df['mh'] < 0), 'sig'] = -1
    df['entry'] = df['sig'].diff()
    return df

def run_backtest(symbol, strategy_fn, name):
    try:
        data = yf.download(symbol, period="2y", interval="1d", progress=False)
        if data.empty:
            return None
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [c[0] for c in data.columns]
        data.columns = [str(c).lower() for c in data.columns]
        df = strategy_fn(data).dropna()
        
        cap = CAPITAL
        pos = 0
        ep = 0
        trades = []
        peak = CAPITAL
        
        for i in range(len(df)):
            r = df.iloc[i]
            sig = r.get('entry', 0)
            
            if sig == 2 and pos == 0:
                pos = 1
                ep = r['close']
                shares = max(1, int(cap * 0.01 / ep))
                pos = shares
            elif sig == -2 and pos > 0:
                pnl = (r['close'] - ep) * pos
                cap += pnl
                trades.append({'P&L': round(pnl), 'Type': 'LONG', 'ExitPrice': round(r['close'],2), 'EntryPrice': round(ep,2)})
                pos = 0
            elif sig == -2 and pos == 0:
                pos = -1
                ep = r['close']
                shares = max(1, int(cap * 0.01 / ep))
                pos = -shares
            elif sig == 2 and pos < 0:
                pnl = (ep - r['close']) * abs(pos)
                cap += pnl
                trades.append({'P&L': round(pnl), 'Type': 'SHORT', 'EntryPrice': round(ep,2), 'ExitPrice': round(r['close'],2)})
                pos = 0
            peak = max(peak, cap)
        
        if pos != 0:
            ep2 = df['close'].iloc[-1]
            if pos > 0:
                pnl = (ep2 - ep) * pos
            else:
                pnl = (ep - ep2) * abs(pos)
            cap += pnl
        
        wins = sum(1 for t in trades if t['P&L'] > 0)
        losses = sum(1 for t in trades if t['P&L'] < 0)
        total = len(trades)
        wr = (wins/total*100) if total else 0
        gross_p = sum(t['P&L'] for t in trades if t['P&L'] > 0) or 0
        gross_l = abs(sum(t['P&L'] for t in trades if t['P&L'] < 0)) or 1
        net = sum(t['P&L'] for t in trades)
        dd = (peak - cap) / peak * 100
        rr = (gross_p / wins) / (gross_l / losses) if wins and losses else 0
        
        return {
            'Symbol': symbol.split('.')[0],
            'Strategy': name,
            'Trades': total,
            'Win%': round(wr, 1),
            'NetP&L': round(net),
            'Return%': round((cap-CAPITAL)/CAPITAL*100, 1),
            'AvgRR': round(rr, 2),
            'MaxDD%': round(dd, 1),
            'Best': round(max([t['P&L'] for t in trades] + [0])),
            'Worst': round(min([t['P&L'] for t in trades] + [0])),
        }
    except Exception as e:
        return None

symbols = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
           "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "ITC.NS", "HINDUNILVR.NS",
           "LT.NS", "AXISBANK.NS", "BAJFINANCE.NS", "MARUTI.NS", "TITAN.NS",
           "ASIANPAINT.NS", "NESTLEIND.NS", "WIPRO.NS", "HCLTECH.NS", "SUNPHARMA.NS"]

strategies = [
    ("EMA Crossover (6/30)", ema_crossover),
    ("Supertrend + EMA50", supertrend),
    ("RSI + MACD", rsi_macd),
]

results = []
for s in symbols:
    for name, fn in strategies:
        r = run_backtest(s, fn, name)
        if r:
            results.append(r)
            print(f"  {s.split('.')[0]:12s} | {name:20s} | Trades:{r['Trades']:3d} | Win%:{r['Win%']:5.1f} | P&L:₹{r['NetP&L']:>7,} | Ret:{r['Return%']:5.1f}% | RR:{r['AvgRR']:4.2f} | DD:{r['MaxDD%']:4.1f}%")

print("\n" + "="*110)
print("SUMMARY BY STRATEGY")
print("="*110)
df = pd.DataFrame(results)
for name in [s[0] for s in strategies]:
    sub = df[df['Strategy'] == name]
    print(f"\n--- {name} ---")
    print(f"  Total P&L: ₹{sub['NetP&L'].sum():>8,}  | Avg Trades: {sub['Trades'].mean():.0f}  | Avg Win%: {sub['Win%'].mean():.1f}% | Avg RR: {sub['AvgRR'].mean():.2f} | Avg DD: {sub['MaxDD%'].mean():.1f}%")

print("\n" + "="*110)
print("BEST SINGLE RESULTS")
print("="*110)
top = df.nlargest(5, 'NetP&L')[['Symbol','Strategy','NetP&L','Return%','Win%','AvgRR','MaxDD%']]
for _, r in top.iterrows():
    print(f"  {r['Symbol']:12s} | {r['Strategy']:20s} | ₹{r['NetP&L']:>7,} | {r['Return%']:5.1f}% | Win {r['Win%']}% | RR {r['AvgRR']} | DD {r['MaxDD%']}%")
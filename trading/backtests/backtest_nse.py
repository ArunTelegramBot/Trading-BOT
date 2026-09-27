#!/usr/bin/env python3
"""
NSE Algo Backtester v1 — Test strategies on Indian stocks using yfinance.
Run with: python3 backtest_nse.py
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================
# CONFIG
# ============================================================
SYMBOLS = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "ITC.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS"
]
PERIOD = "2y"        # 2 years of data
INTERVAL = "1d"      # Daily timeframe
RISK_PCT = 1.0       # 1% risk per trade
CAPITAL = 100000     # Initial capital

# ============================================================
# STRATEGIES
# ============================================================

def ema_crossover(data, fast=6, slow=30):
    """EMA Crossover: buy when fast crosses above slow, sell when crosses below"""
    df = data.copy()
    df['ema_fast'] = df['Close'].ewm(span=fast).mean()
    df['ema_slow'] = df['Close'].ewm(span=slow).mean()
    df['signal'] = 0
    df.loc[df['ema_fast'] > df['ema_slow'], 'signal'] = 1
    df.loc[df['ema_fast'] < df['ema_slow'], 'signal'] = -1
    df['entry'] = df['signal'].diff()
    return df

def rsi_macd(data, rsi_len=14, macd_fast=12, macd_slow=26, macd_sig=9):
    """RSI + MACD: buy when RSI < 30 and MACD crosses up, sell when RSI > 70 and MACD crosses down"""
    df = data.copy()
    delta = df['Close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(rsi_len).mean()
    avg_loss = loss.rolling(rsi_len).mean()
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    df['ema_fast'] = df['Close'].ewm(span=macd_fast).mean()
    df['ema_slow'] = df['Close'].ewm(span=macd_slow).mean()
    df['macd'] = df['ema_fast'] - df['ema_slow']
    df['macd_sig'] = df['macd'].ewm(span=macd_sig).mean()
    df['macd_hist'] = df['macd'] - df['macd_sig']
    df['signal'] = 0
    df.loc[(df['rsi'] < 30) & (df['macd_hist'] > df['macd_hist'].shift(1)), 'signal'] = 1
    df.loc[(df['rsi'] > 70) & (df['macd_hist'] < df['macd_hist'].shift(1)), 'signal'] = -1
    df['entry'] = df['signal'].diff()
    return df

def supertrend(data, atr_period=10, multiplier=3.0):
    """SuperTrend: trend-following with ATR-based bands"""
    df = data.copy()
    df['atr'] = df['High'].rolling(atr_period).max() - df['Low'].rolling(atr_period).min()
    df['atr'] = df['atr'].rolling(atr_period).mean()
    hl2 = (df['High'] + df['Low']) / 2
    df['upper'] = hl2 + multiplier * df['atr']
    df['lower'] = hl2 - multiplier * df['atr']
    df['supertrend'] = 1  # 1=bullish, -1=bearish
    for i in range(1, len(df)):
        if df['Close'].iloc[i] <= df['upper'].iloc[i-1]:
            df.loc[df.index[i], 'supertrend'] = -1
        elif df['Close'].iloc[i] >= df['lower'].iloc[i-1]:
            df.loc[df.index[i], 'supertrend'] = 1
        else:
            df.loc[df.index[i], 'supertrend'] = df['supertrend'].iloc[i-1]
    df['signal'] = df['supertrend']
    df['entry'] = df['signal'].diff()
    df['ema50'] = df['Close'].ewm(span=50).mean()
    # Filter: only long if above 50 EMA, only short if below
    df['signal'] = df['signal'].where(df['Close'] > df['ema50'], -1)
    df['signal'] = df['signal'].where(df['Close'] < df['ema50'], 1)
    return df

def bollinger_squeeze(data, bb_len=20, bb_std=2.0, squeeze_thresh=0.3):
    """BB Squeeze: enter on breakout from low-volatility squeeze"""
    df = data.copy()
    df['bb_mid'] = df['Close'].rolling(bb_len).mean()
    df['bb_upper'] = df['bb_mid'] + bb_std * df['Close'].rolling(bb_len).std()
    df['bb_lower'] = df['bb_mid'] - bb_std * df['Close'].rolling(bb_len).std()
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_mid']
    df['squeeze'] = df['bb_width'] < squeeze_thresh
    df['signal'] = 0
    df.loc[df['squeeze'] & (df['Close'] > df['bb_upper']), 'signal'] = 1
    df.loc[df['squeeze'] & (df['Close'] < df['bb_lower']), 'signal'] = -1
    df['entry'] = df['signal'].diff()
    return df

# ============================================================
# BACKTEST ENGINE
# ============================================================

def backtest(df, symbol, strategy_name):
    df = df.dropna()
    capital = CAPITAL
    position = 0
    entry_price = 0
    trades = []

    for i in range(len(df)):
        row = df.iloc[i]
        signal = row.get('entry', 0)

        # Entry logic
        if signal == 2 and position == 0:  # -1 to -1 diff = 0, -1 to 1 = 2, 1 to -1 = -2
            position = 1
            entry_price = row['Close']
            shares = int((capital * RISK_PCT/100) / entry_price)
            if shares < 1: shares = 1
            position = shares

        elif signal == -2 and position == 0:
            position = -1
            entry_price = row['Close']
            shares = int((capital * RISK_PCT/100) / entry_price)
            if shares < 1: shares = 1
            position = -shares

        # Exit logic
        elif signal == -2 and position > 0:  # long exit
            exit_price = row['Close']
            pnl = (exit_price - entry_price) * abs(position)
            capital += pnl
            trades.append({'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'type': 'LONG', 'entry_date': df.index[i-1], 'exit_date': df.index[i]})
            position = 0

        elif signal == 2 and position < 0:  # short exit
            exit_price = row['Close']
            pnl = (entry_price - exit_price) * abs(position)
            capital += pnl
            trades.append({'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'type': 'SHORT', 'entry_date': df.index[i-1], 'exit_date': df.index[i]})
            position = 0

    # Close open position at end
    if position != 0:
        exit_price = df['Close'].iloc[-1]
        if position > 0:
            pnl = (exit_price - entry_price) * position
        else:
            pnl = (entry_price - exit_price) * abs(position)
        capital += pnl
        trades.append({'entry': entry_price, 'exit': exit_price, 'pnl': pnl, 'type': 'LONG' if position > 0 else 'SHORT', 'entry_date': df.index[-2], 'exit_date': df.index[-1]})

    return trades, capital, df

# ============================================================
# RUN
# ============================================================

strategies = {
    "EMA Crossover (6/30)": ema_crossover,
    "RSI + MACD": rsi_macd,
    "Supertrend + EMA50": supertrend,
    "BB Squeeze": bollinger_squeeze,
}

results = []

for symbol in SYMBOLS:
    print(f"Downloading {symbol}...")
    try:
        data = yf.download(symbol, period=PERIOD, interval=INTERVAL, progress=False)
        if data.empty:
            continue
        data.columns = [c[0] if isinstance(c, tuple) else c for c in data.columns]
    except Exception as e:
        print(f"  Error: {e}")
        continue

    for name, strat_fn in strategies.items():
        try:
            df = strat_fn(data.copy())
            trades, final_capital, _ = backtest(df, symbol, name)
            wins = sum(1 for t in trades if t['pnl'] > 0)
            losses = sum(1 for t in trades if t['pnl'] < 0)
            total_trades = len(trades)
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            gross_profit = sum(t['pnl'] for t in trades if t['pnl'] > 0)
            gross_loss = abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
            net_pnl = sum(t['pnl'] for t in trades)
            avg_win = gross_profit / wins if wins > 0 else 0
            avg_loss = gross_loss / losses if losses > 0 else 0
            avg_rr = avg_win / avg_loss if avg_loss > 0 else 0
            returns_pct = (final_capital - CAPITAL) / CAPITAL * 100

            results.append({
                'Symbol': symbol,
                'Strategy': name,
                'Trades': total_trades,
                'Win Rate %': round(win_rate, 1),
                'Net P&L (₹)': round(net_pnl),
                'Return %': round(returns_pct, 1),
                'Avg RR': round(avg_rr, 2),
                'Avg Win': round(avg_win),
                'Avg Loss': round(avg_loss),
                'Wins': wins,
                'Losses': losses
            })
        except Exception as e:
            print(f"  {name}: Error - {e}")

# ============================================================
# RESULTS
# ============================================================

df_results = pd.DataFrame(results)
if df_results.empty:
    print("\nNo results. Check data download.")
else:
    print("\n" + "="*100)
    print("BACKTEST RESULTS — NSE Top 10 Stocks (2 Years Daily)")
    print("="*100)
    print(df_results.to_string(index=False))
    print("="*100)

    # Summary by strategy
    print("\n--- STRATEGY SUMMARY ---")
    summary = df_results.groupby('Strategy').agg({
        'Trades': 'sum',
        'Wins': 'sum',
        'Losses': 'sum',
        'Net P&L (₹)': 'sum',
        'Return %': 'mean',
        'Avg RR': 'mean',
        'Win Rate %': 'mean'
    }).reset_index()
    summary['Win Rate %'] = summary.apply(lambda r: round(r['Wins']/(r['Wins']+r['Losses'])*100, 1) if (r['Wins']+r['Losses']) > 0 else 0, axis=1)
    print(summary.to_string(index=False))
    print("="*100)
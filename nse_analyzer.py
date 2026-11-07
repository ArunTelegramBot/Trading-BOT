#!/usr/bin/env python3
"""
NSE Stock Analyzer — Live data + Technical indicators + Scanner
Usage: python3 nse_analyzer.py <symbol> [--compare SYMBOL] [--scan] [--watchlist FILE]
"""

import yfinance as yf
import pandas as pd
import numpy as np
import sys, json, os
from datetime import datetime, timedelta

def get_nse(symbol):
    """Fetch NSE stock data with .NS suffix"""
    try:
        s = symbol.upper().strip()
        if not s.endswith('.NS'):
            s += '.NS'
        ticker = yf.Ticker(s)
        return ticker, s
    except Exception as e:
        return None, None

def calc_indicators(df):
    """Calculate key technical indicators"""
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']

    # Moving Averages
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()
    ma200 = close.rolling(200).mean()

    # RSI (14)
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    # MACD
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    macd_hist = macd - signal

    # Bollinger Bands (20,2)
    bb_mid = ma20
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    # Volume avg
    vol_20 = volume.rolling(20).mean()
    vol_ratio = volume / vol_20

    return {
        'close': close,
        'ma20': ma20,
        'ma50': ma50,
        'ma200': ma200,
        'rsi': rsi,
        'macd': macd,
        'macd_signal': signal,
        'macd_hist': macd_hist,
        'bb_upper': bb_upper,
        'bb_lower': bb_lower,
        'bb_mid': bb_mid,
        'vol_20': vol_20,
        'vol_ratio': vol_ratio
    }

def analyze_stock(symbol):
    """Full analysis of a single NSE stock"""
    ticker, full_symbol = get_nse(symbol)
    if ticker is None:
        return {"error": f"Could not fetch {symbol}"}

    # Daily data (6 months)
    df_daily = ticker.history(period='6mo')
    if df_daily.empty:
        return {"error": f"No data for {symbol}"}
    
    ind = calc_indicators(df_daily)
    
    # Intraday data (5 days of 15min candles)
    df_intra = ticker.history(period='5d', interval='15m')
    
    # Info
    info = ticker.info or {}
    
    last = df_daily.iloc[-1]
    prev = df_daily.iloc[-2] if len(df_daily) > 1 else last
    week_ago = df_daily.iloc[-6] if len(df_daily) > 5 else df_daily.iloc[0]

    # Get latest indicator values
    current_rsi = round(ind['rsi'].iloc[-1], 1) if not pd.isna(ind['rsi'].iloc[-1]) else None
    current_macd = round(ind['macd'].iloc[-1], 2) if not pd.isna(ind['macd'].iloc[-1]) else None
    current_signal = round(ind['macd_signal'].iloc[-1], 2) if not pd.isna(ind['macd_signal'].iloc[-1]) else None
    vol_ratio = round(ind['vol_ratio'].iloc[-1], 2) if not pd.isna(ind['vol_ratio'].iloc[-1]) else None

    # Trend
    price = round(last['Close'], 2)
    ma20_v = round(ind['ma20'].iloc[-1], 2) if not pd.isna(ind['ma20'].iloc[-1]) else None
    ma50_v = round(ind['ma50'].iloc[-1], 2) if not pd.isna(ind['ma50'].iloc[-1]) else None
    ma200_v = round(ind['ma200'].iloc[-1], 2) if not pd.isna(ind['ma200'].iloc[-1]) else None
    
    # Support/Resistance (simple: recent lows/highs)
    recent_high = round(df_daily['High'].tail(20).max(), 2)
    recent_low = round(df_daily['Low'].tail(20).min(), 2)

    # Change %
    day_change = round(((last['Close'] - prev['Close']) / prev['Close']) * 100, 2)
    week_change = round(((last['Close'] - week_ago['Close']) / week_ago['Close']) * 100, 2)
    
    # Volume
    current_vol = int(last['Volume'])
    avg_vol = int(ind['vol_20'].iloc[-1]) if not pd.isna(ind['vol_20'].iloc[-1]) else None

    # Signal
    signals = []
    if current_rsi and current_rsi > 70:
        signals.append("⚠️ RSI overbought (>" + str(current_rsi) + ")")
    elif current_rsi and current_rsi < 30:
        signals.append("💡 RSI oversold (<" + str(current_rsi) + ")")
    
    if current_macd and current_signal and current_macd > current_signal:
        signals.append("✅ MACD > Signal (bullish crossover)")
    elif current_macd and current_signal and current_macd < current_signal:
        signals.append("❌ MACD < Signal (bearish crossover)")
    
    if price and ma20_v and price > ma20_v:
        signals.append("✅ Price above 20EMA")
    elif price and ma20_v:
        signals.append("❌ Price below 20EMA")
    
    if vol_ratio and vol_ratio > 1.5:
        signals.append(f"🔥 High volume ({vol_ratio}x avg)")
    
    # BB position
    bb_u = round(ind['bb_upper'].iloc[-1], 2) if not pd.isna(ind['bb_upper'].iloc[-1]) else None
    bb_l = round(ind['bb_lower'].iloc[-1], 2) if not pd.isna(ind['bb_lower'].iloc[-1]) else None
    if bb_u and bb_l and price:
        bb_pos = round(((price - bb_l) / (bb_u - bb_l)) * 100, 1)
        if bb_pos > 100:
            signals.append(f"📈 Above upper Bollinger Band")
        elif bb_pos < 0:
            signals.append(f"📉 Below lower Bollinger Band")
        signals.append(f"BB position: {bb_pos}% of band")

    # Fundamentals
    pe = info.get('trailingPE', None)
    market_cap = info.get('marketCap', None)
    sector = info.get('sector', 'N/A')
    div_yield = info.get('dividendYield', None)
    
    result = {
        'symbol': symbol.upper(),
        'price': price,
        'day_change_pct': day_change,
        'week_change_pct': week_change,
        'volume': current_vol,
        'avg_volume': avg_vol,
        'volume_ratio': vol_ratio,
        'rsi_14': current_rsi,
        'macd': current_macd,
        'macd_signal': current_signal,
        'ma20': ma20_v,
        'ma50': ma50_v,
        'ma200': ma200_v,
        'support_20d': recent_low,
        'resistance_20d': recent_high,
        'bb_upper': bb_u,
        'bb_lower': bb_l,
        'pe_ratio': round(pe, 2) if pe else None,
        'market_cap_cr': round(market_cap / 1e7, 2) if market_cap else None,
        'sector': sector,
        'signals': signals
    }
    return result

def format_output(data):
    """Pretty print analysis"""
    if 'error' in data:
        return f"❌ {data['error']}"
    
    lines = []
    lines.append(f"📊 **{data['symbol']}** — ₹{data['price']}")
    lines.append(f"   Day: {data['day_change_pct']}% | Week: {data['week_change_pct']}% | Vol: {data['volume_ratio']}x avg")
    lines.append(f"")
    lines.append(f"**Technicals:**")
    lines.append(f"   RSI(14): {data['rsi_14']} | MACD: {data['macd']} (sig: {data['macd_signal']})")
    lines.append(f"   MA20: {data['ma20']} | MA50: {data['ma50']} | MA200: {data['ma200']}")
    lines.append(f"   S/R (20d): {data['support_20d']} / {data['resistance_20d']}")
    lines.append(f"   Bollinger: {data['bb_lower']} - {data['bb_upper']}")
    lines.append(f"")
    lines.append(f"**Fundamentals:**")
    lines.append(f"   PE: {data['pe_ratio']} | MCap: ₹{data['market_cap_cr']}Cr | Sector: {data['sector']}")
    lines.append(f"")
    if data['signals']:
        lines.append(f"**Signals:**")
        for s in data['signals']:
            lines.append(f"   {s}")
    
    return '\n'.join(lines)

def scan_watchlist(filepath='watchlist.txt'):
    """Scan a watchlist file for top setups"""
    if not os.path.exists(filepath):
        return f"Watchlist file {filepath} not found"
    
    with open(filepath) as f:
        symbols = [s.strip() for s in f.readlines() if s.strip() and not s.startswith('#')]
    
    results = []
    for sym in symbols[:30]:
        data = analyze_stock(sym)
        if 'error' not in data:
            results.append(data)
    
    # Sort by volume ratio (highest first = most active)
    results.sort(key=lambda x: x['volume_ratio'] if x['volume_ratio'] else 0, reverse=True)
    
    lines = [f"📡 **Watchlist Scan — Top Active**", ""]
    for r in results[:10]:
        sig_count = len([s for s in r['signals'] if s.startswith('✅')])
        lines.append(f"{'🟢' if r['day_change_pct'] > 0 else '🔴'} {r['symbol']} ₹{r['price']} ({r['day_change_pct']}%) — Vol {r['volume_ratio']}x — RSI {r['rsi_14']} — {sig_count} bullish signals")
    return '\n'.join(lines)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 nse_analyzer.py <SYMBOL> [--compare SYMBOL] [--scan]")
        sys.exit(1)
    
    if '--scan' in sys.argv:
        print(scan_watchlist())
    else:
        sym = sys.argv[1]
        data = analyze_stock(sym)
        print(format_output(data))
        
        if '--compare' in sys.argv:
            idx = sys.argv.index('--compare')
            if idx + 1 < len(sys.argv):
                data2 = analyze_stock(sys.argv[idx + 1])
                print("\n" + "="*40 + "\n")
                print(format_output(data2))
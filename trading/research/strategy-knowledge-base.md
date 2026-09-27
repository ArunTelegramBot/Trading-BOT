# Strategy Knowledge Base

Consolidated from 31 strategy videos — organized for Indian market application.

---

## 1. SMC/ICT Strategies (Liquidity + Order Blocks + FVGs)
**Concepts:** Liquidity sweeps, order blocks, fair value gaps, market structure breaks
**Core sequence:** Liquidity sweep (trap) → Order block (zone) → FVG (entry)
- Identify swing highs/lows for resting liquidity
- Wait for price to sweep above high or below low (stops get taken out)
- Mark the order block (origin candle before impulsive move)
- Look for FVG within the order block for precise entry
- Always trade in direction of higher timeframe trend
**Timeframes:** HTF (4H/1H) for bias, LTF (15m/5m) for entry
**Key:** Never trade on the touch — wait for the sweep first

## 2. Trend-Following Strategies
### 2a. Simple Trendline Strategy
- Draw trendlines connecting swing highs (downtrend) or swing lows (uptrend)
- Ray tool on TradingView → extends indefinitely
- Top-down analysis: Monthly → Weekly → Daily → 4H → 1H → Entry TF
- Enter on touch/break of trendline with volume confirmation
### 2b. EMA + ADX Trend Following
- Entry long: EMA20 > EMA50, ADX14 > 25, close above EMA20
- Entry short: EMA20 < EMA50, ADX14 > 25, close below EMA20
- Stop loss: 1%, Take profit: 2% (1:2 RR), Exit after 16 candles if no target hit

## 3. Breakout Strategies
### 3a. Horizontal Breakout
- Identify consolidation range (equal highs/lows forming resistance/support)
- Bullish: Price breaks above resistance → buy next candle
- Bearish: Price breaks below support → sell next candle
- Volume must expand on breakout (otherwise likely fakeout)
### 3b. Trendline Breakout
- Downtrend: Draw line across lower highs → bullish when price breaks above
- Uptrend: Draw line across higher lows → bearish when price breaks below
- Enter on retest of broken level
- Stop loss: below/above breakout candle

## 4. Options Strategies (Indian market)
### 4a. Refined 9:20 Straddle (Non-Directional)
- Original 9:20 straddle (sell call + put at 9:20, expire worthless by 3:30)
- **Refined:** Same concept but with adjustments — sell options based on Nifty spot analysis
- Historical data shows 250-pt OTM calls expire worthless 87% of time
- Average Nifty 0DTE range: ~187 pts (top to bottom)
- Key: Add SL, trade only expiry days, manage delta
### 4b. Non-Directional Option Selling
- Sell options in stocks (monthly expiry)
- Trade twice a week (expiry days)
- Target realistic: 20-30% annual, actual often 40-50%
- Add directional hedge if market turns

## 5. Momentum Trading (Sector-Based)
**Core philosophy:** Trade sectors in momentum, not individual stocks
**3 steps:**
1. Identify trending sectors (Nifty sector indices, weekly timeframe)
2. Within trending sector, find stocks showing momentum (big up-move, then consolidation)
3. Enter during contraction/consolidation (order collection phase), NOT at breakout
**Key:** Never buy breakout. Buy when orders are collecting (consolidation after first up-move)
**Timeframe:** Weekly for trend, Daily for entry
**Exit:** When sector momentum fades or stock breaks structure

## 6. VWAP Prop Firm Strategy
**Setup:** 5-min chart + 15-min VWAP overlay on Nasdaq futures
**Entry rules:**
- 64% profitability rate strategy
- Wait for price to drift away from VWAP
- Enter on pullback to VWAP
- Target: mean reversion to VWAP
**Key insight:** Exploit execution algorithms used by banks/brokerages
**Prop firm adaptation:** 93.6% chance of passing within 4 attempts

## 7. Hedge Fund / Quant Method
**3 states:** Bull (last 20 days return ≥ +5%), Bear (≤ -5%), Sideways (in between)
**Markov property:** The market's next move depends only on today's state
**Hedge fund matrix:** 3x3 grid tracking state transitions:
- From bull → bull, bull → sideways, bull → bear
- From sideways → bull, sideways → sideways, sideways → bear
- From bear → bull, bear → sideways, bear → bear
**Use:** Calculate percentage probability of next state based on historical transitions
**Key insight:** Most weight = current state. Past doesn't predict future; transitions do.

## 8. Scalping: 2-Hour Range Strategy
**Setup:**
- HTF: 2-hour candle (first candle of the day, 5:30-7:30 AM IST)
- Mark the high and low of this first 2-hour candle
- LTF: 15-min chart for entry
**Rules:**
- Don't trade inside the range
- Wait for price to break above 2H high (go long) or below 2H low (go short)
- Stop loss: opposite side of the range
- Target: measured move = range width
**Best for:** Crypto, Gold, Forex (24/7 markets)

## 9. Fib Strategy (New York Session)
**Setup:**
- HTF bias on 4H chart
- Trade only during New York session
- First leg move → pullback → second leg move
- Draw Fibonacci from low to high (bullish) or high to low (bearish)
- Preferred entry: 0.5 - 0.618 retracement (Golden Pocket)
- Stop loss below/above the fib zone
**Key:** Trade with HTF trend direction only

## 10. ARC Method (Area Range Candle)
**4 key levels:** Box high, Box low (previous day's range) + Swing high, Swing low
**Rules:**
- At/near box high or swing high → ONLY sell
- At/near box low or swing low → ONLY buy
- In the middle → DO NOTHING ("Don't diddle in the middle")
- These levels represent strongest institutional flow
**Stop loss:** Above/below the level
**Target:** Opposite level

## 11. Market Structure / Price Action
**Core:** Higher highs + higher lows = uptrend (only buy). Lower highs + lower lows = downtrend (only sell)
**Change of character (CHoCH):** When structure breaks from HH/HL to LL/LH (or vice versa)
**Major vs minor swing points:** Major = top/bottom of impulsive moves. Minor = in-between moves
**Timeframe:** Fractal — rules work on all timeframes

## 12. Risk Management Rules (Across all strategies)
- Win rate alone is meaningless: need win rate × average risk:reward
- 33% win rate with 1:6 RR beats 80% with 1:1
- Never risk more than 1-2% per trade
- Max 10% allocation per strategy
- Multiple uncorrelated strategies
- Drawdown calculation: Required capital = margin + max drawdown + buffer

---

## For Indian Market (NSE) Application
- **NSE-specific strategies:** Momentum (sector-based), Option selling, Breakout
- **Pine Script adaptable:** EMA/ADX trend, Breakout strategies, ARC method, VWAP
- **Python backtestable:** All quantifiable strategies (EMA crossover, momentum, RSI)
- **NSE data source:** yfinance (free), Kite API (₹500/mo), ICICI Breeze (free 1-sec data)
- **NSE trading hours:** 9:15-15:30 IST, Options expiry: Thursday
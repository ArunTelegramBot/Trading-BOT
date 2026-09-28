#!/usr/bin/env python3
"""
NSE Paper Trading Engine v2 — 15 Strategies × 15 stocks, independent positions.
Each strategy has own capital. Tracks per-strategy P&L. Never resets.
"""
import json, os, warnings, openpyxl
from openpyxl.styles import PatternFill, Font, Border, Side
from datetime import datetime, timezone, timedelta
warnings.filterwarnings('ignore')

BASE = "/home/ubuntu/Trading-BOT/trading/paper_trading"
EXCEL_PATH = f"{BASE}/paper_trading.xlsx"
STATE_PATH = f"{BASE}/state.json"
STOCKS = ["BAJAJFINSV.NS","TCS.NS","ADANIPORTS.NS","M&M.NS","KOTAKBANK.NS",
          "BAJFINANCE.NS","ADANIENT.NS","ICICIBANK.NS","NESTLEIND.NS","ASIANPAINT.NS",
          "LT.NS","TITAN.NS","BHARTIARTL.NS","ULTRACEMCO.NS","SBIN.NS"]
START_CAPITAL = 100000
CAP_PER_STRATEGY = START_CAPITAL // 15  # ₹6,666 per strategy
RISK_PCT = 0.02

STRATEGIES = [
    "Supertrend+EMA50","EMA Cross 6/30","RSI+MACD","BB Squeeze",
    "VWAP Pullback","EMA+ADX Trend","SMA 50/200 Cross","Donchian 20",
    "Triple EMA 9/21/50","Keltner Breakout","Vol Surge","MACD Hist Flip",
    "ATR Breakout","Hull MA+RSI","Price Structure"
]

green_fill = PatternFill("solid", fgColor="C6EFCE")
red_fill = PatternFill("solid", fgColor="FFC7CE")
thin_border = Border(left=Side('thin'),right=Side('thin'),top=Side('thin'),bottom=Side('thin'))

def load_state():
    if os.path.exists(STATE_PATH):
        return json.load(open(STATE_PATH))
    s = {"strategies": {}, "closed_trades": [], "last_run": None, "trade_count": 0}
    for strat in STRATEGIES:
        s["strategies"][strat] = {"capital": CAP_PER_STRATEGY, "positions": {}, "pnl": 0}
    return s

def save_state(state):
    os.makedirs(BASE, exist_ok=True)
    json.dump(state, open(STATE_PATH, 'w'), indent=2)

def run_strategies_df(d):
    import pandas as pd, numpy as np
    signals = {}
    c = d['Close']; h = d['High']; l = d['Low']; v = d['Volume']
    last = d.iloc[-1]; prev = d.iloc[-2]
    hl2 = (h + l) / 2

    atr_st = (h - l).rolling(10).mean(); up = hl2 + 3*atr_st; dn = hl2 - 3*atr_st
    st = [1]
    for i in range(1,len(d)):
        if c.iloc[i]<=up.iloc[i-1]: st.append(-1)
        elif c.iloc[i]>=dn.iloc[i-1]: st.append(1)
        else: st.append(st[-1])
    st_entry = pd.Series(st).diff()
    ema50 = c.ewm(50).mean()
    if st_entry.iloc[-1]==2 and last['Close']>ema50.iloc[-1]: signals["Supertrend+EMA50"]=("BUY",last['Close'])
    elif st_entry.iloc[-1]==-2 and last['Close']<ema50.iloc[-1]: signals["Supertrend+EMA50"]=("SELL",last['Close'])

    ema6=c.ewm(6).mean(); ema30=c.ewm(30).mean()
    if ema6.iloc[-1]>ema30.iloc[-1] and ema6.iloc[-2]<=ema30.iloc[-2]: signals["EMA Cross 6/30"]=("BUY",last['Close'])
    elif ema6.iloc[-1]<ema30.iloc[-1] and ema6.iloc[-2]>=ema30.iloc[-2]: signals["EMA Cross 6/30"]=("SELL",last['Close'])

    delta=c.diff(); g=delta.clip(0); lv=-delta.clip(None,0)
    rs=g.rolling(14).mean()/lv.rolling(14).mean(); rsi=100-(100/(1+rs))
    mf=c.ewm(12).mean(); ms=c.ewm(26).mean(); macd=mf-ms; msig=macd.ewm(9).mean(); mh=macd-msig
    if len(d)>=14:
        if rsi.iloc[-1]<30 and mh.iloc[-1]>0 and mh.iloc[-2]<=0: signals["RSI+MACD"]=("BUY",last['Close'])
        elif rsi.iloc[-1]>70 and mh.iloc[-1]<0 and mh.iloc[-2]>=0: signals["RSI+MACD"]=("SELL",last['Close'])

    bb_mid=c.rolling(20).mean(); bb_std=c.rolling(20).std(); bb_u=bb_mid+2*bb_std; bb_l=bb_mid-2*bb_std
    bw=(bb_u-bb_l)/bb_mid
    if bw.iloc[-1]<0.3:
        if last['Close']>bb_u.iloc[-1] and prev['Close']<=bb_u.iloc[-2]: signals["BB Squeeze"]=("BUY",last['Close'])
        elif last['Close']<bb_l.iloc[-1] and prev['Close']>=bb_l.iloc[-2]: signals["BB Squeeze"]=("SELL",last['Close'])

    vwap=(v*hl2).rolling(20).sum()/v.rolling(20).sum()
    if len(vwap)>=20:
        if last['Close']>vwap.iloc[-1] and prev['Close']<=vwap.iloc[-1]: signals["VWAP Pullback"]=("BUY",last['Close'])
        elif last['Close']<vwap.iloc[-1] and prev['Close']>=vwap.iloc[-1]: signals["VWAP Pullback"]=("SELL",last['Close'])

    up_move=h.diff().clip(0).rolling(14).mean(); dn_move=(-l.diff()).clip(0).rolling(14).mean()
    dx=abs(up_move-dn_move)/(up_move+dn_move+1e-9)*100; adx_val=dx.rolling(14).mean()
    ema20=c.ewm(20).mean()
    if len(d)>=20:
        if adx_val.iloc[-1]>25 and ema20.iloc[-1]>ema50.iloc[-1] and ema20.iloc[-2]<=ema50.iloc[-2]: signals["EMA+ADX Trend"]=("BUY",last['Close'])
        elif adx_val.iloc[-1]>25 and ema20.iloc[-1]<ema50.iloc[-1] and ema20.iloc[-2]>=ema50.iloc[-2]: signals["EMA+ADX Trend"]=("SELL",last['Close'])

    sma50=c.rolling(50).mean(); sma200=c.rolling(200).mean()
    if len(d)>=200:
        if sma50.iloc[-1]>sma200.iloc[-1] and sma50.iloc[-2]<=sma200.iloc[-2]: signals["SMA 50/200 Cross"]=("BUY",last['Close'])
        elif sma50.iloc[-1]<sma200.iloc[-1] and sma50.iloc[-2]>=sma200.iloc[-2]: signals["SMA 50/200 Cross"]=("SELL",last['Close'])

    dc_high=h.rolling(20).max(); dc_low=l.rolling(20).min()
    if len(d)>=20:
        if last['Close']>dc_high.iloc[-2] and prev['Close']<=dc_high.iloc[-2]: signals["Donchian 20"]=("BUY",last['Close'])
        elif last['Close']<dc_low.iloc[-2] and prev['Close']>=dc_low.iloc[-2]: signals["Donchian 20"]=("SELL",last['Close'])

    ema9=c.ewm(9).mean(); ema21=c.ewm(21).mean()
    if len(d)>=50:
        if ema9.iloc[-1]>ema21.iloc[-1]>ema50.iloc[-1] and not(ema9.iloc[-2]>ema21.iloc[-2]>ema50.iloc[-2]): signals["Triple EMA 9/21/50"]=("BUY",last['Close'])
        elif ema9.iloc[-1]<ema21.iloc[-1]<ema50.iloc[-1] and not(ema9.iloc[-2]<ema21.iloc[-2]<ema50.iloc[-2]): signals["Triple EMA 9/21/50"]=("SELL",last['Close'])

    kc_mid=c.ewm(20).mean(); kc_atr=(h-l).rolling(10).mean(); kc_u=kc_mid+2*kc_atr; kc_l=kc_mid-2*kc_atr
    if len(d)>=20:
        if last['Close']>kc_u.iloc[-1] and prev['Close']<=kc_u.iloc[-2]: signals["Keltner Breakout"]=("BUY",last['Close'])
        elif last['Close']<kc_l.iloc[-1] and prev['Close']>=kc_l.iloc[-2]: signals["Keltner Breakout"]=("SELL",last['Close'])

    vol_avg=v.rolling(20).mean(); ret_1d=c.pct_change()
    if len(d)>=20:
        if last['Volume']>1.5*vol_avg.iloc[-1] and ret_1d.iloc[-1]>0.01: signals["Vol Surge"]=("BUY",last['Close'])
        elif last['Volume']>1.5*vol_avg.iloc[-1] and ret_1d.iloc[-1]<-0.01: signals["Vol Surge"]=("SELL",last['Close'])

    if len(d)>=14:
        if mh.iloc[-1]>0 and mh.iloc[-2]<0: signals["MACD Hist Flip"]=("BUY",last['Close'])
        elif mh.iloc[-1]<0 and mh.iloc[-2]>0: signals["MACD Hist Flip"]=("SELL",last['Close'])

    atr14=(h-l).rolling(14).mean()
    if len(d)>=14:
        if last['Close']>prev['Close']+1.5*atr14.iloc[-2]: signals["ATR Breakout"]=("BUY",last['Close'])
        elif last['Close']<prev['Close']-1.5*atr14.iloc[-2]: signals["ATR Breakout"]=("SELL",last['Close'])

    def hull(s,p):
        w=int(p/2); sp=int(np.sqrt(p)); hm=s.ewm(span=w).mean()*2-s.ewm(span=p).mean()
        return hm.ewm(span=sp).mean()
    if len(d)>=20:
        h9=hull(c,9); h18=hull(c,18)
        if h9.iloc[-1]>h18.iloc[-1] and h9.iloc[-2]<=h18.iloc[-2] and rsi.iloc[-1]>50: signals["Hull MA+RSI"]=("BUY",last['Close'])
        elif h9.iloc[-1]<h18.iloc[-1] and h9.iloc[-2]>=h18.iloc[-2] and rsi.iloc[-1]<50: signals["Hull MA+RSI"]=("SELL",last['Close'])

    if len(d)>=20:
        rh=h.tail(10).max(); rl=l.tail(10).min(); ph=h.shift(1).tail(10).max(); pl=l.shift(1).tail(10).min()
        if last['Close']>ph and prev['Close']<=h.shift(1).iloc[-2]: signals["Price Structure"]=("BUY",last['Close'])
        elif last['Close']<pl and prev['Close']>=l.shift(1).iloc[-2]: signals["Price Structure"]=("SELL",last['Close'])

    return signals

def update_excel(state):
    wb = openpyxl.load_workbook(EXCEL_PATH) if os.path.exists(EXCEL_PATH) else openpyxl.Workbook()

    if "Trade Log" not in wb.sheetnames:
        ws1=wb.create_sheet("Trade Log")
        [ws1.cell(1,i,h) for i,h in enumerate(["Date","Stock","Strategy","Action","Entry","Exit","Qty","P&L","Days","Strat Capital"],1)]
    ws1=wb["Trade Log"]
    logged=set(); [logged.add(f"{ws1.cell(r,1).value}_{ws1.cell(r,2).value}_{ws1.cell(r,3).value}") for r in range(2,ws1.max_row+1) if ws1.cell(r,1).value]
    for t in state.get("closed_trades",[]):
        k=f"{t['exit_date']}_{t['stock']}_{t['strategy']}"
        if k not in logged:
            r=ws1.max_row+1; ws1.cell(r,1,t['exit_date']); ws1.cell(r,2,t['stock']); ws1.cell(r,3,t['strategy'])
            ws1.cell(r,4,"SELL" if t['action']=='BUY' else "COVER"); ws1.cell(r,5,t['entry']); ws1.cell(r,6,t['exit']); ws1.cell(r,7,t['qty'])
            ws1.cell(r,8,t['pnl']).fill=green_fill if t['pnl']>=0 else red_fill; ws1.cell(r,9,t.get('days','')); ws1.cell(r,10,t.get('strat_cap',''))
            for c in range(1,11): ws1.cell(r,c).border=thin_border

    if "Strategy Performance" not in wb.sheetnames:
        ws2=wb.create_sheet("Strategy Performance")
        [ws2.cell(1,i,h) for i,h in enumerate(["Strategy","Trades","Wins","Losses","Win%","P&L","Avg RR","Now","Return%"],1)]
    ws2=wb["Strategy Performance"]
    for i,s in enumerate(STRATEGIES,2):
        sd=state["strategies"][s]; trades=[t for t in state.get("closed_trades",[]) if t['strategy']==s]
        w=sum(1 for t in trades if t['pnl']>=0); l_=sum(1 for t in trades if t['pnl']<0); pnl=sum(t['pnl'] for t in trades)
        cr=sd['capital']+sum(t['pnl'] for t in trades); rt=(cr-CAP_PER_STRATEGY)/CAP_PER_STRATEGY*100
        aw=sum(t['pnl'] for t in trades if t['pnl']>=0)/w if w>0 else 0
        al=abs(sum(t['pnl'] for t in trades if t['pnl']<0))/l_ if l_>0 else 1
        ws2.cell(i,1,s); ws2.cell(i,2,len(trades)); ws2.cell(i,3,w); ws2.cell(i,4,l_)
        ws2.cell(i,5,round(w/(w+l_)*100,1) if (w+l_)>0 else 0)
        ws2.cell(i,6,pnl).fill=green_fill if pnl>=0 else red_fill; ws2.cell(i,7,round(aw/al,2) if al>0 else 0)
        ws2.cell(i,8,f"₹{cr:,.0f}"); ws2.cell(i,9,f"{rt:+.1f}%")
        for c in range(1,10): ws2.cell(i,c).border=thin_border

    if "Account Overview" in wb.sheetnames:
        ws3=wb["Account Overview"]; [ws3.unmerge_cells(str(mr)) for mr in list(ws3.merged_cells.ranges)]
    else: ws3=wb.create_sheet("Account Overview")
    total_cap=sum(sd['capital']+sum(t['pnl'] for t in state.get("closed_trades",[]) if t['strategy']==s) for s,sd in [(s,state["strategies"][s]) for s in STRATEGIES])
    total_pnl=total_cap-START_CAPITAL; open_pos=sum(len(state["strategies"][s]["positions"]) for s in STRATEGIES)
    all_trades=len(state.get("closed_trades",[]))
    ws3.cell(1,1,"ACCOUNT OVERVIEW").font=Font(bold=True,size=14)
    for i,(k,v) in enumerate([("Start Capital",f"₹{START_CAPITAL:,}"),("Current Capital",f"₹{total_cap:,.0f}"),
        ("Total P&L",f"₹{total_pnl:+,}"),("Total Trades",all_trades),("Open Positions",open_pos),
        ("Return %",f"{total_pnl/START_CAPITAL*100:+.2f}%")],2):
        ws3.cell(i,1,k).font=Font(bold=True); ws3.cell(i,2,v); ws3.cell(i,2).border=thin_border
    ws3.cell(4,2).fill=green_fill if total_pnl>=0 else red_fill

    ws3.cell(9,1,"PER-STRATEGY CAPITAL").font=Font(bold=True,size=11)
    for i,s in enumerate(STRATEGIES,10):
        sd=state["strategies"][s]; trades=[t for t in state.get("closed_trades",[]) if t['strategy']==s]
        cr=sd['capital']+sum(t['pnl'] for t in trades)
        ws3.cell(i,1,s); ws3.cell(i,2,f"₹{cr:,.0f}")
    wb.save(EXCEL_PATH); return total_cap

def run_engine():
    import pandas as pd, numpy as np, yfinance as yf
    state=load_state()
    now_ist=datetime.now(timezone(timedelta(hours=5,minutes=30)))
    tc=sum(state['strategies'][s]['capital'] for s in STRATEGIES)
    print(f"RUN: {now_ist.strftime('%d-%b-%Y %H:%M IST')} | Total: ₹{tc:,.0f}")
    print(f"Strat capital: ₹{CAP_PER_STRATEGY} each | {len(STRATEGIES)} strats × {len(STOCKS)} stocks")
    new_trades=0
    for sym in STOCKS:
        try:
            d=yf.download(sym,period="1y",interval="1d",progress=False)
            if d.empty or len(d)<30: continue
            if isinstance(d.columns,pd.MultiIndex): d.columns=[c[0] for c in d.columns]
            name=sym.replace('.NS',''); date=d.index[-1].strftime("%Y-%m-%d")
            signals=run_strategies_df(d); ema50=d['Close'].ewm(50).mean()
            for strat in STRATEGIES:
                sd=state["strategies"][strat]; sig=signals.get(strat); pos=sd["positions"].get(name)
                if pos and sig:
                    act,price=sig
                    if (act=="SELL" and pos['action']=="BUY") or (act=="BUY" and pos['action']=="SELL"):
                        pnl=(price-pos['entry'])*pos['qty'] if pos['action']=="BUY" else (pos['entry']-price)*pos['qty']
                        ed=datetime.strptime(pos['entry_date'],"%Y-%m-%d"); xd=datetime.strptime(date,"%Y-%m-%d")
                        state['closed_trades'].append({'stock':name,'strategy':strat,'action':pos['action'],
                            'entry':round(pos['entry'],2),'exit':round(price,2),'qty':pos['qty'],'pnl':round(pnl),
                            'days':(xd-ed).days,'exit_date':date,'strat_cap':round(sd['capital'])})
                        sd['capital']+=pnl; sd['pnl']+=pnl; del sd["positions"][name]; new_trades+=1
                        icon="✅" if pnl>=0 else "❌"
                        print(f"  {icon} {strat[:12]:12s} CLOSE {name} @ ₹{price:.0f} P&L ₹{pnl:+,}")
                if name not in sd["positions"] and sig:
                    act,price=sig
                    if (act=="BUY" and d['Close'].iloc[-1]<ema50.iloc[-1]) or (act=="SELL" and d['Close'].iloc[-1]>ema50.iloc[-1]): continue
                    atr_val=(d['High']-d['Low']).rolling(14).mean().iloc[-1]; stop=2*atr_val if atr_val>0 else price*0.02
                    qty=max(1,int((sd['capital']*RISK_PCT)/stop))
                    if qty*price>sd['capital']*0.3: qty=max(1,int(sd['capital']*0.3/price))
                    sd["positions"][name]={'action':act,'entry':float(price),'qty':qty,'entry_date':date}
                    new_trades+=1; print(f"  🟢 {strat[:12]:12s} ENTR {act} {name} @ ₹{price:.0f} x{qty}")
        except Exception as e: print(f"  ⚠️ {sym.split('.')[0]}: {e}")
    update_excel(state); save_state(state)
    all_cap=sum(state['strategies'][s]['capital'] for s in STRATEGIES)
    closed=len(state['closed_trades']); op=sum(len(state['strategies'][s]['positions']) for s in STRATEGIES)
    print(f"\nSummary: ₹{all_cap:,.0f} | P&L ₹{all_cap-START_CAPITAL:+,} | Trades {closed} | Open {op} | New {new_trades}")
    state['last_run']=now_ist.strftime("%Y-%m-%d %H:%M"); save_state(state)

if __name__=="__main__":
    import pandas as pd, numpy as np
    run_engine()
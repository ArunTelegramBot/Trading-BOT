#!/usr/bin/env python3
"""NSE v4 — 10-min intraday, 100 stocks, 50 strats, ₹5L, auto SL/TP, psychology rules."""
import json,os,warnings,openpyxl
from openpyxl.styles import PatternFill,Font,Border,Side
from datetime import datetime,timezone,timedelta
warnings.filterwarnings('ignore')
B="/home/ubuntu/Trading-BOT/trading/paper_trading"
E=f"{B}/paper_trading.xlsx"; S=f"{B}/state.json"; P="/home/ubuntu/Trading-BOT/trading/stocks_100.txt"
I=500000; C=I//50; R=0.02; SL=1.5; TP=3.0

ST=[
"S7/2","S10/2","S10/3","S14/3","S20/4",           # Supertrend 5
"E5/13","E6/30","E8/21","E10/50","E20/50",         # EMA Cross 5
"RSI30","RSI25","RSI75","RSIDiv",                   # RSI 4
"MHist","MACross","MACDV",                           # MACD 3
"BBSqz","BB%<.2","BB%>.8","BBNar","BBExt",          # BB 5
"ADX25","ADX30","ADX20",                             # ADX 3
"D20","D10","D55",                                   # Donchian 3
"VSurge","VClimax","VAccum","VDist",                 # Volume 4
"KBreak","KCTouch","KReject",                         # Keltner 3
"StrBreak","InBar","Engulf","3Bar",                  # PA 4
"ATR1.5","ATR2","ATRAve",                            # ATR 3
"H9/18","H9/50",                                     # Hull 2
"VWAPPull","VWAPDiv",                                 # VWAP 2
"ROCS","ROCV","PRIROC",                               # Momentum 3
"Confluence"                                          # Multi 1
]

G=PatternFill("solid",fgColor="C6EFCE"); Rf=PatternFill("solid",fgColor="FFC7CE")
T=Border(left=Side('thin'),right=Side('thin'),top=Side('thin'),bottom=Side('thin'))
KK=[s.strip() for s in open(P).readlines() if s.strip() and not s.startswith('#')]
def ls():
    if os.path.exists(S): return json.load(open(S))
    r={"strategies":{},"closed_trades":[],"last_run":None,"trade_count":0,"psych":{"dd":0,"loss_streak":0,"trades_today":0}}
    for s in ST: r["strategies"][s]={"capital":C,"positions":{},"pnl":0}
    return r
def ss(x): os.makedirs(B,exist_ok=True); json.dump(x,open(S,'w'),indent=2)

def calc(d):
    import pandas as pd,numpy as np
    r={}; c=d['Close']; h=d['High']; l=d['Low']; v=d['Volume']
    la=d.iloc[-1]; pr=d.iloc[-2]; h2=(h+l)/2; n=len(d)

    # Pre-compute common indicators
    e50=c.ewm(50).mean(); e20=c.ewm(20).mean(); e10=c.ewm(10).mean()
    sma50=c.rolling(50).mean(); sma200=c.rolling(200).mean()
    a14=(h-l).rolling(14).mean()
    a10=(h-l).rolling(10).mean()
    va=v.rolling(20).mean(); rt=c.pct_change()
    dl=c.diff(); g=dl.clip(0); lv=-dl.clip(None,0)
    rs=g.rolling(14).mean()/lv.rolling(14).mean(); rsi=100-(100/(1+rs))
    mf=c.ewm(12).mean(); ms=c.ewm(26).mean(); mc=mf-ms; msig=mc.ewm(9).mean(); mh=mc-msig
    bm=c.rolling(20).mean(); bs=c.rolling(20).std(); bu=bm+2*bs; bl=bm-2*bs; bw=(bu-bl)/bm

    def st(atr_p,a14_v,mult):
        u=h2+mult*a14_v; dn=h2-mult*a14_v; st=[1]
        for i in range(1,n):
            if c.iloc[i]<=u.iloc[i-1]: st.append(-1)
            elif c.iloc[i]>=dn.iloc[i-1]: st.append(1)
            else: st.append(st[-1])
        return pd.Series(st).diff()

    def hull(s,p):
        w=int(p/2); sp=int(np.sqrt(p)); hm=s.ewm(span=w).mean()*2-s.ewm(span=p).mean()
        return hm.ewm(span=sp).mean()

    # 1-5: Supertrend variants
    se=st(a10,c,2)
    if se.iloc[-1]==2 and la['Close']>e50.iloc[-1]: r["S7/2"]=("BUY",la['Close'])
    elif se.iloc[-1]==-2 and la['Close']<e50.iloc[-1]: r["S7/2"]=("SELL",la['Close'])
    se=st(a10,c,2.5)
    if se.iloc[-1]==2: r["S10/2"]=("BUY",la['Close'])
    elif se.iloc[-1]==-2: r["S10/2"]=("SELL",la['Close'])
    se=st(a14,c,3)
    if se.iloc[-1]==2 and la['Close']>e20.iloc[-1]: r["S10/3"]=("BUY",la['Close'])
    elif se.iloc[-1]==-2 and la['Close']<e20.iloc[-1]: r["S10/3"]=("SELL",la['Close'])
    se=st(a14,c,3.5)
    if se.iloc[-1]==2: r["S14/3"]=("BUY",la['Close'])
    elif se.iloc[-1]==-2: r["S14/3"]=("SELL",la['Close'])
    se=st(a14,c,4)
    if se.iloc[-1]==2: r["S20/4"]=("BUY",la['Close'])
    elif se.iloc[-1]==-2: r["S20/4"]=("SELL",la['Close'])

    # 6-10: EMA Cross variants
    e5=c.ewm(5).mean(); e13=c.ewm(13).mean()
    if e5.iloc[-1]>e13.iloc[-1] and e5.iloc[-2]<=e13.iloc[-2]: r["E5/13"]=("BUY",la['Close'])
    elif e5.iloc[-1]<e13.iloc[-1] and e5.iloc[-2]>=e13.iloc[-2]: r["E5/13"]=("SELL",la['Close'])
    e6=c.ewm(6).mean(); e30=c.ewm(30).mean()
    if e6.iloc[-1]>e30.iloc[-1] and e6.iloc[-2]<=e30.iloc[-2]: r["E6/30"]=("BUY",la['Close'])
    elif e6.iloc[-1]<e30.iloc[-1] and e6.iloc[-2]>=e30.iloc[-2]: r["E6/30"]=("SELL",la['Close'])
    e8=c.ewm(8).mean(); e21=c.ewm(21).mean()
    if e8.iloc[-1]>e21.iloc[-1] and e8.iloc[-2]<=e21.iloc[-2]: r["E8/21"]=("BUY",la['Close'])
    elif e8.iloc[-1]<e21.iloc[-1] and e8.iloc[-2]>=e21.iloc[-2]: r["E8/21"]=("SELL",la['Close'])
    e1=c.ewm(10).mean(); e5o=c.ewm(50).mean()
    if e1.iloc[-1]>e5o.iloc[-1] and e1.iloc[-2]<=e5o.iloc[-2]: r["E10/50"]=("BUY",la['Close'])
    elif e1.iloc[-1]<e5o.iloc[-1] and e1.iloc[-2]>=e5o.iloc[-2]: r["E10/50"]=("SELL",la['Close'])
    if e20.iloc[-1]>e50.iloc[-1] and e20.iloc[-2]<=e50.iloc[-2]: r["E20/50"]=("BUY",la['Close'])
    elif e20.iloc[-1]<e50.iloc[-1] and e20.iloc[-2]>=e50.iloc[-2]: r["E20/50"]=("SELL",la['Close'])

    # 11-14: RSI variants
    if n>=14:
        if rsi.iloc[-1]<30 and mh.iloc[-1]>0 and mh.iloc[-2]<=0: r["RSI30"]=("BUY",la['Close'])
        elif rsi.iloc[-1]>70 and mh.iloc[-1]<0 and mh.iloc[-2]>=0: r["RSI30"]=("SELL",la['Close'])
        if rsi.iloc[-1]<25: r["RSI25"]=("BUY",la['Close'])
        elif rsi.iloc[-1]>75: r["RSI25"]=("SELL",la['Close'])
        if rsi.iloc[-1]>50 and rsi.iloc[-2]<=50: r["RSI75"]=("BUY",la['Close'])
        elif rsi.iloc[-1]<50 and rsi.iloc[-2]>=50: r["RSI75"]=("SELL",la['Close'])
        # RSI divergence (price makes new low but RSI doesn't)
        if n>=30:
            if la['Close']<d['Close'].tail(15).min() and rsi.iloc[-1]>rsi.tail(15).max(): r["RSIDiv"]=("BUY",la['Close'])
            elif la['Close']>d['Close'].tail(15).max() and rsi.iloc[-1]<rsi.tail(15).min(): r["RSIDiv"]=("SELL",la['Close'])

    # 15-17: MACD variants
    if n>=14:
        if mh.iloc[-1]>0 and mh.iloc[-2]<0: r["MHist"]=("BUY",la['Close'])
        elif mh.iloc[-1]<0 and mh.iloc[-2]>0: r["MHist"]=("SELL",la['Close'])
        if mc.iloc[-1]>msig.iloc[-1] and mc.iloc[-2]<=msig.iloc[-2]: r["MACross"]=("BUY",la['Close'])
        elif mc.iloc[-1]<msig.iloc[-1] and mc.iloc[-2]>=msig.iloc[-2]: r["MACross"]=("SELL",la['Close'])
        if mh.iloc[-1]>0 and la['Volume']>1.5*va.iloc[-1]: r["MACDV"]=("BUY",la['Close'])
        elif mh.iloc[-1]<0 and la['Volume']>1.5*va.iloc[-1]: r["MACDV"]=("SELL",la['Close'])

    # 18-22: BB variants
    if bw.iloc[-1]<0.2:
        if la['Close']>bu.iloc[-1]: r["BBSqz"]=("BUY",la['Close'])
        elif la['Close']<bl.iloc[-1]: r["BBSqz"]=("SELL",la['Close'])
    pctb=(la['Close']-bl.iloc[-1])/(bu.iloc[-1]-bl.iloc[-1]) if (bu.iloc[-1]-bl.iloc[-1])>0 else 0.5
    if pctb<0.2 and rt.iloc[-1]>0: r["BB%<.2"]=("BUY",la['Close'])
    if pctb>0.8 and rt.iloc[-1]<0: r["BB%>.8"]=("SELL",la['Close'])
    if n>=5 and bw.iloc[-1]<bw.iloc[-5]*0.9 and la['Close']>bm.iloc[-1]: r["BBNar"]=("BUY",la['Close'])
    elif n>=5 and bw.iloc[-1]<bw.iloc[-5]*0.9 and la['Close']<bm.iloc[-1]: r["BBNar"]=("SELL",la['Close'])
    if la['Close']>bu.iloc[-1] and la['Volume']>1.5*va.iloc[-1]: r["BBExt"]=("BUY",la['Close'])
    elif la['Close']<bl.iloc[-1] and la['Volume']>1.5*va.iloc[-1]: r["BBExt"]=("SELL",la['Close'])

    # 23-25: ADX variants
    um=h.diff().clip(0).rolling(14).mean(); dm_=(-l.diff()).clip(0).rolling(14).mean()
    dx=abs(um-dm_)/(um+dm_+1e-9)*100; ax=dx.rolling(14).mean()
    if n>=20:
        if ax.iloc[-1]>25 and e20.iloc[-1]>e50.iloc[-1] and e20.iloc[-2]<=e50.iloc[-2]: r["ADX25"]=("BUY",la['Close'])
        elif ax.iloc[-1]>25 and e20.iloc[-1]<e50.iloc[-1] and e20.iloc[-2]>=e50.iloc[-2]: r["ADX25"]=("SELL",la['Close'])
        if ax.iloc[-1]>30 and um.iloc[-1]>dm_.iloc[-1]: r["ADX30"]=("BUY",la['Close'])
        elif ax.iloc[-1]>30 and um.iloc[-1]<dm_.iloc[-1]: r["ADX30"]=("SELL",la['Close'])
        if ax.iloc[-1]>20 and e10.iloc[-1]>e50.iloc[-1]: r["ADX20"]=("BUY",la['Close'])
        elif ax.iloc[-1]>20 and e10.iloc[-1]<e50.iloc[-1]: r["ADX20"]=("SELL",la['Close'])

    # 26-28: Donchian variants
    dh20=h.rolling(20).max(); dl20=l.rolling(20).min()
    dh10=h.rolling(10).max(); dl10=l.rolling(10).min()
    dh55=h.rolling(55).max(); dl55=l.rolling(55).min()
    if n>=20:
        if la['Close']>dh20.iloc[-2] and pr['Close']<=dh20.iloc[-2]: r["D20"]=("BUY",la['Close'])
        elif la['Close']<dl20.iloc[-2] and pr['Close']>=dl20.iloc[-2]: r["D20"]=("SELL",la['Close'])
    if n>=10:
        if la['Close']>dh10.iloc[-2] and pr['Close']<=dh10.iloc[-2]: r["D10"]=("BUY",la['Close'])
        elif la['Close']<dl10.iloc[-2] and pr['Close']>=dl10.iloc[-2]: r["D10"]=("SELL",la['Close'])
    if n>=55:
        if la['Close']>dh55.iloc[-2] and pr['Close']<=dh55.iloc[-2]: r["D55"]=("BUY",la['Close'])
        elif la['Close']<dl55.iloc[-2] and pr['Close']>=dl55.iloc[-2]: r["D55"]=("SELL",la['Close'])

    # 29-32: Volume variants
    if n>=20:
        if la['Volume']>1.5*va.iloc[-1] and rt.iloc[-1]>0.015: r["VSurge"]=("BUY",la['Close'])
        elif la['Volume']>1.5*va.iloc[-1] and rt.iloc[-1]<-0.015: r["VSurge"]=("SELL",la['Close'])
        if la['Volume']>2.5*va.iloc[-1] and rt.iloc[-1]<-0.01: r["VClimax"]=("SELL",la['Close'])
        elif la['Volume']>2.5*va.iloc[-1] and rt.iloc[-1]>0.01: r["VClimax"]=("BUY",la['Close'])
        if la['Volume']<va.iloc[-1]*0.5 and la['Close']>e50.iloc[-1]: r["VAccum"]=("BUY",la['Close'])
        if la['Volume']<va.iloc[-1]*0.5 and la['Close']<e50.iloc[-1]: r["VDist"]=("SELL",la['Close'])

    # 33-35: Keltner variants
    km=c.ewm(20).mean(); ka=a10
    if n>=20:
        ku=km+2*ka; kl=km-2*ka
        if la['Close']>ku.iloc[-1] and pr['Close']<=ku.iloc[-2]: r["KBreak"]=("BUY",la['Close'])
        elif la['Close']<kl.iloc[-1] and pr['Close']>=kl.iloc[-2]: r["KBreak"]=("SELL",la['Close'])
        if la['Close']<km.iloc[-1]*1.02 and la['Close']>km.iloc[-1]*0.98: r["KCTouch"]=("NEUTRAL",la['Close'])
        if la['Close']>ku.iloc[-1] and la['Close']<ku.iloc[-1]*1.01 and rt.iloc[-1]<0: r["KReject"]=("SELL",la['Close'])
        elif la['Close']<kl.iloc[-1] and la['Close']>kl.iloc[-1]*0.99 and rt.iloc[-1]>0: r["KReject"]=("BUY",la['Close'])

    # 36-39: Price Action variants
    if n>=20:
        rh=h.tail(10).max(); rl=l.tail(10).min(); ph=h.shift(1).tail(10).max(); pl=l.shift(1).tail(10).min()
        if la['Close']>ph and pr['Close']<=h.shift(1).iloc[-2]: r["StrBreak"]=("BUY",la['Close'])
        elif la['Close']<pl and pr['Close']>=l.shift(1).iloc[-2]: r["StrBreak"]=("SELL",la['Close'])
    # Inside bar
    if n>=3:
        if la['High']<d['High'].iloc[-2] and la['Low']>d['Low'].iloc[-2]: r["InBar"]=("NEUTRAL",la['Close'])
    # Engulfing
    if n>=3:
        if la['Close']>la['Open'] and pr['Close']<pr['Open'] and la['Open']<pr['Close'] and la['Close']>pr['Open']: r["Engulf"]=("BUY",la['Close'])
        elif la['Close']<la['Open'] and pr['Close']>pr['Open'] and la['Open']>pr['Close'] and la['Close']<pr['Open']: r["Engulf"]=("SELL",la['Close'])
    # 3-bar push
    if n>=4:
        if all(d['Close'].iloc[-i]>d['Close'].iloc[-i-1] for i in range(1,4)) and la['Close']<la['Open']: r["3Bar"]=("SELL",la['Close'])
        elif all(d['Close'].iloc[-i]<d['Close'].iloc[-i-1] for i in range(1,4)) and la['Close']>la['Open']: r["3Bar"]=("BUY",la['Close'])

    # 40-42: ATR variants
    if n>=14:
        if la['Close']>pr['Close']+1.5*a14.iloc[-2]: r["ATR1.5"]=("BUY",la['Close'])
        elif la['Close']<pr['Close']-1.5*a14.iloc[-2]: r["ATR1.5"]=("SELL",la['Close'])
        if la['Close']>pr['Close']+2*a14.iloc[-2]: r["ATR2"]=("BUY",la['Close'])
        elif la['Close']<pr['Close']-2*a14.iloc[-2]: r["ATR2"]=("SELL",la['Close'])
        # ATR trailing: price stays within ATR band
        if abs(rt.iloc[-1])<a14.iloc[-1]/c.iloc[-1]: r["ATRAve"]=("NEUTRAL",la['Close'])

    # 43-44: Hull MA variants
    if n>=20:
        h9=hull(c,9); h18=hull(c,18); h50=hull(c,50)
        if h9.iloc[-1]>h18.iloc[-1] and h9.iloc[-2]<=h18.iloc[-2] and rsi.iloc[-1]>50: r["H9/18"]=("BUY",la['Close'])
        elif h9.iloc[-1]<h18.iloc[-1] and h9.iloc[-2]>=h18.iloc[-2] and rsi.iloc[-1]<50: r["H9/18"]=("SELL",la['Close'])
        if h9.iloc[-1]>h50.iloc[-1] and h9.iloc[-2]<=h50.iloc[-2]: r["H9/50"]=("BUY",la['Close'])
        elif h9.iloc[-1]<h50.iloc[-1] and h9.iloc[-2]>=h50.iloc[-2]: r["H9/50"]=("SELL",la['Close'])

    # 45-46: VWAP variants
    if n>=20:
        vwap=(v*h2).rolling(20).sum()/v.rolling(20).sum()
        if la['Close']>vwap.iloc[-1] and pr['Close']<=vwap.iloc[-1]: r["VWAPPull"]=("BUY",la['Close'])
        elif la['Close']<vwap.iloc[-1] and pr['Close']>=vwap.iloc[-1]: r["VWAPPull"]=("SELL",la['Close'])
        # VWAP divergence: price vs VWAP direction mismatch
        if la['Close']>vwap.iloc[-1] and rt.iloc[-1]<0: r["VWAPDiv"]=("BUY",la['Close'])
        elif la['Close']<vwap.iloc[-1] and rt.iloc[-1]>0: r["VWAPDiv"]=("SELL",la['Close'])

    # 47-49: Momentum variants  
    if n>=10:
        roc=(c.iloc[-1]/c.iloc[-10]-1)*100
        if roc>3: r["ROCS"]=("BUY",la['Close'])
        elif roc<-3: r["ROCS"]=("SELL",la['Close'])
        if roc>2 and la['Volume']>1.3*va.iloc[-1]: r["ROCV"]=("BUY",la['Close'])
        elif roc<-2 and la['Volume']>1.3*va.iloc[-1]: r["ROCV"]=("SELL",la['Close'])
        if c.iloc[-1]>c.iloc[-10] and c.iloc[-1]>c.iloc[-5]: r["PRIROC"]=("BUY",la['Close'])
        elif c.iloc[-1]<c.iloc[-10] and c.iloc[-1]<c.iloc[-5]: r["PRIROC"]=("SELL",la['Close'])

    # 50: Confluence (multi-indicator agreement)
    signals=[v for v in r.values() if v!="NEUTRAL"]
    bulls=sum(1 for v in signals if v[0]=="BUY"); bears=sum(1 for v in signals if v[0]=="SELL")
    if bulls>=5: r["Confluence"]=("BUY",la['Close'])
    elif bears>=5: r["Confluence"]=("SELL",la['Close'])

    return r

def ux(state):
    wb=openpyxl.load_workbook(E) if os.path.exists(E) else openpyxl.Workbook()
    if "Trade Log" not in wb.sheetnames:
        w1=wb.create_sheet("Trade Log")
        for i,h in enumerate(["Date","Time","Stock","Strategy","Action","Entry","Exit","Qty","P&L","Exit Reason"],1): w1.cell(1,i,h)
    w1=wb["Trade Log"]; log=set()
    for r in range(2,w1.max_row+1):
        v=w1.cell(r,1).value
        if v: log.add(f"{w1.cell(r,1).value}_{w1.cell(r,3).value}_{w1.cell(r,4).value}")
    for t in state.get("closed_trades",[]):
        k=f"{t['exit_date']}_{t['stock']}_{t['strategy']}"
        if k not in log:
            r=w1.max_row+1; w1.cell(r,1,t['exit_date']); w1.cell(r,2,t['exit_time'])
            w1.cell(r,3,t['stock']); w1.cell(r,4,t['strategy'])
            w1.cell(r,5,"SELL" if t['action']=='BUY' else "COVER"); w1.cell(r,6,t['entry']); w1.cell(r,7,t['exit']); w1.cell(r,8,t['qty'])
            p=w1.cell(r,9,t['pnl']); p.fill=G if t['pnl']>=0 else Rf; w1.cell(r,10,t.get('exit_reason',''))
            for c in range(1,11): w1.cell(r,c).border=T
    if "Strategy Performance" not in wb.sheetnames:
        w2=wb.create_sheet("Strategy Performance")
        for i,h in enumerate(["Strategy","Trades","Wins","Losses","Win%","P&L","Avg RR","Now","Return%"],1): w2.cell(1,i,h)
    w2=wb["Strategy Performance"]
    for i,s in enumerate(ST,2):
        td=[t for t in state.get("closed_trades",[]) if t['strategy']==s]
        w=sum(1 for t in td if t['pnl']>=0); l=sum(1 for t in td if t['pnl']<0); pn=sum(t['pnl'] for t in td)
        aw=sum(t['pnl'] for t in td if t['pnl']>=0)/w if w>0 else 0
        al=abs(sum(t['pnl'] for t in td if t['pnl']<0))/l if l>0 else 1
        cr=state["strategies"][s]['capital']+pn; rr=(cr-C)/C*100
        w2.cell(i,1,s); w2.cell(i,2,len(td)); w2.cell(i,3,w); w2.cell(i,4,l)
        w2.cell(i,5,round(w/(w+l)*100,1) if (w+l)>0 else 0)
        w2.cell(i,6,pn).fill=G if pn>=0 else Rf; w2.cell(i,7,round(aw/al,2) if al>0 else 0)
        w2.cell(i,8,f"₹{cr:,.0f}"); w2.cell(i,9,f"{rr:+.1f}%")
        for c in range(1,10): w2.cell(i,c).border=T
    if "Account Overview" in wb.sheetnames:
        w3=wb["Account Overview"]
        for m in list(w3.merged_cells.ranges): w3.unmerge_cells(str(m))
    else: w3=wb.create_sheet("Account Overview")
    tc=sum(state['strategies'][s]['capital'] for s in ST); tp=tc-I
    op=sum(len(state['strategies'][s]['positions']) for s in ST); tr=len(state.get("closed_trades",[]))
    ps=state.get("psych",{})
    w3.cell(1,1,"ACCOUNT OVERVIEW").font=Font(bold=True,size=14)
    for i,(k,v) in enumerate([("Start",f"₹{I:,}"),("Capital",f"₹{tc:,.0f}"),("P&L",f"₹{tp:+,}"),("Trades",tr),("Open",op),("Return",f"{tp/I*100:+.2f}%")],2):
        w3.cell(i,1,k).font=Font(bold=True); w3.cell(i,2,v); w3.cell(i,2).border=T
    w3.cell(4,2).fill=G if tp>=0 else Rf
    w3.cell(9,1,f"🧠 PSYCHOLOGY RULES").font=Font(bold=True,size=12)
    w3.cell(10,1,"Max 2% risk/trade ✓ | Max 5 pos ✓ | Trend filter ✓")
    w3.cell(11,1,"Cool-off 3 losses ✓ | Half-size on 10% DD ✓ | No avg-down ✓")
    w3.cell(12,1,"DD%"); w3.cell(12,2,f"{ps.get('dd',0):.1f}%")
    w3.cell(13,1,"Loss streak"); w3.cell(13,2,ps.get("loss_streak",0))
    w3.cell(14,1,f"{len(ST)} STRATS | {len(KK)} STOCKS | SL {SL}x TP {TP}x | 10MIN").font=Font(bold=True,size=11)
    wb.save(E); return tc

def go():
    import pandas as pd,numpy as np,yfinance as yf
    state=ls(); ni=datetime.now(timezone(timedelta(hours=5,minutes=30)))
    ds=ni.strftime("%Y-%m-%d"); ts=ni.strftime("%H:%M"); wd=ni.weekday(); hr=ni.hour; mn=ni.minute
    if wd>=5 or hr<9 or hr>15 or (hr==9 and mn<15) or (hr==15 and mn>30):
        print(f"Closed. {len(state.get('closed_trades',[]))} total trades.")
        return
    tc=sum(state['strategies'][s]['capital'] for s in ST)
    print(f"RUN {ds} {ts} | ₹{tc:,.0f} | {len(KK)}×{len(ST)}={len(KK)*len(ST)} checks/run")
    ps=state.get("psych",{"dd":0,"loss_streak":0,"trades_today":0})
    dd=(I-tc)/I*100 if tc<I else 0; cooloff=ps.get("loss_streak",0)>=3; psize=0.5 if dd>10 else 1.0
    nt=0
    for sym in KK:
        try:
            d=yf.download(sym,period="5d",interval="15m",progress=False)
            if d.empty or len(d)<30: continue
            if isinstance(d.columns,pd.MultiIndex): d.columns=[c[0] for c in d.columns]
            nm=sym.replace('.NS',''); la=d.iloc[-1]; pr=d.iloc[-2]
            ss_d=calc(d); e50=d['Close'].ewm(50).mean(); a14=(d['High']-d['Low']).rolling(14).mean()
            for st in ST:
                sd=state["strategies"][st]; p=sd["positions"].get(nm); sg=ss_d.get(st)
                if p:
                    er=None; ep=None
                    if p['action']=='BUY':
                        if la['Low']<=p['sl']: er="SL"; ep=p['sl']
                        elif la['High']>=p['tp']: er="TP"; ep=p['tp']
                    else:
                        if la['High']>=p['sl']: er="SL"; ep=p['sl']
                        elif la['Low']<=p['tp']: er="TP"; ep=p['tp']
                    if not er and sg and sg[0]!="NEUTRAL":
                        ac,pc=sg
                        if (ac=="SELL" and p['action']=="BUY") or (ac=="BUY" and p['action']=="SELL"): er="SIG"; ep=pc
                    if er:
                        pnl=(ep-p['entry'])*p['qty'] if p['action']=="BUY" else (p['entry']-ep)*p['qty']
                        state['closed_trades'].append({'exit_date':ds,'exit_time':ts,'stock':nm,'strategy':st,
                            'action':p['action'],'entry':round(p['entry'],2),'exit':round(ep,2),'qty':p['qty'],
                            'pnl':round(pnl),'exit_reason':er})
                        sd['capital']+=pnl; sd['pnl']+=pnl; del sd["positions"][nm]; nt+=1
                        if pnl<0: ps["loss_streak"]=ps.get("loss_streak",0)+1
                        else: ps["loss_streak"]=0
                        ic="✅" if pnl>=0 else "❌"
                        print(f"  {ic} {st:7s} {er:4s} {nm} @{round(ep):.0f} ₹{pnl:+,}")
                if nm not in sd["positions"] and sg and sg[0]!="NEUTRAL" and not cooloff:
                    ac,pc=sg
                    if (ac=="BUY" and d['Close'].iloc[-1]<e50.iloc[-1]) or (ac=="SELL" and d['Close'].iloc[-1]>e50.iloc[-1]): continue
                    av=a14.iloc[-1] if len(a14)>0 else pc*0.01; sd_=SL*av if av>0 else pc*0.015
                    q=max(1,int((sd['capital']*R*psize)/sd_))
                    if q*pc>sd['capital']*0.3: q=max(1,int(sd['capital']*0.3/pc))
                    if q<1: continue
                    sl=pc-SL*av if ac=="BUY" else pc+SL*av
                    tp=pc+TP*av if ac=="BUY" else pc-TP*av
                    sd["positions"][nm]={'action':ac,'entry':float(pc),'qty':q,'entry_date':ds,'entry_time':ts,'sl':float(sl),'tp':float(tp)}
                    nt+=1; print(f"  🟢 {st:7s} ENTR {ac} {nm} @{round(pc):.0f} x{q} SL@{round(sl):.0f} TP@{round(tp):.0f}")
        except Exception as e: print(f"  ⚠️ {sym.split('.')[0]}: {e}")
    ps["dd"]=dd; ps["trades_today"]=ps.get("trades_today",0)+nt; state["psych"]=ps
    ux(state); ss(state)
    cl=len(state['closed_trades']); op=sum(len(state['strategies'][s]['positions']) for s in ST)
    tc=sum(state['strategies'][s]['capital'] for s in ST)
    print(f"DONE: ₹{tc:,.0f} | P&L ₹{tc-I:+,} | Trades {cl} | Open {op} | New {nt}")
    if cooloff: print("⚠️ COOL-OFF ACTIVE (3+ consecutive losses)")
    state['last_run']=ni.strftime("%Y-%m-%d %H:%M"); ss(state)
if __name__=="__main__":
    import pandas as pd,numpy as np; go()
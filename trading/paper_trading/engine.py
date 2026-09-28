#!/usr/bin/env python3
"""NSE v3 — 10-min intraday, 50 stocks, auto SL/TP. 15 strats x 50 stocks."""
import json,os,warnings,openpyxl
from openpyxl.styles import PatternFill,Font,Border,Side
from datetime import datetime,timezone,timedelta
warnings.filterwarnings('ignore')
B="/home/ubuntu/Trading-BOT/trading/paper_trading"
E=f"{B}/paper_trading.xlsx"; S=f"{B}/state.json"; P="/home/ubuntu/Trading-BOT/trading/stocks_50.txt"
I=100000; C=I//15; R=0.02; SL=1.5; TP=3.0
ST=["Supertrend+EMA50","EMA Cross 6/30","RSI+MACD","BB Squeeze","VWAP Pullback",
    "EMA+ADX Trend","SMA 50/200 Cross","Donchian 20","Triple EMA 9/21/50","Keltner Breakout",
    "Vol Surge","MACD Hist Flip","ATR Breakout","Hull MA+RSI","Price Structure"]
G=PatternFill("solid",fgColor="C6EFCE"); Rf=PatternFill("solid",fgColor="FFC7CE")
T=Border(left=Side('thin'),right=Side('thin'),top=Side('thin'),bottom=Side('thin'))
KK=[s.strip() for s in open(P).readlines() if s.strip() and not s.startswith('#')]
def ls():
    if os.path.exists(S): return json.load(open(S))
    r={"strategies":{},"closed_trades":[],"last_run":None,"trade_count":0}
    for s in ST: r["strategies"][s]={"capital":C,"positions":{},"pnl":0}
    return r
def ss(x): os.makedirs(B,exist_ok=True); json.dump(x,open(S,'w'),indent=2)

def sg(d):
    import pandas as pd,numpy as np
    r={}; c=d['Close']; h=d['High']; l=d['Low']; v=d['Volume']
    la=d.iloc[-1]; pr=d.iloc[-2]; h2=(h+l)/2
    a=(h-l).rolling(10).mean(); u=h2+3*a; dn=h2-3*a; st=[1]
    for i in range(1,len(d)):
        if c.iloc[i]<=u.iloc[i-1]: st.append(-1)
        elif c.iloc[i]>=dn.iloc[i-1]: st.append(1)
        else: st.append(st[-1])
    se=pd.Series(st).diff(); e50=c.ewm(50).mean()
    if se.iloc[-1]==2 and la['Close']>e50.iloc[-1]: r["Supertrend+EMA50"]=("BUY",la['Close'])
    elif se.iloc[-1]==-2 and la['Close']<e50.iloc[-1]: r["Supertrend+EMA50"]=("SELL",la['Close'])
    e6=c.ewm(6).mean(); e30=c.ewm(30).mean()
    if e6.iloc[-1]>e30.iloc[-1] and e6.iloc[-2]<=e30.iloc[-2]: r["EMA Cross 6/30"]=("BUY",la['Close'])
    elif e6.iloc[-1]<e30.iloc[-1] and e6.iloc[-2]>=e30.iloc[-2]: r["EMA Cross 6/30"]=("SELL",la['Close'])
    dl=c.diff(); g=dl.clip(0); lv=-dl.clip(None,0)
    rs=g.rolling(14).mean()/lv.rolling(14).mean(); rsi=100-(100/(1+rs))
    mf=c.ewm(12).mean(); ms=c.ewm(26).mean(); mc=mf-ms; msig=mc.ewm(9).mean(); mh=mc-msig
    if len(d)>=14:
        if rsi.iloc[-1]<30 and mh.iloc[-1]>0 and mh.iloc[-2]<=0: r["RSI+MACD"]=("BUY",la['Close'])
        elif rsi.iloc[-1]>70 and mh.iloc[-1]<0 and mh.iloc[-2]>=0: r["RSI+MACD"]=("SELL",la['Close'])
    bm=c.rolling(20).mean(); bs=c.rolling(20).std(); bu=bm+2*bs; bl=bm-2*bs
    if (bu-bl)/bm.iloc[-1]<0.3:
        if la['Close']>bu.iloc[-1] and pr['Close']<=bu.iloc[-2]: r["BB Squeeze"]=("BUY",la['Close'])
        elif la['Close']<bl.iloc[-1] and pr['Close']>=bl.iloc[-2]: r["BB Squeeze"]=("SELL",la['Close'])
    vw=(v*h2).rolling(20).sum()/v.rolling(20).sum()
    if len(vw)>=20:
        if la['Close']>vw.iloc[-1] and pr['Close']<=vw.iloc[-1]: r["VWAP Pullback"]=("BUY",la['Close'])
        elif la['Close']<vw.iloc[-1] and pr['Close']>=vw.iloc[-1]: r["VWAP Pullback"]=("SELL",la['Close'])
    um=h.diff().clip(0).rolling(14).mean(); dm=(-l.diff()).clip(0).rolling(14).mean()
    dx=abs(um-dm)/(um+dm+1e-9)*100; ax=dx.rolling(14).mean(); e20=c.ewm(20).mean()
    if len(d)>=20:
        if ax.iloc[-1]>25 and e20.iloc[-1]>e50.iloc[-1] and e20.iloc[-2]<=e50.iloc[-2]: r["EMA+ADX Trend"]=("BUY",la['Close'])
        elif ax.iloc[-1]>25 and e20.iloc[-1]<e50.iloc[-1] and e20.iloc[-2]>=e50.iloc[-2]: r["EMA+ADX Trend"]=("SELL",la['Close'])
    s50=c.rolling(50).mean(); s200=c.rolling(200).mean()
    if len(d)>=200:
        if s50.iloc[-1]>s200.iloc[-1] and s50.iloc[-2]<=s200.iloc[-2]: r["SMA 50/200 Cross"]=("BUY",la['Close'])
        elif s50.iloc[-1]<s200.iloc[-1] and s50.iloc[-2]>=s200.iloc[-2]: r["SMA 50/200 Cross"]=("SELL",la['Close'])
    dh=h.rolling(20).max(); dl=l.rolling(20).min()
    if len(d)>=20:
        if la['Close']>dh.iloc[-2] and pr['Close']<=dh.iloc[-2]: r["Donchian 20"]=("BUY",la['Close'])
        elif la['Close']<dl.iloc[-2] and pr['Close']>=dl.iloc[-2]: r["Donchian 20"]=("SELL",la['Close'])
    e9=c.ewm(9).mean(); e21=c.ewm(21).mean()
    if len(d)>=50:
        if e9.iloc[-1]>e21.iloc[-1]>e50.iloc[-1] and not(e9.iloc[-2]>e21.iloc[-2]>e50.iloc[-2]): r["Triple EMA 9/21/50"]=("BUY",la['Close'])
        elif e9.iloc[-1]<e21.iloc[-1]<e50.iloc[-1] and not(e9.iloc[-2]<e21.iloc[-2]<e50.iloc[-2]): r["Triple EMA 9/21/50"]=("SELL",la['Close'])
    km=c.ewm(20).mean(); ka=(h-l).rolling(10).mean(); ku=km+2*ka; kl=km-2*ka
    if len(d)>=20:
        if la['Close']>ku.iloc[-1] and pr['Close']<=ku.iloc[-2]: r["Keltner Breakout"]=("BUY",la['Close'])
        elif la['Close']<kl.iloc[-1] and pr['Close']>=kl.iloc[-2]: r["Keltner Breakout"]=("SELL",la['Close'])
    va=v.rolling(20).mean(); rt=c.pct_change()
    if len(d)>=20:
        if la['Volume']>1.5*va.iloc[-1] and rt.iloc[-1]>0.01: r["Vol Surge"]=("BUY",la['Close'])
        elif la['Volume']>1.5*va.iloc[-1] and rt.iloc[-1]<-0.01: r["Vol Surge"]=("SELL",la['Close'])
    if len(d)>=14:
        if mh.iloc[-1]>0 and mh.iloc[-2]<0: r["MACD Hist Flip"]=("BUY",la['Close'])
        elif mh.iloc[-1]<0 and mh.iloc[-2]>0: r["MACD Hist Flip"]=("SELL",la['Close'])
    a14=(h-l).rolling(14).mean()
    if len(d)>=14:
        if la['Close']>pr['Close']+1.5*a14.iloc[-2]: r["ATR Breakout"]=("BUY",la['Close'])
        elif la['Close']<pr['Close']-1.5*a14.iloc[-2]: r["ATR Breakout"]=("SELL",la['Close'])
    def hl(s,p):
        w=int(p/2); sp=int(np.sqrt(p)); hm=s.ewm(span=w).mean()*2-s.ewm(span=p).mean()
        return hm.ewm(span=sp).mean()
    if len(d)>=20:
        h9=hl(c,9); h18=hl(c,18)
        if h9.iloc[-1]>h18.iloc[-1] and h9.iloc[-2]<=h18.iloc[-2] and rsi.iloc[-1]>50: r["Hull MA+RSI"]=("BUY",la['Close'])
        elif h9.iloc[-1]<h18.iloc[-1] and h9.iloc[-2]>=h18.iloc[-2] and rsi.iloc[-1]<50: r["Hull MA+RSI"]=("SELL",la['Close'])
    if len(d)>=20:
        rh=h.tail(10).max(); rl=l.tail(10).min(); ph=h.shift(1).tail(10).max(); pl=l.shift(1).tail(10).min()
        if la['Close']>ph and pr['Close']<=h.shift(1).iloc[-2]: r["Price Structure"]=("BUY",la['Close'])
        elif la['Close']<pl and pr['Close']>=l.shift(1).iloc[-2]: r["Price Structure"]=("SELL",la['Close'])
    return r

def ux(state):
    wb=openpyxl.load_workbook(E) if os.path.exists(E) else openpyxl.Workbook()
    if "Trade Log" not in wb.sheetnames:
        w1=wb.create_sheet("Trade Log")
        for i,h in enumerate(["Date","Time","Stock","Strategy","Action","Entry","Exit","Qty","P&L","Exit Reason"],1): w1.cell(1,i,h)
    w1=wb["Trade Log"]; log=set()
    for r in range(2,w1.max_row+1):
        v=w1.cell(r,1).value
        if v: log.add(f"{w1.cell(r,1).value}_{w1.cell(r,4).value}_{w1.cell(r,3).value}_{w1.cell(r,10).value}")
    for t in state.get("closed_trades",[]):
        k=f"{t['exit_date']}_{t['strategy']}_{t['stock']}_{t['exit_reason']}"
        if k not in log:
            r=w1.max_row+1; w1.cell(r,1,t['exit_date']); w1.cell(r,2,t['exit_time']); w1.cell(r,3,t['stock']); w1.cell(r,4,t['strategy'])
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
        cr=state["strategies"][s]['capital']+sum(t['pnl'] for t in td); rr=(cr-C)/C*100
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
    w3.cell(1,1,"ACCOUNT OVERVIEW").font=Font(bold=True,size=14)
    for i,(k,v) in enumerate([("Start",f"₹{I:,}"),("Capital",f"₹{tc:,.0f}"),("P&L",f"₹{tp:+,}"),("Trades",tr),("Open",op),("Return",f"{tp/I*100:+.2f}%")],2):
        w3.cell(i,1,k).font=Font(bold=True); w3.cell(i,2,v); w3.cell(i,2).border=T
    w3.cell(4,2).fill=G if tp>=0 else Rf
    w3.cell(9,1,f"50 STOCKS | 15 STRATS | SL {SL}xATR | TP {TP}xATR | EVERY 10MIN").font=Font(bold=True,size=11)
    wb.save(E); return tc

def go():
    import pandas as pd,numpy as np,yfinance as yf
    state=ls(); ni=datetime.now(timezone(timedelta(hours=5,minutes=30)))
    ds=ni.strftime("%Y-%m-%d"); ts=ni.strftime("%H:%M"); wd=ni.weekday(); hr=ni.hour; mn=ni.minute
    if wd>=5 or hr<9 or hr>15 or (hr==9 and mn<15) or (hr==15 and mn>30):
        print(f"Market closed. {len(state.get('closed_trades',[]))} total trades.")
        return
    tc=sum(state['strategies'][s]['capital'] for s in ST)
    print(f"RUN {ds} {ts} IST | ₹{tc:,.0f} | {len(KK)} stocks"); nt=0
    for sym in KK:
        try:
            d=yf.download(sym,period="5d",interval="15m",progress=False)
            if d.empty or len(d)<30: continue
            if isinstance(d.columns,pd.MultiIndex): d.columns=[c[0] for c in d.columns]
            nm=sym.replace('.NS',''); la=d.iloc[-1]; pr=d.iloc[-2]
            s=sg(d); e50=d['Close'].ewm(50).mean(); a14=(d['High']-d['Low']).rolling(14).mean()
            for st in ST:
                sd=state["strategies"][st]; p=sd["positions"].get(nm)
                if p:
                    er=None; ep=None
                    if p['action']=='BUY':
                        if la['Low']<=p['sl']: er="SL"; ep=p['sl']
                        elif la['High']>=p['tp']: er="TP"; ep=p['tp']
                    else:
                        if la['High']>=p['sl']: er="SL"; ep=p['sl']
                        elif la['Low']<=p['tp']: er="TP"; ep=p['tp']
                    if not er and s.get(st):
                        ac,pc=s[st]
                        if (ac=="SELL" and p['action']=="BUY") or (ac=="BUY" and p['action']=="SELL"): er="SIG"; ep=pc
                    if er:
                        pnl=(ep-p['entry'])*p['qty'] if p['action']=="BUY" else (p['entry']-ep)*p['qty']
                        state['closed_trades'].append({'exit_date':ds,'exit_time':ts,'stock':nm,'strategy':st,
                            'action':p['action'],'entry':round(p['entry'],2),'exit':round(ep,2),'qty':p['qty'],
                            'pnl':round(pnl),'exit_reason':er})
                        sd['capital']+=pnl; sd['pnl']+=pnl; del sd["positions"][nm]; nt+=1
                        ic="✅" if pnl>=0 else "❌"
                        print(f"  {ic} {st[:10]:10s} {er:6s} {nm} @{round(ep):.0f} ₹{pnl:+,}")
                if nm not in sd["positions"] and s.get(st):
                    ac,pc=s[st]
                    if (ac=="BUY" and d['Close'].iloc[-1]<e50.iloc[-1]) or (ac=="SELL" and d['Close'].iloc[-1]>e50.iloc[-1]): continue
                    av=a14.iloc[-1] if len(a14)>0 else pc*0.01; sd_=SL*av if av>0 else pc*0.015
                    q=max(1,int((sd['capital']*R)/sd_))
                    if q*pc>sd['capital']*0.3: q=max(1,int(sd['capital']*0.3/pc))
                    if q<1: continue
                    sl=pc-SL*av if ac=="BUY" else pc+SL*av
                    tp=pc+TP*av if ac=="BUY" else pc-TP*av
                    sd["positions"][nm]={'action':ac,'entry':float(pc),'qty':q,'entry_date':ds,'entry_time':ts,'sl':float(sl),'tp':float(tp)}
                    nt+=1; print(f"  🟢 {st[:10]:10s} ENTR {ac} {nm} @{round(pc):.0f} x{q} SL@{round(sl):.0f} TP@{round(tp):.0f}")
        except Exception as e: print(f"  ⚠️ {sym.split('.')[0]}: {e}")
    ux(state); ss(state)
    cl=len(state['closed_trades']); op=sum(len(state['strategies'][s]['positions']) for s in ST)
    tc=sum(state['strategies'][s]['capital'] for s in ST)
    print(f"DONE: ₹{tc:,.0f} | P&L ₹{tc-I:+,} | Trades {cl} | Open {op} | New {nt}")
    state['last_run']=ni.strftime("%Y-%m-%d %H:%M"); ss(state)
if __name__=="__main__":
    import pandas as pd,numpy as np; go()
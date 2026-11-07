import json

with open('/home/ubuntu/Trading-BOT/trading/paper_trading/jev_log.json') as f:
    jev_log = json.load(f)
with open('/home/ubuntu/Trading-BOT/trading/paper_trading/state.json') as f:
    state = json.load(f)

closed = state.get('closed_trades', [])

# Check how many Jev entries have 'entry' field
has_entry = sum(1 for e in jev_log if 'entry' in e)
no_entry = sum(1 for e in jev_log if 'entry' not in e)
print(f"Jev entries with entry price: {has_entry}")
print(f"Jev entries without entry price: {no_entry}")

# Check per date
from collections import Counter
dates = sorted(set(e['date'] for e in jev_log))
for d in dates:
    de = [e for e in jev_log if e['date'] == d]
    he = sum(1 for e in de if 'entry' in e)
    print(f"  {d}: {len(de)} entries, {he} with entry")

# For entries WITHOUT entry, try matching by stock+strategy only (any close trade)
close_lookup = {}
for t in closed:
    key = (t.get('stock',''), t.get('strategy',''))
    if key not in close_lookup:
        close_lookup[key] = []
    close_lookup[key].append(t)

agree_map = {'BUY': 'LONG', 'SELL': 'SHORT'}

# Relaxed matching: stock+strategy only, take most recent closed trade
date_ordered = {}
for t in closed:
    key = (t.get('stock',''), t.get('strategy',''))
    if key not in date_ordered:
        date_ordered[key] = []
    date_ordered[key].append(t)

# Take the most recent closed trade for each stock+strategy
recent_lookup = {}
for k, trades in date_ordered.items():
    # Sort by exit_date descending
    trades.sort(key=lambda t: t.get('exit_date',''), reverse=True)
    recent_lookup[k] = trades[0]

# Match all entries using entry price or most recent close
all_agree_pnl = []
all_wait_pnl = []

for e in jev_log:
    key = (e['stock'], e['strategy'])
    entry_price = e.get('entry', 0)
    
    # Try exact match
    matched = False
    if key in close_lookup:
        for t in close_lookup[key]:
            if entry_price and abs(t.get('entry', 0) - entry_price) < 0.5:
                pnl = t.get('pnl', 0)
                if e['jev_vote'] == 'WAIT':
                    all_wait_pnl.append((pnl, e['date'], e['stock'], e['strategy']))
                else:
                    all_agree_pnl.append((pnl, e['date'], e['stock'], e['strategy']))
                matched = True
                break
    
    if not matched and key in recent_lookup:
        # Use most recent trade for this stock+strategy
        t = recent_lookup[key]
        pnl = t.get('pnl', 0)
        if e['jev_vote'] == 'WAIT':
            all_wait_pnl.append((pnl, e['date'], e['stock'], e['strategy']))
        else:
            all_agree_pnl.append((pnl, e['date'], e['stock'], e['strategy']))

print(f"\n=== Expanded matching ===")
print(f"AGREE matched: {len(all_agree_pnl)}")
print(f"WAIT matched: {len(all_wait_pnl)}")
print(f"Total: {len(all_agree_pnl) + len(all_wait_pnl)} / {len(jev_log)}")

agree_total = sum(p[0] for p in all_agree_pnl)
wait_total = sum(p[0] for p in all_wait_pnl)
agree_wins = sum(1 for p in all_agree_pnl if p[0] > 0)
wait_wins = sum(1 for p in all_wait_pnl if p[0] > 0)

print(f"\nAGREE: {len(all_agree_pnl)} trades, total P&L={agree_total:.2f}, WR={agree_wins/len(all_agree_pnl)*100:.1f}%")
print(f"WAIT: {len(all_wait_pnl)} trades, total P&L={wait_total:.2f}, WR={wait_wins/len(all_wait_pnl)*100:.1f}%")
print(f"Combined: total P&L={agree_total+wait_total:.2f}")

# Today
today = [e for e in jev_log if e['date'] == '2026-10-22']
today_agree = []
for e in today:
    key = (e['stock'], e['strategy'])
    if key in close_lookup:
        for t in close_lookup[key]:
            entry_price = e.get('entry', 0)
            if entry_price and abs(t.get('entry', 0) - entry_price) < 0.5:
                today_agree.append(t.get('pnl', 0))
                break

print(f"\nToday matched: {len(today_agree)}/{len(today)}")
if today_agree:
    print(f"Today P&L: {sum(today_agree):.2f}")
    wins = sum(1 for p in today_agree if p > 0)
    print(f"Today WR: {wins}/{len(today_agree)} ({wins/len(today_agree)*100:.1f}%)")
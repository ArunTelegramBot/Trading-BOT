import json

with open('/home/ubuntu/Trading-BOT/trading/paper_trading/jev_log.json') as f:
    jev_log = json.load(f)
with open('/home/ubuntu/Trading-BOT/trading/paper_trading/state.json') as f:
    state = json.load(f)

closed = state.get('closed_trades', [])

# Today's entries
today_jev = [e for e in jev_log if e['date'] == '2026-10-22']

# Closed trades today
today_closed = [t for t in closed if t.get('exit_date') == '2026-10-22']

print(f"Today Jev entries: {len(today_jev)}")
print(f"Closed trades today: {len(today_closed)}")

# Sample fields
if today_closed:
    print(f"Closed trade keys: {list(today_closed[0].keys())}")
    
# Match by stock+strategy
matched_pnl = []
jev_with_entry = [e for e in today_jev if 'entry' in e]
print(f"Jev entries with entry price: {len(jev_with_entry)}")

# Build lookup for closed trades
close_lookup = {}
for t in today_closed:
    key = (t['stock'], t['strategy'])
    if key not in close_lookup:
        close_lookup[key] = []
    close_lookup[key].append(t)

# Match Jev entries to closed trades by stock+strategy
matched = 0
for e in today_jev:
    key = (e['stock'], e['strategy'])
    if key in close_lookup:
        matched += 1

print(f"Matched by stock+strategy: {matched}/{len(today_jev)}")

# If no match, check if entry dates differ - Jev entries may be for new signals
# that haven't closed yet. Let's see
entry_dates = set(e['date'] for e in jev_log)
print(f"Jev dates: {sorted(entry_dates)}")

# Check exit dates in closed trades
exit_dates = set()
for t in closed:
    d = t.get('exit_date')
    if d:
        exit_dates.add(d)
print(f"Exit dates in closed: {sorted(exit_dates)}")

# For today's Jev entries that DO have 'entry' price, find the matching closed trade
# by exact entry price match for stock+strategy
exact_matched = 0
for e in today_jev:
    if 'entry' not in e:
        continue
    key = (e['stock'], e['strategy'])
    if key in close_lookup:
        for t in close_lookup[key]:
            if abs(t.get('entry',0) - e['entry']) < 0.5:
                exact_matched += 1
                break

print(f"Exact match by entry price: {exact_matched}")

# Let's aggregate P&L by strategy from state.json instead
# The state has per-strategy P&L - but that's overall not per-day
# Let's just count the closed trades that are open positions matching entries

# Broader match: check all closed trades for stock+strategy regardless of date
all_close_lookup = {}
for t in closed:
    key = (t.get('stock',''), t.get('strategy',''))
    if key not in all_close_lookup:
        all_close_lookup[key] = []
    all_close_lookup[key].append(t)

# For Jev entries with entry price, try to find the closest matching closed trade
matched_all = 0
pnl_agree = []
pnl_disagree = []
pnl_wait = []

for e in today_jev:
    key = (e['stock'], e['strategy'])
    if key in all_close_lookup:
        best = None
        best_diff = 99999
        for t in all_close_lookup[key]:
            entry_diff = abs(t.get('entry',0) - e.get('entry',0))
            if entry_diff < best_diff:
                best_diff = entry_diff
                best = t
        if best and best_diff < 1.0:
            matched_all += 1
            pnl = best.get('pnl', 0)
            if e['jev_vote'] == 'WAIT':
                pnl_wait.append(pnl)
            elif e['agree']:
                pnl_agree.append(pnl)
            else:
                pnl_disagree.append(pnl)

print(f"\nMatched with closed trades: {matched_all}")
print(f"AGREE trades: {len(pnl_agree)}, total PnL: {sum(pnl_agree):.2f}")
if pnl_agree:
    wins = sum(1 for p in pnl_agree if p > 0)
    print(f"  Win rate: {wins}/{len(pnl_agree)} ({wins/len(pnl_agree)*100:.1f}%)")
print(f"DISAGREE trades: {len(pnl_disagree)}, total PnL: {sum(pnl_disagree):.2f}")
print(f"WAIT trades: {len(pnl_wait)}, total PnL: {sum(pnl_wait):.2f}")

# Running totals
all_pnl_agree = []
all_pnl_disagree = []
all_pnl_wait = []

all_close_lookup2 = {}
for t in closed:
    key = (t.get('stock',''), t.get('strategy',''))
    if key not in all_close_lookup2:
        all_close_lookup2[key] = []
    all_close_lookup2[key].append(t)

matched_all2 = 0
for e in jev_log:
    key = (e['stock'], e['strategy'])
    if key in all_close_lookup2:
        best = None
        best_diff = 99999
        for t in all_close_lookup2[key]:
            entry_diff = abs(t.get('entry',0) - e.get('entry',0))
            if entry_diff < best_diff:
                best_diff = entry_diff
                best = t
        if best and best_diff < 1.0:
            matched_all2 += 1
            pnl = best.get('pnl', 0)
            if e['jev_vote'] == 'WAIT':
                all_pnl_wait.append(pnl)
            elif e['agree']:
                all_pnl_agree.append(pnl)
            else:
                all_pnl_disagree.append(pnl)

print(f"\n=== RUNNING TOTALS (all dates) ===")
print(f"Total matched: {matched_all2}")
print(f"Total cost: {sum(e['cost'] for e in jev_log):.4f}")
print(f"Cumulative votes: {len(jev_log)}")

all_agree_pnl = sum(all_pnl_agree)
all_disagree_pnl = sum(all_pnl_disagree)
all_wait_pnl = sum(all_pnl_wait)

print(f"AGREE: {len(all_pnl_agree)} trades, total PnL={all_agree_pnl:.2f}", end="")
if all_pnl_agree:
    wins = sum(1 for p in all_pnl_agree if p > 0)
    print(f", win rate={wins/len(all_pnl_agree)*100:.1f}%", end="")
print()

print(f"DISAGREE: {len(all_pnl_disagree)} trades, total PnL={all_disagree_pnl:.2f}", end="")
if all_pnl_disagree:
    wins = sum(1 for p in all_pnl_disagree if p > 0)
    print(f", win rate={wins/len(all_pnl_disagree)*100:.1f}%", end="")
print()

print(f"WAIT: {len(all_pnl_wait)} trades, total PnL={all_wait_pnl:.2f}", end="")
if all_pnl_wait:
    wins = sum(1 for p in all_pnl_wait if p > 0)
    print(f", win rate={wins/len(all_pnl_wait)*100:.1f}%", end="")
print()

print(f"\nFilter simulation (all time):")
print(f"  Avoided PnL by disagreeing: {all_disagree_pnl:.2f}")
if all_pnl_disagree:
    wins = sum(1 for p in all_pnl_disagree if p > 0)
    print(f"  Win rate on skipped trades: {wins}/{len(all_pnl_disagree)} ({wins/len(all_pnl_disagree)*100:.1f}%)")

print(f"\nToday filter simulation:")
print(f"  Avoided PnL: {sum(pnl_disagree):.2f}")
if pnl_disagree:
    wins = sum(1 for p in pnl_disagree if p > 0)
    print(f"  Win rate on skipped trades: {wins}/{len(pnl_disagree)} ({wins/len(pnl_disagree)*100:.1f}%)")
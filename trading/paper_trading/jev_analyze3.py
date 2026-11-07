import json

with open('/home/ubuntu/Trading-BOT/trading/paper_trading/jev_log.json') as f:
    jev_log = json.load(f)
with open('/home/ubuntu/Trading-BOT/trading/paper_trading/state.json') as f:
    state = json.load(f)

closed = state.get('closed_trades', [])

# Build close trade lookup by stock+strategy
close_lookup = {}
for t in closed:
    key = (t.get('stock',''), t.get('strategy',''))
    if key not in close_lookup:
        close_lookup[key] = []
    close_lookup[key].append(t)

def match_pnl(jev_entry):
    """Find matching closed trade by stock+strategy+entry price"""
    key = (jev_entry['stock'], jev_entry['strategy'])
    if key not in close_lookup:
        return None
    # Try exact entry price match first
    entry = jev_entry.get('entry', 0)
    for t in close_lookup[key]:
        if abs(t.get('entry', 0) - entry) < 0.5:
            return t.get('pnl', 0)
    return None

# === TODAY (2026-10-22) ===
today = [e for e in jev_log if e['date'] == '2026-10-22']
today_agree_pnl = []
today_disagree_pnl = []
today_wait_pnl = []

# Compute actual agreement
agree_map = {'BUY': 'LONG', 'SELL': 'SHORT'}
for e in today:
    pnl = match_pnl(e)
    if pnl is None:
        continue
    if e['jev_vote'] == 'WAIT':
        today_wait_pnl.append(pnl)
    elif e['jev_vote'] == agree_map.get(e['signal']):
        today_agree_pnl.append(pnl)
    else:
        today_disagree_pnl.append(pnl)

print("=== TODAY (2026-10-22) ===")
votes = {}
for e in today:
    v = e['jev_vote']
    votes[v] = votes.get(v, 0) + 1
print(f"Votes: LONG={votes.get('LONG',0)} SHORT={votes.get('SHORT',0)} WAIT={votes.get('WAIT',0)}")

agree_ct = sum(1 for e in today if e['jev_vote'] != 'WAIT' and e['jev_vote'] == agree_map.get(e['signal']))
print(f"Agreement rate: {agree_ct}/{len(today)} ({agree_ct/len(today)*100:.1f}%)")

print(f"\nAGREE trades: {len(today_agree_pnl)}")
if today_agree_pnl:
    print(f"  Total P&L: {sum(today_agree_pnl):.2f}")
    wins = sum(1 for p in today_agree_pnl if p > 0)
    print(f"  Win rate: {wins}/{len(today_agree_pnl)} ({wins/len(today_agree_pnl)*100:.1f}%)")

print(f"DISAGREE trades: {len(today_disagree_pnl)}")
if today_disagree_pnl:
    print(f"  Total P&L: {sum(today_disagree_pnl):.2f}")

print(f"WAIT trades: {len(today_wait_pnl)}")
if today_wait_pnl:
    print(f"  Total P&L: {sum(today_wait_pnl):.2f}")
    wins = sum(1 for p in today_wait_pnl if p > 0)
    print(f"  Win rate: {wins}/{len(today_wait_pnl)} ({wins/len(today_wait_pnl)*100:.1f}%)")

# Cost
today_cost = sum(e['cost'] for e in today)
print(f"\nToday cost: ${today_cost:.4f}")

# Filter simulation
if today_disagree_pnl:
    print(f"Filter: avoided {sum(today_disagree_pnl):.2f} by skipping disagree trades")
    wins = sum(1 for p in today_disagree_pnl if p > 0)
    print(f"  Skipped trades win rate: {wins}/{len(today_disagree_pnl)} ({wins/len(today_disagree_pnl)*100:.1f}%)")

# === RUNNING TOTALS ===
all_agree_pnl = []
all_disagree_pnl = []
all_wait_pnl = []

for e in jev_log:
    pnl = match_pnl(e)
    if pnl is None:
        continue
    if e['jev_vote'] == 'WAIT':
        all_wait_pnl.append(pnl)
    elif e['jev_vote'] == agree_map.get(e['signal']):
        all_agree_pnl.append(pnl)
    else:
        all_disagree_pnl.append(pnl)

print("\n=== RUNNING TOTALS (ALL DATES) ===")
print(f"Total votes: {len(jev_log)}")
total_cost = sum(e['cost'] for e in jev_log)
print(f"Total cost: ${total_cost:.4f}")

print(f"\nAGREE trades: {len(all_agree_pnl)}")
if all_agree_pnl:
    print(f"  Total P&L: {sum(all_agree_pnl):.2f}")
    wins = sum(1 for p in all_agree_pnl if p > 0)
    print(f"  Win rate: {wins}/{len(all_agree_pnl)} ({wins/len(all_agree_pnl)*100:.1f}%)")

print(f"DISAGREE trades: {len(all_disagree_pnl)}")
if all_disagree_pnl:
    print(f"  Total P&L: {sum(all_disagree_pnl):.2f}")

print(f"WAIT trades: {len(all_wait_pnl)}")
if all_wait_pnl:
    print(f"  Total P&L: {sum(all_wait_pnl):.2f}")
    wins = sum(1 for p in all_wait_pnl if p > 0)
    print(f"  Win rate: {wins}/{len(all_wait_pnl)} ({wins/len(all_wait_pnl)*100:.1f}%)")

if all_disagree_pnl:
    print(f"\nFilter all-time: avoided {sum(all_disagree_pnl):.2f} by skipping disagree trades")
    wins = sum(1 for p in all_disagree_pnl if p > 0)
    print(f"  Skipped trades win rate: {wins}/{len(all_disagree_pnl)}")

# Also calculate: what if we skipped all NON-WAIT trades where Jev disagreed
# Since there are 0 disagree, the filter only matters for WAIT trades
print(f"\nNote: Jev never voted against the signal (0 disagree votes all-time)")
print(f"All 'difference' is through WAIT votes ({len(all_wait_pnl)} matched trades)")

# Summary of WAIT vs AGREE win rates
if all_agree_pnl and all_wait_pnl:
    a_wins = sum(1 for p in all_agree_pnl if p > 0)
    w_wins = sum(1 for p in all_wait_pnl if p > 0)
    print(f"\nAGREE win rate: {a_wins}/{len(all_agree_pnl)} ({a_wins/len(all_agree_pnl)*100:.1f}%)")
    print(f"WAIT win rate: {w_wins}/{len(all_wait_pnl)} ({w_wins/len(all_wait_pnl)*100:.1f}%)")
    print(f"Difference: {w_wins/len(all_wait_pnl)*100 - a_wins/len(all_agree_pnl)*100:+.1f}pp")
import json

with open('/home/ubuntu/Trading-BOT/trading/paper_trading/jev_log.json') as f:
    jev_log = json.load(f)

# Check agree=false entries
disagree = [e for e in jev_log if not e.get('agree', True)]
print(f"Total entries with agree=false: {len(disagree)}")
if disagree:
    # Sample first 10
    for d in disagree[:10]:
        print(f"  {d['date']} {d['time']} {d['stock']} {d['strategy']} signal={d['signal']} vote={d['jev_vote']} agree={d.get('agree')}")
    print("...")
    
    # By date
    from collections import Counter
    dc = Counter(e['date'] for e in disagree)
    for d in sorted(dc):
        total = sum(1 for e in jev_log if e['date'] == d)
        print(f"  {d}: {dc[d]}/{total} disagree")

# Compute actual agree based on signal-vote mapping
print("\n=== Computing actual agreement ===")
agree_signal_map = {'BUY': 'LONG', 'SELL': 'SHORT'}
computed_agree = 0
computed_disagree = 0
computed_wait = 0
for e in jev_log:
    expected = agree_signal_map.get(e['signal'])
    if e['jev_vote'] == 'WAIT':
        computed_wait += 1
    elif e['jev_vote'] == expected:
        computed_agree += 1
    else:
        computed_disagree += 1

print(f"Computed agree (signal matches vote): {computed_agree}")
print(f"Computed disagree (signal != vote, non-WAIT): {computed_disagree}")
print(f"WAIT votes: {computed_wait}")
print(f"Total: {computed_agree + computed_disagree + computed_wait}")

# Today
today = [e for e in jev_log if e['date'] == '2026-10-22']
today_agree = 0
today_disagree = 0
today_wait = 0
for e in today:
    expected = agree_signal_map.get(e['signal'])
    if e['jev_vote'] == 'WAIT':
        today_wait += 1
    elif e['jev_vote'] == expected:
        today_agree += 1
    else:
        today_disagree += 1
print(f"\nToday (2026-10-22):")
print(f"  Agree: {today_agree}, Disagree: {today_disagree}, WAIT: {today_wait}")
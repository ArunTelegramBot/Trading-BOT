#!/bin/bash
# NSE Scanner wrapper — exits silently outside market hours
set -e

# Market hours check: Mon-Fri, 9:15-15:30 IST
hour=$(TZ='Asia/Kolkata' date +%H%M)
dow=$(TZ='Asia/Kolkata' date +%u)

if [ "$dow" -gt 5 ]; then exit 0; fi          # Weekend
if [ "$hour" -lt 0915 ] || [ "$hour" -ge 1530 ]; then exit 0; fi  # Before open or after close

PYTHON=/home/ubuntu/.hermes/tools/python-3.14.7+202****0901-linux-x64/bin/python3
SCRIPT=/home/ubuntu/Trading-BOT/trading/signals/intraday_scanner.py

output=$($PYTHON $SCRIPT 2>/dev/null)

json=$(echo "$output" | awk '/JSON_OUTPUT/{flag=1; next} /END_JSON/{flag=0} flag')

if [ -z "$json" ] || [ "$json" = "[]" ]; then
    exit 0
fi

echo "$json" | $PYTHON -c '
import sys, json
signals = json.load(sys.stdin)
for s in signals:
    icon = "\U0001F7E2" if s["signal"]=="BUY" else "\U0001F534"
    print(f"{icon} {s["signal"]} {s["stock"]} @ \u20B9{s["price"]}")
    print(f"   Time: {s["date"]} {s["time"]} IST | Trend: {s["trend"]}")
print(f"— NSE Scanner ({len(signals)} signal(s))")
' 2>/dev/null
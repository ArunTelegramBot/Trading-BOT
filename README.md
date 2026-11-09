# Indian Paper Trading Research Bot

This package runs a paper-only strategy research loop for 50 rule-based strategies.

It provides:

- Indian market-hours guard in `Asia/Kolkata`
- 50 deterministic strategy variants
- simulated paper broker with capital and risk limits
- daily JSON observations for Hermes
- Excel performance workbook updates
- 16:00 IST daily report generation
- optional Telegram reporting and approval messages
- optional Hermes HTTP handoff
- compact searchable knowledge base for the uploaded book study notes
- Docker/VPS files and tests

## Safety

The default mode is `paper`. No live order adapter is included. The bot stops at the approval boundary when Hermes proposes a rule change. Do not enable live execution without implementing and reviewing a broker-specific adapter and compliance controls.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m bot demo
python -m bot report
python -m bot hermes
```

The demo creates sample market data, runs the 50 strategies, writes observations, updates the workbook, and creates a Hermes review file.

`python -m bot schedule` is the unattended loop. It runs the configured daily batch at the configured report time and sends the review to Hermes when `HERMES_URL` is set. A real-time market feed must be supplied by replacing `bot/data_provider.py`; the included CSV provider is intentionally safe and deterministic.

## VPS

```bash
docker compose up -d --build
```

The scheduler runs the paper loop during the configured session and generates the report at 16:00 IST. Set Telegram and Hermes variables in `.env` to enable those integrations.

## Inputs

The default CSV data source is `data/market_data.csv` with columns:

```text
timestamp,symbol,open,high,low,close,volume
```

Replace `bot/data_provider.py` with the approved broker/data-provider implementation when ready.

## Book knowledge base

The `knowledge` directory converts the uploaded study corpus into compact chunks, candidate rule cards, and a SQLite full-text index. Build it with:

```bash
python knowledge/build_knowledge_base.py /path/to/Unsaved\ Document\ 1 --output data/knowledge
python -m knowledge.retrieve "low volume trend filter drawdown"
```

Hermes should call `hermes_context(...)` and receive only the relevant chunks. The extracted rules are research candidates and require backtesting and approval.

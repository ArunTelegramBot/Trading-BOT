# Migration Restore Guide — AMD → Ampere ARM

Backup created: Nov 7, 2026
From: AMD VM.Standard.E2.1.Micro
To: Ampere ARM (12GB Free Tier)

---

## 1. Clone all repos

```bash
cd ~/
git clone git@github.com:ArunTelegramBot/Trading-BOT.git
git clone git@github.com:ArunTelegramBot/Website-devlopment.git trading-kb
git clone https://github.com/ArunTelegramBot/AsukaDXbot.git
git clone https://github.com/ArunTelegramBot/ShreyaPrivateBot.git
git clone https://github.com/ArunTelegramBot/CarissaDanielleBOT.git
git clone https://github.com/ArunTelegramBot/CherieMaferbot.git
git clone https://github.com/ArunTelegramBot/MarinaSmithbot.git
git clone https://github.com/ArunTelegramBot/Valentinagomezzbot.git
git clone https://github.com/ArunTelegramBot/voice-changer-bot.git
```

---

## 2. System deps

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip git curl nodejs npm
```

---

## 3. SSH key for GitHub

```bash
ssh-keygen -t ed25519 -C "hermes-vps" -f ~/.ssh/github_hermes -N ""
cat >> ~/.ssh/config << 'EOF'
Host github.com
  IdentityFile ~/.ssh/github_hermes
  StrictHostKeyChecking no
EOF
cat ~/.ssh/github_hermes.pub
# → Add to GitHub: https://github.com/settings/keys (ArunTelegramBot account)
```

---

## 4. Git config

```bash
git config --global user.email "arun887229@gmail.com"
git config --global user.name "ArunTelegramBot"
```

---

## 5. Set up Telegram bots

For each bot dir:

```bash
cd /home/ubuntu/<RepoName>
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in each bot dir with:

| Bot | Token | Port | VIP Group | Secret |
|---|---|---|---|---|
| AsukaDXbot | 8519455322:*** | 8081 | -1003497234061 | asuka@2026 |
| Valentinagomezzbot | 7985767358:*** | 8082 | -5186113202 | valentina@2026 |
| MarinaSmithbot | 8230382899:*** | 8083 | -5238001769 | marina@2026 |
| CarissaDanielleBOT | 8620283321:*** | 8084 | -5248525738 | carissa@2026 |
| CherieMaferbot | 8617737136:*** | 8085 | -5162404653 | cherie@2026 |

All share: `ADMIN_GROUP_ID=-1002594045216`, `VIP_LINK=https://t.me/+...`

ShreyaPrivateBot + voice-changer-bot: ask user for env vars.

### Start via PM2

```bash
npm install -g pm2
pm2 start start_bot.sh --name asuka-bot --cwd /home/ubuntu/AsukaDXbot
pm2 start start_bot.sh --name shreya-bot --cwd /home/ubuntu/ShreyaPrivateBot
pm2 start start_bot.sh --name carissa-bot --cwd /home/ubuntu/CarissaDanielleBOT
pm2 start start_bot.sh --name cherie-bot --cwd /home/ubuntu/CherieMaferbot
pm2 start start_bot.sh --name marina-bot --cwd /home/ubuntu/MarinaSmithbot
pm2 start start_bot.sh --name valentina-bot --cwd /home/ubuntu/Valentinagomezzbot
pm2 save && pm2 startup
```

---

## 6. Trading Engine

```bash
cd /home/ubuntu/Trading-BOT/trading/paper_trading
python3 -m venv venv
source venv/bin/activate
pip install yfinance pandas openpyxl python-telegram-bot aiohttp
```

Copy live state from block volume (if attached):

```bash
# Source: old block volume mounted at /mnt/block-volume or copied via rsync
cp /mnt/block-volume/Trading-BOT/trading/paper_trading/state.json ./
cp /mnt/block-volume/Trading-BOT/trading/paper_trading/*.xlsx ./
cp /mnt/block-volume/Trading-BOT/trading/paper_trading/jev_log.json ./
cp /mnt/block-volume/Trading-BOT/trading/paper_trading/news.json ./
```

---

## 7. Cron

```bash
crontab -e
# Add:
0 4-10 * * 1-5 bash /home/ubuntu/Trading-BOT/trading/signals/run_scanner.sh
```

Engine 10-min run + daily audit at 8:30am IST = managed by Hermes internal cron.

---

## 8. Restore checklist

- [ ] All repos cloned
- [ ] SSH key added to GitHub
- [ ] Python venvs + deps installed
- [ ] .env files created (6 bots)
- [ ] PM2 running — all bots online
- [ ] Engine deps installed
- [ ] Live state copied from block volume
- [ ] Cron for scanner added
- [ ] DNS / public IP updated
- [ ] Old instance stopped after confirmation
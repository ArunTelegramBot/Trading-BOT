#!/bin/bash
set -e

# Full restore script for new Ampere ARM instance
# Run from /home/ubuntu/Trading-BOT on the new instance

echo "===== FULL RESTORE - Nov 2026 ====="
cd /home/ubuntu

# 1. System deps
echo "[1/8] Installing system deps..."
sudo apt update -y && sudo apt install -y python3-venv python3-pip git curl nodejs npm

# 2. Git config (update email if different)
git config --global user.email "arun887229@gmail.com"
git config --global user.name "ArunTelegramBot"

# 3. Clone all repos (uses HTTPS - will prompt for credentials once)
echo "[2/8] Cloning all repos..."
REPOS="Trading-BOT Website-devlopment AsukaDXbot ShreyaPrivateBot CarissaDanielleBOT CherieMaferbot MarinaSmithbot Valentinagomezzbot voice-changer-bot"
for repo in $REPOS; do
    if [ ! -d "$repo" ]; then
        echo "Cloning $repo..."
        git clone https://github.com/ArunTelegramBot/$repo.git
    else
        echo "$repo already exists, pulling..."
        cd $repo && git pull && cd ..
    fi
done

# 4. Set up Python venvs + deps for each bot
echo "[3/8] Setting up Python environments..."
for repo in AsukaDXbot ShreyaPrivateBot CarissaDanielleBOT CherieMaferbot MarinaSmithbot Valentinagomezzbot; do
    if [ -f "$repo/requirements.txt" ]; then
        echo "Setting up $repo..."
        cd $repo
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        deactivate
        cd ..
    fi
done

# 5. Trading engine deps
echo "[4/8] Setting up trading engine..."
cd Trading-BOT/trading/paper_trading
python3 -m venv venv
source venv/bin/activate
pip install yfinance pandas openpyxl python-telegram-bot aiohttp
deactivate
cd /home/ubuntu

# 6. Create .env files from backup
echo "[5/8] Restoring .env files..."
# Copy ENV_BACKUP from old instance first
if [ -f "ENV_BACKUP_NOV2026.txt" ]; then
    echo "Found ENV_BACKUP file"
elif [ -f "Trading-BOT/ENV_BACKUP_NOV2026.txt" ]; then
    echo "Found ENV_BACKUP in Trading-BOT"
elif [ -f "Trading-BOT/trading/ENV_BACKUP_NOV2026.txt" ]; then
    echo "Found ENV_BACKUP in Trading-BOT/trading"
else
    echo ""
    echo "⚠️  ENV_BACKUP file not found."
    echo "   Copy it from the OLD instance:"
    echo "   scp ubuntu@<OLD_IP>:~/Trading-BOT/ENV_BACKUP_NOV2026.txt ./"
    echo "   Then re-run this script."
fi

# Parse backup and recreate .env files (python based)
if [ -f "ENV_BACKUP_NOV2026.txt" ] || [ -f "Trading-BOT/trading/ENV_BACKUP_NOV2026.txt" ]; then
    python3 -c "
import os, re
bp = 'ENV_BACKUP_NOV2026.txt'
if not os.path.exists(bp):
    bp = 'Trading-BOT/trading/ENV_BACKUP_NOV2026.txt'
with open(bp) as f:
    content = f.read()
sections = content.split('FILE: ')
for s in sections[1:]:
    path = s.split('\n')[0].strip()
    body_end = s.find('\n============================================')
    body = s[body_end+1:].strip() if body_end > 0 else ''
    # Find the actual env content - it's between the header line and next section
    lines = s.split('\n')
    env_lines = []
    in_env = False
    for line in lines:
        if '============================================' in line:
            if in_env:
                break
            in_env = True
            continue
        if in_env and line.strip():
            env_lines.append(line)
    env_content = '\n'.join(env_lines)
    if env_content:
        with open(path, 'w') as ef:
            ef.write(env_content)
        print(f'Created {path}')
"
fi

# 7. Install PM2 and start bots
echo "[6/8] Starting PM2 bots..."
npm install -g pm2 2>/dev/null

pm2 delete all 2>/dev/null || true
pm2 start start_bot.sh --name asuka-bot --cwd /home/ubuntu/AsukaDXbot 2>/dev/null || echo "No shreya bot" 
pm2 start start_bot.sh --name shreya-bot --cwd /home/ubuntu/ShreyaPrivateBot 2>/dev/null || echo "No asuka bot"
pm2 start start_bot.sh --name carissa-bot --cwd /home/ubuntu/CarissaDanielleBOT 2>/dev/null || echo "No carissa bot"
pm2 start start_bot.sh --name cherie-bot --cwd /home/ubuntu/CherieMaferbot 2>/dev/null || echo "No cherie bot"
pm2 start start_bot.sh --name marina-bot --cwd /home/ubuntu/MarinaSmithbot 2>/dev/null || echo "No marina bot"
pm2 start start_bot.sh --name valentina-bot --cwd /home/ubuntu/Valentinagomezzbot 2>/dev/null || echo "No valentina bot"
pm2 save
pm2 startup 2>/dev/null || true

# 8. Setup cron
echo "[7/8] Setting up cron..."
(crontab -l 2>/dev/null; echo "# NSE Scanner — every hour during market hours (4-10 UTC = 9:30-15:30 IST)") | crontab -
(crontab -l 2>/dev/null; echo "0 4-10 * * 1-5 bash /home/ubuntu/Trading-BOT/trading/signals/run_scanner.sh") | crontab -

echo "[8/8] Done!"
echo ""
echo "===== RESTORE COMPLETE ====="
echo "Bots: run 'pm2 list' to check status"
echo "Trading: run 'cd ~/Trading-BOT/trading/paper_trading && source venv/bin/activate'"
echo "Need env files? Copy from old: scp ubuntu@<OLD_IP>:~/Trading-BOT/ENV_BACKUP_NOV2026.txt ./"
echo "Then re-run this script or manually cp to each bot dir"
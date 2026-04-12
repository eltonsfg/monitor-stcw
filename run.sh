#!/bin/bash
# Monitor STCW — runner principal
# Corre o monitor e faz push dos resultados para GitHub
set -e

echo "=== $(date -u '+%Y-%m-%d %H:%M UTC') ==="

# Configurar git com token de acesso
if [ -n "$GITHUB_TOKEN" ]; then
    git config user.name  "monitor-stcw-bot"
    git config user.email "monitor-bot@stcw.pt"
    git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/eltonsfg/monitor-stcw.git"
    # Sincronizar com o remoto antes de escrever
    git fetch origin main --quiet
    git reset --hard origin/main --quiet
fi

# Executar o monitor
python -m scraper.main

# Guardar resultados no GitHub
if [ -n "$GITHUB_TOKEN" ]; then
    git add data/resultados.csv data/log.csv 2>/dev/null || true
    if git diff --cached --quiet; then
        echo "[git] Sem novas alterações para guardar"
    else
        git commit -m "chore: resultados $(date -u +%Y-%m-%d) [Fly.io/GRU]"
        git push origin main
        echo "[git] Resultados guardados no GitHub"
    fi
fi

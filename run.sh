#!/bin/bash
# Monitor STCW — runner para Fly.io/container
# Clona o repo, corre o monitor e faz push dos resultados
set -e

echo "=== $(date -u '+%Y-%m-%d %H:%M UTC') ==="

if [ -n "$GITHUB_TOKEN" ]; then
    # Clonar repo para directório temporário (container não tem .git)
    WORK_DIR="/tmp/monitor-$(date +%s)"
    echo "[git] A clonar repositório..."
    git clone --depth 1 \
        "https://x-access-token:${GITHUB_TOKEN}@github.com/eltonsfg/monitor-stcw.git" \
        "$WORK_DIR" --quiet
    cd "$WORK_DIR"
    git config user.name  "monitor-stcw-bot"
    git config user.email "monitor-bot@stcw.pt"
else
    # Sem token — correr a partir do /app (modo local/debug)
    cd /app
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
        git push origin main --quiet
        echo "[git] Resultados guardados no GitHub"
    fi
    # Limpar directório temporário
    rm -rf "$WORK_DIR"
fi

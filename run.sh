#!/bin/bash
# Script principal para Railway (São Paulo)
# Corre o monitor e faz push dos resultados para GitHub
set -e

# Configurar git com token de acesso (GITHUB_TOKEN injectado pelo Railway)
if [ -n "$GITHUB_TOKEN" ]; then
    git config user.name  "railway-bot"
    git config user.email "railway-bot@stcw.pt"
    git remote set-url origin "https://x-access-token:${GITHUB_TOKEN}@github.com/eltonsfg/monitor-stcw.git"
    # Garantir que estamos actualizados
    git pull --rebase --autostash origin main 2>/dev/null || true
fi

# Executar o monitor
python -m scraper.main

# Guardar resultados no GitHub
if [ -n "$GITHUB_TOKEN" ]; then
    git add data/resultados.csv data/log.csv 2>/dev/null || true
    git diff --cached --quiet || git commit -m "chore: resultados $(date -u +%Y-%m-%d) [Railway/BR]"
    git push origin main 2>/dev/null || echo "[git push] sem alterações para enviar"
fi

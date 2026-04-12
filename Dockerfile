FROM python:3.11-slim

WORKDIR /app

# git (para push de resultados) + cron
RUN apt-get update && apt-get install -y cron git && rm -rf /var/lib/apt/lists/*

# Dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código
COPY . .
RUN chmod +x run.sh

# Cron job: 08:00 UTC = 05:00 Brasília
COPY crontab /etc/cron.d/monitor-stcw
RUN chmod 0644 /etc/cron.d/monitor-stcw && crontab /etc/cron.d/monitor-stcw

# Log visível nos logs do Fly
RUN touch /var/log/monitor.log

# Iniciar cron + seguir log (mantém container vivo)
CMD cron && tail -f /var/log/monitor.log

# Monitor STCW — Acordo Marítimo Bilateral Brasil-Portugal

Monitorização diária automática do **Diário Oficial da União (Brasil)** e do
**Diário da República (Portugal)** para publicações relacionadas com o acordo
de reconhecimento mútuo de certificações marítimas STCW.

## O que monitoriza

| Fonte | País | Método |
|---|---|---|
| Diário Oficial da União | 🇧🇷 Brasil | Pesquisa web (Playwright) |
| DRE Série I | 🇵🇹 Portugal | RSS feed |
| DRE Série II | 🇵🇹 Portugal | RSS feed |

**Autoridades acompanhadas:** DPC (Diretoria de Portos e Costas) · DGRM (Direção-Geral de Recursos Marítimos)

## Configuração — 3 passos

### 1. Clonar e instalar

```bash
git clone https://github.com/SEU_USUARIO/monitor-stcw.git
cd monitor-stcw
pip install -r requirements.txt
playwright install chromium
```

### 2. Configurar email

```bash
cp .env.example .env
# Edita .env com o teu email e app password do Gmail
```

**Como obter o App Password do Gmail:**
1. Vai a [myaccount.google.com](https://myaccount.google.com) → Segurança
2. Activa "Verificação em duas etapas" (se ainda não tiveres)
3. Pesquisa "App Passwords" → cria para "Mail"
4. Copia os 16 caracteres para `EMAIL_PASSWORD` no `.env`

### 3. Testar localmente

```bash
python -m scraper.main
```

Deverás ver output como:
```
============================================================
  Monitor STCW — 2026-04-06 08:00 UTC
============================================================

[1/2] Pesquisando DOU (Brasil)...
  [DOU] Total relevantes: 0

[2/2] Pesquisando DRE (Portugal)...
  [DRE Série I] 12 publicações → 0 relevantes
  [DRE Série II] 89 publicações → 0 relevantes

Total encontrado: 0 publicação(ões) relevante(s)
— Sem novas publicações hoje
```

## Activar no GitHub Actions (execução diária gratuita)

### 1. Criar repositório no GitHub

```bash
git init
git add .
git commit -m "feat: monitor STCW inicial"
git remote add origin https://github.com/SEU_USUARIO/monitor-stcw.git
git push -u origin main
```

### 2. Configurar Secrets no GitHub

Vai ao repositório → **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Valor |
|---|---|
| `EMAIL_FROM` | teu email Gmail |
| `EMAIL_PASSWORD` | app password (16 caracteres) |
| `EMAIL_TO` | email de destino dos alertas |

### 3. Activar o workflow

O workflow corre automaticamente todos os dias às **08:00 UTC**.

Para testar manualmente: **Actions → Monitor STCW → Run workflow**

## Ajustar palavras-chave

Edita `config.yaml` — secção `keywords`. Não precisas de tocar no código.

```yaml
keywords:
  primary:
    - "STCW"
    - "endosso de certificado"
    - "reconhecimento mútuo"
    # adiciona aqui mais termos
```

## Ficheiros de saída

| Ficheiro | Conteúdo |
|---|---|
| `data/resultados.csv` | Todas as publicações relevantes encontradas |
| `data/log.csv` | Log diário (incluindo dias sem resultados) |

## Estrutura do projecto

```
monitor-stcw/
├── config.yaml              ← configura aqui (keywords, email, fontes)
├── scraper/
│   ├── main.py              ← orquestrador principal
│   ├── filters.py           ← lógica de filtragem por keywords
│   └── sources/
│       ├── dou.py           ← scraper do DOU (Brasil)
│       └── dre.py           ← RSS do DRE (Portugal)
├── notifier/
│   └── email_alert.py       ← envio de alertas por email
├── storage/
│   └── csv_sync.py          ← persistência em CSV
├── data/
│   ├── resultados.csv       ← gerado automaticamente
│   └── log.csv              ← gerado automaticamente
└── .github/workflows/
    └── monitor.yml          ← GitHub Actions (cron diário)
```

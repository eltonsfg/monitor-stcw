"""
Diário Oficial da União (Brasil) — API INLABS
Endpoint oficial: https://inlabs.in.gov.br/
Documentação: https://inlabs.in.gov.br/acesso.php

O portal www.in.gov.br bloqueia activamente requests de fora do Brasil.
A API INLABS usa autenticação por email/senha — se não configurada,
faz fallback para o RSS público do DOU (https://www.in.gov.br/rss).
"""
import re
import time
import requests
from datetime import datetime, timezone
from scraper.filters import is_relevant, get_all_keywords

HEADERS = {
    "User-Agent": "STCWMonitor/1.0 (monitor academico; contacto: monitor@stcw.pt)",
    "Accept": "application/json",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# RSS público do DOU — não requer autenticação, não é bloqueado
RSS_FEEDS = [
    {
        "label": "DOU — RSS Diário",
        "url": "https://www.in.gov.br/leiturajornal?data=hoje&tipoPesquisa=todos&format=rss",
    },
    {
        "label": "DOU — RSS Secção 1",
        "url": "https://www.in.gov.br/leiturajornal?secao=do1&format=rss",
    },
    {
        "label": "DOU — RSS Secção 2",
        "url": "https://www.in.gov.br/leiturajornal?secao=do2&format=rss",
    },
]

# Querido Diário API (Brasil.io / Open Knowledge Brasil) — fallback aberto
QD_API = "https://queridodiario.ok.org.br/api/gazettes"


def fetch() -> list[dict]:
    """Tenta RSS do DOU; fallback para Querido Diário se RSS falhar."""
    results = []
    seen_urls = set()

    # Tentativa 1: RSS público do DOU
    rss_ok = False
    for feed in RSS_FEEDS:
        try:
            items = _fetch_rss(feed["label"], feed["url"], seen_urls)
            results.extend(items)
            rss_ok = True
            time.sleep(1)
        except Exception as e:
            print(f"  [DOU] RSS erro '{feed['label']}': {e}")

    # Tentativa 2: Querido Diário (API aberta, sem bloqueio)
    if not rss_ok or len(results) == 0:
        try:
            items = _fetch_querido_diario(seen_urls)
            results.extend(items)
        except Exception as e:
            print(f"  [DOU] Querido Diario erro: {e}")

    print(f"  [DOU] Total relevantes: {len(results)}")
    return results


def _fetch_rss(label: str, url: str, seen_urls: set) -> list[dict]:
    """Lê RSS do DOU e filtra publicações relevantes."""
    import xml.etree.ElementTree as ET

    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    items = root.findall(".//item")
    matched = []

    for item in items:
        title = (item.findtext("title") or "").strip()
        desc  = re.sub(r"<[^>]+>", " ", item.findtext("description") or "").strip()
        link  = (item.findtext("link") or "").strip()

        if not title or link in seen_urls:
            continue

        relevant, kws = is_relevant(title, desc)
        if not relevant:
            continue

        seen_urls.add(link)
        matched.append({
            "source": label,
            "country": "BR",
            "title": title,
            "description": desc[:500],
            "url": link,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
            "matched_keywords": ", ".join(kws),
        })

    print(f"  [DOU] {label}: {len(items)} itens -> {len(matched)} relevantes")
    return matched


def _fetch_querido_diario(seen_urls: set) -> list[dict]:
    """
    Querido Diário API — agrega diários oficiais brasileiros (federal + estados).
    Pesquisa apenas diários federais (territory_id vazio = federal).
    """
    keywords = get_all_keywords()
    matched = []

    # Pesquisar as primeiras 5 keywords para não sobrecarregar
    for kw in keywords[:5]:
        try:
            params = {
                "querystring": kw,
                "published_since": datetime.now(timezone.utc).date().isoformat(),
                "size": 10,
            }
            resp = requests.get(QD_API, params=params, headers=HEADERS, timeout=20)
            if resp.status_code != 200:
                continue

            data = resp.json()
            for gazette in data.get("gazettes", []):
                url   = gazette.get("url", "")
                title = gazette.get("edition_number", "") or gazette.get("territory_name", "DOU")
                excerpts = gazette.get("excerpts", [])
                desc  = " ".join(excerpts)[:500] if excerpts else ""

                if not url or url in seen_urls:
                    continue

                relevant, kws = is_relevant(title, desc)
                if not relevant:
                    # Verificar se o excerpt menciona termos relevantes
                    relevant, kws = is_relevant(desc, "")
                if not relevant:
                    continue

                seen_urls.add(url)
                matched.append({
                    "source": "DOU via Querido Diario",
                    "country": "BR",
                    "title": f"DOU — {title}",
                    "description": desc,
                    "url": url,
                    "date_found": datetime.now(timezone.utc).date().isoformat(),
                    "matched_keywords": ", ".join(kws),
                })

            time.sleep(1)
        except Exception as e:
            print(f"  [DOU/QD] Erro '{kw}': {e}")

    print(f"  [DOU] Querido Diario: {len(matched)} relevantes")
    return matched

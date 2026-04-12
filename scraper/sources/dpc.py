"""
DPC — Diretoria de Portos e Costas (Brasil)
Monitoriza portarias, normas e avisos em:
  https://www.dpc.mar.mil.br
"""
import re
import time
import warnings
import requests
import urllib3
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from scraper.filters import is_relevant

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; STCWMonitor/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

# Páginas a monitorizar na DPC (scraping directo — sem RSS)
PAGES = [
    {
        "label": "DPC — Portarias",
        "url": "https://www.dpc.mar.mil.br/pt-br/legislacao/portarias",
    },
    {
        "label": "DPC — Notícias",
        "url": "https://www.dpc.mar.mil.br/pt-br/noticias",
    },
    {
        "label": "DPC — Habilitação Aquaviária",
        "url": "https://www.dpc.mar.mil.br/pt-br/aquaviarios/habilitacao-aquaviaria",
    },
]


def fetch() -> list[dict]:
    """Pesquisa portarias e publicações relevantes na DPC."""
    results = []
    seen_urls = set()

    for page in PAGES:
        try:
            items = _scrape_page(page["label"], page["url"], seen_urls)
            results.extend(items)
            time.sleep(2)
        except Exception as e:
            print(f"  [DPC] Erro em '{page['label']}': {e}")

    print(f"  [DPC] Total relevantes: {len(results)}")
    return results


def _scrape_page(label: str, url: str, seen_urls: set) -> list[dict]:
    """Extrai links e títulos de uma página da DPC."""
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=40, verify=False)
            resp.raise_for_status()
            break
        except Exception as e:
            if attempt == 1:
                print(f"  [DPC] HTTP erro em {url}: {e}")
                return []
            time.sleep(3)

    html = resp.text
    matched = []

    # Extrair links com títulos — padrão típico de portais gov.br
    # Padrões: <a href="...">Portaria DPC-...</a> ou links de notícias
    patterns = [
        # Links em listas de portarias / normas
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*([^<]{10,200})\s*</a>',
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
            link_raw = m.group(1).strip()
            title    = re.sub(r"\s+", " ", m.group(2)).strip()

            if not title or len(title) < 10:
                continue

            # Resolver URL relativa
            if link_raw.startswith("/"):
                link = f"https://www.dpc.mar.mil.br{link_raw}"
            elif link_raw.startswith("http"):
                link = link_raw
            else:
                continue

            if link in seen_urls:
                continue

            relevant, keywords_found = is_relevant(title)
            if not relevant:
                # Verificar também se é claramente uma portaria/norma marítima
                if not _is_maritime_document(title):
                    continue
                keywords_found = _extract_doc_keywords(title)

            seen_urls.add(link)
            matched.append({
                "source": label,
                "country": "BR",
                "title": title,
                "description": f"Publicação detectada em: {label}",
                "url": link,
                "date_found": datetime.now(timezone.utc).date().isoformat(),
                "matched_keywords": ", ".join(keywords_found) if keywords_found else "portaria/norma marítima",
            })

    return matched


def _is_maritime_document(title: str) -> bool:
    """Verifica se o título parece ser um documento marítimo relevante."""
    title_lower = title.lower()
    triggers = [
        "portaria", "norma", "instrução normativa", "aviso",
        "stcw", "certificad", "endoss", "aquaviár",
        "marítim", "habilitaç", "reconheciment",
    ]
    return any(t in title_lower for t in triggers)


def _extract_doc_keywords(title: str) -> list[str]:
    title_lower = title.lower()
    found = []
    for kw in ["portaria", "stcw", "certificado", "endosso", "aquaviário", "habilitação", "reconhecimento"]:
        if kw in title_lower:
            found.append(kw)
    return found

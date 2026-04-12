"""
CIAGA — Centro de Instrução Almirante Graça Aranha (Brasil)
Monitoriza avisos, cursos e publicações relevantes em:
  https://www.ciaga.mar.mil.br
"""
import re
import time
import requests
import urllib3
from datetime import datetime, timezone
from scraper.filters import is_relevant

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; STCWMonitor/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml",
    "Accept-Language": "pt-BR,pt;q=0.9",
}

PAGES = [
    {
        "label": "CIAGA — Página Principal",
        "url": "https://www.ciaga.mar.mil.br",
    },
    {
        "label": "CIAGA — Notícias",
        "url": "https://www.ciaga.mar.mil.br/noticias",
    },
    {
        "label": "CIAGA — Cursos",
        "url": "https://www.ciaga.mar.mil.br/cursos",
    },
]


def fetch() -> list[dict]:
    """Pesquisa publicações relevantes no CIAGA."""
    results = []
    seen_urls = set()

    for page in PAGES:
        try:
            items = _scrape_page(page["label"], page["url"], seen_urls)
            results.extend(items)
            time.sleep(2)
        except Exception as e:
            print(f"  [CIAGA] Erro em '{page['label']}': {e}")

    print(f"  [CIAGA] Total relevantes: {len(results)}")
    return results


def _scrape_page(label: str, url: str, seen_urls: set) -> list[dict]:
    for attempt in range(2):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=40, verify=False)
            resp.raise_for_status()
            break
        except Exception as e:
            if attempt == 1:
                print(f"  [CIAGA] HTTP erro em {url}: {e}")
                return []
            time.sleep(3)

    html = resp.text
    matched = []

    pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*([^<]{10,200})\s*</a>'

    for m in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
        link_raw = m.group(1).strip()
        title    = re.sub(r"\s+", " ", m.group(2)).strip()

        if not title or len(title) < 10:
            continue

        if link_raw.startswith("/"):
            link = f"https://www.ciaga.mar.mil.br{link_raw}"
        elif link_raw.startswith("http"):
            link = link_raw
        else:
            continue

        if link in seen_urls:
            continue

        relevant, keywords_found = is_relevant(title)
        if not relevant:
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
            "matched_keywords": ", ".join(keywords_found) if keywords_found else "aviso/curso marítimo",
        })

    return matched


def _is_maritime_document(title: str) -> bool:
    title_lower = title.lower()
    triggers = [
        "portaria", "aviso", "stcw", "certificad", "endoss",
        "aquaviár", "marítim", "habilitaç", "reconheciment", "curso",
        "instrução", "normativa", "circular",
    ]
    return any(t in title_lower for t in triggers)


def _extract_doc_keywords(title: str) -> list[str]:
    title_lower = title.lower()
    found = []
    for kw in ["portaria", "aviso", "stcw", "certificado", "endosso",
               "aquaviário", "habilitação", "reconhecimento", "curso"]:
        if kw in title_lower:
            found.append(kw)
    return found

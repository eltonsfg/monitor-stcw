"""
DGRM — Direção-Geral de Recursos Naturais, Segurança e Serviços Marítimos (Portugal)
Monitoriza portarias, despachos e publicações relevantes em:
  https://www.dgrm.mm.gov.pt
"""
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from scraper.filters import is_relevant

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; STCWMonitor/1.0)",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/rss+xml",
    "Accept-Language": "pt-PT,pt;q=0.9",
}

PAGES = [
    {
        "label": "DGRM — Maritimos (Gente do Mar / Titulos)",
        "url": "https://www.dgrm.pt/maritimos",
    },
    {
        "label": "DGRM — Titulos e Certificados",
        "url": "https://www.dgrm.pt/titulos",
    },
    {
        "label": "DGRM — Noticias",
        "url": "https://www.dgrm.pt/noticias-geral",
    },
    {
        "label": "DGRM — Destaques",
        "url": "https://www.dgrm.pt/destaques",
    },
]

# RSS nao disponivel no novo dominio — lista vazia
RSS_FEEDS = []


def fetch() -> list[dict]:
    """Pesquisa portarias e publicações relevantes na DGRM."""
    results = []
    seen_urls = set()

    # Tentar RSS primeiro (mais fiável)
    for feed in RSS_FEEDS:
        try:
            items = _fetch_rss(feed["label"], feed["url"], seen_urls)
            results.extend(items)
            time.sleep(1)
        except Exception as e:
            print(f"  [DGRM] RSS erro em '{feed['label']}': {e}")

    # Scraping directo das páginas
    for page in PAGES:
        try:
            items = _scrape_page(page["label"], page["url"], seen_urls)
            results.extend(items)
            time.sleep(2)
        except Exception as e:
            print(f"  [DGRM] Erro em '{page['label']}': {e}")

    print(f"  [DGRM] Total relevantes: {len(results)}")
    return results


def _fetch_rss(label: str, url: str, seen_urls: set) -> list[dict]:
    """Tenta RSS Liferay da DGRM."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return []
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")
    except Exception:
        return []

    matched = []
    for item in items:
        title       = (item.findtext("title") or "").strip()
        description = re.sub(r"<[^>]+>", " ", item.findtext("description") or "").strip()
        link        = (item.findtext("link") or "").strip()

        if not title or link in seen_urls:
            continue

        relevant, keywords_found = is_relevant(title, description)
        if not relevant:
            if not _is_maritime_document(title):
                continue
            keywords_found = _extract_doc_keywords(title)

        seen_urls.add(link)
        matched.append({
            "source": label,
            "country": "PT",
            "title": title,
            "description": description[:500],
            "url": link,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
            "matched_keywords": ", ".join(keywords_found) if keywords_found else "portaria/despacho marítimo",
        })

    return matched


def _scrape_page(label: str, url: str, seen_urls: set) -> list[dict]:
    """Extrai links e títulos de uma página da DGRM."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [DGRM] HTTP erro em {url}: {e}")
        return []

    html = resp.text
    matched = []

    pattern = r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>\s*([^<]{10,300})\s*</a>'

    for m in re.finditer(pattern, html, re.IGNORECASE | re.DOTALL):
        link_raw = m.group(1).strip()
        title    = re.sub(r"\s+", " ", m.group(2)).strip()

        if not title or len(title) < 10:
            continue

        # Resolver URL relativa
        if link_raw.startswith("/"):
            link = f"https://www.dgrm.pt{link_raw}"
        elif link_raw.startswith("http"):
            link = link_raw
        else:
            continue

        # Filtrar links internos de navegação
        if any(skip in link_raw for skip in ["#", "javascript:", "mailto:", "tel:"]):
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
            "country": "PT",
            "title": title,
            "description": f"Publicação detectada em: {label}",
            "url": link,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
            "matched_keywords": ", ".join(keywords_found) if keywords_found else "portaria/despacho marítimo",
        })

    return matched


def _is_maritime_document(title: str) -> bool:
    title_lower = title.lower()
    triggers = [
        "portaria", "despacho", "circular", "aviso", "decreto",
        "stcw", "certificad", "endoss", "maritim", "marítim",
        "habilitaç", "reconheciment", "gente do mar", "dgrm",
        "diploma", "regulamento",
    ]
    return any(t in title_lower for t in triggers)


def _extract_doc_keywords(title: str) -> list[str]:
    title_lower = title.lower()
    found = []
    for kw in ["portaria", "despacho", "stcw", "certificado", "endosso",
               "marítimo", "habilitação", "reconhecimento", "gente do mar", "decreto"]:
        if kw in title_lower:
            found.append(kw)
    return found

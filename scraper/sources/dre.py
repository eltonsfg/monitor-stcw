"""
Diário da República (Portugal) — RSS Série I e Série II.
Feeds: https://files.diariodarepublica.pt/rss/serie1.xml
       https://files.diariodarepublica.pt/rss/serie2.xml
"""
import re
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from scraper.filters import is_relevant

FEEDS = {
    "DRE Série I": "https://files.diariodarepublica.pt/rss/serie1.xml",
    "DRE Série II": "https://files.diariodarepublica.pt/rss/serie2.xml",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; STCWMonitor/1.0; +https://github.com)",
    "Accept": "application/rss+xml, application/xml, text/xml",
}


def fetch() -> list[dict]:
    results = []
    for feed_name, url in FEEDS.items():
        try:
            items = _fetch_feed(feed_name, url)
            results.extend(items)
            time.sleep(1)
        except Exception as e:
            print(f"  [{feed_name}] ERRO: {e}")
    return results


def _fetch_feed(feed_name: str, url: str) -> list[dict]:
    resp = requests.get(url, headers=HEADERS, timeout=20)
    resp.raise_for_status()

    root = ET.fromstring(resp.content)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items = root.findall(".//item") or root.findall(".//atom:entry", ns)

    matched = []
    seen_urls = set()

    for item in items:
        title = _text(item, "title")
        description = _strip_html(_text(item, "description"))
        link = _text(item, "link")

        # DRE tem duplicados (PDF + imagens) — manter só PDFs
        if link and not link.endswith(".pdf"):
            continue
        if link in seen_urls:
            continue
        seen_urls.add(link)

        relevant, keywords = is_relevant(title, description)
        if not relevant:
            continue

        matched.append({
            "source": feed_name,
            "country": "PT",
            "title": title,
            "description": description[:500],
            "url": link,
            "date_found": datetime.now(timezone.utc).date().isoformat(),
            "matched_keywords": ", ".join(keywords),
        })

    print(f"  [{feed_name}] {len(items)} publicacoes -> {len(matched)} relevantes")
    return matched


def _text(element, tag: str) -> str:
    el = element.find(tag)
    if el is None:
        return ""
    text = el.text or ""
    # CDATA
    if hasattr(el, "text") and el.text:
        text = el.text
    return text.strip()


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text).strip()

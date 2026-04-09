"""
Diário Oficial da União (Brasil) — pesquisa via Playwright.
O RSS do DOU está bloqueado para bots; usamos o motor de busca oficial.
URL: https://www.in.gov.br/consulta/-/busca-oficial
"""
import time
from datetime import datetime, timezone
from scraper.filters import is_relevant, get_all_keywords

# Data de hoje no formato do DOU (dd-mm-yyyy)
_TODAY = datetime.now(timezone.utc).strftime("%d-%m-%Y")


def fetch() -> list[dict]:
    """Pesquisa cada keyword no DOU e devolve publicações relevantes."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [DOU] playwright não instalado. Corre: pip install playwright && playwright install chromium")
        return []

    results = []
    seen_urls = set()
    keywords = get_all_keywords()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--disable-http2", "--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            locale="pt-BR",
            extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9"},
        )
        page = context.new_page()

        for kw in keywords:
            try:
                items = _search_keyword(page, kw, seen_urls)
                results.extend(items)
                time.sleep(2)  # respeitar rate limit
            except Exception as e:
                print(f"  [DOU] Erro ao pesquisar '{kw}': {e}")

        browser.close()

    print(f"  [DOU] Total relevantes: {len(results)}")
    return results


def _search_keyword(page, keyword: str, seen_urls: set) -> list[dict]:
    """Executa uma pesquisa no DOU e extrai resultados de hoje."""
    url = (
        f"https://www.in.gov.br/consulta/-/busca-oficial"
        f"?q={_encode(keyword)}&exactDate=dia&newPage=1&delta=20&score=0&types=materia"
    )

    page.goto(url, wait_until="domcontentloaded", timeout=35000)

    # Aguardar resultados
    try:
        page.wait_for_selector(".resultado-item, .no-result, #sem-resultado", timeout=10000)
    except Exception:
        pass  # continuar mesmo sem selector específico

    # Extrair itens
    items_html = page.query_selector_all(".resultado-item")
    matched = []

    for el in items_html:
        try:
            title_el = el.query_selector("h5, .title, [class*='title']")
            title = title_el.inner_text().strip() if title_el else ""

            desc_el = el.query_selector("p, .resumo, [class*='summary']")
            description = desc_el.inner_text().strip() if desc_el else ""

            link_el = el.query_selector("a")
            link = link_el.get_attribute("href") if link_el else ""
            if link and not link.startswith("http"):
                link = f"https://www.in.gov.br{link}"

            if not title or link in seen_urls:
                continue

            relevant, keywords_found = is_relevant(title, description)
            if not relevant:
                continue

            seen_urls.add(link)
            matched.append({
                "source": "DOU",
                "country": "BR",
                "title": title,
                "description": description[:500],
                "url": link,
                "date_found": datetime.now(timezone.utc).date().isoformat(),
                "matched_keywords": ", ".join(keywords_found),
            })
        except Exception:
            continue

    return matched


def _encode(text: str) -> str:
    from urllib.parse import quote
    return quote(f'"{text}"')

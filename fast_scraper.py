"""
fast_scraper.py — Async scraper using Playwright for ALL sites.
RESILIENT VERSION: Uses page.evaluate() with structural DOM traversal
instead of fragile CSS class selectors. Extracts data by:
  - data-* attributes (stable)
  - href URL patterns (stable)
  - Text content patterns (₹ for price, structural position for title)
  - Embedded JSON where available (window.__myx for Myntra)
Falls back to Selenium-based Scraper.py if Playwright fails.
"""

import asyncio
import random
import re
import time

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def _clean_price(raw):
    if not raw:
        return None
    raw = raw.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    match = re.search(r'(\d+(?:\.\d+)?)', raw)
    return float(match.group(1)) if match else None


async def _scroll_page(page):
    """Scroll the page to trigger lazy-loaded content."""
    await page.evaluate("window.scrollBy(0, 1200)")
    await asyncio.sleep(1.5)
    await page.evaluate("window.scrollBy(0, 1000)")
    await asyncio.sleep(1)
    await page.evaluate("window.scrollBy(0, 800)")
    await asyncio.sleep(0.5)


# ---------------------------------------------------------------------------
# AMAZON — stable data-component-type selectors (keep proven approach)
# ---------------------------------------------------------------------------
async def scrape_amazon_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.amazon.in/s?k={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=20000,
        )
        try:
            await page.wait_for_selector("div[data-component-type='s-search-result']", timeout=12000)
        except:
            pass
        await _scroll_page(page)

        raw = await page.evaluate("""() => {
            const results = [];
            const cards = document.querySelectorAll("div[data-component-type='s-search-result']");
            for (const card of [...cards].slice(0, 25)) {
                try {
                    const titleEl = card.querySelector('h2 a span') || card.querySelector('h2 span');
                    const priceEl = card.querySelector('.a-price-whole');
                    const ratingEl = card.querySelector('.a-icon-alt');
                    const linkEl = card.querySelector('h2 a');
                    const title = titleEl ? titleEl.innerText.trim() : '';
                    const priceRaw = priceEl ? priceEl.innerText.trim() : '';
                    const rating = ratingEl ? ratingEl.innerText.trim() : null;
                    let href = linkEl ? linkEl.getAttribute('href') : '';
                    if (href && !href.startsWith('http')) href = 'https://www.amazon.in' + href;
                    if (title && href) {
                        results.push({ source:'Amazon', title, price_raw:'₹'+priceRaw, rating, link:href });
                    }
                } catch(e) { continue; }
            }
            return results;
        }""")
        for p in raw:
            p['price'] = _clean_price(p.get('price_raw'))
            products.append(p)
    except Exception as e:
        print(f"[Amazon PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# FLIPKART — structural extraction: data-id containers + href /p/ pattern
# ---------------------------------------------------------------------------
async def scrape_flipkart_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.flipkart.com/search?q={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=20000,
        )
        await asyncio.sleep(2)
        await _scroll_page(page)

        raw = await page.evaluate("""() => {
            const results = [];
            let containers = [...document.querySelectorAll('div[data-id]')];
            if (!containers.length) {
                const links = document.querySelectorAll('a[href*="/p/itm"]');
                const cSet = new Set();
                for (const l of links) {
                    let el = l.parentElement;
                    for (let i = 0; i < 5 && el; i++) { el = el.parentElement; }
                    if (el) cSet.add(el);
                }
                containers = [...cSet];
            }
            for (const c of containers.slice(0, 25)) {
                try {
                    const linkEl = c.querySelector('a[href*="/p/itm"]') || c.querySelector('a[href*="/p/"]') || c.querySelector('a[href]');
                    if (!linkEl) continue;
                    let href = linkEl.getAttribute('href');
                    if (href && !href.startsWith('http')) href = 'https://www.flipkart.com' + href;
                    if (!href || !href.includes('flipkart.com')) continue;

                    const lines = c.innerText.split('\n').map(t=>t.trim()).filter(Boolean);
                    let title='', priceRaw='', rating=null;
                    for (const t of lines) {
                        if (!title && t.length>8 && !t.startsWith('\u20b9') && !t.includes('% off') && !t.match(/^\d\.\d$/) && !t.includes('Sponsored') && !t.startsWith('Free')) { title=t; }
                        if (!priceRaw && t.startsWith('\u20b9') && t.length<15) { priceRaw=t; }
                        if (!rating) { const m=t.match(/^(\d\.\d)\s/); if(m) rating=m[1]; }
                    }
                    if (title && href) results.push({source:'Flipkart',title,price_raw:priceRaw,rating,link:href});
                } catch(e) { continue; }
            }
            return results;
        }""")
        for p in raw:
            p['price'] = _clean_price(p.get('price_raw'))
            products.append(p)
    except Exception as e:
        print(f"[Flipkart PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# MYNTRA — embedded JSON (window.__myx) with DOM fallback
# ---------------------------------------------------------------------------
async def scrape_myntra_pw(page, query):
    products = []
    try:
        # Myntra search URL uses hyphens
        await page.goto(
            f"https://www.myntra.com/{query.replace(' ', '-')}",
            wait_until="domcontentloaded", timeout=20000,
        )
        await asyncio.sleep(2)
        await _scroll_page(page)

        raw = await page.evaluate("""() => {
            const results = [];
            try {
                const d = window.__myx;
                if (d && d.searchData && d.searchData.results && d.searchData.results.products) {
                    for (const p of d.searchData.results.products.slice(0, 25)) {
                        results.push({
                            source:'Myntra',
                            title: ((p.brand||'') + ' ' + (p.product||p.name||'')).trim(),
                            price_raw: '\u20b9' + (p.discountedPrice||p.price||p.mrp||''),
                            price_num: p.discountedPrice||p.price||p.mrp||null,
                            rating: p.rating ? String(p.rating) : null,
                            link: 'https://www.myntra.com/' + (p.landingPageUrl||p.id||''),
                        });
                    }
                    if (results.length) return results;
                }
            } catch(e) {}

            const items = document.querySelectorAll('li');
            for (const li of [...items].slice(0, 60)) {
                try {
                    const link = li.querySelector('a[href]');
                    if (!link) continue;
                    const href = link.getAttribute('href');
                    if (!href || href==='/' || href.includes('login') || href.startsWith('/shop/')) continue;
                    const lines = li.innerText.split('\n').map(t=>t.trim()).filter(Boolean);
                    if (lines.length < 2) continue;
                    let brand='', name='', priceRaw='';
                    for (const t of lines) {
                        if (t.startsWith('\u20b9') || t.startsWith('Rs')) { if(!priceRaw) priceRaw=t; }
                        else if (!brand && t.length>1 && t.length<40) brand=t;
                        else if (brand && !name && t.length>1 && t.length<80) name=t;
                    }
                    const title = (brand+' '+name).trim();
                    if (title.length<3) continue;
                    const fullHref = href.startsWith('http') ? href : 'https://www.myntra.com/' + href.replace(/^\//, '');
                    results.push({source:'Myntra',title,price_raw:priceRaw,rating:null,link:fullHref});
                } catch(e) { continue; }
            }
            const seen = new Set();
            return results.filter(r=>{if(seen.has(r.link))return false;seen.add(r.link);return true;}).slice(0,25);
        }""")
        for p in raw:
            if p.get('price_num'):
                p['price'] = float(p['price_num'])
            else:
                p['price'] = _clean_price(p.get('price_raw'))
            p.pop('price_num', None)
            products.append(p)
    except Exception as e:
        print(f"[Myntra PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# MEESHO — structural: product links always contain /product/
# ---------------------------------------------------------------------------
async def scrape_meesho_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.meesho.com/search?q={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=20000,
        )
        await asyncio.sleep(2)
        await _scroll_page(page)

        raw = await page.evaluate("""() => {
            const results = [];
            const links = document.querySelectorAll('a[href*="/product/"]');
            const seen = new Set();
            for (const link of [...links].slice(0, 30)) {
                try {
                    let href = link.getAttribute('href');
                    if (href && !href.startsWith('http')) href = 'https://www.meesho.com' + href;
                    if (seen.has(href)) continue;
                    seen.add(href);
                    let container = link;
                    for (let i=0; i<6 && container.parentElement; i++) container = container.parentElement;
                    const lines = container.innerText.split('\n').map(t=>t.trim()).filter(Boolean);
                    let title='', priceRaw='';
                    for (const t of lines) {
                        if (!title && t.length>5 && t.length<120 && !t.startsWith('\u20b9') && !t.includes('% off') && !t.includes('Free') && !t.match(/^\d+$/)) title=t;
                        if (!priceRaw && t.startsWith('\u20b9') && t.length<12) priceRaw=t;
                    }
                    if (title && href) results.push({source:'Meesho',title,price_raw:priceRaw,rating:null,link:href});
                } catch(e) { continue; }
            }
            return results.slice(0, 25);
        }""")
        for p in raw:
            p['price'] = _clean_price(p.get('price_raw'))
            products.append(p)
    except Exception as e:
        print(f"[Meesho PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# AJIO — structural: product links contain /p/ pattern
# ---------------------------------------------------------------------------
async def scrape_ajio_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.ajio.com/search/?text={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=20000,
        )
        await asyncio.sleep(3)
        await _scroll_page(page)

        raw = await page.evaluate("""() => {
            const results = [];
            const allLinks = document.querySelectorAll('a[href*="/p/"]');
            const seen = new Set();
            for (const link of [...allLinks].slice(0, 30)) {
                try {
                    let href = link.getAttribute('href');
                    if (href && !href.startsWith('http')) href = 'https://www.ajio.com' + href;
                    if (seen.has(href)) continue;
                    seen.add(href);
                    let container = link;
                    if (link.children.length < 2) {
                        for (let i=0; i<4 && container.parentElement; i++) container = container.parentElement;
                    }
                    const lines = container.innerText.split('\n').map(t=>t.trim()).filter(Boolean);
                    let title='', priceRaw='';
                    for (const t of lines) {
                        if (!title && t.length>3 && t.length<100 && !t.startsWith('\u20b9') && !t.includes('% off') && !t.match(/^\d+$/)) title=t;
                        if (!priceRaw && (t.startsWith('\u20b9') || t.startsWith('Rs')) && t.length<15) priceRaw=t;
                    }
                    if (title && href && href.includes('ajio.com')) results.push({source:'Ajio',title,price_raw:priceRaw,rating:null,link:href});
                } catch(e) { continue; }
            }
            return results.slice(0, 20);
        }""")
        for p in raw:
            p['price'] = _clean_price(p.get('price_raw'))
            products.append(p)
    except Exception as e:
        print(f"[Ajio PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# NYKAA — structural extraction from product grid
# ---------------------------------------------------------------------------
async def scrape_nykaa_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.nykaa.com/search/result/?q={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=20000,
        )
        await asyncio.sleep(3)
        await _scroll_page(page)

        raw = await page.evaluate("""() => {
            const results = [];
            const allLinks = document.querySelectorAll('a[href*="/p/"]');
            const seen = new Set();
            for (const link of [...allLinks].slice(0, 30)) {
                try {
                    let href = link.getAttribute('href');
                    if (href && !href.startsWith('http')) href = 'https://www.nykaa.com' + href;
                    if (seen.has(href) || !href.includes('nykaa.com')) continue;
                    seen.add(href);
                    let container = link;
                    for (let i=0; i<4 && container.parentElement; i++) container = container.parentElement;
                    const lines = container.innerText.split('\n').map(t=>t.trim()).filter(Boolean);
                    if (lines.length < 2) continue;
                    let title='', priceRaw='';
                    for (const t of lines) {
                        if (!title && t.length>3 && t.length<120 && !t.startsWith('\u20b9') && !t.includes('% off') && !t.match(/^\d+$/)) title=t;
                        if (!priceRaw && (t.startsWith('\u20b9') || t.startsWith('Rs')) && t.length<15) priceRaw=t;
                    }
                    if (title && href) results.push({source:'Nykaa',title,price_raw:priceRaw,rating:null,link:href});
                } catch(e) { continue; }
            }
            return results.slice(0, 20);
        }""")
        for p in raw:
            p['price'] = _clean_price(p.get('price_raw'))
            products.append(p)
    except Exception as e:
        print(f"[Nykaa PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# TATACLIQ — structural extraction
# ---------------------------------------------------------------------------
async def scrape_tatacliq_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.tatacliq.com/search/?searchCategory=all&text={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=20000,
        )
        await asyncio.sleep(3)
        await _scroll_page(page)

        raw = await page.evaluate("""() => {
            const results = [];
            const allLinks = document.querySelectorAll('a[href*="/p/"]');
            const seen = new Set();
            for (const link of [...allLinks].slice(0, 30)) {
                try {
                    let href = link.getAttribute('href');
                    if (href && !href.startsWith('http')) href = 'https://www.tatacliq.com' + href;
                    if (seen.has(href) || !href.includes('tatacliq.com')) continue;
                    seen.add(href);
                    let container = link;
                    for (let i=0; i<4 && container.parentElement; i++) container = container.parentElement;
                    const lines = container.innerText.split('\n').map(t=>t.trim()).filter(Boolean);
                    let title='', priceRaw='';
                    for (const t of lines) {
                        if (!title && t.length>3 && t.length<120 && !t.startsWith('\u20b9') && !t.includes('% off') && !t.match(/^\d+$/) && !t.startsWith('Free')) title=t;
                        if (!priceRaw && (t.startsWith('\u20b9') || t.startsWith('Rs')) && t.length<15) priceRaw=t;
                    }
                    if (title && href) results.push({source:'TataCLiQ',title,price_raw:priceRaw,rating:null,link:href});
                } catch(e) { continue; }
            }
            return results.slice(0, 20);
        }""")
        for p in raw:
            p['price'] = _clean_price(p.get('price_raw'))
            products.append(p)
    except Exception as e:
        print(f"[TataCLiQ PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# MASTER: run_all_fast — single browser, all sites as separate tabs
# ---------------------------------------------------------------------------
async def run_all_fast(
    query: str,
    use_amazon=True, use_myntra=True, use_flipkart=True,
    use_ajio=True, use_nykaa=True, use_tatacliq=True, use_meesho=True,
):
    start = time.time()
    all_products = []

    try:
        from playwright.async_api import async_playwright
        try:
            # pyrefly: ignore [missing-import]
            from playwright_stealth import stealth as _stealth
            _has_stealth = True
        except ImportError:
            print("[FastScraper] playwright_stealth not installed — running without stealth mode")
            _has_stealth = False

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-blink-features=AutomationControlled",
                    "--blink-settings=imagesEnabled=false",
                ],
            )
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice(USER_AGENTS),
                java_script_enabled=True,
                bypass_csp=True,
            )

            async def create_stealth_page():
                pg = await context.new_page()
                if _has_stealth:
                    await _stealth(pg)
                await pg.route(
                    "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,ico}",
                    lambda route: route.abort(),
                )
                return pg

            tasks = []
            platform_map = []

            if use_amazon:
                async def _a():
                    pg = await create_stealth_page()
                    try: return await scrape_amazon_pw(pg, query)
                    finally: await pg.close()
                tasks.append(_a()); platform_map.append("Amazon")

            if use_flipkart:
                async def _f():
                    pg = await create_stealth_page()
                    try: return await scrape_flipkart_pw(pg, query)
                    finally: await pg.close()
                tasks.append(_f()); platform_map.append("Flipkart")

            if use_myntra:
                async def _m():
                    pg = await create_stealth_page()
                    try: return await scrape_myntra_pw(pg, query)
                    finally: await pg.close()
                tasks.append(_m()); platform_map.append("Myntra")

            if use_meesho:
                async def _me():
                    pg = await create_stealth_page()
                    try: return await scrape_meesho_pw(pg, query)
                    finally: await pg.close()
                tasks.append(_me()); platform_map.append("Meesho")

            if use_ajio:
                async def _aj():
                    pg = await create_stealth_page()
                    try: return await scrape_ajio_pw(pg, query)
                    finally: await pg.close()
                tasks.append(_aj()); platform_map.append("Ajio")

            if use_nykaa:
                async def _ny():
                    pg = await create_stealth_page()
                    try: return await scrape_nykaa_pw(pg, query)
                    finally: await pg.close()
                tasks.append(_ny()); platform_map.append("Nykaa")

            if use_tatacliq:
                async def _ta():
                    pg = await create_stealth_page()
                    try: return await scrape_tatacliq_pw(pg, query)
                    finally: await pg.close()
                tasks.append(_ta()); platform_map.append("TataCLiQ")

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                name = platform_map[i] if i < len(platform_map) else f"Unknown_{i}"
                if isinstance(result, list) and len(result) > 0:
                    all_products.extend(result)
                    print(f"[Scraper] {name}: {len(result)} results")
                elif isinstance(result, Exception):
                    print(f"[Scraper Error] {name}: {result}")
                    all_products.append({"source":name,"title":f"Product not available on {name}","price":None,"price_raw":None,"rating":None,"link":None,"unavailable":True})
                else:
                    print(f"[Scraper] {name}: 0 results")
                    all_products.append({"source":name,"title":f"Product not available on {name}","price":None,"price_raw":None,"rating":None,"link":None,"unavailable":True})

            await browser.close()
    except Exception as e:
        print(f"[FastScraper] Critical error: {e}")

    all_products.sort(key=lambda x: (x.get("unavailable", False), x["price"] is None, x["price"] or 0))
    elapsed = time.time() - start
    print(f"[FastScraper] Scraped {len(all_products)} products in {elapsed:.2f}s")
    return all_products


def run_fast_sync(query: str, **kwargs):
    """Synchronous wrapper for Flask routes."""
    return asyncio.run(run_all_fast(query, **kwargs))


# ---------------------------------------------------------------------------
# FALLBACK: Use the working Selenium scraper if Playwright returns nothing
# ---------------------------------------------------------------------------
def run_with_fallback(query: str, **kwargs):
    results = run_fast_sync(query, **kwargs)
    # Filter out only unavailable placeholders to check if we got real data
    real_results = [r for r in results if not r.get("unavailable")]
    if real_results:
        return results

    print("[FastScraper] Playwright returned 0 real results, falling back to Selenium scraper...")
    try:
        from Scraper import run_scrapers_and_update_db, DB_NAME, TABLE_NAME
        import sqlite3, pandas as pd

        run_scrapers_and_update_db(
            query,
            use_amazon=kwargs.get("use_amazon", True),
            use_flipkart=kwargs.get("use_flipkart", True),
            use_myntra=kwargs.get("use_myntra", True),
            use_meesho=kwargs.get("use_meesho", True),
            use_ajio=kwargs.get("use_ajio", True),
            use_nykaa=kwargs.get("use_nykaa", True),
            use_tatacliq=kwargs.get("use_tatacliq", True),
            max_pages=1, headless=True,
        )

        conn = sqlite3.connect(DB_NAME)
        try:
            df = pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
        except Exception:
            conn.close()
            return results  # return placeholders
        conn.close()

        selenium_results = []
        for _, row in df.iterrows():
            selenium_results.append({
                "source": row.get("Source", "Unknown"),
                "title": row.get("Title", ""),
                "price_raw": str(row.get("Price", "")),
                "price": float(row["Price"]) if pd.notna(row.get("Price")) else None,
                "rating": str(row.get("Rating", "")) if pd.notna(row.get("Rating")) else None,
                "link": row.get("Link", ""),
            })

        selenium_results.sort(key=lambda x: (x["price"] is None, x["price"] or 0))
        print(f"[Selenium Fallback] Returned {len(selenium_results)} products from DB")
        return selenium_results if selenium_results else results
    except Exception as e:
        print(f"[Selenium Fallback] Error: {e}")
        return results
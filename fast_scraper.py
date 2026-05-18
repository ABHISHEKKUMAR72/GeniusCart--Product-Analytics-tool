"""
fast_scraper.py — Async scraper using Playwright for ALL sites.
httpx doesn't work for JS-heavy e-commerce sites (they render products via JavaScript).
Playwright renders all JS, blocks images/fonts for speed, and runs all sites concurrently.
Falls back to Selenium-based Scraper.py if Playwright fails.
"""

import asyncio
import random
import re
import time

# ---------------------------------------------------------------------------
# User-Agent pool
# ---------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
]

def _clean_price(raw):
    """Extract numeric price from strings like '₹1,23,456' or 'Rs. 999'."""
    if not raw:
        return None
    raw = raw.replace(",", "").replace("₹", "").replace("Rs.", "").replace("Rs", "").strip()
    match = re.search(r'(\d+(?:\.\d+)?)', raw)
    return float(match.group(1)) if match else None


async def _create_page(browser):
    """Create a stealth browser page with image/font blocking for speed."""
    ctx = await browser.new_context(
        user_agent=random.choice(USER_AGENTS),
        viewport={"width": 1366, "height": 768},
        java_script_enabled=True,
    )
    page = await ctx.new_page()
    # Block heavy resources to speed up page loads
    await page.route(
        "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,ico}",
        lambda route: route.abort()
    )
    await page.route("**/*", lambda route: (
        route.abort() if route.request.resource_type in ("image", "font", "media", "stylesheet")
        else route.continue_()
    ))
    return page
# ---------------------------------------------------------------------------
# ------ Async Playwright Scrapers (with Fallbacks) ------
# Reduced timeouts to give control back faster 

async def scrape_amazon_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.amazon.in/s?k={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=18000,
        )
        try:
            await page.wait_for_selector("div[data-component-type='s-search-result']", timeout=10000)
        except:
            pass

        # Scroll to trigger lazy-loaded content
        await page.evaluate("window.scrollBy(0, 1200)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(0.5)

        cards = await page.query_selector_all("div[data-component-type='s-search-result']")
        for card in cards[:25]:
            try:
                title_el = await card.query_selector("h2 a span, h2 span")
                price_el = await card.query_selector(".a-price-whole")
                rating_el = await card.query_selector(".a-icon-alt")
                link_el = await card.query_selector("h2 a")

                title = (await title_el.inner_text()).strip() if title_el else ""
                price_raw = (await price_el.inner_text()).strip() if price_el else ""
                rating = (await rating_el.inner_text()).strip() if rating_el else None
                href = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.amazon.in" + href

                if title and href:
                    products.append({
                        "source": "Amazon", "title": title,
                        "price_raw": f"₹{price_raw}", "price": _clean_price(price_raw),
                        "rating": rating, "link": href,
                    })
            except:
                continue
    except Exception as e:
        print(f"[Amazon PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# FLIPKART — Playwright
# ---------------------------------------------------------------------------
async def scrape_flipkart_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.flipkart.com/search?q={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=18000,
        )
        try:
            await page.wait_for_selector("div[data-id], div._75nlfW, a.CGtC98", timeout=10000)
        except:
            pass

        # Scroll to trigger lazy-loaded content
        await page.evaluate("window.scrollBy(0, 1200)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(0.5)

        cards = await page.query_selector_all("div[data-id]")
        if not cards:
            cards = await page.query_selector_all("div._75nlfW")
        if not cards:
            cards = await page.query_selector_all("a.CGtC98")

        for card in cards[:25]:
            try:
                title_el = (
                    await card.query_selector("a.IRpwTa") or
                    await card.query_selector("div.KzDlHZ") or
                    await card.query_selector("a.wjcEIp") or
                    await card.query_selector("div._4rR01T") or
                    await card.query_selector("a.s1Q8DL")
                )
                price_el = (
                    await card.query_selector("div.Nx9bqj") or
                    await card.query_selector("div._30jeq3") or
                    await card.query_selector("div._1_WHN1")
                )
                link_el = await card.query_selector("a[href]")

                title = (await title_el.inner_text()).strip() if title_el else ""
                price_raw = (await price_el.inner_text()).strip() if price_el else ""
                href = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.flipkart.com" + href

                if title and href:
                    products.append({
                        "source": "Flipkart", "title": title,
                        "price_raw": price_raw, "price": _clean_price(price_raw),
                        "rating": None, "link": href,
                    })
            except:
                continue
    except Exception as e:
        print(f"[Flipkart PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# MYNTRA — Playwright
# ---------------------------------------------------------------------------
async def scrape_myntra_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.myntra.com/search?q={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=18000,
        )
        try:
            await page.wait_for_selector("li.product-base", timeout=10000)
        except:
            pass

        # Scroll to trigger lazy-loaded content
        await page.evaluate("window.scrollBy(0, 1200)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(0.5)

        cards = await page.query_selector_all("li.product-base")
        for card in cards[:25]:
            try:
                brand_el = await card.query_selector(".product-brand")
                name_el = await card.query_selector(".product-product")
                price_el = (
                    await card.query_selector(".product-discountedPrice") or
                    await card.query_selector(".product-price")
                )
                link_el = await card.query_selector("a[href]")

                brand = (await brand_el.inner_text()).strip() if brand_el else ""
                name = (await name_el.inner_text()).strip() if name_el else ""
                title = f"{brand} {name}".strip()
                price_raw = (await price_el.inner_text()).strip() if price_el else ""
                href = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.myntra.com/" + href

                if title and href:
                    products.append({
                        "source": "Myntra", "title": title,
                        "price_raw": price_raw, "price": _clean_price(price_raw),
                        "rating": None, "link": href,
                    })
            except:
                continue
    except Exception as e:
        print(f"[Myntra PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# MEESHO — Playwright
# ---------------------------------------------------------------------------
async def scrape_meesho_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.meesho.com/search?q={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=18000,
        )
        try:
            await page.wait_for_selector("div[class*='ProductCard'], a[href*='/product/']", timeout=10000)
        except:
            pass

        await page.evaluate("window.scrollBy(0, 1200)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(0.5)

        cards = await page.query_selector_all("a[href*='/product/']")
        if not cards:
            cards = await page.query_selector_all("div[class*='ProductCard']")

        for card in cards[:25]:
            try:
                title_el = await card.query_selector("p, h4, h5")
                price_el = await card.query_selector("h5, span[class*='Price']")
                
                title = (await title_el.inner_text()).strip() if title_el else ""
                price_raw = (await price_el.inner_text()).strip() if price_el else ""
                href = await card.get_attribute("href") if card.tag_name == "a" else ""
                if not href:
                    link_el = await card.query_selector("a[href]")
                    href = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.meesho.com" + href

                if title and href and "meesho.com" in str(href):
                    products.append({
                        "source": "Meesho", "title": title,
                        "price_raw": price_raw, "price": _clean_price(price_raw),
                        "rating": None, "link": href,
                    })
            except:
                continue
    except Exception as e:
        print(f"[Meesho PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# AJIO — Playwright
# ---------------------------------------------------------------------------
async def scrape_ajio_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.ajio.com/search/?text={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=18000,
        )
        try:
            await page.wait_for_selector(".item, .rilrtl-products-list__item, div.contentHolder", timeout=10000)
        except:
            pass

        # Scroll to trigger lazy-loaded content
        await page.evaluate("window.scrollBy(0, 1200)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(0.5)

        cards = await page.query_selector_all(".item, .rilrtl-products-list__item")
        for card in cards[:20]:
            try:
                title_el = await card.query_selector(".nameCls, .name, .brand")
                price_el = await card.query_selector(".price, .orginal-price")
                link_el = await card.query_selector("a[href]")

                title = (await title_el.inner_text()).strip() if title_el else ""
                price_raw = (await price_el.inner_text()).strip() if price_el else ""
                href = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.ajio.com" + href

                if title and href:
                    products.append({
                        "source": "Ajio", "title": title,
                        "price_raw": price_raw, "price": _clean_price(price_raw),
                        "rating": None, "link": href,
                    })
            except:
                continue
    except Exception as e:
        print(f"[Ajio PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# NYKAA — Playwright
# ---------------------------------------------------------------------------
async def scrape_nykaa_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.nykaa.com/search/result/?q={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=18000,
        )
        try:
            await page.wait_for_selector("div.productWrapper, div[class*='product']", timeout=10000)
        except:
            pass

        # Scroll to trigger lazy-loaded content
        await page.evaluate("window.scrollBy(0, 1200)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(0.5)

        cards = await page.query_selector_all("div.productWrapper, div[class*='css-']")
        for card in cards[:20]:
            try:
                title_el = await card.query_selector("div[class*='title'], p, span")
                price_el = await card.query_selector("span[class*='price'], div[class*='price']")
                link_el = await card.query_selector("a[href]")

                title = (await title_el.inner_text()).strip() if title_el else ""
                price_raw = (await price_el.inner_text()).strip() if price_el else ""
                href = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.nykaa.com" + href

                if title and href and len(title) > 3:
                    products.append({
                        "source": "Nykaa", "title": title,
                        "price_raw": price_raw, "price": _clean_price(price_raw),
                        "rating": None, "link": href,
                    })
            except:
                continue
    except Exception as e:
        print(f"[Nykaa PW] Error: {e}")
    return products


# ---------------------------------------------------------------------------
# TATACLIQ — Playwright
# ---------------------------------------------------------------------------
async def scrape_tatacliq_pw(page, query):
    products = []
    try:
        await page.goto(
            f"https://www.tatacliq.com/search/?searchCategory=all&text={query.replace(' ', '+')}",
            wait_until="domcontentloaded", timeout=18000,
        )
        try:
            await page.wait_for_selector("div[class*='ProductModule'], div[class*='product']", timeout=10000)
        except:
            pass

        # Scroll to trigger lazy-loaded content
        await page.evaluate("window.scrollBy(0, 1200)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollBy(0, 800)")
        await asyncio.sleep(0.5)

        cards = await page.query_selector_all("div[class*='ProductModule'], div[class*='ProductCard']")
        for card in cards[:20]:
            try:
                title_el = await card.query_selector("h2, p[class*='title'], div[class*='description']")
                price_el = await card.query_selector("h3, span[class*='price'], div[class*='price']")
                link_el = await card.query_selector("a[href]")

                title = (await title_el.inner_text()).strip() if title_el else ""
                price_raw = (await price_el.inner_text()).strip() if price_el else ""
                href = await link_el.get_attribute("href") if link_el else ""
                if href and not href.startswith("http"):
                    href = "https://www.tatacliq.com" + href

                if title and href:
                    products.append({
                        "source": "TataCLiQ", "title": title,
                        "price_raw": price_raw, "price": _clean_price(price_raw),
                        "rating": None, "link": href,
                    })
            except:
                continue
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
    """
    Launch ONE Playwright browser, open all scrapers as concurrent tasks
    (each in its own page/tab). Much faster than launching separate browsers.
    """
    start = time.time()
    all_products = []

    try:
        from playwright.async_api import async_playwright
        from playwright_stealth import stealth

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-blink-features=AutomationControlled",
                    "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "--blink-settings=imagesEnabled=false",
                ]
            )
            # Create context with anti-bot evasion headers
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                java_script_enabled=True,
                bypass_csp=True,
            )

            async def create_stealth_page():
                page = await context.new_page()
                await stealth(page)
                await page.route(
                    "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot,ico}",
                    lambda route: route.abort()
                )
                return page

            tasks = []
            if use_myntra:
                async def _m():
                    page = await create_stealth_page()
                    try:
                        return await scrape_myntra_pw(page, query)
                    finally:
                        await page.close()
                tasks.append(_m())

            if use_flipkart:
                async def _f():
                    page = await create_stealth_page()
                    try:
                        return await scrape_flipkart_pw(page, query)
                    finally:
                        await page.close()
                tasks.append(_f())

            if use_amazon:
                async def _a():
                    page = await create_stealth_page()
                    try:
                        return await scrape_amazon_pw(page, query)
                    finally:
                        await page.close()
                tasks.append(_a())

            if use_meesho:
                async def _me():
                    page = await create_stealth_page()
                    try:
                        return await scrape_meesho_pw(page, query)
                    finally:
                        await page.close()
                tasks.append(_me())

            if use_ajio:
                async def _aj():
                    page = await create_stealth_page()
                    try:
                        return await scrape_ajio_pw(page, query)
                    finally:
                        await page.close()
                tasks.append(_aj())

            if use_nykaa:
                async def _ny():
                    page = await create_stealth_page()
                    try:
                        return await scrape_nykaa_pw(page, query)
                    finally:
                        await page.close()
                tasks.append(_ny())

            if use_tatacliq:
                async def _ta():
                    page = await create_stealth_page()
                    try:
                        return await scrape_tatacliq_pw(page, query)
                    finally:
                        await page.close()
                tasks.append(_ta())

            # Run all concurrently — each uses a separate page in the SAME browser
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Build a map of platform->scraper_function for tracking
            platform_map = []
            if use_myntra:   platform_map.append("Myntra")
            if use_flipkart:  platform_map.append("Flipkart")
            if use_amazon:    platform_map.append("Amazon")
            if use_meesho:    platform_map.append("Meesho")
            if use_ajio:      platform_map.append("Ajio")
            if use_nykaa:     platform_map.append("Nykaa")
            if use_tatacliq:  platform_map.append("TataCLiQ")

            for i, result in enumerate(results):
                platform_name = platform_map[i] if i < len(platform_map) else f"Unknown_{i}"
                if isinstance(result, list) and len(result) > 0:
                    all_products.extend(result)
                elif isinstance(result, Exception):
                    print(f"[Scraper Error] {platform_name}: {result}")
                    # Inject "not available" placeholder for this platform
                    all_products.append({
                        "source": platform_name,
                        "title": f"Product not available on {platform_name}",
                        "price": None, "price_raw": None,
                        "rating": None, "link": None,
                        "unavailable": True,
                    })
                else:
                    # Empty list — platform returned 0 results
                    print(f"[Scraper] {platform_name}: 0 results")
                    all_products.append({
                        "source": platform_name,
                        "title": f"Product not available on {platform_name}",
                        "price": None, "price_raw": None,
                        "rating": None, "link": None,
                        "unavailable": True,
                    })

            await browser.close()
    except Exception as e:
        print(f"[FastScraper] Critical error: {e}")

    # Sort: real products by price ascending, unavailable at end
    all_products.sort(key=lambda x: (
        x.get("unavailable", False),
        x["price"] is None,
        x["price"] or 0
    ))

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
    """
    Try the fast Playwright scraper first.
    If it returns 0 results, fall back to the slower but proven Selenium scraper.
    """
    results = run_fast_sync(query, **kwargs)
    if results:
        return results

    print("[FastScraper] Playwright returned 0 results, falling back to Selenium scraper...")
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
            print("[Selenium Fallback] No products table exists.")
            return []
        conn.close()

        results = []
        for _, row in df.iterrows():
            results.append({
                "source": row.get("Source", "Unknown"),
                "title": row.get("Title", ""),
                "price_raw": str(row.get("Price", "")),
                "price": float(row["Price"]) if pd.notna(row.get("Price")) else None,
                "rating": str(row.get("Rating", "")) if pd.notna(row.get("Rating")) else None,
                "link": row.get("Link", ""),
            })

        results.sort(key=lambda x: (x["price"] is None, x["price"] or 0))
        print(f"[Selenium Fallback] Returned {len(results)} products from DB")
        return results
    except Exception as e:
        print(f"[Selenium Fallback] Error: {e}")
        return []
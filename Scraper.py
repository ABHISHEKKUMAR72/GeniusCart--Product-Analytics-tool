# scraper.py – optimized with multithreading, explicit waits & image-blocking
import time, sqlite3, pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options

DB_NAME = "ecommerce.db"
TABLE_NAME = "products"

def _init_driver(headless=True):
    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # --- Speed Optimizations ---
    # Block images, fonts & CSS to massively reduce page-load time
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--dns-prefetch-disable")
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2,
    })
    # Set page strategy to 'eager' – don't wait for all resources, just DOM
    options.page_load_strategy = 'eager'

    # Anti-Bot evasion
    from components.anti_bot import add_stealth
    options = add_stealth(options)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.set_page_load_timeout(20)
    return driver

# ---------- Amazon ----------
def scrape_amazon(query, max_pages=1, headless=True):
    driver = _init_driver(headless)
    wait = WebDriverWait(driver, 12)
    try:
        driver.get(f"https://www.amazon.in/s?k={query.replace(' ', '+')}")
        # Wait explicitly for product cards instead of sleeping
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@data-component-type='s-search-result']")))
    except TimeoutException:
        print(f"Amazon: Timed out waiting for results.")
        driver.quit()
        return pd.DataFrame()
    except Exception as e:
        print(f"Amazon page load timeout/error: {e}")
        driver.quit()
        return pd.DataFrame()

    products = []
    for page in range(max_pages):
        try:
            items = driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")
            if not items:
                print(f"Amazon: No items found on page {page}. Trying alternative selector...")
                items = driver.find_elements(By.CSS_SELECTOR, "div[data-component-type='s-search-result']")

            print(f"Amazon: Found {len(items)} items on page {page}")

            for item in items:
                try:
                    try:
                        title = item.find_element(By.XPATH, ".//h2//a//span").text.strip()
                    except:
                        try:
                            title = item.find_element(By.TAG_NAME, "h2").text.strip()
                        except:
                            continue

                    try:
                        price = item.find_element(By.CSS_SELECTOR, ".a-price-whole").text
                    except:
                        try:
                            price = item.find_element(By.CSS_SELECTOR, ".a-price span").text
                        except:
                            price = "N/A"

                    try:
                        rating = item.find_element(By.CSS_SELECTOR, ".a-icon-star-small span").text
                    except:
                        try:
                            rating = item.find_element(By.CSS_SELECTOR, ".a-icon-alt").get_attribute("innerHTML")
                        except:
                            rating = "N/A"

                    try:
                        link = item.find_element(By.XPATH, ".//h2//a").get_attribute("href")
                    except:
                        try:
                            link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                        except:
                            link = ""

                    if title and link:
                        if not link.startswith("http"):
                            link = "https://www.amazon.in" + link
                        products.append({"Source": "Amazon", "Title": title, "Price": price, "Rating": rating, "Link": link})
                except Exception:
                    continue

            # Navigate to next page using explicit wait
            if page < max_pages - 1:
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "a.s-pagination-next")
                    next_btn.click()
                    wait.until(EC.staleness_of(items[0]))
                except Exception:
                    break
        except Exception as e:
            print(f"Amazon error on page {page}: {e}")
            break

    print(f"Amazon: Scraped {len(products)} products total")
    driver.quit()
    return pd.DataFrame(products)

# ---------- Myntra ----------
def scrape_myntra(query, max_pages=1, headless=True):
    driver = _init_driver(headless)
    wait = WebDriverWait(driver, 12)
    try:
        driver.get(f"https://www.myntra.com/search?q={query.replace(' ', '+')}")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".productCardImg, .productCard, .productBase")))
    except TimeoutException:
        print(f"Myntra: Timed out waiting for results.")
        driver.quit()
        return pd.DataFrame()
    except Exception as e:
        print(f"Myntra page load timeout/error: {e}")
        driver.quit()
        return pd.DataFrame()

    products = []
    for page in range(max_pages):
        try:
            items = driver.find_elements(By.CSS_SELECTOR, ".productCardImg, .productCard, .productBase")
            if not items:
                items = driver.find_elements(By.XPATH, "//div[contains(@class, 'productCardImg')]")

            print(f"Myntra: Found {len(items)} items on page {page}")

            for item in items:
                try:
                    try:
                        brand = item.find_element(By.CSS_SELECTOR, ".productBrand, .productCardBrand").text
                    except:
                        brand = ""
                    try:
                        name = item.find_element(By.CSS_SELECTOR, ".productCardName, .productName").text
                    except:
                        name = ""
                    title = f"{brand} {name}".strip()
                    if not title:
                        try:
                            title = item.text.split('\n')[0]
                        except:
                            continue

                    try:
                        price = item.find_element(By.CSS_SELECTOR, ".productCardPrice, .productPrice, span.discountedPriceText").text
                    except:
                        price = "N/A"

                    try:
                        rating = item.find_element(By.CSS_SELECTOR, ".ratingCount, .productRating").text
                    except:
                        rating = "N/A"

                    try:
                        link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                    except:
                        link = ""

                    if title and link:
                        if not link.startswith("http"):
                            link = "https://www.myntra.com" + link
                        products.append({"Source": "Myntra", "Title": title, "Price": price, "Rating": rating, "Link": link})
                except Exception:
                    continue

            if page < max_pages - 1:
                try:
                    next_btn = driver.find_element(By.CSS_SELECTOR, "a.pagination-next, li.pagination-next a")
                    next_btn.click()
                    wait.until(EC.staleness_of(items[0]))
                except Exception:
                    break
        except Exception as e:
            print(f"Myntra error on page {page}: {e}")
            break

    print(f"Myntra: Scraped {len(products)} products total")
    driver.quit()
    return pd.DataFrame(products)

# ---------- Flipkart ----------
def scrape_flipkart(query, max_pages=1, headless=True):
    driver = _init_driver(headless)
    wait = WebDriverWait(driver, 12)
    try:
        driver.get(f"https://www.flipkart.com/search?q={query.replace(' ', '+')}")
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='KzDlHZ'] | //div[@data-id]")))
    except TimeoutException:
        print(f"Flipkart: Timed out waiting for results.")
        driver.quit()
        return pd.DataFrame()
    except Exception as e:
        print(f"Flipkart page load error: {e}")
        driver.quit()
        return pd.DataFrame()

    products = []
    for page in range(max_pages):
        try:
            items = driver.find_elements(By.XPATH, "//div[@class='KzDlHZ']")
            if not items:
                items = driver.find_elements(By.CSS_SELECTOR, "div[data-id], div.s1Q8DL")

            for item in items:
                try:
                    try:
                        title = item.find_element(By.XPATH, ".//a[contains(@class, 'IRpwTa')]").text
                        if not title:
                            title = item.find_element(By.XPATH, ".//span[@class='BvHyOb']").text
                    except:
                        title = ""

                    try:
                        price = item.find_element(By.XPATH, ".//div[@class='_30jeq3']").text
                    except:
                        try:
                            price = item.find_element(By.CSS_SELECTOR, "div._30jeq3, span._16Jk6d").text
                        except:
                            price = "N/A"

                    try:
                        link = item.find_element(By.XPATH, ".//a[@class='IRpwTa']").get_attribute("href")
                        if not link:
                            link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                    except:
                        link = ""

                    if title and link:
                        if not link.startswith("http"):
                            link = "https://www.flipkart.com" + link
                        products.append({"Source": "Flipkart", "Title": title, "Price": price, "Rating": "N/A", "Link": link})
                except Exception:
                    continue

            try:
                next_btn = driver.find_element(By.XPATH, "//a[@class='_1LKTO3']")
                if next_btn and page < max_pages - 1:
                    next_btn.click()
                    wait.until(EC.staleness_of(items[0]))
                else:
                    break
            except Exception:
                break
        except Exception as e:
            print(f"Flipkart scraping error on page {page}: {e}")
            break

    driver.quit()
    return pd.DataFrame(products)

# ---------- Ajio ----------
def scrape_ajio(query, max_pages=1, headless=True):
    driver = _init_driver(headless)
    wait = WebDriverWait(driver, 12)
    try:
        driver.get(f"https://www.ajio.com/search/?text={query.replace(' ', '+')}")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".item, .rilrtl-products-list__item")))
    except TimeoutException:
        print(f"Ajio: Timed out waiting for results.")
        driver.quit()
        return pd.DataFrame()
    except Exception as e:
        print(f"Ajio page load error: {e}")
        driver.quit()
        return pd.DataFrame()

    products = []
    for page in range(max_pages):
        items = driver.find_elements(By.CSS_SELECTOR, ".item, .rilrtl-products-list__item")
        for item in items:
            try:
                try: title = item.find_element(By.CSS_SELECTOR, ".nameCls, .name").text
                except: title = ""
                try: price = item.find_element(By.CSS_SELECTOR, ".price").text
                except: price = "N/A"
                try: link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                except: link = ""
                if title and link:
                    products.append({"Source": "Ajio", "Title": title, "Price": price, "Rating": "N/A", "Link": link})
            except: break
    driver.quit()
    return pd.DataFrame(products)

# ---------- Nykaa ----------
def scrape_nykaa(query, max_pages=1, headless=True):
    driver = _init_driver(headless)
    wait = WebDriverWait(driver, 12)
    try:
        driver.get(f"https://www.nykaa.com/search/result/?q={query.replace(' ', '+')}")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".product-list-box, .css-d5z3ro, .css-xrzmfa")))
    except TimeoutException:
        print(f"Nykaa: Timed out waiting for results.")
        driver.quit()
        return pd.DataFrame()
    except Exception as e:
        print(f"Nykaa page load error: {e}")
        driver.quit()
        return pd.DataFrame()

    products = []
    for page in range(max_pages):
        items = driver.find_elements(By.CSS_SELECTOR, ".product-list-box, .css-d5z3ro, .css-xrzmfa")
        for item in items:
            try:
                try: title = item.find_element(By.CSS_SELECTOR, ".css-xrzmfa, .title").text
                except: title = ""
                try: price = item.find_element(By.CSS_SELECTOR, ".css-111z9ua, .price").text
                except: price = "N/A"
                try: link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                except: link = ""
                if title and link:
                    products.append({"Source": "Nykaa", "Title": title, "Price": price, "Rating": "N/A", "Link": link})
            except: break
    driver.quit()
    return pd.DataFrame(products)

# ---------- TataCLiQ ----------
def scrape_tatacliq(query, max_pages=1, headless=True):
    driver = _init_driver(headless)
    wait = WebDriverWait(driver, 12)
    try:
        driver.get(f"https://www.tatacliq.com/search/?searchCategory=all&text={query.replace(' ', '+')}")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ProductModule__dummyDiv, .ProductDescription__dummyDiv")))
    except TimeoutException:
        print(f"TataCLiQ: Timed out waiting for results.")
        driver.quit()
        return pd.DataFrame()
    except Exception as e:
        print(f"TataCLiQ page load error: {e}")
        driver.quit()
        return pd.DataFrame()

    products = []
    for page in range(max_pages):
        items = driver.find_elements(By.CSS_SELECTOR, ".ProductModule__dummyDiv, .ProductDescription__dummyDiv")
        for item in items:
            try:
                try: title = item.find_element(By.CSS_SELECTOR, "h2, .ProductDescription__description").text
                except: title = ""
                try: price = item.find_element(By.CSS_SELECTOR, "h3, .ProductDescription__priceHolder").text
                except: price = "N/A"
                try: link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                except: link = ""
                if title and link:
                    products.append({"Source": "TataCLiQ", "Title": title, "Price": price, "Rating": "N/A", "Link": link})
            except: break
    driver.quit()
    return pd.DataFrame(products)

# ---------- Meesho ----------
def scrape_meesho(query, max_pages=1, headless=True):
    driver = _init_driver(headless)
    wait = WebDriverWait(driver, 12)
    try:
        driver.get(f"https://www.meesho.com/search?q={query.replace(' ', '+')}")
        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'ProductListingCard')] | //a[contains(@href, '/product/')]")))
    except TimeoutException:
        print(f"Meesho: Timed out waiting for results.")
        driver.quit()
        return pd.DataFrame()
    except Exception as e:
        print(f"Meesho page load error: {e}")
        driver.quit()
        return pd.DataFrame()

    products = []
    for page in range(max_pages):
        try:
            items = driver.find_elements(By.XPATH, "//div[contains(@class, 'ProductListingCard')]")
            if not items:
                items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")

            for item in items:
                try:
                    try:
                        title = item.find_element(By.XPATH, ".//h2 | .//p[contains(@class, 'ProductTitle')]").text
                        if not title:
                            title = item.find_element(By.TAG_NAME, "h2").text
                    except:
                        try:
                            title = item.text.split('\n')[0] if item.text else ""
                        except:
                            title = ""

                    try:
                        price = item.find_element(By.XPATH, ".//span[contains(@class, 'Product_price')]").text
                    except:
                        try:
                            price_elements = item.find_elements(By.XPATH, ".//span[contains(text(), '₹')]")
                            price = price_elements[0].text if price_elements else "N/A"
                        except:
                            price = "N/A"

                    try:
                        link = item.find_element(By.TAG_NAME, "a").get_attribute("href")
                        if not link:
                            link = item.get_attribute("href")
                    except:
                        link = ""

                    if title and link and "meesho.com" in str(link):
                        if not link.startswith("http"):
                            link = "https://www.meesho.com" + link
                        products.append({"Source": "Meesho", "Title": title, "Price": price, "Rating": "N/A", "Link": link})
                except Exception:
                    continue

            try:
                next_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Next')] | //a[contains(@class, 'next')]")
                if next_btn and page < max_pages - 1:
                    next_btn.click()
                    wait.until(EC.staleness_of(items[0]))
                else:
                    break
            except Exception:
                break
        except Exception as e:
            print(f"Meesho scraping error on page {page}: {e}")
            break

    driver.quit()
    return pd.DataFrame(products)

# ---------- DB Save & Clean ----------
def save_raw_to_db(df, reset=False, db_name=None):
    if df is None or df.empty: return
    _db = db_name or DB_NAME
    conn=sqlite3.connect(_db)
    if reset: conn.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
    df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    conn.close()

def clean_and_update_db(db_name=None):
    _db = db_name or DB_NAME
    conn=sqlite3.connect(_db)
    try: df=pd.read_sql(f"SELECT * FROM {TABLE_NAME}", conn)
    except: conn.close(); return
    if df.empty: conn.close(); return
    df["Price"]=df["Price"].astype(str).str.replace("₹","").str.replace(",","").str.extract(r"(\d+)")
    df["Price"]=pd.to_numeric(df["Price"],errors="coerce")
    df["Rating"]=pd.to_numeric(df["Rating"].astype(str).str.extract(r"(\d+(?:\.\d+)?)")[0],errors="coerce")
    df=df.dropna(subset=["Price"]); df["Price"]=df["Price"].astype(float)
    conn.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
    df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)
    
    # Save a copy to price_history table for historical tracking
    import datetime
    df["Timestamp"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    history_df = df[["Title", "Source", "Price", "Link", "Timestamp"]]
    history_df.to_sql("price_history", conn, if_exists="append", index=False)
    
    conn.close()

def run_scrapers_and_update_db(
    query, use_amazon=False, use_myntra=False, use_flipkart=False,
    use_ajio=False, use_nykaa=False, use_tatacliq=False, use_meesho=False,
    max_pages=1, headless=True, db_name=None
):
    """
    Runs all selected scrapers IN PARALLEL using ThreadPoolExecutor,
    then saves all results to the DB in one go (thread-safe).
    """
    # Build a list of (scraper_fn, site_name) to run in parallel
    tasks = []
    if use_amazon:   tasks.append((scrape_amazon,   "Amazon"))
    if use_myntra:   tasks.append((scrape_myntra,   "Myntra"))
    if use_flipkart: tasks.append((scrape_flipkart, "Flipkart"))
    if use_ajio:     tasks.append((scrape_ajio,     "Ajio"))
    if use_nykaa:    tasks.append((scrape_nykaa,    "Nykaa"))
    if use_tatacliq: tasks.append((scrape_tatacliq, "TataCLiQ"))
    if use_meesho:   tasks.append((scrape_meesho,   "Meesho"))

    all_dfs = []

    # Run all scrapers concurrently — max_workers capped at number of tasks
    with ThreadPoolExecutor(max_workers=min(len(tasks), 7)) as executor:
        future_to_site = {
            executor.submit(fn, query, max_pages, headless): name
            for fn, name in tasks
        }
        for future in as_completed(future_to_site):
            site = future_to_site[future]
            try:
                df = future.result()
                if df is not None and not df.empty:
                    print(f"[✓] {site}: {len(df)} products scraped")
                    all_dfs.append(df)
                else:
                    print(f"[!] {site}: No products found")
            except Exception as e:
                print(f"[✗] {site} scraper raised an exception: {e}")

    # Combine all results and save once — avoids SQLite threading lock issues
    _db = db_name or DB_NAME
    if all_dfs:
        combined = pd.concat(all_dfs, ignore_index=True)
        save_raw_to_db(combined, reset=True, db_name=_db)
        clean_and_update_db(db_name=_db)
        print(f"[DB] Saved {len(combined)} total products from {len(all_dfs)} sources to {_db}")
    else:
        print("[DB] No data to save.")
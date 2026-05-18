import time
from Scraper import run_scrapers_and_update_db, DB_NAME

QUERY_CACHE = {}

EXTENSION_DB_NAME = "ecommerce_extension.db"

def get_cached_or_scrape(query, use_amazon, use_myntra, use_flipkart, use_ajio, use_nykaa, use_tatacliq, use_meesho, max_pages, headless, origin=None):
    """
    Handles robust 10-minute in-memory caching to prevent redundant webdriver scraping tasks.
    When origin='extension', uses a separate database (ecommerce_extension.db).
    """
    global QUERY_CACHE
    
    # Determine the target database
    db_name = EXTENSION_DB_NAME if origin == "extension" else DB_NAME
    
    cache_key = f"{origin or 'web'}_{query}_{use_amazon}_{use_myntra}_{use_flipkart}_{use_ajio}_{use_nykaa}_{use_tatacliq}_{use_meesho}_{max_pages}"
    current_time = time.time()
    
    if cache_key in QUERY_CACHE and (current_time - QUERY_CACHE[cache_key]) < 600:
        print(f"⚡ Bypassing scraper! Returning cached results for: {query} (origin={origin or 'web'})")
        return True
    else:
        QUERY_CACHE[cache_key] = current_time
        # Synchronous blocking call to update DB
        run_scrapers_and_update_db(
            query, use_amazon, use_myntra, use_flipkart, use_ajio, use_nykaa, use_tatacliq, use_meesho,
            max_pages=max_pages, headless=headless, db_name=db_name
        )
        return False

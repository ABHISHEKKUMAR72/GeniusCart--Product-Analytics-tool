# 🛒 Product Analysis Tool

**Product Analysis Tool** is a Flask-based web application that allows users to search products across **Amazon, Flipkart, and Myntra**, analyze product details and pricing, store data in a **SQLite database**, and visualize insights with interactive plots.

The tool is designed to make **e-commerce product comparison simple, fast, and visually appealing**.

---

## ✨ Key Features

* 🔍 **Multi-Platform Search** → Search products on Amazon, Flipkart, Myntra, Meesho, Ajio, Nykaa, and TataCLiQ
* 🦅 **PriceHawk Chrome Extension** → A BuyHatke-style browser extension for instant price comparisons directly on product pages
* ⚡ **Fast Async Scraping** → Blazing fast parallel scraping using Playwright and httpx
* 🗂️ **Database Integration** → Save all results into SQLite for structured access
* 📊 **Visual Analytics** → Compare prices and analyze insights with interactive plots
* 📥 **Downloadable Reports** → Export results to CSV for further use
* 🎨 **Modern UI** → Built with TailwindCSS, responsive, and user-friendly (both Web App & Browser Extension)
* 🤖 **AI-Powered Recommendations** → KNN-based similar product suggestions based on price and rating
* 💬 **Sentiment Analysis** → Analyze product reviews and sentiment scores
* ⭐ **Value Scoring** → Intelligent product scoring based on specs-to-price ratio
* 🔔 **Price Alerts** → Set custom price alerts and get notified when prices drop
* 🔄 **Product Comparison** → Side-by-side comparison of selected products
* 🧹 **Data Cleaning** → Automatic outlier detection and data validation
* 🛡️ **Anti-Bot Protection** → Playwright resource blocking, user-agent randomization, and Selenium fallback.
* ⚙️ **Smart Caching** → 10-minute caching for API responses to ensure blazing fast searches

---

## 🎯 Advanced Features Explained

### 🤖 AI-Powered Recommendations (`recommendation_engine.py`)
Uses **K-Nearest Neighbors (KNN)** algorithm to find products similar to your selection based on:
- Price range
- Rating distribution
- Product characteristics
Helps users discover alternatives that match their budget and quality expectations.

### 💬 Sentiment Analysis (`sentiment.py`)
Analyzes **product reviews and ratings** to determine:
- Overall sentiment (Positive, Neutral, Negative)
- Consumer satisfaction levels
- Review credibility scores
Real-world implementation integrates with HuggingFace transformers for NLP analysis.

### ⭐ Value Scoring (`value_scorer.py`)
Intelligently scores products (0-100) by analyzing:
- **Specs extraction** → RAM, Storage, Battery, Screen size, etc.
- **Price-to-specs ratio** → Better value = higher score
- **Rating weight** → Quality assurance factor
- **Market positioning** → Competitive pricing comparison
Helps identify the best value products in your search results.

### 🔔 Price Alerts (`alerts.py`)
- **Set custom price targets** for any product
- **Email notifications** when prices drop below target
- **Persistent storage** in SQLite database
- **Track multiple products** simultaneously
Uses event-driven notifications to keep you informed of deals.

### 🔄 Product Comparison (`compare.py`)
- **Side-by-side comparison** of multiple products
- **Feature extraction** from titles and descriptions
- **Price trend analysis** for selected products
- **Visual charts** for easy decision-making
Simplifies multi-product evaluation.

### 🧹 Data Cleaning (`data_cleaner.py`)
- **Outlier detection** → Removes suspiciously priced items
- **Data validation** → Ensures price and rating accuracy
- **Missing value handling** → Graceful degradation
- **Duplicate removal** → Prevents inflated search results
Ensures high data quality for analysis.

### 🛡️ Anti-Bot Protection (`anti_bot.py`)
- **Adaptive scraping** → Changes user agents & headers
- **Request throttling** → Avoids detection by rate-limiting
- **Proxy rotation** (future enhancement)
- **Session management** → Appears as legitimate user traffic
Maintains scraping stability while respecting platform policies.

### ⚙️ Smart Caching (`caching_service.py`)
- **In-memory caching** of recent search results
- **Database query optimization** → Faster data retrieval
- **TTL-based expiration** → Fresh data after timeout
- **Performance metrics** → Tracks cache hit/miss rates
Improves user experience with faster load times.

### 🦅 PriceHawk Chrome Extension (`extension/`)
- **BuyHatke-Style Utility:** Reads the product you are currently viewing and fetches lowest prices across the internet.
- **Manifest V3:** Modern Chrome extension architecture with strict security.
- **REST API Driven:** Calls Python Flask backend to offload all heavy scraping work.
- **Premium UI:** Designed with dark-mode aesthetic, micro-animations, and visual product cards.

### ⚡ Fast Async Scraper (`fast_scraper.py`)
- **Parallel Playwright Instances:** Uses a single browser session to query up to 7 platforms concurrently.
- **Blazing Fast:** Drops heavy resources (images, fonts, stylesheets) avoiding rendering delays.
- **Automatic Fallback:** Seamlessly defaults to the robust Selenium scraper if bot defenses engage.

---

```
product-analysis-tool/
│
├── app.py                          # Flask entry point & main routes
├── fast_scraper.py                 # Async Playwright/httpx scraper
├── Scraper.py                      # Core Selenium scraping logic (Amazon, Flipkart, etc.)
├── test_scrape.py                  # Unit tests for scraper
├── requirements.txt                # Python dependencies
│
├── extension/                      # PriceHawk Chrome Extension
│   ├── manifest.json               # Chrome Manifest V3 Config
│   ├── popup.html                  # Extension UI shell
│   ├── popup.js                    # Extension logic & API calls
│   ├── popup.css                   # Dark mode styling & animations
│   ├── content.js                  # DOM reader for product pages
│   ├── background.js               # Service worker for extension badge
│   └── icons/                      # Extension logo assets
│
├── components/                     # Advanced features & utilities
│   ├── recommendation_engine.py    # KNN-based product recommendations
│   ├── sentiment.py                # NLP sentiment analysis for reviews
│   ├── value_scorer.py             # Dynamic value scoring (specs-to-price ratio)
│   ├── alerts.py                   # Price alert management
│   ├── compare.py                  # Product comparison logic
│   ├── data_cleaner.py             # Outlier detection & data validation
│   ├── anti_bot.py                 # Bot detection avoidance
│   ├── caching_service.py          # Performance caching layer
│   └── __init__.py
│
├── templates/                      # HTML Templates
│   ├── home.html                   # Home/Search page
│   ├── products.html               # Products results table
│   ├── visuals.html                # Visualization & analytics page
│   ├── history.html                # Product history & trends
│   ├── compare.html                # Product comparison view
│   └── base.html                   # Base template (if exists)
│
├── static/                         # Static assets
│   └── images/                     # Image assets
│
├── frontend/                       # React/Vite frontend (optional)
│   ├── src/
│   ├── package.json
│   └── vite.config.js
│
├── backend/                        # Additional backend routes
│   ├── routes/
│   └── services/
│
├── README.md                       # Documentation
├── LICENSE                         # Open-source license
└── Procfile                        # Deployment configuration for Render
```

---

## 🛠️ Tech Stack

* **Backend:** Flask (Python)
* **REST API:** JSON Endpoints, Flask-CORS
* **Browser Extension:** Manifest V3, HTML5, Vanilla JS, CSS3
* **Database:** SQLite3
* **Frontend Web:** HTML, TailwindCSS, JavaScript
* **Scraping (Fast):** Playwright Async API, httpx
* **Scraping (Standard):** Selenium, Webdriver Manager
* **Data Processing:** Pandas, NumPy
* **Visualization:** Matplotlib, Seaborn
* **Machine Learning:** Scikit-learn (KNN for recommendations)
* **Additional Frameworks:** BeautifulSoup4, lxml, Gunicorn

---

## 🌐 Available Routes & API Endpoints

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET, POST | Home page - Search products via Web Interface |
| `/products` | GET | Display all successfully scraped products |
| `/visuals` | GET | Show analytics & price comparison charts |
| `/history/{link}` | GET | View historical price trends for a product |
| `/alert` | POST | Set a price alert for a product |
| `/compare` | GET | Compare selected products side-by-side |
| `/api/search` | GET | **[Extension]** Scrapes and returns prices for a product in JSON format |
| `/api/status` | GET | **[Extension]** Health check endpoint to verify backend status |

---

## 🚀 Getting Started

Follow these steps to run the project locally:

### 1️⃣ Clone the Repository

```bash
git clone https://github.com/pranayguptag/product-analysis-tool.git
cd product-analysis-tool
```

### 2️⃣ Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
venv\Scripts\activate      # Windows
```

### 3️⃣ Install Dependencies & Browser Dependencies

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

### 4️⃣ Run Locally

```bash
python app.py
```

App will be live at → `http://127.0.0.1:5000`

---

## ⚙️ Configuration

### Environment Variables (optional)
Create a `.env` file in the project root:

```env
FLASK_ENV=development
FLASK_DEBUG=True
DATABASE_URL=sqlite:///products.db
CACHE_TTL=3600
MAX_RESULTS=100
```

### Running with Gunicorn (Production)

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

---

## 📦 Dependencies Summary

All dependencies are listed in `requirements.txt`:
- **Flask 3.0.3** - Web framework
- **Pandas 2.3.3** - Data manipulation
- **Selenium 4.25.0** - Web scraping automation
- **BeautifulSoup4 4.12.3** - HTML parsing
- **Scikit-learn** - Machine learning (KNN recommendations)
- **Matplotlib & Seaborn** - Data visualization
- **Requests 2.32.3** - HTTP library

Install all at once: `pip install -r requirements.txt`

---

## 🖼️ Screenshots

### 🔎 Home Page

Users can search and select platforms (Amazon, Myntra, Flipkart, Ajio, Nykaa, Tatacliq, Meesho)
![Home Page](https://github.com/pranayguptag/GeniusCart--Product-Analytics-tool/blob/main/Media/Home-Page-new.png)

### 📋 Product Results

Clean tabular view of products scraped from platforms
![Products](https://github.com/pranayguptag/GeniusCart--Product-Analytics-tool/blob/main/Media/Scraped-Data.png)
![Products](https://github.com/pranayguptag/GeniusCart--Product-Analytics-tool/blob/main/Media/Extension.png)

### 📊 Visual Analysis

Compare product prices and insights visually
![Visuals](https://github.com/pranayguptag/GeniusCart--Product-Analytics-tool/blob/main/Media/Scraped-Data.png)

### 📊 Product Comparison

![Comparison](https://github.com/pranayguptag/GeniusCart--Product-Analytics-tool/blob/main/Media/Comparison.png)


---

## 💡 Usage Guide

### 1. **Search Products**
- Navigate to the home page (`/`)
- Enter a product name (e.g., "iPhone 15")
- Select platforms: Amazon, Flipkart, Myntra
- Click "Search" to scrape products

### 2. **View Results**
- Check the `/products` page for all scraped items
- View product details: name, price, rating, link
- Download results as CSV for offline analysis

### 3. **Analyze Trends**
- Visit `/visuals` for interactive price charts
- Compare products across platforms
- View sentiment scores and value ratings

### 4. **Set Price Alerts**
- Click "Set Alert" on any product
- Enter target price and email
- Get notified when price drops

### 5. **Compare Products**
- Use `/compare` to view side-by-side specifications
- View price history and trends
- Identify the best value option

### 6. **Get Recommendations**
- System automatically suggests similar products
- Based on your selected item's price & rating
- Powered by AI/ML recommendations

### 7. **PriceHawk Chrome Extension**
We've added a BuyHatke-inspired Chrome Extension to get instant price comparison across sites while you shop online!

*Start your Flask server first:* `python app.py`

**Install the Extension:**
1. Open Google Chrome and type `chrome://extensions/` in the URL bar.
2. Toggle **Developer mode** ON (top right corner).
3. Click on **Load unpacked**.
4. Select the `extension/` folder located inside the `product-analysis-tool` directory.
5. Pin the "PriceHawk" extension to your Chrome toolbar.
6. Visit Amazon, Flipkart, etc. Navigate to a product page and click PriceHawk to auto-fetch prices!

---

## 🐛 Troubleshooting

### Issue: Only getting results from Amazon and Myntra, not Flipkart/Meesho
**Root Cause:** Website selectors change frequently. The scrapers use CSS/XPath selectors that may become outdated.

**Solution:** 
1. **Ensure you're using the latest version** of the code with improved selectors (check Scraper.py was updated)
2. **Check your internet connection** - some sites block automated requests
3. **Try searching for simpler queries** first (e.g., "phone" instead of "latest iPhone 15 pro")
4. **Increase wait time:** Edit `Scraper.py` and change `time.sleep(3)` to `time.sleep(5)` for slower connections
5. **Check browser compatibility:** Install latest ChromeDriver
   ```bash
   python -m webdriver_manager chrome
   ```

**If still getting blank results for specific platforms:**
- Open browser in non-headless mode to debug: Change `headless=True` to `headless=False` in `app.py` line 75
- Watch the browser and note any errors that appear
- This helps identify if the website structure changed

### Issue: "selenium.common.exceptions.WebDriverException"
**Solution:** Update webdriver-manager  
```bash
pip install --upgrade webdriver-manager
python -m webdriver_manager chrome
```

### Issue: "ModuleNotFoundError: No module named 'sklearn'"
**Solution:** Install scikit-learn  
```bash
pip install scikit-learn
```

### Issue: Port 5000 already in use
**Solution:** Change the port in `app.py`  
```python
if __name__ == "__main__":
    app.run(debug=True, port=8000)  # Change to any free port
```

### Issue: Scraper is slow or getting blocked
**Solution:** The anti-bot module adds delays and changes headers automatically. Check:
- Internet connection speed
- Website's robots.txt policies
- Try searching for simpler/fewer keywords
- Increase the delay in `components/anti_bot.py` if sites are blocking you

### Issue: Compare feature not showing products from specific platforms
**Solution:**
1. Ensure you've selected multiple platforms in the search form
2. Wait for all scrapers to complete (check console output for which platform is running)
3. The compare feature uses KNN algorithm - it finds similar products based on price & rating from ALL selected platforms
4. If a platform didn't return enough results, comparison will be limited to available products

---

## � Future Roadmap

- [ ] **Mobile App** - React Native/Flutter mobile version
- [ ] **Real-time Notifications** - Push notifications for price drops
- [ ] **Advanced Filters** - Filter by specifications, reviews, brand
- [ ] **Multi-language Support** - Internationalization (i18n)
- [ ] **Competitor Analysis** - Track competitor pricing
- [ ] **API for Third-party** - RESTful API for integrations
- [ ] **Cloud Deployment** - AWS/Azure/GCP templates
- [ ] **Database Analytics** - Advanced BI dashboards
- [ ] **Proxy Integration** - Rotating proxy support
- [ ] **Review Aggregation** - Collect reviews from multiple sources

---

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

---

## 👨‍💻 Author

**Pranay Gupta** - [GitHub](https://github.com/pranayguptag)

---


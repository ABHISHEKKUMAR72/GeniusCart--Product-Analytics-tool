/**
 * popup.js — PriceHawk Chrome Extension popup logic.
 * Reads product title from content.js via chrome.storage.session,
 * calls the Flask API at localhost:5000/api/search, renders results.
 * 
 * ENHANCEMENTS:
 * - Popup state persistence: results survive popup close/reopen
 * - Missing platform display: shows "Product not available" for empty platforms
 * - Robust search history with recommendation data
 * - All 7 platforms enabled by default
 */

const API_BASE = "http://localhost:5000";
const SOURCE_COLORS = {
  Amazon:   "#FF9900",
  Flipkart: "#2874f0",
  Myntra:   "#ff3f6c",
  Meesho:   "#f43397",
  Nykaa:    "#fc2779",
  Ajio:     "#000000",
  TataCLiQ: "#593fb6",
};
const SOURCE_ICONS = {
  Amazon:   "🛒",
  Flipkart: "🛍",
  Myntra:   "👗",
  Meesho:   "📦",
  Nykaa:    "💄",
  Ajio:     "✨",
  TataCLiQ: "🏷",
};

let _allResults = [];
let _activeFilter = "All";
let _searchHistory = [];
let _lastQuery = "";

// ─── Restore persisted state on startup ──────────────────────────────────────
chrome.storage.local.get(['searchHistory', 'popupState'], (result) => {
  if (result.searchHistory) {
    _searchHistory = result.searchHistory;
  }
  // Restore previous popup state so clicking away doesn't lose results
  if (result.popupState && result.popupState.results && result.popupState.results.length > 0) {
    _lastQuery = result.popupState.query || "";
    _activeFilter = result.popupState.activeFilter || "All";
    $searchInput.value = _lastQuery;
    $detectedLabel.textContent = "Last search: " + truncate(_lastQuery, 40);
    renderResults(result.popupState.results, _lastQuery, true);
  }
});

// ─── DOM refs ────────────────────────────────────────────────────────────────
const $searchInput    = document.getElementById("searchInput");
const $searchBtn      = document.getElementById("searchBtn");
const $detectedLabel  = document.getElementById("detectedLabel");
const $stateLoading   = document.getElementById("stateLoading");
const $stateError     = document.getElementById("stateError");
const $stateEmpty     = document.getElementById("stateEmpty");
const $resultsSection = document.getElementById("resultsSection");
const $serverStatus   = document.getElementById("serverStatus");
const $statusText     = document.getElementById("statusText");
const $retryBtn       = document.getElementById("retryBtn");
const $productList    = document.getElementById("productList");
const $filterTabs     = document.getElementById("filterTabs");
const $bestDeal       = document.getElementById("bestDealBanner");
const $bestSource     = document.getElementById("bestSource");
const $bestTitle      = document.getElementById("bestTitle");
const $bestPrice      = document.getElementById("bestPrice");
const $bestLink       = document.getElementById("bestLink");
const $statCount      = document.getElementById("statCount");
const $statSites      = document.getElementById("statSites");
const $statCheapest   = document.getElementById("statCheapest");
const $statHighest    = document.getElementById("statHighest");
const $resultsFooter  = document.getElementById("resultsFooter");

// ─── Utilities ───────────────────────────────────────────────────────────────
function showState(name) {
  $stateLoading.style.display   = name === "loading"  ? "flex"  : "none";
  $stateError.style.display     = name === "error"    ? "flex"  : "none";
  $stateEmpty.style.display     = name === "empty"    ? "flex"  : "none";
  $resultsSection.style.display = name === "results"  ? "block" : "none";
}

function formatPrice(price) {
  if (!price && price !== 0) return "N/A";
  return "₹" + Number(price).toLocaleString("en-IN");
}

function truncate(str, n) {
  return str && str.length > n ? str.slice(0, n - 1) + "…" : str;
}

// ─── Server health check ─────────────────────────────────────────────────────
async function checkServer() {
  try {
    const r = await fetch(`${API_BASE}/api/status`, { signal: AbortSignal.timeout(2000) });
    if (r.ok) {
      $serverStatus.classList.add("online");
      $statusText.textContent = "Server online";
      return true;
    }
  } catch (_) {}
  $serverStatus.classList.remove("online");
  $statusText.textContent = "Server offline";
  return false;
}

// ─── Persist popup state ─────────────────────────────────────────────────────
function savePopupState() {
  chrome.storage.local.set({
    popupState: {
      query: _lastQuery,
      results: _allResults,
      activeFilter: _activeFilter,
      timestamp: Date.now(),
    }
  });
}

// ─── Render results ───────────────────────────────────────────────────────────
function renderResults(results, query, fromCache) {
  _allResults = results;
  _lastQuery = query;
  if (!results.length) { showState("empty"); return; }

  // Separate real products from unavailable placeholders
  const realProducts = results.filter(r => !r.unavailable);
  const unavailablePlatforms = results.filter(r => r.unavailable);

  // Best deal (from real products only)
  const priced = realProducts.filter(r => r.price);
  if (priced.length) {
    const best = priced[0];
    $bestDeal.style.display = "flex";
    $bestSource.textContent = (SOURCE_ICONS[best.source] || "🛒") + " " + best.source;
    $bestSource.style.color = SOURCE_COLORS[best.source] || "#6C63FF";
    $bestTitle.textContent  = truncate(best.title, 60);
    $bestPrice.textContent  = formatPrice(best.price);
    $bestLink.href          = best.link;
    
    // Update history with the best price
    addToHistory(query, best.price, results);
  } else {
    $bestDeal.style.display = "none";
  }

  // Stats (count only real products)
  const sources = [...new Set(realProducts.map(r => r.source))];
  $statCount.textContent = realProducts.length;
  $statSites.textContent = sources.length;
  if (priced.length) {
    $statCheapest.textContent = "₹" + Math.min(...priced.map(p => p.price)).toLocaleString();
    $statHighest.textContent  = "₹" + Math.max(...priced.map(p => p.price)).toLocaleString();
  }

  // Filter tabs
  $filterTabs.innerHTML = "";
  const allSources = [...new Set(results.map(r => r.source))];
  ["All", ...allSources].forEach(s => {
    const btn = document.createElement("button");
    btn.className = "filter-tab" + (s === _activeFilter ? " active" : "");
    btn.textContent = s;
    btn.onclick = () => {
      _activeFilter = s;
      renderList();
      [...$filterTabs.children].forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      savePopupState();
    };
    $filterTabs.appendChild(btn);
  });

  renderList();
  showState("results");
  
  $resultsFooter.textContent = fromCache ? "⚡ Loaded from cache" : `Found ${realProducts.length} products`;

  // Persist state
  savePopupState();
}

function renderList() {
  const filtered = _activeFilter === "All" 
    ? _allResults 
    : _allResults.filter(r => r.source === _activeFilter);

  $productList.innerHTML = filtered.map(r => {
    // Handle "unavailable" placeholder items
    if (r.unavailable) {
      return `
        <div class="product-card unavailable-card">
          <div class="pc-source" style="color: ${SOURCE_COLORS[r.source] || '#999'}">
            ${SOURCE_ICONS[r.source] || "🛒"} ${r.source}
          </div>
          <div class="pc-content">
            <div class="pc-title pc-unavailable">⚠️ ${r.title}</div>
            <div class="pc-row">
              <div class="pc-price pc-na">Not Available</div>
            </div>
          </div>
        </div>
      `;
    }

    // Normal product card
    return `
      <div class="product-card">
        <div class="pc-source" style="color: ${SOURCE_COLORS[r.source]}">
          ${SOURCE_ICONS[r.source] || "🛒"} ${r.source}
        </div>
        <div class="pc-content">
          <div class="pc-title" title="${r.title}">${truncate(r.title, 65)}</div>
          <div class="pc-row">
            <div class="pc-price">${formatPrice(r.price)}</div>
            ${r.rating ? `<div class="pc-rating">⭐ ${r.rating}</div>` : ''}
            <div class="pc-actions">
              <button class="pc-hist-btn" onclick="showPriceHistory('${r.title.replace(/'/g, "\\'")}')" title="Price Trend">📈</button>
              <a href="${r.link}" target="_blank" class="pc-link">Buy</a>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join("");
}

async function showPriceHistory(title) {
  try {
    const resp = await fetch(`${API_BASE}/api/price-history?title=${encodeURIComponent(title)}`);
    const data = await resp.json();
    const history = data.history || [];
    
    if (history.length < 2) {
      alert("Not enough history data for this product yet.");
      return;
    }
    
    const last = history[history.length - 1].Price;
    const prev = history[history.length - 2].Price;
    const diff = last - prev;
    const status = diff < 0 ? "📉 Price Dropped!" : (diff > 0 ? "📈 Price Increased" : "⚖️ Price Stable");
    
    alert(`Price Trend for: ${title}\n\n${status}\nLatest: ₹${last}\nPrevious: ₹${prev}`);
  } catch (err) {
    alert("Could not load history.");
  }
}

function addToHistory(query, price, results) {
  const timestamp = Date.now();
  
  // Gather platform-level summary for recommendation context
  const platformSummary = {};
  if (results) {
    results.forEach(r => {
      if (!r.unavailable && r.price) {
        if (!platformSummary[r.source]) {
          platformSummary[r.source] = { count: 0, minPrice: Infinity, maxPrice: 0 };
        }
        platformSummary[r.source].count++;
        platformSummary[r.source].minPrice = Math.min(platformSummary[r.source].minPrice, r.price);
        platformSummary[r.source].maxPrice = Math.max(platformSummary[r.source].maxPrice, r.price);
      }
    });
  }

  const entry = {
    query,
    price,
    timestamp,
    totalResults: results ? results.filter(r => !r.unavailable).length : 0,
    platformSummary,
  };
  
  // Keep last 20 unique searches (increased from 10)
  _searchHistory = _searchHistory.filter(h => h.query.toLowerCase() !== query.toLowerCase());
  _searchHistory.unshift(entry);
  _searchHistory = _searchHistory.slice(0, 20);
  
  chrome.storage.local.set({ searchHistory: _searchHistory });
}

// ─── Search action ───────────────────────────────────────────────────────────
async function performSearch(q) {
  if (!q || q.length < 3) return;
  showState("loading");
  
  const isOnline = await checkServer();
  if (!isOnline) { showState("error"); return; }

  try {
    // Enable ALL platforms and pass origin=extension
    const url = `${API_BASE}/api/search?q=${encodeURIComponent(q)}&amazon=true&flipkart=true&myntra=true&ajio=true&nykaa=true&tatacliq=true&meesho=true&origin=extension`;
    const resp = await fetch(url);
    if (!resp.ok) throw new Error("Search failed");
    
    const data = await resp.json();
    renderResults(data.results || [], q, data.from_cache);
  } catch (err) {
    console.error(err);
    showState("error");
  }
}

// ─── Events ──────────────────────────────────────────────────────────────────
$searchBtn.onclick = () => performSearch($searchInput.value.trim());
$searchInput.onkeydown = (e) => { if (e.key === "Enter") performSearch($searchInput.value.trim()); };
$retryBtn.onclick = () => performSearch($searchInput.value.trim());

// Auto-detect from storage
chrome.storage.session.get(["detectedProduct"], (res) => {
  if (res.detectedProduct) {
    $searchInput.value = res.detectedProduct;
    $detectedLabel.textContent = "Detected: " + truncate(res.detectedProduct, 40);
    performSearch(res.detectedProduct);
  }
});

// Initial health check
checkServer();

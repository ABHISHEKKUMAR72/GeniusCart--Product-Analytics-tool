/**
 * content.js — Injected into supported e-commerce pages.
 * Reads the product title from the current page DOM and stores it
 * in chrome.storage.session so the popup can retrieve it instantly.
 */

(function () {
  const hostname = window.location.hostname;

  function extractTitle() {
    // Amazon
    if (hostname.includes("amazon")) {
      const el =
        document.getElementById("productTitle") ||
        document.querySelector("h1.a-size-large") ||
        document.querySelector("span#productTitle");
      if (el) return el.innerText.trim();
    }

    // Flipkart
    if (hostname.includes("flipkart")) {
      const el =
        document.querySelector("h1.yhB1nd") ||
        document.querySelector("span.B_NuCI") ||
        document.querySelector("h1._6EBuvT") ||
        document.querySelector("div._4rR01T");
      if (el) return el.innerText.trim();
    }

    // Myntra
    if (hostname.includes("myntra")) {
      const el =
        document.querySelector("h1.pdp-title") ||
        document.querySelector("h1.pdp-name") ||
        document.querySelector("h1");
      if (el) return el.innerText.trim();
    }

    // Meesho
    if (hostname.includes("meesho")) {
      const el =
        document.querySelector("p[class*='ProductTitle']") ||
        document.querySelector("h1") ||
        document.querySelector("p.sc-eDvSVe");
      if (el) return el.innerText.trim();
    }

    // Ajio
    if (hostname.includes("ajio")) {
      const el =
        document.querySelector("h1.prod-name") ||
        document.querySelector("h1.fn-label") ||
        document.querySelector("h1");
      if (el) return el.innerText.trim();
    }

    // Nykaa
    if (hostname.includes("nykaa")) {
      const el =
        document.querySelector("h1[class*='css']") ||
        document.querySelector("h1");
      if (el) return el.innerText.trim();
    }

    // TataCLiQ
    if (hostname.includes("tatacliq")) {
      const el =
        document.querySelector("h1[class*='pdp']") ||
        document.querySelector("h1");
      if (el) return el.innerText.trim();
    }

    // Generic fallback — use page title
    return document.title
      .replace(/ - Amazon\.in$| - Flipkart| - Myntra| : Online.*$/i, "")
      .trim();
  }

  const title = extractTitle();
  if (title) {
    chrome.storage.session.set({ productTitle: title, pageUrl: window.location.href });
    console.log("[GeniusCart] Detected product:", title);
  }
})();

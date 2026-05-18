/**
 * background.js — Service worker for GeniusCart extension.
 * Handles badge updates and communication between content script and popup.
 */

// Show a badge on the icon when on a supported product page
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === "complete" && tab.url) {
    const supportedSites = [
      "amazon.in", "amazon.com",
      "flipkart.com", "myntra.com",
      "meesho.com", "ajio.com",
      "nykaa.com", "tatacliq.com"
    ];
    const isSupported = supportedSites.some(site => tab.url.includes(site));
    if (isSupported) {
      chrome.action.setBadgeText({ text: "₹", tabId });
      chrome.action.setBadgeBackgroundColor({ color: "#6C63FF", tabId });
    } else {
      chrome.action.setBadgeText({ text: "", tabId });
    }
  }
});

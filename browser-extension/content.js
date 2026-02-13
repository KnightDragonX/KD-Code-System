// content.js - Content script for KD-Code extension

// Listen for messages from the popup or background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fillText') {
    // Fill the active text field with the selected text
    const activeElement = document.activeElement;
    if (activeElement && (activeElement.tagName === 'INPUT' || activeElement.tagName === 'TEXTAREA')) {
      activeElement.value = request.text;
    }
  }
  
  if (request.action === 'extractPageContent') {
    // Extract text content from the current page
    const pageText = document.body.innerText.substring(0, 1000); // Limit to first 1000 characters
    sendResponse({ text: pageText });
  }
});

// Add a context menu option to page elements
document.addEventListener('contextmenu', (event) => {
  // You can customize this to add context menu options to specific elements
});

// Function to extract selected text
function getSelectedText() {
  return window.getSelection().toString();
}

// Function to extract URL of current page
function getCurrentUrl() {
  return window.location.href;
}

// Expose functions to global scope for use in page context
window.KDCodeExtension = {
  getSelectedText: getSelectedText,
  getCurrentUrl: getCurrentUrl
};
// background.js - Background script for KD-Code extension

// Listen for extension icon clicks
chrome.action.onClicked.addListener((tab) => {
  // Open the extension popup
  chrome.action.openPopup();
});

// Listen for messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'generateKdCode') {
    // Forward the request to the KD-Code API
    fetch('http://localhost:5000/api/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ text: request.text })
    })
    .then(response => response.json())
    .then(data => {
      sendResponse({ success: true, data: data });
    })
    .catch(error => {
      console.error('Error generating KD-Code:', error);
      sendResponse({ success: false, error: error.message });
    });
    
    // Return true to indicate we wish to send a response asynchronously
    return true;
  }
  
  if (request.action === 'scanKdCode') {
    // Handle scan request
    // This would typically involve capturing the current tab and processing it
    // For now, we'll just return a placeholder response
    sendResponse({ success: false, error: 'Scanning not yet implemented' });
  }
});

// Set up context menu
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'generate-kd-code',
    title: 'Generate KD-Code from selection',
    contexts: ['selection']
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'generate-kd-code') {
    // Create a new tab with the extension popup and pre-fill with selected text
    chrome.tabs.create({
      url: chrome.runtime.getURL('popup.html'),
      active: true
    }, (newTab) => {
      // Send the selected text to the popup
      setTimeout(() => {
        chrome.tabs.sendMessage(newTab.id, {
          action: 'fillText',
          text: info.selectionText
        });
      }, 500);
    });
  }
});
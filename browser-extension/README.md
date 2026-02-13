# KD-Code Browser Extension

A browser extension for generating and scanning KD-Codes directly from your browser.

## Overview

This browser extension provides convenient access to KD-Code functionality right from your browser. It allows users to:

- Generate KD-Codes from selected text or entered text
- Access KD-Code functionality from any webpage
- Quickly generate codes without leaving the current page

## Features

- **Context Menu Integration**: Right-click on selected text to generate a KD-Code
- **Popup Interface**: Easy-to-use popup for generating codes
- **Page Integration**: Works on any webpage to extract content

## Installation

### For Chrome/Chromium browsers:

1. Open Chrome and navigate to `chrome://extensions`
2. Enable "Developer mode" in the top right corner
3. Click "Load unpacked" and select the `browser-extension` folder
4. The extension should now appear in your extensions toolbar

### For Firefox:

1. Open Firefox and navigate to `about:debugging`
2. Click "This Firefox" (or "Extensions" in older versions)
3. Click "Load Temporary Add-on"
4. Select the `manifest.json` file from the `browser-extension` folder

## Usage

1. Click the KD-Code extension icon in your browser toolbar
2. Enter text in the input field or paste from clipboard
3. Click "Generate KD-Code" to create the code
4. The generated KD-Code will appear in the popup

### Context Menu

- Select text on any webpage
- Right-click and choose "Generate KD-Code from selection"
- The extension will open with the selected text pre-filled

## API Integration

The extension connects to the KD-Code web service API running locally at `http://localhost:5000`. Make sure the KD-Code server is running for full functionality.

## Development

To modify the extension:

1. Make changes to the source files
2. Go to `chrome://extensions` and click "Reload" on the KD-Code extension

## Security Notes

- The extension requires permissions to access active tabs and storage
- All data is processed through the local KD-Code API
- No data is sent to external servers

## License

MIT License
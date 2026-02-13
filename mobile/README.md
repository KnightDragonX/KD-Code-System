# KD-Code Mobile Application

A React Native application for generating and scanning KD-Codes on mobile devices.

## Overview

This mobile application provides the same functionality as the web application but optimized for mobile devices. It allows users to:

- Generate KD-Codes from text/URLs
- Scan KD-Codes using the device camera
- Save and share generated codes

## Prerequisites

- Node.js (v16 or higher)
- React Native CLI or Expo CLI
- For iOS: Xcode and iOS Simulator
- For Android: Android Studio and Android Virtual Device

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd KD-Code-System/mobile
```

2. Install dependencies:
```bash
npm install
```

3. For iOS, install pods:
```bash
cd ios && pod install && cd ..
```

## Running the Application

### Android
```bash
npm run android
```

### iOS
```bash
npm run ios
```

## Features

- **KD-Code Generation**: Create KD-Codes from any text or URL
- **Camera Scanner**: Use device camera to scan KD-Codes
- **Offline Capability**: Basic functionality works offline
- **Cross-Platform**: Works on both iOS and Android

## API Integration

The mobile app connects to the KD-Code web service API for advanced features:

- Code generation
- Complex decoding
- Analytics

## Contributing

See the main project README for contribution guidelines.

## License

MIT License
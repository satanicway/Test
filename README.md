# D&D Companion App

This project is now a **React Native** application targeting both Android and iOS.
It provides quick adventure hooks and monster lookups for your D&D 5e games.

## Features

* **Home Screen** with buttons for `Contracts`, `Journey`, `Mystery`, `Monster`, and `Search`.
* Each button opens a dedicated screen displaying random data from local JSON files or a searchable list of monsters.
* Basic stack navigation and simple placeholder components.

## Development

1. Install [Node.js](https://nodejs.org/) and `npm`.
2. Install the React Native CLI dependencies for your platform (Android Studio, Xcode, etc.).
3. Clone this repository and run `npm install` inside `dndCompanion`.

### Running on Android

```bash
cd dndCompanion
npm run android
```

### Running on iOS

```bash
cd dndCompanion
npm run ios
```

### Building an APK

```bash
cd dndCompanion
npm run android --variant=release
```

### Building an IPA

```bash
cd dndCompanion
npm run ios --configuration Release
```

The React Native CLI will start the Metro bundler and deploy the app to the
connected simulator or device.

# Tedile Mobile Wrapper

This folder wraps the Tedile Flask web app into native iOS and Android apps
using [Capacitor](https://capacitorjs.com/). During development the app loads
the live Flask server (`capacitor.config.json` -> `server.url`); for a
production build, point it at the deployed Tedile URL (e.g. your Render URL)
or bundle a static build into `www/`.

## First-time setup

```bash
cd mobile
npm install
npx cap add android
npx cap add ios
```

This generates the `android/` and `ios/` native projects (gitignored build
output only — the generated project folders are checked in so Xcode/Android
Studio can open them directly as generated native projects).

## Point at your backend

Edit `capacitor.config.json`:

- Android emulator: `http://10.0.2.2:<port>`
- iOS simulator / physical device on same network: `http://<your-lan-ip>:<port>`
- Production: `https://<your-render-service>.onrender.com`

Then re-sync:

```bash
npx cap sync
```

## Run

```bash
npm run android:open   # opens Android Studio
npm run ios:open       # opens Xcode
```

Build and run from the native IDE as usual.

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

## Build a temporary DEV APK

The checked-in Android wrapper keeps the release/UAT URL unchanged:
`https://tedile-uat.onrender.com`. Debug builds use a configurable Gradle
property and default to the Android emulator host mapping:
`http://10.0.2.2:5001`.

From `Tedile/android/`:

```bash
./gradlew assembleDebug
```

To build for a physical device or an external tester on the same reachable
network as the developer machine, pass the developer machine's LAN IP. Do not
commit the personal IP:

```bash
./gradlew assembleDebug -PtedileDevUrl=http://192.168.x.x:5001
```

The resulting APK is `android/app/build/outputs/apk/debug/app-debug.apk`.
The URL is compiled into the debug APK only. Release builds continue to load
`https://tedile-uat.onrender.com`, and cleartext HTTP is enabled only by the
debug manifest.

The developer Flask server must listen on an interface reachable by the
tester, for example:

```bash
flask run --host 0.0.0.0 --port 5001
```

or use the equivalent host/port settings for `python app.py`. A physical
device cannot use `127.0.0.1` to reach the developer machine; use the machine's
LAN address and allow TCP port 5001 through its firewall. An Android emulator
uses `10.0.2.2` to reach the host machine.

The local OSRM service remains behind Flask at `127.0.0.1:5002`. The APK calls
Flask only; it does not connect directly to OSRM and does not alter the
existing West Bengal OSRM dataset.

The older Capacitor `mobile/capacitor.config.json` remains a development shell
configuration. The temporary APK URL is selected through the Android Gradle
property above, without changing the release/UAT URL.

## Run

```bash
npm run android:open   # opens Android Studio
npm run ios:open       # opens Xcode
```

Build and run from the native IDE as usual.

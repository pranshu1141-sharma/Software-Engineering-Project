# Carelane — patient app prototype

## Open the app

Double-click **START_APP.bat** in this folder. It starts the local AI/booking service and app preview, then opens **http://localhost:8081**. Keep using `localhost` for this preview: Expo may bind its local server to IPv6, so `127.0.0.1:8081` may not work.

The existing model report stays at http://127.0.0.1:8766/dashboard/index.html.

## Try a complete visit

1. Select **Start symptom guide**, then **Itchy skin** and **Explore suggested departments**.
2. Explore a suggested department or browse all doctors.
3. Select a doctor, choose a time, and confirm the demo appointment.
4. Open **My visits**. Refreshing the browser preserves the visit in the same session.
5. Select **Check in to demo queue**, then **Open demo desk**.
6. Select **Call next demo patient** to move three fictional patients through the queue. When it is your turn, select **Complete demo visit**.

You can cancel a booked appointment before check-in. The time becomes available again. Fees are illustrative; there is no payment or contact with a clinic.

## What this version includes

- Expo / React Native patient app with a responsive browser preview, four navigation tabs, loading and error states, and mobile safe-area support.
- Real local specialty inference using the trained TF-IDF + Logistic Regression specialty baseline. DistilBERT remains available in the research service but is not called by this app version.
- Fictional directory of nine doctors, searchable by name, department and clinic; available times for four days in India Standard Time.
- FastAPI + SQLite appointment service, anonymous session ownership, duplicate-request protection and transactional slot reservations.
- Queue check-in, five-second refresh, explicit demo controls and a completed-visit state.
- CatBoost queue estimates for General Medicine, Dermatology and Orthopedics. Other departments use a simple simulated arithmetic estimate. Neither represents real hospital waiting times.

## Where things are saved

| Item | Location |
| --- | --- |
| Patient UI | `patient-app/App.tsx` |
| App service client | `patient-app/src/api.ts` |
| Appointment and model API | `healthcare_ml/patient_api.py` |
| Local appointments | `data/app_demo.sqlite3` |
| Backend logs | `logs/patient-api.log`, `logs/patient-api-error.log` |
| Expo logs | `logs/patient-app.log`, `logs/patient-app-error.log` |
| Screenshots and browser check results | `reports/app/` |
| Backend tests | `tests/test_patient_api.py` |

The device stores an anonymous session token; the database stores its hash and that session’s appointments. Clearing browser/app storage loses access to that session's visits. This is a local demo mechanism, not production account security. Raw symptom text is not saved by the appointment service. Use example symptoms and avoid real personal data.

## Develop and verify

The launcher uses Node.js from PATH or this computer's bundled runtime. On a different computer install Node.js 22.13+ and run `npm install` inside `patient-app`. The backend needs the existing `.venv`, Python requirements and trained model artifacts from this project.

From `patient-app`:

```powershell
npm run typecheck
npm run build:web
npx expo export --platform android --output-dir dist-android
npm run test:app
```

Start the app and API before `test:app`. Its isolated browser session creates fictional appointments. The test uses installed Chrome by default on this computer; `CARELANE_CHROME` can override the executable path. It saves screenshots and JSON results in `reports/app`. Type checking uses a larger Node stack for this TypeScript version on Windows.

From `healthcare-ai`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_patient_api.py -q
```

## Try on an Android phone

The source and Android JavaScript bundle are ready for device testing. An APK has **not** been built, and this version has **not** been verified on a physical phone.

For Expo Go on the same trusted Wi-Fi, start an additional backend on port 8002 from `healthcare-ai`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn healthcare_ml.patient_api:app --host 0.0.0.0 --port 8002
```

Then, in a second terminal inside `patient-app`, replace `YOUR_PC_WIFI_IP` with your computer's Wi-Fi IPv4 address:

```powershell
$env:EXPO_PUBLIC_API_URL = 'http://YOUR_PC_WIFI_IP:8002'
npx expo start --lan --port 8082
```

Scan the QR code with a compatible Expo Go installation. Windows may require access on your private network. Stop the additional backend when finished. Use localhost:8081 for the laptop preview; the LAN mode above is for the native app. Account login, real clinic integration, production security, notification delivery and a distributable Android build are later development stages.

## Research boundary

This prototype demonstrates software integration. Department labels are unreviewed research proxies, and queue training uses simulated sessions. The app does not diagnose, assess urgency or reserve real healthcare. Software tests show that the app flow works; they do not establish medical accuracy or clinical safety.

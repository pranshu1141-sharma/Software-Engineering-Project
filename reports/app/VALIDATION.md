# Carelane prototype — validation record

Date: 9 September 2026. Environment: this Windows laptop, Python 3.12 environment, Node.js 24.19, Expo SDK 57, desktop Chrome.

| Check | Result |
| --- | --- |
| Backend tests | 4 passed in 8.79 seconds; two upstream deprecation warnings |
| TypeScript check | Passed with configured larger Node stack |
| Web export | Passed |
| Android JavaScript/Hermes export | Passed; not an APK or device test |
| Browser journey | All 9 recorded checks passed |
| Uncaught browser errors in final test | 0 |
| 390 × 844 mobile viewport | No horizontal page overflow; screenshot inspected |
| Launcher | Starts local service and recognizes running app |

The browser test used actual local specialty inference, booked an available fictional slot, reloaded to verify persistence, checked in and advanced the queue from three people ahead through completion. It also tested doctor search, empty results and an unavailable backend. Full details are in `browser-checks.json`; runnable checks are in `patient-app/scripts/check-app.cjs`.

Screenshots: `home-desktop.png`, `home-mobile.png`, `guidance.png`, `booking.png`, `queue.png`.

These are software integration results. They do not measure medical accuracy. No real patients or clinics were involved. Physical Android device testing, a signed APK, production authentication and real hospital integrations remain future work.

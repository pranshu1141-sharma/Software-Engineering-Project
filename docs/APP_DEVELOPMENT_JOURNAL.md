# Patient app development journal

## 9 September 2026 — first implementation

Created the Carelane patient prototype in `patient-app`, using Expo SDK 57, React Native, TypeScript, Lucide icons and AsyncStorage. Added the independent `healthcare_ml.patient_api` FastAPI service and local SQLite persistence. Existing model training scripts and research dashboard are preserved.

Implemented symptom input and local model guidance, fictional doctor search, time-slot booking, appointment persistence/cancellation, queue check-in and simulated desk controls. Native back handling and safe-area layout are included. The model used for specialty suggestions is the saved TF-IDF + Logistic Regression pipeline; this work did not retrain it. CatBoost is used only for the three departments supported by its simulated queue training data.

Appointment creation uses an idempotency key and a SQLite unique index inside a transaction, so a duplicate submission cannot reserve a second appointment and concurrent requests cannot reserve the same doctor/time slot. All appointment reads and actions require ownership of the anonymous demo session. Cancellation and check-in transitions also run inside transactions.

Validation artifacts are stored in `reports/app/`. Backend tests cover ownership, missing credentials, idempotency, competing reservations, cancellation releasing a slot, queue progression, invalid inputs and actual saved-model inference. Browser checks cover the patient journey, reload persistence, search, mobile layout and service-unavailable feedback. Web and Android JavaScript bundle exports are build checks, not proof of a phone installation.

Known limits: fictional directory and appointments; no production authentication or hospital integrations; simulated waiting times; no physical-device test or signed APK yet. Screenshots should be described as prototype software screens in documentation. Do not present demo bookings, software checks or simulated waiting times as clinical research results.

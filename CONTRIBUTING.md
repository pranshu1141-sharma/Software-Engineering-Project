# Contributing to Carelane

Carelane is a local software engineering prototype. The app uses fictional providers and simulated queues. Do not describe its model outputs as clinical diagnoses or real hospital performance.

## Start here

1. Read [README.md](README.md) for model setup and [APP_README.md](APP_README.md) for the patient app.
2. Read the [project journal](PROJECT_JOURNAL.md) and [errors and corrections journal](ERRORS_AND_CORRECTIONS_JOURNAL.md) before changing a reported result.
3. Create a branch for each piece of work, such as `app/booking-ui` or `ml/error-analysis`.
4. Keep changes small enough to review. Record the commands and results you used to verify them.
5. Open a pull request and have another team member review it before merging.

The Python virtual environment, downloaded datasets, trained model files, local SQLite database, logs and generated build folders are intentionally excluded from Git. Run the setup and training instructions locally to recreate them. The checked-in reports and metrics document the saved experiments; changing a model or dataset requires a new run and updated evidence.

Please update `PROJECT_JOURNAL.md` for completed work and `ERRORS_AND_CORRECTIONS_JOURNAL.md` when you investigate or fix a problem. Credit only the people who actually did that work. Keep any real patient information, access tokens, API keys and private credentials out of the repository.

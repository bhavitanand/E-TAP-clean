# Deploying E-TAP to Google Cloud Run

**Optional and unused.** The team decided on 2026-10-25 not to deploy here: Cloud Run needs a billing account with a card, there is no hard spending cap, and the API has no login. The hosted app runs on Render and Vercel. These files were never built or run; use them only if you accept that.

Two services: `etap-api` (FastAPI, built from `backend/Dockerfile`) and `etap-web` (the React dashboard served by nginx). The database stays on MongoDB Atlas.

## One-time setup
1. A Google Cloud project with billing on, and `gcloud` signed in (`gcloud auth login`).
2. Create these secrets in Secret Manager (the values never go in the repository):
   `etap-mongodb-uri`, `etap-gemini-api-key`, `etap-virustotal-api-key`, `etap-abuseipdb-api-key`.
   ```bash
   printf '%s' "$VALUE" | gcloud secrets create etap-gemini-api-key --data-file=-
   ```
3. Let the Cloud Run service account read them (`roles/secretmanager.secretAccessor`).
4. In Atlas, allow the Cloud Run egress (Network Access). Atlas free tiers need `0.0.0.0/0` because Cloud Run has no fixed IP.

## Deploy
```bash
PROJECT_ID=my-project REGION=us-central1 ./deploy/cloudrun/deploy.sh
```
The first run prints the dashboard URL. Run it once more with `FRONTEND_ORIGIN=<that url>` so the API's CORS list contains it.

## Why these settings
- **One API instance** (`minScale` and `maxScale` both 1): analysis jobs, caches and rate limiters live in process memory (see `CONTEXT.md`, known gaps). More instances would lose jobs between polls.
- **2 GiB memory**: XGBoost, OpenCV and Tesseract are loaded together.
- **Deeper (sandbox) analysis** still needs the user's own paired VM; nothing in this deployment starts a VM.

## Tear down
```bash
gcloud run services delete etap-api --region us-central1
gcloud run services delete etap-web --region us-central1
```

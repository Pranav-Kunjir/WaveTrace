# WaveTrace
A song detection application using FFTs

## Deploy the frontend

Import the `frontend` directory as the Vercel project root. Vercel will use
`frontend/vercel.json` to build the Vite app.

Set this Vercel environment variable:

```text
VITE_API_URL=https://your-backend.example.com
```

The backend must be deployed separately on a Python-capable host because it
uses FastAPI, Torch/Torchaudio, SQLite, and local fingerprint/audio files. Set
the backend variable below to the deployed Vercel URL so microphone requests
are allowed by CORS:

```text
FRONTEND_URL=https://your-app.vercel.app
```

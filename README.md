# PrintGuardianAI

Local MVP for monitoring 3D prints through a USB/Raspberry Pi camera and OctoPrint.

## Project layout

```text
.
├── backend/                 # FastAPI service, camera, AI and OctoPrint integration
├── frontend/                # React dashboard
├── tests/                   # Backend tests
├── .github/workflows/       # Continuous integration
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

## Quick start

1. Copy `.env.example` to `.env` and provide the camera and OctoPrint settings.
2. Install Python dependencies: `pip install -r requirements.txt`.
3. Start the API: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`.
4. Visit `http://localhost:8000/docs`.

To start the dashboard locally:

```bash
cd frontend
npm install
npm run dev
```

## API

- `GET /api/status`
- `GET /api/camera`, `/api/camera/frame`, `/api/camera/stream`
- `GET /api/analyze`, `/api/printer`, `/api/events`
- `POST /api/printer/stop`

## Safety

The current detector is a visual-change heuristic, not a trained failure-detection model. Automatic print stopping is disabled by default and should be enabled only after supervised testing.

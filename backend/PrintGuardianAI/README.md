# PrintGuardianAI

Local MVP for monitoring a 3D printer through a USB/Raspberry Pi camera and OctoPrint.

## Included

- FastAPI API: camera, analysis, printer status, events, emergency stop
- OpenCV camera capture and a baseline visual-change detector
- OctoPrint REST integration and JSONL event log
- Docker setup

## Quick start

1. Copy `.env.example` to `.env` and enter the OctoPrint details.
2. Install: `pip install -r requirements.txt`
3. Run: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
4. Open `http://localhost:8000/docs`.

## Safety

The current detector is an MVP visual-change heuristic, not a reliable failure-detection model. Automatic stopping is disabled by default and should be enabled only after supervised testing.

## API

- `GET /api/status`, `/api/camera`, `/api/camera/frame`, `/api/analyze`, `/api/printer`, `/api/events`
- `POST /api/printer/stop`

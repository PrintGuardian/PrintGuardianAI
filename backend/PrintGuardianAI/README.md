# PrintGuardianAI

Local MVP for monitoring a 3D printer through a USB/Raspberry Pi camera and OctoPrint.

## Included

- FastAPI API: camera, analysis, printer status, events, emergency stop
- Camera frame capture and browser-compatible MJPEG live stream
- OpenCV baseline visual-change detector
- OctoPrint REST integration and JSONL event log
- Docker setup and automated backend checks

## Quick start

1. Change into `backend/PrintGuardianAI`.
2. Copy `.env.example` to `.env` and enter the camera and OctoPrint details.
3. Install: `pip install -r requirements.txt`
4. Run: `uvicorn backend.main:app --host 0.0.0.0 --port 8000`
5. Open `http://localhost:8000/docs`.

## Safety

The current detector is an MVP visual-change heuristic, not a reliable failure-detection model. Automatic stopping is disabled by default and should be enabled only after supervised testing.

## API

- `GET /api/status`
- `GET /api/camera`, `/api/camera/frame`, `/api/camera/stream`
- `GET /api/analyze`, `/api/printer`, `/api/events`
- `POST /api/printer/stop`

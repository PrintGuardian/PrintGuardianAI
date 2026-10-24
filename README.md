# PrintGuardianAI

Local MVP for monitoring 3D prints through a USB/Raspberry Pi camera and OctoPrint.

## Run locally with Docker Compose

On a Raspberry Pi or Linux host with Docker Compose:

1. Copy `.env.example` to `.env`.
2. Set `OCTOPRINT_URL` and `OCTOPRINT_API_KEY`.
3. Set `CONTROL_API_TOKEN` to a unique secret (for example, `openssl rand -hex 32`). The stop endpoint stays disabled while this value is empty.
4. Start the stack with `docker compose up --build -d`.
5. Open `http://<host>:8080`.

The dashboard and API use one origin. Only the dashboard port is published; the API is available to the dashboard through the private Compose network. The camera device defaults to `/dev/video0`; change the device mapping in `docker-compose.yml` if your camera uses another path.

To follow service logs, run `docker compose logs -f`. Stop the stack with `docker compose down`.

## Optional local vision agent (Raspberry Pi 5, 8 GB)

The opt-in agent sends resized camera frames to a local Ollama service and reports structured assessments in the dashboard and event list. It does not call OctoPrint or stop a print. A possible warning is advisory and should be checked against the live printer.

The default model is [`qwen3-vl:2b-instruct`](https://ollama.com/library/qwen3-vl:2b-instruct) (Q4_K_M, about 1.9 GB). The agent samples every 120 seconds, scales frames to at most 768 pixels on the longest side, limits context to 2,048 tokens, and lets Ollama unload the model after two idle minutes. These settings reduce memory and CPU pressure on the Pi; inference speed still depends on cooling, camera resolution, and other services. This configuration assumes CPU inference and does not require an AI HAT. It has not yet been benchmarked on the target Pi, so monitor temperature and response time during supervised use.

To enable it:

1. Start the optional local model service: `docker compose --profile ai up -d ollama`.
2. Download the model once: `docker compose exec ollama ollama pull qwen3-vl:2b-instruct`.
3. Set `AI_AGENT_ENABLED=true` in `.env`.
4. Restart the API: `docker compose up -d --force-recreate printguardian`.

The dashboard shows agent state, model, last assessment, confidence, and any service error. The `/api/ai/status` endpoint exposes the same status. To disable the agent, set `AI_AGENT_ENABLED=false` and recreate the API container. Model files stay in the ignored local `ollama/` directory.

Inference runs inside the local Compose network. The model is downloaded from Ollama during setup, but camera frames are sent only to the local Ollama service at runtime. Keep the Pi on a ventilated surface and allow extra time for the first model load. The model is a general vision-language model, not a detector trained specifically for your printer, so it can miss failures or raise false alarms. The local vision agent never sends a stop command. The separate legacy heuristic auto-stop remains disabled by default.

## Run for development

1. Copy `.env.example` to `.env` and provide the camera, OctoPrint, and control-token settings.
2. Install Python dependencies: `pip install -r requirements.txt`.
3. Start the API from the repository root: `uvicorn backend.main:app --host 127.0.0.1 --port 8000`.
4. In another terminal, run the dashboard:

```bash
cd frontend
npm install
npm run dev
```

The Vite development server proxies `/api` to `http://localhost:8000`. Visit the URL printed by Vite. API documentation is available at `http://localhost:8000/docs`.

## API

- `GET /api/status`
- `GET /api/camera`
- `GET /api/camera/devices?max_devices=5` — probes local camera indexes 0–4 and reports devices that return a frame.
- `GET /api/camera/frame`
- `GET /api/camera/stream` — multipart MJPEG stream for browser previews.
- `GET /api/analyze`
- `GET /api/printer`
- `GET /api/events`
- `POST /api/printer/stop` — requires the `X-PrintGuardian-Token` header to match `CONTROL_API_TOKEN`.

Camera discovery briefly opens each device; avoid running it repeatedly while another application is using the camera. Read-only status endpoints do not require a control token. If `AUTO_STOP_ENABLED=true`, a qualifying stop triggered through `/api/analyze` also requires the control token. If `CONTROL_API_TOKEN` is unset, stop actions are disabled with `503`; a missing or incorrect token responds with `401`.

## Safety

Keep the dashboard on a trusted local network. Do not expose the API or dashboard directly to the public internet; use a VPN or a properly configured HTTPS reverse proxy with access controls for remote access. Store secrets in `.env` and do not commit that file.

The current detector is a visual-change heuristic, not a trained failure-detection model. Automatic print stopping is disabled by default and should be enabled only after supervised testing. Test the emergency stop with the printer disconnected or otherwise in a safe state before operational use.

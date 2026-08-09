import { useCallback, useEffect, useState } from "react";

type Camera = {
  online: boolean;
  index: number;
  error?: string | null;
};

type ServiceStatus = {
  service: string;
  status: string;
  camera: Camera;
};

type PrinterStatus = {
  connected: boolean;
  reason?: string;
  printer?: Record<string, unknown>;
};

type EventItem = {
  timestamp: string;
  level: string;
  type: string;
  message: string;
};

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

async function readJson<T>(path: string): Promise<T> {
  const response = await fetch(`${apiBase}${path}`);
  if (!response.ok) throw new Error(`Request failed (${response.status})`);
  return response.json() as Promise<T>;
}

export default function App() {
  const [service, setService] = useState<ServiceStatus | null>(null);
  const [printer, setPrinter] = useState<PrinterStatus | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [nextService, nextPrinter, nextEvents] = await Promise.all([
        readJson<ServiceStatus>("/status"),
        readJson<PrinterStatus>("/printer"),
        readJson<EventItem[]>("/events?limit=8"),
      ]);
      setService(nextService);
      setPrinter(nextPrinter);
      setEvents(nextEvents);
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not reach PrintGuardianAI.");
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const stopPrint = async () => {
    if (!window.confirm("Stop the active print? This action cannot be undone.")) return;

    setStopping(true);
    try {
      const response = await fetch(`${apiBase}/printer/stop`, { method: "POST" });
      if (!response.ok) throw new Error("The printer did not accept the stop command.");
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not stop the print.");
    } finally {
      setStopping(false);
    }
  };

  const cameraState = service?.camera.online ? "Online" : "Unavailable";
  const printerState = printer?.connected ? "Connected" : "Not connected";

  return (
    <main className="dashboard">
      <header>
        <div>
          <p className="eyebrow">PRINTGUARDIAN AI</p>
          <h1>Printer monitor</h1>
        </div>
        <button className="refresh" onClick={() => void refresh()}>Refresh</button>
      </header>

      {error && <p className="alert">{error}</p>}

      <section className="summary">
        <article>
          <span>Service</span>
          <strong className={service?.status === "online" ? "good" : ""}>
            {service?.status ?? "Checking…"}
          </strong>
        </article>
        <article>
          <span>Camera</span>
          <strong className={service?.camera.online ? "good" : "warning"}>{cameraState}</strong>
        </article>
        <article>
          <span>OctoPrint</span>
          <strong className={printer?.connected ? "good" : "warning"}>{printerState}</strong>
        </article>
      </section>

      <section className="grid">
        <article className="camera-card">
          <div className="card-title">
            <h2>Live camera</h2>
            <span className={service?.camera.online ? "badge online" : "badge"}>{cameraState}</span>
          </div>
          {service?.camera.online ? (
            <img src={`${apiBase}/camera/stream`} alt="Live view of the printer" />
          ) : (
            <div className="camera-placeholder">Connect a camera to start the live preview.</div>
          )}
        </article>

        <article className="control-card">
          <h2>Safety control</h2>
          <p>Emergency stop sends a cancel command to OctoPrint.</p>
          <button className="stop" disabled={!printer?.connected || stopping} onClick={() => void stopPrint()}>
            {stopping ? "Stopping…" : "STOP PRINT"}
          </button>
          {!printer?.connected && <small>Configure OctoPrint in <code>.env</code> to enable this action.</small>}
        </article>

        <article className="events-card">
          <div className="card-title"><h2>Recent events</h2><span>{events.length}</span></div>
          {events.length ? (
            <ul>
              {events.map((event) => (
                <li key={`${event.timestamp}-${event.type}`}>
                  <span className={`level ${event.level.toLowerCase()}`}>{event.level}</span>
                  <div><strong>{event.message}</strong><small>{new Date(event.timestamp).toLocaleString()}</small></div>
                </li>
              ))}
            </ul>
          ) : <p className="empty">No recorded events yet.</p>}
        </article>
      </section>
    </main>
  );
}

import { useCallback, useEffect, useState } from "react";

type Camera = { online: boolean; index: number; error?: string | null };
type ServiceStatus = { service: string; status: string; camera: Camera };
type PrinterStatus = {
  connected: boolean;
  reason?: string;
  job_error?: string;
  printer?: { state?: { text?: string; flags?: Record<string, boolean> }; [key: string]: unknown };
  job?: {
    job?: { file?: { name?: string }; estimatedPrintTime?: number };
    progress?: { completion?: number; printTime?: number; printTimeLeft?: number };
    state?: string;
  };
};
type VisionObservation = {
  risk_level: "clear" | "watch" | "warning" | "critical";
  confidence: number;
  issue: string;
  evidence: string;
  recommendation: string;
  model: string;
  timestamp: string;
  compared_frames: number;
};
type AgentStatus = {
  enabled: boolean;
  state: string;
  provider: string;
  model: string;
  interval_seconds: number;
  last_analysis_at?: string | null;
  last_observation?: VisionObservation | null;
  last_error?: string | null;
  last_duration_seconds?: number | null;
};
type EventItem = { timestamp: string; level: string; type: string; message: string; details?: Record<string, unknown> };

const apiBase = (import.meta.env.VITE_API_BASE_URL ?? "/api").replace(/\/$/, "");

async function readJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBase}${path}`, init);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail ?? body?.message;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${response.status})`);
  }
  return body as T;
}

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function formatDuration(seconds?: number): string {
  if (seconds === undefined || !Number.isFinite(seconds)) return "—";
  const minutes = Math.max(0, Math.floor(seconds / 60));
  const hours = Math.floor(minutes / 60);
  return hours ? `${hours}h ${minutes % 60}m` : `${minutes}m`;
}

export default function App() {
  const [service, setService] = useState<ServiceStatus | null>(null);
  const [printer, setPrinter] = useState<PrinterStatus | null>(null);
  const [agent, setAgent] = useState<AgentStatus | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  const [stopping, setStopping] = useState(false);
  const [cameraFailed, setCameraFailed] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refresh = useCallback(async () => {
    const results = await Promise.allSettled([
      readJson<ServiceStatus>("/status"),
      readJson<PrinterStatus>("/printer"),
      readJson<EventItem[]>("/events?limit=12"),
      readJson<AgentStatus>("/ai/status"),
    ]);
    const nextErrors: string[] = [];
    if (results[0].status === "fulfilled") {
      setService(results[0].value);
      setCameraFailed(false);
    } else nextErrors.push(`System status: ${results[0].reason instanceof Error ? results[0].reason.message : "request failed"}`);
    if (results[1].status === "fulfilled") setPrinter(results[1].value);
    else nextErrors.push(`Printer status: ${results[1].reason instanceof Error ? results[1].reason.message : "request failed"}`);
    if (results[2].status === "fulfilled") setEvents(results[2].value);
    else nextErrors.push(`Events: ${results[2].reason instanceof Error ? results[2].reason.message : "request failed"}`);
    if (results[3].status === "fulfilled") setAgent(results[3].value);
    else nextErrors.push(`Local AI: ${results[3].reason instanceof Error ? results[3].reason.message : "request failed"}`);
    setErrors(nextErrors);
    setLastUpdated(new Date());
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 5_000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const stopPrint = async () => {
    if (!window.confirm("Stop the active print? This sends a cancel command to OctoPrint.")) return;
    const token = window.prompt("Enter the control token configured as CONTROL_API_TOKEN on the PrintGuardian server.");
    if (token === null) return;
    setStopping(true);
    setNotice(null);
    setErrors([]);
    try {
      await readJson<{ success: boolean }>("/printer/stop", {
        method: "POST",
        headers: { "X-PrintGuardian-Token": token },
      });
      setNotice("Stop command accepted by OctoPrint.");
      await refresh();
    } catch (reason) {
      setErrors([reason instanceof Error ? reason.message : "Could not stop the print."]);
    } finally {
      setStopping(false);
    }
  };

  const cameraOnline = Boolean(service?.camera.online) && !cameraFailed;
  const agentLabel = !agent?.enabled
    ? "Disabled"
    : agent.state === "analyzing"
      ? "Analyzing"
      : agent.last_error
        ? "Unavailable"
        : agent.last_observation
          ? "Ready"
          : "Starting";
  const observation = agent?.last_observation;
  const printerConnected = Boolean(printer?.connected);
  const printerState = printer?.printer?.state?.text ?? (printerConnected ? "Connected" : "Not connected");
  const activePrint = Boolean(printer?.printer?.state?.flags?.printing);
  const job = printer?.job?.job;
  const jobProgress = printer?.job?.progress;
  const progressPercent = typeof jobProgress?.completion === "number"
    ? Math.min(100, Math.max(0, jobProgress.completion))
    : null;

  return (
    <main className="dashboard">
      <header className="page-header">
        <div>
          <p className="eyebrow">PRINTGUARDIAN AI <span className="eyebrow-dot" /></p>
          <h1>Printer monitor</h1>
          <p className="subtitle">Live safety overview for your 3D printer</p>
        </div>
        <div className="header-actions">
          <span className="updated">{lastUpdated ? `Updated ${lastUpdated.toLocaleTimeString()}` : "Connecting…"}</span>
          <button className="refresh" onClick={() => void refresh()}>Refresh</button>
        </div>
      </header>

      {errors.length > 0 && <div className="alerts" role="alert">{errors.map((message) => <p className="alert" key={message}>{message}</p>)}</div>}
      {notice && <p className="notice" role="status">{notice}</p>}

      <section className="summary" aria-label="System status">
        <article className="summary-card">
          <span className="summary-label">System</span>
          <div className="summary-value"><i className={`status-dot ${service?.status === "online" ? "is-good" : "is-muted"}`} /><strong>{service?.status ?? "Checking…"}</strong></div>
          <small>{service?.service ?? "PrintGuardianAI"}</small>
        </article>
        <article className="summary-card">
          <span className="summary-label">Camera</span>
          <div className="summary-value"><i className={`status-dot ${cameraOnline ? "is-good" : "is-warning"}`} /><strong>{cameraOnline ? "Online" : "Unavailable"}</strong></div>
          <small>{service?.camera ? `Device ${service.camera.index}` : "Waiting for camera"}</small>
        </article>
        <article className="summary-card">
          <span className="summary-label">Printer</span>
          <div className="summary-value"><i className={`status-dot ${printerConnected ? "is-good" : "is-warning"}`} /><strong>{printerState}</strong></div>
          <small>{activePrint ? "Print in progress" : printerConnected ? "OctoPrint connected" : printer?.reason ?? "Waiting for OctoPrint"}</small>
        </article>
      </section>

      <section className="print-progress panel" aria-label="Print progress">
        <div className="card-title">
          <div><p className="section-kicker">PRINT JOB</p><h2>{job?.file?.name ?? (printerConnected ? "No active print" : "Printer unavailable")}</h2></div>
          <span className={`job-badge ${activePrint ? "printing" : ""}`}>{activePrint ? "IN PROGRESS" : printer?.job?.state ?? (printerConnected ? "IDLE" : "OFFLINE")}</span>
        </div>
        {job ? (
          <>
            <div className="progress-track" aria-label={progressPercent === null ? "Progress unavailable" : `${progressPercent.toFixed(0)} percent complete`}>
              <span style={{ width: `${progressPercent ?? 0}%` }} />
            </div>
            <div className="progress-meta">
              <strong>{progressPercent === null ? "Progress unavailable" : `${progressPercent.toFixed(1)}% complete`}</strong>
              <span>{formatDuration(jobProgress?.printTimeLeft)} remaining</span>
            </div>
            {printer?.job_error && <small className="hint">Job details are temporarily unavailable: {printer.job_error}</small>}
          </>
        ) : <p className="empty">{printerConnected ? "OctoPrint reports no current job." : printer?.reason ?? "Connect to OctoPrint to see print progress."}</p>}
      </section>

      <section className="grid">
        <article className="camera-card panel">
          <div className="card-title"><div><p className="section-kicker">MONITORING</p><h2>Live camera</h2></div><span className={`badge ${cameraOnline ? "online" : ""}`}><i className="status-dot" />{cameraOnline ? "LIVE" : "OFFLINE"}</span></div>
          {cameraOnline ? (
            <div className="camera-frame">
              {!cameraFailed && <img src={`${apiBase}/camera/stream`} alt="Live view of the printer" onError={() => setCameraFailed(true)} />}
              {cameraFailed && <div className="camera-placeholder"><strong>Stream unavailable</strong><span>{service?.camera.error ?? "The camera connection was interrupted. Refresh to try again."}</span></div>}
              {!cameraFailed && <span className="live-tag"><i className="status-dot is-live" /> LIVE VIEW</span>}
            </div>
          ) : <div className="camera-frame camera-placeholder"><strong>Camera unavailable</strong><span>{service?.camera.error ?? "Connect or configure a camera to start the live preview."}</span></div>}
        </article>

        <article className="control-card panel">
          <div className="card-title"><div><p className="section-kicker">MANUAL CONTROL</p><h2>Safety stop</h2></div><span className="stop-symbol">!</span></div>
          <p className="control-copy">Cancel the current print job through OctoPrint. You’ll be asked to confirm before the command is sent.</p>
          <div className="job-state"><span>Printer state</span><strong>{printerState}</strong></div>
          <button className="stop" disabled={!printerConnected || stopping} onClick={() => void stopPrint()}><span>{stopping ? "SENDING STOP…" : "STOP PRINT"}</span><span aria-hidden="true">→</span></button>
          {!printerConnected && <small className="hint">Connect OctoPrint to enable the stop control.</small>}
          {printerConnected && !activePrint && <small className="hint">Stop command will be sent to OctoPrint even if no active job is reported.</small>}
          <div className="safety-note"><span aria-hidden="true">◆</span><p>Only use this control when you need to cancel a print immediately.</p></div>
        </article>

        <article className="events-card panel">
          <div className="card-title"><div><p className="section-kicker">ACTIVITY</p><h2>Recent events</h2></div><span className="event-count">{events.length} {events.length === 1 ? "event" : "events"}</span></div>
          {events.length ? <ul>{events.map((event, index) => <li key={`${event.timestamp}-${event.type}-${index}`}>
            <span className={`level ${event.level.toLowerCase()}`}>{event.level}</span>
            <div className="event-copy"><strong>{event.message}</strong><small>{formatDate(event.timestamp)}</small></div>
            <span className="event-type">{event.type.replace(/_/g, " ")}</span>
          </li>)}</ul> : <p className="empty">{errors.some((message) => message.startsWith("Events:")) ? "Events could not be loaded." : "No recorded events yet."}</p>}
        </article>
      </section>
      <footer><span>PrintGuardianAI</span><span>Monitoring refreshes every 5 seconds</span></footer>
    </main>
  );
}



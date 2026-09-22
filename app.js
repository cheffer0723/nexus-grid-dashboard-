const DEFAULT_MODE = "demo";
const MODE_STORAGE_KEY = "NEXUS_DASHBOARD_MODE";
const BUILD_COMMIT = document.currentScript?.dataset.commit || localStorage.getItem("NEXUS_BUILD_SHA") || "unknown";
const MODE_CONFIG = {
  demo: { label: "Demo sample", apiBase: "" },
  remote: { label: "Your API, read-only", apiBase: "" },
  remoteControl: { label: "Your API, with control", apiBase: "" },
  local: { label: "This computer, control on", apiBase: "http://127.0.0.1:8080" },
};
let DASHBOARD_MODE = localStorage.getItem(MODE_STORAGE_KEY) || DEFAULT_MODE;
if (!MODE_CONFIG[DASHBOARD_MODE]) DASHBOARD_MODE = DEFAULT_MODE;
let API_BASE = MODE_CONFIG[DASHBOARD_MODE].apiBase;
const REFRESH_MS = 45000;
const PROCESS_REFRESH_MS = 5000;
const DEFAULT_PROCESS_SERVICES = [
  { key: "engine", label: "Nexus engine" },
  { key: "bridge", label: "Bridge" },
  { key: "outcomes_tracker", label: "Outcomes tracker" },
  { key: "morning_bias", label: "Morning bias loop" },
];

function normalizeApiBase(value) {
  return String(value ?? "").trim().replace(/\/$/, "");
}

function apiBaseKeyForMode(mode) {
  if (mode === "remoteControl") return "NEXUS_REMOTE_CONTROL_BASE";
  if (mode === "local") return "NEXUS_LOCAL_API_BASE";
  return "NEXUS_REMOTE_READONLY_BASE";
}

function syncApiBaseUi() {
  const input = document.getElementById("apiBaseInput");
  const modeSelect = document.getElementById("modeSelect");
  const tokenInput = document.getElementById("controlTokenInput");
  const pill = document.getElementById("backendStatusPill");
  const hint = document.getElementById("backendBaseText");
  const build = document.getElementById("frontendCommitText");
  if (input) input.value = API_BASE;
  if (modeSelect) modeSelect.value = DASHBOARD_MODE;
  if (tokenInput) tokenInput.value = localStorage.getItem("NEXUS_CONTROL_TOKEN") || "";
  if (pill) {
    const className = DASHBOARD_MODE === "remoteControl" || DASHBOARD_MODE === "local" ? "ok" : DASHBOARD_MODE === "demo" ? "neutral" : "warn";
    pill.className = `pill ${className}`;
    pill.textContent = MODE_CONFIG[DASHBOARD_MODE].label;
  }
  if (hint) hint.textContent = API_BASE;
  if (build) build.textContent = `Build: ${localStorage.getItem("NEXUS_BUILD_SHA") || BUILD_COMMIT}`;
}

function syncBuildCommit() {
  const build = document.getElementById("frontendCommitText");
  if (build) build.textContent = `Build: ${BUILD_COMMIT}`;
}

function updateApiBase(nextBase) {
  const normalized = normalizeApiBase(nextBase);
  if (!normalized) return false;
  API_BASE = normalized;
  localStorage.setItem(apiBaseKeyForMode(DASHBOARD_MODE), API_BASE);
  syncApiBaseUi();
  return true;
}

function updateControlToken(nextToken) {
  const token = String(nextToken ?? "").trim();
  if (!token) return false;
  localStorage.setItem("NEXUS_CONTROL_TOKEN", token);
  syncApiBaseUi();
  return true;
}

function setMode(nextMode) {
  DASHBOARD_MODE = MODE_CONFIG[nextMode] ? nextMode : DEFAULT_MODE;
  API_BASE = localStorage.getItem(apiBaseKeyForMode(DASHBOARD_MODE)) || MODE_CONFIG[DASHBOARD_MODE].apiBase || "";
  localStorage.setItem(MODE_STORAGE_KEY, DASHBOARD_MODE);
  syncApiBaseUi();
}

function dashboardEndpoint() {
  if (DASHBOARD_MODE === "demo") return "";
  if (!API_BASE) return "";
  if (DASHBOARD_MODE === "remote") return `${API_BASE}/state`;
  if (DASHBOARD_MODE === "remoteControl") return `${API_BASE}/api/remote/state`;
  return `${API_BASE}/api/nexus/dashboard`;
}

function buildRemoteDashboardPayload(raw) {
  const data = raw?.data && typeof raw.data === "object" ? raw.data : raw;
  return normalizeDashboardPayload({
    generated_at_utc: raw?.received_at_utc || raw?.generated_at_utc,
    engine_state: data || {},
    recent_trades: raw?.recent_trades || [],
    disagreements: raw?.disagreements || [],
    regime_summary: raw?.regime_summary || { deterministic: [], ml: [], meta: { trade_count: 0 } },
    processes: raw?.processes || [],
    deployment_incident: raw?.deployment_incident || data?.deployment_incident,
    workflow_handoff: raw?.workflow_handoff || raw?.handoff_status || data?.workflow_handoff || data?.handoff_status,
  });
}

function normalizeDashboardPayload(raw) {
  if (raw?.engine_state) {
    return {
      generated_at_utc: raw.generated_at_utc || raw.generated_at || new Date().toISOString(),
      engine_state: raw.engine_state || {},
      recent_trades: raw.recent_trades || raw.executions_recent || [],
      disagreements: raw.disagreements || [],
      regime_summary: raw.regime_summary || { deterministic: [], ml: [], meta: { trade_count: raw.recent_trades?.length || 0 } },
      processes: raw.processes || [],
      deployment_incident: raw.deployment_incident || raw.engine_state?.deployment_incident || null,
      workflow_handoff: raw.workflow_handoff || raw.handoff_status || raw.engine_state?.workflow_handoff || raw.engine_state?.handoff_status || null,
    };
  }

  return {
    generated_at_utc: raw?.generated_at_utc || raw?.generated_at || new Date().toISOString(),
    engine_state: raw || {},
    recent_trades: raw?.recent_trades || raw?.executions_recent || [],
    disagreements: raw?.disagreements || [],
    regime_summary: raw?.regime_summary || { deterministic: [], ml: [], meta: { trade_count: raw?.executions_recent?.length || 0 } },
    processes: raw?.processes || [],
    deployment_incident: raw?.deployment_incident || null,
    workflow_handoff: raw?.workflow_handoff || raw?.handoff_status || null,
  };
}

async function loadBundledDashboardState() {
  const res = await fetch("./state.json", { cache: "no-store" });
  if (!res.ok) throw new Error(`Static state fetch failed: ${res.status}`);
  return normalizeDashboardPayload(await res.json());
}

function initBackendControls() {
  const input = document.getElementById("apiBaseInput");
  const modeSelect = document.getElementById("modeSelect");
  const tokenInput = document.getElementById("controlTokenInput");
  const saveButton = document.getElementById("saveApiBaseButton");
  const saveTokenButton = document.getElementById("saveControlTokenButton");
  if (input) input.value = API_BASE;
  if (modeSelect) modeSelect.value = DASHBOARD_MODE;
  if (modeSelect) {
    modeSelect.addEventListener("change", async () => {
      setMode(modeSelect.value);
      await refreshDashboard();
    });
  }
  if (saveButton) {
    saveButton.addEventListener("click", async () => {
      if (!updateApiBase(input?.value)) return;
      await refreshDashboard();
    });
  }
  if (saveTokenButton) {
    saveTokenButton.addEventListener("click", async () => {
      if (!updateControlToken(tokenInput?.value)) return;
      await refreshDashboard();
    });
  }
  if (input) {
    input.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        if (!updateApiBase(input.value)) return;
        await refreshDashboard();
      }
    });
  }
  if (tokenInput) {
    tokenInput.addEventListener("keydown", async (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        if (!updateControlToken(tokenInput.value)) return;
        await refreshDashboard();
      }
    });
  }
  syncApiBaseUi();
  syncBuildCommit();
}

const fmt = {
  int(value) {
    const n = Number(value);
    return Number.isFinite(n) ? new Intl.NumberFormat().format(Math.round(n)) : "—";
  },
  num(value, digits = 4) {
    const n = Number(value);
    return Number.isFinite(n) ? n.toFixed(digits) : "—";
  },
  pct(value, digits = 2) {
    const n = Number(value);
    if (!Number.isFinite(n)) return "—";
    const body = `${Math.abs(n * 100).toFixed(digits)}%`;
    return n < 0 ? `−${body}` : body;
  },
  price(value) {
    const n = Number(value);
    return Number.isFinite(n) ? n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—";
  },
  text(value, fallback = "—") {
    return value === null || value === undefined || value === "" ? fallback : String(value);
  },
};

function formatWhen(value, withTime = true) {
  if (value === null || value === undefined || value === "") return "—";
  const raw = String(value);
  const dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(raw);
  const date = new Date(dateOnly ? `${raw}T00:00:00Z` : raw);
  if (Number.isNaN(date.getTime())) return raw;
  const datePart = new Intl.DateTimeFormat("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(date);
  if (!withTime || dateOnly) return datePart;
  const timePart = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
    hourCycle: "h23",
  }).format(date);
  return `${datePart}, ${timePart} UTC`;
}

function humanize(value) {
  const text = fmt.text(value).replaceAll("_", " ").toLowerCase();
  if (text === "—") return text;
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function yesNo(value) {
  if (value === true) return "Yes";
  if (value === false) return "No";
  return fmt.text(value);
}

function money(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  const body = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  if (n < 0) return `−${body}`;
  if (n > 0) return `+${body}`;
  return body;
}

function signed(value, text) {
  const n = Number(value);
  const tone = !Number.isFinite(n) || n === 0 ? "" : n > 0 ? "up" : "down";
  return `<span class="${tone}">${text}</span>`;
}

function toneForAction(value) {
  const normalized = String(value ?? "").toUpperCase();
  if (["LONG", "WIN", "BULL", "GOOD", "EXPANDING"].some((word) => normalized.includes(word))) return "up";
  if (["SHORT", "LOSS", "BEAR", "BAD", "CONTRACTING"].some((word) => normalized.includes(word))) return "down";
  return "";
}

function toneText(value) {
  return `<span class="${toneForAction(value)}">${escapeHtml(humanize(value))}</span>`;
}

function shown(value) {
  if (Array.isArray(value)) return value.length ? value.join(" ") : "";
  if (value === null || value === undefined || value === "") return "";
  return String(value);
}

function escapeHtml(value) {
  return fmt.text(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function badgeClass(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (normalized.includes("match") || normalized.includes("true") || normalized.includes("good") || normalized.includes("ok")) return "badge ok";
  if (normalized.includes("mismatch") || normalized.includes("false") || normalized.includes("error") || normalized.includes("bad")) return "badge bad";
  if (normalized.includes("warn") || normalized.includes("unknown") || normalized.includes("null") || normalized.includes("shadow") || normalized.includes("stress")) return "badge warn";
  return "badge neutral";
}

function actionClass(value) {
  const normalized = String(value ?? "").toUpperCase();
  if (normalized.includes("LONG") || normalized.includes("EXPANDING") || normalized.includes("GOOD")) return "badge ok";
  if (normalized.includes("SHORT") || normalized.includes("CONTRACTING") || normalized.includes("BAD")) return "badge bad";
  if (normalized.includes("WAIT") || normalized.includes("NEUTRAL") || normalized.includes("STRESS")) return "badge warn";
  return "badge neutral";
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = fmt.text(value);
}

function setBadge(id, label, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `pill ${badgeClass(value)}`;
  el.textContent = `${label}: ${fmt.text(value, "unknown")}`;
}

function renderEmpty(container, message) {
  container.innerHTML = `<div class="empty-state">${escapeHtml(message)}</div>`;
}

function renderKeyValues(container, entries) {
  if (!entries.length) {
    renderEmpty(container, "No engine data available.");
    return;
  }
  container.innerHTML = entries
    .map(
      (entry) => `
        <div class="kv-item">
          <span class="kv-label">${escapeHtml(entry.label)}</span>
          <span class="kv-value ${entry.className || ""}">${escapeHtml(entry.value)}</span>
        </div>
      `,
    )
    .join("");
}

function rowBadge(value, fallback = "neutral") {
  return `<span class="badge ${badgeClass(value) || fallback}">${escapeHtml(fmt.text(value))}</span>`;
}

function renderTable(container, columns, rows, emptyMessage) {
  if (!rows.length) {
    renderEmpty(container, emptyMessage);
    return;
  }

  const head = columns.map((column) => `<th class="${column.numeric ? "num" : ""}">${escapeHtml(column.label)}</th>`).join("");
  const body = rows
    .map((row) => {
      const cells = columns
        .map((column) => {
          const raw = typeof column.value === "function" ? column.value(row) : row[column.key];
          const extra = column.className ? column.className(row) : "";
          const className = [column.numeric ? "num" : "", extra].filter(Boolean).join(" ");
          return `<td class="${className}">${raw ?? "—"}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("");

  container.innerHTML = `
    <table>
      <thead><tr>${head}</tr></thead>
      <tbody>${body}</tbody>
    </table>
  `;
}

function summarizeOutcomes(map) {
  const entries = Object.entries(map || {});
  if (!entries.length) return "—";
  return entries.map(([key, value]) => `${key}: ${value}`).join(", ");
}

function processStatusClass(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (normalized.includes("running") || normalized.includes("healthy")) return "badge ok";
  if (normalized.includes("error")) return "badge bad";
  if (normalized.includes("stopping") || normalized.includes("starting") || normalized.includes("degraded")) return "badge warn";
  if (normalized.includes("stopped")) return "badge neutral";
  return "badge neutral";
}

function commandText(value) {
  if (Array.isArray(value)) return value.join(" ");
  return fmt.text(value);
}

async function processAction(service, action) {
  if (DASHBOARD_MODE === "remote" || DASHBOARD_MODE === "demo") {
    setText("lastErrorText", DASHBOARD_MODE === "demo" ? "Process control is off in demo mode." : "Process control is off in read-only mode.");
    return;
  }
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem("NEXUS_CONTROL_TOKEN") || "";
  if (DASHBOARD_MODE === "remoteControl" && token) headers["x-nexus-remote-token"] = token;
  const targetUrl = DASHBOARD_MODE === "remoteControl"
    ? `${API_BASE}/api/remote/commands`
    : `${API_BASE}/api/processes/${encodeURIComponent(service)}/${action}`;
  const body = DASHBOARD_MODE === "remoteControl"
    ? JSON.stringify({ service, action, requested_by: "dashboard", source: "nexus-grid-static" })
    : undefined;
  const res = await fetch(targetUrl, {
    method: "POST",
    headers,
    body,
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`Process ${action} failed for ${service}: ${res.status}`);
  }
  await refreshDashboard();
}

function renderProcessCards(payload) {
  const services = payload.services && payload.services.length ? payload.services : DEFAULT_PROCESS_SERVICES;
  const controlMode = DASHBOARD_MODE === "local" || DASHBOARD_MODE === "remoteControl";
  const notice = document.getElementById("processNotice");
  if (notice) {
    notice.hidden = controlMode;
    notice.textContent = controlMode
      ? ""
      : DASHBOARD_MODE === "demo"
        ? "Start and stop stay off until you connect an engine that accepts commands."
        : "This mode only reads state. Switch to a control mode to start or stop services.";
  }
  setText(
    "processCountStamp",
    controlMode ? `${services.length} services` : "Not connected",
  );

  const container = document.getElementById("processCards");
  if (!container) return;

  if (!services.length) {
    renderEmpty(container, "No managed services found.");
    return;
  }

  container.innerHTML = services
    .map((service) => {
      const status = String(service.status || "stopped").toLowerCase();
      const statusLabel = humanize(status);
      const stdoutTail = (service.last_stdout_tail || []).join("\n");
      const stderrTail = (service.last_stderr_tail || []).join("\n");
      const combinedTail = [stdoutTail, stderrTail].filter(Boolean).join(stdoutTail && stderrTail ? "\n" : "");
      const launchCommand = shown(service.launch_command);
      const scriptPath = shown(service.script_path);
      const commandDisplay = shown(service.command_display);
      const monitored = service.monitored_paths || [];
      const meta = [
        ["PID", shown(service.pid)],
        ["Started", service.start_time_utc ? formatWhen(service.start_time_utc) : ""],
        ["Heartbeat", service.last_heartbeat_at_utc ? formatWhen(service.last_heartbeat_at_utc) : ""],
        ["File update", service.last_file_update_at_utc ? formatWhen(service.last_file_update_at_utc) : ""],
        ["Last error", shown(service.last_error)],
        ["Exit code", shown(service.exit_code)],
      ].filter(([, value]) => value);
      const stopDisabled = !controlMode || (status !== "running" && status !== "starting" && status !== "stopping");
      const startDisabled = !controlMode || status === "running" || status === "starting";
      const detailParts = [];
      if (meta.length) {
        detailParts.push(`<div class="process-meta">${meta.map(([label, value]) => `<div class="kv-item"><span class="kv-label">${escapeHtml(label)}</span><span class="kv-value mono">${escapeHtml(value)}</span></div>`).join("")}</div>`);
      }
      if (launchCommand) detailParts.push(`<div class="process-command"><span class="kv-label">Launch command</span><div class="mono">${escapeHtml(launchCommand)}</div></div>`);
      if (scriptPath) detailParts.push(`<div class="process-command"><span class="kv-label">Script path</span><div class="mono">${escapeHtml(scriptPath)}</div></div>`);
      if (commandDisplay && commandDisplay !== launchCommand) detailParts.push(`<div class="process-command"><span class="kv-label">Runner command</span><div class="mono">${escapeHtml(commandDisplay)}</div></div>`);
      if (monitored.length) detailParts.push(`<div class="process-paths"><span class="kv-label">Watched files</span>${monitored.map((p) => `<div class="mono">${escapeHtml(fmt.text(p))}</div>`).join("")}</div>`);
      if (combinedTail) detailParts.push(`<div class="process-tail"><span class="kv-label">Recent output</span><pre>${escapeHtml(combinedTail)}</pre></div>`);
      return `
        <article class="process-card status-${escapeHtml(status)}">
          <div class="process-row">
            <div class="process-id">
              <h3>${escapeHtml(service.label || service.key)}</h3>
              <span class="process-status">${escapeHtml(statusLabel)}</span>
            </div>
            <div class="process-actions">
              <button type="button" onclick="processAction('${escapeHtml(service.key)}','start')" ${startDisabled ? "disabled" : ""}>Start</button>
              <button type="button" onclick="processAction('${escapeHtml(service.key)}','stop')" ${stopDisabled ? "disabled" : ""}>Stop</button>
              <button type="button" onclick="processAction('${escapeHtml(service.key)}','restart')" ${controlMode ? "" : "disabled"}>Restart</button>
            </div>
          </div>
          ${detailParts.length ? `<div class="process-detail">${detailParts.join("")}</div>` : ""}
        </article>
      `;
    })
    .join("");
}

async function loadProcesses() {
  if (DASHBOARD_MODE === "demo") {
    renderProcessCards({ services: DEFAULT_PROCESS_SERVICES.map((service) => ({
      ...service,
      status: "stopped",
      pid: null,
      start_time_utc: null,
      stop_time_utc: null,
      exit_code: null,
      last_error: null,
      last_output_at_utc: null,
      last_file_update_at_utc: null,
      last_heartbeat_at_utc: null,
      last_stdout_tail: [],
      last_stderr_tail: [],
      script_path: null,
      command_display: null,
      launch_command: null,
      monitored_paths: [],
    })) });
    return { ok: true, mode: "demo" };
  }
  if (DASHBOARD_MODE === "remoteControl") {
    const res = await fetch(`${API_BASE}/api/remote/state`, {
      cache: "no-store",
      headers: localStorage.getItem("NEXUS_CONTROL_TOKEN") ? { "x-nexus-remote-token": localStorage.getItem("NEXUS_CONTROL_TOKEN") } : {},
    });
    if (!res.ok) throw new Error(`Remote command state fetch failed: ${res.status}`);
    const raw = await res.json();
    const services = (raw.services || []).map((row) => {
      let statusData = {};
      try { statusData = JSON.parse(row.status_json || "{}"); } catch { statusData = {}; }
      return {
        key: row.service,
        label: row.service,
        status: statusData.status || "unknown",
        pid: statusData.pid ?? null,
        start_time_utc: statusData.start_time_utc || null,
        stop_time_utc: statusData.stop_time_utc || null,
        exit_code: statusData.exit_code ?? null,
        last_error: statusData.last_error || row.last_error || null,
        last_output_at_utc: statusData.last_output_at_utc || null,
        last_file_update_at_utc: statusData.last_file_update_at_utc || null,
        last_heartbeat_at_utc: statusData.last_heartbeat_at_utc || row.last_heartbeat_at_utc || null,
        last_stdout_tail: [],
        last_stderr_tail: [],
        script_path: null,
        command_display: null,
        launch_command: null,
        monitored_paths: [],
      };
    });
    renderProcessCards({ services });
    return { ok: true, mode: "remoteControl" };
  }
  if (DASHBOARD_MODE !== "local") {
    renderProcessCards({ services: DEFAULT_PROCESS_SERVICES.map((service) => ({
      ...service,
      status: "stopped",
      pid: null,
      start_time_utc: null,
      stop_time_utc: null,
      exit_code: null,
      last_error: null,
      last_output_at_utc: null,
      last_file_update_at_utc: null,
      last_heartbeat_at_utc: null,
      last_stdout_tail: [],
      last_stderr_tail: [],
      script_path: null,
      command_display: null,
      launch_command: null,
      monitored_paths: [],
    })) });
    return { ok: true, mode: "remote" };
  }
  const res = await fetch(`${API_BASE}/api/processes`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Process fetch failed: ${res.status}`);
  }
  const payload = await res.json();
  renderProcessCards(payload);
}

function renderSummary(container, rows, emptyMessage) {
  const columns = [
    { label: "Group", key: "group", value: (row) => escapeHtml(humanize(row.group)) },
    { label: "Trades", key: "trade_count", numeric: true, value: (row) => fmt.int(row.trade_count) },
    { label: "Wins", key: "win_count", numeric: true, value: (row) => fmt.int(row.win_count) },
    { label: "Win rate", key: "win_rate", numeric: true, value: (row) => fmt.pct(row.win_rate) },
    { label: "Avg PnL", key: "avg_pnl_abs", numeric: true, value: (row) => signed(row.avg_pnl_abs, money(row.avg_pnl_abs)) },
    { label: "Total PnL", key: "total_pnl_abs", numeric: true, value: (row) => signed(row.total_pnl_abs, money(row.total_pnl_abs)) },
    { label: "Outcomes", key: "outcome_distribution", value: (row) => escapeHtml(summarizeOutcomes(row.outcome_distribution)) },
  ];
  renderTable(container, columns, rows, emptyMessage);
}

function renderEngineState(payload) {
  const state = payload.engine_state || {};
  const system = state.system_status || {};
  const health = state.health || {};
  const control = state.control_state || {};
  const paper = state.paper_summary || {};
  const signal = state.signal_latest || {};

  const marketBias = signal.market_bias ?? signal.marketBias ?? state.market_bias ?? state.marketBias ?? "unknown";
  const volatilityState = signal.volatility_state ?? signal.volatilityState ?? state.volatility_state ?? state.volatilityState ?? "unknown";
  const deterministicRegime = signal.deterministic_regime ?? signal.deterministicRegime ?? "unknown";
  const shadowEodOnly = signal.shadow_eod_only ?? signal.shadowEodOnly ?? false;
  const confidenceAdjusted = signal.confidence_adjusted ?? signal.confidenceAdjusted ?? signal.confidence;
  const currentPrice = signal.current_price ?? signal.currentPrice ?? state.current_price ?? state.currentPrice;
  const mlMatch = signal.ml_vs_deterministic_match;
  const engineMode = system.mode || marketBias || "unknown";

  const mlLabel = mlMatch === false ? "Mismatch" : mlMatch === true ? "Match" : shadowEodOnly ? "Shadow" : "Unknown";
  const mlTone = mlMatch === false ? "down" : mlMatch === true ? "up" : "";
  const enginePill = document.getElementById("engineModePill");
  if (enginePill) {
    enginePill.className = "status-value";
    enginePill.textContent = humanize(engineMode);
  }
  const mlPill = document.getElementById("mlPill");
  if (mlPill) {
    mlPill.className = `status-value ${mlTone}`.trim();
    mlPill.textContent = mlLabel;
  }
  setText("freshnessPill", formatWhen(payload.generated_at_utc));
  setText("dashboardUpdated", `Updated ${formatWhen(payload.generated_at_utc)}`);
  setText("dashboardSource", state.source_file ? `Source ${state.source_file}` : "Source —");
  setText("engineSourceStamp", formatWhen(state.source_mtime_utc || signal.timestamp_utc || payload.generated_at_utc));

  const matchLabel = signal.ml_vs_deterministic_match === null || signal.ml_vs_deterministic_match === undefined
    ? "Unknown"
    : signal.ml_vs_deterministic_match ? "Match" : "Mismatch";
  const groups = [
    {
      title: "Tape",
      rows: [
        { label: "Symbol", value: fmt.text(signal.symbol), className: "mono" },
        { label: "Price", value: fmt.price(currentPrice), className: "mono" },
        { label: "Action", value: humanize(signal.action), className: toneForAction(signal.action) },
        { label: "Bias", value: humanize(marketBias), className: toneForAction(marketBias) },
        { label: "Regime", value: humanize(deterministicRegime), className: toneForAction(deterministicRegime) },
        { label: "Volatility", value: humanize(volatilityState), className: toneForAction(volatilityState) },
        { label: "As of", value: formatWhen(signal.timestamp_utc ?? signal.timestamp), className: "mono" },
      ],
    },
    {
      title: "Model",
      rows: [
        { label: "ML regime", value: humanize(signal.ml_regime_pred), className: toneForAction(signal.ml_regime_pred) },
        { label: "ML confidence", value: fmt.pct(signal.ml_regime_confidence), className: "mono" },
        { label: "Versus tape", value: matchLabel, className: mlMatch === false ? "down" : mlMatch === true ? "up" : "" },
        { label: "Confidence", value: fmt.num(signal.confidence, 2), className: "mono" },
        { label: "Adjusted", value: fmt.num(confidenceAdjusted, 2), className: "mono" },
        { label: "End-of-day shadow", value: yesNo(shadowEodOnly) },
      ],
    },
    {
      title: "Desk",
      rows: [
        { label: "Mode", value: humanize(system.mode) },
        { label: "Running", value: yesNo(system.running), className: system.running === true ? "up" : "" },
        { label: "Broker", value: yesNo(system.brokerConnected), className: system.brokerConnected === true ? "up" : system.brokerConnected === false ? "down" : "" },
        { label: "Risk", value: humanize(system.riskState) },
        { label: "Loop alive", value: yesNo(health.loopAlive), className: health.loopAlive === true ? "up" : health.loopAlive === false ? "down" : "" },
        { label: "Emergency stop", value: yesNo(control.emergencyStopActive), className: control.emergencyStopActive === true ? "down" : control.emergencyStopActive === false ? "up" : "" },
        { label: "Open positions", value: fmt.int(paper.open_position_count), className: "mono" },
        { label: "Realized PnL", value: money(paper.realized_pnl_abs), className: `mono ${Number(paper.realized_pnl_abs) > 0 ? "up" : Number(paper.realized_pnl_abs) < 0 ? "down" : ""}`.trim() },
      ],
    },
  ];

  const board = document.getElementById("engineStateGrid");
  if (!board) return;
  board.innerHTML = `<div class="state-board">${groups.map((group) => `
    <section class="state-group">
      <h3>${escapeHtml(group.title)}</h3>
      ${group.rows.map((row) => `
        <div class="state-row">
          <span>${escapeHtml(row.label)}</span>
          <strong class="${row.className || ""}">${escapeHtml(row.value)}</strong>
        </div>
      `).join("")}
    </section>
  `).join("")}</div>`;
}

function renderDeploymentIncident(payload) {
  const incident = payload.deployment_incident || payload.engine_state?.deployment_incident;
  const card = document.getElementById("deploymentIncidentCard");
  if (!card) return;
  if (!incident) {
    card.hidden = true;
    return;
  }

  card.hidden = false;
  const status = incident.status || "reported";
  const service = incident.service || "backend";
  const environment = incident.environment || "production";
  const observedAt = incident.observed_at_utc || incident.last_log_at_utc || payload.generated_at_utc;
  const statusPill = document.getElementById("deploymentIncidentStatus");
  if (statusPill) {
    statusPill.className = `pill ${badgeClass(status)}`;
    statusPill.textContent = `Status: ${fmt.text(status)}`;
  }
  setText("deploymentIncidentTitle", incident.title || `${service} deployment incident`);
  setText("deploymentIncidentSummary", incident.summary || incident.impact || "Recent production deployment event recorded.");

  const metaEntries = [
    { label: "service", value: service, className: "mono" },
    { label: "environment", value: environment },
    { label: "observed", value: observedAt, className: "mono" },
    { label: "severity", value: incident.severity || status, className: badgeClass(incident.severity || status) },
  ];
  renderKeyValues(document.getElementById("deploymentIncidentMeta"), metaEntries);

  const actions = document.getElementById("deploymentIncidentActions");
  const actionItems = incident.next_actions || [];
  if (actions) {
    actions.innerHTML = actionItems.length
      ? `<h3>Next actions</h3><ul>${actionItems.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : "";
  }

  const log = document.getElementById("deploymentIncidentLog");
  if (log) {
    const lines = incident.log_excerpt || [];
    log.textContent = lines.length ? lines.join("\n") : "No log excerpt recorded.";
  }
}


function handoffStatusClass(value) {
  const normalized = String(value ?? "").toLowerCase();
  if (normalized.includes("complete") || normalized.includes("done") || normalized.includes("committed")) return "ok";
  if (normalized.includes("blocked") || normalized.includes("failed") || normalized.includes("error")) return "bad";
  if (normalized.includes("progress") || normalized.includes("running") || normalized.includes("started")) return "warn";
  return "neutral";
}

function renderWorkflowHandoff(payload) {
  const handoff = payload.workflow_handoff || payload.engine_state?.workflow_handoff || payload.engine_state?.handoff_status;
  const card = document.getElementById("workflowHandoffCard");
  if (!card) return;
  if (!handoff) {
    card.hidden = true;
    return;
  }

  card.hidden = false;
  const status = handoff.status || "reported";
  const statusPill = document.getElementById("workflowHandoffStatus");
  if (statusPill) {
    statusPill.className = `pill ${handoffStatusClass(status)}`;
    statusPill.textContent = `Status: ${fmt.text(status)}`;
  }

  const summary = document.getElementById("workflowHandoffSummary");
  if (summary) {
    const lines = [
      handoff.summary,
      handoff.current_step ? `Current step: ${handoff.current_step}` : null,
      handoff.updated_at_utc ? `Updated: ${handoff.updated_at_utc}` : null,
      handoff.source ? `Source: ${handoff.source}` : null,
    ].filter(Boolean);
    summary.innerHTML = lines.length
      ? lines.map((line) => `<p>${escapeHtml(line)}</p>`).join("")
      : "<p>No handoff summary recorded.</p>";
  }

  const list = document.getElementById("workflowHandoffList");
  if (!list) return;
  const tasks = handoff.tasks || handoff.steps || [];
  if (!tasks.length) {
    renderEmpty(list, "No task checklist recorded.");
    return;
  }

  list.innerHTML = tasks
    .map((task, index) => {
      const label = task.label || task.name || task.task || `Task ${index + 1}`;
      const taskStatus = task.status || "pending";
      const details = task.details || task.note || task.summary || "";
      return `
        <div class="handoff-item">
          <span class="badge ${handoffStatusClass(taskStatus)}">${escapeHtml(taskStatus)}</span>
          <div>
            <strong>${escapeHtml(label)}</strong>
            ${details ? `<p>${escapeHtml(details)}</p>` : ""}
          </div>
        </div>
      `;
    })
    .join("");
}

function renderDashboard(payload) {
  renderDeploymentIncident(payload);
  renderWorkflowHandoff(payload);
  renderEngineState(payload);

  const trades = payload.recent_trades || [];
  const disagreements = payload.disagreements || [];
  const summary = payload.regime_summary || {};

  setText("tradeCountStamp", trades.length ? `${trades.length} closed` : "None yet");
  setText("disagreementCountStamp", disagreements.length ? `${disagreements.length} rows` : "None");
  setText("summaryMetaStamp", `${summary.meta?.trade_count ?? trades.length} closed`);

  renderTable(
    document.getElementById("recentTradesWrap"),
    [
      { label: "Time", key: "timestamp_utc", value: (row) => escapeHtml(formatWhen(row.timestamp_utc, false)) },
      { label: "Symbol", key: "symbol", value: (row) => escapeHtml(fmt.text(row.symbol).replace("-USD", "")) },
      { label: "Side", key: "side", value: (row) => toneText(row.side || row.action) },
      { label: "Entry", key: "entry_price", numeric: true, value: (row) => fmt.price(row.entry_price) },
      { label: "Exit", key: "exit_price", numeric: true, value: (row) => fmt.price(row.exit_price) },
      { label: "PnL", key: "pnl_abs", numeric: true, value: (row) => signed(row.pnl_abs, money(row.pnl_abs)) },
      { label: "PnL %", key: "pnl_pct", numeric: true, value: (row) => signed(row.pnl_pct, fmt.pct(row.pnl_pct)) },
      { label: "Outcome", key: "outcome_label", value: (row) => toneText(row.outcome_label) },
      { label: "Regime", key: "deterministic_regime", value: (row) => toneText(row.deterministic_regime) },
      { label: "ML", key: "ml_regime", value: (row) => row.ml_regime ? toneText(row.ml_regime) : "—" },
    ],
    trades,
    "No closed trades yet.",
  );

  renderTable(
    document.getElementById("disagreementWrap"),
    [
      { label: "Time", key: "timestamp_utc", value: (row) => escapeHtml(formatWhen(row.timestamp_utc, false)) },
      { label: "Symbol", key: "symbol", value: (row) => escapeHtml(fmt.text(row.symbol).replace("-USD", "")) },
      { label: "Tape", key: "deterministic_regime", value: (row) => toneText(row.deterministic_regime) },
      { label: "Model", key: "ml_regime", value: (row) => toneText(row.ml_regime) },
      { label: "Confidence", key: "ml_confidence", numeric: true, value: (row) => fmt.pct(row.ml_confidence) },
      { label: "Note", key: "mismatch_text", value: (row) => escapeHtml(fmt.text(row.mismatch_text)) },
      { label: "Outcome", key: "outcome_label", value: (row) => toneText(row.outcome_label) },
    ],
    disagreements,
    "No disagreements in this window.",
  );

  renderSummary(
    document.getElementById("deterministicSummaryWrap"),
    summary.deterministic || [],
    "No deterministic summary available.",
  );

  renderSummary(
    document.getElementById("mlSummaryWrap"),
    summary.ml || [],
    "No ML summary available.",
  );
}

function pointsGap(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  const points = Math.round(n * 100);
  if (points > 0) return `+${points} pts`;
  if (points < 0) return `−${Math.abs(points)} pts`;
  return "0 pts";
}

function renderScorecard(data) {
  const engines = [...(data.engines || [])].sort((left, right) => (right.excess_return ?? -Infinity) - (left.excess_return ?? -Infinity));
  const assets = data.assets || [];
  const bestGap = engines[0];
  const bestHit = [...engines].sort((left, right) => (right.hit_rate_active ?? -1) - (left.hit_rate_active ?? -1))[0];
  const coinsAt60 = engines.reduce((sum, engine) => sum + (engine.assets_hit_rate_at_least_60 || 0), 0);
  const upDay = engines[0]?.market_up_day_rate;

  setText("scorecardStamp", data.eval_start && data.eval_end ? `${formatWhen(data.eval_start, false)} – ${formatWhen(data.eval_end, false)}` : "—");
  const note = document.getElementById("scorecardNote");
  if (note) {
    const count = assets.length || (data.universe || []).length;
    note.textContent = count
      ? `${count} coins, one window, 0.40% fee each time a position changes.`
      : "Same coins, same dates, same fee.";
  }

  const leads = document.getElementById("scorecardLeads");
  if (leads) {
    const rulesAt60 = engines.filter((engine) => engine.assets_hit_rate_at_least_60 > 0).map((engine) => engine.name);
    const gapHtml = (engine) => signed(engine.excess_return, escapeHtml(pointsGap(engine.excess_return)));
    const cards = [
      {
        label: "Closest to buy and hold",
        value: bestGap ? bestGap.name : "—",
        detail: bestGap ? `${fmt.pct(bestGap.total_return, 0)} return · ${gapHtml(bestGap)} vs buy and hold` : "—",
      },
      {
        label: "Best hit rate",
        value: bestHit ? fmt.pct(bestHit.hit_rate_active, 1) : "—",
        detail: bestHit ? `${escapeHtml(bestHit.name)} · ${bestHit.assets_hit_rate_at_least_60 || 0} coins at 60% or better` : "—",
      },
      {
        label: "Up-day rate",
        value: fmt.pct(upDay, 1),
        detail: "Share of days these coins closed higher",
      },
      {
        label: "Coins at 60% or better",
        value: String(coinsAt60),
        detail: rulesAt60.length ? escapeHtml(rulesAt60.join(", ")) : "No rule cleared that bar",
      },
    ];
    leads.innerHTML = cards
      .map(
        (card) => `
          <article class="stat">
            <p class="stat-k">${escapeHtml(card.label)}</p>
            <p class="stat-v">${escapeHtml(card.value)}</p>
            <p class="stat-d">${card.detail}</p>
          </article>
        `,
      )
      .join("");
  }

  const caveat = document.getElementById("scorecardCaveat");
  if (caveat) {
    const cerberus = engines.find((engine) => engine.id === "cerberus");
    const sisyphus = engines.find((engine) => engine.id === "sisyphus");
    const sentences = [
      cerberus
        ? `Cerberus hit ${fmt.pct(cerberus.hit_rate_active, 1)} and reached 60% on ${cerberus.assets_hit_rate_at_least_60 || 0} of these coins.`
        : null,
      sisyphus
        ? `Sisyphus hit ${fmt.pct(sisyphus.hit_rate_active, 1)} and cleared 60% on ${sisyphus.assets_hit_rate_at_least_60 || 0} coins, while staying in the market about ${fmt.pct(sisyphus.pct_in_market, 0)} of days.`
        : null,
      "A hit counts a day in the market when price moved with the position. Gap is percentage points versus buy and hold, after the 0.40% fee.",
      "Archived rules, rerun as published. This is a replay, not a live track record.",
    ].filter(Boolean);
    caveat.innerHTML = `<ul class="score-facts">${sentences.map((sentence) => `<li>${escapeHtml(sentence)}</li>`).join("")}</ul>`;
  }

  renderTable(
    document.getElementById("scorecardEngineWrap"),
    [
      { label: "Rule", key: "name", value: (row) => `<strong>${escapeHtml(row.name)}</strong>` },
      { label: "Hit rate", key: "hit_rate_active", numeric: true, value: (row) => `<span class="${row.hit_rate_active >= 0.6 ? "up" : ""}">${fmt.pct(row.hit_rate_active, 1)}</span>` },
      { label: "At 60%", key: "assets_hit_rate_at_least_60", numeric: true, value: (row) => fmt.int(row.assets_hit_rate_at_least_60) },
      { label: "Return", key: "total_return", numeric: true, value: (row) => signed(row.total_return, fmt.pct(row.total_return, 0)) },
      { label: "Buy and hold", key: "benchmark_return", numeric: true, value: (row) => signed(row.benchmark_return, fmt.pct(row.benchmark_return, 0)) },
      { label: "Gap", key: "excess_return", numeric: true, value: (row) => signed(row.excess_return, escapeHtml(pointsGap(row.excess_return))) },
      { label: "Drawdown", key: "max_drawdown", numeric: true, value: (row) => `<span class="down">${fmt.pct(row.max_drawdown, 0)}</span>` },
      { label: "In market", key: "pct_in_market", numeric: true, value: (row) => fmt.pct(row.pct_in_market, 0) },
      { label: "Trades", key: "trades", numeric: true, value: (row) => fmt.int(row.trades) },
    ],
    engines,
    "No scorecard rows yet.",
  );

  const assetRows = assets.map((asset) => {
    const byEngine = Object.fromEntries((asset.engines || []).map((engine) => [engine.engine, engine]));
    return { ...asset, byEngine };
  });
  const hitCell = (engineId) => (row) => {
    const metrics = row.byEngine[engineId];
    if (!metrics || metrics.hit_rate_active === null || metrics.hit_rate_active === undefined) return "—";
    const hitTone = metrics.hit_rate_active >= 0.6 ? "up" : "";
    return `<span class="pair"><span class="${hitTone}">${fmt.pct(metrics.hit_rate_active, 1)}</span><span class="pair-ret">${signed(metrics.total_return, fmt.pct(metrics.total_return, 0))}</span></span>`;
  };
  renderTable(
    document.getElementById("scorecardAssetWrap"),
    [
      { label: "Coin", key: "symbol", value: (row) => `<strong>${escapeHtml(String(row.symbol).replace("-USD", ""))}</strong>` },
      { label: "Buy and hold", key: "benchmark_return", numeric: true, value: (row) => signed(row.benchmark_return, fmt.pct(row.benchmark_return, 0)) },
      { label: "Up days", key: "market_up_day_rate", numeric: true, value: (row) => fmt.pct(row.market_up_day_rate, 1) },
      { label: "Cerberus", key: "cerberus", numeric: true, value: hitCell("cerberus") },
      { label: "Orthrus", key: "orthrus", numeric: true, value: hitCell("orthrus") },
      { label: "Hydra", key: "hydra", numeric: true, value: hitCell("hydra") },
      { label: "Sisyphus", key: "sisyphus", numeric: true, value: hitCell("sisyphus") },
    ],
    assetRows,
    "No per-coin rows yet.",
  );
}

async function loadScorecard() {
  const path = window.TEMPLATE_CONFIG?.scorecardPath || "./scorecard.json";
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) throw new Error(`Scorecard fetch failed: ${res.status}`);
  renderScorecard(await res.json());
}

async function loadTemplateConfig() {
  try {
    const res = await fetch("./template.config.json", { cache: "no-store" });
    if (!res.ok) return;
    const config = await res.json();
    window.TEMPLATE_CONFIG = config;
    if (config.productName) {
      const title = document.querySelector("h1");
      if (title) title.textContent = config.productName;
      document.title = config.productName;
    }
    if (config.subtitle) {
      const subtitle = document.querySelector(".subtitle");
      if (subtitle) subtitle.textContent = config.subtitle;
    }
  } catch (error) {
    console.error(error);
  }
}

async function loadDashboard() {
  if (DASHBOARD_MODE === "demo") {
    const payload = await loadBundledDashboardState();
    renderDashboard(payload);
    return payload;
  }
  if (!dashboardEndpoint()) {
    throw new Error("Paste an API base and save it.");
  }
  const res = await fetch(dashboardEndpoint(), { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`Dashboard fetch failed: ${res.status}`);
  }
  const raw = await res.json();
  const payload = (DASHBOARD_MODE === "remote" || DASHBOARD_MODE === "remoteControl") ? buildRemoteDashboardPayload(raw) : normalizeDashboardPayload(raw);
  renderDashboard(payload);
  return payload;
}

async function refreshDashboard() {
  let ok = true;
  const now = new Date();
  try {
    await loadDashboard();
  } catch (error) {
    ok = false;
    console.error(error);
    const lastError = document.getElementById("lastErrorText");
    if (lastError) lastError.textContent = `Last error: ${error.message}`;
    try {
      const fallbackPayload = await loadBundledDashboardState();
      renderDashboard(fallbackPayload);
      if (lastError) lastError.textContent = `Last error: ${error.message}; showing bundled static state.`;
    } catch (fallbackError) {
      console.error(fallbackError);
      if (lastError) lastError.textContent = `Last error: ${error.message}; static fallback failed: ${fallbackError.message}`;
    }
  }

  try {
    await loadScorecard();
  } catch (error) {
    ok = false;
    console.error(error);
    const lastError = document.getElementById("lastErrorText");
    if (lastError) lastError.textContent = `Last error: ${error.message}`;
    const caveat = document.getElementById("scorecardCaveat");
    if (caveat) caveat.textContent = "The scorecard file did not load. From the project folder run python3 scripts/build_regime_scorecard.py.";
  }

  try {
    await loadProcesses();
  } catch (error) {
    ok = false;
    console.error(error);
    const lastError = document.getElementById("lastErrorText");
    if (lastError) lastError.textContent = `Last error: ${error.message}`;
  }

  document.body.dataset.status = ok ? "ok" : "error";
  const successText = document.getElementById("lastSuccessText");
  const reachabilityText = document.getElementById("backendReachabilityText");
  const lastError = document.getElementById("lastErrorText");
  if (ok && lastError) lastError.textContent = "";
  if (successText && ok) successText.textContent = DASHBOARD_MODE === "demo" ? `Sample loaded ${formatWhen(now.toISOString())}` : `Last fetch ${formatWhen(now.toISOString())}`;
  if (reachabilityText) {
    reachabilityText.textContent = DASHBOARD_MODE === "demo"
      ? "Demo sample loaded. No engine API was called."
      : `Backend reachable: ${ok ? "yes" : "no"}`;
  }
  if (!ok) {
    const footer = document.getElementById("dashboardUpdated");
    if (footer) footer.textContent = "Last updated: unavailable";
  }
}

async function boot() {
  await loadTemplateConfig();
  if (!localStorage.getItem(MODE_STORAGE_KEY)) {
    setMode(window.TEMPLATE_CONFIG?.defaultMode || DEFAULT_MODE);
  }
  initBackendControls();

renderProcessCards({ services: DEFAULT_PROCESS_SERVICES.map((service) => ({
  ...service,
  status: "stopped",
  pid: null,
  start_time_utc: null,
  stop_time_utc: null,
  exit_code: null,
  last_error: null,
  last_output_at_utc: null,
  last_file_update_at_utc: null,
  last_heartbeat_at_utc: null,
  last_stdout_tail: [],
  last_stderr_tail: [],
  script_path: null,
  command_display: null,
  launch_command: null,
  monitored_paths: [],
})) });

await refreshDashboard();
setInterval(refreshDashboard, REFRESH_MS);
setInterval(() => loadProcesses().catch((error) => console.error(error)), PROCESS_REFRESH_MS);
}

boot();

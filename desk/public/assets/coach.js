(() => {
  const STORAGE_KEY = "nexus-desk-coach-v4";
  const state = (() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") || {};
    } catch {
      return {};
    }
  })();

  const STEPS = [
    {
      title: "You are on paper",
      body: "This desk starts in <strong>paper mode</strong>. It watches public market data and simulates trades. No exchange keys. Nothing here can spend real money until you deliberately turn live on later.",
    },
    {
      title: "Watch Status tick",
      body: "Stay on <strong>Status</strong>. Look for heartbeat / engine status updating. If it ticks, your desk is running — you’re in.",
    },
    {
      title: "Use the left rail",
      body: "<strong>Market</strong> = prices. <strong>Engine</strong> = paper loop. <strong>Control</strong> = arming. <strong>Settings</strong> = knobs. <strong>Logs</strong> / <strong>Instance</strong> = what’s running.",
    },
    {
      title: "Live later — optional",
      body: `Only after paper feels boring-in-a-good-way. Create Kraken keys at <a href="https://www.kraken.com/u/security/api" target="_blank" rel="noopener noreferrer">kraken.com/u/security/api</a>. Minimum permissions. Paste <code>KRAKEN_API_KEY</code> / <code>SECRET</code> in Railway, then flip paper-only / live-arm only when you mean it.`,
    },
  ];

  const root = document.createElement("div");
  root.className = "nexus-coach-root";
  root.innerHTML = `
    <button type="button" class="nexus-coach-fab" data-coach-open hidden>New here?</button>
    <section class="nexus-coach-panel" data-coach-panel hidden aria-label="Nexus desk starter guide">
      <div class="nexus-coach-head">
        <div>
          <p class="nexus-coach-kicker">Feet wet · not flintstones</p>
          <h2 class="nexus-coach-title">Welcome to the desk</h2>
        </div>
        <button type="button" class="nexus-coach-close" data-coach-minimize aria-label="Minimize guide">×</button>
      </div>
      <div class="nexus-coach-steps" data-coach-steps></div>
      <div class="nexus-coach-actions">
        <button type="button" class="primary" data-coach-got-it>Got it — I’m on paper</button>
        <button type="button" data-coach-minimize>Keep this for later</button>
      </div>
    </section>
  `;

  const panel = root.querySelector("[data-coach-panel]");
  const fab = root.querySelector("[data-coach-open]");
  const stepsHost = root.querySelector("[data-coach-steps]");

  stepsHost.innerHTML = STEPS.map(
    (step, i) => `
    <article class="nexus-coach-step">
      <p class="nexus-coach-step-num">Step ${String(i + 1).padStart(2, "0")}</p>
      <h3>${step.title}</h3>
      <p>${step.body}</p>
    </article>`
  ).join("");

  function persist(next) {
    Object.assign(state, next, { updatedAt: Date.now() });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* ignore */
    }
  }

  function showPanel(open) {
    panel.hidden = !open;
    fab.hidden = open;
  }

  function openCoach() {
    showPanel(true);
    persist({ dismissed: false });
  }

  function minimizeCoach() {
    showPanel(false);
    persist({ dismissed: true });
  }

  root.querySelector("[data-coach-open]").addEventListener("click", openCoach);
  root.querySelectorAll("[data-coach-minimize]").forEach((el) => {
    el.addEventListener("click", minimizeCoach);
  });
  root.querySelector("[data-coach-got-it]").addEventListener("click", () => {
    persist({ dismissed: true, completed: true });
    showPanel(false);
  });

  function boot() {
    if (!document.querySelector(".nexus-atmos")) {
      const atmos = document.createElement("div");
      atmos.className = "nexus-atmos";
      atmos.setAttribute("aria-hidden", "true");
      document.body.prepend(atmos);
    }
    document.body.appendChild(root);
    if (state.completed || state.dismissed) showPanel(false);
    else showPanel(true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();

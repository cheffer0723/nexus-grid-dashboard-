(() => {
  const STORAGE_KEY = "nexus-desk-coach-v1";
  const state = (() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") || {};
    } catch {
      return {};
    }
  })();

  const STARTER = [
    {
      eyebrow: "Step 01",
      accent: "var(--nexus-vault, #22d3ee)",
      title: "You are on paper",
      body: "This desk starts in <strong>paper mode</strong>. It watches public market data and simulates trades. No exchange keys. Nothing here can spend real money until you deliberately turn live on later.",
    },
    {
      eyebrow: "Step 02",
      accent: "var(--nexus-observer, #f97316)",
      title: "Watch Observe tick",
      body: "Stay on <strong>Observe</strong>. Look for heartbeat / engine status updating. If it ticks, your desk is running — you’re in.",
    },
    {
      eyebrow: "Step 03",
      accent: "var(--nexus-gateway, #3b82f6)",
      title: "Learn the left rail",
      body: "Gateway = market feed. Core = engine. Sentinel = safety lock. Vault = settings. Observer = what’s happening. Spin the Agents deck for the marks.",
    },
    {
      eyebrow: "Step 04",
      accent: "var(--nexus-sentinel, #eab308)",
      title: "Live later — optional",
      body: `Only after paper feels boring-in-a-good-way. Create Kraken keys at <a href="https://www.kraken.com/u/security/api" target="_blank" rel="noopener noreferrer">kraken.com/u/security/api</a>. Minimum permissions. Paste <code>KRAKEN_API_KEY</code> / <code>SECRET</code>, then flip paper-only / live-arm only when you mean it. Sentinel still gates arming.`,
    },
  ];

  const AGENTS = [
    {
      eyebrow: "Gateway",
      accent: "var(--nexus-gateway, #3b82f6)",
      media: "/brand/agents/gateway.png",
      title: "Ingest. Connect. Enter.",
      body: "Market feed / prices coming in. This is how the desk sees the world.",
    },
    {
      eyebrow: "Core",
      accent: "var(--nexus-core, #a855f7)",
      media: "/brand/agents/core.png",
      title: "Execute. Adapt. Evolve.",
      body: "The paper engine doing the work — loops, signals, decisions.",
    },
    {
      eyebrow: "Vault",
      accent: "var(--nexus-vault, #22d3ee)",
      media: "/brand/agents/vault.png",
      title: "Store. Structure. Remember.",
      body: "Settings: symbol, size, stops. Your knobs without touching code.",
    },
    {
      eyebrow: "Sentinel",
      accent: "var(--nexus-sentinel, #eab308)",
      media: "/brand/agents/sentinel.png",
      title: "Protect. Defend. Preserve.",
      body: "Safety lock. Live arming stays gated until you opt in on purpose.",
    },
    {
      eyebrow: "Observer",
      accent: "var(--nexus-observer, #f97316)",
      media: "/brand/agents/observer.png",
      title: "Analyze. Learn. Anticipate.",
      body: "What’s happening right now — status, logs, heartbeat.",
    },
  ];

  const root = document.createElement("div");
  root.className = "nexus-coach-root nexus-coach-root--ring";
  root.innerHTML = `
    <button type="button" class="nexus-coach-fab" data-coach-open hidden>New here?</button>
    <section class="nexus-coach-panel nexus-coach-panel--ring" data-coach-panel hidden aria-label="Nexus desk starter guide">
      <div class="nexus-coach-head">
        <div>
          <p class="nexus-coach-kicker">Feet wet · not flintstones</p>
          <h2 class="nexus-coach-title">Welcome to the desk</h2>
        </div>
        <button type="button" class="nexus-coach-close" data-coach-minimize aria-label="Minimize guide">×</button>
      </div>

      <div class="nexus-coach-tabs" role="tablist">
        <button type="button" class="is-active" data-deck="starter" role="tab" aria-selected="true">Starter</button>
        <button type="button" data-deck="agents" role="tab" aria-selected="false">Agents</button>
      </div>

      <div data-ring-host class="nexus-coach-ring-host"></div>

      <div class="nexus-coach-actions">
        <button type="button" class="primary" data-coach-got-it>Got it — I’m on paper</button>
        <button type="button" data-coach-minimize>Keep this for later</button>
      </div>
    </section>
  `;

  const panel = root.querySelector("[data-coach-panel]");
  const fab = root.querySelector("[data-coach-open]");
  const host = root.querySelector("[data-ring-host]");
  let ring = null;
  let deck = "starter";

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
    if (open) mountDeck(deck);
  }

  function mountDeck(name) {
    deck = name;
    root.querySelectorAll(".nexus-coach-tabs button").forEach((btn) => {
      const on = btn.dataset.deck === name;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
    if (ring) ring.destroy();
    const items = name === "agents" ? AGENTS : STARTER;
    if (!window.NexusRing) return;
    ring = window.NexusRing.create(host, items, {
      accent: name === "agents" ? "var(--nexus-gateway, #3b82f6)" : "var(--nexus-vault, #22d3ee)",
    });
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
  root.querySelectorAll(".nexus-coach-tabs button").forEach((btn) => {
    btn.addEventListener("click", () => mountDeck(btn.dataset.deck));
  });

  function boot() {
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

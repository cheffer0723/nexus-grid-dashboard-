(() => {
  const STORAGE_KEY = "nexus-desk-coach-v1";
  const state = (() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") || {};
    } catch {
      return {};
    }
  })();

  const root = document.createElement("div");
  root.className = "nexus-coach-root";
  root.innerHTML = `
    <button type="button" class="nexus-coach-fab" data-coach-open hidden>New here?</button>
    <section class="nexus-coach-panel" data-coach-panel hidden aria-label="Nexus desk starter guide">
      <div class="nexus-coach-head">
        <div>
          <p class="nexus-coach-kicker">Feet wet · not live yet</p>
          <h2 class="nexus-coach-title">Welcome to the desk</h2>
        </div>
        <button type="button" class="nexus-coach-close" data-coach-minimize aria-label="Minimize guide">×</button>
      </div>

      <div class="nexus-coach-step">
        <h3>1. You are on paper money</h3>
        <p>
          This template starts in <strong>paper mode</strong>. It watches public market data and
          simulates trades. No exchange keys. Nothing here can spend real money until you
          deliberately turn live on later.
        </p>
      </div>

      <div class="nexus-coach-step">
        <h3>2. First thing to check</h3>
        <ol>
          <li>Stay on <strong>Observe</strong> (home).</li>
          <li>Look for heartbeat / engine status updating.</li>
          <li>If it ticks, your desk is running. You’re in.</li>
        </ol>
      </div>

      <div class="nexus-coach-step">
        <h3>3. What the left words mean</h3>
        <ul class="nexus-coach-agents">
          <li><span class="nexus-coach-dot" style="--c:var(--nexus-observer,#f97316)"></span><strong>Observe</strong><span>What’s happening right now</span></li>
          <li><span class="nexus-coach-dot" style="--c:var(--nexus-gateway,#3b82f6)"></span><strong>Gateway</strong><span>Market feed / prices coming in</span></li>
          <li><span class="nexus-coach-dot" style="--c:var(--nexus-core,#a855f7)"></span><strong>Core</strong><span>The paper engine doing the work</span></li>
          <li><span class="nexus-coach-dot" style="--c:var(--nexus-sentinel,#eab308)"></span><strong>Sentinel</strong><span>Safety lock — live stays gated</span></li>
          <li><span class="nexus-coach-dot" style="--c:var(--nexus-vault,#22d3ee)"></span><strong>Vault</strong><span>Settings (symbol, size, stops)</span></li>
        </ul>
      </div>

      <div class="nexus-coach-step nexus-coach-warn">
        <h3>4. Want live later? Keys are optional — and careful</h3>
        <p>
          Only after paper feels boring-in-a-good-way. Live needs Kraken API keys in Railway
          variables, plus flipping paper-only / live-arm flags on purpose.
        </p>
        <ol>
          <li>
            Create keys in your Kraken account:
            <a href="https://www.kraken.com/u/security/api" target="_blank" rel="noopener noreferrer">kraken.com/u/security/api</a>
            (or Kraken’s guide:
            <a href="https://support.kraken.com/articles/360000919966-how-to-generate-an-api-key-pair" target="_blank" rel="noopener noreferrer">how to generate an API key pair</a>).
          </li>
          <li>Permissions: start with the minimum needed for trading you intend — never withdraw if you don’t need it.</li>
          <li>Paste into Railway as <code>KRAKEN_API_KEY</code> and <code>KRAKEN_API_SECRET</code>.</li>
          <li>Then set <code>NEXUS_PAPER_ONLY=0</code> and <code>NEXUS_DASHBOARD_ALLOW_LIVE_ARM=1</code> only when you mean it.</li>
        </ol>
        <p style="margin-top:0.55rem">
          Sentinel still blocks live arming until those flags and confirmations are set.
          If you’re unsure, stay paper.
        </p>
      </div>

      <div class="nexus-coach-actions">
        <button type="button" class="primary" data-coach-got-it>Got it — I’m on paper</button>
        <button type="button" data-coach-minimize>Keep this for later</button>
      </div>
    </section>
  `;

  const panel = root.querySelector("[data-coach-panel]");
  const fab = root.querySelector("[data-coach-open]");

  function persist(next) {
    Object.assign(state, next, { updatedAt: Date.now() });
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch {
      /* ignore quota / private mode */
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

  document.body.appendChild(root);

  // First visit: open. Returning visitors who dismissed: FAB only.
  if (state.completed || state.dismissed) {
    showPanel(false);
  } else {
    showPanel(true);
  }
})();

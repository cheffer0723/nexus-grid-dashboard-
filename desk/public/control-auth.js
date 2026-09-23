(() => {
  const storageKey = "NEXUS_CONTROL_PASSWORD";
  const protectedPaths = new Set(["/api/command", "/api/settings"]);
  const originalFetch = window.fetch.bind(window);

  function isProtectedWrite(resource, init) {
    const method = String(init?.method || "GET").toUpperCase();
    if (method === "GET" || method === "HEAD" || method === "OPTIONS") return false;
    try {
      const url = new URL(typeof resource === "string" ? resource : resource.url, window.location.origin);
      return protectedPaths.has(url.pathname);
    } catch {
      return false;
    }
  }

  window.fetch = (resource, init = {}) => {
    if (!isProtectedWrite(resource, init)) return originalFetch(resource, init);
    const password = String(localStorage.getItem(storageKey) || "").trim();
    const headers = new Headers(init.headers || {});
    if (password && !headers.has("x-nexus-control-password")) {
      headers.set("x-nexus-control-password", password);
    }
    return originalFetch(resource, { ...init, headers });
  };

  function pct(n, d) {
    if (!Number.isFinite(n)) return "—";
    const body = `${Math.abs(n * 100).toFixed(d)}%`;
    return n < 0 ? `−${body}` : body;
  }
  function pts(n) {
    if (!Number.isFinite(n)) return "—";
    const v = Math.round(n * 100);
    return `${v < 0 ? "−" : v > 0 ? "+" : ""}${Math.abs(v)} pts`;
  }

  async function refreshScorecard() {
    const panel = document.getElementById("nexus-scorecard-panel");
    if (!panel) return;
    const body = panel.querySelector(".nexus-scorecard-body");
    try {
      const res = await originalFetch("/scorecard.json", { cache: "no-store" });
      if (!res.ok) throw new Error("missing");
      const data = await res.json();
      const rows = [...(data.engines || [])].sort(
        (a, b) => (b.excess_return ?? -Infinity) - (a.excess_return ?? -Infinity),
      );
      body.innerHTML =
        rows
          .map((row) => {
            const gap = Number(row.excess_return);
            const tone = gap > 0 ? "up" : "down";
            return `<div class="nexus-scorecard-row"><span>${row.name}</span><span>${pct(row.hit_rate_active, 1)}</span><span class="${tone}">${pts(gap)}</span></div>`;
          })
          .join("") || "No rows.";
    } catch {
      body.textContent = "Optional. Set NEXUS_SCORECARD_URL or ship scorecard.json.";
    }
  }

  function renderScorecard() {
    if (!/^\/(|status|core|market)\/?$/.test(location.pathname)) {
      document.getElementById("nexus-scorecard-panel")?.remove();
      return;
    }
    if (!document.getElementById("nexus-scorecard-panel")) {
      const panel = document.createElement("section");
      panel.id = "nexus-scorecard-panel";
      panel.innerHTML = `<div class="nexus-scorecard-heading"><span>Regime scorecard</span><button type="button" class="nexus-scorecard-toggle" data-scorecard-toggle aria-expanded="true">Hide</button></div><div class="nexus-scorecard-body">Loading…</div><div class="nexus-scorecard-note">Research replay from Critical-Mass-Lab. This does not trade.</div>`;
      document.body.appendChild(panel);
      panel.querySelector("[data-scorecard-toggle]")?.addEventListener("click", () => {
        const collapsed = panel.classList.toggle("is-collapsed");
        const btn = panel.querySelector("[data-scorecard-toggle]");
        if (btn) {
          btn.textContent = collapsed ? "Show" : "Hide";
          btn.setAttribute("aria-expanded", collapsed ? "false" : "true");
        }
        try {
          localStorage.setItem("nexus-scorecard-collapsed", collapsed ? "1" : "0");
        } catch {}
      });
      try {
        const mobile = window.matchMedia("(max-width: 1023px)").matches;
        const stored = localStorage.getItem("nexus-scorecard-collapsed");
        // On mobile, default collapsed so the toolbar stays usable until they open it
        if (stored === "1" || (stored == null && mobile)) {
          panel.classList.add("is-collapsed");
          const btn = panel.querySelector("[data-scorecard-toggle]");
          if (btn) {
            btn.textContent = "Show";
            btn.setAttribute("aria-expanded", "false");
          }
        }
      } catch {}
    }
    refreshScorecard();
  }

  function renderAuth() {
    if (!/^\/(controls|settings)\/?$/.test(location.pathname)) {
      document.getElementById("nexus-control-auth-panel")?.remove();
      return;
    }
    if (document.getElementById("nexus-control-auth-panel")) return;
    const panel = document.createElement("section");
    panel.id = "nexus-control-auth-panel";
    panel.innerHTML = `
      <div class="nexus-control-auth-title">Protected controls</div>
      <div class="nexus-control-auth-row">
        <input id="nexus-control-auth-input" type="password" placeholder="Control password (optional)" />
        <button id="nexus-control-auth-save" type="button">Save</button>
        <button id="nexus-control-auth-clear" type="button">Clear</button>
      </div>
      <div id="nexus-control-auth-status" class="nexus-control-auth-status"></div>`;
    document.body.appendChild(panel);
    const input = panel.querySelector("#nexus-control-auth-input");
    const status = panel.querySelector("#nexus-control-auth-status");
    input.value = localStorage.getItem(storageKey) || "";
    status.textContent = input.value
      ? "Password saved in this browser."
      : "Paper viewing is open. Set NEXUS_CONTROL_PASSWORD in Railway only if you want to lock writes.";
    panel.querySelector("#nexus-control-auth-save").onclick = () => {
      const value = String(input.value || "").trim();
      if (value) localStorage.setItem(storageKey, value);
      else localStorage.removeItem(storageKey);
      status.textContent = value ? "Password saved." : "Password cleared.";
    };
    panel.querySelector("#nexus-control-auth-clear").onclick = () => {
      input.value = "";
      localStorage.removeItem(storageKey);
      status.textContent = "Password cleared.";
    };
  }

  const style = document.createElement("style");
  style.textContent = `
    #nexus-control-auth-panel,#nexus-scorecard-panel{position:fixed;z-index:45;width:min(22rem,calc(100vw - 2rem));padding:.85rem;border:1px solid rgba(0,229,255,.35);border-radius:1rem;background:rgba(4,8,20,.94);color:#eaf8ff;font:12px ui-monospace,Menlo,Consolas,monospace;backdrop-filter:blur(14px)}
    #nexus-control-auth-panel{right:1rem;bottom:5.6rem}
    #nexus-scorecard-panel{right:1rem;bottom:1rem;z-index:40}
    .nexus-control-auth-title,.nexus-scorecard-heading{display:flex;justify-content:space-between;align-items:center;gap:.5rem;color:#36e7ff;font-weight:800;letter-spacing:.14em;text-transform:uppercase;margin-bottom:.5rem}
    .nexus-control-auth-row{display:grid;grid-template-columns:1fr auto auto;gap:.45rem}
    #nexus-control-auth-input{min-width:0;height:2.4rem;border:1px solid rgba(145,92,255,.45);border-radius:.65rem;background:rgba(0,0,0,.38);color:#fff;padding:0 .7rem}
    #nexus-control-auth-save,#nexus-control-auth-clear{height:2.4rem;border:1px solid rgba(54,231,255,.42);border-radius:.65rem;background:rgba(54,231,255,.08);color:#36e7ff;padding:0 .7rem;font:inherit;font-weight:800;cursor:pointer}
    .nexus-scorecard-row{display:grid;grid-template-columns:1fr auto auto;gap:.8rem;margin-top:.35rem}
    .nexus-scorecard-row .up{color:#49e6c1}.nexus-scorecard-row .down{color:#ef70c5}
    .nexus-scorecard-note,.nexus-control-auth-status{margin-top:.45rem;color:rgba(234,248,255,.65);line-height:1.4}
    .nexus-scorecard-toggle{border:1px solid rgba(54,231,255,.35);border-radius:.55rem;background:rgba(54,231,255,.08);color:#36e7ff;font:inherit;font-weight:800;letter-spacing:.08em;text-transform:uppercase;padding:.2rem .45rem;cursor:pointer}
    #nexus-scorecard-panel.is-collapsed .nexus-scorecard-body,
    #nexus-scorecard-panel.is-collapsed .nexus-scorecard-note{display:none}
    #nexus-scorecard-panel.is-collapsed{padding:.65rem .85rem}
    /* Mobile bottom toolbar is h-20 / sm:h-24 at z-50 — keep scorecard above it, under chrome */
    @media (max-width:1023px){
      #nexus-scorecard-panel{
        right:.65rem;left:.65rem;width:auto;
        bottom:calc(5rem + .75rem);
        max-height:min(34vh,14.5rem);
        overflow:auto;
        z-index:40;
      }
      #nexus-control-auth-panel{
        bottom:calc(5rem + .75rem);
        z-index:41;
      }
    }
    @media (max-width:1023px) and (min-width:640px){
      #nexus-scorecard-panel,#nexus-control-auth-panel{bottom:calc(6rem + .75rem)}
    }
    @media (min-width:1024px){
      #nexus-scorecard-panel{bottom:1rem;left:auto;width:min(22rem,calc(100vw - 2rem))}
    }
  `;

  function boot() {
    document.head.appendChild(style);
    renderAuth();
    renderScorecard();
  }
  if (document.body) boot();
  else document.addEventListener("DOMContentLoaded", boot);
  window.addEventListener("popstate", () => setTimeout(() => { renderAuth(); renderScorecard(); }, 0));
  document.addEventListener("click", () => setTimeout(() => { renderAuth(); renderScorecard(); }, 0), true);
})();

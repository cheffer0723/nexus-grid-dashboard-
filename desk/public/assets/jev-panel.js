(() => {
  const ROOT = "[data-nexus-jev-panel]";

  function pct(n) {
    if (n == null || Number.isNaN(Number(n))) return "—";
    const v = Number(n);
    // desk confidence is 0-1; conviction score is 0-4
    if (v <= 1.5) return `${Math.round(v * 100)}%`;
    return v.toFixed(2);
  }

  function money(n) {
    if (n == null || Number.isNaN(Number(n))) return "—";
    return Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 });
  }

  function agreeClass(a) {
    if (a === "agree") return "is-agree";
    if (a === "disagree") return "is-disagree";
    if (a === "partial") return "is-partial";
    return "";
  }

  function buildShell() {
    const el = document.createElement("section");
    el.className = "nexus-jev-panel nexus-panel";
    el.setAttribute("data-nexus-jev-panel", "");
    el.innerHTML = `
      <div class="nexus-jev-panel__head">
        <div>
          <p class="nexus-jev-panel__kicker">Core · paper research</p>
          <h3 class="nexus-jev-panel__title">Jev vs desk signal</h3>
        </div>
        <button type="button" class="nexus-jev-panel__ask" data-jev-ask>Ask Jev</button>
      </div>
      <p class="nexus-jev-panel__note" data-jev-note>Loading…</p>
      <div class="nexus-jev-panel__grid">
        <article class="nexus-jev-card" data-jev-desk>
          <p class="nexus-jev-card__label">Desk (rules)</p>
          <p class="nexus-jev-card__value" data-desk-action>—</p>
          <p class="nexus-jev-card__meta" data-desk-meta></p>
        </article>
        <article class="nexus-jev-card" data-jev-model>
          <p class="nexus-jev-card__label">Jev (System One)</p>
          <p class="nexus-jev-card__value" data-jev-action>—</p>
          <p class="nexus-jev-card__meta" data-jev-meta></p>
        </article>
      </div>
      <div class="nexus-jev-panel__agreement">
        <span class="nexus-jev-panel__agree-label">Agreement</span>
        <strong data-jev-agree class="">n/a</strong>
      </div>
      <div class="nexus-jev-panel__extras" data-jev-extras hidden></div>
      <div class="nexus-jev-panel__history">
        <p class="nexus-jev-panel__hist-label">Recent compares</p>
        <div data-jev-history class="nexus-jev-panel__hist-list">No asks yet.</div>
      </div>
      <p class="nexus-jev-panel__disclaimer">
        Paper research only. Jev never arms live on this desk.
      </p>
    `;

    el.querySelector("[data-jev-ask]").addEventListener("click", () => load(true));
    return el;
  }

  function renderHistory(el, rows) {
    const host = el.querySelector("[data-jev-history]");
    if (!rows?.length) {
      host.textContent = "No asks yet.";
      return;
    }
    host.innerHTML = rows
      .slice(0, 8)
      .map((r) => {
        const cls = agreeClass(r.agreement);
        return `<div class="nexus-jev-hist ${cls}">
          <span>${r.deskAction || "—"} → ${r.jevDirection || "—"}</span>
          <span>${r.agreement || "n/a"}</span>
          <span>${(r.at || "").replace("T", " ").slice(0, 19)}</span>
        </div>`;
      })
      .join("");
  }

  function paint(el, data) {
    const note = el.querySelector("[data-jev-note]");
    const ask = el.querySelector("[data-jev-ask]");
    note.textContent = data.message || data.disclaimer || "";
    ask.disabled = !data.configured;
    ask.textContent = data.configured ? (ask.dataset.busy === "1" ? "Asking…" : "Ask Jev") : "Needs API key";

    const desk = data.desk || {};
    el.querySelector("[data-desk-action]").textContent = desk.action || "WAIT";
    el.querySelector("[data-desk-meta]").textContent = [
      desk.symbol || "",
      desk.price != null ? `$${money(desk.price)}` : "",
      desk.confidence != null ? `conf ${pct(desk.confidence)}` : "",
      desk.rsi14 != null ? `rsi ${Number(desk.rsi14).toFixed(1)}` : "",
    ]
      .filter(Boolean)
      .join(" · ");

    const jev = data.jev;
    const jevAction = el.querySelector("[data-jev-action]");
    const jevMeta = el.querySelector("[data-jev-meta]");
    const extras = el.querySelector("[data-jev-extras]");
    if (jev) {
      jevAction.textContent = String(jev.direction || "flat").toUpperCase();
      jevMeta.textContent = [
        jev.directionConfidence != null ? `conf ${pct(jev.directionConfidence)}` : "",
        jev.conviction != null ? `conviction ${Number(jev.conviction).toFixed(2)}` : "",
        jev.takeTrade != null ? `take ${(Number(jev.takeTrade) * 100).toFixed(0)}%` : "",
        jev.latencyMs != null ? `${jev.latencyMs}ms` : "",
      ]
        .filter(Boolean)
        .join(" · ");
      const probs = jev.directionProbabilities || {};
      extras.hidden = false;
      extras.innerHTML = Object.keys(probs).length
        ? `<p>Direction mix: ${Object.entries(probs)
            .map(([k, v]) => `${k} ${(Number(v) * 100).toFixed(0)}%`)
            .join(" · ")}</p>`
        : "";
    } else {
      jevAction.textContent = data.configured ? "—" : "OFF";
        jevMeta.textContent = data.configured
        ? `Press Ask Jev for one evaluation${data.provider ? ` (${data.provider})` : ""}`
        : "Set OPENROUTER_API_KEY on Railway";
      extras.hidden = true;
      extras.innerHTML = "";
    }

    const agree = el.querySelector("[data-jev-agree]");
    agree.textContent = data.agreement || "n/a";
    agree.className = agreeClass(data.agreement);
    renderHistory(el, data.history || []);
  }

  async function load(run) {
    const el = document.querySelector(ROOT);
    if (!el) return;
    const ask = el.querySelector("[data-jev-ask]");
    const note = el.querySelector("[data-jev-note]");
    if (run) {
      ask.dataset.busy = "1";
      ask.disabled = true;
      ask.textContent = "Asking…";
      note.textContent = "Calling TypeSafe System One…";
    }
    try {
      const url = `/api/jev/compare${run ? "?run=1" : ""}`;
      const res = await fetch(url, { cache: "no-store" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || data.message || `HTTP ${res.status}`);
      paint(el, data);
    } catch (err) {
      note.textContent = `Jev panel error: ${err.message || err}`;
    } finally {
      if (ask) {
        ask.dataset.busy = "0";
      }
    }
  }

  function findAnchor() {
    const headings = document.querySelectorAll("h2, h1");
    for (const h of headings) {
      if (/core ai/i.test(h.textContent || "")) {
        return h.closest(".space-y-6") || h.parentElement;
      }
    }
    return document.querySelector("main") || document.querySelector("#root");
  }

  function mount() {
    if (location.pathname !== "/core") {
      document.querySelector(ROOT)?.remove();
      return;
    }
    if (document.querySelector(ROOT)) return;
    const anchor = findAnchor();
    if (!anchor) return;
    const el = buildShell();
    if (anchor.classList?.contains("space-y-6")) {
      const first = anchor.firstElementChild;
      if (first?.nextSibling) anchor.insertBefore(el, first.nextSibling);
      else anchor.appendChild(el);
    } else {
      anchor.prepend(el);
    }
    load(false);
  }

  const boot = () => {
    mount();
    setInterval(mount, 800);
    window.addEventListener("popstate", () => setTimeout(mount, 50));
    ["pushState", "replaceState"].forEach((method) => {
      const orig = history[method];
      history[method] = function (...args) {
        const ret = orig.apply(this, args);
        setTimeout(mount, 50);
        return ret;
      };
    });
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();

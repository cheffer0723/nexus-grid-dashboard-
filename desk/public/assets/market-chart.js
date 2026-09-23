(() => {
  const ROOT_SEL = "[data-nexus-market-chart]";
  const SYMBOLS = ["BTC/USD", "ETH/USD"];
  const INTERVALS = [
    { value: 1, label: "1m" },
    { value: 5, label: "5m" },
    { value: 15, label: "15m" },
    { value: 60, label: "1h" },
  ];

  let symbol = "BTC/USD";
  let interval = 5;
  let timer = null;
  let loading = false;

  function money(n) {
    if (n == null || Number.isNaN(n)) return "—";
    return n.toLocaleString(undefined, {
      minimumFractionDigits: n >= 1000 ? 2 : 4,
      maximumFractionDigits: n >= 1000 ? 2 : 4,
    });
  }

  function pct(n) {
    if (n == null || Number.isNaN(n)) return "—";
    const sign = n > 0 ? "+" : "";
    return `${sign}${n.toFixed(2)}%`;
  }

  function fmtTime(ts) {
    try {
      return new Date(ts * 1000).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  }

  function buildShell() {
    const el = document.createElement("section");
    el.className = "nexus-market-chart nexus-panel";
    el.setAttribute("data-nexus-market-chart", "");
    el.innerHTML = `
      <div class="nexus-market-chart__head">
        <div>
          <p class="nexus-market-chart__kicker">Gateway · live tape</p>
          <h3 class="nexus-market-chart__title">Price chart</h3>
        </div>
        <div class="nexus-market-chart__meta" data-chart-meta>Loading…</div>
      </div>
      <div class="nexus-market-chart__toolbar">
        <div class="nexus-market-chart__tabs" data-chart-symbols>
          ${SYMBOLS.map(
            (s) =>
              `<button type="button" data-symbol="${s}" class="${
                s === symbol ? "is-active" : ""
              }">${s}</button>`
          ).join("")}
        </div>
        <div class="nexus-market-chart__tabs" data-chart-intervals>
          ${INTERVALS.map(
            (i) =>
              `<button type="button" data-interval="${i.value}" class="${
                i.value === interval ? "is-active" : ""
              }">${i.label}</button>`
          ).join("")}
        </div>
      </div>
      <div class="nexus-market-chart__stats">
        <div>
          <span class="nexus-market-chart__stat-label">Last</span>
          <strong data-chart-last>—</strong>
        </div>
        <div>
          <span class="nexus-market-chart__stat-label">Window</span>
          <strong data-chart-change>—</strong>
        </div>
        <div>
          <span class="nexus-market-chart__stat-label">Range</span>
          <strong data-chart-range>—</strong>
        </div>
      </div>
      <div class="nexus-market-chart__canvas-wrap">
        <svg class="nexus-market-chart__svg" data-chart-svg viewBox="0 0 800 280" preserveAspectRatio="none" role="img" aria-label="Price chart"></svg>
        <p class="nexus-market-chart__empty" data-chart-empty hidden>No candles yet.</p>
      </div>
      <div class="nexus-market-chart__axis">
        <span data-chart-t0></span>
        <span data-chart-t1></span>
      </div>
    `;

    el.querySelector("[data-chart-symbols]").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-symbol]");
      if (!btn) return;
      symbol = btn.getAttribute("data-symbol");
      el.querySelectorAll("[data-symbol]").forEach((b) =>
        b.classList.toggle("is-active", b === btn)
      );
      load();
    });
    el.querySelector("[data-chart-intervals]").addEventListener("click", (e) => {
      const btn = e.target.closest("[data-interval]");
      if (!btn) return;
      interval = Number(btn.getAttribute("data-interval"));
      el.querySelectorAll("[data-interval]").forEach((b) =>
        b.classList.toggle("is-active", b === btn)
      );
      load();
    });
    return el;
  }

  function draw(el, candles) {
    const svg = el.querySelector("[data-chart-svg]");
    const empty = el.querySelector("[data-chart-empty]");
    if (!candles.length) {
      svg.innerHTML = "";
      empty.hidden = false;
      return;
    }
    empty.hidden = true;

    const W = 800;
    const H = 280;
    const padL = 8;
    const padR = 8;
    const padT = 16;
    const padB = 12;
    const closes = candles.map((c) => c.c);
    const highs = candles.map((c) => c.h);
    const lows = candles.map((c) => c.l);
    let min = Math.min(...lows);
    let max = Math.max(...highs);
    if (min === max) {
      min *= 0.999;
      max *= 1.001;
    }
    const span = max - min || 1;
    const n = candles.length;

    const xAt = (i) => padL + (i / Math.max(n - 1, 1)) * (W - padL - padR);
    const yAt = (v) => padT + (1 - (v - min) / span) * (H - padT - padB);

    const line = closes
      .map((v, i) => `${i === 0 ? "M" : "L"}${xAt(i).toFixed(2)},${yAt(v).toFixed(2)}`)
      .join(" ");
    const area =
      line +
      ` L${xAt(n - 1).toFixed(2)},${(H - padB).toFixed(2)} L${xAt(0).toFixed(2)},${(
        H - padB
      ).toFixed(2)} Z`;

    const up = closes[closes.length - 1] >= closes[0];
    const stroke = up ? "var(--nexus-vault, #22d3ee)" : "var(--nexus-observer, #f97316)";
    const fillId = up ? "nexusChartFillUp" : "nexusChartFillDn";

    // grid lines
    const grids = [0.25, 0.5, 0.75]
      .map((p) => {
        const y = padT + p * (H - padT - padB);
        const price = max - p * span;
        return `<line x1="${padL}" y1="${y}" x2="${W - padR}" y2="${y}" class="nexus-market-chart__grid"/>
          <text x="${W - padR}" y="${y - 4}" class="nexus-market-chart__ylab" text-anchor="end">${money(
          price
        )}</text>`;
      })
      .join("");

    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.innerHTML = `
      <defs>
        <linearGradient id="nexusChartFillUp" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#22d3ee" stop-opacity="0.35"/>
          <stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>
        </linearGradient>
        <linearGradient id="nexusChartFillDn" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#f97316" stop-opacity="0.3"/>
          <stop offset="100%" stop-color="#f97316" stop-opacity="0"/>
        </linearGradient>
      </defs>
      ${grids}
      <path d="${area}" fill="url(#${fillId})"/>
      <path d="${line}" fill="none" stroke="${stroke}" stroke-width="2.2" vector-effect="non-scaling-stroke" class="nexus-market-chart__line"/>
      <circle cx="${xAt(n - 1)}" cy="${yAt(closes[n - 1])}" r="3.5" fill="${stroke}" class="nexus-market-chart__dot"/>
    `;

    el.querySelector("[data-chart-t0]").textContent = fmtTime(candles[0].t);
    el.querySelector("[data-chart-t1]").textContent = fmtTime(candles[n - 1].t);
    el.querySelector("[data-chart-range]").textContent = `${money(min)} – ${money(max)}`;
  }

  async function load() {
    const el = document.querySelector(ROOT_SEL);
    if (!el || loading) return;
    loading = true;
    const meta = el.querySelector("[data-chart-meta]");
    meta.textContent = "Fetching Kraken…";
    try {
      const url = `/api/market/ohlc?symbol=${encodeURIComponent(symbol)}&interval=${interval}&limit=120`;
      const res = await fetch(url, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const candles = data.candles || [];
      el.querySelector("[data-chart-last]").textContent = money(data.last);
      const ch = el.querySelector("[data-chart-change]");
      ch.textContent = pct(data.changePercent);
      ch.classList.toggle("is-up", (data.changePercent || 0) > 0);
      ch.classList.toggle("is-down", (data.changePercent || 0) < 0);
      draw(el, candles);
      meta.textContent = `${data.sourceLabel || "Kraken"} · ${interval}m · ${candles.length} bars`;
    } catch (err) {
      meta.textContent = `Chart error: ${err.message || err}`;
    } finally {
      loading = false;
    }
  }

  function findAnchor() {
    const headings = document.querySelectorAll("h2, h1");
    for (const h of headings) {
      if (/market core/i.test(h.textContent || "")) {
        return h.closest(".space-y-6") || h.parentElement?.parentElement || h.parentElement;
      }
    }
    // Fallback: main column under sticky header
    return (
      document.querySelector("main") ||
      document.querySelector("#root > div > div.lg\\:pl-\\[19rem\\]") ||
      document.querySelector("#root")
    );
  }

  function mount() {
    if (location.pathname !== "/market") {
      document.querySelector(ROOT_SEL)?.remove();
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
      return;
    }
    if (document.querySelector(ROOT_SEL)) return;
    const anchor = findAnchor();
    if (!anchor) return;
    const el = buildShell();
    // Insert as first child of market page stack when possible
    if (anchor.classList?.contains("space-y-6")) {
      const first = anchor.firstElementChild;
      if (first) anchor.insertBefore(el, first.nextSibling);
      else anchor.appendChild(el);
    } else {
      anchor.prepend(el);
    }
    load();
    if (timer) clearInterval(timer);
    timer = setInterval(load, 30000);
  }

  const boot = () => {
    mount();
    setInterval(mount, 700);
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

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();

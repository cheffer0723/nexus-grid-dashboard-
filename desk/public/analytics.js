/* Privacy-first aggregate page-view analytics for the public Nexus Desk.
   The browser sends only path, referrer domain, and a coarse screen class.
   It sends no IP, user-agent, cookie, or persistent visitor identifier. */
(() => {
  const controlKey = "NEXUS_CONTROL_PASSWORD";

  function referrerDomain() {
    try { return document.referrer ? new URL(document.referrer).hostname : ""; }
    catch { return ""; }
  }

  function recordPageview() {
    if (navigator.globalPrivacyControl === true || navigator.doNotTrack === "1" || window.doNotTrack === "1") return;
    const body = JSON.stringify({
      path: location.pathname,
      referrer: referrerDomain(),
      screen: window.matchMedia("(max-width: 767px)").matches ? "compact" : "wide",
    });
    const blob = new Blob([body], { type: "application/json" });
    if (navigator.sendBeacon) navigator.sendBeacon("/api/analytics/pageview", blob);
    else fetch("/api/analytics/pageview", { method: "POST", headers: { "Content-Type": "application/json" }, body, keepalive: true }).catch(() => {});
  }

  function renderAnalytics() {
    if (!/^\/analytics\/?$/.test(location.pathname) || document.getElementById("nexus-analytics")) return;
    const panel = document.createElement("main");
    panel.id = "nexus-analytics";
    panel.innerHTML = `
      <section class="nexus-analytics-card">
        <p class="nexus-analytics-kicker">NEXUS DESK / PRIVATE</p>
        <h1>Traffic analytics</h1>
        <p class="nexus-analytics-note">Aggregate page views only. No IP addresses, user agents, cookies, or visitor identifiers are stored.</p>
        <form id="nexus-analytics-form">
          <label>Control password <input id="nexus-analytics-password" type="password" autocomplete="current-password" /></label>
          <label>Window <select id="nexus-analytics-days"><option value="7">7 days</option><option value="30" selected>30 days</option><option value="90">90 days</option></select></label>
          <button type="submit">Load report</button>
        </form>
        <p id="nexus-analytics-status" role="status">Enter the control password to view aggregate counts.</p>
        <section id="nexus-analytics-results" hidden></section>
      </section>`;
    document.body.appendChild(panel);
    const password = panel.querySelector("#nexus-analytics-password");
    password.value = sessionStorage.getItem(controlKey) || "";
    panel.querySelector("#nexus-analytics-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      const status = panel.querySelector("#nexus-analytics-status");
      const results = panel.querySelector("#nexus-analytics-results");
      const value = password.value.trim();
      if (value) sessionStorage.setItem(controlKey, value);
      else sessionStorage.removeItem(controlKey);
      status.textContent = "Loading...";
      results.hidden = true;
      try {
        const days = panel.querySelector("#nexus-analytics-days").value;
        const response = await fetch(`/api/analytics?days=${encodeURIComponent(days)}`, { headers: { "x-nexus-control-password": value } });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Unable to load analytics.");
        const rows = (items, first, second) => items.length ? items.map((item) => `<tr><td>${escapeHtml(item[first])}</td><td>${Number(item[second]).toLocaleString()}</td></tr>`).join("") : "<tr><td colspan=\"2\">No data yet.</td></tr>";
        results.innerHTML = `<div class="nexus-analytics-total"><span>Page views / ${data.windowDays} days</span><strong>${Number(data.totalPageviews).toLocaleString()}</strong></div>
          <div class="nexus-analytics-grid"><table><caption>Daily</caption><thead><tr><th>UTC date</th><th>Views</th></tr></thead><tbody>${rows(data.daily, "day", "pageviews")}</tbody></table>
          <table><caption>Pages</caption><thead><tr><th>Path</th><th>Views</th></tr></thead><tbody>${rows(data.pages, "page", "pageviews")}</tbody></table>
          <table><caption>Referrers</caption><thead><tr><th>Domain</th><th>Views</th></tr></thead><tbody>${rows(data.referrers, "domain", "pageviews")}</tbody></table>
          <table><caption>Screen class</caption><thead><tr><th>Class</th><th>Views</th></tr></thead><tbody>${rows(data.screens, "screen", "pageviews")}</tbody></table></div>`;
        status.textContent = data.privacy.data;
        results.hidden = false;
      } catch (error) { status.textContent = error.message || "Unable to load analytics."; }
    });
  }

  function escapeHtml(value) {
    const node = document.createElement("span");
    node.textContent = String(value);
    return node.innerHTML;
  }

  function boot() { recordPageview(); renderAnalytics(); }
  if (document.body) boot(); else document.addEventListener("DOMContentLoaded", boot);
  window.addEventListener("popstate", () => setTimeout(renderAnalytics, 0));
})();

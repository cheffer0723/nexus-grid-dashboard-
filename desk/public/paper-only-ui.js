/* The checked-in React bundle has no source in this repo. Hide obsolete live-order
   controls until that bundle can be rebuilt as a paper-only UI. Backend writes
   remain fail-closed independently of this presentation layer. */
(() => {
  const marker = "data-nexus-paper-only-hidden";
  const style = document.createElement("style");
  style.textContent = `[${marker}="1"]{display:none!important}`;
  document.head.appendChild(style);

  let scheduled = false;
  function hideUnsupportedControls() {
    scheduled = false;
    if (!/^\/controls\/?$/.test(location.pathname)) return;
    const buttons = [...document.querySelectorAll("#root button")];
    const arm = buttons.find((button) => button.textContent.trim().toUpperCase().startsWith("ARM LIVE"));
    arm?.closest(".space-y-5")?.setAttribute(marker, "1");
    const stop = buttons.find((button) => button.textContent.trim().toUpperCase().startsWith("STOP LIVE"));
    stop?.setAttribute(marker, "1");
  }
  function schedule() {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(hideUnsupportedControls);
  }
  new MutationObserver(schedule).observe(document.getElementById("root") || document.body, {
    childList: true,
    subtree: true,
  });
  window.addEventListener("popstate", schedule);
  document.addEventListener("click", schedule, true);
  schedule();
})();

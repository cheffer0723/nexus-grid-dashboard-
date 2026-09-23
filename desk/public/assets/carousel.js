(() => {
  function clampIndex(i, n) {
    return ((i % n) + n) % n;
  }

  function faceHTML(item, i) {
    return `
      ${item.media ? `<img class="nexus-ring-media" src="${item.media}" alt="" />` : ""}
      <p class="nexus-ring-eyebrow">${item.eyebrow || `Step ${String(i + 1).padStart(2, "0")}`}</p>
      <h3 class="nexus-ring-title">${item.title || ""}</h3>
      <div class="nexus-ring-body">${item.body || ""}</div>
    `;
  }

  function createRing(host, items, options = {}) {
    const accent = options.accent || "var(--nexus-vault, #22d3ee)";
    const radiusOpt = options.radius;
    const autoSpeed = options.autoSpeed ?? 10;
    const resumeMs = options.resumeMs ?? 2200;
    const segments = Math.max(5, Math.min(14, options.segments ?? 9));

    host.classList.add("nexus-ring");
    host.style.setProperty("--ring-accent", accent);
    if (radiusOpt != null) {
      host.style.setProperty(
        "--ring-radius",
        typeof radiusOpt === "number" ? `${radiusOpt}px` : String(radiusOpt)
      );
    }

    host.innerHTML = `
      <div class="nexus-ring-stage" data-ring-stage>
        <div class="nexus-ring-track" data-ring-track></div>
      </div>
      <p class="nexus-ring-hint">Scroll to spin</p>
      <div class="nexus-ring-nav">
        <button type="button" data-ring-prev aria-label="Previous">‹</button>
        <button type="button" data-ring-next aria-label="Next">›</button>
      </div>
      <div class="nexus-ring-dots" data-ring-dots></div>
    `;

    const stage = host.querySelector("[data-ring-stage]");
    const track = host.querySelector("[data-ring-track]");
    const dots = host.querySelector("[data-ring-dots]");
    const n = items.length;
    const step = 360 / n;
    let rotation = 0;
    let active = 0;
    let dragging = false;
    let lastX = 0;
    let autoPaused = false;
    let resumeTimer = 0;
    let raf = 0;
    let lastTs = 0;
    let destroyed = false;
    const reduceMotion =
      typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;

    const cs = getComputedStyle(host);
    const R = parseFloat(cs.getPropertyValue("--ring-radius")) || 300;
    const cardW = parseFloat(cs.getPropertyValue("--ring-card-w")) || 240;
    // Angular half-width of the card chord on the imaginary circle.
    const halfArc = Math.asin(Math.min(0.92, cardW / 2 / R)) * (180 / Math.PI);
    const segAngle = (2 * halfArc) / segments;
    const slatW = cardW / segments;

    items.forEach((item, i) => {
      const card = document.createElement("article");
      card.className = "nexus-ring-card";
      card.style.setProperty("--card-accent", item.accent || accent);
      // Orbit seat only — curve comes from slats at translateZ(R).
      card.style.transform = `rotateY(${i * step}deg)`;

      const shell = document.createElement("div");
      shell.className = "nexus-ring-card-shell";
      const html = faceHTML(item, i);

      for (let s = 0; s < segments; s++) {
        const offset = -halfArc + (s + 0.5) * segAngle;
        const slat = document.createElement("div");
        slat.className = "nexus-ring-slat";
        if (s === 0) slat.classList.add("is-leading");
        if (s === segments - 1) slat.classList.add("is-trailing");
        slat.style.width = `${slatW + 1.25}px`;
        slat.style.marginLeft = `${-((slatW + 1.25) / 2)}px`;
        slat.style.setProperty("--slat-shine", String(1 - Math.abs((s + 0.5) / segments - 0.5) * 1.35));
        slat.style.transform = `rotateY(${offset}deg) translateZ(var(--ring-radius))`;
        slat.innerHTML = `<div class="nexus-ring-slat-face" style="width:${cardW}px;transform:translateX(${-s * slatW}px)">${html}</div>`;
        shell.appendChild(slat);
      }

      card.appendChild(shell);
      track.appendChild(card);

      const dot = document.createElement("button");
      dot.type = "button";
      dot.setAttribute("aria-label", `Go to card ${i + 1}`);
      dot.addEventListener("click", () => {
        pauseAuto();
        goTo(i);
        scheduleResume();
      });
      dots.appendChild(dot);
    });

    const cards = [...track.querySelectorAll(".nexus-ring-card")];
    const dotBtns = [...dots.querySelectorAll("button")];

    function render(smooth) {
      track.classList.toggle("is-snapping", !!smooth);
      track.style.transform = `rotateY(${rotation}deg)`;
      const normalized = ((-rotation / step) % n + n) % n;
      active = Math.round(normalized) % n;
      cards.forEach((card, i) => {
        const dist = Math.min(Math.abs(i - active), n - Math.abs(i - active));
        card.dataset.face = dist === 0 ? "front" : dist === 1 ? "side" : "back";
      });
      dotBtns.forEach((d, i) => d.setAttribute("aria-current", i === active ? "true" : "false"));
    }

    function goTo(index) {
      const target = clampIndex(index, n);
      let delta = target - active;
      if (delta > n / 2) delta -= n;
      if (delta < -n / 2) delta += n;
      rotation -= delta * step;
      active = target;
      render(true);
    }

    function nudge(dir) {
      pauseAuto();
      rotation -= dir * step;
      render(true);
      scheduleResume();
    }

    function pauseAuto() {
      autoPaused = true;
      if (resumeTimer) {
        clearTimeout(resumeTimer);
        resumeTimer = 0;
      }
    }

    function scheduleResume() {
      if (reduceMotion || destroyed) return;
      if (resumeTimer) clearTimeout(resumeTimer);
      resumeTimer = setTimeout(() => {
        autoPaused = false;
        lastTs = 0;
      }, resumeMs);
    }

    function tick(ts) {
      if (destroyed) return;
      if (!lastTs) lastTs = ts;
      const dt = Math.min(0.05, (ts - lastTs) / 1000);
      lastTs = ts;
      if (!autoPaused && !dragging && !reduceMotion && autoSpeed) {
        rotation -= autoSpeed * dt;
        render(false);
      }
      raf = requestAnimationFrame(tick);
    }

    host.querySelector("[data-ring-prev]").addEventListener("click", () => nudge(-1));
    host.querySelector("[data-ring-next]").addEventListener("click", () => nudge(1));

    stage.addEventListener(
      "wheel",
      (e) => {
        e.preventDefault();
        pauseAuto();
        rotation -= Math.sign(e.deltaY || e.deltaX) * (step * 0.35);
        render(false);
        scheduleResume();
      },
      { passive: false }
    );

    const onDown = (x) => {
      dragging = true;
      lastX = x;
      pauseAuto();
      stage.classList.add("is-dragging");
    };
    const onMove = (x) => {
      if (!dragging) return;
      const dx = x - lastX;
      lastX = x;
      rotation += dx * 0.35;
      render(false);
    };
    const onUp = () => {
      if (!dragging) return;
      dragging = false;
      stage.classList.remove("is-dragging");
      const snapped = Math.round(rotation / step) * step;
      rotation = snapped;
      render(true);
      scheduleResume();
    };

    stage.addEventListener("pointerdown", (e) => {
      stage.setPointerCapture(e.pointerId);
      onDown(e.clientX);
    });
    stage.addEventListener("pointermove", (e) => onMove(e.clientX));
    stage.addEventListener("pointerup", onUp);
    stage.addEventListener("pointercancel", onUp);

    const onVis = () => {
      if (document.hidden) pauseAuto();
      else scheduleResume();
    };
    document.addEventListener("visibilitychange", onVis);

    render(false);
    if (!reduceMotion && autoSpeed) raf = requestAnimationFrame(tick);

    return {
      goTo,
      next: () => nudge(1),
      prev: () => nudge(-1),
      get active() {
        return active;
      },
      destroy() {
        destroyed = true;
        pauseAuto();
        if (raf) cancelAnimationFrame(raf);
        document.removeEventListener("visibilitychange", onVis);
        host.innerHTML = "";
      },
    };
  }

  window.NexusRing = { create: createRing };
})();

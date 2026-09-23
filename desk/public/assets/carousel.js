(() => {
  function clampIndex(i, n) {
    return ((i % n) + n) % n;
  }

  function createRing(host, items, options = {}) {
    const accent = options.accent || "var(--nexus-vault, #22d3ee)";
    const autoSpeed = options.autoSpeed ?? 28;
    const resumeMs = options.resumeMs ?? 1800;

    host.classList.add("nexus-ring");
    host.style.setProperty("--ring-accent", accent);
    host.style.setProperty("--ring-count", String(items.length));
    host.style.setProperty("--ring-step", String(360 / items.length));

    host.innerHTML = `
      <div class="nexus-ring-stage" data-ring-stage>
        <div class="nexus-ring-track" data-ring-track></div>
      </div>
      <p class="nexus-ring-hint">Drag or scroll to spin</p>
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
    let turn = 0; // degrees
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

    items.forEach((item, i) => {
      const card = document.createElement("article");
      card.className = "nexus-ring-card";
      card.style.setProperty("--i", String(i));
      card.style.setProperty("--card-accent", item.accent || accent);
      card.innerHTML = `
        <span class="nexus-ring-shine" aria-hidden="true"></span>
        ${item.media ? `<img class="nexus-ring-media" src="${item.media}" alt="" />` : ""}
        <p class="nexus-ring-eyebrow">${item.eyebrow || `Step ${String(i + 1).padStart(2, "0")}`}</p>
        <h3 class="nexus-ring-title">${item.title || ""}</h3>
        <div class="nexus-ring-body">${item.body || ""}</div>
      `;
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

    function faceFor(i) {
      // 1 = facing camera, 0 = back of ring
      let ang = ((i * step + turn) % 360 + 360) % 360;
      if (ang > 180) ang = 360 - ang;
      return Math.max(0, 1 - ang / 180);
    }

    function render(smooth) {
      track.classList.toggle("is-snapping", !!smooth);
      track.style.setProperty("--turn", `${turn}deg`);
      const normalized = ((-turn / step) % n + n) % n;
      active = Math.round(normalized) % n;
      cards.forEach((card, i) => {
        const face = faceFor(i);
        card.style.setProperty("--face", face.toFixed(3));
        card.dataset.face = face > 0.72 ? "front" : face > 0.35 ? "side" : "back";
      });
      dotBtns.forEach((d, i) => d.setAttribute("aria-current", i === active ? "true" : "false"));
    }

    function goTo(index) {
      const target = clampIndex(index, n);
      let delta = target - active;
      if (delta > n / 2) delta -= n;
      if (delta < -n / 2) delta += n;
      turn -= delta * step;
      active = target;
      render(true);
    }

    function nudge(dir) {
      pauseAuto();
      turn -= dir * step;
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
        turn -= autoSpeed * dt;
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
        turn -= Math.sign(e.deltaY || e.deltaX) * (step * 0.28);
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
      turn += dx * 0.32;
      render(false);
    };
    const onUp = () => {
      if (!dragging) return;
      dragging = false;
      stage.classList.remove("is-dragging");
      turn = Math.round(turn / step) * step;
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

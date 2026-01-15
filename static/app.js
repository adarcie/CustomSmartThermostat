// static/app.js
//
// Behavior you requested:
// - The input between +/- is LOCAL ONLY and never overwritten by polling.
// - Preset buttons ONLY change the local input (do NOT send).
// - Pressing "Set" sends to the thermostat WITHOUT reloading the page (uses fetch()).
// - The "Setpoint" bubble is AUTHORITATIVE (only updates when thermostat reports back).
// - "Live" becomes "Pending…" after Set until the thermostat confirms the new setpoint.

function roundToHalf(x) {
  return Math.round(x * 2) / 2;
}

function nearlyEqual(a, b, eps = 0.05) {
  return Math.abs(Number(a) - Number(b)) <= eps;
}

function updatePresetButtons(card, settings) {
  const presets = (settings && settings.presets) ? settings.presets : null;

  card.querySelectorAll('button[data-role="preset"]').forEach(btn => {
    const name = btn.getAttribute("data-name");
    const value = presets && (name in presets) ? presets[name] : null;

    if (value == null || Number.isNaN(Number(value))) {
      btn.textContent = name;
      btn.dataset.value = "";
      btn.disabled = true;
      return;
    }

    btn.disabled = false;
    btn.dataset.value = Number(value).toFixed(1);
    btn.textContent = `${name} (${Number(value).toFixed(1)}°)`;
  });
}

function ensureLocalInitialized(input, thermostatSetpoint) {
  // Initialize the local input ONCE from thermostat setpoint, then never touch it again from polling.
  if (!input) return;
  if (input.dataset.localInit === "1") return;

  if (thermostatSetpoint != null && !Number.isNaN(Number(thermostatSetpoint))) {
    input.value = Number(thermostatSetpoint).toFixed(1);
    input.dataset.localInit = "1";
  }
}

function setLocalInput(input, value) {
  const v = roundToHalf(Number(value));
  if (Number.isNaN(v)) return;
  input.value = v.toFixed(1);
}

function getLocalInput(input) {
  const v = parseFloat(input.value);
  return Number.isNaN(v) ? null : v;
}

function setPending(card, value) {
  card.dataset.pendingSetpoint = String(Number(value));
}

function clearPending(card) {
  delete card.dataset.pendingSetpoint;
}

function updateCard(card, data) {
  const tempEl = card.querySelector('[data-role="temp"]');
  const setBubbleEl = card.querySelector('[data-role="setpoint"]'); // authoritative
  const heatEl = card.querySelector('[data-role="heating"]');
  const statusEl = card.querySelector('[data-role="status"]');
  const heatPill = card.querySelector('[data-role="heatpill"]');
  const input = card.querySelector('input[name="setpoint"]');

  const temp = data.temperature;
  const sp = data.setpoint;     // authoritative thermostat setpoint
  const heating = !!data.heating;

  if (tempEl) tempEl.textContent = (temp == null) ? "--.-" : Number(temp).toFixed(1);

  // Bubble setpoint: ONLY from thermostat feedback
  if (setBubbleEl) setBubbleEl.textContent = (sp == null) ? "--.-" : Number(sp).toFixed(1);

  if (heatEl) heatEl.textContent = heating ? "ON" : "OFF";
  if (heatPill) heatPill.classList.toggle("on", heating);

  // Presets from settings
  updatePresetButtons(card, data.settings);

  // Local input init once
  ensureLocalInitialized(input, sp);

  // Pending resolution (only affects status)
  const pending = card.dataset.pendingSetpoint;
  if (pending != null && sp != null && nearlyEqual(pending, sp)) {
    clearPending(card);
  }

  // Status logic
  if (statusEl) {
    if (card.dataset.pendingSetpoint != null) {
      statusEl.textContent = "Pending…";
    } else {
      statusEl.textContent = (temp == null && sp == null) ? "Waiting for MQTT…" : "Live";
    }
  }
}

async function poll() {
  try {
    const res = await fetch("/api/state", { cache: "no-store" });
    const all = await res.json();

    document.querySelectorAll(".card[data-thermo-id]").forEach(card => {
      const tid = card.getAttribute("data-thermo-id");
      if (tid && all[tid]) updateCard(card, all[tid]);
    });
  } catch (e) {
    // ignore transient errors
  } finally {
    setTimeout(poll, 750);
  }
}

// This is the "fetch thing": it sends a POST without reloading the page.
async function sendSetpoint(card, thermoId, value) {
  setPending(card, value);

  const form = new FormData();
  form.set("setpoint", Number(value).toFixed(1));

  const res = await fetch(`/thermostat/${encodeURIComponent(thermoId)}/setpoint`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    // If send failed, clear pending so UI doesn't get stuck.
    clearPending(card);
  }
}

function wireControls() {
  document.querySelectorAll(".card[data-thermo-id]").forEach(card => {
    const thermoId = card.getAttribute("data-thermo-id");
    const input = card.querySelector('input[name="setpoint"]');
    if (!input || !thermoId) return;

    if (!input.dataset.localInit) input.dataset.localInit = "0";

    // Typing: local only
    input.addEventListener("input", () => {});

    // +/- buttons: local only, instant
    card.querySelectorAll("button[data-action]").forEach(btn => {
      btn.addEventListener("click", () => {
        const action = btn.getAttribute("data-action");
        const current = getLocalInput(input) ?? 0;
        const next = action === "inc" ? current + 0.5 : current - 0.5;
        setLocalInput(input, next);
        input.focus({ preventScroll: true });
      });
    });

    // Preset buttons: local only (NO submit)
    card.querySelectorAll('button[data-role="preset"]').forEach(btn => {
      btn.addEventListener("click", () => {
        const v = parseFloat(btn.dataset.value || "");
        if (Number.isNaN(v)) return;
        setLocalInput(input, v);
        input.focus({ preventScroll: true });
      });
    });

    // Intercept submit so we do NOT reload the page
    const formEl = card.querySelector("form.controls");
    if (formEl) {
      formEl.addEventListener("submit", async (e) => {
        e.preventDefault();

        const desired = getLocalInput(input);
        if (desired == null) return;

        await sendSetpoint(card, thermoId, roundToHalf(desired));
      });
    }
  });
}

// Boot
wireControls();
poll();

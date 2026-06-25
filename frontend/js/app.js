/* ------------------------------------------------------------------
   Shift Roster — frontend application script
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  // ---------------------------------------------------------
  // Constants
  // ---------------------------------------------------------
  const STORAGE_KEY = "shiftroster-theme";
  const API_BASE = "/api";

  // ---------------------------------------------------------
  // 1. Theme handling — system detection + manual toggle + persist
  // ---------------------------------------------------------
  const root = document.documentElement;

  function getStoredTheme() {
    try {
      return localStorage.getItem(STORAGE_KEY);
    } catch (_) {
      return null;
    }
  }

  function setStoredTheme(theme) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (_) {
      /* ignore quota / private mode errors */
    }
  }

  function systemPrefersDark() {
    return (
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches
    );
  }

  function applyTheme(theme) {
    if (theme === "dark") {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
  }

  function currentTheme() {
    return root.classList.contains("dark") ? "dark" : "light";
  }

  // Apply the right theme BEFORE first paint to avoid a flash.
  function initTheme() {
    const stored = getStoredTheme();
    if (stored === "dark" || stored === "light") {
      applyTheme(stored);
    } else {
      applyTheme(systemPrefersDark() ? "dark" : "light");
    }
  }

  // Track system changes only when the user has not made a manual choice.
  function watchSystemTheme() {
    if (!window.matchMedia) return;
    const mq = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = (event) => {
      if (!getStoredTheme()) {
        applyTheme(event.matches ? "dark" : "light");
      }
    };
    if (mq.addEventListener) mq.addEventListener("change", handler);
    else if (mq.addListener) mq.addListener(handler);
  }

  // ---------------------------------------------------------
  // 2. Wire up the toggle button
  // ---------------------------------------------------------
  function bindToggle() {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      const next = currentTheme() === "dark" ? "light" : "dark";
      applyTheme(next);
      setStoredTheme(next);
    });
  }

  // ---------------------------------------------------------
  // 3. Header — show the current month
  // ---------------------------------------------------------
  function renderCurrentMonth() {
    const el = document.getElementById("current-month");
    if (!el) return;
    const now = new Date();
    el.textContent = now.toLocaleString(undefined, {
      month: "long",
      year: "numeric",
    });
  }

  function renderCurrentYear() {
    const el = document.getElementById("current-year");
    if (el) el.textContent = String(new Date().getFullYear());
  }

  // ---------------------------------------------------------
  // 4. Health check — show whether the API is reachable
  // ---------------------------------------------------------
  async function checkApiHealth() {
    const statusEl = document.getElementById("api-status");
    if (!statusEl) return;
    try {
      const res = await fetch(API_BASE + "/health", {
        headers: { Accept: "application/json" },
        cache: "no-store",
      });
      if (!res.ok) throw new Error("HTTP " + res.status);
      const data = await res.json();
      if (data && data.status === "ok") {
        statusEl.textContent = "Online · /api/health OK";
      } else {
        statusEl.textContent = "Unexpected response";
      }
    } catch (err) {
      statusEl.textContent = "Unreachable";
    }
  }

  // ---------------------------------------------------------
  // Boot
  // ---------------------------------------------------------
  initTheme();
  document.addEventListener("DOMContentLoaded", function () {
    bindToggle();
    renderCurrentMonth();
    renderCurrentYear();
    checkApiHealth();
    watchSystemTheme();
  });
})();

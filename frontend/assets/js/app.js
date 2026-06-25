/* ------------------------------------------------------------------
   Shift Roster — shared utilities (theme, auth, API helpers)
   ------------------------------------------------------------------ */

var ShiftRoster = (function () {
  "use strict";

  var STORAGE_KEY_THEME = "shiftroster-theme";
  var STORAGE_KEY_TOKEN = "shiftroster-token";
  var API_BASE = "/api";

  // ---- Theme ----
  function getStoredTheme() {
    try { return localStorage.getItem(STORAGE_KEY_THEME); } catch (_) { return null; }
  }
  function setStoredTheme(theme) {
    try { localStorage.setItem(STORAGE_KEY_THEME, theme); } catch (_) {}
  }
  function systemPrefersDark() {
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function applyTheme(theme) {
    if (theme === "dark") document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
  }
  function currentTheme() {
    return document.documentElement.classList.contains("dark") ? "dark" : "light";
  }
  function initTheme() {
    var stored = getStoredTheme();
    applyTheme(stored === "dark" || stored === "light" ? stored : (systemPrefersDark() ? "dark" : "light"));
  }
  function watchSystemTheme() {
    if (!window.matchMedia) return;
    var mq = window.matchMedia("(prefers-color-scheme: dark)");
    var handler = function (e) { if (!getStoredTheme()) applyTheme(e.matches ? "dark" : "light"); };
    if (mq.addEventListener) mq.addEventListener("change", handler);
    else if (mq.addListener) mq.addListener(handler);
  }
  function bindThemeToggle() {
    var btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      applyTheme(next);
      setStoredTheme(next);
    });
  }

  // ---- Token / Auth ----
  function getToken() { try { return localStorage.getItem(STORAGE_KEY_TOKEN); } catch (_) { return null; } }
  function setToken(token) { try { localStorage.setItem(STORAGE_KEY_TOKEN, token); } catch (_) {} }
  function removeToken() { try { localStorage.removeItem(STORAGE_KEY_TOKEN); } catch (_) {} }

  function decodeJwt(token) {
    try {
      var parts = token.split(".");
      if (parts.length !== 3) return null;
      return JSON.parse(atob(parts[1].replace(/-/g, "+").replace(/_/g, "/")));
    } catch (_) { return null; }
  }

  function isLoggedIn() {
    var token = getToken();
    if (!token) return false;
    var payload = decodeJwt(token);
    if (!payload || !payload.exp) return false;
    return Date.now() < payload.exp * 1000;
  }

  function authHeaders() {
    var token = getToken();
    return token ? { Authorization: "Bearer " + token } : {};
  }

  function requireAuth() {
    if (!isLoggedIn()) {
      removeToken();
      window.location.href = "/login";
      return false;
    }
    return true;
  }

  function logout() {
    fetch(API_BASE + "/auth/logout", { method: "POST", headers: authHeaders() }).catch(function () {});
    removeToken();
    window.location.href = "/";
  }

  function getUsername() {
    if (!isLoggedIn()) return null;
    var payload = decodeJwt(getToken());
    return payload ? payload.sub : null;
  }

  // ---- Helpers ----
  function renderCurrentMonth() {
    var el = document.getElementById("current-month");
    if (el) el.textContent = new Date().toLocaleString(undefined, { month: "long", year: "numeric" });
  }

  function renderCurrentYear() {
    var el = document.getElementById("current-year");
    if (el) el.textContent = String(new Date().getFullYear());
  }

  async function checkApiHealth() {
    var el = document.getElementById("api-status");
    if (!el) return;
    try {
      var res = await fetch(API_BASE + "/health", { headers: { Accept: "application/json" }, cache: "no-store" });
      var data = await res.json();
      el.textContent = data && data.status === "ok" ? "Online · OK" : "Unexpected";
    } catch (_) { el.textContent = "Unreachable"; }
  }

  // ---- Boot (call from every page) ----
  function boot() {
    initTheme();
    // If DOM is already ready, run setup immediately; otherwise wait for DOMContentLoaded
    if (document.readyState !== "loading") {
      onDomReady();
    } else {
      document.addEventListener("DOMContentLoaded", onDomReady);
    }
  }

  function onDomReady() {
    bindThemeToggle();
    watchSystemTheme();
    renderCurrentMonth();
    renderCurrentYear();
    // Auto-logout timer
    setInterval(function () {
      if (getToken() && !isLoggedIn()) { removeToken(); window.location.href = "/login"; }
    }, 60000);
  }

  // Public API
  return {
    API_BASE: API_BASE,
    initTheme: initTheme,
    boot: boot,
    getToken: getToken,
    setToken: setToken,
    removeToken: removeToken,
    decodeJwt: decodeJwt,
    isLoggedIn: isLoggedIn,
    authHeaders: authHeaders,
    requireAuth: requireAuth,
    logout: logout,
    getUsername: getUsername,
    renderCurrentMonth: renderCurrentMonth,
    renderCurrentYear: renderCurrentYear,
    checkApiHealth: checkApiHealth,
    bindThemeToggle: bindThemeToggle,
    watchSystemTheme: watchSystemTheme,
  };
})();

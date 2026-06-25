/* ------------------------------------------------------------------
   Shift Roster — Login page script
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  ShiftRoster.boot();

  document.addEventListener("DOMContentLoaded", function () {
    // If already logged in, go straight to admin
    if (ShiftRoster.isLoggedIn()) {
      window.location.href = "/admin";
      return;
    }

    var form = document.getElementById("login-form");
    var errorEl = document.getElementById("login-error");
    var btnSubmit = document.getElementById("btn-submit");
    var btnTogglePw = document.getElementById("btn-toggle-pw");
    var pwInput = document.getElementById("login-password");
    var rememberMe = document.getElementById("remember-me");

    function showError(msg) {
      if (errorEl) { errorEl.textContent = msg; errorEl.classList.remove("hidden"); }
    }
    function hideError() {
      if (errorEl) { errorEl.classList.add("hidden"); errorEl.textContent = ""; }
    }
    function setLoading(loading) {
      if (btnSubmit) {
        btnSubmit.disabled = loading;
        btnSubmit.textContent = loading ? "Signing in…" : "Login";
      }
    }

    // Show / hide password
    if (btnTogglePw && pwInput) {
      btnTogglePw.addEventListener("click", function () {
        var isPassword = pwInput.type === "password";
        pwInput.type = isPassword ? "text" : "password";
        // Swap icon
        var eyeOpen = btnTogglePw.querySelector(".icon-eye-open");
        var eyeShut = btnTogglePw.querySelector(".icon-eye-shut");
        if (eyeOpen) eyeOpen.classList.toggle("hidden", !isPassword);
        if (eyeShut) eyeShut.classList.toggle("hidden", isPassword);
      });
    }

    // Submit
    if (form) {
      form.addEventListener("submit", async function (e) {
        e.preventDefault();
        hideError();

        var username = document.getElementById("login-username").value.trim();
        var password = document.getElementById("login-password").value;

        if (!username || !password) {
          showError("Please enter both username and password.");
          return;
        }

        setLoading(true);
        try {
          var res = await fetch(ShiftRoster.API_BASE + "/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username: username, password: password }),
          });

          if (!res.ok) {
            var data = null;
            try { data = await res.json(); } catch (_) {}
            var detail = (data && data.detail) || "Login failed";
            if (res.status === 401) showError("Invalid username or password.");
            else if (res.status === 403) showError("Account is disabled. Contact administrator.");
            else showError(detail);
            setLoading(false);
            return;
          }

          var tokenData = await res.json();
          if (tokenData && tokenData.access_token) {
            ShiftRoster.setToken(tokenData.access_token);
            window.location.href = "/admin";
          } else {
            showError("Unexpected server response.");
            setLoading(false);
          }
        } catch (err) {
          showError("Network error. Please check your connection and try again.");
          setLoading(false);
        }
      });
    }

    // Focus username on load
    var usernameInput = document.getElementById("login-username");
    if (usernameInput) usernameInput.focus();
  });
})();

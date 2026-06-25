/* ------------------------------------------------------------------
   Shift Roster — Admin layout script (sidebar, topnav, route guard)
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  ShiftRoster.boot();

  document.addEventListener("DOMContentLoaded", function () {
    // Route guard
    if (!ShiftRoster.requireAuth()) return;

    var username = ShiftRoster.getUsername() || "Admin";
    var elUsername = document.getElementById("admin-username");
    if (elUsername) elUsername.textContent = username;

    // Sidebar toggle (mobile)
    var sidebar = document.getElementById("admin-sidebar");
    var overlay = document.getElementById("sidebar-overlay");
    var btnOpen = document.getElementById("btn-sidebar-open");
    var btnClose = document.getElementById("btn-sidebar-close");

    function openSidebar() {
      if (sidebar) sidebar.classList.remove("-translate-x-full");
      if (overlay) overlay.classList.remove("hidden");
    }
    function closeSidebar() {
      if (sidebar) sidebar.classList.add("-translate-x-full");
      if (overlay) overlay.classList.add("hidden");
    }

    if (btnOpen) btnOpen.addEventListener("click", openSidebar);
    if (btnClose) btnClose.addEventListener("click", closeSidebar);
    if (overlay) overlay.addEventListener("click", closeSidebar);

    // Highlight active nav item
    var path = window.location.pathname;
    var navItems = document.querySelectorAll("[data-nav]");
    navItems.forEach(function (item) {
      var href = item.getAttribute("href");
      if (href === path) {
        item.classList.add("bg-indigo-50", "text-indigo-700", "font-semibold", "active");
        item.classList.remove("text-slate-600", "dark:text-slate-300");
        item.classList.add("dark:bg-indigo-500/10", "dark:text-indigo-300");
      } else {
        item.classList.remove("bg-indigo-50", "text-indigo-700", "font-semibold", "active");
      }
    });

    // Logout
    var btnLogout = document.getElementById("btn-admin-logout");
    if (btnLogout) btnLogout.addEventListener("click", ShiftRoster.logout);

    // Health check on dashboard
    ShiftRoster.checkApiHealth();
  });
})();

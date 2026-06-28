/* ------------------------------------------------------------------
   Shift Roster — Roster Management page (admin, Phase 5 + 6 + 7)

   Thin wrapper over the shared ``ShiftRosterGrid`` module.  This file
   only does the page-specific wiring (booting the app and starting
   the editable grid).  All rendering, editing, and persistence logic
   lives in ``roster-grid.js``.

   Phase 5: generation + read API
   Phase 6: spreadsheet-style grid (display)
   Phase 7: cell editing (click/type, dbl-click/dropdown, keyboard)
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  if (window.ShiftRoster && typeof ShiftRoster.boot === "function") {
    ShiftRoster.boot();
  }

  var grid = ShiftRosterGrid.create({
    isEditable: true,
    requireAuth: true,
    usePublicApi: false,
    apiBase: "/api/roster",
  });

  document.addEventListener("DOMContentLoaded", grid.boot);
})();

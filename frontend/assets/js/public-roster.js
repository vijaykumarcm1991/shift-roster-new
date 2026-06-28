/* ------------------------------------------------------------------
   Shift Roster — Public Roster page (Phase 7)

   Read-only view of the monthly roster.  Uses the same shared
   ``ShiftRosterGrid`` module as the admin page, but configured for:

     - isEditable:    false  (no click / dblclick / keyboard edit)
     - requireAuth:   false  (no redirect to /login)
     - usePublicApi:  true   (hits /api/roster/{year}/{month}/public)

   The page is meant to be linkable from the public homepage so
   anyone (no login required) can see who's on which shift.
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  if (window.ShiftRoster && typeof ShiftRoster.boot === "function") {
    ShiftRoster.boot();
  }

  var grid = ShiftRosterGrid.create({
    isEditable: false,
    requireAuth: false,
    usePublicApi: true,
    apiBase: "/api/roster",
  });

  document.addEventListener("DOMContentLoaded", grid.boot);
})();

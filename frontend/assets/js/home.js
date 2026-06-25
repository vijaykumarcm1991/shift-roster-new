/* ------------------------------------------------------------------
   Shift Roster — Public homepage script
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  ShiftRoster.boot();

  document.addEventListener("DOMContentLoaded", function () {
    ShiftRoster.checkApiHealth();
  });
})();

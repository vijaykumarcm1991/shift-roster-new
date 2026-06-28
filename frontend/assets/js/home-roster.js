/* ------------------------------------------------------------------
   Shift Roster — Homepage roster module
   Fetches the current month from the public API and renders a
   7-day window centred on today (clamped to the current month).
   After rendering, auto-scrolls the wrapper so today's column
   is visible.  No auth required.
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  if (window.ShiftRoster && typeof ShiftRoster.boot === "function") {
    ShiftRoster.boot();
  }

  var SHIFT_TYPES_API = "/api/shift-types";
  var ROSTER_API = "/api/roster";

  // ---- Constants ----
  var WEEKDAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var WEEKDAY_LONG = ["Sunday", "Monday", "Tuesday", "Wednesday",
                      "Thursday", "Friday", "Saturday"];
  var DAY_CELL_WIDTH = 60;
  var EMPLOYEE_COL_WIDTH = 200;
  var COLOR_RGB = {
    blue:   [59, 130, 246],
    green:  [34, 197, 94],
    purple: [168, 85, 247],
    violet: [139, 92, 246],
    gray:   [107, 114, 128],
    orange: [249, 115, 22],
    red:    [239, 68, 68],
    yellow: [234, 179, 8],
  };

  // ---- Element refs ----
  var monthLabel = document.getElementById("home-roster-month");
  var loadingState = document.getElementById("home-roster-loading");
  var notGeneratedState = document.getElementById("home-roster-not-generated");
  var noEmployeesState = document.getElementById("home-roster-no-employees");
  var gridContainer = document.getElementById("home-roster-grid-container");
  var gridWrapper = document.getElementById("home-roster-grid-wrapper");
  var gridHead = document.getElementById("home-roster-grid-head");
  var gridBody = document.getElementById("home-roster-grid-body");

  // ---- Cached state ----
  var shiftTypesById = {};

  // ---- Pure helpers ----
  function esc(str) {
    if (str === null || str === undefined) return "";
    var d = document.createElement("div");
    d.textContent = String(str);
    return d.innerHTML;
  }
  function shiftColorRgb(color) {
    return COLOR_RGB[color] || COLOR_RGB.gray;
  }
  function pad2(n) { return n < 10 ? "0" + n : "" + n; }
  function isoDate(year, month, day) {
    return year + "-" + pad2(month) + "-" + pad2(day);
  }

  // ---- Show / hide state panels ----
  function showOnly(target) {
    var panels = [loadingState, notGeneratedState, noEmployeesState, gridContainer];
    for (var i = 0; i < panels.length; i++) {
      if (!panels[i]) continue;
      if (panels[i] === target) panels[i].classList.remove("hidden");
      else panels[i].classList.add("hidden");
    }
  }

  // ---- Compute the 7-day window to show ----
  // We want 7 consecutive days, centred on today, all within the
  // current month.  If today is within 3 days of either edge, the
  // window shifts to fit.  Returns { startDay, endDay } (1-based,
  // inclusive, both within [1, totalDays]).
  function computeWeekWindow(today, totalDays) {
    var idealStart = today - 3; // 3 days before today
    var idealEnd = today + 3;   // 3 days after today
    if (idealStart < 1) {
      idealStart = 1;
      idealEnd = Math.min(totalDays, 7);
    } else if (idealEnd > totalDays) {
      idealEnd = totalDays;
      idealStart = Math.max(1, totalDays - 6);
    }
    return { startDay: idealStart, endDay: idealEnd };
  }

  // ---- Render the grid ----
  function render(meta, entries) {
    var year = meta.year;
    var month = meta.month;
    var totalDays = meta.total_days;
    var now = new Date();
    var today = now.getDate();
    var isCurrentMonth = (year === now.getFullYear() && month === now.getMonth() + 1);
    var week = computeWeekWindow(isCurrentMonth ? today : Math.ceil(totalDays / 2), totalDays);

    if (monthLabel) {
      monthLabel.textContent = meta.month_name + " " + year;
    }

    // Group entries by (employee_id, ISO date)
    var byEmpDate = {};
    var employees = [];
    var seen = {};
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      if (!byEmpDate[e.employee.id]) byEmpDate[e.employee.id] = {};
      byEmpDate[e.employee.id][e.date] = e;
      if (!seen[e.employee.id]) {
        seen[e.employee.id] = true;
        employees.push(e.employee);
      }
    }

    // ---- <colgroup> ----
    // Per the HTML spec, <colgroup> must be a direct child of
    // <table>.  Nesting it inside <thead> makes browsers silently
    // ignore it and fall back to auto-sizing.
    var colHtml = '<col style="width:' + EMPLOYEE_COL_WIDTH + 'px">';
    for (var c = week.startDay; c <= week.endDay; c++) {
      colHtml += '<col style="width:' + DAY_CELL_WIDTH + 'px">';
    }
    var table = document.getElementById("home-roster-grid");
    if (table) {
      var colgroup = table.querySelector("colgroup");
      if (!colgroup) {
        colgroup = document.createElement("colgroup");
        table.insertBefore(colgroup, table.firstChild);
      }
      colgroup.innerHTML = colHtml;
    }

    // ---- Header row ----
    var headHtml = "<tr>";
    headHtml +=
      '<th class="corner" scope="col">' +
      '<div class="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300">Employee</div>' +
      '<div class="mt-0.5 text-[10px] font-medium text-slate-400 dark:text-slate-500">Code · Team</div>' +
      "</th>";
    for (var d = week.startDay; d <= week.endDay; d++) {
      var dateObj = new Date(year, month - 1, d);
      var dow = dateObj.getDay();
      var isWeekend = dow === 0 || dow === 6;
      var isToday = isCurrentMonth && d === today;
      var thClasses = [];
      if (isWeekend) thClasses.push("weekend");
      if (isToday) thClasses.push("today");
      headHtml +=
        '<th scope="col" data-day="' + d + '"' +
        (thClasses.length ? ' class="' + thClasses.join(" ") + '"' : "") +
        ">" +
        '<div class="day-num">' + d + "</div>" +
        '<div class="day-name" title="' + WEEKDAY_LONG[dow] + '">' + WEEKDAY_SHORT[dow] + "</div>" +
        "</th>";
    }
    headHtml += "</tr>";
    gridHead.innerHTML = headHtml;

    // ---- Body rows ----
    var bodyHtml = "";
    for (var k = 0; k < employees.length; k++) {
      var employee = employees[k];
      var rowEntries = byEmpDate[employee.id] || {};
      bodyHtml += "<tr>";
      bodyHtml +=
        '<th class="employee-name" scope="row" data-employee-id="' + employee.id + '">' +
        '<div class="truncate font-medium">' + esc(employee.employee_name) + "</div>" +
        '<div class="mt-0.5 truncate text-[10px] font-normal text-slate-400 dark:text-slate-500">' +
        esc(employee.employee_code) +
        (employee.team_name ? " · " + esc(employee.team_name) : "") +
        "</div>" +
        "</th>";

      for (var day = week.startDay; day <= week.endDay; day++) {
        var iso = isoDate(year, month, day);
        var entry = rowEntries[iso];
        var dayDate = new Date(year, month - 1, day);
        var dayDow = dayDate.getDay();
        var dayWeekend = dayDow === 0 || dayDow === 6;
        var dayToday = isCurrentMonth && day === today;

        var cellClasses = ["day-cell"];
        if (dayWeekend) cellClasses.push("weekend");
        if (dayToday) cellClasses.push("today");

        var inner = "";
        var dataAttrs = ' data-employee-id="' + employee.id + '"' +
                        ' data-date="' + iso + '"' +
                        ' data-day="' + day + '"' +
                        ' data-entry-id="' + (entry ? entry.id : "") + '"';
        if (entry && entry.shift) {
          var shiftType = shiftTypesById[entry.shift.id];
          var colorName = (shiftType && shiftType.color) || entry.shift.color || "gray";
          var rgb = shiftColorRgb(colorName);
          dataAttrs += ' data-shift-id="' + entry.shift.id + '"' +
                       ' data-shift-code="' + esc(entry.shift.code) + '"';
          inner =
            '<div class="shift-pill" style="background-color: rgb(' +
            rgb.join(",") +
            ');" title="' +
            esc(entry.shift.display_name || entry.shift.code || "") +
            '">' +
            esc(entry.shift.code || "") +
            "</div>";
        } else {
          cellClasses.push("empty");
        }

        bodyHtml +=
          '<td class="' + cellClasses.join(" ") + '"' +
          dataAttrs +
          ">" + inner + "</td>";
      }
      bodyHtml += "</tr>";
    }
    gridBody.innerHTML = bodyHtml;

    // Set CSS custom properties on the table (same `table` ref we
    // created the <colgroup> on above).
    if (table) {
      table.style.setProperty("--roster-day-col-width", DAY_CELL_WIDTH + "px");
      table.style.setProperty("--roster-emp-col-width", EMPLOYEE_COL_WIDTH + "px");
    }

    showOnly(gridContainer);

    // Inject the same per-N col-hover / active-col CSS rules that
    // roster-grid.js injects, so the home grid has matching
    // hover behaviour.
    injectColumnHoverCSS();

    // Auto-scroll to today's column (no-op if the displayed month
    // is not the current month).
    setTimeout(function () { scrollToToday(today, isCurrentMonth); }, 0);
  }

  // ---- Inject the col-hover / active-col CSS ----
  // Same rules that roster-grid.js injects, scoped by a unique id
  // so we never clash with the admin page if both happen to be
  // loaded in the same session.
  function injectColumnHoverCSS() {
    if (document.getElementById("home-col-hover-styles")) return;
    var style = document.createElement("style");
    style.id = "home-col-hover-styles";
    var lines = [];
    for (var d = 1; d <= 31; d++) {
      lines.push(
        ".home-roster-grid.col-hover-" + d + " td[data-day=\"" + d + "\"]," +
        ".home-roster-grid.col-hover-" + d + " th[data-day=\"" + d + "\"]" +
        "{background-color:rgb(224 231 255 / 0.6) !important;" +
        "box-shadow:inset 0 0 0 1px rgb(165 180 252 / 0.5);}"
      );
      lines.push(
        ".dark .home-roster-grid.col-hover-" + d + " td[data-day=\"" + d + "\"]," +
        ".dark .home-roster-grid.col-hover-" + d + " th[data-day=\"" + d + "\"]" +
        "{background-color:rgb(30 27 75 / 0.5) !important;}"
      );
    }
    style.textContent = lines.join("\n");
    document.head.appendChild(style);
  }

  // ---- Auto-scroll to today's column ----
  function scrollToToday(today, isCurrentMonth) {
    if (!isCurrentMonth) return;
    var cell = document.querySelector(
      '.home-roster-grid td[data-day="' + today + '"]'
    );
    if (!cell || !gridWrapper) return;
    var cellLeft = cell.offsetLeft;
    var cellRight = cellLeft + cell.offsetWidth;
    var viewLeft = gridWrapper.scrollLeft;
    var viewRight = viewLeft + gridWrapper.clientWidth;
    var margin = cell.offsetWidth;
    if (
      cellLeft >= viewLeft + margin &&
      cellRight <= viewRight - margin
    ) {
      return;
    }
    var target = cellLeft - (gridWrapper.clientWidth - cell.offsetWidth) / 2;
    var max = Math.max(0, gridWrapper.scrollWidth - gridWrapper.clientWidth);
    gridWrapper.scrollLeft = Math.max(0, Math.min(target, max));
  }

  // ---- Fetch shift types + current month roster, then render ----
  function load() {
    showOnly(loadingState);
    var now = new Date();
    var year = now.getFullYear();
    var month = now.getMonth() + 1;

    fetch(SHIFT_TYPES_API)
      .then(function (r) {
        if (!r.ok) throw new Error("Failed to load shift types");
        return r.json();
      })
      .then(function (types) {
        shiftTypesById = {};
        for (var i = 0; i < types.length; i++) {
          shiftTypesById[types[i].id] = types[i];
        }
        return fetch(ROSTER_API + "/" + year + "/" + month + "/public");
      })
      .then(function (r) {
        if (r.status === 404) {
          // Month not generated yet — show a friendly state.
          showOnly(notGeneratedState);
          return null;
        }
        if (!r.ok) throw new Error("Failed to load roster");
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        if (data.meta.total_employees === 0) {
          showOnly(noEmployeesState);
          return;
        }
        if (!data.meta.is_generated) {
          showOnly(notGeneratedState);
          return;
        }
        render(data.meta, data.entries);
      })
      .catch(function () {
        showOnly(notGeneratedState);
      });
  }

  if (document.readyState !== "loading") {
    load();
  } else {
    document.addEventListener("DOMContentLoaded", load);
  }
})();

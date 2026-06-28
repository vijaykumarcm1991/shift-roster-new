/* ------------------------------------------------------------------
   Shift Roster — Roster Management page (Phase 5 + Phase 6)
   Phase 5: generation + read API
   Phase 6: spreadsheet-style grid (display-only, no editing yet)
   Phase 7 will add editing on top of this same grid structure.
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  if (window.ShiftRoster && typeof ShiftRoster.boot === "function") {
    ShiftRoster.boot();
  }

  var API_BASE = "/api/roster";
  var SHIFT_TYPES_API = "/api/shift-types";

  var monthSelect = document.getElementById("month-select");
  var yearSelect = document.getElementById("year-select");
  var btnLoad = document.getElementById("btn-load");
  var btnGenerate = document.getElementById("btn-generate");
  var genIcon = document.getElementById("gen-icon");
  var genSpinner = document.getElementById("gen-spinner");
  var genText = document.getElementById("gen-text");

  var statMonth = document.getElementById("stat-month");
  var statEmployees = document.getElementById("stat-employees");
  var statDays = document.getElementById("stat-days");
  var statCells = document.getElementById("stat-cells");
  var statusDot = document.getElementById("status-dot");
  var statusText = document.getElementById("status-text");
  var loadingState = document.getElementById("loading-state");
  var noEmployeesState = document.getElementById("no-employees-state");
  var gridSummary = document.getElementById("grid-summary");
  var summaryText = document.getElementById("summary-text");
  var gridContainer = document.getElementById("grid-container");
  var gridHead = document.getElementById("roster-grid-head");
  var gridBody = document.getElementById("roster-grid-body");
  var toastContainer = document.getElementById("toast-container");

  // ---- Constants ----

  var WEEKDAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

  // Width of a single day column in the grid (in px). This is the ONE
  // place that controls how wide every day cell is — the value is
  // applied via <col> elements for table-layout: fixed, and the CSS
  // reads it through a CSS custom property so all cells stay in sync.
  var DAY_CELL_WIDTH = 60;

  // Width of the frozen first (employee) column (in px). Same story.
  var EMPLOYEE_COL_WIDTH = 200;

  // RGB triplets for the named CSS colors used by the seed shift types.
  // Used to render tinted cell backgrounds without losing readability.
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

  // ---- Cached state ----

  var shiftTypesById = {};  // populated from /api/shift-types

  // ---- Helpers ----

  function headers(extra) {
    return Object.assign(
      { "Content-Type": "application/json" },
      ShiftRoster.authHeaders(),
      extra || {}
    );
  }

  function esc(str) {
    if (str === null || str === undefined) return "";
    var d = document.createElement("div");
    d.textContent = String(str);
    return d.innerHTML;
  }

  function shiftColorRgb(color) {
    return COLOR_RGB[color] || COLOR_RGB.gray;
  }

  function pad2(n) {
    return n < 10 ? "0" + n : "" + n;
  }

  function isoDate(year, month, day) {
    return year + "-" + pad2(month) + "-" + pad2(day);
  }

  // ---- Toast ----

  function showToast(message, type) {
    type = type || "success";
    var colors = {
      success: "bg-emerald-600 text-white",
      error: "bg-red-600 text-white",
      info: "bg-indigo-600 text-white",
    };
    var icons = {
      success: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd"/></svg>',
      error: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clip-rule="evenodd"/></svg>',
      info: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd"/></svg>',
    };
    var el = document.createElement("div");
    el.className =
      "flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium shadow-lg transition-all duration-300 " +
      (colors[type] || colors.info);
    el.innerHTML = (icons[type] || icons.info) + " " + esc(message);
    toastContainer.appendChild(el);
    setTimeout(function () {
      el.style.opacity = "0";
      el.style.transform = "translateX(100%)";
      setTimeout(function () { el.remove(); }, 300);
    }, 3500);
  }

  // ---- Status / stats ----

  function setLoading(loading) {
    if (loading) {
      loadingState.classList.remove("hidden");
      gridContainer.classList.add("hidden");
      gridSummary.classList.add("hidden");
      noEmployeesState.classList.add("hidden");
    } else {
      loadingState.classList.add("hidden");
    }
  }

  function setStatus(generated, monthName) {
    if (generated) {
      statusDot.className = "inline-block h-2 w-2 rounded-full bg-emerald-500";
      statusText.textContent = "Roster for " + monthName + " has been generated.";
      statusText.className = "text-slate-700 dark:text-slate-200";
    } else {
      statusDot.className = "inline-block h-2 w-2 rounded-full bg-amber-500";
      statusText.textContent =
        "No roster yet for " + monthName + ". Generate to create the empty grid.";
      statusText.className = "text-slate-600 dark:text-slate-300";
    }
  }

  function renderStats(meta) {
    statMonth.textContent = meta.month_name + " " + meta.year;
    statEmployees.textContent = meta.total_employees;
    statDays.textContent = meta.total_days;
    statCells.textContent = (meta.total_employees * meta.total_days).toLocaleString();
  }

  function updateGenerateButton(generated) {
    btnGenerate.disabled = generated;
    if (generated) {
      genText.textContent = "Already Generated";
    } else {
      genText.textContent = "Generate Roster";
    }
  }

  // ---- Shift types cache ----

  function loadShiftTypes() {
    return fetch(SHIFT_TYPES_API, { headers: headers() })
      .then(function (r) { return r.json(); })
      .then(function (types) {
        var byId = {};
        for (var i = 0; i < types.length; i++) {
          byId[types[i].id] = types[i];
        }
        shiftTypesById = byId;
      })
      .catch(function () {
        // Non-fatal — cells will just show no color
        shiftTypesById = {};
      });
  }

  // ---- Column hover (injected styles + event handlers) ----

  function injectColumnHoverCSS() {
    if (document.getElementById("col-hover-styles")) return;
    var style = document.createElement("style");
    style.id = "col-hover-styles";
    var lines = [];
    for (var d = 1; d <= 31; d++) {
      lines.push(
        ".roster-grid.col-hover-" + d + " td[data-day=\"" + d + "\"]," +
        ".roster-grid.col-hover-" + d + " th[data-day=\"" + d + "\"]" +
        "{background-color:rgb(224 231 255 / 0.6) !important;" +
        "box-shadow:inset 0 0 0 1px rgb(165 180 252 / 0.5);}"
      );
      lines.push(
        ".dark .roster-grid.col-hover-" + d + " td[data-day=\"" + d + "\"]," +
        ".dark .roster-grid.col-hover-" + d + " th[data-day=\"" + d + "\"]" +
        "{background-color:rgb(30 27 75 / 0.5) !important;}"
      );
    }
    style.textContent = lines.join("\n");
    document.head.appendChild(style);
  }

  function attachColumnHover() {
    var table = document.getElementById("roster-grid");
    if (!table || table.dataset.colHoverBound === "1") return;
    table.dataset.colHoverBound = "1";

    table.addEventListener("mouseover", function (e) {
      var cell = e.target.closest("th[data-day], td[data-day]");
      if (!cell || !table.contains(cell)) return;
      var day = cell.getAttribute("data-day");
      if (!day) return;
      // Remove any other col-hover-* class first
      var toRemove = [];
      for (var i = 0; i < table.classList.length; i++) {
        var c = table.classList[i];
        if (c.indexOf("col-hover-") === 0) toRemove.push(c);
      }
      for (var j = 0; j < toRemove.length; j++) table.classList.remove(toRemove[j]);
      table.classList.add("col-hover-" + day);
    });

    table.addEventListener("mouseout", function (e) {
      var cell = e.target.closest("th[data-day], td[data-day]");
      if (!cell) return;
      var day = cell.getAttribute("data-day");
      if (!day) return;
      // Only remove the class if the new target is NOT in the same column
      var related = e.relatedTarget;
      if (
        related &&
        related.closest &&
        related.closest("[data-day=\"" + day + "\"]")
      ) {
        return; // still within the same column — keep highlight
      }
      table.classList.remove("col-hover-" + day);
    });
  }

  // ---- Horizontal scroll indicator (fade gradient on right edge) ----
  // The grid is wider than the card on most screens. A small fade on the
  // right edge signals there's more content off-screen and that the user
  // can scroll horizontally. It hides when scrolled to the end.
  function updateScrollFade() {
    var wrapper = document.getElementById("roster-grid-wrapper");
    if (!wrapper) return;
    var hasMore = wrapper.scrollWidth > wrapper.clientWidth;
    var atEnd = wrapper.scrollLeft + wrapper.clientWidth >= wrapper.scrollWidth - 1;
    if (hasMore && !atEnd) {
      wrapper.classList.add("has-scroll-fade");
    } else {
      wrapper.classList.remove("has-scroll-fade");
    }
  }

  function attachScrollFade() {
    var wrapper = document.getElementById("roster-grid-wrapper");
    if (!wrapper || wrapper.dataset.fadeBound === "1") return;
    wrapper.dataset.fadeBound = "1";
    wrapper.addEventListener("scroll", updateScrollFade);
    window.addEventListener("resize", updateScrollFade);
  }

  // ---- Grid rendering ----

  function renderGrid(meta, entries) {
    var year = meta.year;
    var month = meta.month;
    var totalDays = meta.total_days;
    var totalEmployees = meta.total_employees;

    if (totalEmployees === 0) {
      noEmployeesState.classList.remove("hidden");
      gridContainer.classList.add("hidden");
      gridSummary.classList.add("hidden");
      return;
    }

    // Summary line
    gridSummary.classList.remove("hidden");
    gridSummary.classList.add("flex");
    var totalCells = totalEmployees * totalDays;
    summaryText.textContent =
      totalEmployees +
      " Employee" + (totalEmployees !== 1 ? "s" : "") +
      " × " +
      totalDays +
      " Day" + (totalDays !== 1 ? "s" : "") +
      " = " +
      totalCells.toLocaleString() +
      " Cell" + (totalCells !== 1 ? "s" : "");

    // Group entries by employee_id, indexed by ISO date
    var byEmpDate = {};
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      if (!byEmpDate[e.employee.id]) byEmpDate[e.employee.id] = {};
      byEmpDate[e.employee.id][e.date] = e;
    }

    // Discover distinct active employees (preserves entry order = display order)
    var employees = [];
    var seen = {};
    for (var j = 0; j < entries.length; j++) {
      var emp = entries[j].employee;
      if (!seen[emp.id]) {
        seen[emp.id] = true;
        employees.push(emp);
      }
    }
    // If generated but somehow empty (shouldn't happen, but defensive)
    if (employees.length === 0) {
      // Fall back to no render
      gridContainer.classList.add("hidden");
      return;
    }

    // "Today" comparison values
    var now = new Date();
    var isCurrentMonth = (year === now.getFullYear() && month === now.getMonth() + 1);
    var todayDate = now.getDate();

    // ---- <colgroup> ----
    // With table-layout: fixed, the <col> widths are how the browser
    // distributes space to every cell in that column. We set:
    //   - 1 col for the employee (frozen first column)
    //   - N cols for the days, each DAY_CELL_WIDTH wide
    // The <colgroup> goes inside <thead> at the top.
    var colHtml = '<colgroup>';
    colHtml += '<col style="width:' + EMPLOYEE_COL_WIDTH + 'px">';
    for (var c = 1; c <= totalDays; c++) {
      colHtml += '<col style="width:' + DAY_CELL_WIDTH + 'px">';
    }
    colHtml += '</colgroup>';

    // ---- Header row ----
    var headHtml = colHtml + "<tr>";
    headHtml +=
      '<th class="corner" scope="col">' +
      '<div class="text-xs font-semibold uppercase tracking-wider text-slate-600 dark:text-slate-300">Employee</div>' +
      '<div class="mt-0.5 text-[10px] font-medium text-slate-400 dark:text-slate-500">Code · Team</div>' +
      "</th>";

    for (var d = 1; d <= totalDays; d++) {
      var dateObj = new Date(year, month - 1, d);
      var dow = dateObj.getDay(); // 0=Sun .. 6=Sat
      var isWeekend = dow === 0 || dow === 6;
      var isToday = isCurrentMonth && d === todayDate;
      var thClasses = [];
      if (isWeekend) thClasses.push("weekend");
      if (isToday) thClasses.push("today");
      headHtml +=
        '<th scope="col" data-day="' + d + '"' +
        (thClasses.length ? ' class="' + thClasses.join(" ") + '"' : "") +
        ">" +
        '<div class="day-num">' + d + "</div>" +
        '<div class="day-name">' + WEEKDAY_SHORT[dow] + "</div>" +
        "</th>";
    }
    headHtml += "</tr>";
    gridHead.innerHTML = headHtml;

    // ---- Body rows ----
    var bodyHtml = "";
    for (var k = 0; k < employees.length; k++) {
      var employee = employees[k];
      var rowEntries = byEmpDate[employee.id] || {};

      // Row header (frozen employee name)
      bodyHtml += "<tr>";
      bodyHtml +=
        '<th class="employee-name" scope="row" data-employee-id="' + employee.id + '">' +
        '<div class="truncate font-medium">' + esc(employee.employee_name) + "</div>" +
        '<div class="mt-0.5 truncate text-[10px] font-normal text-slate-400 dark:text-slate-500">' +
        esc(employee.employee_code) +
        (employee.team_name ? " · " + esc(employee.team_name) : "") +
        "</div>" +
        "</th>";

      // Day cells
      for (var day = 1; day <= totalDays; day++) {
        var iso = isoDate(year, month, day);
        var entry = rowEntries[iso];
        var dayDate = new Date(year, month - 1, day);
        var dayDow = dayDate.getDay();
        var dayWeekend = dayDow === 0 || dayDow === 6;
        var dayToday = isCurrentMonth && day === todayDate;

        var cellClasses = ["day-cell"];
        if (dayWeekend) cellClasses.push("weekend");
        if (dayToday) cellClasses.push("today");

        var inner = "";
        if (entry && entry.shift) {
          var shiftType = shiftTypesById[entry.shift.id];
          var colorName = (shiftType && shiftType.color) || entry.shift.color || "gray";
          var rgb = shiftColorRgb(colorName);
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
          ' data-employee-id="' + employee.id + '"' +
          ' data-date="' + iso + '"' +
          ' data-day="' + day + '"' +
          ">" + inner + "</td>";
      }
      bodyHtml += "</tr>";
    }
    gridBody.innerHTML = bodyHtml;

    // Expose column widths as CSS custom properties so the CSS
    // rules can stay in sync with the <col> definitions without
    // duplicating the numbers.
    var table = document.getElementById("roster-grid");
    if (table) {
      table.style.setProperty("--roster-day-col-width", DAY_CELL_WIDTH + "px");
      table.style.setProperty("--roster-emp-col-width", EMPLOYEE_COL_WIDTH + "px");
    }

    // Show the grid
    gridContainer.classList.remove("hidden");

    // Update the scroll-fade indicator after layout settles
    // (needs to know the final scrollWidth/clientWidth)
    setTimeout(updateScrollFade, 0);
  }

  // ---- API ----

  function loadRoster(autoGenerate) {
    var year = parseInt(yearSelect.value, 10);
    var month = parseInt(monthSelect.value, 10);
    var monthLabel = monthSelect.options[monthSelect.selectedIndex].text + " " + year;
    setLoading(true);
    setStatus(false, monthLabel);

    fetch(API_BASE + "/" + year + "/" + month, { headers: headers() })
      .then(function (r) {
        if (r.status === 401) { ShiftRoster.logout(); return null; }
        if (!r.ok) { throw new Error("Failed to load roster"); }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        renderStats(data.meta);
        setStatus(data.meta.is_generated, data.meta.month_name + " " + data.meta.year);
        updateGenerateButton(data.meta.is_generated);
        if (data.meta.is_generated) {
          renderGrid(data.meta, data.entries);
        } else {
          if (data.meta.total_employees === 0) {
            renderGrid(data.meta, []);
            return;
          }
          // Active employees but no roster yet → show only the empty employees state
          gridContainer.classList.add("hidden");
          gridSummary.classList.add("hidden");
          noEmployeesState.classList.add("hidden");
          if (autoGenerate) {
            generateRoster(true);
            return;
          }
        }
        setLoading(false);
      })
      .catch(function (err) {
        setLoading(false);
        showToast(err.message || "Failed to load roster", "error");
      });
  }

  function generateRoster(silent) {
    var year = parseInt(yearSelect.value, 10);
    var month = parseInt(monthSelect.value, 10);
    btnGenerate.disabled = true;
    genIcon.classList.add("hidden");
    genSpinner.classList.remove("hidden");
    genText.textContent = "Generating…";
    // Clear the page-level loading state — the button spinner is enough.
    setLoading(false);

    fetch(API_BASE + "/" + year + "/" + month + "/generate", {
      method: "POST",
      headers: headers(),
    })
      .then(function (r) {
        if (r.status === 401) { ShiftRoster.logout(); return null; }
        if (!r.ok) {
          return r.json().then(function (d) {
            throw new Error(d.detail || "Generation failed");
          });
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        renderStats(data.meta);
        setStatus(data.meta.is_generated, data.meta.month_name + " " + data.meta.year);
        updateGenerateButton(data.meta.is_generated);
        renderGrid(data.meta, data.entries);
        if (!silent) {
          showToast(
            "Generated " +
              data.meta.total_records +
              " roster entries for " +
              data.meta.month_name +
              " " +
              data.meta.year,
            "success"
          );
        } else {
          showToast(
            "Roster for " + data.meta.month_name + " " + data.meta.year + " generated automatically",
            "info"
          );
        }
      })
      .catch(function (err) {
        showToast(err.message || "Generation failed", "error");
        updateGenerateButton(false);
      })
      .finally(function () {
        genIcon.classList.remove("hidden");
        genSpinner.classList.add("hidden");
        btnGenerate.disabled = false;
      });
  }

  // ---- Init ----

  function init() {
    var now = new Date();
    monthSelect.value = String(now.getMonth() + 1);
    var year = now.getFullYear();
    if (!yearSelect.querySelector('option[value="' + year + '"]')) {
      var opt = document.createElement("option");
      opt.value = String(year);
      opt.textContent = String(year);
      yearSelect.appendChild(opt);
    }
    yearSelect.value = String(year);

    btnLoad.addEventListener("click", function () { loadRoster(false); });
    btnGenerate.addEventListener("click", function () { generateRoster(false); });
    monthSelect.addEventListener("change", function () { loadRoster(true); });
    yearSelect.addEventListener("change", function () { loadRoster(true); });

    // Load shift types first (for cell colors), then load the roster
    injectColumnHoverCSS();
    attachColumnHover();
    attachScrollFade();
    loadShiftTypes().then(function () { loadRoster(true); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!ShiftRoster.isLoggedIn()) {
      ShiftRoster.requireAuth();
      return;
    }
    init();
  });
})();

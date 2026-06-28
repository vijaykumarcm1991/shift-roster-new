/* ------------------------------------------------------------------
   Shift Roster — Reusable roster grid renderer
   Phase 5 + 6 + 7.  Shared by the admin page (roster.html) and the
   public read-only page (public-roster.html).

   Exposes a global ``ShiftRosterGrid`` factory.  Each call returns a
   controller bound to a specific set of DOM elements, with a config
   object that controls:

     - isEditable     (default false) — click/dblclick/keys to edit
     - requireAuth    (default true)  — redirect to /login if no token
     - usePublicApi   (default false) — use the public roster endpoint
     - apiBase        (default "/api/roster")

   The page is responsible for placing the right elements in the DOM
   (selects, grid container, toast container, etc.) and for supplying
   the matching CSS class names.  See roster.html and public-roster.html
   for the expected markup.
   ------------------------------------------------------------------ */

(function (global) {
  "use strict";

  // ---- Constants ----

  var WEEKDAY_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
  var DAY_CELL_WIDTH = 60;
  var EMPLOYEE_COL_WIDTH = 200;

  // RGB triplets for the named CSS colors used by the seed shift types.
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

  // ---- Pure helpers (exposed for tests) ----

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

  function makeToast(toastContainer) {
    return function showToast(message, type) {
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
    };
  }

  // ---- Column-hover styles ----

  function injectColumnHoverCSS() {
    if (document.getElementById("col-hover-styles")) return;
    var style = document.createElement("style");
    style.id = "col-hover-styles";
    var lines = [];
    for (var d = 1; d <= 31; d++) {
      // col-hover-N — light mode
      lines.push(
        ".roster-grid.col-hover-" + d + " td[data-day=\"" + d + "\"]," +
        ".roster-grid.col-hover-" + d + " th[data-day=\"" + d + "\"]" +
        "{background-color:rgb(224 231 255 / 0.6) !important;" +
        "box-shadow:inset 0 0 0 1px rgb(165 180 252 / 0.5);}"
      );
      // col-hover-N — dark mode
      lines.push(
        ".dark .roster-grid.col-hover-" + d + " td[data-day=\"" + d + "\"]," +
        ".dark .roster-grid.col-hover-" + d + " th[data-day=\"" + d + "\"]" +
        "{background-color:rgb(30 27 75 / 0.5) !important;}"
      );
      // active-col-N — light mode (injected AFTER col-hover so it wins
      // when both classes are set on the table — e.g., the user just
      // clicked and the mouse is still on the column).
      lines.push(
        ".roster-grid.active-col-" + d + " td[data-day=\"" + d + "\"]," +
        ".roster-grid.active-col-" + d + " th[data-day=\"" + d + "\"]" +
        "{background-color:rgb(224 231 255 / 0.85) !important;" +
        "box-shadow:inset 0 0 0 1px rgb(165 180 252 / 0.8) !important;}"
      );
      // active-col-N — dark mode
      lines.push(
        ".dark .roster-grid.active-col-" + d + " td[data-day=\"" + d + "\"]," +
        ".dark .roster-grid.active-col-" + d + " th[data-day=\"" + d + "\"]" +
        "{background-color:rgb(30 27 75 / 0.55) !important;" +
        "box-shadow:inset 0 0 0 1px rgb(99 102 241 / 0.7) !important;}"
      );
    }
    style.textContent = lines.join("\n");
    document.head.appendChild(style);
  }

  // ---- Shift type cache ----

  function makeShiftTypeCache(headers) {
    var byId = {};
    var list = [];
    return {
      byId: function () { return byId; },
      list: function () { return list; },
      reload: function () {
        return fetch("/api/shift-types", { headers: headers() })
          .then(function (r) {
            if (!r.ok) throw new Error("Failed to load shift types");
            return r.json();
          })
          .then(function (types) {
            byId = {};
            for (var i = 0; i < types.length; i++) byId[types[i].id] = types[i];
            var sorted = [];
            for (var j = 0; j < types.length; j++) sorted.push(types[j]);
            sorted.sort(function (a, b) {
              return (a.display_order || 0) - (b.display_order || 0) ||
                     (a.code || "").localeCompare(b.code || "");
            });
            list = sorted;
          })
          .catch(function () {
            byId = {};
            list = [];
          });
      },
    };
  }

  // ---- Grid rendering ----

  function renderGrid(els, shiftCache, meta, entries) {
    var year = meta.year;
    var month = meta.month;
    var totalDays = meta.total_days;
    var totalEmployees = meta.total_employees;
    var byId = shiftCache.byId();

    if (totalEmployees === 0) {
      els.noEmployeesState.classList.remove("hidden");
      els.gridContainer.classList.add("hidden");
      els.gridSummary.classList.add("hidden");
      return [];
    }

    els.gridSummary.classList.remove("hidden");
    els.gridSummary.classList.add("flex");
    var totalCells = totalEmployees * totalDays;
    els.summaryText.textContent =
      totalEmployees + " Employee" + (totalEmployees !== 1 ? "s" : "") +
      " × " + totalDays + " Day" + (totalDays !== 1 ? "s" : "") +
      " = " + totalCells.toLocaleString() + " Cell" + (totalCells !== 1 ? "s" : "");

    var byEmpDate = {};
    for (var i = 0; i < entries.length; i++) {
      var e = entries[i];
      if (!byEmpDate[e.employee.id]) byEmpDate[e.employee.id] = {};
      byEmpDate[e.employee.id][e.date] = e;
    }

    var employees = [];
    var seen = {};
    for (var j = 0; j < entries.length; j++) {
      var emp = entries[j].employee;
      if (!seen[emp.id]) {
        seen[emp.id] = true;
        employees.push(emp);
      }
    }
    if (employees.length === 0) {
      els.gridContainer.classList.add("hidden");
      return [];
    }

    var now = new Date();
    var isCurrentMonth = (year === now.getFullYear() && month === now.getMonth() + 1);
    var todayDate = now.getDate();

    // ---- <colgroup> ----
    // With table-layout: fixed, the <col> widths are how the browser
    // distributes space to every cell in that column. We set:
    //   - 1 col for the employee (frozen first column)
    //   - N cols for the days, each DAY_CELL_WIDTH wide
    // Per the HTML spec, <colgroup> must be a direct child of
    // <table> — nesting it inside <thead> makes browsers silently
    // ignore it and fall back to auto-sizing the columns.
    var colHtml = '<col style="width:' + EMPLOYEE_COL_WIDTH + 'px">';
    for (var c = 1; c <= totalDays; c++) {
      colHtml += '<col style="width:' + DAY_CELL_WIDTH + 'px">';
    }
    var table = document.getElementById("roster-grid");
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

    for (var d = 1; d <= totalDays; d++) {
      var dateObj = new Date(year, month - 1, d);
      var dow = dateObj.getDay();
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
    els.gridHead.innerHTML = headHtml;

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
        var dataAttrs = ' data-employee-id="' + employee.id + '"' +
                        ' data-date="' + iso + '"' +
                        ' data-day="' + day + '"' +
                        ' data-entry-id="' + (entry ? entry.id : "") + '"';
        if (entry && entry.shift) {
          var shiftType = byId[entry.shift.id];
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
    els.gridBody.innerHTML = bodyHtml;

    // Expose column widths as CSS custom properties so the CSS
    // rules can stay in sync with the <col> definitions without
    // duplicating the numbers.  The `table` reference is the same
    // one we created the <colgroup> on above.
    if (table) {
      table.style.setProperty("--roster-day-col-width", DAY_CELL_WIDTH + "px");
      table.style.setProperty("--roster-emp-col-width", EMPLOYEE_COL_WIDTH + "px");
    }

    els.gridContainer.classList.remove("hidden");
    return entries;
  }

  // ---- Column hover events ----

  function attachColumnHover() {
    var table = document.getElementById("roster-grid");
    if (!table || table.dataset.colHoverBound === "1") return;
    table.dataset.colHoverBound = "1";

    table.addEventListener("mouseover", function (e) {
      var cell = e.target.closest("th[data-day], td[data-day]");
      if (!cell || !table.contains(cell)) return;
      var day = cell.getAttribute("data-day");
      if (!day) return;
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
      var related = e.relatedTarget;
      if (
        related &&
        related.closest &&
        related.closest("[data-day=\"" + day + "\"]")
      ) {
        return;
      }
      table.classList.remove("col-hover-" + day);
    });
  }

  // ---- Scroll-fade ----

  function makeScrollFade() {
    function update() {
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
    function attach() {
      var wrapper = document.getElementById("roster-grid-wrapper");
      if (!wrapper || wrapper.dataset.fadeBound === "1") return;
      wrapper.dataset.fadeBound = "1";
      wrapper.addEventListener("scroll", update);
      window.addEventListener("resize", update);
    }
    return { update: update, attach: attach };
  }

  // ---- Auto-scroll to today's column ----
  // If the displayed month is the current month, scroll the wrapper
  // horizontally so today's column is centred.  We don't scroll at
  // all if today is already "comfortably visible" — at least one
  // cell-width of margin on each side — so that a user who has
  // manually scrolled isn't yanked back to centre.
  // No-op for past / future months — the user explicitly chose them.
  function scrollToToday(meta) {
    if (!meta) return;
    var today = new Date();
    if (today.getFullYear() !== meta.year || today.getMonth() + 1 !== meta.month) {
      return; // Not the current month — leave the scroll position alone.
    }
    var day = today.getDate();
    var cell = document.querySelector(
      '.roster-grid td[data-day="' + day + '"]'
    );
    if (!cell) return;
    var wrapper = document.getElementById("roster-grid-wrapper");
    if (!wrapper) return;
    var cellLeft = cell.offsetLeft;
    var cellRight = cellLeft + cell.offsetWidth;
    var viewLeft = wrapper.scrollLeft;
    var viewRight = viewLeft + wrapper.clientWidth;
    var margin = cell.offsetWidth;
    // "Comfortably visible" = at least one cell-width of slack on
    // both sides.  Without this guard a single click that puts the
    // column at the viewport edge would always trigger a re-centre.
    if (
      cellLeft >= viewLeft + margin &&
      cellRight <= viewRight - margin
    ) {
      return;
    }
    // Centre the cell in the viewport.
    var target = cellLeft - (wrapper.clientWidth - cell.offsetWidth) / 2;
    var max = Math.max(0, wrapper.scrollWidth - wrapper.clientWidth);
    wrapper.scrollLeft = Math.max(0, Math.min(target, max));
  }

  // ---- Expand / compress the grid to full page ----
  // Moved inside the factory closure (below) where it has access
  // to scrollToToday() + scrollFade.

  // ---- Factory ----

  function create(opts) {
    opts = opts || {};
    var isEditable = !!opts.isEditable;
    var requireAuth = opts.requireAuth !== false;
    var usePublicApi = !!opts.usePublicApi;
    var apiBase = opts.apiBase || "/api/roster";

    // ---- Element lookup ----
    var els = {
      monthSelect: document.getElementById("month-select"),
      yearSelect: document.getElementById("year-select"),
      btnLoad: document.getElementById("btn-load"),
      btnGenerate: document.getElementById("btn-generate"),
      btnExpand: document.getElementById("btn-expand"),
      genIcon: document.getElementById("gen-icon"),
      genSpinner: document.getElementById("gen-spinner"),
      genText: document.getElementById("gen-text"),
      statMonth: document.getElementById("stat-month"),
      statEmployees: document.getElementById("stat-employees"),
      statDays: document.getElementById("stat-days"),
      statCells: document.getElementById("stat-cells"),
      statusDot: document.getElementById("status-dot"),
      statusText: document.getElementById("status-text"),
      loadingState: document.getElementById("loading-state"),
      noEmployeesState: document.getElementById("no-employees-state"),
      gridSummary: document.getElementById("grid-summary"),
      summaryText: document.getElementById("summary-text"),
      gridContainer: document.getElementById("grid-container"),
      gridHead: document.getElementById("roster-grid-head"),
      gridBody: document.getElementById("roster-grid-body"),
      toastContainer: document.getElementById("toast-container"),
    };
    // The card is the .roster-card element — captured lazily so that
    // callers can re-query it after the DOM is mutated (e.g., the
    // public-roster.html page renders the same card but the user
    // navigates back here from elsewhere).
    function getCard() { return document.querySelector(".roster-card"); }

    // ---- Expand / compress the grid to full page ----
    // The expand button is a single toggle: clicking it adds the
    // .roster-card--expanded class to the card (which the CSS
    // positions fixed at the viewport edges) and the .roster-expanded
    // class to <body> (which disables page scroll).  Clicking again
    // removes both.  Pressing Escape also exits expanded mode.
    function setExpanded(isExpanded) {
      var card = getCard();
      if (!card) return;
      card.classList.toggle("roster-card--expanded", isExpanded);
      document.body.classList.toggle("roster-expanded", isExpanded);
      // Update the button label + icon to match the new state.
      if (els.btnExpand) {
        var iconExpand = els.btnExpand.querySelector(".icon-expand");
        var iconCompress = els.btnExpand.querySelector(".icon-compress");
        var label = els.btnExpand.querySelector(".expand-label");
        if (iconExpand) iconExpand.classList.toggle("hidden", isExpanded);
        if (iconCompress) iconCompress.classList.toggle("hidden", !isExpanded);
        if (label) label.textContent = isExpanded ? "Compress" : "Expand";
        els.btnExpand.setAttribute(
          "title",
          isExpanded ? "Compress (Esc)" : "Expand to full page"
        );
        els.btnExpand.setAttribute(
          "aria-label",
          isExpanded ? "Compress grid back to normal" : "Expand grid to full page"
        );
      }
      // The grid wrapper's clientWidth changes when the card grows.
      // Wait for the next paint so the layout is up to date, then
      // re-centre today's column in the new viewport and refresh
      // the scroll-fade indicator.  Without this the user has to
      // scroll manually after expanding.
      setTimeout(function () {
        if (scrollFade && scrollFade.update) scrollFade.update();
        if (lastData && lastData.meta) scrollToToday(lastData.meta);
      }, 60);
    }
    function bindExpandHandler() {
      if (!els.btnExpand) return;
      if (els.btnExpand.dataset.expandBound === "1") return;
      els.btnExpand.dataset.expandBound = "1";
      els.btnExpand.addEventListener("click", function (e) {
        e.stopPropagation();
        var card = getCard();
        if (!card) return;
        setExpanded(!card.classList.contains("roster-card--expanded"));
      });
      // Escape key exits expanded mode from anywhere on the page.
      document.addEventListener("keydown", function (e) {
        if (e.key !== "Escape") return;
        var card = getCard();
        if (card && card.classList.contains("roster-card--expanded")) {
          setExpanded(false);
        }
      });
    }

    var headers = function (extra) {
      return Object.assign(
        { "Content-Type": "application/json" },
        ShiftRoster.authHeaders(),
        extra || {}
      );
    };
    var showToast = makeToast(els.toastContainer);
    var shiftCache = makeShiftTypeCache(headers);
    var scrollFade = makeScrollFade();

    // Cached entry map for editing
    var entriesById = {};
    var editingState = null;
    var lastData = null;

    function setEntriesById(entries) {
      entriesById = {};
      for (var i = 0; i < entries.length; i++) {
        entriesById[entries[i].id] = entries[i];
      }
    }

    function setLoading(loading) {
      if (loading) {
        els.loadingState.classList.remove("hidden");
        els.gridContainer.classList.add("hidden");
        els.gridSummary.classList.add("hidden");
        els.noEmployeesState.classList.add("hidden");
      } else {
        els.loadingState.classList.add("hidden");
      }
    }

    function setStatus(generated, monthName) {
      if (generated) {
        els.statusDot.className = "inline-block h-2 w-2 rounded-full bg-emerald-500";
        els.statusText.textContent = "Roster for " + monthName + " has been generated.";
        els.statusText.className = "text-slate-700 dark:text-slate-200";
      } else {
        els.statusDot.className = "inline-block h-2 w-2 rounded-full bg-amber-500";
        els.statusText.textContent =
          "No roster yet for " + monthName + ". " +
          (isEditable ? "Generate to create the empty grid." : "Waiting for an admin to generate it.");
        els.statusText.className = "text-slate-600 dark:text-slate-300";
      }
    }

    function renderStats(meta) {
      els.statMonth.textContent = meta.month_name + " " + meta.year;
      els.statEmployees.textContent = meta.total_employees;
      els.statDays.textContent = meta.total_days;
      els.statCells.textContent = (meta.total_employees * meta.total_days).toLocaleString();
    }

    function updateGenerateButton(generated) {
      if (!els.btnGenerate) return;
      els.btnGenerate.disabled = generated;
      if (generated) {
        els.genText.textContent = "Already Generated";
      } else {
        els.genText.textContent = "Generate Roster";
      }
    }

    // ---- Editing: Active highlight ----
    function clearActiveHighlights() {
      if (editingState && editingState.row) {
        editingState.row.classList.remove("active-row");
      }
      var table = document.getElementById("roster-grid");
      if (table) {
        var toRemove = [];
        for (var i = 0; i < table.classList.length; i++) {
          if (table.classList[i].indexOf("active-col-") === 0) {
            toRemove.push(table.classList[i]);
          }
        }
        for (var j = 0; j < toRemove.length; j++) {
          table.classList.remove(toRemove[j]);
        }
      }
    }

    function applyActiveHighlights(td) {
      var row = td.parentNode;
      if (row) row.classList.add("active-row");
      var day = td.getAttribute("data-day");
      if (day) {
        var table = document.getElementById("roster-grid");
        if (table) table.classList.add("active-col-" + day);
      }
    }

    // ---- Editing: start ----
    function startEdit(td, mode) {
      if (!isEditable) return;
      mode = mode || "typing";

      if (editingState && editingState.td === td) {
        if (editingState.input) editingState.input.focus();
        return;
      }
      if (editingState) {
        commitEdit();
      }

      var entryId = parseInt(td.getAttribute("data-entry-id"), 10);
      if (!entryId) return;
      var entry = entriesById[entryId];
      if (!entry) return;

      var originalShift = null;
      if (entry.shift) {
        originalShift = {
          id: entry.shift.id,
          code: entry.shift.code,
          color: entry.shift.color,
        };
      }

      clearActiveHighlights();
      applyActiveHighlights(td);
      td.classList.add("editing");

      var input = document.createElement("input");
      input.type = "text";
      input.className = "editing-input";
      input.placeholder = "S1, WO, L…";
      input.value = mode === "dropdown" ? "" : (originalShift ? originalShift.code : "");
      input.autocomplete = "off";
      input.autocapitalize = "off";
      input.spellcheck = false;
      input.setAttribute("aria-label", "Shift code");

      var dropdown = document.createElement("div");
      dropdown.className = "editing-dropdown";
      var list = document.createElement("ul");
      list.className = "editing-list";
      list.setAttribute("role", "listbox");
      dropdown.appendChild(list);

      td.innerHTML = "";
      td.appendChild(input);
      document.body.appendChild(dropdown);

      editingState = {
        td: td,
        row: td.parentNode,
        entryId: entryId,
        input: input,
        dropdown: dropdown,
        list: list,
        items: [],
        selectedIndex: -1,
        originalShift: originalShift,
        mode: mode,
      };

      input.addEventListener("input", function () {
        renderAutocomplete(input.value);
      });
      input.addEventListener("keydown", function (e) {
        handleEditKeydown(e);
      });
      input.addEventListener("mousedown", function (e) { e.stopPropagation(); });
      input.addEventListener("click", function (e) { e.stopPropagation(); });

      renderAutocomplete(input.value);
      input.focus();
      if (input.value) input.select();

      // Reposition dropdown on scroll/resize.  We capture a unique
      // handler per edit so the cleanup in commitEdit/cancelEdit only
      // removes this edit's listeners, not a later edit's.
      var scrollHandler = function () { positionDropdown(); };
      var resizeHandler = function () { positionDropdown(); };
      editingState.scrollHandler = scrollHandler;
      editingState.resizeHandler = resizeHandler;
      positionDropdown();
      window.addEventListener("scroll", scrollHandler, true);
      window.addEventListener("resize", resizeHandler);
    }

    function positionDropdown() {
      if (!editingState) return;
      var td = editingState.td;
      var rect = td.getBoundingClientRect();
      var dd = editingState.dropdown;
      dd.style.left = rect.left + "px";
      dd.style.top = (rect.bottom + 2) + "px";
      dd.style.minWidth = Math.max(200, rect.width) + "px";
    }

    function renderAutocomplete(query) {
      if (!editingState) return;
      var items = filterShifts(query);
      editingState.items = items;
      var exactIndex = -1;
      if (query) {
        var q = query.toLowerCase().trim();
        for (var k = 0; k < items.length; k++) {
          if (items[k].code.toLowerCase() === q) { exactIndex = k; break; }
        }
      }
      editingState.selectedIndex = exactIndex >= 0 ? exactIndex : (items.length > 0 ? 0 : -1);

      var list = editingState.list;
      list.innerHTML = "";
      if (items.length === 0) {
        var empty = document.createElement("li");
        empty.className = "editing-empty";
        empty.textContent = query
          ? "No match for \u201c" + query + "\u201d"
          : "No shifts available";
        list.appendChild(empty);
      } else {
        for (var i = 0; i < items.length; i++) {
          var it = items[i];
          var li = document.createElement("li");
          li.className = "editing-item" +
            (i === editingState.selectedIndex ? " selected" : "");
          li.setAttribute("role", "option");
          li.setAttribute("data-shift-id", it.id);
          var rgb = shiftColorRgb(it.color);
          var colorStyle = "background-color: rgb(" + rgb.join(",") + ");";
          li.innerHTML =
            '<span class="editing-item-swatch" style="' + colorStyle + '"></span>' +
            '<span class="editing-item-code">' + esc(it.code) + '</span>' +
            '<span class="editing-item-name">' + esc(it.display_name || "") + '</span>';
          li.addEventListener("mousedown", function (e) {
            e.preventDefault();
            e.stopPropagation();
            var sid = parseInt(this.getAttribute("data-shift-id"), 10);
            commitEdit(sid);
          });
          list.appendChild(li);
        }
      }
    }

    function filterShifts(query) {
      var q = (query || "").toLowerCase().trim();
      var out = [];
      var all = shiftCache.list();
      for (var i = 0; i < all.length; i++) {
        var s = all[i];
        if (s.is_active === false) continue;
        if (!q) { out.push(s); continue; }
        if (s.code.toLowerCase().indexOf(q) === 0) {
          out.push(s);
        } else if ((s.display_name || "").toLowerCase().indexOf(q) >= 0) {
          out.push(s);
        }
      }
      return out;
    }

    function handleEditKeydown(e) {
      if (!editingState) return;
      var key = e.key;

      if (key === "Enter") {
        e.preventDefault();
        e.stopPropagation();
        var typed = (editingState.input.value || "").toUpperCase().trim();
        var match = null;
        if (typed) {
          var all = shiftCache.list();
          for (var i = 0; i < all.length; i++) {
            if (all[i].code.toUpperCase() === typed) {
              match = all[i];
              break;
            }
          }
        }
        if (match) {
          commitEdit(match.id);
        } else if (editingState.selectedIndex >= 0 &&
                   editingState.items.length > 0) {
          commitEdit(editingState.items[editingState.selectedIndex].id);
        } else if (typed) {
          showValidationError("Unknown shift code \u201c" + typed + "\u201d");
        } else {
          commitEdit();
        }
      } else if (key === "Escape") {
        e.preventDefault();
        e.stopPropagation();
        cancelEdit();
      } else if (key === "ArrowDown") {
        e.preventDefault();
        e.stopPropagation();
        moveSelection(1);
      } else if (key === "ArrowUp") {
        e.preventDefault();
        e.stopPropagation();
        moveSelection(-1);
      } else if (key === "Tab") {
        e.preventDefault();
        e.stopPropagation();
        var dir = e.shiftKey ? "left" : "right";
        var cur = editingState.td;
        commitEdit();
        setTimeout(function () {
          var next = neighborCell(cur, dir);
          if (next) startEdit(next, "typing");
        }, 0);
      } else if (key === "ArrowLeft" || key === "ArrowRight") {
        return;
      }
    }

    function moveSelection(delta) {
      if (!editingState) return;
      var items = editingState.items;
      if (items.length === 0) return;
      var idx = editingState.selectedIndex + delta;
      if (idx < 0) idx = items.length - 1;
      if (idx >= items.length) idx = 0;
      editingState.selectedIndex = idx;
      renderAutocomplete(editingState.input.value);
      var sel = editingState.list.querySelector(".editing-item.selected");
      if (sel && sel.scrollIntoView) {
        sel.scrollIntoView({ block: "nearest" });
      }
    }

    function showValidationError(msg) {
      if (!editingState) return;
      var input = editingState.input;
      input.classList.add("validation-error");
      setTimeout(function () {
        if (editingState) {
          editingState.input.classList.remove("validation-error");
        }
      }, 800);
      showToast(msg, "error");
    }

    function commitEdit(shiftId) {
      if (!editingState) return;

      if (shiftId === undefined) {
        var typed = (editingState.input.value || "").toUpperCase().trim();
        if (typed) {
          var all = shiftCache.list();
          for (var i = 0; i < all.length; i++) {
            if (all[i].code.toUpperCase() === typed) {
              shiftId = all[i].id;
              break;
            }
          }
        }
        if (shiftId === undefined &&
            editingState.selectedIndex >= 0 &&
            editingState.items.length > 0) {
          shiftId = editingState.items[editingState.selectedIndex].id;
        }
        if (shiftId === undefined) {
          if (typed) {
            showValidationError("Unknown shift code \u201c" + typed + "\u201d");
          } else {
            cancelEdit();
          }
          return;
        }
      }

      var original = editingState.originalShift;
      if (original && original.id === shiftId) {
        cancelEdit();
        return;
      }

      var td = editingState.td;
      var entryId = editingState.entryId;
      var dropdownEl = editingState.dropdown;
      var scrollHandler = editingState.scrollHandler;
      var resizeHandler = editingState.resizeHandler;
      var byId = shiftCache.byId();
      var shift = byId[shiftId];

      renderCellWithShift(td, shift, true);

      fetch(apiBase + "/entries/" + entryId, {
        method: "PATCH",
        headers: headers(),
        body: JSON.stringify({ shift_type_id: shiftId }),
      })
        .then(function (r) {
          if (r.status === 401) { ShiftRoster.logout(); return null; }
          if (!r.ok) {
            return r.json().then(function (d) {
              throw new Error(d.detail || "Save failed");
            });
          }
          return r.json();
        })
        .then(function (updated) {
          if (!updated) return;
          entriesById[updated.id] = updated;
          var newShift = updated.shift;
          var shiftObj = newShift ? byId[newShift.id] : null;
          renderCellWithShift(td, shiftObj, false);
          var row = td.parentNode;
          if (row && row.classList.contains("active-row")) {
            clearActiveHighlights();
            editingState = null;
          }
          if (scrollHandler) window.removeEventListener("scroll", scrollHandler, true);
          if (resizeHandler) window.removeEventListener("resize", resizeHandler);
          if (dropdownEl && dropdownEl.parentNode) {
            dropdownEl.parentNode.removeChild(dropdownEl);
          }
          var code = newShift ? newShift.code : "(cleared)";
          showToast("Saved " + code, "success");
        })
        .catch(function (err) {
          var originalEntry = entriesById[entryId];
          var originalShiftObj = (originalEntry && originalEntry.shift)
            ? byId[originalEntry.shift.id]
            : null;
          renderCellWithShift(td, originalShiftObj, false);
          var row = td.parentNode;
          if (row && row.classList.contains("active-row")) {
            clearActiveHighlights();
            editingState = null;
          }
          if (scrollHandler) window.removeEventListener("scroll", scrollHandler, true);
          if (resizeHandler) window.removeEventListener("resize", resizeHandler);
          if (dropdownEl && dropdownEl.parentNode) {
            dropdownEl.parentNode.removeChild(dropdownEl);
          }
          showToast("Save failed: " + (err.message || "unknown error"), "error");
        });
    }

    function cancelEdit() {
      if (!editingState) return;
      var td = editingState.td;
      var entryId = editingState.entryId;
      var entry = entriesById[entryId];
      var byId = shiftCache.byId();
      var shiftObj = entry && entry.shift ? byId[entry.shift.id] : null;
      var dropdownEl = editingState.dropdown;
      var scrollHandler = editingState.scrollHandler;
      var resizeHandler = editingState.resizeHandler;
      td.classList.remove("editing", "validation-error");
      renderCellWithShift(td, shiftObj, false);
      clearActiveHighlights();
      editingState = null;
      if (scrollHandler) window.removeEventListener("scroll", scrollHandler, true);
      if (resizeHandler) window.removeEventListener("resize", resizeHandler);
      if (dropdownEl && dropdownEl.parentNode) {
        dropdownEl.parentNode.removeChild(dropdownEl);
      }
    }

    function renderCellWithShift(td, shift, isSaving) {
      td.classList.remove("editing", "validation-error", "saving", "empty");
      if (isSaving) td.classList.add("saving");

      if (shift) {
        var rgb = shiftColorRgb(shift.color);
        td.innerHTML =
          '<div class="shift-pill" style="background-color: rgb(' +
          rgb.join(",") +
          ');" title="' + esc(shift.display_name || shift.code || "") +
          '">' + esc(shift.code || "") + '</div>';
        td.setAttribute("data-shift-id", shift.id);
        td.setAttribute("data-shift-code", shift.code);
      } else {
        td.innerHTML = "";
        td.classList.add("empty");
        td.removeAttribute("data-shift-id");
        td.removeAttribute("data-shift-code");
      }
    }

    function neighborCell(td, dir) {
      if (!td) return null;
      var row = td.parentNode;
      var day = parseInt(td.getAttribute("data-day"), 10);
      if (dir === "right" || dir === "left") {
        var newDay = day + (dir === "right" ? 1 : -1);
        if (newDay < 1) return null;
        var cells = row.querySelectorAll("td.day-cell");
        for (var i = 0; i < cells.length; i++) {
          if (parseInt(cells[i].getAttribute("data-day"), 10) === newDay) {
            return cells[i];
          }
        }
        return null;
      }
      if (dir === "down" || dir === "up") {
        var table = document.getElementById("roster-grid");
        var tbody = table ? table.querySelector("tbody") : null;
        if (!tbody) return null;
        var rows = tbody.querySelectorAll("tr");
        var rowIndex = -1;
        for (var r = 0; r < rows.length; r++) {
          if (rows[r] === row) { rowIndex = r; break; }
        }
        var newRowIndex = rowIndex + (dir === "down" ? 1 : -1);
        if (newRowIndex < 0 || newRowIndex >= rows.length) return null;
        var newRow = rows[newRowIndex];
        var newCells = newRow.querySelectorAll("td.day-cell");
        for (var j = 0; j < newCells.length; j++) {
          if (parseInt(newCells[j].getAttribute("data-day"), 10) === day) {
            return newCells[j];
          }
        }
        return null;
      }
      return null;
    }

    function setupEditingHandlers() {
      var body = els.gridBody;
      if (!body || body.dataset.editBound === "1") return;
      body.dataset.editBound = "1";

      body.addEventListener("click", function (e) {
        var td = e.target.closest("td.day-cell");
        if (!td) return;
        if (e.target.closest(".editing-input, .editing-dropdown")) return;
        e.stopPropagation();
        startEdit(td, "typing");
      });

      body.addEventListener("dblclick", function (e) {
        var td = e.target.closest("td.day-cell");
        if (!td) return;
        e.preventDefault();
        e.stopPropagation();
        if (editingState && editingState.td === td) return;
        startEdit(td, "dropdown");
      });

      document.addEventListener("click", function (e) {
        if (!editingState) return;
        if (e.target.closest("#roster-grid-body")) return;
        if (e.target.closest(".editing-dropdown")) return;
        commitEdit();
      });
    }

    // ---- API ----
    function rosterUrl(year, month) {
      return usePublicApi
        ? apiBase + "/" + year + "/" + month + "/public"
        : apiBase + "/" + year + "/" + month;
    }

    function loadRoster(autoGenerate) {
      var year = parseInt(els.yearSelect.value, 10);
      var month = parseInt(els.monthSelect.value, 10);
      var monthLabel = els.monthSelect.options[els.monthSelect.selectedIndex].text + " " + year;
      setLoading(true);
      setStatus(false, monthLabel);

      fetch(rosterUrl(year, month), { headers: headers() })
        .then(function (r) {
          if (r.status === 401) { ShiftRoster.logout(); return null; }
          if (!r.ok) { throw new Error("Failed to load roster"); }
          return r.json();
        })
        .then(function (data) {
          if (!data) return;
          lastData = data;
          renderStats(data.meta);
          setStatus(data.meta.is_generated, data.meta.month_name + " " + data.meta.year);
          updateGenerateButton(data.meta.is_generated);
          if (data.meta.is_generated) {
            setEntriesById(data.entries);
            renderGrid(els, shiftCache, data.meta, data.entries);
            setTimeout(function () {
              scrollFade.update();
              scrollToToday(data.meta);
            }, 0);
          } else {
            if (data.meta.total_employees === 0) {
              renderGrid(els, shiftCache, data.meta, []);
              return;
            }
            els.gridContainer.classList.add("hidden");
            els.gridSummary.classList.add("hidden");
            els.noEmployeesState.classList.add("hidden");
            // On the public read-only page, show a friendly "not generated
            // yet" card so visitors know nothing is wrong — the admin just
            // hasn't generated this month yet.
            var notGen = document.getElementById("not-generated-state");
            if (notGen) notGen.classList.remove("hidden");
            if (autoGenerate && isEditable) {
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
      var year = parseInt(els.yearSelect.value, 10);
      var month = parseInt(els.monthSelect.value, 10);
      if (els.btnGenerate) els.btnGenerate.disabled = true;
      if (els.genIcon) els.genIcon.classList.add("hidden");
      if (els.genSpinner) els.genSpinner.classList.remove("hidden");
      if (els.genText) els.genText.textContent = "Generating…";
      setLoading(false);

      fetch(apiBase + "/" + year + "/" + month + "/generate", {
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
          lastData = data;
          renderStats(data.meta);
          setStatus(data.meta.is_generated, data.meta.month_name + " " + data.meta.year);
          updateGenerateButton(data.meta.is_generated);
          setEntriesById(data.entries);
          renderGrid(els, shiftCache, data.meta, data.entries);
          setTimeout(function () {
            scrollFade.update();
            scrollToToday(data.meta);
          }, 0);
          if (!silent) {
            showToast(
              "Generated " + data.meta.total_records +
              " roster entries for " + data.meta.month_name + " " + data.meta.year,
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
          if (els.genIcon) els.genIcon.classList.remove("hidden");
          if (els.genSpinner) els.genSpinner.classList.add("hidden");
          if (els.btnGenerate) els.btnGenerate.disabled = false;
        });
    }

    // ---- Init ----
    function init() {
      var now = new Date();
      els.monthSelect.value = String(now.getMonth() + 1);
      var year = now.getFullYear();
      if (!els.yearSelect.querySelector('option[value="' + year + '"]')) {
        var opt = document.createElement("option");
        opt.value = String(year);
        opt.textContent = String(year);
        els.yearSelect.appendChild(opt);
      }
      els.yearSelect.value = String(year);

      if (els.btnLoad) {
        els.btnLoad.addEventListener("click", function () { loadRoster(false); });
      }
      if (els.btnGenerate && isEditable) {
        els.btnGenerate.addEventListener("click", function () { generateRoster(false); });
      }
      els.monthSelect.addEventListener("change", function () { loadRoster(true); });
      els.yearSelect.addEventListener("change", function () { loadRoster(true); });

      if (isEditable) {
        setupEditingHandlers();
      }

      injectColumnHoverCSS();
      attachColumnHover();
      scrollFade.attach();
      bindExpandHandler();
      shiftCache.reload().then(function () { loadRoster(true); });
    }

    function boot() {
      if (requireAuth && !ShiftRoster.isLoggedIn()) {
        ShiftRoster.requireAuth();
        return;
      }
      init();
    }

    return {
      boot: boot,
      // For tests / external triggers
      loadRoster: loadRoster,
      // Read-only state access
      get lastData() { return lastData; },
    };
  }

  global.ShiftRosterGrid = { create: create };
})(window);

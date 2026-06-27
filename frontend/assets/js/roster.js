/* ------------------------------------------------------------------
   Shift Roster — Roster Management page (Phase 5)
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  // Ensure theme + boot wiring runs on this page even if admin.js
  // hasn't loaded yet.
  if (window.ShiftRoster && typeof ShiftRoster.boot === "function") {
    ShiftRoster.boot();
  }

  var API_BASE = "/api/roster";
  var PREVIEW_LIMIT = 50;

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
  var statRecords = document.getElementById("stat-records");
  var statusDot = document.getElementById("status-dot");
  var statusText = document.getElementById("status-text");
  var loadingState = document.getElementById("loading-state");
  var emptyState = document.getElementById("empty-state");
  var tableWrapper = document.getElementById("table-wrapper");
  var tbody = document.getElementById("roster-tbody");
  var previewFooter = document.getElementById("preview-footer");
  var toastContainer = document.getElementById("toast-container");

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
      setTimeout(function () {
        el.remove();
      }, 300);
    }, 3500);
  }

  // ---- Rendering ----

  function setLoading(loading) {
    if (loading) {
      loadingState.classList.remove("hidden");
      tableWrapper.classList.add("hidden");
      emptyState.classList.add("hidden");
    } else {
      loadingState.classList.add("hidden");
    }
  }

  function setStatus(generated, monthName) {
    if (generated) {
      statusDot.className =
        "inline-block h-2 w-2 rounded-full bg-emerald-500";
      statusText.textContent =
        "Roster for " + monthName + " has been generated.";
      statusText.className = "text-slate-700 dark:text-slate-200";
    } else {
      statusDot.className = "inline-block h-2 w-2 rounded-full bg-amber-500";
      statusText.textContent =
        "No roster yet for " + monthName + ". Generate to create the empty grid.";
      statusText.className = "text-slate-600 dark:text-slate-300";
    }
  }

  function renderStats(meta) {
    statMonth.textContent =
      meta.month_name + " " + meta.year;
    statEmployees.textContent = meta.total_employees;
    statDays.textContent = meta.total_days;
    statRecords.textContent = meta.total_records;
  }

  function renderTable(entries) {
    tbody.innerHTML = "";
    if (!entries || entries.length === 0) {
      tableWrapper.classList.add("hidden");
      previewFooter.textContent = "";
      return;
    }
    tableWrapper.classList.remove("hidden");
    var shown = 0;
    for (var i = 0; i < entries.length; i++) {
      if (shown >= PREVIEW_LIMIT) break;
      var e = entries[i];
      var shiftCell;
      if (e.shift) {
        shiftCell =
          '<span class="inline-flex items-center gap-1 rounded-full bg-slate-100 px-2.5 py-0.5 text-xs font-medium dark:bg-slate-800"><span class="h-1.5 w-1.5 rounded-full" style="background-color:' +
          esc(e.shift.color) +
          '"></span>' +
          esc(e.shift.code) +
          " " +
          esc(e.shift.display_name) +
          "</span>";
      } else {
        shiftCell =
          '<span class="text-xs text-slate-400 dark:text-slate-500">—</span>';
      }
      var tr = document.createElement("tr");
      tr.className =
        "transition hover:bg-slate-50/80 dark:hover:bg-slate-800/40";
      tr.innerHTML =
        '<td class="px-5 py-2.5 text-slate-900 dark:text-slate-100">' +
        esc(e.employee.employee_name) +
        ' <span class="text-xs text-slate-400">(' +
        esc(e.employee.employee_code) +
        ")</span></td>" +
        '<td class="px-5 py-2.5 text-slate-600 dark:text-slate-300">' +
        esc(e.date) +
        "</td>" +
        '<td class="px-5 py-2.5">' +
        shiftCell +
        "</td>" +
        '<td class="px-5 py-2.5 text-slate-600 dark:text-slate-300">' +
        (e.remarks ? esc(e.remarks) : '<span class="text-xs text-slate-400 dark:text-slate-500">—</span>') +
        "</td>";
      tbody.appendChild(tr);
      shown++;
    }
    if (entries.length > PREVIEW_LIMIT) {
      previewFooter.textContent =
        "Showing first " +
        PREVIEW_LIMIT +
        " of " +
        entries.length +
        " rows";
    } else {
      previewFooter.textContent = "Showing all " + entries.length + " rows";
    }
  }

  function updateGenerateButton(generated) {
    btnGenerate.disabled = generated;
    if (generated) {
      genText.textContent = "Already Generated";
    } else {
      genText.textContent = "Generate Roster";
    }
  }

  // ---- API ----

  function loadRoster(autoGenerate) {
    var year = parseInt(yearSelect.value, 10);
    var month = parseInt(monthSelect.value, 10);
    setLoading(true);
    setStatus(false, monthSelect.options[monthSelect.selectedIndex].text + " " + year);

    fetch(API_BASE + "/" + year + "/" + month, { headers: headers() })
      .then(function (r) {
        if (r.status === 401) {
          ShiftRoster.logout();
          return null;
        }
        if (!r.ok) {
          throw new Error("Failed to load roster");
        }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        renderStats(data.meta);
        setStatus(data.meta.is_generated, data.meta.month_name + " " + data.meta.year);
        updateGenerateButton(data.meta.is_generated);
        if (data.meta.is_generated) {
          renderTable(data.entries);
        } else {
          if (data.meta.total_employees === 0) {
            tableWrapper.classList.add("hidden");
            emptyState.classList.add("hidden");
            statusText.textContent =
              "No active employees — add at least one to generate a roster.";
          } else {
            emptyState.classList.remove("hidden");
            tableWrapper.classList.add("hidden");
            if (autoGenerate) {
              generateRoster(true);
              return;
            }
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

    fetch(API_BASE + "/" + year + "/" + month + "/generate", {
      method: "POST",
      headers: headers(),
    })
      .then(function (r) {
        if (r.status === 401) {
          ShiftRoster.logout();
          return null;
        }
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
        renderTable(data.entries);
        emptyState.classList.add("hidden");
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
    // Default selectors to current month/year
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

    btnLoad.addEventListener("click", function () {
      loadRoster(false);
    });
    btnGenerate.addEventListener("click", function () {
      generateRoster(false);
    });
    monthSelect.addEventListener("change", function () {
      loadRoster(true);
    });
    yearSelect.addEventListener("change", function () {
      loadRoster(true);
    });

    // Auto-load on first paint and auto-generate if needed
    loadRoster(true);
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!ShiftRoster.isLoggedIn()) {
      ShiftRoster.requireAuth();
      return;
    }
    init();
  });
})();

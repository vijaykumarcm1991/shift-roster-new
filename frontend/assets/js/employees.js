/* ------------------------------------------------------------------
   Shift Roster — Employee Directory page script
   ------------------------------------------------------------------ */

(function () {
  "use strict";

  // Ensure theme + boot wiring runs on this page even if the admin
  // layout script hasn't loaded yet.
  if (window.ShiftRoster && typeof ShiftRoster.boot === "function") {
    ShiftRoster.boot();
  }

  var API = "/api/employees";
  var TEAMS_API = "/api/teams";

  // DOM refs
  var tbody = document.getElementById("employees-tbody");
  var emptyState = document.getElementById("empty-state");
  var loadingState = document.getElementById("loading-state");
  var pageInfo = document.getElementById("page-info");
  var pageNumbers = document.getElementById("page-numbers");
  var prevBtn = document.getElementById("prev-page");
  var nextBtn = document.getElementById("next-page");
  var pageSizeSelect = document.getElementById("page-size");
  var searchInput = document.getElementById("search-input");
  var teamFilter = document.getElementById("team-filter");
  var statusFilter = document.getElementById("status-filter");

  // Drawer
  var drawer = document.getElementById("employee-drawer");
  var drawerBackdrop = document.getElementById("drawer-backdrop");
  var drawerTitle = document.getElementById("drawer-title");
  var form = document.getElementById("employee-form");
  var addBtn = document.getElementById("btn-add-employee");
  var addEmptyBtn = document.getElementById("btn-add-empty");
  var closeDrawerBtn = document.getElementById("close-drawer");
  var cancelDrawerBtn = document.getElementById("cancel-drawer");
  var saveBtnText = document.getElementById("save-btn-text");
  var saveSpinner = document.getElementById("save-spinner");

  // Form fields
  var fCode = document.getElementById("f-code");
  var fName = document.getElementById("f-name");
  var fEmail = document.getElementById("f-email");
  var fDesignation = document.getElementById("f-designation");
  var fTeam = document.getElementById("f-team");
  var fActive = document.getElementById("f-active");

  // Error fields
  var errCode = document.getElementById("err-code");
  var errName = document.getElementById("err-name");
  var errEmail = document.getElementById("err-email");

  // Confirm dialog
  var confirmBackdrop = document.getElementById("confirm-backdrop");
  var confirmDialog = document.getElementById("confirm-dialog");
  var confirmTitle = document.getElementById("confirm-title");
  var confirmMessage = document.getElementById("confirm-message");
  var confirmOk = document.getElementById("confirm-ok");
  var confirmCancel = document.getElementById("confirm-cancel");

  // Team modal
  var addTeamBtn = document.getElementById("btn-add-team");
  var teamModal = document.getElementById("team-modal");
  var teamModalBackdrop = document.getElementById("team-modal-backdrop");
  var teamModalClose = document.getElementById("team-modal-close");
  var teamModalCancel = document.getElementById("team-modal-cancel");
  var teamForm = document.getElementById("team-form");
  var tName = document.getElementById("t-name");
  var tDescription = document.getElementById("t-description");
  var tOrder = document.getElementById("t-order");
  var tErrName = document.getElementById("t-err-name");
  var teamSaveSpinner = document.getElementById("team-save-spinner");
  var teamSaveText = document.getElementById("team-save-text");

  // Toast
  var toastContainer = document.getElementById("toast-container");

  // State
  var currentPage = 1;
  var totalPages = 1;
  var totalItems = 0;
  var editingId = null;
  var searchTimer = null;

  // ─── Helpers ──────────────────────────────────────────────

  function headers(extra) {
    return Object.assign({ "Content-Type": "application/json" }, ShiftRoster.authHeaders(), extra || {});
  }

  function esc(str) {
    if (!str) return "";
    var d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  // ─── Toast notifications ──────────────────────────────────

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
    el.className = "flex items-center gap-2 rounded-xl px-4 py-3 text-sm font-medium shadow-lg transition-all duration-300 " + (colors[type] || colors.info);
    el.innerHTML = (icons[type] || icons.info) + " " + esc(message);
    toastContainer.appendChild(el);
    setTimeout(function () {
      el.style.opacity = "0";
      el.style.transform = "translateX(100%)";
      setTimeout(function () { el.remove(); }, 300);
    }, 3500);
  }

  // ─── Confirm dialog ───────────────────────────────────────

  function showConfirm(title, message, onOk) {
    confirmTitle.textContent = title;
    confirmMessage.textContent = message;
    confirmBackdrop.classList.remove("hidden");
    confirmDialog.classList.remove("hidden");
    confirmOk.onclick = function () {
      hideConfirm();
      onOk();
    };
  }

  function hideConfirm() {
    confirmBackdrop.classList.add("hidden");
    confirmDialog.classList.add("hidden");
    confirmOk.onclick = null;
  }

  confirmCancel.addEventListener("click", hideConfirm);
  confirmBackdrop.addEventListener("click", hideConfirm);

  // ─── Load teams for filter + drawer dropdown ──────────────

  function loadTeams() {
    fetch(TEAMS_API, { headers: headers() })
      .then(function (r) { return r.json(); })
      .then(function (teams) {
        teamFilter.innerHTML = '<option value="">All Teams</option>';
        fTeam.innerHTML = '<option value="">No Team</option>';
        teams.forEach(function (t) {
          teamFilter.innerHTML += '<option value="' + t.id + '">' + esc(t.team_name) + '</option>';
          fTeam.innerHTML += '<option value="' + t.id + '">' + esc(t.team_name) + '</option>';
        });
      })
      .catch(function () {});
  }

  // ─── Fetch employees ─────────────────────────────────────

  function fetchEmployees() {
    loadingState.classList.remove("hidden");
    tbody.innerHTML = "";
    emptyState.classList.add("hidden");

    var params = new URLSearchParams({
      page: currentPage,
      page_size: pageSizeSelect.value,
    });
    var searchVal = searchInput.value.trim();
    if (searchVal) params.append("search", searchVal);
    if (teamFilter.value) params.append("team_id", teamFilter.value);
    if (statusFilter.value) params.append("status", statusFilter.value);

    fetch(API + "?" + params.toString(), { headers: headers() })
      .then(function (r) {
        if (r.status === 401) { ShiftRoster.logout(); return null; }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        loadingState.classList.add("hidden");
        totalItems = data.total;
        totalPages = data.total_pages || 0;
        renderTable(data.items || []);
        renderPagination(data.page, data.total_pages, data.total, data.page_size);
      })
      .catch(function () {
        loadingState.classList.add("hidden");
        showToast("Failed to load employees", "error");
      });
  }

  // ─── Render table ─────────────────────────────────────────

  function renderTable(items) {
    tbody.innerHTML = "";
    if (!items || items.length === 0) {
      emptyState.classList.remove("hidden");
      return;
    }
    emptyState.classList.add("hidden");

    items.forEach(function (emp) {
      var statusBadge = emp.is_active
        ? '<span class="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300"><span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>Active</span>'
        : '<span class="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-700 dark:bg-red-500/10 dark:text-red-300"><span class="h-1.5 w-1.5 rounded-full bg-red-500"></span>Inactive</span>';

      var actionBtns = "";
      actionBtns += '<button data-id="' + emp.id + '" class="edit-btn inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-indigo-600 transition hover:bg-indigo-50 dark:text-indigo-400 dark:hover:bg-indigo-500/10" title="Edit"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5"><path d="M2.695 14.763l-1.262 3.154a.5.5 0 00.65.65l3.155-1.262a4 4 0 001.343-.885L17.5 5.5a2.121 2.121 0 00-3-3L3.58 13.42a4 4 0 00-.885 1.343z"/></svg>Edit</button>';
      if (emp.is_active) {
        actionBtns += '<button data-id="' + emp.id + '" data-name="' + esc(emp.employee_name) + '" class="deactivate-btn inline-flex items-center gap-1 rounded-lg px-2 py-1 text-xs font-medium text-red-600 transition hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10" title="Deactivate"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="h-3.5 w-3.5"><path fill-rule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clip-rule="evenodd"/></svg>Deactivate</button>';
      }

      var tr = document.createElement("tr");
      tr.className = "transition hover:bg-slate-50/80 dark:hover:bg-slate-800/40";
      tr.innerHTML =
        '<td class="px-5 py-3 font-medium text-slate-900 dark:text-white">' + esc(emp.employee_code) + '</td>' +
        '<td class="px-5 py-3 text-slate-700 dark:text-slate-200">' + esc(emp.employee_name) + '</td>' +
        '<td class="hidden px-5 py-3 text-slate-600 md:table-cell dark:text-slate-400">' + esc(emp.email || "—") + '</td>' +
        '<td class="hidden px-5 py-3 text-slate-600 lg:table-cell dark:text-slate-400">' + esc(emp.designation || "—") + '</td>' +
        '<td class="hidden px-5 py-3 text-slate-600 sm:table-cell dark:text-slate-400">' + esc(emp.team_name || "—") + '</td>' +
        '<td class="px-5 py-3">' + statusBadge + '</td>' +
        '<td class="px-5 py-3 text-center"><div class="flex items-center justify-center gap-1">' + actionBtns + '</div></td>';
      tbody.appendChild(tr);
    });

    // Attach action listeners
    tbody.querySelectorAll(".edit-btn").forEach(function (btn) {
      btn.addEventListener("click", function () { openDrawer("edit", btn.dataset.id); });
    });
    tbody.querySelectorAll(".deactivate-btn").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var empName = btn.dataset.name || "this employee";
        showConfirm(
          "Deactivate Employee",
          "Are you sure you want to deactivate " + empName + "? They will be marked as inactive.",
          function () { deactivateEmployee(btn.dataset.id); }
        );
      });
    });
  }

  // ─── Pagination ───────────────────────────────────────────

  function renderPagination(page, tPages, total, pageSize) {
    var start = total === 0 ? 0 : (page - 1) * pageSize + 1;
    var end = Math.min(page * pageSize, total);
    pageInfo.textContent = "Showing " + start + "–" + end + " of " + total;
    prevBtn.disabled = page <= 1;
    nextBtn.disabled = page >= tPages;
    renderPageNumbers(page, tPages);
  }

  function renderPageNumbers(current, tPages) {
    pageNumbers.innerHTML = "";
    if (tPages <= 1) return;
    var pages = [];
    if (tPages <= 7) {
      for (var i = 1; i <= tPages; i++) pages.push(i);
    } else {
      pages.push(1);
      if (current > 3) pages.push("...");
      for (var j = Math.max(2, current - 1); j <= Math.min(tPages - 1, current + 1); j++) pages.push(j);
      if (current < tPages - 2) pages.push("...");
      pages.push(tPages);
    }
    pages.forEach(function (p) {
      var btn = document.createElement("button");
      if (p === "...") {
        btn.type = "button";
        btn.className = "inline-flex h-8 w-8 items-center justify-center text-xs text-slate-400 dark:text-slate-500";
        btn.textContent = "…";
        btn.disabled = true;
      } else {
        btn.type = "button";
        btn.className = p === current
          ? "inline-flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-xs font-medium text-white"
          : "inline-flex h-8 w-8 items-center justify-center rounded-lg text-xs font-medium text-slate-600 transition hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800";
        btn.textContent = p;
        btn.addEventListener("click", function () { currentPage = p; fetchEmployees(); });
      }
      pageNumbers.appendChild(btn);
    });
  }

  // ─── Drawer open / close ──────────────────────────────────

  function openDrawer(mode, id) {
    editingId = null;
    clearFormErrors();
    form.reset();
    fActive.checked = true;

    if (mode === "edit") {
      editingId = id;
      drawerTitle.textContent = "Edit Employee";
      saveBtnText.textContent = "Update";
      fetch(API + "/" + id, { headers: headers() })
        .then(function (r) {
          if (r.status === 401) { ShiftRoster.logout(); return; }
          return r.json();
        })
        .then(function (emp) {
          if (!emp) return;
          fCode.value = emp.employee_code || "";
          fName.value = emp.employee_name || "";
          fEmail.value = emp.email || "";
          fDesignation.value = emp.designation || "";
          fTeam.value = emp.team_id || "";
          fActive.checked = emp.is_active;
        })
        .catch(function () { showToast("Failed to load employee", "error"); });
    } else {
      drawerTitle.textContent = "Add Employee";
      saveBtnText.textContent = "Save";
    }

    drawer.classList.remove("translate-x-full");
    drawerBackdrop.classList.remove("hidden");
    setTimeout(function () { fCode.focus(); }, 300);
  }

  function closeDrawer() {
    drawer.classList.add("translate-x-full");
    drawerBackdrop.classList.add("hidden");
    editingId = null;
    clearFormErrors();
  }

  addBtn.addEventListener("click", function () { openDrawer("add"); });
  addEmptyBtn.addEventListener("click", function () { openDrawer("add"); });
  closeDrawerBtn.addEventListener("click", closeDrawer);
  cancelDrawerBtn.addEventListener("click", closeDrawer);
  drawerBackdrop.addEventListener("click", closeDrawer);

  // ─── Form validation ──────────────────────────────────────

  function clearFormErrors() {
    errCode.classList.add("hidden"); errCode.textContent = "";
    errName.classList.add("hidden"); errName.textContent = "";
    errEmail.classList.add("hidden"); errEmail.textContent = "";
    fCode.classList.remove("border-red-500");
    fName.classList.remove("border-red-500");
    fEmail.classList.remove("border-red-500");
  }

  function showFieldError(errEl, inputEl, msg) {
    errEl.textContent = msg;
    errEl.classList.remove("hidden");
    inputEl.classList.add("border-red-500");
  }

  function validateForm() {
    clearFormErrors();
    var valid = true;
    if (!fCode.value.trim()) { showFieldError(errCode, fCode, "Employee code is required"); valid = false; }
    if (!fName.value.trim()) { showFieldError(errName, fName, "Employee name is required"); valid = false; }
    if (fEmail.value.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(fEmail.value.trim())) {
      showFieldError(errEmail, fEmail, "Invalid email format");
      valid = false;
    }
    return valid;
  }

  // ─── Save (create / update) ───────────────────────────────

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!validateForm()) return;

    saveBtnText.textContent = editingId ? "Updating…" : "Saving…";
    saveSpinner.classList.remove("hidden");

    var payload = {
      employee_code: fCode.value.trim(),
      employee_name: fName.value.trim(),
      email: fEmail.value.trim() || null,
      designation: fDesignation.value.trim() || null,
      team_id: fTeam.value ? Number(fTeam.value) : null,
      is_active: fActive.checked,
    };

    var method = editingId ? "PUT" : "POST";
    var url = editingId ? API + "/" + editingId : API;

    fetch(url, {
      method: method,
      headers: headers(),
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        if (r.status === 401) { ShiftRoster.logout(); return null; }
        return r.json().then(function (d) { return { status: r.status, data: d }; });
      })
      .then(function (result) {
        if (!result) return;
        saveSpinner.classList.add("hidden");
        saveBtnText.textContent = editingId ? "Update" : "Save";

        if (result.status >= 400) {
          var detail = result.data.detail || "An error occurred";
          if (detail.toLowerCase().indexOf("code") !== -1) {
            showFieldError(errCode, fCode, detail);
          } else if (detail.toLowerCase().indexOf("email") !== -1) {
            showFieldError(errEmail, fEmail, detail);
          } else {
            showToast(detail, "error");
          }
          return;
        }

        closeDrawer();
        showToast(editingId ? "Employee updated" : "Employee created", "success");
        fetchEmployees();
      })
      .catch(function () {
        saveSpinner.classList.add("hidden");
        saveBtnText.textContent = editingId ? "Update" : "Save";
        showToast("Network error — please try again", "error");
      });
  });

  // ─── Deactivate (soft delete) ─────────────────────────────

  function deactivateEmployee(id) {
    fetch(API + "/" + id, {
      method: "DELETE",
      headers: headers(),
    })
      .then(function (r) {
        if (r.status === 401) { ShiftRoster.logout(); return null; }
        return r.json();
      })
      .then(function (data) {
        if (!data) return;
        if (data.detail) {
          showToast(data.detail, "error");
        } else {
          showToast("Employee deactivated", "success");
          fetchEmployees();
        }
      })
      .catch(function () { showToast("Network error — please try again", "error"); });
  }

  // ─── Team modal (add team) ─────────────────────────────────

  function openTeamModal() {
    teamForm.reset();
    tOrder.value = "0";
    clearTeamFormErrors();
    teamModal.classList.remove("hidden");
    teamModalBackdrop.classList.remove("hidden");
    setTimeout(function () { tName.focus(); }, 50);
  }

  function closeTeamModal() {
    teamModal.classList.add("hidden");
    teamModalBackdrop.classList.add("hidden");
    clearTeamFormErrors();
  }

  function clearTeamFormErrors() {
    tErrName.classList.add("hidden");
    tErrName.textContent = "";
    tName.classList.remove("border-red-500");
  }

  function validateTeamForm() {
    clearTeamFormErrors();
    var valid = true;
    if (!tName.value.trim()) {
      tErrName.textContent = "Team name is required";
      tErrName.classList.remove("hidden");
      tName.classList.add("border-red-500");
      valid = false;
    }
    var orderVal = parseInt(tOrder.value, 10);
    if (isNaN(orderVal) || orderVal < 0) {
      showToast("Display order must be a non-negative number", "error");
      valid = false;
    }
    return valid;
  }

  teamForm.addEventListener("submit", function (e) {
    e.preventDefault();
    if (!validateTeamForm()) return;

    teamSaveText.textContent = "Creating…";
    teamSaveSpinner.classList.remove("hidden");

    var payload = {
      team_name: tName.value.trim(),
      description: tDescription.value.trim() || null,
      display_order: parseInt(tOrder.value, 10) || 0,
      is_active: true,
    };

    fetch(TEAMS_API, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(payload),
    })
      .then(function (r) {
        if (r.status === 401) { ShiftRoster.logout(); return null; }
        return r.json().then(function (d) { return { status: r.status, data: d }; });
      })
      .then(function (result) {
        if (!result) return;
        teamSaveSpinner.classList.add("hidden");
        teamSaveText.textContent = "Create Team";

        if (result.status >= 400) {
          var detail = result.data.detail || "Failed to create team";
          if (typeof detail === "string" && detail.toLowerCase().indexOf("name") !== -1) {
            tErrName.textContent = detail;
            tErrName.classList.remove("hidden");
            tName.classList.add("border-red-500");
          } else {
            showToast(typeof detail === "string" ? detail : "Failed to create team", "error");
          }
          return;
        }

        var newTeam = result.data;
        // Refresh both team dropdowns so the new team is selectable.
        loadTeams();
        // Auto-select the new team in the employee drawer (if it's open).
        // Use a small delay so loadTeams() has time to populate the select.
        setTimeout(function () {
          if (fTeam && newTeam && newTeam.id) {
            fTeam.value = String(newTeam.id);
          }
        }, 200);

        showToast("Team '" + (newTeam.team_name || "") + "' created", "success");
        closeTeamModal();
      })
      .catch(function () {
        teamSaveSpinner.classList.add("hidden");
        teamSaveText.textContent = "Create Team";
        showToast("Network error — please try again", "error");
      });
  });

  addTeamBtn.addEventListener("click", openTeamModal);
  teamModalClose.addEventListener("click", closeTeamModal);
  teamModalCancel.addEventListener("click", closeTeamModal);
  teamModalBackdrop.addEventListener("click", closeTeamModal);

  // ─── Filter / pagination events ───────────────────────────

  prevBtn.addEventListener("click", function () { if (currentPage > 1) { currentPage--; fetchEmployees(); } });
  nextBtn.addEventListener("click", function () { if (currentPage < totalPages) { currentPage++; fetchEmployees(); } });
  pageSizeSelect.addEventListener("change", function () { currentPage = 1; fetchEmployees(); });
  teamFilter.addEventListener("change", function () { currentPage = 1; fetchEmployees(); });
  statusFilter.addEventListener("change", function () { currentPage = 1; fetchEmployees(); });

  // Debounced search (300ms)
  searchInput.addEventListener("input", function () {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { currentPage = 1; fetchEmployees(); }, 300);
  });

  // ─── Init ─────────────────────────────────────────────────

  document.addEventListener("DOMContentLoaded", function () {
    if (!ShiftRoster.isLoggedIn()) { ShiftRoster.requireAuth(); return; }
    loadTeams();
    fetchEmployees();
  });
})();

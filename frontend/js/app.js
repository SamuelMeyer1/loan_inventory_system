// ============================================================
// STATE OCH KONFIGURATION
// ============================================================

const state = {
  objects: [],
  loanCart: [],
  returnBusy: false,
  returnSummary: null,
  damageBusy: false,
  damagedReturns: [],
  users: [],
  groups: [],
  loans: [],
  jobs: [],
  consumableReports: [],
  events: [],
  systemSettings: {},
  statistics: {},
  editingObjectId: null,
  editingUserId: null,
  editingGroupId: null,
  cardUserId: null,
  autoUserCardScanTimer: null,
  autoUserCardScanBusy: false,
  lastAutoUserCardUid: "",
  lastAutoUserCardAt: 0,
  lastUnknownAutoUserCardUid: "",
  role: "operator",
  language: localStorage.getItem("language") || "sv",
  selectedJobId: null,
  dashboardTipIndex: 0,
  jobsCollapsed: localStorage.getItem("jobsCollapsed") === "1",
};

const viewTitles = {
  dashboard: "nav.dashboard",
  myLoans: "nav.myLoans",
  checkout: "nav.checkout",
  pickup: "nav.pickup",
  consumable: "nav.consumable",
  return: "nav.return",
  statistics: "nav.statistics",
  jobs: "nav.jobs",
  objects: "nav.objects",
  loans: "nav.loans",
  admin: "nav.admin",
  log: "nav.log",
  system: "nav.system",
};

const $ = (selector) => document.querySelector(selector);
const TABLE_RENDER_LIMIT = 500;
const notificationRecipientKeys = [
  "notification_recipients_new_job",
  "notification_recipients_returned_loan",
  "notification_recipients_low_stock",
  "notification_recipients_empty_stock",
];
const messageTemplateFields = [
  ["messageNewJobSubject", "message_new_job_subject"],
  ["messageNewJobBody", "message_new_job_body"],
  ["messagePickupReadySubject", "message_pickup_ready_subject"],
  ["messagePickupReadyBody", "message_pickup_ready_body"],
  ["messageReturnedLoanSubject", "message_returned_loan_subject"],
  ["messageReturnedLoanBody", "message_returned_loan_body"],
  ["messageStockAlertSubject", "message_stock_alert_subject"],
  ["messageStockAlertBody", "message_stock_alert_body"],
  ["messageLoanReminderSubject", "message_loan_reminder_subject"],
  ["messageLoanOverdueSubject", "message_loan_overdue_subject"],
  ["messageLoanReminderBody", "message_loan_reminder_body"],
];

// Translations are defined in translations.js.

// Translation helpers are defined in i18n.js.

// ============================================================
// API
// Alla anrop till backend samlas har.
// ============================================================

// API helpers are defined in api.js.

// ============================================================
// NAVIGATION OCH SIDANS HUVUDUPPDATERING
// ============================================================

function setView(view) {
  if (!canSeeView(view)) {
    view = "dashboard";
  }
  document.querySelectorAll(".nav-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === view);
  });
  document.querySelectorAll(".view").forEach((panel) => {
    panel.classList.toggle("active", panel.id === `${view}View`);
  });
  if (view === "statistics") {
  renderAllStatisticsCharts(state);
}
  updateAutoUserCardScan();
}

async function refreshAll() {
  const [stats, statistics, objects, users, groups, loans, jobs, consumableReports, events, systemSettings, damagedReturns] = await Promise.all([
    api("/api/stats"),
    state.role === "operator" ? Promise.resolve({}) : api("/api/statistics"),
    api("/api/objects"),
    api("/api/users"),
    state.role === "operator" ? Promise.resolve([]) : api("/api/groups"),
    api("/api/loans"),
    api("/api/loan-requests"),
    state.role === "operator" ? Promise.resolve([]) : api("/api/consumable-reports"),
    state.role === "superadmin" ? api("/api/events?limit=100") : Promise.resolve([]),
    api("/api/system-settings"),
    state.role === "operator" ? Promise.resolve([]) : api("/api/damaged-returns"),
  ]);

  state.objects = objects;
  state.statistics = statistics;
  state.users = users;
  state.groups = groups;
  state.loans = loans;
  state.jobs = jobs;
  state.consumableReports = consumableReports;
  state.events = events;
  state.systemSettings = systemSettings;
  state.damagedReturns = damagedReturns;

  renderStats(stats);
  renderUsers();
  renderGroups();
  renderFilters();
  renderObjects();
  renderAdminObjectsTable();
  renderLoans();
  renderReturnLoans();
  renderPickupItems();
  renderMyLoans();
  renderDashboardTips();
  renderJobs();
  renderConsumableReports();
  renderDamagedReturns();
  renderEvents();
  renderSystemSettings();
  showAdminSettingsSection(document.querySelector(".admin-settings-nav-button.active")?.dataset.adminSection || "add-object");
  applyRole();
  updateCheckoutInfo();
  renderReturnLoans();
  renderPickupItems();
  renderMyLoans();
  applyTranslations();
  if (document.querySelector("#statisticsView.active")) {
    renderAllStatisticsCharts(state);
  }

}

// ============================================================
// RENDERING
// Funktioner som skriver ut data till HTML.
// ============================================================

function renderStats(stats) {
  const summary = state.statistics?.summary || stats;
  $("#objectsStat").textContent = summary.objects || 0;
  $("#loanedStat").textContent = summary.loaned || 0;
  $("#overdueStat").textContent = summary.overdue || 0;
  $("#lowStockStat").textContent = summary.low_stock || 0;
  $("#readyPickupStat").textContent = summary.ready_pickup || 0;
  $("#openJobsStat").textContent = summary.jobs || 0;
  updateJobsNavBadge(summary.jobs || 0);
  const warning = $("#statsDataWarning");
  if (warning) {
    const orphanCount = Number(summary.orphan_active_loans || 0);
    warning.hidden = orphanCount <= 0;
    warning.textContent = orphanCount > 0
      ? `Datavarning: ${orphanCount} aktiva lån är kopplade till borttagna jobb. De syns därför i Aktiva lån/statistik men inte på Jobb.`
      : "";
  }
}

function updateJobsNavBadge(count) {
  const badge = $("#jobsNavBadge");
  if (!badge) return;
  badge.textContent = String(count);
  badge.hidden = Number(count) <= 0;
}

function renderSystemSettings() {
  if (!$("#systemSettingsForm")) return;
  const settings = state.systemSettings || {};
  setChecked("#modbusEnabled", settings.modbus_enabled === "1");
  setValue("#modbusHost", settings.modbus_host || "");
  setValue("#modbusPort", settings.modbus_port || "502");
  setValue("#modbusUnitId", settings.modbus_unit_id || "1");
  setValue("#modbusRegisterStart", settings.modbus_register_start || "");
  setChecked("#smtpEnabled", settings.smtp_enabled === "1");
  setValue("#smtpHost", settings.smtp_host || "");
  setValue("#smtpPort", settings.smtp_port || "587");
  setValue("#smtpUsername", settings.smtp_username || "");
  setValue("#smtpPassword", "");
  const smtpPasswordInput = $("#smtpPassword");
  if (smtpPasswordInput) {
    smtpPasswordInput.placeholder = settings.smtp_password_configured
      ? "Lösenord sparat – lämna tomt för att behålla"
      : "Ange SMTP-lösenord";
  }
  setValue("#smtpFromAddress", settings.smtp_from_address || "");
  setChecked("#smtpUseTls", settings.smtp_use_tls !== "0");
  setChecked("#teamsEnabled", settings.teams_enabled === "1");
  setValue("#teamsGroupRecipient", settings.teams_group_recipient || "group.id.a474985@volvo.com");
  setValue("#teamsSubjectPrefix", settings.teams_subject_prefix || "TEAMS");
  setChecked("#notificationSimulationEnabled", settings.notification_simulation_enabled !== "0");
  setValue("#notificationSimulationRecipient", settings.notification_simulation_recipient || "");
  setValue("#loanReminderDays", settings.loan_reminder_days || settings.due_soon_days || "10");
  setChecked("#notifyLoanReminders", settings.notify_loan_reminders !== "0");
  setChecked("#notifyNewJobAutomation", settings.notify_new_job !== "0");
  setChecked("#notifyPickupReady", settings.notify_pickup_ready !== "0");
  setChecked("#notifyReturnedLoan", settings.notify_returned_loan !== "0");
  setChecked("#notifyLowStockAutomation", settings.notify_low_stock !== "0");
  setChecked("#notifyEmptyStock", settings.notify_empty_stock !== "0");
  setChecked("#notifyDueSoon", (settings.notify_due_soon || settings.notify_loan_reminders) !== "0");
  setValue("#dueSoonDays", settings.due_soon_days || settings.loan_reminder_days || "10");
  setChecked("#notifyOverdue", settings.notify_overdue !== "0");
  setChecked("#notifyOverdueRepeat", settings.notify_overdue_repeat !== "0");
  setValue("#overdueRepeatDays", settings.overdue_repeat_days || "3");
  setChecked("#overdueBlockEnabled", settings.overdue_block_enabled === "1");
  setValue("#overdueBlockLimit", settings.overdue_block_limit || "3");
  setValue("#maxLoanDays", settings.max_loan_days || "90");
  updateCheckoutDateLimit();
  setTextValue("#smtpSummary", settings.smtp_enabled === "1" ? "Ja" : "Nej");
  setTextValue("#teamsSummary", settings.teams_enabled === "1" ? "Ja" : "Nej");
  setTextValue("#notificationSimulationSummary", settings.notification_simulation_enabled !== "0" ? "På" : "Av");
  setTextValue("#modbusSummary", settings.modbus_enabled === "1" ? "Ja" : "Nej");
  setTextValue(
    "#borrowBlockSummary",
    settings.overdue_block_enabled === "1" ? `Från ${settings.overdue_block_limit || "3"} sena lån` : "Av"
  );
  messageTemplateFields.forEach(([id, key]) => setValue(`#${id}`, settings[key] || ""));
  renderNotificationRecipients();
}

function setChecked(selector, value) {
  const element = $(selector);
  if (element) element.checked = value;
}

function setValue(selector, value) {
  const element = $(selector);
  if (!element) return;
  if (element.tagName === "SELECT" && value !== "" && !Array.from(element.options).some((option) => option.value === String(value))) {
    const option = document.createElement("option");
    option.value = String(value);
    option.textContent = String(value);
    element.append(option);
  }
  element.value = value;
}

function setTextValue(selector, value) {
  const element = $(selector);
  if (element) element.textContent = value;
}

function populateNumberSelects() {
  document.querySelectorAll("select[data-number-select]").forEach((select) => {
    const min = Number(select.dataset.min || 0);
    const max = Number(select.dataset.max || 100);
    const step = Number(select.dataset.step || 1);
    const defaultValue = select.dataset.default || String(min);
    select.innerHTML = "";
    for (let value = min; value <= max; value += step) {
      const option = document.createElement("option");
      option.value = String(value);
      option.textContent = String(value);
      select.append(option);
    }
    select.value = defaultValue;
  });
}

function splitRecipients(value) {
  return String(value || "")
    .split(/[,\n;]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function normalizeRecipient(value) {
  return String(value || "").trim().toLowerCase();
}

function recipientsForKey(key) {
  return splitRecipients(state.systemSettings?.[key] || "");
}

function setRecipientsForKey(key, recipients) {
  const uniqueRecipients = [];
  const seen = new Set();
  recipients.forEach((recipient) => {
    const normalized = normalizeRecipient(recipient);
    if (!normalized || seen.has(normalized)) return;
    seen.add(normalized);
    uniqueRecipients.push(normalized);
  });
  state.systemSettings[key] = uniqueRecipients.join(", ");
}

function renderNotificationRecipientOptions() {
  const datalist = $("#notificationRecipientOptions");
  if (!datalist) return;
  const values = new Set();
  state.users.forEach((user) => {
    if (user.email) values.add(user.email);
  });
  datalist.innerHTML = [...values].sort().map((email) => `<option value="${escapeHtml(email)}"></option>`).join("");
}

function renderNotificationRecipients() {
  renderNotificationRecipientOptions();
  notificationRecipientKeys.forEach((key) => {
    const container = document.querySelector(`[data-recipient-chips="${key}"]`);
    if (!container) return;
    const recipients = recipientsForKey(key);
    if (!recipients.length) {
      container.innerHTML = `<span class="recipient-empty">Ingen ansvarig vald</span>`;
      return;
    }
    container.innerHTML = recipients.map((recipient) => `
      <span class="recipient-chip">
        ${escapeHtml(recipient)}
        <button type="button" aria-label="Ta bort ${escapeHtml(recipient)}" data-remove-recipient="${key}" data-recipient-value="${escapeHtml(recipient)}">×</button>
      </span>
    `).join("");
  });
}

function addNotificationRecipient(key) {
  const input = document.querySelector(`[data-recipient-input="${key}"]`);
  if (!input) return;
  const additions = splitRecipients(input.value);
  if (!additions.length) return;
  const invalid = additions.find((recipient) => !recipient.includes("@"));
  if (invalid) {
    showToast(`Ogiltig e-postadress: ${invalid}`);
    return;
  }
  setRecipientsForKey(key, recipientsForKey(key).concat(additions));
  input.value = "";
  renderNotificationRecipients();
}

function removeNotificationRecipient(key, recipient) {
  setRecipientsForKey(key, recipientsForKey(key).filter((item) => normalizeRecipient(item) !== normalizeRecipient(recipient)));
  renderNotificationRecipients();
}

function showSystemSettingsSection(section) {
  document.querySelectorAll(".system-settings-nav-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.systemSection === section);
  });
  document.querySelectorAll(".system-settings-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.systemPanel === section);
  });
}

function showAdminSettingsSection(section) {
  if (section === "settings" && state.role !== "superadmin") section = "add-object";
  document.querySelectorAll(".admin-settings-nav-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.adminSection === section);
  });
  document.querySelectorAll(".admin-settings-panel").forEach((panel) => {
    panel.classList.toggle("active", panel.dataset.adminPanel === section);
  });
}

function syncCheckboxPair(sourceSelector, targetSelector) {
  const source = $(sourceSelector);
  const target = $(targetSelector);
  if (!source || !target) return;
  target.checked = source.checked;
}


function renderUsers() {
  renderGroupOptions();
  renderUsersTable();
}

function renderUsersTable() {
  const usersBody = $("#usersBody");
		  if (usersBody) {
		    usersBody.innerHTML = state.users.map((user) => `
		      <tr>
        <td>${userBorrowStatus(user)}</td>
	        <td>${escapeHtml(user.name)}</td>
	        <td>${escapeHtml(user.alias || "")}</td>
	        <td>${escapeHtml(user.rfid_code || "")}</td>
	        <td>${escapeHtml(user.email || "")}</td>
        <td>${escapeHtml(user.phone || "")}</td>
	        <td>${escapeHtml(user.company || "")}</td>
	        <td>${escapeHtml(user.department_name || user.department || "")}</td>
		        <td>${escapeHtml(user.role || "operator")}</td>
	        <td>
	          <button class="table-action-button" type="button" data-edit-user="${escapeHtml(user.user_id)}">Edit</button>
	          <button class="table-action-button" type="button" data-user-card="${escapeHtml(user.user_id)}">Lägg till kort</button>
          ${userBorrowOverrideButton(user)}
	          <button class="danger-button" type="button" data-remove-user="${escapeHtml(user.user_id)}">Remove</button>
	        </td>
		      </tr>
		    `).join("");
    document.querySelectorAll("[data-edit-user]").forEach((button) => {
      button.addEventListener("click", () => startEditUser(button.dataset.editUser));
    });
	    document.querySelectorAll("[data-remove-user]").forEach((button) => {
	      button.addEventListener("click", () => removeUser(button.dataset.removeUser));
	    });
    document.querySelectorAll("[data-toggle-borrow-override]").forEach((button) => {
      button.addEventListener("click", () => toggleBorrowOverride(button.dataset.toggleBorrowOverride, button.dataset.borrowOverride === "1"));
    });
    document.querySelectorAll("[data-user-card]").forEach((button) => {
      button.addEventListener("click", () => openUserCardModal(button.dataset.userCard));
    });
		  }
}

function userBorrowStatus(user) {
  const overdueCount = Number(user.overdue_loan_count || 0);
  const isOverride = Number(user.borrow_override || 0) === 1;
  const isBlocked = Number(user.borrow_blocked || 0) === 1;
  if (isOverride) {
    return `<span class="borrow-status-badge borrow-status-override" title="Manuell tillåtelse aktiv"><span class="borrow-status-icon">!</span><span>Tillåten</span></span>`;
  }
  if (isBlocked) {
    return `<span class="borrow-status-badge borrow-status-blocked" title="Blockerad: ${overdueCount} sena lån"><span class="borrow-status-icon">!</span><span>Spärrad</span></span>`;
  }
  if (overdueCount > 0) {
    return `<span class="borrow-status-badge borrow-status-warning" title="${overdueCount} sena lån"><span class="borrow-status-icon">${overdueCount}</span><span>Sena lån</span></span>`;
  }
  return `<span class="borrow-status-badge borrow-status-ok" title="Får låna"><span class="borrow-status-icon">OK</span></span>`;
}

function userBorrowOverrideButton(user) {
  const isOverride = Number(user.borrow_override || 0) === 1;
  const isBlocked = Number(user.borrow_blocked || 0) === 1;
  if (!isOverride && !isBlocked) return "";
  const enabled = isOverride ? "0" : "1";
  const label = isOverride ? "Ta bort tillåtelse" : "Tillåt lån";
  return `
    <button class="table-action-button" type="button" data-toggle-borrow-override="${escapeHtml(user.user_id)}" data-borrow-override="${enabled}">
      ${label}
    </button>
  `;
}

function renderGroupOptions() {
  ["#newUserDepartmentName", "#quickUserDepartmentName"].forEach((selector) => {
    const select = $(selector);
    if (!select) return;
    const currentValue = select.value;
    select.innerHTML = [
      `<option value="">${state.language === "en" ? "No group" : "Ingen grupp"}</option>`,
      ...state.groups.map((group) => `<option value="${escapeHtml(group.name)}">${escapeHtml(group.department ? `${group.name} - ${group.department}` : group.name)}</option>`),
    ].join("");
    select.value = state.groups.some((group) => group.name === currentValue) ? currentValue : "";
  });
}

function renderGroups() {
  renderGroupOptions();
  const body = $("#groupsBody");
  if (!body) return;
  body.innerHTML = state.groups.map((group) => `
    <tr>
      <td>${escapeHtml(group.name)}</td>
      <td>${escapeHtml(group.department || "")}</td>
      <td>${group.user_count || 0}</td>
      <td class="table-actions-cell">
        <button class="table-action-button" type="button" data-edit-group="${group.group_id}">Edit</button>
        <button class="danger-button" type="button" data-delete-group="${group.group_id}" ${(group.user_count || 0) > 0 ? "disabled" : ""}>Ta bort</button>
      </td>
    </tr>
  `).join("");
  document.querySelectorAll("[data-edit-group]").forEach((button) => {
    button.addEventListener("click", () => startEditGroup(Number(button.dataset.editGroup)));
  });
  document.querySelectorAll("[data-delete-group]").forEach((button) => {
    button.addEventListener("click", () => deleteGroup(Number(button.dataset.deleteGroup)));
  });
}

function startEditGroup(groupId) {
  const group = state.groups.find((item) => item.group_id === groupId);
  if (!group) return;
  state.editingGroupId = groupId;
  $("#newGroupName").value = group.name || "";
  $("#newGroupDepartment").value = group.department || "";
  $("#saveGroupButton").textContent = "Spara ändringar";
  $("#cancelGroupEditButton").style.display = "block";
  showAdminSettingsSection("groups");
}

function resetGroupForm() {
  state.editingGroupId = null;
  $("#groupForm")?.reset();
  if ($("#saveGroupButton")) $("#saveGroupButton").textContent = "Skapa grupp";
  if ($("#cancelGroupEditButton")) $("#cancelGroupEditButton").style.display = "none";
}

function selectedGroupDepartment(selector) {
  const groupName = $(selector)?.value || "";
  const group = state.groups.find((item) => item.name === groupName);
  return group?.department || "";
}

function syncDepartmentFromGroup(groupSelector, departmentSelector) {
  const department = selectedGroupDepartment(groupSelector);
  const departmentInput = $(departmentSelector);
  if (!departmentInput) return;
  departmentInput.value = department;
  departmentInput.readOnly = Boolean(department);
}

function userLabels() {
  const nameCounts = state.users.reduce((counts, user) => {
    counts[user.name] = (counts[user.name] || 0) + 1;
    return counts;
  }, {});
  const nameIndex = {};
  return new Map(state.users.map((user) => {
    nameIndex[user.name] = (nameIndex[user.name] || 0) + 1;
    const suffix = nameCounts[user.name] > 1 ? ` (${nameIndex[user.name]})` : "";
    return [user.user_id, `${user.name}${suffix}`];
  }));
}

function userSearchText(user) {
  return [
    user.user_id,
    user.name,
    user.first_name,
    user.last_name,
    user.email,
    user.phone,
    user.company,
    user.alias,
    user.rfid_code,
    user.department,
    user.department_name,
    user.role,
  ].join(" ").toLowerCase();
}

function renderCheckoutUserSuggestions() {
  const term = $("#checkoutUserSearch").value.trim().toLowerCase();
  const suggestions = $("#checkoutUserSuggestions");
  $("#checkoutUser").value = "";
  renderCheckoutUserDetails();
  if (!term) {
    suggestions.classList.remove("visible");
    suggestions.innerHTML = "";
    return;
  }

  const labels = userLabels();
  const matches = state.users.filter((user) => userSearchText(user).includes(term)).slice(0, 8);
  suggestions.innerHTML = matches.map((user) => `
    <button class="suggestion-button" type="button" data-select-user="${escapeHtml(user.user_id)}">
      <strong>${escapeHtml(labels.get(user.user_id) || user.name)}</strong>
      <span>${escapeHtml([user.company, user.department_name || user.department, user.alias].filter(Boolean).join(" · "))}</span>
    </button>
  `).join("");
  suggestions.classList.toggle("visible", matches.length > 0);
  document.querySelectorAll("[data-select-user]").forEach((button) => {
    button.addEventListener("click", () => selectCheckoutUser(button.dataset.selectUser));
  });
}

function showDashboardMyLoans() {
  setView("myLoans");
  renderMyLoans();
}

function selectCheckoutUser(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  if (!user) return;
  const labels = userLabels();
  $("#checkoutUser").value = user.user_id;
  $("#checkoutUserSearch").value = labels.get(user.user_id) || user.name;
  $("#checkoutUserSuggestions").classList.remove("visible");
  renderCheckoutUserDetails(user);
}

function resolveCheckoutUserId() {
  const selectedUserId = $("#checkoutUser").value;
  if (selectedUserId) return selectedUserId;
  const term = $("#checkoutUserSearch").value.trim().toLowerCase();
  const exact = state.users.find((user) => {
    const label = userLabels().get(user.user_id)?.toLowerCase();
    return label === term || user.user_id.toLowerCase() === term || user.email?.toLowerCase() === term || user.alias?.toLowerCase() === term;
  });
  return exact ? exact.user_id : "";
}

function resolveUserSearchTerm(selector) {
  const term = $(selector)?.value.trim().toLowerCase() || "";
  if (!term) return "";
  const labels = userLabels();
  const exact = state.users.find((user) => {
    const label = labels.get(user.user_id)?.toLowerCase();
    return label === term || user.name.toLowerCase() === term || user.user_id.toLowerCase() === term || user.email?.toLowerCase() === term || user.alias?.toLowerCase() === term;
  });
  if (exact) return exact.user_id;

  const matches = state.users.filter((user) => userSearchText(user).includes(term));
  return matches.length === 1 ? matches[0].user_id : "";
}

function renderCheckoutUserDetails(user = null) {
  const details = $("#checkoutUserDetails");
  if (!details) return;
  const selectedUser = user || state.users.find((item) => item.user_id === $("#checkoutUser").value);
  if (!selectedUser) {
    ["Company", "Group", "Department", "Email", "Phone", "Alias"].forEach((field) => {
      const input = $(`#checkoutUser${field}`);
      if (input) input.value = "";
    });
    return;
  }

  $("#checkoutUserCompany").value = selectedUser.company || "";
  $("#checkoutUserGroup").value = selectedUser.department_name || "";
  $("#checkoutUserDepartment").value = selectedUser.department || "";
  $("#checkoutUserEmail").value = selectedUser.email || "";
  $("#checkoutUserPhone").value = selectedUser.phone || "";
  $("#checkoutUserAlias").value = selectedUser.alias || "";
}

function renderFilters() {
  fillSelect("#categoryFilter", ["Alla", ...unique(state.objects.map((item) => item.category))]);
  fillSelect("#statusFilter", ["Alla", ...unique(state.objects.map((item) => item.status))]);
}

function fillSelect(selector, values) {
  const select = $(selector);
  const current = select.value;
  select.innerHTML = values.map((value) => {
    const label = value === "Alla" ? t("search.all") : statusText(value);
    return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
  }).join("");
  if (values.includes(current)) select.value = current;
}

function renderObjects() {
  const search = $("#objectSearch").value.trim().toLowerCase();
  const category = $("#categoryFilter").value || "Alla";
  const status = $("#statusFilter").value || "Alla";
  const filtered = state.objects.filter((item) => {
    const searchable = [
      item.object_id,
      item.category,
      item.item_type,
      item.description,
      item.article_number,
      item.name,
      item.supplier_article_number,
      item.location,
      item.storage_location_2,
      item.tornado_id,
      item.door_id,
      item.belongs_to_instrument,
      item.device,
      item.belongs_to,
      item.search_words,
      item.tray_for,
      item.lift_tray,
    ].join(" ").toLowerCase();
    return (!search || searchable.includes(search)) &&
      (category === "Alla" || item.category === category) &&
      (status === "Alla" || item.status === status);
  });

  $("#objectsBody").innerHTML = filtered.slice(0, TABLE_RENDER_LIMIT).map((item) => `
    <tr class="${item.available_quantity <= item.min_quantity ? "low" : ""}">
      <td>${objectThumbnail(item)}</td>
      <td>${escapeHtml(item.category)}</td>
      <td>${escapeHtml(item.item_type || "")}</td>
      <td>${escapeHtml(item.description || "")}</td>
      <td>${escapeHtml(item.article_number || "")}</td>
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.supplier_article_number || "")}</td>
      <td>${item.available_quantity} / ${item.total_quantity}${item.quarantined_quantity ? `<small class="request-reference">${t("damage.quarantined")}: ${item.quarantined_quantity}</small>` : ""}</td>
      <td>${item.min_quantity}</td>
      <td>${escapeHtml(item.location)}</td>
      <td>${escapeHtml(item.tornado_id)}</td>
      <td>${escapeHtml(item.belongs_to_instrument || "")}</td>
      <td>${escapeHtml(item.device || "")}</td>
      <td>${escapeHtml(item.belongs_to || "")}</td>
      <td>${escapeHtml(item.last_changed || "")}</td>
      <td>${escapeHtml(item.search_words || "")}</td>
      <td>${escapeHtml(item.tray_for || "")}</td>
      <td>${escapeHtml(item.storage_location_2 || "")}</td>
      <td>${escapeHtml(item.lift_tray || item.door_id || "")}</td>
      <td>${statusBadge(item.status)}</td>
      <td class="admin-only">
        <button class="table-action-button" type="button" data-edit-object="${escapeHtml(item.object_id)}">Redigera</button>
        <button class="danger-button" type="button" data-delete-object="${escapeHtml(item.object_id)}">Ta bort</button>
      </td>
    </tr>
  `).join("");

  document.querySelectorAll("[data-edit-object]").forEach((button) => {
    button.addEventListener("click", () => startEditObject(button.dataset.editObject));
  });
  document.querySelectorAll("[data-delete-object]").forEach((button) => {
    button.addEventListener("click", () => deleteObject(button.dataset.deleteObject));
  });
  applyRole();
}

function renderAdminObjectsTable() {
  const body = $("#adminObjectsBody");
  if (!body) return;
  body.innerHTML = state.objects.slice(0, TABLE_RENDER_LIMIT).map((item) => `
    <tr class="${item.available_quantity <= item.min_quantity ? "low" : ""}">
      <td>${escapeHtml(item.object_id)}</td>
      <td>${escapeHtml(item.name)}</td>
      <td>${escapeHtml(item.category)}</td>
      <td>${item.available_quantity} / ${item.total_quantity}${item.quarantined_quantity ? `<small class="request-reference">${t("damage.quarantined")}: ${item.quarantined_quantity}</small>` : ""}</td>
      <td>${statusBadge(item.status)}</td>
      <td>
        <button class="table-action-button" type="button" data-admin-edit-object="${escapeHtml(item.object_id)}">Redigera</button>
        <button class="danger-button" type="button" data-admin-delete-object="${escapeHtml(item.object_id)}">Ta bort</button>
      </td>
    </tr>
  `).join("");

  document.querySelectorAll("[data-admin-edit-object]").forEach((button) => {
    button.addEventListener("click", () => startEditObject(button.dataset.adminEditObject));
  });
  document.querySelectorAll("[data-admin-delete-object]").forEach((button) => {
    button.addEventListener("click", () => deleteObject(button.dataset.adminDeleteObject));
  });
}

function objectSearchText(item) {
  return [
    item.object_id,
    item.name,
    item.category,
    item.item_type,
    item.description,
    item.article_number,
    item.supplier_article_number,
    item.location,
    item.storage_location_2,
    item.tornado_id,
    item.door_id,
    item.search_words,
    item.lift_tray,
  ].join(" ").toLowerCase();
}

function isConsumableObject(item) {
  if (item.is_consumable === 1 || item.is_consumable === "1" || item.is_consumable === true) return true;
  const text = [
    item.category,
    item.item_type,
    item.description,
    item.search_words,
    item.name,
  ].join(" ").toLowerCase();
  return text.includes("förbruk") || text.includes("forbruk") || text.includes("consumable");
}

function matchesCheckoutStockFilter(item) {
  return item.available_quantity > 0;
}

function renderCheckoutObjectSuggestions() {
  const term = $("#checkoutObjectId").value.trim().toLowerCase();
  const suggestions = $("#checkoutObjectSuggestions");
  if (!term) {
    suggestions.classList.remove("visible");
    suggestions.innerHTML = "";
    return;
  }

  const allMatches = state.objects
    .filter((item) => !isConsumableObject(item) && objectSearchText(item).includes(term))
    .sort((a, b) => b.available_quantity - a.available_quantity || a.name.localeCompare(b.name));
  const filteredMatches = allMatches.filter(matchesCheckoutStockFilter);
  const matches = filteredMatches.slice(0, 8);
  suggestions.innerHTML = matches.map((item) => `
    <button class="suggestion-button" type="button" data-select-object="${escapeHtml(item.object_id)}">
      <strong>${escapeHtml(item.name)} (${escapeHtml(item.article_number || item.object_id)})</strong>
      <span>${escapeHtml([t("stock.count", { count: item.available_quantity }), item.category, item.location, item.supplier_article_number].filter(Boolean).join(" · "))}</span>
    </button>
  `).join("");
  suggestions.classList.toggle("visible", matches.length > 0);
  document.querySelectorAll("[data-select-object]").forEach((button) => {
    button.addEventListener("click", () => selectCheckoutObject(button.dataset.selectObject));
  });
}

function selectCheckoutObject(objectId) {
  const item = state.objects.find((objectItem) => objectItem.object_id === objectId);
  $("#checkoutObjectId").value = item?.name || objectId;
  $("#checkoutObjectSuggestions").classList.remove("visible");
  updateCheckoutInfo(item);
}

function renderConsumableObjectSuggestions() {
  const term = $("#consumableObjectSearch")?.value.trim().toLowerCase();
  const suggestions = $("#consumableObjectSuggestions");
  if (!suggestions) return;
  $("#consumableObjectId").value = "";
  if (!term) {
    suggestions.classList.remove("visible");
    suggestions.innerHTML = "";
    return;
  }
  const matches = state.objects.filter((item) => isConsumableObject(item) && objectSearchText(item).includes(term)).slice(0, 8);
  suggestions.innerHTML = matches.map((item) => `
    <button class="suggestion-button" type="button" data-select-consumable="${escapeHtml(item.object_id)}">
      <strong>${escapeHtml(item.name)}</strong>
      <span>${escapeHtml([item.object_id, item.article_number, item.location].filter(Boolean).join(" · "))}</span>
    </button>
  `).join("");
  suggestions.classList.toggle("visible", matches.length > 0);
  document.querySelectorAll("[data-select-consumable]").forEach((button) => {
    button.addEventListener("click", () => selectConsumableObject(button.dataset.selectConsumable));
  });
}

function selectConsumableObject(objectId) {
  const item = state.objects.find((objectItem) => objectItem.object_id === objectId);
  $("#consumableObjectId").value = objectId;
  $("#consumableObjectSearch").value = item?.name || objectId;
  $("#consumableObjectSuggestions").classList.remove("visible");
}

function renderLoans() {
  const term = $("#loanSearch")?.value.trim().toLowerCase() || "";
  const statusFilter = $("#loanStatusFilter")?.value || "all";
  const filtered = state.loans.filter((loan) => {
    const status = loan.overdue ? "overdue" : "active";
    const searchable = [
      loan.loan_id,
      loan.object_id,
      loan.object_name,
      loan.user_name,
      loan.user_department,
      loan.engine_id,
      loan.project_number,
      loan.remaining_quantity ?? loan.quantity,
      formatTime(loan.checkout_time),
      formatTime(loan.due_time),
      formatTime(loan.last_reminder_sent_at),
      loan.overdue ? "sen overdue" : "aktiv active",
    ].join(" ").toLowerCase();
    return (!term || searchable.includes(term)) &&
      (statusFilter === "all" || statusFilter === status);
  });

  $("#loansBody").innerHTML = filtered.map((loan) => `
	    <tr class="${loan.overdue ? "late" : ""}">
	      <td>${loan.loan_id}</td>
      <td>${escapeHtml(loan.object_id)}</td>
      <td>${escapeHtml(loan.object_name)} (${escapeHtml(loan.object_id)})</td>
      <td>${escapeHtml(loan.user_name)}</td>
      <td>${escapeHtml(loan.user_department || "")}</td>
      <td>${escapeHtml(loan.engine_id || "")}</td>
      <td>${escapeHtml(loan.project_number || "")}</td>
      <td>${loan.remaining_quantity ?? loan.quantity}</td>
      <td>${formatTime(loan.checkout_time)}</td>
      <td>${formatTime(loan.due_time)}</td>
      <td>${statusBadge(loan.overdue ? "Sen" : "Aktiv")}</td>
      <td>${loan.last_reminder_sent_at ? formatTime(loan.last_reminder_sent_at) : "-"}</td>
      <td>
        <button class="table-action-button table-reminder-button" type="button" data-send-loan-reminder="${loan.loan_id}" ${loan.user_email ? "" : "disabled"}>
          ${t("action.sendReminder")}
        </button>
      </td>
      <td><button class="link-button" type="button" data-print-loan="${loan.loan_id}">${t("action.print")}</button></td>
    </tr>
  `).join("");
  document.querySelectorAll("[data-send-loan-reminder]").forEach((button) => {
    button.addEventListener("click", () => sendLoanReminder(Number(button.dataset.sendLoanReminder), button));
  });
  document.querySelectorAll("[data-print-loan]").forEach((button) => {
    button.addEventListener("click", () => printLoanReceipt(Number(button.dataset.printLoan)));
  });
}

function dashboardTips() {
  if (state.language === "en") {
    return [
      {
        title: "Borrow an item",
        text: "Press Borrow, choose yourself, search for the item and send the loan request with quantity and return date.",
      },
      {
        title: "Pick up an item",
        text: "Press Pick up item when your request is ready. Search for your name and mark the prepared item as collected.",
      },
      {
        title: "Return an item",
        text: "Press Return, search for your name and return the active loan from the list.",
      },
      {
        title: "Find your loans",
        text: "Use My loans to see your active loans in one place. Search for your name to quickly find what you have borrowed and when it should be returned.",
      },
      {
        title: "Consumable",
        text: "Use Consumable when a consumable article needs refilling.",
      },
    ];
  }
  return [
    {
      title: "Låna ett objekt",
      text: "Tryck på Låna, välj dig själv, sök fram objektet och skicka låneförfrågan med antal och returdatum.",
    },
    {
      title: "Hämta artikel",
      text: "Tryck på Hämta artikel när din förfrågan är förberedd. Sök på ditt namn och markera artikeln som hämtad.",
    },
    {
      title: "Lämna tillbaka",
      text: "Tryck på Lämna tillbaka, sök på ditt namn och återlämna rätt aktivt lån i listan.",
    },
    {
      title: "Mina utlåningar",
      text: "Här ser du dina aktiva lån samlade på ett ställe. Sök på ditt namn för att snabbt hitta vad du har lånat och när det ska lämnas tillbaka.",
    },
    {
      title: "Förbrukningsvara",
      text: "Använd Förbrukningsvara när en förbrukningsvara behöver fyllas på.",
    },
  ];
}

function renderDashboardTips() {
  const slide = $("#dashboardTipsSlide");
  const dots = $("#dashboardTipsDots");
  if (!slide || !dots) return;
  const tips = dashboardTips();
  const index = state.dashboardTipIndex % tips.length;
  const tip = tips[index];
  slide.innerHTML = `
    <strong>${escapeHtml(tip.title)}</strong>
    <p>${escapeHtml(tip.text)}</p>
  `;
  dots.innerHTML = tips.map((_, tipIndex) => `
    <button class="dashboard-tips-dot ${tipIndex === index ? "active" : ""}" type="button" data-dashboard-tip="${tipIndex}" aria-label="Visa tips ${tipIndex + 1}"></button>
  `).join("");
  dots.querySelectorAll("[data-dashboard-tip]").forEach((button) => {
    button.addEventListener("click", () => {
      state.dashboardTipIndex = Number(button.dataset.dashboardTip);
      renderDashboardTips();
    });
  });
}

function stepDashboardTip(direction) {
  const tips = dashboardTips();
  state.dashboardTipIndex = (state.dashboardTipIndex + direction + tips.length) % tips.length;
  renderDashboardTips();
}

function nextJobAction(status) {
  const transitions = {
    requested: ["approved", "jobs.nextApproved"],
    approved: ["prepared", "jobs.nextPrepared"],
    prepared: ["loaned", "jobs.nextLoaned"],
    loaned: ["returned", "jobs.nextReturned"],
    returned: ["stocked", "jobs.nextStocked"],
  };
  return transitions[status] || null;
}

function renderJobs() {
  const jobsBoard = $("#jobsBoard");
  if (!jobsBoard) return;
  jobsBoard.classList.toggle("jobs-collapsed", state.jobsCollapsed);
  const filteredJobs = getFilteredJobs();
  const visibleGroupIds = [...new Set(filteredJobs.map((job) => Number(job.request_group_id || job.request_id)))];
  const groups = visibleGroupIds.map((groupId) => groupLoanRequestRows(
    state.jobs.filter((job) => Number(job.request_group_id || job.request_id) === groupId)
  )[0]);
  const columns = [
    { status: "requested", tone: "yellow" },
    { status: "approved", tone: "blue" },
    { status: "prepared", tone: "green" },
    { status: "loaned", tone: "blue" },
    { status: "returned", tone: "yellow" },
    { status: "stocked", tone: "gray" },
  ];
  jobsBoard.innerHTML = columns.map((column) => {
    const columnGroups = groups.filter((group) => group.status === column.status);
    return `
      <section class="job-column job-column-${column.tone}">
        <header class="job-column-header">
          <h2>${escapeHtml(jobStatusText(column.status))}</h2>
          <span>${columnGroups.length}</span>
        </header>
        <div class="job-column-list" data-job-drop-status="${column.status}">
          ${columnGroups.length ? columnGroups.map(renderJobGroup).join("") : `<div class="job-empty">${escapeHtml(t("jobs.empty"))}</div>`}
        </div>
      </section>
    `;
  }).join("");
  document.querySelectorAll("[data-job-group-id]").forEach((button) => {
    button.addEventListener("click", () => updateJobGroupStatus(Number(button.dataset.jobGroupId), button.dataset.jobStatus));
  });
  document.querySelectorAll("[data-job-id]").forEach((button) => {
    button.addEventListener("click", () => updateJobStatus(Number(button.dataset.jobId), button.dataset.jobStatus));
  });
  document.querySelectorAll("[data-delete-job]").forEach((button) => {
    button.addEventListener("click", () => deleteJob(Number(button.dataset.deleteJob)));
  });
  document.querySelectorAll("[data-pickup-email]").forEach((button) => {
    button.addEventListener("click", () => sendPickupReadyEmail(Number(button.dataset.pickupEmail), button));
  });
  document.querySelectorAll("[data-open-job-id]").forEach((button) => {
    button.addEventListener("click", () => openJobDetail(Number(button.dataset.openJobId)));
  });
  bindJobDragAndDrop();
}

function updateJobsCollapseButton() {
  const button = $("#toggleJobsCollapsed");
  if (!button) return;
  button.textContent = t(state.jobsCollapsed ? "jobs.expandAll" : "jobs.collapseAll");
  button.setAttribute("aria-pressed", String(state.jobsCollapsed));
}

function toggleJobsCollapsed() {
  state.jobsCollapsed = !state.jobsCollapsed;
  localStorage.setItem("jobsCollapsed", state.jobsCollapsed ? "1" : "0");
  updateJobsCollapseButton();
  renderJobs();
}

function getFilteredJobs() {
  const term = $("#jobSearch")?.value.trim().toLowerCase() || "";
  const dateSort = $("#jobDateSort")?.value || "updated_desc";
  const filtered = state.jobs.filter((job) => {
    const searchable = [
      job.request_id,
      job.request_group_id,
      job.object_id,
      job.object_name,
      job.user_name,
      job.user_department,
      job.engine_id,
      job.project_number,
      job.lending_date,
      job.return_date,
      job.created_at,
      job.updated_at,
      jobStatusText(job.status),
    ].join(" ").toLowerCase();
    return !term || searchable.includes(term);
  });
  return filtered.sort((a, b) => {
    if (dateSort === "lending_asc") return String(a.lending_date || "").localeCompare(String(b.lending_date || ""));
    if (dateSort === "return_asc") return String(a.return_date || "").localeCompare(String(b.return_date || ""));
    if (dateSort === "created_desc") return String(b.created_at || "").localeCompare(String(a.created_at || ""));
    return String(b.updated_at || "").localeCompare(String(a.updated_at || ""));
  });
}

function renderConsumableReports() {
  const list = $("#consumableReportsList");
  if (!list) return;
  if (!state.consumableReports.length) {
    list.innerHTML = `<div class="job-empty">${state.language === "en" ? "No open reports." : "Inga öppna rapporter."}</div>`;
    return;
  }
  list.innerHTML = state.consumableReports.map((report) => `
    <article class="consumable-report-card">
      <div>
        <strong>${escapeHtml(report.object_name)}</strong>
        <span>${escapeHtml(report.object_id)}${report.article_number ? ` · ${escapeHtml(report.article_number)}` : ""}</span>
      </div>
      <dl>
        <dt>${escapeHtml(t("table.storage"))}</dt><dd>${escapeHtml(report.location || "")}</dd>
        <dt>${escapeHtml(t("table.store"))}</dt><dd>${escapeHtml(report.tornado_id || "")}</dd>
      </dl>
      <button class="table-action-button" type="button" data-close-consumable="${report.report_id}">${state.language === "en" ? "Mark handled" : "Markera åtgärdad"}</button>
    </article>
  `).join("");
  document.querySelectorAll("[data-close-consumable]").forEach((button) => {
    button.addEventListener("click", () => closeConsumableReport(Number(button.dataset.closeConsumable)));
  });
}

function renderJobGroup(group) {
  const first = group.items[0];
  const action = nextJobAction(group.status);
  const pickupEmailSent = group.items.every((job) => Boolean(job.pickup_ready_email_sent_at));
  const allPrepared = group.items.every((job) => job.status === "prepared");
  const pickupEmailButton = allPrepared
    ? `<button class="job-pickup-email-button ${pickupEmailSent ? "is-muted" : ""}" type="button" data-pickup-email="${group.id}" ${pickupEmailSent ? "disabled" : ""} title="${pickupEmailSent ? (state.language === "en" ? "Pickup email sent" : "Hämtningsmail skickat") : (state.language === "en" ? "Send pickup email for all articles" : "Skicka hämtningsmail för alla artiklar")}" aria-label="${pickupEmailSent ? (state.language === "en" ? "Pickup email sent" : "Hämtningsmail skickat") : (state.language === "en" ? "Send pickup email for all articles" : "Skicka hämtningsmail för alla artiklar")}">
        <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path d="M22 2 11 13"></path>
          <path d="m22 2-7 20-4-9-9-4Z"></path>
        </svg>
      </button>` : "";
  const statusCounts = JOB_REQUEST_STATUS_ORDER
    .map((status) => [status, group.items.filter((job) => job.status === status).length])
    .filter(([, count]) => count)
    .map(([status, count]) => `${count} ${escapeHtml(jobStatusText(status)).toLowerCase()}`)
    .join(" · ");
  return `
    <article class="request-group" draggable="true" data-drag-group-id="${group.id}" data-drag-job-status="${group.status}">
      <div class="job-card-top">
        <strong>${state.language === "en" ? "Request" : "Förfrågan"} #${group.id}</strong>
        <span class="job-card-top-right">${pickupEmailButton}<span>${group.items.length} ${state.language === "en" ? "articles" : "artiklar"}</span></span>
      </div>
      <h3>${escapeHtml(first.user_name)}</h3>
      <div class="job-card-summary">
        <span>${escapeHtml(first.user_department || "")}</span>
        <span>${escapeHtml(t("field.lendingDate"))}: ${escapeHtml(first.lending_date || "")}</span>
        <span>${escapeHtml(t("field.returnDate"))}: ${escapeHtml(first.return_date || "")}</span>
        ${group.partial ? `<strong class="job-partial-status">${state.language === "en" ? "Mixed status" : "Delvis klar"}: ${statusCounts}</strong>` : ""}
      </div>
      <details class="job-card-details">
        <summary>${state.language === "en" ? "Show articles" : "Visa artiklar"}</summary>
        <div class="job-group-items">${group.items.map(renderJobGroupItem).join("")}</div>
      </details>
      <div class="job-card-actions">
        ${action ? `<button class="primary-button" type="button" data-job-group-id="${group.id}" data-job-status="${action[0]}">${escapeHtml(t(action[1]))}</button>` : ""}
      </div>
    </article>
  `;
}

function renderJobGroupItem(job) {
  const action = nextJobAction(job.status);
  return `
    <div class="job-group-item">
      <div>
        <strong>${escapeHtml(job.object_name)}</strong>
        <span>${escapeHtml(job.object_id)} · ${job.quantity} st · ${escapeHtml(jobStatusText(job.status))}</span>
      </div>
      <div class="job-group-item-actions">
        <button class="secondary-button" type="button" data-open-job-id="${job.request_id}">${state.language === "en" ? "Details" : "Detaljer"}</button>
        ${action ? `<button class="table-action-button" type="button" data-job-id="${job.request_id}" data-job-status="${action[0]}">${escapeHtml(jobStatusText(action[0]))}</button>` : ""}
        <button class="danger-button" type="button" data-delete-job="${job.request_id}">${state.language === "en" ? "Remove" : "Ta bort"}</button>
      </div>
    </div>
  `;
}

function jobDetailRows(job) {
  return [
    [t("table.jobId"), job.request_id],
    [t("field.status"), jobStatusText(job.status)],
    [t("field.instrumentId"), job.object_id],
    [t("table.object"), job.object_name],
    [t("table.borrower"), job.user_name],
    [t("table.deptNo"), job.user_department || ""],
    [t("table.storage"), job.object_location || ""],
    [t("table.store"), job.object_store || ""],
    [t("field.engineId"), job.engine_id || ""],
    [t("table.projectNo"), job.project_number || ""],
    [t("field.quantity"), job.quantity],
    [t("field.lendingDate"), job.lending_date],
    [t("field.returnDate"), job.return_date],
  ];
}

function openJobDetail(requestId) {
  const job = state.jobs.find((item) => item.request_id === requestId);
  if (!job) return;
  state.selectedJobId = requestId;
  $("#jobDetailTitle").textContent = `#${job.request_id} ${job.object_name}`;
  renderJobDetailView(job);
  $("#jobDetailModal").classList.add("open");
  $("#jobDetailModal").setAttribute("aria-hidden", "false");
}

function renderJobDetailView(job) {
  $("#editJobButton").hidden = job.status === "returned" || job.status === "stocked";
  $("#editJobButton").textContent = state.language === "en" ? "Edit" : "Ändra";
  $("#jobDetailContent").innerHTML = `
    <dl class="job-detail-grid">
      ${jobDetailRows(job).map(([label, value]) => `
        <dt>${escapeHtml(label)}</dt>
        <dd>${escapeHtml(String(value ?? ""))}</dd>
      `).join("")}
    </dl>
  `;
}

function renderJobEditForm() {
  const job = selectedJob();
  if (!job) return;
  const hasActiveLoan = job.status === "loaned";
  $("#editJobButton").textContent = state.language === "en" ? "Cancel" : "Avbryt";
  $("#jobDetailContent").innerHTML = `
    <form class="job-edit-form" id="jobEditForm">
      <label>
        ${escapeHtml(t("field.engineId"))}
        <input id="editJobEngineId" value="${escapeHtml(job.engine_id || "")}" autocomplete="off">
      </label>
      <label>
        ${escapeHtml(t("table.projectNo"))}
        <input id="editJobProjectNumber" value="${escapeHtml(job.project_number || "")}" autocomplete="off">
      </label>
      <label>
        ${escapeHtml(t("field.quantity"))}
        <input id="editJobQuantity" type="number" min="1" step="1" value="${job.quantity}" ${hasActiveLoan ? "disabled" : ""}>
      </label>
      <label>
        ${escapeHtml(t("field.lendingDate"))}
        <input id="editJobLendingDate" type="date" value="${escapeHtml(String(job.lending_date || "").slice(0, 10))}" ${hasActiveLoan ? "disabled" : ""}>
      </label>
      <label>
        ${escapeHtml(t("field.returnDate"))}
        <input id="editJobReturnDate" type="date" value="${escapeHtml(String(job.return_date || "").slice(0, 10))}">
      </label>
      <div class="form-actions">
        <button class="primary-button" type="submit">${state.language === "en" ? "Save changes" : "Spara ändringar"}</button>
      </div>
    </form>
  `;
  $("#jobEditForm").addEventListener("submit", saveJobDetails);
}

function closeJobDetail() {
  $("#jobDetailModal").classList.remove("open");
  $("#jobDetailModal").setAttribute("aria-hidden", "true");
  state.selectedJobId = null;
}

function toggleJobEdit() {
  const job = selectedJob();
  if (!job) return;
  if ($("#jobEditForm")) {
    renderJobDetailView(job);
  } else {
    renderJobEditForm();
  }
}

function selectedJob() {
  return state.jobs.find((job) => job.request_id === state.selectedJobId) || null;
}

function printSelectedJob() {
  const job = selectedJob();
  if (!job) return;
  const receipt = $("#printReceipt");
  receipt.innerHTML = `
    <div class="receipt-page">
      <header class="receipt-header">
        <div>
          <h1>${escapeHtml(t("nav.jobs"))}</h1>
          <p>${escapeHtml(jobStatusText(job.status))}</p>
        </div>
        <div class="receipt-id">Job #${job.request_id}</div>
      </header>
      <dl class="receipt-grid">
        ${jobDetailRows(job).map(([label, value]) => `
          <dt>${escapeHtml(label)}</dt>
          <dd>${escapeHtml(String(value ?? ""))}</dd>
        `).join("")}
      </dl>
    </div>
  `;
  window.print();
}

function exportSelectedJobCsv() {
  const job = selectedJob();
  if (!job) return;
  const rows = jobDetailRows(job);
  const csv = [
    ["Field", "Value"],
    ...rows,
  ].map((row) => row.map(csvCell).join(";")).join("\r\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `job-${job.request_id}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportObjectsCsv() {
  const rows = [
    ["Objekt-ID", "Namn", "Kategori", "Typ", "Beteckning", "VOLVO-ID", "Leverantörsartikel", "Totalt antal", "Tillgängligt antal", "Min-nivå", "Plats", "Lagerplats 2", "Förråd", "Dörr/fack", "Tillhör instrument", "Device", "Tillhör", "Sökord", "Hissbricka", "Status"],
    ...state.objects.map((item) => [
      item.object_id,
      item.name,
      item.category,
      item.item_type || "",
      item.description || "",
      item.article_number || "",
      item.supplier_article_number || "",
      item.total_quantity,
      item.available_quantity,
      item.min_quantity,
      item.location,
      item.storage_location_2 || "",
      item.tornado_id,
      item.door_id || "",
      item.belongs_to_instrument || "",
      item.device || "",
      item.belongs_to || "",
      item.search_words || "",
      item.lift_tray || "",
      item.status,
    ]),
  ];
  const csv = rows.map((row) => row.map(csvCell).join(";")).join("\r\n");
  const blob = new Blob([`\ufeff${csv}`], { type: "application/vnd.ms-excel;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "objektlista.xls";
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportVisibleObjectsCsv() {
  exportObjectsCsv();
}

function csvCell(value) {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

function bindJobDragAndDrop() {
  let draggedCard = null;
  const placeholder = document.createElement("div");
  placeholder.className = "job-drop-placeholder";

  document.querySelectorAll("[data-drag-group-id]").forEach((card) => {
    card.addEventListener("dragstart", (event) => {
      draggedCard = card;
      card.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", card.dataset.dragGroupId);
    });
    card.addEventListener("dragend", () => {
      card.classList.remove("dragging");
      placeholder.remove();
      draggedCard = null;
    });
  });

  document.querySelectorAll("[data-job-drop-status]").forEach((zone) => {
    zone.addEventListener("dragover", (event) => {
      event.preventDefault();
      zone.classList.add("drag-over");
      event.dataTransfer.dropEffect = "move";
      const afterElement = getDragAfterElement(zone, event.clientY);
      if (afterElement == null) {
        zone.appendChild(placeholder);
      } else {
        zone.insertBefore(placeholder, afterElement);
      }
    });
    zone.addEventListener("dragleave", (event) => {
      if (!zone.contains(event.relatedTarget)) {
        zone.classList.remove("drag-over");
      }
    });
    zone.addEventListener("drop", (event) => {
      event.preventDefault();
      zone.classList.remove("drag-over");
      const requestGroupId = Number(event.dataTransfer.getData("text/plain"));
      const status = zone.dataset.jobDropStatus;
      const group = groupLoanRequestRows(state.jobs.filter(
        (item) => Number(item.request_group_id || item.request_id) === requestGroupId
      ))[0];
      if (!group) return;
      if (draggedCard && placeholder.parentElement === zone) {
        zone.insertBefore(draggedCard, placeholder);
      }
      placeholder.remove();
      if (group.status === status) return;
      updateJobGroupStatus(requestGroupId, status);
    });
  });
}

function getDragAfterElement(container, y) {
  const draggableElements = [...container.querySelectorAll(".request-group:not(.dragging)")];
  return draggableElements.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) {
      return { offset, element: child };
    }
    return closest;
  }, { offset: Number.NEGATIVE_INFINITY, element: null }).element;
}

function renderEvents() {
  const rows = state.events.map((event) => `
    <tr>
      <td>${formatTime(event.event_time)}</td>
      <td>${escapeHtml(event.event_type)}</td>
      <td>${escapeHtml(event.message)}</td>
    </tr>
  `).join("");
  $("#eventsBody").innerHTML = rows;
}

// ============================================================
// ROLLER OCH BEHORIGHET
// Visar/doljer vyer och adminfunktioner beroende pa vald roll.
// ============================================================

function applyRole() {
  const settingsButton = document.querySelector('[data-admin-section="settings"]');
  if (settingsButton) settingsButton.hidden = state.role !== "superadmin";
  ["#openQuickUserButton", "#openUserScanButton"].forEach((selector) => {
    const button = document.querySelector(selector);
    if (button) button.hidden = state.role === "operator";
  });
  document.querySelectorAll(".nav-button").forEach((button) => {
    const roles = button.dataset.roles.split(",");
    button.hidden = !roles.includes(state.role);
  });
  document.querySelectorAll(".admin-only").forEach((element) => {
    element.hidden = state.role === "operator";
  });
  const currentView = document.querySelector(".view.active")?.id.replace("View", "");
  if (currentView && !canSeeView(currentView)) {
    setView("dashboard");
  }
}

function canSeeView(view) {
  const button = document.querySelector(`.nav-button[data-view="${view}"]`);
  if (!button) return true;
  return button.dataset.roles.split(",").includes(state.role);
}

// ============================================================
// OBJEKTFORMULAR OCH BILDER
// Hanterar redigering, aterstallning och forhandsvisning.
// ============================================================

function resetObjectForm() {
  state.editingObjectId = null;
  $("#addObjectForm").reset();
  $("#objectFormTitle").textContent = "Lägg till objekt";
  $("#saveObjectButton").textContent = "Spara objekt";
  $("#cancelObjectEditButton").style.display = "none";
  $("#newObjectId").readOnly = false;
  $("#newObjectTotal").value = "1";
  $("#newObjectAvailable").value = "1";
  $("#newObjectMin").value = "1";
  $("#newObjectConsumable").checked = false;
  $("#removeObjectImage").checked = false;
  clearImagePreview();
}

function objectThumbnail(item) {
  const imageData = objectDisplayImage(item);
  if (imageData) {
    return `<img class="object-thumb" src="${escapeHtml(imageData)}" alt="">`;
  }
  const label = String(item.category || "Objekt").slice(0, 3).toUpperCase();
  return `<span class="object-thumb-placeholder">${escapeHtml(label)}</span>`;
}

function readSelectedObjectImage() {
  const file = $("#newObjectImage").files[0];
  if (!file) return Promise.resolve("");
  if (!file.type.startsWith("image/")) {
    return Promise.reject(new Error("Välj en bildfil."));
  }
  return resizeObjectImage(file);
}

function resizeObjectImage(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const image = new Image();
      image.onload = () => {
        const maxSide = 900;
        const scale = Math.min(1, maxSide / Math.max(image.width, image.height));
        const width = Math.max(1, Math.round(image.width * scale));
        const height = Math.max(1, Math.round(image.height * scale));
        const canvas = document.createElement("canvas");
        canvas.width = width;
        canvas.height = height;
        const context = canvas.getContext("2d");
        context.fillStyle = "#ffffff";
        context.fillRect(0, 0, width, height);
        context.drawImage(image, 0, 0, width, height);

        let quality = 0.82;
        let dataUrl = canvas.toDataURL("image/jpeg", quality);
        while (dataUrl.length > 700_000 && quality > 0.45) {
          quality -= 0.08;
          dataUrl = canvas.toDataURL("image/jpeg", quality);
        }
        resolve(dataUrl);
      };
      image.onerror = () => reject(new Error("Kunde inte läsa bilden."));
      image.src = String(reader.result || "");
    };
    reader.onerror = () => reject(new Error("Kunde inte läsa bilden."));
    reader.readAsDataURL(file);
  });
}

async function updateImagePreview() {
  const file = $("#newObjectImage").files[0];
  const preview = $("#newObjectImagePreview");
  if (!file) {
    clearImagePreview();
    return;
  }
  if (!file.type.startsWith("image/")) {
    preview.innerHTML = "<span>Filen är inte en bild.</span>";
    return;
  }

  preview.innerHTML = "<span>Anpassar bilden...</span>";
  try {
    const dataUrl = await resizeObjectImage(file);
    preview.innerHTML = `<img src="${dataUrl}" alt="">`;
  } catch (error) {
    preview.innerHTML = `<span>${escapeHtml(error.message)}</span>`;
  }
}

function clearImagePreview() {
  $("#newObjectImage").value = "";
  $("#newObjectImagePreview").innerHTML = "<span>Ingen bild vald</span>";
}

// ============================================================
// KOPPLING TILL HTML-KNAPPAR OCH INPUTS
// Alla event listeners samlas har sa du snabbt hittar vad en knapp gor.
// ============================================================

function bindEvents() {
  document.querySelectorAll(".nav-button").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  document.querySelectorAll(".language-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.language = button.dataset.language;
      localStorage.setItem("language", state.language);
      applyTranslations();
      renderFilters();
	      renderUsers();
	      renderLoans();
	      renderJobs();
	      renderObjects();
	      renderAdminObjectsTable();
	      updateCheckoutInfo();
      renderCheckoutUserDetails();
      renderPickupItems();
      renderMyLoans();
      renderReturnLoans(true);
    });
  });
  document.querySelectorAll("[data-view-target]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.viewTarget));
  });
  document.querySelectorAll("[data-dashboard-focus='consumable']").forEach((button) => {
    button.addEventListener("click", () => {
      showToast(state.language === "en" ? "This will move to a separate page." : "Den funktionen hamnar på en egen sida.");
    });
  });

	  $("#objectSearch").addEventListener("input", renderObjects);
	  $("#categoryFilter").addEventListener("change", renderObjects);
	  $("#statusFilter").addEventListener("change", renderObjects);
	  $("#loanSearch")?.addEventListener("input", renderLoans);
	  $("#loanStatusFilter")?.addEventListener("change", renderLoans);
	  $("#jobSearch")?.addEventListener("input", renderJobs);
	  $("#jobDateSort")?.addEventListener("change", renderJobs);
	  $("#toggleJobsCollapsed")?.addEventListener("click", toggleJobsCollapsed);
	  $("#checkoutObjectId").addEventListener("input", () => {
    updateCheckoutInfo();
    renderCheckoutObjectSuggestions();
  });
	  $("#exportObjectsExcelButton")?.addEventListener("click", exportVisibleObjectsCsv);
	  $("#checkoutUserSearch").addEventListener("input", renderCheckoutUserSuggestions);
  $("#openUserScanButton")?.addEventListener("click", openUserScanModal);
  $("#closeUserScanButton")?.addEventListener("click", closeUserScanModal);
  $("#userScanBackdrop")?.addEventListener("click", closeUserScanModal);
  $("#readUserCardButton")?.addEventListener("click", scanCheckoutUserCard);
  $("#openObjectScanButton")?.addEventListener("click", openObjectScanModal);
  $("#closeObjectScanButton")?.addEventListener("click", closeObjectScanModal);
  $("#objectScanBackdrop")?.addEventListener("click", closeObjectScanModal);
	  $("#dashboardMyLoansButton")?.addEventListener("click", showDashboardMyLoans);
  $("#dashboardTipPrev")?.addEventListener("click", () => stepDashboardTip(-1));
  $("#dashboardTipNext")?.addEventListener("click", () => stepDashboardTip(1));
	  $("#consumableObjectSearch")?.addEventListener("input", renderConsumableObjectSuggestions);
  $("#checkoutLendingDate")?.addEventListener("change", updateCheckoutDateLimit);
  $("#newUserPhone")?.addEventListener("input", () => sanitizePhoneField("#newUserPhone"));
  $("#quickUserPhone")?.addEventListener("input", () => sanitizePhoneField("#quickUserPhone"));
	  $("#returnUserSearch")?.addEventListener("input", renderReturnUserSuggestions);
	  $("#pickupUserSearch")?.addEventListener("input", renderPickupUserSuggestions);
	  $("#myLoansUserSearch")?.addEventListener("input", renderMyLoansUserSuggestions);

	  $("#addLoanArticle").addEventListener("click", () => {
      try { addLoanArticle(); } catch (error) { showToast(error.message); }
    });
    $("#checkoutForm").addEventListener("submit", (event) => {
      event.preventDefault();
      if ($("#checkoutObjectId").value.trim()) {
        try { addLoanArticle(); } catch (error) { showToast(error.message); }
      }
    });
    $("#returnSelectedButton").addEventListener("click", () => returnSelectedLoans());
    $("#returnAllButton").addEventListener("click", () => returnSelectedLoans(true));
    $("#requestLoanButton").addEventListener("click", requestLoan);
	  $("#consumableReportForm")?.addEventListener("submit", saveConsumableReport);
	  $("#addObjectForm").addEventListener("submit", saveObject);
  $("#addUserForm").addEventListener("submit", saveUser);
  $("#groupForm")?.addEventListener("submit", saveGroup);
  $("#cancelGroupEditButton")?.addEventListener("click", resetGroupForm);
	  $("#cancelUserEditButton").addEventListener("click", resetUserForm);
  $("#systemSettingsForm")?.addEventListener("submit", saveSystemSettings);
  $("#saveAutomationSettingsButton")?.addEventListener("click", saveSystemSettings);
  $("#saveMessageTemplatesButton")?.addEventListener("click", saveSystemSettings);
  $("#sendRemindersButton")?.addEventListener("click", sendLoanReminders);
  $("#sendTeamsTestButton")?.addEventListener("click", sendTeamsTestMessage);
  document.querySelectorAll("[data-add-recipient]").forEach((button) => {
    button.addEventListener("click", () => addNotificationRecipient(button.dataset.addRecipient));
  });
  document.querySelectorAll("[data-recipient-input]").forEach((input) => {
    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter") return;
      event.preventDefault();
      addNotificationRecipient(input.dataset.recipientInput);
    });
  });
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-recipient]");
    if (!button) return;
    removeNotificationRecipient(button.dataset.removeRecipient, button.dataset.recipientValue);
  });
  document.querySelectorAll(".admin-settings-nav-button").forEach((button) => {
    button.addEventListener("click", () => showAdminSettingsSection(button.dataset.adminSection));
  });
  document.querySelectorAll(".system-settings-nav-button").forEach((button) => {
    button.addEventListener("click", () => showSystemSettingsSection(button.dataset.systemSection));
  });
  $("#quickUserForm").addEventListener("submit", saveQuickUser);
  $("#openQuickUserButton").addEventListener("click", openQuickUserModal);
  $("#closeQuickUserButton").addEventListener("click", closeQuickUserModal);
  $("#quickUserBackdrop").addEventListener("click", closeQuickUserModal);
  $("#userCardForm")?.addEventListener("submit", saveUserCard);
  $("#scanUserCardCodeButton")?.addEventListener("click", scanUserCardCode);
  $("#generateUserCardCodeButton")?.addEventListener("click", generateUserCardCode);
  $("#closeUserCardButton")?.addEventListener("click", closeUserCardModal);
  $("#userCardBackdrop")?.addEventListener("click", closeUserCardModal);
	  $("#closeJobDetailButton").addEventListener("click", closeJobDetail);
	  $("#jobDetailBackdrop").addEventListener("click", closeJobDetail);
  $("#editJobButton").addEventListener("click", toggleJobEdit);
	  $("#printJobButton").addEventListener("click", printSelectedJob);
  $("#exportJobExcelButton").addEventListener("click", exportSelectedJobCsv);
  $("#quickUserDepartmentName").addEventListener("change", () => {
    syncDepartmentFromGroup("#quickUserDepartmentName", "#quickUserDepartment");
  });
  $("#newUserDepartmentName").addEventListener("change", () => {
    syncDepartmentFromGroup("#newUserDepartmentName", "#newUserDepartment");
  });
  $("#cancelObjectEditButton").addEventListener("click", resetObjectForm);

  $("#newObjectImage").addEventListener("change", updateImagePreview);
  $("#roleSelect").addEventListener("change", () => {
    $("#roleSelect").value = state.role;
    applyRole();
  });

  $("#openSearchButton").addEventListener("click", openSearch);
  $("#closeSearchButton").addEventListener("click", closeSearch);
  $("#searchBackdrop").addEventListener("click", closeSearch);
  $("#submitSearchButton").addEventListener("click", performSearch);
  $("#clearSearchButton").addEventListener("click", () => {
    $("#globalSearchInput").value = "";
    performSearch();
    $("#globalSearchInput").focus();
  });
  $("#globalSearchInput").addEventListener("input", () => {
    clearTimeout(performSearch.timeout);
    performSearch.timeout = setTimeout(performSearch, 160);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeSearch();
    if (event.key === "Escape") closeQuickUserModal();
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      openSearch();
    }
  });
}

// ============================================================
// START
// Kor nar sidan laddas.
// ============================================================

async function init() {
  if (!await establishSession()) return;
  populateNumberSelects();
  bindEvents();
  setDefaultDates();
  applyTranslations();
  refreshAll().catch((error) => showToast(error.message));
}

init().catch((error) => showToast(error.message));

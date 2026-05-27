// ============================================================
// STATE OCH KONFIGURATION
// ============================================================

const state = {
  objects: [],
  users: [],
  loans: [],
  jobs: [],
  consumableReports: [],
  events: [],
  systemSettings: {},
  statistics: {},
  editingObjectId: null,
  editingUserId: null,
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
}

async function refreshAll() {
  const [stats, statistics, objects, users, loans, jobs, consumableReports, events, systemSettings] = await Promise.all([
    api("/api/stats"),
    api("/api/statistics"),
    api("/api/objects"),
    api("/api/users"),
    api("/api/loans"),
    api("/api/loan-requests"),
    api("/api/consumable-reports"),
    api("/api/events?limit=100"),
    api("/api/system-settings"),
  ]);

  state.objects = objects;
  state.statistics = statistics;
  state.users = users;
  state.loans = loans;
  state.jobs = jobs;
  state.consumableReports = consumableReports;
  state.events = events;
  state.systemSettings = systemSettings;

  renderStats(stats);
  renderUsers();
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
  setValue("#smtpFromAddress", settings.smtp_from_address || "");
  setChecked("#smtpUseTls", settings.smtp_use_tls !== "0");
  setValue("#notificationRecipients", settings.notification_recipients || "");
  setValue("#loanReminderDays", settings.loan_reminder_days || settings.due_soon_days || "10");
  setChecked("#notifyLoanReminders", settings.notify_loan_reminders !== "0");
  setChecked("#notifyNewJobAutomation", settings.notify_new_job !== "0");
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
  setTextValue("#smtpSummary", settings.smtp_enabled === "1" ? "Ja" : "Nej");
  setTextValue("#modbusSummary", settings.modbus_enabled === "1" ? "Ja" : "Nej");
  setTextValue(
    "#borrowBlockSummary",
    settings.overdue_block_enabled === "1" ? `Från ${settings.overdue_block_limit || "3"} sena lån` : "Av"
  );
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
  splitRecipients(state.systemSettings?.notification_recipients || "").forEach((recipient) => values.add(recipient));
  datalist.innerHTML = [...values].sort().map((email) => `<option value="${escapeHtml(email)}"></option>`).join("");
}

function renderNotificationRecipients() {
  renderNotificationRecipientOptions();
  notificationRecipientKeys.forEach((key) => {
    const container = document.querySelector(`[data-recipient-chips="${key}"]`);
    if (!container) return;
    const recipients = recipientsForKey(key);
    if (!recipients.length) {
      container.innerHTML = `<span class="recipient-empty">Använder global SMTP-lista</span>`;
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
  renderDepartmentNames();
  renderUsersTable();
}

function renderUsersTable() {
  const usersBody = $("#usersBody");
	  if (usersBody) {
	    usersBody.innerHTML = state.users.map((user) => `
	      <tr>
        <td>${escapeHtml(user.name)}</td>
        <td>${escapeHtml(user.alias || "")}</td>
        <td>${escapeHtml(user.email || "")}</td>
        <td>${escapeHtml(user.phone || "")}</td>
	        <td>${escapeHtml(user.company || "")}</td>
	        <td>${escapeHtml(user.department_name || user.department || "")}</td>
		        <td>${escapeHtml(user.role || "operator")}</td>
        <td>
          <button class="table-action-button" type="button" data-edit-user="${escapeHtml(user.user_id)}">Edit</button>
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
	  }
}

function renderDepartmentNames() {
  const departmentList = $("#departmentNameList");
  if (!departmentList) return;
  departmentList.innerHTML = unique(state.users.map((user) => user.department_name || user.department))
    .map((departmentName) => `<option value="${escapeHtml(departmentName)}"></option>`)
    .join("");
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
      <td>${item.available_quantity} / ${item.total_quantity}</td>
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
      <td>${item.available_quantity} / ${item.total_quantity}</td>
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
  const filter = $("#checkoutStockFilter")?.value || "in_stock";
  if (filter === "all") return true;
  if (filter === "in_stock") return item.available_quantity > 0;
  if (filter === "low_stock") return item.available_quantity > 0 && item.available_quantity <= item.min_quantity;
  if (filter === "out_of_stock") return item.available_quantity <= 0;
  return true;
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
  const matches = (filteredMatches.length ? filteredMatches : allMatches).slice(0, 8);
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
      loan.quantity,
      formatTime(loan.checkout_time),
      formatTime(loan.due_time),
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
      <td>${loan.quantity}</td>
      <td>${formatTime(loan.checkout_time)}</td>
      <td>${formatTime(loan.due_time)}</td>
      <td>${statusBadge(loan.overdue ? "Sen" : "Aktiv")}</td>
      <td><button class="link-button" type="button" data-print-loan="${loan.loan_id}">${t("action.print")}</button></td>
    </tr>
  `).join("");
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
        title: "Return an item",
        text: "Press Return, search for your name and return the active loan from the list.",
      },
      {
        title: "Find your loans",
        text: "Use My loans to see your active loans in one place. Search for your name to quickly find what you have borrowed and when it should be returned.",
      },
      {
        title: "Report empty stock",
        text: "Use Report out of stock when a consumable article needs refilling.",
      },
    ];
  }
  return [
    {
      title: "Låna ett objekt",
      text: "Tryck på Låna, välj dig själv, sök fram objektet och skicka låneförfrågan med antal och returdatum.",
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
      title: "Anmäl slut på lager",
      text: "Använd Anmäl slut på lager när en förbrukningsvara behöver fyllas på.",
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
    requested: ["prepared", "jobs.nextPrepared"],
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
  const columns = [
    { status: "requested", tone: "yellow" },
    { status: "prepared", tone: "green" },
    { status: "loaned", tone: "blue" },
    { status: "returned", tone: "yellow" },
    { status: "stocked", tone: "gray" },
  ];
  jobsBoard.innerHTML = columns.map((column) => {
    const jobs = filteredJobs.filter((job) => job.status === column.status);
    return `
      <section class="job-column job-column-${column.tone}">
        <header class="job-column-header">
          <h2>${escapeHtml(jobStatusText(column.status))}</h2>
          <span>${jobs.length}</span>
        </header>
        <div class="job-column-list" data-job-drop-status="${column.status}">
          ${jobs.length ? jobs.map(renderJobCard).join("") : `<div class="job-empty">${escapeHtml(t("jobs.empty"))}</div>`}
        </div>
      </section>
    `;
  }).join("");
  document.querySelectorAll("[data-job-id]").forEach((button) => {
    button.addEventListener("click", () => updateJobStatus(Number(button.dataset.jobId), button.dataset.jobStatus));
  });
  document.querySelectorAll("[data-delete-job]").forEach((button) => {
    button.addEventListener("click", () => deleteJob(Number(button.dataset.deleteJob)));
  });
  document.querySelectorAll("[data-open-job-id]").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("button, summary, details")) return;
      openJobDetail(Number(card.dataset.openJobId));
    });
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

function renderJobCard(job) {
  const action = nextJobAction(job.status);
  return `
    <article class="job-card" draggable="true" data-open-job-id="${job.request_id}" data-drag-job-id="${job.request_id}" data-drag-job-status="${job.status}">
      <div class="job-card-top">
        <strong>#${job.request_id}</strong>
        <span>${escapeHtml(job.object_id)}</span>
      </div>
      <h3>${escapeHtml(job.object_name)}</h3>
      <div class="job-card-summary">
        <span>${escapeHtml(job.user_name)}</span>
        <span>${escapeHtml(t("table.storage"))}: ${escapeHtml(job.object_location || "")}</span>
        <span>${escapeHtml(t("table.store"))}: ${escapeHtml(job.object_store || "")}</span>
      </div>
      <details class="job-card-details">
        <summary>${state.language === "en" ? "Details" : "Detaljer"}</summary>
        <dl>
          <dt>${escapeHtml(t("table.borrower"))}</dt><dd>${escapeHtml(job.user_name)}</dd>
          <dt>${escapeHtml(t("table.deptNo"))}</dt><dd>${escapeHtml(job.user_department || "")}</dd>
          <dt>${escapeHtml(t("table.storage"))}</dt><dd>${escapeHtml(job.object_location || "")}</dd>
          <dt>${escapeHtml(t("table.store"))}</dt><dd>${escapeHtml(job.object_store || "")}</dd>
          <dt>${escapeHtml(t("field.engineId"))}</dt><dd>${escapeHtml(job.engine_id || "")}</dd>
          <dt>${escapeHtml(t("table.projectNo"))}</dt><dd>${escapeHtml(job.project_number || "")}</dd>
          <dt>${escapeHtml(t("field.quantity"))}</dt><dd>${job.quantity}</dd>
          <dt>${escapeHtml(t("field.lendingDate"))}</dt><dd>${escapeHtml(job.lending_date)}</dd>
          <dt>${escapeHtml(t("field.returnDate"))}</dt><dd>${escapeHtml(job.return_date)}</dd>
        </dl>
      </details>
      <div class="job-card-actions">
        ${action ? `<button class="table-action-button" type="button" data-job-id="${job.request_id}" data-job-status="${action[0]}">${t(action[1])}</button>` : ""}
        <button class="danger-button" type="button" data-delete-job="${job.request_id}">${state.language === "en" ? "Remove" : "Ta bort"}</button>
      </div>
    </article>
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
  $("#jobDetailContent").innerHTML = `
    <dl class="job-detail-grid">
      ${jobDetailRows(job).map(([label, value]) => `
        <dt>${escapeHtml(label)}</dt>
        <dd>${escapeHtml(String(value ?? ""))}</dd>
      `).join("")}
    </dl>
  `;
  $("#jobDetailModal").classList.add("open");
  $("#jobDetailModal").setAttribute("aria-hidden", "false");
}

function closeJobDetail() {
  $("#jobDetailModal").classList.remove("open");
  $("#jobDetailModal").setAttribute("aria-hidden", "true");
  state.selectedJobId = null;
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

function csvCell(value) {
  const text = String(value ?? "");
  return `"${text.replaceAll('"', '""')}"`;
}

function bindJobDragAndDrop() {
  let draggedCard = null;
  const placeholder = document.createElement("div");
  placeholder.className = "job-drop-placeholder";

  document.querySelectorAll("[data-drag-job-id]").forEach((card) => {
    card.addEventListener("dragstart", (event) => {
      draggedCard = card;
      card.classList.add("dragging");
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData("text/plain", card.dataset.dragJobId);
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
      const requestId = Number(event.dataTransfer.getData("text/plain"));
      const status = zone.dataset.jobDropStatus;
      const job = state.jobs.find((item) => item.request_id === requestId);
      if (!job) return;
      if (draggedCard && placeholder.parentElement === zone) {
        zone.insertBefore(draggedCard, placeholder);
      }
      placeholder.remove();
      if (job.status === status) return;
      updateJobStatus(requestId, status);
    });
  });
}

function getDragAfterElement(container, y) {
  const draggableElements = [...container.querySelectorAll(".job-card:not(.dragging)")];
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
  if (item.image_data) {
    return `<img class="object-thumb" src="${escapeHtml(item.image_data)}" alt="">`;
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
  if (file.size > 700_000) {
    return Promise.reject(new Error("Bilden är för stor. Välj en bild under 700 KB."));
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(new Error("Kunde inte läsa bilden."));
    reader.readAsDataURL(file);
  });
}

function updateImagePreview() {
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

  const url = URL.createObjectURL(file);
  preview.innerHTML = `<img src="${url}" alt="">`;
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
	  $("#checkoutStockFilter").addEventListener("change", renderCheckoutObjectSuggestions);
	  $("#checkoutUserSearch").addEventListener("input", renderCheckoutUserSuggestions);
  $("#openUserScanButton")?.addEventListener("click", openUserScanModal);
  $("#closeUserScanButton")?.addEventListener("click", closeUserScanModal);
  $("#userScanBackdrop")?.addEventListener("click", closeUserScanModal);
  $("#openObjectScanButton")?.addEventListener("click", openObjectScanModal);
  $("#closeObjectScanButton")?.addEventListener("click", closeObjectScanModal);
  $("#objectScanBackdrop")?.addEventListener("click", closeObjectScanModal);
	  $("#dashboardMyLoansButton")?.addEventListener("click", showDashboardMyLoans);
  $("#dashboardTipPrev")?.addEventListener("click", () => stepDashboardTip(-1));
  $("#dashboardTipNext")?.addEventListener("click", () => stepDashboardTip(1));
	  $("#consumableObjectSearch")?.addEventListener("input", renderConsumableObjectSuggestions);
	  $("#returnUserSearch")?.addEventListener("input", renderReturnUserSuggestions);
	  $("#pickupUserSearch")?.addEventListener("input", renderPickupUserSuggestions);
	  $("#myLoansUserSearch")?.addEventListener("input", renderMyLoansUserSuggestions);

	  $("#requestLoanButton").addEventListener("click", requestLoan);
	  $("#consumableReportForm")?.addEventListener("submit", saveConsumableReport);
	  $("#addObjectForm").addEventListener("submit", saveObject);
  $("#addUserForm").addEventListener("submit", saveUser);
  $("#cancelUserEditButton").addEventListener("click", resetUserForm);
  $("#systemSettingsForm")?.addEventListener("submit", saveSystemSettings);
  $("#saveAutomationSettingsButton")?.addEventListener("click", saveSystemSettings);
  $("#sendRemindersButton")?.addEventListener("click", sendLoanReminders);
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
  $("#closeJobDetailButton").addEventListener("click", closeJobDetail);
  $("#jobDetailBackdrop").addEventListener("click", closeJobDetail);
  $("#printJobButton").addEventListener("click", printSelectedJob);
  $("#exportJobExcelButton").addEventListener("click", exportSelectedJobCsv);
  $("#quickUserDepartmentName").addEventListener("change", () => {
    fillDepartmentFromDepartmentName("#quickUserDepartmentName", "#quickUserDepartment");
  });
  $("#newUserDepartmentName").addEventListener("change", () => {
    fillDepartmentFromDepartmentName("#newUserDepartmentName", "#newUserDepartment");
  });
  $("#cancelObjectEditButton").addEventListener("click", resetObjectForm);

  $("#newObjectImage").addEventListener("change", updateImagePreview);
  $("#roleSelect").addEventListener("change", () => {
    state.role = $("#roleSelect").value;
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

function init() {
  populateNumberSelects();
  bindEvents();
  setDefaultDates();
  applyTranslations();
  refreshAll().catch((error) => showToast(error.message));
}

init();

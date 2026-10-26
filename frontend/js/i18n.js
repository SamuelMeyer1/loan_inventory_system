// Frontend translation helpers.
function t(key, values = {}) {
  const text = translations[state.language]?.[key] || translations.sv[key] || key;
  return Object.entries(values).reduce((result, [name, value]) => result.replaceAll(`{${name}}`, value), text);
}

function statusText(status) {
  const statusKeys = {
    "Tillgänglig": "status.available",
    "Låg nivå": "status.low",
    "Slut": "status.out",
    "Aktiv": "status.active",
    "Sen": "status.late",
  };
  return t(statusKeys[status] || status);
}

function jobStatusText(status) {
  return t(`jobs.status.${status}`);
}

function setText(selector, key) {
  const element = $(selector);
  if (element) element.textContent = t(key);
}

function setPlaceholder(selector, key) {
  const element = $(selector);
  if (element) element.placeholder = t(key);
}

function setLabel(inputId, key) {
  const input = $(`#${inputId}`);
  const label = input?.closest("label");
  if (!label) return;
  const textNode = Array.from(label.childNodes).find((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim());
  if (textNode) textNode.textContent = `\n              ${t(key)}\n              `;
}

function setOptionText(selectId, value, key) {
  const option = $(`#${selectId} option[value="${value}"]`);
  if (option) option.textContent = t(key);
}

function setHeaderTexts(selector, keys) {
  document.querySelectorAll(`${selector} th`).forEach((header, index) => {
    if (keys[index]) header.textContent = t(keys[index]);
  });
}

function applyTranslations() {
  const adminTexts = {
    "#adminRulesDescription": "settings.rulesDescription",
    "#inactivitySettingsTitle": "settings.inactivityTitle",
    "#inactiveUserWarningLabel": "settings.inactivityEnabled",
    "#inactiveUserDaysLabel": "settings.inactivityDays",
    "#inactiveUserHelp": "settings.inactivityHelp",
    "#adminNotificationSettingsTitle": "notifications.settingsTitle",
    "#notifyAdminNewRequestLabel": "notifications.request",
    "#notifyAdminLoanedLabel": "notifications.loan",
    "#adminNotificationSettingsHelp": "notifications.settingsHelp",
    "#adminNotificationsTitle": "notifications.title",
    "#adminNotificationsHelp": "notifications.help",
    "#markAdminNotificationsRead": "notifications.markRead",
    "#adminNotificationJobs": "notifications.jobs",
    "#newUserActiveLabel": "admin.activeUser",
    "#newUserActiveHelp": "admin.activeUserHelp",
    "#borrowerProfileHelp": "admin.borrowerProfileHelp",
    "#jobReturnTitle": "jobs.returnArticles",
    "#jobReturnHelp": "jobs.returnHelp",
    "#saveJobReturn": "jobs.returnSave",
    "#cancelJobReturn": "action.cancel",
  };
  Object.entries(adminTexts).forEach(([selector, key]) => setText(selector, key));
  renderAdminNotifications();
  ["newUser", "quickUser"].forEach((prefix) => {
    setText(`#${prefix}PrivacyText`, "privacy.acknowledge");
    setText(`#${prefix}PrivacyLink`, "privacy.read");
  });
  setText("#simulationBadge", "runtime.simulation");
  setText("#loginSimulationBadge", "runtime.simulation");
  renderLoanCart();
  updateReturnButtons();
  document.documentElement.lang = state.language;
  const languageToggle = document.querySelector(".language-toggle");
  if (languageToggle) languageToggle.setAttribute("aria-label", t("topbar.language"));
  setText(".language-label", "topbar.language");
  document.querySelectorAll(".language-button").forEach((button) => {
    const isActive = button.dataset.language === state.language;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });

  setText(".brand-subtitle", "brand.subtitle");
  document.querySelectorAll(".nav-button").forEach((button) => {
    setText(`.nav-button[data-view="${button.dataset.view}"]`, viewTitles[button.dataset.view]);
  });
  setText("#openSearchButton", "topbar.search");
  setLabel("roleSelect", "topbar.role");
  setOptionText("roleSelect", "operator", "role.operator");
  setOptionText("roleSelect", "admin", "role.admin");
  setOptionText("roleSelect", "superadmin", "role.superadmin");

  setText(".dashboard-command-button[data-view-target=\"checkout\"]", "dashboard.borrow");
  setText(".dashboard-command-button[data-view-target=\"pickup\"]", "dashboard.pickup");
  setText(".dashboard-command-button[data-view-target=\"return\"]", "dashboard.return");
  setText(".dashboard-command-button[data-view-target=\"consumable\"]", "dashboard.reportConsumable");
  setText("#dashboardMyLoansButton", "dashboard.myLoans");
  renderDashboardTips();

  setText("#statisticsView h1", "nav.statistics");
  setText(".stat-card:nth-of-type(1) span", "stats.objects");
  setText(".stat-card:nth-of-type(2) span", "stats.loaned");
  setText(".stat-card:nth-of-type(3) span", "stats.overdue");
  setText(".stat-card:nth-of-type(4) span", "stats.low");
  setText(".stat-card:nth-of-type(5) span", "stats.readyPickup");
  setText(".stat-card:nth-of-type(6) span", "stats.openJobs");

  setText("#checkoutView h1", "nav.checkout");
  setText(".checkout-action-row span", "checkout.missingUser");
  setText("#openQuickUserButton", "checkout.createUser");
  setText("#openUserScanButton", "checkout.scanUser");
  setText("#checkoutUserShowMore", "checkout.showUserDetails");
  setText("#checkoutUserShowLess", "checkout.hideUserDetails");
  setText("#checkoutObjectShowMore", "checkout.showUserDetails");
  setText("#checkoutObjectShowLess", "checkout.hideUserDetails");
  setText("#userScanTitle", "checkout.scanUser");
  setText("#userScanStatusTitle", "checkout.scanWaiting");
  setText("#userScanStatusText", "checkout.scanFuture");
  $("#closeUserScanButton")?.setAttribute("aria-label", t("search.close"));
  setText("#openObjectScanButton", "checkout.scanObject");
  setText("#objectScanTitle", "checkout.scanObject");
  setText("#objectScanStatusTitle", "checkout.scanObjectWaiting");
  setText("#objectScanStatusText", "checkout.scanObjectFuture");
  $("#closeObjectScanButton")?.setAttribute("aria-label", t("search.close"));
  setLabel("checkoutUserSearch", "checkout.searchUser");
  setPlaceholder("#checkoutUserSearch", "checkout.searchUser");
  setLabel("checkoutObjectId", "checkout.searchObject");
  setPlaceholder("#checkoutObjectId", "checkout.searchObject");
  setText("#requestLoanButton", "action.requestLoan");

  [
    ["checkoutUserCompany", "field.company"],
    ["checkoutUserGroup", "field.group"],
    ["checkoutUserDepartment", "field.department"],
    ["checkoutUserEmail", "field.email"],
    ["checkoutUserPhone", "field.phone"],
    ["checkoutUserAlias", "field.alias"],
    ["checkoutObjectName", "field.name"],
    ["checkoutObjectInstrumentId", "field.instrumentId"],
    ["checkoutObjectCategory", "field.category"],
    ["checkoutObjectType", "field.type"],
    ["checkoutObjectDescription", "field.description"],
    ["checkoutObjectLocation", "field.location"],
    ["checkoutObjectLift", "field.lift"],
    ["checkoutObjectQuantity", "checkout.remainingStock"],
    ["checkoutObjectStatus", "field.status"],
    ["checkoutEngineId", "field.engineId"],
    ["checkoutProjectNumber", "field.projectNumber"],
    ["checkoutQuantity", "field.quantity"],
    ["checkoutLendingDate", "field.lendingDate"],
    ["checkoutDue", "field.returnDate"],
    ["consumableObjectSearch", "field.article"],
    ["returnUserSearch", "nav.return"],
    ["newUserFirstName", "field.firstName"],
    ["newUserLastName", "field.lastName"],
    ["newUserEmail", "field.email"],
    ["newUserPhone", "field.phone"],
    ["newUserCompany", "field.company"],
    ["newUserAlias", "field.alias"],
    ["newUserDepartment", "field.department"],
    ["newUserDepartmentName", "field.group"],
    ["quickUserFirstName", "field.firstName"],
    ["quickUserLastName", "field.lastName"],
    ["quickUserEmail", "field.email"],
    ["quickUserPhone", "field.phone"],
    ["quickUserCompany", "field.company"],
    ["quickUserAlias", "field.alias"],
    ["quickUserDepartment", "field.department"],
    ["quickUserDepartmentName", "field.group"],
    ["newObjectId", "field.instrumentId"],
    ["newObjectName", "field.name"],
    ["newObjectCategory", "field.category"],
    ["newObjectType", "field.type"],
    ["newObjectDescription", "field.description"],
    ["newObjectArticle", "table.article"],
    ["newObjectSupplierArticle", "table.supplierArticle"],
    ["newObjectLocation", "field.location"],
    ["newObjectStorageLocation2", "table.storage2"],
    ["newObjectTornado", "table.store"],
    ["newObjectDoor", "field.lift"],
    ["newObjectBelongsToInstrument", "table.belongsInstrument"],
    ["newObjectDevice", "Device"],
    ["newObjectBelongsTo", "table.belongsTo"],
    ["newObjectLastChanged", "table.lastChanged"],
    ["newObjectSearchWords", "table.keywords"],
    ["newObjectTrayFor", "table.trayFor"],
    ["newObjectLiftTray", "table.liftTray"],
    ["newObjectTotal", "field.total"],
    ["newObjectAvailable", "table.balance"],
    ["newObjectMin", "table.reorderPoint"],
  ].forEach(([id, key]) => setLabel(id, key));

  setText("#returnView h1", "nav.return");
  setText("#returnInstructions", "return.instructions");
  setLabel("returnUserSearch", "checkout.searchUser");
  setHeaderTexts("#returnView table", ["table.loanId", "table.object", "return.remaining", "return.quantity", "return.damaged", "return.description", "field.returnDate"]);
  setText("#damageNav", "damage.title");
  setText("#damageTitle", "damage.title");
  setText("#damageInstructions", "damage.instructions");
  renderReturnSummary();
  renderDamagedReturns();
  setPlaceholder("#returnUserSearch", "checkout.searchUser");
  setText("#pickupView h1", "nav.pickup");
  setLabel("pickupUserSearch", "checkout.searchUser");
  setPlaceholder("#pickupUserSearch", "checkout.searchUser");
  setText("#myLoansView h1", "nav.myLoans");
  setLabel("myLoansUserSearch", "checkout.searchUser");
  setPlaceholder("#myLoansUserSearch", "checkout.searchUser");
  setText("#consumableView h1", "nav.consumable");
  setText("#consumableSubmitButton", "action.reportConsumableEmpty");
  setText("#objectsView h1", "nav.objects");
  setPlaceholder("#objectSearch", "objects.searchPlaceholder");
  setHeaderTexts("#objectsView table", [
    "table.image",
    "field.category",
    "field.type",
    "field.description",
    "table.article",
    "field.name",
    "table.supplierArticle",
    "table.balance",
    "table.reorderPoint",
    "table.storage",
    "table.store",
    "table.belongsInstrument",
    "Device",
    "table.belongsTo",
    "table.lastChanged",
    "table.keywords",
    "table.trayFor",
    "table.storage2",
    "table.liftTray",
    "field.status",
    "",
  ]);
  setText("#loansView h1", "nav.loans");
  setText("#jobsView h1", "nav.jobs");
  updateJobsCollapseButton();

  setHeaderTexts("#loansView table", [
    "table.loanId",
    "field.instrumentId",
    "table.object",
    "table.borrower",
    "table.deptNo",
    "field.engineId",
    "table.projectNo",
    "field.quantity",
    "field.lendingDate",
    "field.returnDate",
    "field.status",
    "table.lastReminder",
    "action.sendReminder",
    "table.receipt",
  ]);

	  setText("#adminView h1", "nav.admin");
	  setText("#objectFormTitle", "admin.addObject");
	  setText("#saveObjectButton", "action.saveObject");
	  setText("#cancelObjectEditButton", "action.cancel");
	  setText("#cancelUserEditButton", "action.cancel");
	  const adminCards = document.querySelectorAll("#adminView .admin-card");
	  if (adminCards[1]?.querySelector("h2")) adminCards[1].querySelector("h2").textContent = t("admin.createUser");
	  if (!state.editingUserId) setText("#saveUserButton", "admin.createUser");
	  setText("#adminView .admin-subtitle", "admin.users");
	  setHeaderTexts("#adminView .compact-table-wrap table", [
	    "field.name",
    "field.alias",
    "field.email",
    "field.phone",
	    "field.company",
	    "field.department",
	    "topbar.role",
	    "",
	  ]);
  setText("#logView h1", "nav.log");
  setHeaderTexts("#logView table", ["table.time", "table.eventType", "table.message"]);
  setText("#systemView h1", "nav.system");

	  setText("#quickUserTitle", "admin.createUser");
	  setText("#quickUserForm .primary-button", "modal.createAndSelect");
	  setText("#printJobButton", "action.print");
	  setText("#exportJobExcelButton", "action.exportExcel");
  setText("#exportObjectsExcelButton", "action.exportExcel");
  setPlaceholder("#globalSearchInput", "search.placeholder");
  setText("#submitSearchButton", "topbar.search");
  setText("#closeSearchButton", "search.close");
  $("#clearSearchButton")?.setAttribute("aria-label", t("search.clearLabel"));
  setText("#searchTitle", "search.results");
  setText(".search-section-title", "search.objects");
  const searchTabs = document.querySelectorAll(".search-tab");
  if (searchTabs[0]) searchTabs[0].textContent = `${t("search.all")} (0)`;
  if (searchTabs[1]) searchTabs[1].textContent = `${t("search.objects")} (0)`;
  if (searchTabs[2]) searchTabs[2].textContent = t("search.loans");
  if (searchTabs[3]) searchTabs[3].textContent = t("search.log");
  $("#searchEmpty").textContent = t("search.empty");

}

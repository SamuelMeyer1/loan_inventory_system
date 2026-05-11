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
  editingObjectId: null,
  editingUserId: null,
  role: "operator",
  language: localStorage.getItem("language") || "sv",
  selectedJobId: null,
  dashboardGuideIndex: 0,
};

const viewTitles = {
  dashboard: "nav.dashboard",
  checkout: "nav.checkout",
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

const translations = {
  sv: {
    "brand.subtitle": "Utlåning och lager",
    "sidebar.footer": "Lokal HTML-prototyp",
    "nav.dashboard": "Dashboard",
    "nav.checkout": "Låna",
    "nav.return": "Lämna tillbaka",
    "nav.issue": "Checka ut",
    "nav.book": "Boka",
    "nav.objects": "Objekt",
    "nav.statistics": "Statistik",
    "nav.jobs": "Jobb",
    "nav.loans": "Aktiva lån",
    "nav.admin": "Admin",
    "nav.log": "Logg",
    "nav.system": "System",
    "topbar.search": "Sök",
    "topbar.role": "Roll",
    "role.operator": "Operatör",
    "role.admin": "Admin",
    "role.superadmin": "SuperAdmin",
    "dashboard.borrow": "Låna",
    "dashboard.borrow.desc": "Skapa ett lån med returdatum.",
    "dashboard.kicker": "Arbetsflöde",
    "dashboard.title": "Utlåning och förbrukning",
    "dashboard.text": "Skicka låneförfrågningar, följ jobb och rapportera artiklar som behöver fyllas på.",
    "dashboard.newRequest": "Ny låneförfrågan",
    "dashboard.showJobs": "Visa jobb",
    "dashboard.reportConsumable": "Rapportera slut förbrukningsvara",
    "dashboard.openReports": "Öppna förbrukningsrapporter",
    "dashboard.return": "Lämna tillbaka",
    "dashboard.return.desc": "Avsluta ett aktivt lån.",
    "dashboard.issue": "Checka ut",
    "dashboard.issue.desc": "Ta ut förbrukning utan retur.",
    "dashboard.book": "Boka",
    "dashboard.book.desc": "Boka ett framtida lån.",
    "stats.objects": "Antal objekt",
    "stats.loaned": "Utlånade objekt",
    "stats.overdue": "Sena lån",
    "stats.low": "Låg nivå",
    "stats.objectStatus": "Objektstatus",
    "stats.monthlyLoans": "Lånade per månad",
    "checkout.missingUser": "Saknas användaren?",
    "checkout.createUser": "Skapa användare",
    "checkout.searchUser": "Sök användare",
    "checkout.searchObject": "Sök objekt",
    "checkout.stockFilter": "Lagerfilter",
    "checkout.inStock": "I lager",
    "checkout.lowStock": "Låg nivå",
    "checkout.outOfStock": "Slut",
    "checkout.allObjects": "Alla objekt",
    "field.company": "Företag",
    "field.group": "Grupp",
    "field.department": "Avdelning",
    "field.email": "E-post",
    "field.phone": "Telefon",
    "field.alias": "Alias",
    "field.article": "Artikel",
    "field.comment": "Kommentar",
    "field.firstName": "Förnamn",
    "field.lastName": "Efternamn",
    "field.name": "Namn",
    "field.instrumentId": "Instrument ID",
    "field.category": "Kategori",
    "field.type": "Typ",
    "field.description": "Beteckning",
    "field.location": "Plats",
    "field.lift": "Hiss",
    "field.stockQty": "Antal i lager",
    "field.status": "Status",
    "field.engineId": "Engine ID",
    "field.projectNumber": "Project Number",
    "field.quantity": "Antal",
    "field.total": "Totalt antal",
    "field.lendingDate": "Lending date",
    "field.returnDate": "Return date",
    "action.borrow": "Låna",
    "action.requestLoan": "Skicka låneförfrågan",
    "action.return": "Lämna tillbaka",
    "action.issue": "Checka ut utan retur",
    "action.book": "Boka",
    "action.saveObject": "Spara objekt",
    "action.cancel": "Avbryt",
    "action.print": "Skriv ut/PDF",
    "action.exportExcel": "Export Excel",
    "return.activeLoan": "Aktivt lån",
    "return.placeholder": "Objekt-ID eller lån-ID",
    "book.title": "Bokning",
    "book.help": "Välj datum du vill boka prylen",
    "book.start": "Startdatum",
    "book.end": "Slutdatum",
    "objects.searchPlaceholder": "Sök på objekt, artikelnummer, leverantörsartikel, sökord eller plats",
    "admin.addObject": "Lägg till objekt",
    "admin.createUser": "Skapa användare",
    "admin.users": "Användare",
    "admin.activeUser": "Aktiv användare",
    "admin.image": "Bild",
    "admin.chooseImage": "Välj en bild på objektet. Den sparas lokalt i SQLite.",
    "admin.noImage": "Ingen bild vald",
    "admin.removeImage": "Ta bort befintlig bild",
    "modal.createAndSelect": "Skapa och välj användare",
    "search.placeholder": "Sök efter tryckgivare, artikelnummer, plats...",
    "search.close": "Stäng",
    "search.clearLabel": "Rensa sökning",
    "search.results": "Sökresultat",
    "search.all": "Alla",
    "search.objects": "Objekt",
    "search.loans": "Lån",
    "search.log": "Logg",
    "search.empty": "Skriv något för att söka i inventariet.",
    "search.noResults": "Inga objekt matchade sökningen.",
    "table.loanId": "Lån-ID",
    "table.object": "Objekt",
    "table.borrower": "Borrower",
    "table.deptNo": "Dept no",
    "table.projectNo": "Project no",
    "table.receipt": "Kvitto",
    "table.jobId": "Jobb-ID",
    "table.action": "Åtgärd",
    "jobs.nextPrepared": "Förbered",
    "jobs.nextLoaned": "Markera lånad",
    "jobs.nextReturned": "Markerad inlämnad",
    "jobs.nextStocked": "Lagerförd",
    "jobs.status.requested": "Request",
    "jobs.status.prepared": "Ready for pickup",
    "jobs.status.loaned": "Lånad",
    "jobs.status.returned": "Återlämnad",
    "jobs.status.stocked": "Lagerförd",
    "jobs.empty": "Inga jobb i detta fält.",
    "toast.requestCreated": "Låneförfrågan {id} skapades.",
    "toast.jobUpdated": "Jobb {id} uppdaterades.",
    "table.image": "Bild",
    "table.article": "Volvoid/Artikelnummer",
    "table.supplierArticle": "Leverantörens art.",
    "table.balance": "Saldo",
    "table.reorderPoint": "Beställningspunkt",
    "table.storage": "Lagerplats",
    "table.store": "Förråd",
    "table.belongsInstrument": "Tillhör instrument",
    "table.belongsTo": "Tillhör",
    "table.lastChanged": "Senast ändrad",
    "table.keywords": "Sök ord",
    "table.trayFor": "Ligger på bricka för",
    "table.storage2": "Lagerplats 2",
    "table.liftTray": "Hissbricka",
    "table.time": "Tid",
    "table.eventType": "Typ",
    "table.message": "Meddelande",
    "toast.chooseDates": "Välj startdatum och slutdatum.",
    "toast.bookingMissing": "Bokningsfunktionen är inte kopplad ännu.",
    "toast.noReceiptLoan": "Kunde inte hitta lånet för utskrift.",
    "toast.chooseUser": "Välj en användare från sökresultatet eller skapa en ny.",
    "toast.loanCreated": "Lån {id} skapades.",
    "toast.loanReturned": "Lån {id} är återlämnat.",
    "toast.issued": "Objekt {id} checkades ut utan retur.",
    "toast.userCreated": "Användare {id} skapades.",
    "toast.objectSaved": "Objekt {id} sparades.",
    "toast.objectDeleted": "Objekt {id} togs bort.",
    "error.backendJson": "Backend svarade inte med JSON. Starta om Python-servern och uppdatera sidan.",
    "error.unknown": "Okänt fel",
    "status.available": "Tillgänglig",
    "status.low": "Låg nivå",
    "status.out": "Slut",
    "status.active": "Aktiv",
    "status.late": "Sen",
    "stock.count": "{count} i lager",
  },
  en: {
    "brand.subtitle": "Loans and inventory",
    "sidebar.footer": "Local HTML prototype",
    "nav.dashboard": "Dashboard",
    "nav.checkout": "Borrow",
    "nav.return": "Return",
    "nav.issue": "Issue",
    "nav.book": "Book",
    "nav.objects": "Objects",
    "nav.statistics": "Statistics",
    "nav.jobs": "Jobs",
    "nav.loans": "Active loans",
    "nav.admin": "Admin",
    "nav.log": "Log",
    "nav.system": "System",
    "topbar.search": "Search",
    "topbar.role": "Role",
    "role.operator": "Operator",
    "role.admin": "Admin",
    "role.superadmin": "SuperAdmin",
    "dashboard.borrow": "Borrow",
    "dashboard.borrow.desc": "Create a loan with a return date.",
    "dashboard.kicker": "Workflow",
    "dashboard.title": "Loans and consumables",
    "dashboard.text": "Send loan requests, follow jobs and report articles that need replenishment.",
    "dashboard.newRequest": "New loan request",
    "dashboard.showJobs": "Show jobs",
    "dashboard.reportConsumable": "Report empty consumable",
    "dashboard.openReports": "Open consumable reports",
    "dashboard.return": "Return",
    "dashboard.return.desc": "Close an active loan.",
    "dashboard.issue": "Issue",
    "dashboard.issue.desc": "Issue consumables without return.",
    "dashboard.book": "Book",
    "dashboard.book.desc": "Book a future loan.",
    "stats.objects": "Objects",
    "stats.loaned": "Loaned objects",
    "stats.overdue": "Overdue loans",
    "stats.low": "Low stock",
    "stats.objectStatus": "Object status",
    "stats.monthlyLoans": "Loans per month",
    "checkout.missingUser": "Missing user?",
    "checkout.createUser": "Create user",
    "checkout.searchUser": "Search user",
    "checkout.searchObject": "Search object",
    "checkout.stockFilter": "Stock filter",
    "checkout.inStock": "In stock",
    "checkout.lowStock": "Low stock",
    "checkout.outOfStock": "Out of stock",
    "checkout.allObjects": "All objects",
    "field.company": "Company",
    "field.group": "Group",
    "field.department": "Department",
    "field.email": "Email",
    "field.phone": "Phone",
    "field.alias": "Alias",
    "field.article": "Article",
    "field.comment": "Comment",
    "field.firstName": "First name",
    "field.lastName": "Last name",
    "field.name": "Name",
    "field.instrumentId": "Instrument ID",
    "field.category": "Category",
    "field.type": "Type",
    "field.description": "Description",
    "field.location": "Location",
    "field.lift": "Lift",
    "field.stockQty": "Quantity in stock",
    "field.status": "Status",
    "field.engineId": "Engine ID",
    "field.projectNumber": "Project Number",
    "field.quantity": "Quantity",
    "field.total": "Total quantity",
    "field.lendingDate": "Lending date",
    "field.returnDate": "Return date",
    "action.borrow": "Borrow",
    "action.requestLoan": "Send loan request",
    "action.return": "Return",
    "action.issue": "Issue without return",
    "action.book": "Book",
    "action.saveObject": "Save object",
    "action.cancel": "Cancel",
    "action.print": "Print/PDF",
    "action.exportExcel": "Export Excel",
    "return.activeLoan": "Active loan",
    "return.placeholder": "Object ID or loan ID",
    "book.title": "Booking",
    "book.help": "Choose dates for the booking",
    "book.start": "Start date",
    "book.end": "End date",
    "objects.searchPlaceholder": "Search objects, article numbers, supplier articles, keywords or location",
    "admin.addObject": "Add object",
    "admin.createUser": "Create user",
    "admin.users": "Users",
    "admin.activeUser": "Active user",
    "admin.image": "Image",
    "admin.chooseImage": "Choose an object image. It is stored locally in SQLite.",
    "admin.noImage": "No image selected",
    "admin.removeImage": "Remove existing image",
    "modal.createAndSelect": "Create and select user",
    "search.placeholder": "Search pressure sensor, article number, location...",
    "search.close": "Close",
    "search.clearLabel": "Clear search",
    "search.results": "Search results",
    "search.all": "All",
    "search.objects": "Objects",
    "search.loans": "Loans",
    "search.log": "Log",
    "search.empty": "Type something to search the inventory.",
    "search.noResults": "No objects matched the search.",
    "table.loanId": "Loan ID",
    "table.object": "Object",
    "table.borrower": "Borrower",
    "table.deptNo": "Dept no",
    "table.projectNo": "Project no",
    "table.receipt": "Receipt",
    "table.jobId": "Job ID",
    "table.action": "Action",
    "jobs.nextPrepared": "Prepare",
    "jobs.nextLoaned": "Mark loaned",
    "jobs.nextReturned": "Mark returned",
    "jobs.nextStocked": "Stocked",
    "jobs.status.requested": "Request",
    "jobs.status.prepared": "Ready for pickup",
    "jobs.status.loaned": "Loaned",
    "jobs.status.returned": "Returned",
    "jobs.status.stocked": "Stocked",
    "jobs.empty": "No jobs in this field.",
    "toast.requestCreated": "Loan request {id} was created.",
    "toast.jobUpdated": "Job {id} was updated.",
    "table.image": "Image",
    "table.article": "Volvo ID/Article no.",
    "table.supplierArticle": "Supplier article",
    "table.balance": "Balance",
    "table.reorderPoint": "Reorder point",
    "table.storage": "Storage location",
    "table.store": "Store",
    "table.belongsInstrument": "Belongs to instrument",
    "table.belongsTo": "Belongs to",
    "table.lastChanged": "Last changed",
    "table.keywords": "Search words",
    "table.trayFor": "Tray for",
    "table.storage2": "Storage location 2",
    "table.liftTray": "Lift tray",
    "table.time": "Time",
    "table.eventType": "Type",
    "table.message": "Message",
    "toast.chooseDates": "Choose start date and end date.",
    "toast.bookingMissing": "The booking function is not connected yet.",
    "toast.noReceiptLoan": "Could not find the loan for printing.",
    "toast.chooseUser": "Choose a user from the search results or create a new one.",
    "toast.loanCreated": "Loan {id} was created.",
    "toast.loanReturned": "Loan {id} was returned.",
    "toast.issued": "Object {id} was issued without return.",
    "toast.userCreated": "User {id} was created.",
    "toast.objectSaved": "Object {id} was saved.",
    "toast.objectDeleted": "Object {id} was deleted.",
    "error.backendJson": "Backend did not return JSON. Restart the Python server and refresh the page.",
    "error.unknown": "Unknown error",
    "status.available": "Available",
    "status.low": "Low stock",
    "status.out": "Out of stock",
    "status.active": "Active",
    "status.late": "Overdue",
    "stock.count": "{count} in stock",
  },
};

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
  document.documentElement.lang = state.language;
  document.querySelectorAll(".language-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.language === state.language);
  });

  setText(".brand-subtitle", "brand.subtitle");
  setText(".sidebar-footer", "sidebar.footer");
  document.querySelectorAll(".nav-button").forEach((button) => {
    setText(`.nav-button[data-view="${button.dataset.view}"]`, viewTitles[button.dataset.view]);
  });
  setText("#openSearchButton", "topbar.search");
  setLabel("roleSelect", "topbar.role");
  setOptionText("roleSelect", "operator", "role.operator");
  setOptionText("roleSelect", "admin", "role.admin");
  setOptionText("roleSelect", "superadmin", "role.superadmin");
  setOptionText("newUserRole", "operator", "role.operator");
  setOptionText("newUserRole", "admin", "role.admin");
  setOptionText("newUserRole", "superadmin", "role.superadmin");

  setText("#dashboardView h1", "nav.dashboard");

  setText("#statisticsView h1", "nav.statistics");
  setText(".stat-card:nth-of-type(1) span", "stats.objects");
  setText(".stat-card:nth-of-type(2) span", "stats.loaned");
  setText(".stat-card:nth-of-type(3) span", "stats.overdue");
  setText(".stat-card:nth-of-type(4) span", "stats.low");
  setText(".chart-container:nth-of-type(1) .chart-title", "stats.objectStatus");
  setText(".chart-container:nth-of-type(2) .chart-title", "stats.monthlyLoans");

  setText("#checkoutView h1", "nav.checkout");
  setText(".checkout-action-row span", "checkout.missingUser");
  setText("#openQuickUserButton", "checkout.createUser");
  setLabel("checkoutUserSearch", "checkout.searchUser");
  setPlaceholder("#checkoutUserSearch", "checkout.searchUser");
  setLabel("checkoutObjectId", "checkout.searchObject");
  setPlaceholder("#checkoutObjectId", "checkout.searchObject");
  setLabel("checkoutStockFilter", "checkout.stockFilter");
  setOptionText("checkoutStockFilter", "in_stock", "checkout.inStock");
  setOptionText("checkoutStockFilter", "low_stock", "checkout.lowStock");
  setOptionText("checkoutStockFilter", "out_of_stock", "checkout.outOfStock");
  setOptionText("checkoutStockFilter", "all", "checkout.allObjects");
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
    ["checkoutObjectQuantity", "field.stockQty"],
    ["checkoutObjectStatus", "field.status"],
    ["checkoutEngineId", "field.engineId"],
    ["checkoutProjectNumber", "field.projectNumber"],
    ["checkoutQuantity", "field.quantity"],
    ["checkoutLendingDate", "field.lendingDate"],
    ["checkoutDue", "field.returnDate"],
    ["consumableObjectSearch", "field.article"],
    ["consumableQuantity", "field.quantity"],
    ["consumableReportedBy", "table.borrower"],
    ["consumableMessage", "field.comment"],
    ["returnUserSearch", "nav.return"],
    ["newUserFirstName", "field.firstName"],
    ["newUserLastName", "field.lastName"],
    ["newUserEmail", "field.email"],
    ["newUserPhone", "field.phone"],
    ["newUserCompany", "field.company"],
    ["newUserAlias", "field.alias"],
    ["newUserDepartment", "field.department"],
    ["newUserDepartmentName", "field.group"],
    ["newUserRole", "topbar.role"],
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
  setPlaceholder("#returnUserSearch", "checkout.searchUser");
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

  $("#topbarTitle").textContent = t(viewTitles[document.querySelector(".nav-button.active")?.dataset.view || "dashboard"]);
}

// ============================================================
// API
// Alla anrop till backend samlas har.
// ============================================================

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error(t("error.backendJson"));
  }

  const payload = await response.json();
  if (!payload.ok) {
    throw new Error(payload.error || t("error.unknown"));
  }
  return payload.data;
}

async function searchApi(term) {
  return api(`/api/search?q=${encodeURIComponent(term)}&limit=9`);
}

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
  $("#topbarTitle").textContent = t(viewTitles[view]);

  if (view === "statistics") {
  renderStatusChart(state);
  renderLoansPerMonthChart(state);
}
}

async function refreshAll() {
  const [stats, objects, users, loans, jobs, consumableReports, events, systemSettings] = await Promise.all([
    api("/api/stats"),
    api("/api/objects"),
    api("/api/users"),
    api("/api/loans"),
    api("/api/loan-requests"),
    api("/api/consumable-reports"),
    api("/api/events?limit=100"),
    api("/api/system-settings"),
  ]);

  state.objects = objects;
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
  renderDashboardLoans();
  renderDashboardGuide();
  renderJobs();
  renderConsumableReports();
  renderEvents();
  renderSystemSettings();
  showAdminSettingsSection(document.querySelector(".admin-settings-nav-button.active")?.dataset.adminSection || "add-object");
  applyRole();
  updateCheckoutInfo();
  renderReturnLoans();
  applyTranslations();
  if (document.querySelector("#statisticsView.active")) {
    renderStatusChart(state);
    renderLoansPerMonthChart(state);
  }

}

// ============================================================
// RENDERING
// Funktioner som skriver ut data till HTML.
// ============================================================

function renderStats(stats) {
  $("#objectsStat").textContent = stats.objects;
  $("#loanedStat").textContent = stats.loaned;
  $("#overdueStat").textContent = stats.overdue;
  $("#lowStockStat").textContent = stats.low_stock;
}

function renderSystemSettings() {
  if (!$("#systemSettingsForm")) return;
  const settings = state.systemSettings || {};
  $("#modbusEnabled").checked = settings.modbus_enabled === "1";
  $("#modbusHost").value = settings.modbus_host || "";
  $("#modbusPort").value = settings.modbus_port || "502";
  $("#modbusUnitId").value = settings.modbus_unit_id || "1";
  $("#modbusRegisterStart").value = settings.modbus_register_start || "";
  $("#smtpEnabled").checked = settings.smtp_enabled === "1";
  $("#smtpHost").value = settings.smtp_host || "";
  $("#smtpPort").value = settings.smtp_port || "587";
  $("#smtpUsername").value = settings.smtp_username || "";
  $("#smtpPassword").value = "";
  $("#smtpFromAddress").value = settings.smtp_from_address || "";
  $("#smtpUseTls").checked = settings.smtp_use_tls !== "0";
  $("#notificationRecipients").value = settings.notification_recipients || "";
  $("#loanReminderDays").value = settings.loan_reminder_days || "1";
  $("#notifyNewJob").checked = settings.notify_new_job !== "0";
  $("#notifyLowStock").checked = settings.notify_low_stock !== "0";
  $("#notifyLoanReminders").checked = settings.notify_loan_reminders !== "0";
  $("#notifyNewJobAutomation").checked = settings.notify_new_job !== "0";
  $("#notifyLowStockAutomation").checked = settings.notify_low_stock !== "0";
  $("#smtpSummary").textContent = settings.smtp_enabled === "1" ? "Ja" : "Nej";
  $("#modbusSummary").textContent = settings.modbus_enabled === "1" ? "Ja" : "Nej";
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
  const issueSelect = $("#issueUser");
  if (!issueSelect) {
    renderDepartmentNames();
    renderUsersTable();
    return;
  }
  const currentIssueUser = issueSelect.value;
  const options = state.users
    .map((user) => `<option value="${escapeHtml(user.user_id)}">${escapeHtml(user.name)} (${escapeHtml(user.department || "")})</option>`)
    .join("");
  issueSelect.innerHTML = options;
  if (currentIssueUser) issueSelect.value = currentIssueUser;
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

  $("#objectsBody").innerHTML = filtered.map((item) => `
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
  body.innerHTML = state.objects.map((item) => `
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

  const matches = state.objects
    .filter((item) => matchesCheckoutStockFilter(item) && objectSearchText(item).includes(term))
    .sort((a, b) => b.available_quantity - a.available_quantity || a.name.localeCompare(b.name))
    .slice(0, 8);
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
  const matches = state.objects.filter((item) => objectSearchText(item).includes(term)).slice(0, 8);
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

function handleBookButtonClick() {
  const start = $("#startDate").value;
  const end = $("#endDate").value;

  if (!start || !end) {
    showToast(t("toast.chooseDates"));
    return;
  }

  if (typeof boka !== "function") {
    showToast(t("toast.bookingMissing"));
    return;
  }

  boka(start, end);
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

function renderDashboardLoans() {
  const list = $("#dashboardLoansList");
  if (!list) return;
  if (!state.loans.length) {
    list.innerHTML = `<div class="job-empty">${state.language === "en" ? "No active loans." : "Inga aktiva utlåningar."}</div>`;
    return;
  }
  list.innerHTML = state.loans.slice(0, 5).map((loan) => `
    <article class="dashboard-loan-card ${loan.overdue ? "late" : ""}">
      <div>
        <strong>${escapeHtml(loan.object_name)}</strong>
        <span>#${loan.loan_id} · ${escapeHtml(loan.user_name)}</span>
      </div>
      <div>
        <span>${escapeHtml(formatTime(loan.due_time))}</span>
        ${statusBadge(loan.overdue ? "Sen" : "Aktiv")}
      </div>
    </article>
  `).join("");
}

function renderDashboardGuide() {
  const track = $("#dashboardGuideTrack");
  const dots = $("#dashboardGuideDots");
  if (!track || !dots) return;
  const slides = [...track.querySelectorAll(".dashboard-guide-slide")];
  track.style.transform = `translateX(-${state.dashboardGuideIndex * 100}%)`;
  dots.innerHTML = slides.map((_, index) => `
    <button class="dashboard-guide-dot ${index === state.dashboardGuideIndex ? "active" : ""}" type="button" data-guide-index="${index}" aria-label="Visa steg ${index + 1}"></button>
  `).join("");
  dots.querySelectorAll("[data-guide-index]").forEach((button) => {
    button.addEventListener("click", () => {
      state.dashboardGuideIndex = Number(button.dataset.guideIndex);
      renderDashboardGuide();
    });
  });
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
  document.querySelectorAll("[data-open-job-id]").forEach((card) => {
    card.addEventListener("click", (event) => {
      if (event.target.closest("button, summary, details")) return;
      openJobDetail(Number(card.dataset.openJobId));
    });
  });
  bindJobDragAndDrop();
}

function getFilteredJobs() {
  const term = $("#jobSearch")?.value.trim().toLowerCase() || "";
  const statusFilter = $("#jobStatusFilter")?.value || "all";
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
    return (!term || searchable.includes(term)) &&
      (statusFilter === "all" || job.status === statusFilter);
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
        <dt>${escapeHtml(t("field.quantity"))}</dt><dd>${escapeHtml(report.quantity ?? "")}</dd>
        <dt>${state.language === "en" ? "Reported by" : "Rapporterad av"}</dt><dd>${escapeHtml(report.reported_by || "")}</dd>
        <dt>${state.language === "en" ? "Comment" : "Kommentar"}</dt><dd>${escapeHtml(report.message || "")}</dd>
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
      ${action ? `<button class="table-action-button" type="button" data-job-id="${job.request_id}" data-job-status="${action[0]}">${t(action[1])}</button>` : ""}
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
  const dashboardEventsBody = $("#dashboardEventsBody");
  if (dashboardEventsBody) {
    dashboardEventsBody.innerHTML = state.events.slice(0, 8).map((event) => `
      <tr>
        <td>${formatTime(event.event_time)}</td>
        <td>${escapeHtml(event.event_type)}</td>
        <td>${escapeHtml(event.message)}</td>
      </tr>
    `).join("");
  }
}

// ============================================================
// SOK
// Global sokpanel och sokresultat.
// ============================================================

async function performSearch() {
  const term = $("#globalSearchInput").value.trim();
  $("#searchTitle").textContent = term ? `Sökresultat för "${term}"` : "Sökresultat";
  if (!term) {
    renderSearchResults([]);
    $("#searchEmpty").textContent = "Skriv något för att söka i inventariet.";
    $("#searchEmpty").classList.add("visible");
    return;
  }

  try {
    const results = await searchApi(term);
    renderSearchResults(results);
  } catch (error) {
    showToast(error.message);
  }
}

function renderSearchResults(results) {
  $("#allResultsTab").textContent = `${t("search.all")} (${results.length})`;
  $("#objectResultsTab").textContent = `${t("search.objects")} (${results.length})`;
  $("#searchResultsGrid").innerHTML = results.map((item) => `
    <article class="search-card">
      <div class="search-card-visual">${item.image_data ? `<img src="${escapeHtml(item.image_data)}" alt="">` : escapeHtml(item.category)}</div>
      <div class="search-card-body">
        <div class="search-card-title">${escapeHtml(item.name)}</div>
        <div class="search-card-meta">${escapeHtml(item.article_number || item.object_id)} ${item.supplier_article_number ? `· ${escapeHtml(item.supplier_article_number)}` : ""}</div>
        <div class="search-card-meta">${escapeHtml(item.location)} · Hissbricka ${escapeHtml(item.lift_tray || item.door_id)}</div>
      </div>
      <div class="search-card-footer">
        ${statusBadge(item.status)}
        <button class="search-card-action" type="button" data-object-id="${escapeHtml(item.object_id)}">Låna</button>
      </div>
    </article>
  `).join("");

  $("#searchEmpty").textContent = t("search.noResults");
  $("#searchEmpty").classList.toggle("visible", results.length === 0);

  document.querySelectorAll(".search-card-action").forEach((button) => {
    button.addEventListener("click", () => {
      $("#checkoutObjectId").value = button.dataset.objectId;
      closeSearch();
      setView("checkout");
      updateCheckoutInfo();
    });
  });
}

function openSearch() {
  $("#searchLayer").classList.add("open");
  $("#searchLayer").setAttribute("aria-hidden", "false");
  $("#globalSearchInput").focus();
  performSearch();
}

function closeSearch() {
  $("#searchLayer").classList.remove("open");
  $("#searchLayer").setAttribute("aria-hidden", "true");
}

// ============================================================
// FORMULARINFORMATION
// Uppdaterar informationsrutor nar anvandaren skriver i formular.
// ============================================================

function updateCheckoutInfo(selectedItem = null) {
  const objectId = $("#checkoutObjectId").value.trim();
  const term = objectId.toLowerCase();
  const item = selectedItem || state.objects.find((objectItem) =>
    objectItem.object_id.toLowerCase() === term || objectItem.name.toLowerCase() === term
  );
  const details = $("#checkoutInfo");
  if (!item) {
    [
      "InstrumentId",
      "Name",
      "Category",
      "Type",
      "Description",
      "Location",
      "Lift",
      "Quantity",
      "Status",
    ].forEach((field) => {
      const input = $(`#checkoutObject${field}`);
      if (input) input.value = "";
    });
    return;
  }
  $("#checkoutObjectInstrumentId").value = item.object_id || "";
  $("#checkoutObjectName").value = item.name || "";
  $("#checkoutObjectCategory").value = item.category || "";
  $("#checkoutObjectType").value = item.item_type || "";
  $("#checkoutObjectDescription").value = item.description || "";
  $("#checkoutObjectLocation").value = item.location || "";
  $("#checkoutObjectLift").value = item.lift_tray || item.door_id || "";
  $("#checkoutObjectQuantity").value = state.language === "en" ? `${item.available_quantity} of ${item.total_quantity}` : `${item.available_quantity} av ${item.total_quantity}`;
  $("#checkoutObjectStatus").value = statusText(item.status || "");
}

function updateReturnInfo() {
  const identifier = $("#returnIdentifier").value.trim().toLowerCase();
  const loan = state.loans.find((item) => String(item.loan_id) === identifier || item.object_id.toLowerCase() === identifier);
  if (!loan) {
    $("#returnInfo").innerHTML = "<h2>Aktivt lån</h2><dl><dt>Status</dt><dd>Inget aktivt lån hittat.</dd></dl>";
    return;
  }
  $("#returnInfo").innerHTML = `
    <h2>Aktivt lån</h2>
    <dl>
      <dt>Lån-ID</dt><dd>${loan.loan_id}</dd>
      <dt>Instrument ID</dt><dd>${escapeHtml(loan.object_id)}</dd>
      <dt>Objekt</dt><dd>${escapeHtml(loan.object_name)} (${escapeHtml(loan.object_id)})</dd>
      <dt>Användare</dt><dd>${escapeHtml(loan.user_name)}</dd>
      <dt>Dept no</dt><dd>${escapeHtml(loan.user_department || "")}</dd>
      <dt>Engine ID</dt><dd>${escapeHtml(loan.engine_id || "")}</dd>
      <dt>Project no</dt><dd>${escapeHtml(loan.project_number || "")}</dd>
      <dt>Antal</dt><dd>${loan.quantity}</dd>
      <dt>Lending date</dt><dd>${formatTime(loan.checkout_time)}</dd>
      <dt>Returdatum</dt><dd>${formatTime(loan.due_time)}</dd>
      <dt>Status</dt><dd>${statusBadge(loan.overdue ? "Sen" : "Aktiv")}</dd>
    </dl>
  `;
}

function renderReturnLoans() {
  const body = $("#returnLoansBody");
  if (!body) return;
  const selectedUserId = $("#returnUser")?.value || "";
  const empty = $("#returnLoansEmpty");
  const matches = selectedUserId
    ? state.loans.filter((loan) => loan.user_id === selectedUserId)
    : [];

  body.innerHTML = matches.map((loan) => `
    <tr class="${loan.overdue ? "late" : ""}">
      <td>${loan.loan_id}</td>
      <td>${escapeHtml(loan.object_name)} (${escapeHtml(loan.object_id)})</td>
      <td>${escapeHtml(loan.user_name)}</td>
      <td>${escapeHtml(loan.user_department || "")}</td>
      <td>${escapeHtml(loan.engine_id || "")}</td>
      <td>${escapeHtml(loan.project_number || "")}</td>
      <td>${loan.quantity}</td>
      <td>${formatTime(loan.checkout_time)}</td>
      <td>${formatTime(loan.due_time)}</td>
      <td>${statusBadge(loan.overdue ? "Sen" : "Aktiv")}</td>
      <td><button class="primary-button table-return-button" type="button" data-return-loan="${loan.loan_id}">Återlämna</button></td>
    </tr>
  `).join("");

  document.querySelectorAll("[data-return-loan]").forEach((button) => {
    button.addEventListener("click", () => returnItem(Number(button.dataset.returnLoan)));
  });

  if (empty) {
    empty.textContent = selectedUserId
      ? matches.length
        ? ""
        : "Den valda användaren har inga aktiva utlåningar."
      : "Välj en användare för att se aktiva utlåningar.";
  }
}

function renderReturnUserSuggestions() {
  const term = $("#returnUserSearch").value.trim().toLowerCase();
  const suggestions = $("#returnUserSuggestions");
  $("#returnUser").value = "";
  renderReturnLoans();
  if (!term) {
    suggestions.classList.remove("visible");
    suggestions.innerHTML = "";
    return;
  }

  const labels = userLabels();
  const matches = state.users.filter((user) => userSearchText(user).includes(term)).slice(0, 8);
  suggestions.innerHTML = matches.map((user) => `
    <button class="suggestion-button" type="button" data-select-return-user="${escapeHtml(user.user_id)}">
      <strong>${escapeHtml(labels.get(user.user_id) || user.name)}</strong>
      <span>${escapeHtml([user.company, user.department_name || user.department, user.alias].filter(Boolean).join(" · "))}</span>
    </button>
  `).join("");
  suggestions.classList.toggle("visible", matches.length > 0);
  document.querySelectorAll("[data-select-return-user]").forEach((button) => {
    button.addEventListener("click", () => selectReturnUser(button.dataset.selectReturnUser));
  });
}

function selectReturnUser(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  if (!user) return;
  const labels = userLabels();
  $("#returnUser").value = user.user_id;
  $("#returnUserSearch").value = labels.get(user.user_id) || user.name;
  $("#returnUserSuggestions").classList.remove("visible");
  renderReturnLoans();
}

function updateIssueInfo() {
  const objectId = $("#issueObjectId").value.trim();
  const item = state.objects.find((objectItem) => objectItem.object_id.toLowerCase() === objectId.toLowerCase());
  if (!item) {
    $("#issueInfo").innerHTML = "<h2>Objektinformation</h2><dl><dt>Status</dt><dd>Inget objekt valt eller hittat.</dd></dl>";
    return;
  }
  $("#issueInfo").innerHTML = `
    <h2>Objektinformation</h2>
    <dl>
      <dt>Namn</dt><dd>${escapeHtml(item.name)}</dd>
      <dt>Typ</dt><dd>${escapeHtml(item.item_type || "")}</dd>
      <dt>Beteckning</dt><dd>${escapeHtml(item.description || "")}</dd>
      <dt>Plats</dt><dd>${escapeHtml(item.location)}</dd>
      <dt>Tornado</dt><dd>${escapeHtml(item.tornado_id)}</dd>
      <dt>Hissbricka</dt><dd>${escapeHtml(item.lift_tray || item.door_id)}</dd>
      <dt>Tillgängligt</dt><dd>${item.available_quantity} av ${item.total_quantity}</dd>
      <dt>Status</dt><dd>${statusBadge(item.status)}</dd>
    </dl>
  `;
}

function printLoanReceipt(loanId) {
  const loan = state.loans.find((item) => item.loan_id === loanId);
  if (!loan) {
    showToast(t("toast.noReceiptLoan"));
    return;
  }
  const receipt = $("#printReceipt");
  receipt.innerHTML = `
    <div class="receipt-page">
      <header class="receipt-header">
        <div>
          <h1>Loan receipt</h1>
          <p>Volvo Penta tool and instrument lending</p>
        </div>
        <div class="receipt-id">Loan ID ${loan.loan_id}</div>
      </header>
      <dl class="receipt-grid">
        <dt>Instrument ID</dt><dd>${escapeHtml(loan.object_id)}</dd>
        <dt>Instrument name</dt><dd>${escapeHtml(loan.object_name)}</dd>
        <dt>Engine ID</dt><dd>${escapeHtml(loan.engine_id || "")}</dd>
        <dt>Project Number</dt><dd>${escapeHtml(loan.project_number || "")}</dd>
        <dt>Name of borrower</dt><dd>${escapeHtml(loan.user_name)}</dd>
        <dt>Dept no</dt><dd>${escapeHtml(loan.user_department || "")}</dd>
        <dt>Quantity</dt><dd>${loan.quantity}</dd>
        <dt>Lending date</dt><dd>${formatTime(loan.checkout_time)}</dd>
        <dt>Return date</dt><dd>${formatTime(loan.due_time)}</dd>
        <dt>Status</dt><dd>${loan.overdue ? "Overdue" : "Active"}</dd>
      </dl>
      <div class="receipt-signatures">
        <div><span></span><p>Borrower signature</p></div>
        <div><span></span><p>Returned/received by</p></div>
      </div>
    </div>
  `;
  window.print();
}

// ============================================================
// HANDLINGAR
// Funktioner som skapar, uppdaterar eller tar bort data via API.
// ============================================================

async function checkout() {
  try {
    const userId = resolveCheckoutUserId();
    if (!userId) {
      showToast(t("toast.chooseUser"));
      return;
    }
    const data = await api("/api/checkout", {
      method: "POST",
      body: JSON.stringify(checkoutPayload(userId)),
    });
    showToast(t("toast.loanCreated", { id: data.loan_id }));
    clearCheckoutForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

function checkoutPayload(userId) {
  return {
    object_id: $("#checkoutObjectInstrumentId").value || $("#checkoutObjectId").value,
    user_id: userId,
    quantity: Number($("#checkoutQuantity").value),
    lending_date: $("#checkoutLendingDate").value,
    due_time: $("#checkoutDue").value,
    engine_id: $("#checkoutEngineId").value,
    project_number: $("#checkoutProjectNumber").value,
  };
}

function clearCheckoutForm() {
  $("#checkoutObjectId").value = "";
  updateCheckoutInfo();
  $("#checkoutUser").value = "";
  $("#checkoutUserSearch").value = "";
  renderCheckoutUserDetails();
  $("#checkoutEngineId").value = "";
  $("#checkoutProjectNumber").value = "";
  $("#checkoutQuantity").value = "1";
  setDefaultDates();
}

async function requestLoan() {
  try {
    const userId = resolveCheckoutUserId();
    if (!userId) {
      showToast(t("toast.chooseUser"));
      return;
    }
    const data = await api("/api/loan-requests", {
      method: "POST",
      body: JSON.stringify(checkoutPayload(userId)),
    });
    showToast(t("toast.requestCreated", { id: data.request_id }));
    clearCheckoutForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function saveConsumableReport(event) {
  event.preventDefault();
  try {
    const objectId = resolveConsumableObjectId();
    const data = await api("/api/consumable-reports", {
      method: "POST",
      body: JSON.stringify({
        object_id: objectId,
        quantity: $("#consumableQuantity").value,
        reported_by: $("#consumableReportedBy").value,
        message: $("#consumableMessage").value,
      }),
    });
    showToast(state.language === "en" ? `Report ${data.report_id} was created.` : `Rapport ${data.report_id} skapades.`);
    $("#consumableReportForm").reset();
    $("#consumableObjectId").value = "";
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

function resolveConsumableObjectId() {
  const selected = $("#consumableObjectId").value;
  if (selected) return selected;
  const term = $("#consumableObjectSearch").value.trim().toLowerCase();
  const item = state.objects.find((objectItem) =>
    objectItem.object_id.toLowerCase() === term ||
    objectItem.name.toLowerCase() === term ||
    objectItem.article_number?.toLowerCase() === term ||
    objectItem.supplier_article_number?.toLowerCase() === term
  );
  return item ? item.object_id : $("#consumableObjectSearch").value;
}

async function closeConsumableReport(reportId) {
  try {
    await api("/api/consumable-reports", {
      method: "PUT",
      body: JSON.stringify({ report_id: reportId }),
    });
    showToast(state.language === "en" ? "Report marked handled." : "Rapport markerad åtgärdad.");
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function updateJobStatus(requestId, status) {
  try {
    const data = await api("/api/loan-requests", {
      method: "PUT",
      body: JSON.stringify({ request_id: requestId, status }),
    });
    showToast(t("toast.jobUpdated", { id: data.request_id }));
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function returnItem(loanId) {
  try {
    if (!loanId) {
      showToast("Välj ett aktivt lån att återlämna.");
      return;
    }
    const data = await api("/api/return", {
      method: "POST",
      body: JSON.stringify({ identifier: String(loanId) }),
    });
    showToast(t("toast.loanReturned", { id: data.loan_id }));
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function issueItem() {
  try {
    const data = await api("/api/issue", {
      method: "POST",
      body: JSON.stringify({
        object_id: $("#issueObjectId").value,
        user_id: $("#issueUser").value,
        quantity: Number($("#issueQuantity").value),
      }),
    });
    showToast(t("toast.issued", { id: data.object_id }));
    $("#issueObjectId").value = "";
    $("#issueQuantity").value = "1";
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function saveUser(event) {
  event.preventDefault();
  try {
    const payload = {
      first_name: $("#newUserFirstName").value,
      last_name: $("#newUserLastName").value,
      email: $("#newUserEmail").value,
      phone: $("#newUserPhone").value,
      company: $("#newUserCompany").value,
      alias: $("#newUserAlias").value,
      department: $("#newUserDepartment").value,
      department_name: $("#newUserDepartmentName").value,
      role: $("#newUserRole").value,
      active: $("#newUserActive").checked,
    };
    if (state.editingUserId) payload.user_id = state.editingUserId;

    const data = await api("/api/users", {
      method: state.editingUserId ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    showToast(state.editingUserId ? `Användare ${data.user_id} uppdaterades.` : t("toast.userCreated", { id: data.user_id }));
    resetUserForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

function startEditUser(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  if (!user) return;
  state.editingUserId = userId;
  $("#newUserFirstName").value = user.first_name || user.name?.split(" ")[0] || "";
  $("#newUserLastName").value = user.last_name || user.name?.split(" ").slice(1).join(" ") || "";
  $("#newUserEmail").value = user.email || "";
  $("#newUserPhone").value = user.phone || "";
  $("#newUserCompany").value = user.company || "";
  $("#newUserAlias").value = user.alias || "";
  $("#newUserDepartment").value = user.department || "";
  $("#newUserDepartmentName").value = user.department_name || "";
  $("#newUserRole").value = user.role || "operator";
  $("#newUserActive").checked = user.active !== 0;
  $("#saveUserButton").textContent = "Spara ändringar";
  $("#cancelUserEditButton").style.display = "block";
  showAdminSettingsSection("create-user");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetUserForm() {
  state.editingUserId = null;
  $("#addUserForm").reset();
  $("#newUserActive").checked = true;
  $("#saveUserButton").textContent = "Skapa användare";
  $("#cancelUserEditButton").style.display = "none";
}

async function removeUser(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  const name = user ? user.name : userId;
  if (!confirm(`Ta bort ${name} (${userId}) från aktiva användare?`)) return;
  try {
    await api(`/api/users?user_id=${encodeURIComponent(userId)}`, { method: "DELETE" });
    showToast(`Användare ${userId} togs bort.`);
    if (state.editingUserId === userId) resetUserForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function saveSystemSettings(event) {
  event.preventDefault();
  try {
    state.systemSettings = await api("/api/system-settings", {
      method: "PUT",
      body: JSON.stringify({
        modbus_enabled: $("#modbusEnabled").checked,
        modbus_host: $("#modbusHost").value,
        modbus_port: $("#modbusPort").value,
        modbus_unit_id: $("#modbusUnitId").value,
        modbus_register_start: $("#modbusRegisterStart").value,
        smtp_enabled: $("#smtpEnabled").checked,
        smtp_host: $("#smtpHost").value,
        smtp_port: $("#smtpPort").value,
        smtp_username: $("#smtpUsername").value,
        smtp_password: $("#smtpPassword").value,
        smtp_from_address: $("#smtpFromAddress").value,
        smtp_use_tls: $("#smtpUseTls").checked,
        notification_recipients: $("#notificationRecipients").value,
        loan_reminder_days: $("#loanReminderDays").value,
        notify_new_job: $("#notifyNewJob").checked || $("#notifyNewJobAutomation").checked,
        notify_low_stock: $("#notifyLowStock").checked || $("#notifyLowStockAutomation").checked,
        notify_loan_reminders: $("#notifyLoanReminders").checked,
      }),
    });
    renderSystemSettings();
    showToast("Systeminställningarna sparades.");
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function sendLoanReminders() {
  try {
    const data = await api("/api/reminders/send", { method: "POST", body: JSON.stringify({}) });
    showToast(`Påminnelser skickade: ${data.sent} av ${data.matched}.`);
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

function fillDepartmentFromDepartmentName(departmentNameSelector, departmentSelector) {
  const departmentName = $(departmentNameSelector).value.trim().toLowerCase();
  if (!departmentName) return;
  const match = state.users.find((user) => (user.department_name || "").toLowerCase() === departmentName);
  if (match?.department && !$(departmentSelector).value.trim()) {
    $(departmentSelector).value = match.department;
  }
}

async function saveQuickUser(event) {
  event.preventDefault();
  try {
    const data = await api("/api/users", {
      method: "POST",
      body: JSON.stringify({
        first_name: $("#quickUserFirstName").value,
        last_name: $("#quickUserLastName").value,
        email: $("#quickUserEmail").value,
        phone: $("#quickUserPhone").value,
        company: $("#quickUserCompany").value,
        alias: $("#quickUserAlias").value,
        department: $("#quickUserDepartment").value,
        department_name: $("#quickUserDepartmentName").value,
        role: "operator",
        active: true,
      }),
    });
    showToast(t("toast.userCreated", { id: data.user_id }));
    $("#quickUserForm").reset();
    closeQuickUserModal();
    await refreshAll();
    selectCheckoutUser(data.user_id);
  } catch (error) {
    showToast(error.message);
  }
}

function openQuickUserModal() {
  $("#quickUserModal").classList.add("open");
  $("#quickUserModal").setAttribute("aria-hidden", "false");
  $("#quickUserFirstName").focus();
}

function closeQuickUserModal() {
  $("#quickUserModal").classList.remove("open");
  $("#quickUserModal").setAttribute("aria-hidden", "true");
}

async function saveObject(event) {
  event.preventDefault();
  try {
    const imageData = await readSelectedObjectImage();
    const isEditing = Boolean(state.editingObjectId);
    const data = await api("/api/objects", {
      method: isEditing ? "PUT" : "POST",
      body: JSON.stringify({
        object_id: $("#newObjectId").value,
        name: $("#newObjectName").value,
        category: $("#newObjectCategory").value,
        item_type: $("#newObjectType").value,
        description: $("#newObjectDescription").value,
        article_number: $("#newObjectArticle").value,
        supplier_article_number: $("#newObjectSupplierArticle").value,
        location: $("#newObjectLocation").value,
        storage_location_2: $("#newObjectStorageLocation2").value,
        tornado_id: $("#newObjectTornado").value,
        door_id: $("#newObjectDoor").value,
        belongs_to_instrument: $("#newObjectBelongsToInstrument").value,
        device: $("#newObjectDevice").value,
        belongs_to: $("#newObjectBelongsTo").value,
        last_changed: $("#newObjectLastChanged").value,
        search_words: $("#newObjectSearchWords").value,
        tray_for: $("#newObjectTrayFor").value,
        lift_tray: $("#newObjectLiftTray").value,
        total_quantity: Number($("#newObjectTotal").value),
        available_quantity: Number($("#newObjectAvailable").value),
        min_quantity: Number($("#newObjectMin").value),
        image_data: imageData,
        remove_image: $("#removeObjectImage").checked,
      }),
    });
    showToast(t("toast.objectSaved", { id: data.object_id }));
    resetObjectForm();
    await refreshAll();
    setView("objects");
  } catch (error) {
    showToast(error.message);
  }
}

function startEditObject(objectId) {
  if (state.role === "operator") return;
  const item = state.objects.find((objectItem) => objectItem.object_id === objectId);
  if (!item) return;

  state.editingObjectId = objectId;
  $("#objectFormTitle").textContent = `Redigera objekt ${objectId}`;
  $("#saveObjectButton").textContent = "Spara ändringar";
  $("#cancelObjectEditButton").style.display = "block";
  $("#newObjectId").value = item.object_id;
  $("#newObjectId").readOnly = true;
  $("#newObjectName").value = item.name;
  $("#newObjectCategory").value = item.category;
  $("#newObjectType").value = item.item_type || "";
  $("#newObjectDescription").value = item.description || "";
  $("#newObjectArticle").value = item.article_number || "";
  $("#newObjectSupplierArticle").value = item.supplier_article_number || "";
  $("#newObjectLocation").value = item.location;
  $("#newObjectStorageLocation2").value = item.storage_location_2 || "";
  $("#newObjectTornado").value = item.tornado_id;
  $("#newObjectDoor").value = item.door_id;
  $("#newObjectBelongsToInstrument").value = item.belongs_to_instrument || "";
  $("#newObjectDevice").value = item.device || "";
  $("#newObjectBelongsTo").value = item.belongs_to || "";
  $("#newObjectLastChanged").value = item.last_changed || "";
  $("#newObjectSearchWords").value = item.search_words || "";
  $("#newObjectTrayFor").value = item.tray_for || "";
  $("#newObjectLiftTray").value = item.lift_tray || "";
  $("#newObjectTotal").value = item.total_quantity;
  $("#newObjectAvailable").value = item.available_quantity;
  $("#newObjectMin").value = item.min_quantity;
  $("#removeObjectImage").checked = false;

  if (item.image_data) {
    $("#newObjectImagePreview").innerHTML = `<img src="${escapeHtml(item.image_data)}" alt="">`;
  } else {
    $("#newObjectImagePreview").innerHTML = "<span>Ingen bild vald</span>";
  }

  setView("admin");
  showAdminSettingsSection("add-object");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function deleteObject(objectId) {
  if (state.role === "operator") return;
  const item = state.objects.find((objectItem) => objectItem.object_id === objectId);
  const name = item ? item.name : objectId;
  if (!confirm(`Ta bort ${name} (${objectId}) från databasen?`)) return;

  try {
    await api(`/api/objects?object_id=${encodeURIComponent(objectId)}`, { method: "DELETE" });
    showToast(t("toast.objectDeleted", { id: objectId }));
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
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
// HJÄLPFUNKTIONER
// Små funktioner som ateranvands pa flera stallen.
// ============================================================

function statusBadge(status) {
  const className = status === "Tillgänglig" || status === "Aktiv" ? "ok" : status === "Låg nivå" ? "warn" : status === "Sen" ? "late" : "";
  return `<span class="status ${className}">${escapeHtml(statusText(status))}</span>`;
}

function formatTime(value) {
  if (!value) return "";
  return value.slice(0, 16);
}

function unique(values) {
  return [...new Set(values)].filter(Boolean).sort((a, b) => a.localeCompare(b, "sv"));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function showToast(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.classList.add("visible");
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(() => toast.classList.remove("visible"), 2600);
}

function setDefaultDates() {
  const today = new Date();
  const returnDate = new Date();
  returnDate.setDate(returnDate.getDate() + 7);
  $("#checkoutLendingDate").value = today.toISOString().slice(0, 10);
  $("#checkoutDue").value = returnDate.toISOString().slice(0, 10);
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
	      renderObjects();
	      renderAdminObjectsTable();
	      updateCheckoutInfo();
      renderCheckoutUserDetails();
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
	  $("#jobStatusFilter")?.addEventListener("change", renderJobs);
	  $("#jobDateSort")?.addEventListener("change", renderJobs);
	  $("#checkoutObjectId").addEventListener("input", () => {
    updateCheckoutInfo();
    renderCheckoutObjectSuggestions();
  });
	  $("#checkoutStockFilter").addEventListener("change", renderCheckoutObjectSuggestions);
	  $("#checkoutUserSearch").addEventListener("input", renderCheckoutUserSuggestions);
	  $("#consumableObjectSearch")?.addEventListener("input", renderConsumableObjectSuggestions);
	  $("#returnUserSearch")?.addEventListener("input", renderReturnUserSuggestions);

	  $("#requestLoanButton").addEventListener("click", requestLoan);
	  $("#consumableReportForm")?.addEventListener("submit", saveConsumableReport);
	  $("#addObjectForm").addEventListener("submit", saveObject);
  $("#addUserForm").addEventListener("submit", saveUser);
  $("#cancelUserEditButton").addEventListener("click", resetUserForm);
  $("#systemSettingsForm")?.addEventListener("submit", saveSystemSettings);
  $("#sendRemindersButton")?.addEventListener("click", sendLoanReminders);
  document.querySelectorAll(".admin-settings-nav-button").forEach((button) => {
    button.addEventListener("click", () => showAdminSettingsSection(button.dataset.adminSection));
  });
  document.querySelectorAll(".system-settings-nav-button").forEach((button) => {
    button.addEventListener("click", () => showSystemSettingsSection(button.dataset.systemSection));
  });
  $("#notifyNewJob")?.addEventListener("change", () => syncCheckboxPair("#notifyNewJob", "#notifyNewJobAutomation"));
  $("#notifyNewJobAutomation")?.addEventListener("change", () => syncCheckboxPair("#notifyNewJobAutomation", "#notifyNewJob"));
  $("#notifyLowStock")?.addEventListener("change", () => syncCheckboxPair("#notifyLowStock", "#notifyLowStockAutomation"));
  $("#notifyLowStockAutomation")?.addEventListener("change", () => syncCheckboxPair("#notifyLowStockAutomation", "#notifyLowStock"));
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
  bindEvents();
  setDefaultDates();
  renderDashboardGuide();
  applyTranslations();
  refreshAll().catch((error) => showToast(error.message));
}

init();

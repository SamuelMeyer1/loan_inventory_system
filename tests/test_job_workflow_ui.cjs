const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const elements = new Map();
function get(selector) {
  if (!elements.has(selector)) elements.set(selector, {
    value: "", checked: false, hidden: false, disabled: false, open: false,
    innerHTML: "", textContent: "", dataset: {}, style: {},
    reset() {}, querySelectorAll: () => [],
    showModal() { this.open = true; }, close() { this.open = false; },
    classList: { contains: () => false, remove() {} },
  });
  return elements.get(selector);
}
const messages = [];
const calls = [];
const context = vm.createContext({
  document: { querySelector: get, querySelectorAll: () => [] },
  window: { scrollTo() {} },
  localStorage: { getItem: () => "sv" },
  establishSession: async () => false,
  escapeHtml: (value) => String(value).replaceAll("<", "&lt;"),
  showToast: (message) => messages.push(message),
  sanitizePhoneField() {}, syncDepartmentFromGroup() {}, showAdminSettingsSection() {},
  isConsumableObject: () => false,
  confirm: () => true,
});
for (const name of ["app.js", "translations.js", "i18n.js", "loan-views.js", "actions.js"]) {
  vm.runInContext(fs.readFileSync(`frontend/js/${name}`, "utf8"), context);
}
vm.runInContext("refreshAll = async () => {}; showAdminSettingsSection = () => {}; state.role = 'admin';", context);
const state = vm.runInContext("state", context);
const submit = { preventDefault() {} };

async function main() {
  const source = fs.readFileSync("frontend/index.html", "utf8");
  assert.doesNotMatch(source, /id="newUserRole"/);
  assert.match(source, /id="newUserActiveControl" hidden/);
  assert.match(source, /class="topbar-controls">[\s\S]*id="openSearchButton"[\s\S]*class="account-access"/);
  get("#newUserFirstName").value = "Test";
  get("#newUserLastName").value = "Borrower";
  get("#newUserEmail").value = "test@example.invalid";
  get("#newUserPrivacyAcknowledged").checked = true;
  context.api = async (url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) });
    return { user_id: "new" };
  };
  await context.saveUser(submit);
  assert.equal("role" in calls[0].payload, false);
  assert.equal("active" in calls[0].payload, false);
  assert.equal(calls[0].payload.privacy_notice_acknowledged, true);
  state.users = [{ user_id: "old", name: "Old Borrower", active: 0, role: "admin" }];
  context.startEditUser("old");
  assert.equal(get("#newUserActiveControl").hidden, false);
  assert.equal(get("#newUserActive").checked, false);
  await context.saveUser(submit);
  assert.equal("role" in calls[1].payload, false);
  assert.equal(calls[1].payload.active, false);
  assert.equal(get("#newUserActiveControl").hidden, true);
  context.renderUsersTable();
  assert.doesNotMatch(get("#usersBody").innerHTML, /<td>admin<\/td>/);
  assert.match(get("#usersBody").innerHTML, /Avstängd/);
  state.language = "en";
  assert.match(context.userBorrowStatus({ active: 0 }), /Suspended/);
  state.language = "sv";

  state.objects = [
    { object_id: "A", name: "Article A", available_quantity: 15, total_quantity: 15 },
    { object_id: "B", name: "Article B", available_quantity: 5, total_quantity: 5 },
  ];
  get("#checkoutObjectId").value = "A";
  context.updateCheckoutInfo();
  const disclosure = get("#checkoutObjectDisclosure");
  assert.equal(disclosure.hidden, false);
  assert.equal(disclosure.open, false);
  disclosure.open = true;
  state.loanCart = [{ object_id: "A", quantity: 4 }];
  context.updateCheckoutInfo();
  assert.equal(disclosure.open, true);
  assert.equal(get("#checkoutObjectQuantity").value, "11 av 15");
  get("#checkoutObjectId").value = "B";
  context.updateCheckoutInfo();
  assert.equal(disclosure.open, false);
  get("#checkoutObjectId").value = "";
  context.updateCheckoutInfo();
  assert.equal(disclosure.hidden, true);
  assert.equal(get("#checkoutInfo").hidden, true);

  const jobs = [
    { request_id: 10, request_group_id: 10, object_id: "A", object_name: "Article A",
      user_name: "Test Borrower", status: "requested", quantity: 15 },
    { request_id: 11, request_group_id: 10, object_id: "B", object_name: "Article B",
      user_name: "Test Borrower", status: "requested", quantity: 5 },
  ];
  for (const status of ["requested", "approved", "prepared"]) {
    jobs.forEach((job) => { job.status = status; });
    const html = context.renderJobGroup({ id: 10, status, items: jobs });
    assert.doesNotMatch(html, /data-job-id=/);
    assert.equal((html.match(/data-job-group-id=/g) || []).length, 1);
    assert.equal((html.match(/data-delete-job=/g) || []).length, 2);
    if (status === "prepared") {
      assert.match(html, /disabled title="SMS/);
      assert.match(html, /data-pickup-email="10"/);
    }
  }
  jobs.forEach((job) => { job.status = "loaned"; });
  const loanedHtml = context.renderJobGroup({ id: 10, status: "loaned", items: jobs });
  assert.doesNotMatch(loanedHtml, /data-delete-job=/);
  assert.match(loanedHtml, /Återlämna – välj antal/);
  assert.match(loanedHtml, /data-job-return-id="10"/);
  assert.doesNotMatch(loanedHtml, /job-warning-icon/);
  const damagedJob = { ...jobs[0], status: "returned", returned_quantity: 15, remaining_quantity: 0,
    unresolved_damage_quantity: 1, unresolved_damage_description: "<broken housing>", stocking_blocked: 1 };
  const damagedHtml = context.renderJobGroup({ id: 10, status: "returned", items: [damagedJob] });
  assert.match(damagedHtml, /job-warning-icon/);
  assert.match(damagedHtml, /Till felanmälan/);
  assert.match(damagedHtml, /data-open-damage-report="10" data-object-id="A"/);
  assert.doesNotMatch(damagedHtml, /&lt;broken housing>/);
  assert.match(damagedHtml, /data-job-status="stocked" disabled/);
  assert.doesNotMatch(context.renderJobGroupItem({ ...damagedJob, unresolved_damage_quantity: 0, stocking_blocked: 0 }), /job-warning-text/);
  assert.match(context.renderJobGroupItem({ ...jobs[0], returned_quantity: 4, remaining_quantity: 11 }), /11 exemplar återstår/);
  state.language = "en";
  assert.match(context.renderJobGroupItem(damagedJob), /Open damage report/);
  state.language = "sv";

  const navigation = [];
  context.setView = (view) => navigation.push(view);
  context.showAdminSettingsSection = (section) => navigation.push(section);
  context.closeJobDetail = () => {};
  state.damagedReturns = [{ return_id: 99, loan_request_id: 10, object_id: "A" }];
  context.openDamageReport(10, "A");
  assert.deepEqual(navigation, ["admin", "damage"]);

  const loans = [
    { loan_id: 1, loan_request_id: 10, request_group_id: 10, user_id: "test",
      object_id: "A", object_name: "Article A", quantity: 15, remaining_quantity: 15, returned_quantity: 0 },
    { loan_id: 2, loan_request_id: 11, request_group_id: 10, user_id: "test",
      object_id: "B", object_name: "Article B", quantity: 5, remaining_quantity: 5, returned_quantity: 0 },
    { loan_id: 3, request_group_id: 20, user_id: "other" },
  ];
  calls.length = 0;
  context.api = async (url, options) => {
    if (url === "/api/loans") return loans;
    calls.push({ url, payload: JSON.parse(options.body) });
    return { returned: 4 };
  };
  await context.updateJobGroupStatus(10, "returned");
  assert.equal(get("#jobReturnDialog").open, true);
  assert.equal(state.jobReturnLoans.length, 2);
  assert.equal(calls.length, 0, "Opening or cancelling must not return anything");
  assert.match(get("#jobReturnItems").innerHTML, /max="15"/);
  assert.match(get("#jobReturnItems").innerHTML, /value="0"/);
  for (const id of [1, 2]) {
    get(`[data-job-return-quantity="${id}"]`).value = "0";
    get(`[data-job-return-damaged="${id}"]`).value = "0";
  }
  for (const value of ["0", "", "-1", "16", "4.5"]) {
    get('[data-job-return-quantity="1"]').value = value;
    await context.saveJobReturn(submit);
    assert.equal(calls.length, 0, `Reject quantity ${value}`);
    assert.equal(get("#jobReturnDialog").open, true);
  }
  get('[data-job-return-quantity="1"]').value = "4";
  await context.saveJobReturn(submit);
  assert.deepEqual(calls[0], { url: "/api/return", payload: {
    user_id: "test", items: [{ loan_id: 1, quantity: 4, damaged_quantity: 0,
      damage_description: "", expected_returned_quantity: 0 }],
  } });
  assert.equal(get("#jobReturnDialog").open, false);

  loans[0].returned_quantity = 4;
  loans[0].remaining_quantity = 11;
  await context.openJobReturn(10, 10);
  assert.equal(state.jobReturnLoans.length, 1);
  assert.match(get("#jobReturnItems").innerHTML, /max="11"/);
  context.api = async () => { throw new Error("Stale return"); };
  await context.saveJobReturn(submit);
  assert.equal(get("#jobReturnDialog").open, true);
  assert.equal(messages.at(-1), "Stale return");
  assert.equal(get("#jobReturnError").hidden, false);
  assert.equal(get("#jobReturnError").textContent, "Stale return");
  assert.equal(state.returnBusy, false);
  get("#jobReturnDialog").close();

  state.language = "en";
  assert.equal(context.t("return.confirm", { quantity: 2, damaged: 1 }),
    "Record 2 returned units, including 1 damaged units?");
  state.language = "sv";
  assert.equal(context.t("return.confirm", { quantity: 2, damaged: 1 }),
    "Registrera 2 återlämnade exemplar, varav 1 skadade?");
  state.language = "en";
  assert.equal(context.t("jobs.nextReturned"), "Return – choose quantities");
  assert.match(context.t("jobs.smsFuture"), /not available/);
  console.log("Borrower form, object disclosure, grouped actions, SMS placeholder and quantity return checks passed.");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });

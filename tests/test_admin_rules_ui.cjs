const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

const elements = new Map();
const get = (selector) => {
  if (!elements.has(selector)) elements.set(selector, {
    value: "", checked: false, hidden: false, disabled: false,
    textContent: "", innerHTML: "", attributes: {},
    setAttribute(name, value) { this.attributes[name] = value; },
    classes: new Set(),
    classList: { toggle(name, on) { on ? get(selector).classes.add(name) : get(selector).classes.delete(name); } },
  });
  return elements.get(selector);
};
const calls = [];
const messages = [];
const context = vm.createContext({
  document: { querySelector: get, querySelectorAll: () => [] },
  localStorage: { getItem: () => "sv" },
  establishSession: async () => false,
  escapeHtml: (value) => String(value).replaceAll("<", "&lt;"),
  formatTime: (value) => value,
  showToast: (message) => messages.push(message),
  unique: (values) => [...new Set(values)],
  objectDisplayImage: (item) => item.image_data || "",
  statusBadge: (status) => `<span>${status}</span>`,
});
for (const name of ["app.js", "translations.js", "i18n.js", "actions.js"]) {
  vm.runInContext(fs.readFileSync(`frontend/js/${name}`, "utf8"), context);
}
vm.runInContext("refreshAll = async () => {}; state.role = 'superadmin';", context);
const state = vm.runInContext("state", context);

async function main() {
  get("#inactiveUserWarningEnabled").checked = true;
  get("#inactiveUserDays").value = "180";
  get("#notifyAdminNewRequest").checked = false;
  get("#notifyAdminLoaned").checked = true;
  context.api = async (url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) });
    return {};
  };
  await context.saveSystemSettings({ type: "submit", preventDefault() {} });
  assert.deepEqual(calls[0], { url: "/api/system-settings", payload: {
    inactive_user_warning_enabled: true, inactive_user_days: "180",
    notify_admin_new_request: false, notify_admin_loaned: true,
  } });
  assert.ok(messages.includes("Reglerna sparades."));

  const notification = { event_id: 5, event_type: "request", event_time: "2026-10-23", unread: 1 };
  context.api = async () => ({ items: [notification], unread_count: 1, latest_event_id: 5 });
  await context.refreshAdminNotifications();
  assert.equal(get("#adminNotificationCount").textContent, "1");
  assert.match(get("#adminNotificationList").innerHTML, /Ny låneförfrågan/);
  assert.equal(get("#markAdminNotificationsRead").disabled, false);
  assert.equal(get("#adminNotifications").classes.has("has-unread"), true);
  context.api = async (url, options) => {
    if (options) calls.push({ url, payload: JSON.parse(options.body) });
    return { items: [], unread_count: 0, latest_event_id: 5 };
  };
  await context.markAdminNotificationsRead();
  assert.deepEqual(calls.at(-1), { url: "/api/admin-notifications/read", payload: { up_to_event_id: 5 } });
  assert.equal(get("#adminNotificationCount").textContent, "0");
  assert.equal(get("#adminNotifications").classes.has("has-unread"), false);

  context.applyRole = () => {};
  state.objectCategories = ["Instrument"];
  state.objects = [{ object_id: "OBJ-1", name: "Tryckgivare", category: "Instrument",
    article_number: "VOL-123", brand: "Pentronic", model: "100-3", measurement_range: "20-100 C",
    unit_volvo_ids: "ID-1\nID-2",
    unit_price: "1458.50", location: "Våning 8, blått skåp 1", total_quantity: 2,
    available_quantity: 2, min_quantity: 0, status: "Tillgänglig", device: "legacy" }];
  get("#objectSearch").value = "";
  get("#categoryFilter").value = "Alla";
  get("#statusFilter").value = "Alla";
  context.renderObjects();
  assert.match(get("#objectsGrid").innerHTML, /VOL-123/);
  assert.match(get("#objectsGrid").innerHTML, /Pentronic/);
  assert.match(get("#objectsGrid").innerHTML, /Våning 8, blått skåp 1/);
  assert.match(get("#objectsGrid").innerHTML, /1\s*458,50 kr/);
  assert.match(get("#objectsGrid").innerHTML, /Visa äldre uppgifter/);
  state.objects[0].article_number = "";
  context.renderObjects();
  assert.match(get("#objectsGrid").innerHTML, /2 exemplars-ID:n/);
  state.objects[0].unit_volvo_ids = "004712";
  context.renderObjects();
  assert.match(get("#objectsGrid").innerHTML, />004712<\/p>/);
  state.objects[0].article_number = "VOL-123";

  context.readSelectedObjectImage = async () => "";
  context.resetObjectForm = () => {};
  context.refreshAll = async () => {};
  context.setView = () => {};
  get("#newObjectId").value = "OBJ-1";
  get("#newObjectName").value = "Tryckgivare";
  get("#newObjectCategory").value = "Instrument";
  get("#newObjectArticle").value = "VOL-123";
  get("#newObjectBrand").value = "Pentronic";
  get("#newObjectModel").value = "100-3";
  get("#newObjectMeasurementRange").value = "20-100 C";
  get("#newObjectUnitPrice").value = "1458.50";
  get("#newObjectLocation").value = "Våning 8, blått skåp 1";
  get("#newObjectTotal").value = "2";
  get("#newObjectAvailable").value = "2";
  get("#newObjectMin").value = "0";
  state.editingObjectId = "OBJ-1";
  context.api = async (url, options) => {
    calls.push({ url, payload: JSON.parse(options.body) });
    return url === "/api/objects" ? { object_id: "OBJ-1" } : { name: "Sensorer" };
  };
  await context.saveObject({ preventDefault() {} });
  assert.equal(calls.at(-1).url, "/api/objects");
  assert.equal(calls.at(-1).payload.unit_price, "1458.50");
  assert.equal("device" in calls.at(-1).payload, false);
  assert.equal("tornado_id" in calls.at(-1).payload, false);

  get("#objectCategoryName").value = "Sensorer";
  await context.addObjectCategory({ preventDefault() {} });
  assert.equal(state.objectCategories.at(-1), "Sensorer");
  assert.match(get("#newObjectCategory").innerHTML, /Sensorer/);

  get("#adminNotifications").open = true;
  let readCursor = 0;
  context.api = async (url, options) => {
    if (options) {
      readCursor = JSON.parse(options.body).up_to_event_id;
      return {};
    }
    return { items: [notification], unread_count: readCursor ? 0 : 1, latest_event_id: 5 };
  };
  await context.readOpenedAdminNotifications();
  assert.equal(readCursor, 5, "Opening the bell must mark the fetched snapshot read");
  assert.equal(get("#adminNotificationCount").textContent, "0");
  get("#adminNotifications").open = false;
  readCursor = 0;
  await context.readOpenedAdminNotifications();
  assert.equal(readCursor, 0, "Closing the bell must not mark anything read");

  get("#adminNotifications").open = true;
  let finishOpenFetch;
  context.api = () => new Promise((resolve) => { finishOpenFetch = resolve; });
  const opening = context.readOpenedAdminNotifications();
  get("#adminNotifications").open = false;
  finishOpenFetch({ items: [notification], unread_count: 1, latest_event_id: 5 });
  await opening;
  assert.equal(readCursor, 0, "Leaving before loading must not mark notifications read");

  get("#adminNotifications").open = true;
  context.api = async (url, options) => {
    if (options) {
      readCursor = JSON.parse(options.body).up_to_event_id;
      return {};
    }
    return { items: [notification], unread_count: 1, latest_event_id: readCursor ? 6 : 5 };
  };
  await context.readOpenedAdminNotifications();
  assert.equal(readCursor, 5, "A concurrent new event must not be marked read");
  assert.equal(get("#adminNotificationCount").textContent, "1");
  readCursor = 0;
  get("#adminNotifications").open = true;
  context.api = async () => { throw new Error("Offline opening"); };
  await context.readOpenedAdminNotifications();
  assert.equal(readCursor, 0);
  assert.match(get("#adminNotificationError").textContent, /Offline opening/);
  get("#adminNotifications").open = false;

  context.api = async () => { throw new Error("Offline"); };
  await context.refreshAdminNotifications();
  assert.equal(get("#adminNotificationCount").textContent, "!");
  assert.match(get("#adminNotificationError").textContent, /Offline/);
  assert.equal(get("#markAdminNotificationsRead").disabled, true);

  let resolveOld;
  context.api = () => new Promise((resolve) => { resolveOld = resolve; });
  const oldRequest = context.refreshAdminNotifications();
  context.api = async () => ({ items: [], unread_count: 0, latest_event_id: 6 });
  await context.refreshAdminNotifications();
  resolveOld({ items: [notification], unread_count: 1, latest_event_id: 5 });
  await oldRequest;
  assert.equal(get("#adminNotificationCount").textContent, "0", "Stale poll must not undo read state");
  assert.equal(get("#adminNotificationError").hidden, true);
  vm.runInContext("state.language = 'en'; state.role = 'operator';", context);
  context.renderAdminNotifications();
  assert.equal(get("#adminNotifications").hidden, true);
  assert.equal(get("#adminNotificationList").innerHTML, "");
  assert.equal(context.t("settings.inactive"), "Inactive");
  console.log("Admin rules payload, notification read/error/race handling and role visibility passed.");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });

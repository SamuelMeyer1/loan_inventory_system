const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");

const source = fs.readFileSync(path.join(__dirname, "../frontend/js/session.js"), "utf8");
const appPage = fs.readFileSync(path.join(__dirname, "../frontend/index.html"), "utf8");

async function main() {
  const updates = fs.readFileSync(path.join(__dirname, "../uppdates"), "utf8");
  const version = updates.match(/Nuvarande version: V(\d+\.\d+\.\d+)/)[1];
  assert.ok(appPage.includes(`<span class="login-version">Version ${version}</span>`));

  const nodes = new Map();
  const makeNode = () => ({
    hidden: false,
    inert: false,
    disabled: false,
    value: "",
    textContent: "",
    handlers: {},
    addEventListener(type, handler) { this.handlers[type] = handler; },
    querySelector(selector) { return selector === "button[type='submit']" ? submitButton : null; },
    setAttribute(name, value) { this[name] = value; },
    removeAttribute(name) { delete this[name]; },
    focus() { this.focused = true; },
  });
  const submitButton = { disabled: false };
  const query = (selector) => {
    if (!nodes.has(selector)) nodes.set(selector, makeNode());
    return nodes.get(selector);
  };
  const requests = [];
  let reloads = 0;
  let simulation = true;
  const api = async (url) => {
    requests.push(url);
    if (url === "/api/runtime") return { simulation };
    if (url === "/api/privacy/notice") return { configured: false };
    if (url === "/api/auth/session") {
      return { role: "operator", user_id: null, csrf: "guest-csrf", expires_in: 0, anonymous: true };
    }
    if (url === "/api/auth/login") {
      return { role: "superadmin", csrf: "admin-csrf", expires_in: 1800 };
    }
    throw new Error(`Unexpected API request: ${url}`);
  };
  const context = vm.createContext({
    api,
    state: { role: "" },
    window: {},
    document: { querySelector: query },
    location: { reload() { reloads += 1; } },
    setTimeout() {},
  });
  vm.runInContext(source, context);

  assert.equal(await vm.runInContext("establishSession()", context), true);
  assert.equal(query("#loginPanel").hidden, true);
  assert.equal(query(".app-shell").hidden, false);
  assert.equal(query("#accountRole").textContent, "Operatör");
  assert.equal(query("#adminLoginButton").hidden, false);
  assert.equal(query("#logoutButton").hidden, true);
  assert.equal(query("#simulationBadge").hidden, false);
  assert.equal(query("#loginSimulationBadge").hidden, false);

  query("#adminLoginButton").handlers.click();
  assert.equal(query("#loginPanel").hidden, false);
  assert.equal(query(".app-shell").inert, true);
  query("#loginCloseButton").handlers.click();
  assert.equal(query("#loginPanel").hidden, true);
  assert.equal(query(".app-shell").inert, false);

  query("#adminLoginButton").handlers.click();
  const form = query("#loginForm");
  await form.handlers.submit({
    preventDefault() {},
    target: { querySelector() { return submitButton; } },
  });
  assert.equal(requests.includes("/api/auth/login"), true);
  assert.equal(reloads, 1, "Reload after admin login so the app fetches admin-only data");

  simulation = false;
  await vm.runInContext("establishSession()", context);
  assert.equal(query("#simulationBadge").hidden, true);
  assert.equal(query("#loginSimulationBadge").hidden, true);

  console.log("Admin login panel open/close and LAN role switching checks passed.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});

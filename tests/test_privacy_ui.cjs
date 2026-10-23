const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const source = (name) => fs.readFileSync(path.join(__dirname, "../frontend/js", name), "utf8");
const tick = () => new Promise(setImmediate);

async function main() {
  const privacyPage = fs.readFileSync(path.join(__dirname, "../frontend/privacy.html"), "utf8");
  const appPage = fs.readFileSync(path.join(__dirname, "../frontend/index.html"), "utf8");
  assert.match(privacyPage, /olof\.samuelsson@volvo\.com/);
  assert.match(privacyPage, /class="privacy-notice"/);
  assert.match(appPage, /id="newUserPrivacyAcknowledged" type="checkbox" required/);
  assert.match(appPage, /id="quickUserPrivacyAcknowledged" type="checkbox" required/);
  assert.match(appPage, /olof\.samuelsson@volvo\.com/);
  assert.doesNotMatch(appPage, /<details open>/);
  for (const prefix of ["newUser", "quickUser"]) {
    const section = appPage.match(new RegExp(`<section[^>]+id="${prefix}PrivacyAcknowledgement">([\\s\\S]*?)</section>`))[1];
    assert.equal((section.match(/type="checkbox"/g) || []).length, 1);
    assert.doesNotMatch(section, /<details|<small|<p[ >]|acknowledgement-heading/);
    assert.match(section, /href="\/privacy.html" target="_blank" rel="noopener"/);
    assert.match(section, /Jag har läst dataskyddsinformationen\./);
  }

  const sent = [];
  const apiContext = vm.createContext({
    window: { loanSession: { csrf: "test-csrf" } },
    location: { reload() {} }, t: (key) => key,
    fetch: async (url, options) => {
      sent.push({ url, options });
      return { status: 200, headers: { get: () => "application/json" }, json: async () => ({ ok: true, data: {} }) };
    },
  });
  vm.runInContext(source("api.js"), apiContext);
  await vm.runInContext('api("/api/return", {method:"POST", body:"{}"})', apiContext);
  assert.equal(sent[0].options.headers["X-CSRF-Token"], "test-csrf");
  assert.equal(sent[0].options.headers["X-Loan-Client"], "browser");

  const nodes = {};
  const node = (id) => nodes[id] ||= {
    value: "", hidden: true, disabled: true, textContent: "", elements: {},
    addEventListener(name, handler) { this[name] = handler; },
  };
  const requests = [];
  const timers = [];
  let reloads = 0;
  const context = vm.createContext({
    document: { getElementById: node },
    location: { href: "", reload() { reloads += 1; } },
    setTimeout: (callback, delay) => timers.push({ callback, delay }),
    fetch: async (url, options = {}) => {
      requests.push({ url, options });
      let data;
      if (url === "/api/auth/session") data = { role: "superadmin", csrf: "test-csrf", expires_in: 42 };
      else if (url === "/api/privacy/notice") data = { configured: false };
      else data = { blocked: false, applied: options.method === "POST", counts: { users: 1 } };
      return { ok: true, status: 200, json: async () => ({ ok: true, data }) };
    },
  });
  vm.runInContext(source("privacy.js"), context);
  await tick();
  assert.equal(node("privacyAdmin").hidden, false);
  assert.equal(timers[0].delay, 42000, "Use remaining server lifetime, not a new 30-minute window");
  node("subjectId").value = "test-subject";
  await node("previewErase").onclick();
  assert.equal(node("applyErase").disabled, true);
  node("eraseConfirmation").value = "wrong";
  node("eraseConfirmation").oninput();
  await node("applyErase").onclick();
  assert.equal(requests.filter((r) => r.options.method === "POST").length, 0);
  node("eraseConfirmation").value = "DELETE";
  node("eraseConfirmation").oninput();
  assert.equal(node("applyErase").disabled, false);
  // Changing the subject invalidates confirmation; a stale preview must never
  // authorise deletion of a different person.
  node("subjectId").value = "other-subject";
  node("subjectId").input();
  assert.equal(node("applyErase").disabled, true);
  await node("applyErase").onclick();
  assert.equal(requests.filter((r) => r.options.method === "POST").length, 0);
  await node("previewErase").onclick();
  node("eraseConfirmation").value = "DELETE";
  node("eraseConfirmation").oninput();
  await node("applyErase").onclick();
  const deletion = requests.find((r) => r.options.method === "POST");
  assert.equal(deletion.url, "/api/privacy/erase");
  assert.deepEqual(JSON.parse(deletion.options.body), { user_id: "other-subject", confirm: "DELETE" });
  assert.equal(deletion.options.headers["X-CSRF-Token"], "test-csrf");
  assert.equal(node("applyErase").disabled, true, "Prevent repeat submission");
  timers[0].callback();
  assert.equal(node("privacyAdmin").hidden, true, "Hide expired admin controls without reloading the page");
  assert.equal(reloads, 0, "The public privacy page must not reload when the admin session expires");
  console.log("Privacy UI confirmation and API session checks passed (simulated DOM; not a browser smoke test).");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });

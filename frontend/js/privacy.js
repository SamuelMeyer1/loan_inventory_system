let privacySession;
let erasePreview = null;
let retentionPreview = false;
const element = (id) => document.getElementById(id);
async function privacyApi(path, method = "GET", data = null) {
  const response = await fetch(path, { method, headers: { "Content-Type": "application/json", "X-Loan-Client": "browser",
    "X-CSRF-Token": privacySession?.csrf || "" }, ...(data === null ? {} : { body: JSON.stringify(data) }) });
  const payload = await response.json();
  if (response.status === 401) {
    location.href = "/";
    throw new Error("Logga in / Sign in");
  }
  if (!payload.ok) throw new Error(payload.error);
  return payload.data;
}
function showResult(data) { element("result").textContent = JSON.stringify(data, null, 2); }
function invalidatePreviews() {
  erasePreview = null;
  retentionPreview = false;
  element("applyErase").disabled = true;
  element("applyRetention").disabled = true;
  element("eraseConfirmation").value = "";
  element("retentionConfirmation").value = "";
}
async function act(task) {
  element("message").textContent = "";
  try { await task(); }
  catch (error) { element("message").textContent = error.message; }
}
async function initPrivacy() {
  const policy = await privacyApi("/api/privacy/notice");
  element("notice").textContent = policy.configured
    ? `Personuppgiftsansvarig / Controller: ${policy.controller}\nKontakt / Contact: ${policy.contact}\nÄndamål / Purpose: ${policy.purpose}\nRättslig grund / Legal basis: ${policy.lawful_basis}\nAvslutad lånehistorik / Completed loan history: ${policy.loan_days} dagar / days\nLoggar / Logs: ${policy.event_days} dagar / days`
    : "Information om behandlingen är inte konfigurerad. Använd endast fiktiva uppgifter tills verksamheten har beslutat om hanteringen. / Processing information is not configured. Use fictitious data until the organisation has approved processing.";
  // Public notice can be read without forcing a login.
  const sessionResponse = await fetch("/api/auth/session");
  if (!sessionResponse.ok) return;
  privacySession = (await sessionResponse.json()).data;
  if (privacySession.role !== "superadmin") return;
  element("privacyAdmin").hidden = false;
  setTimeout(() => { element("privacyAdmin").hidden = true; }, Math.max(1, privacySession.expires_in || 0) * 1000);
  const form = element("policyForm");
  Object.entries(policy).forEach(([key, value]) => { if (form.elements[key]) form.elements[key].value = value; });
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    act(async () => { await privacyApi("/api/privacy/policy", "PUT", Object.fromEntries(new FormData(form))); invalidatePreviews(); location.reload(); });
  });
  element("subjectId").addEventListener("input", invalidatePreviews);
  element("exportSubject").onclick = () => act(async () => { invalidatePreviews(); showResult(await privacyApi(`/api/privacy/export?user_id=${encodeURIComponent(element("subjectId").value)}`)); });
  element("previewErase").onclick = () => act(async () => {
    invalidatePreviews();
    const id = element("subjectId").value;
    const result = await privacyApi(`/api/privacy/erase?user_id=${encodeURIComponent(id)}`);
    showResult(result);
    erasePreview = result.blocked ? null : id;
  });
  element("eraseConfirmation").oninput = () => { element("applyErase").disabled = !erasePreview || element("eraseConfirmation").value !== "DELETE"; };
  element("applyErase").onclick = () => act(async () => {
    if (!erasePreview || element("eraseConfirmation").value !== "DELETE") return;
    const id = erasePreview;
    invalidatePreviews();
    showResult(await privacyApi("/api/privacy/erase", "POST", { user_id: id, confirm: "DELETE" }));
  });
  element("previewRetention").onclick = () => act(async () => {
    invalidatePreviews();
    showResult(await privacyApi("/api/privacy/retention"));
    retentionPreview = true;
  });
  element("retentionConfirmation").oninput = () => { element("applyRetention").disabled = !retentionPreview || element("retentionConfirmation").value !== "DELETE"; };
  element("applyRetention").onclick = () => act(async () => {
    if (!retentionPreview || element("retentionConfirmation").value !== "DELETE") return;
    invalidatePreviews();
    showResult(await privacyApi("/api/privacy/retention", "POST", { confirm: "DELETE" }));
  });
}
act(initPrivacy);

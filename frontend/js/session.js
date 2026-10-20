async function establishSession() {
  const accept = (identity) => {
    window.loanSession = identity;
    state.role = identity.role;
    document.querySelector("#roleSelect").value = identity.role;
    document.querySelector("#loginPanel").hidden = true;
    document.querySelector(".app-shell").hidden = false;
    // Remove rendered personal data when the fixed server session expires,
    // including when the user leaves the page open without further requests.
    setTimeout(() => location.reload(), Math.max(1, identity.expires_in || 0) * 1000);
    document.querySelector("#logoutButton").addEventListener("click", async () => {
      try { await api("/api/auth/logout", { method: "POST", body: "{}" }); }
      finally { location.reload(); }
    });
    return true;
  };
  const notice = await api("/api/privacy/notice");
  document.querySelector("#privacyNotice").textContent = notice.configured
    ? `${notice.controller}\n${notice.contact}\n${notice.purpose}\n${notice.lawful_basis}\nAvslutad lånehistorik / Completed loan history: ${notice.loan_days} dagar / days\nLoggar / Logs: ${notice.event_days} dagar / days\nSe Dataskydd för omfattning och rättigheter. / See Privacy for scope and rights.`
    : "Information om behandlingen är inte konfigurerad. Använd endast fiktiva uppgifter tills verksamheten godkänt hanteringen. / Processing information is not configured. Use fictitious data until approved by the organisation.";
  try { return accept(await api("/api/auth/session")); }
  catch (error) { /* An unauthenticated visit shows the form. */ }
  return new Promise((resolve) => {
    document.querySelector("#loginForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = event.target.querySelector("button");
      button.disabled = true;
      try {
        const identity = await api("/api/auth/login", { method: "POST", body: JSON.stringify({
          username: document.querySelector("#loginUsername").value,
          password: document.querySelector("#loginPassword").value,
        }) });
        document.querySelector("#loginPassword").value = "";
        document.querySelector("#loginError").textContent = "";
        resolve(accept(identity));
      } catch (error) {
        document.querySelector("#loginPassword").value = "";
        document.querySelector("#loginError").textContent = error.message;
      } finally { button.disabled = false; }
    });
  });
}

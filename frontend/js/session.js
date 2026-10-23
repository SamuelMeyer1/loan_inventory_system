async function establishSession() {
  const panel = document.querySelector("#loginPanel");
  const shell = document.querySelector(".app-shell");
  const adminLoginButton = document.querySelector("#adminLoginButton");
  const closeButton = document.querySelector("#loginCloseButton");
  let resolveInitialLogin;
  const initialLogin = new Promise((resolve) => { resolveInitialLogin = resolve; });

  const closeLogin = () => {
    panel.hidden = true;
    shell.inert = false;
    shell.removeAttribute("aria-hidden");
    adminLoginButton.focus();
  };

  adminLoginButton.addEventListener("click", () => {
    panel.hidden = false;
    shell.inert = true;
    shell.setAttribute("aria-hidden", "true");
    closeButton.hidden = false;
    document.querySelector("#loginUsername").focus();
  });
  closeButton.addEventListener("click", closeLogin);
  panel.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !closeButton.hidden) closeLogin();
  });

  document.querySelector("#loginForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = event.target.querySelector("button[type='submit']");
    const switchingFromAnonymous = window.loanSession?.anonymous === true;
    button.disabled = true;
    try {
      const identity = await api("/api/auth/login", { method: "POST", body: JSON.stringify({
        username: document.querySelector("#loginUsername").value,
        password: document.querySelector("#loginPassword").value,
      }) });
      document.querySelector("#loginPassword").value = "";
      document.querySelector("#loginError").textContent = "";
      if (switchingFromAnonymous) {
        location.reload();
        return;
      }
      accept(identity);
      resolveInitialLogin(true);
    } catch (error) {
      document.querySelector("#loginPassword").value = "";
      document.querySelector("#loginError").textContent = error.message;
    } finally { button.disabled = false; }
  });

  const accept = (identity) => {
    window.loanSession = identity;
    state.role = identity.role;
    document.querySelector("#roleSelect").value = identity.role;
    document.querySelector("#accountRole").textContent = ({
      operator: "Operatör",
      admin: "Admin",
      superadmin: "Systemadmin",
    })[identity.role] || "Användare";
    panel.hidden = true;
    shell.hidden = false;
    shell.inert = false;
    shell.removeAttribute("aria-hidden");
    adminLoginButton.hidden = !identity.anonymous;
    closeButton.hidden = true;
    // Remove rendered personal data when the fixed server session expires,
    // including when the user leaves the page open without further requests.
    if (identity.anonymous) {
      document.querySelector("#logoutButton").hidden = true;
    } else {
      document.querySelector("#logoutButton").hidden = false;
      setTimeout(() => location.reload(), Math.max(1, identity.expires_in || 0) * 1000);
      document.querySelector("#logoutButton").addEventListener("click", async () => {
        try { await api("/api/auth/logout", { method: "POST", body: "{}" }); }
        finally { location.reload(); }
      });
    }
    return true;
  };
  window.loanRuntime = await api("/api/runtime");
  document.querySelector("#simulationBadge").hidden = !window.loanRuntime.simulation;
  document.querySelector("#loginSimulationBadge").hidden = !window.loanRuntime.simulation;
  const notice = await api("/api/privacy/notice");
  const privacyText = notice.configured
    ? `Personuppgiftsansvarig / Controller: ${notice.controller}\nKontakt / Contact: ${notice.contact}\nÄndamål / Purpose: ${notice.purpose}\nRättslig grund / Legal basis: ${notice.lawful_basis}\nAvslutad lånehistorik / Completed loan history: ${notice.loan_days} dagar / days\nLoggar / Logs: ${notice.event_days} dagar / days`
    : "Information om behandlingen är inte konfigurerad. Använd endast fiktiva uppgifter tills verksamheten godkänt hanteringen. / Processing information is not configured. Use fictitious data until approved by the organisation.";
  document.querySelector("#privacyNotice").textContent = privacyText;
  try { return accept(await api("/api/auth/session")); }
  catch (error) { /* An unauthenticated visit shows the form. */ }
  adminLoginButton.hidden = true;
  closeButton.hidden = true;
  panel.hidden = false;
  return initialLogin;
}

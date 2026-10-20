// Browser API client helpers.
async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: { "Content-Type": "application/json", "X-Loan-Client": "browser",
        "X-CSRF-Token": window.loanSession?.csrf || "", ...(options.headers || {}) },
    });
  } catch (error) {
    throw new Error(t("error.network"));
  }
  const contentType = response.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    throw new Error(t("error.backendJson"));
  }

  if (response.status === 401 && window.loanSession) {
    window.loanSession = null;
    location.reload();
    throw new Error("Sessionen har gått ut / Session expired");
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

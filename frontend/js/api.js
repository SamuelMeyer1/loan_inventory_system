// Browser API client helpers.
async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch (error) {
    throw new Error(t("error.network"));
  }
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

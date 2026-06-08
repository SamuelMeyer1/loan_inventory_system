// Shared UI helpers.
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

function daysUntilDue(value) {
  if (!value) return null;
  const due = new Date(value.replace(" ", "T"));
  if (Number.isNaN(due.getTime())) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  due.setHours(0, 0, 0, 0);
  return Math.ceil((due - today) / 86400000);
}

function daysUntilDueText(value) {
  const days = daysUntilDue(value);
  if (days === null) return "";
  if (state.language === "en") {
    if (days < 0) return `${Math.abs(days)} days overdue`;
    if (days === 0) return "Due today";
    if (days === 1) return "1 day left";
    return `${days} days left`;
  }
  if (days < 0) return `${Math.abs(days)} dagar sen`;
  if (days === 0) return "Ska lämnas idag";
  if (days === 1) return "1 dag kvar";
  return `${days} dagar kvar`;
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

function objectDisplayImage(item) {
  return item?.display_image_data || item?.image_data || "";
}

function inferToastType(message) {
  const text = String(message || "").trim().toLowerCase();
  if (
    text.includes("skapades") ||
    text.includes("sparades") ||
    text.includes("uppdaterades") ||
    text.includes("togs bort") ||
    text.includes("återlämnat") ||
    text.includes("återlämnad") ||
    text.includes("markerad") ||
    text.includes("skickade") ||
    text.includes("created") ||
    text.includes("saved") ||
    text.includes("updated") ||
    text.includes("deleted") ||
    text.includes("returned") ||
    text.includes("handled")
  ) {
    return "success";
  }
  if (
    text.includes("serverfel") ||
    text.includes("kunde inte") ||
    text.includes("smtp") ||
    text.includes("error") ||
    text.includes("failed")
  ) {
    return "error";
  }
  if (
    text.startsWith("ange ") ||
    text.startsWith("välj ") ||
    text.includes("måste") ||
    text.includes("kan inte") ||
    text.includes("hittades inte") ||
    text.includes("ogiltig") ||
    text.startsWith("choose ") ||
    text.includes("must") ||
    text.includes("cannot") ||
    text.includes("not found") ||
    text.includes("invalid")
  ) {
    return "warning";
  }
  return "info";
}

function toastMeta(type, message) {
  const isEnglish = state.language === "en";
  const text = String(message || "").trim().toLowerCase();
  const missingInput = text.startsWith("ange ") || text.startsWith("välj ") || text.startsWith("choose ");
  const labels = {
    success: { icon: "OK", title: isEnglish ? "Done" : "Klart" },
    warning: { icon: "!", title: missingInput ? (isEnglish ? "Missing input" : "Saknar uppgift") : (isEnglish ? "Check this" : "Kontrollera") },
    error: { icon: "!", title: isEnglish ? "Something went wrong" : "Något gick fel" },
    info: { icon: "i", title: isEnglish ? "Information" : "Information" },
  };
  return labels[type] || labels.info;
}

function hideToast() {
  const toast = $("#toast");
  if (!toast) return;
  toast.classList.remove("visible");
}

function showToast(message, type = null) {
  const toast = $("#toast");
  if (!toast) return;
  const toastType = type || inferToastType(message);
  const meta = toastMeta(toastType, message);

  toast.className = `toast toast-${toastType}`;
  toast.setAttribute("role", toastType === "error" ? "alert" : "status");
  toast.setAttribute("aria-live", toastType === "error" ? "assertive" : "polite");
  toast.innerHTML = `
    <div class="toast-icon" aria-hidden="true">${escapeHtml(meta.icon)}</div>
    <div class="toast-content">
      <strong class="toast-title">${escapeHtml(meta.title)}</strong>
      <p class="toast-message">${escapeHtml(message)}</p>
    </div>
    <button class="toast-close" type="button" aria-label="${state.language === "en" ? "Close notification" : "Stäng notis"}">×</button>
  `;
  toast.querySelector(".toast-close")?.addEventListener("click", hideToast);

  requestAnimationFrame(() => toast.classList.add("visible"));
  clearTimeout(showToast.timeout);
  showToast.timeout = setTimeout(hideToast, toastType === "error" || toastType === "warning" ? 5200 : 3400);
}

function setDefaultDates() {
  const today = new Date();
  const returnDate = new Date();
  returnDate.setDate(returnDate.getDate() + 7);
  $("#checkoutLendingDate").value = today.toISOString().slice(0, 10);
  $("#checkoutDue").value = returnDate.toISOString().slice(0, 10);
  updateCheckoutDateLimit();
}

function updateCheckoutDateLimit() {
  const lendingInput = $("#checkoutLendingDate");
  const dueInput = $("#checkoutDue");
  if (!lendingInput || !dueInput || !lendingInput.value) return;
  const maxDays = Math.max(1, Number(state?.systemSettings?.max_loan_days || 90));
  const maxDate = new Date(`${lendingInput.value}T00:00:00`);
  maxDate.setDate(maxDate.getDate() + maxDays);
  dueInput.min = lendingInput.value;
  dueInput.max = maxDate.toISOString().slice(0, 10);
  if (dueInput.value && dueInput.value > dueInput.max) {
    dueInput.value = dueInput.max;
  }
}

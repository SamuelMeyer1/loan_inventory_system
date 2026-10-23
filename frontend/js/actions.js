// API-backed UI actions.
// ============================================================
// HANDLINGAR
// Funktioner som skapar, uppdaterar eller tar bort data via API.
// ============================================================

async function checkout() {
  const button = $("#checkoutButton");
  if (button?.disabled) return;
  try {
    if (button) button.disabled = true;
    const userId = resolveCheckoutUserId();
    if (!userId) {
      showToast(t("toast.chooseUser"));
      return;
    }
    const data = await api("/api/checkout", {
      method: "POST",
      body: JSON.stringify(checkoutPayload(userId)),
    });
    showToast(t("toast.loanCreated", { id: data.loan_id }));
    clearCheckoutForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

function checkoutPayload(userId) {
  return {
    object_id: $("#checkoutObjectInstrumentId").value || $("#checkoutObjectId").value,
    user_id: userId,
    quantity: Number($("#checkoutQuantity").value),
    lending_date: $("#checkoutLendingDate").value,
    due_time: $("#checkoutDue").value,
    engine_id: $("#checkoutEngineId").value,
    project_number: $("#checkoutProjectNumber").value,
  };
}

function clearCheckoutForm() {
  state.loanCart = [];
  renderLoanCart();
  $("#checkoutObjectId").value = "";
  updateCheckoutInfo();
  $("#checkoutUser").value = "";
  $("#checkoutUserSearch").value = "";
  renderCheckoutUserDetails();
  resetAutoUserCardScanMemory();
  $("#checkoutEngineId").value = "";
  $("#checkoutProjectNumber").value = "";
  $("#checkoutQuantity").value = "1";
  setDefaultDates();
}

async function requestLoan() {
  const button = $("#requestLoanButton");
  if (button?.disabled) return;
  const originalText = button?.textContent || "";
  try {
    if (button) button.disabled = true;
    if (button) button.textContent = state.language === "en" ? "Sending..." : "Skickar...";
    const userId = resolveCheckoutUserId();
    if (!userId) {
      showToast(t("toast.chooseUser"));
      return;
    }
    if ($("#checkoutObjectId").value.trim()) addLoanArticle();
    if (!state.loanCart.length) throw new Error(state.language === "en" ? "Add at least one article." : "Lägg till minst en artikel.");
    const data = await api("/api/loan-requests", {
      method: "POST",
      body: JSON.stringify({ ...checkoutPayload(userId), items: state.loanCart.map(({ object_id, quantity }) => ({ object_id, quantity })) }),
    });
    showToast(t("toast.requestCreated", { id: data.request_id }));
    clearCheckoutForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.textContent = originalText || t("action.requestLoan");
    if (button) button.disabled = false;
  }
}

async function saveConsumableReport(event) {
  event.preventDefault();
  try {
    const objectId = resolveConsumableObjectId();
    const data = await api("/api/consumable-reports", {
      method: "POST",
      body: JSON.stringify({
        object_id: objectId,
      }),
    });
    showToast(state.language === "en" ? "Consumable reported out of stock." : "Förbrukningsvaran anmäldes som slut.");
    $("#consumableReportForm").reset();
    $("#consumableObjectId").value = "";
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

function resolveConsumableObjectId() {
  const selected = $("#consumableObjectId").value;
  if (selected) return selected;
  const term = $("#consumableObjectSearch").value.trim().toLowerCase();
  const item = state.objects.find((objectItem) =>
    objectItem.object_id.toLowerCase() === term ||
    objectItem.name.toLowerCase() === term ||
    objectItem.article_number?.toLowerCase() === term ||
    objectItem.supplier_article_number?.toLowerCase() === term
  );
  return item ? item.object_id : $("#consumableObjectSearch").value;
}

async function closeConsumableReport(reportId) {
  try {
    await api("/api/consumable-reports", {
      method: "PUT",
      body: JSON.stringify({ report_id: reportId }),
    });
    showToast(state.language === "en" ? "Report marked handled." : "Rapport markerad åtgärdad.");
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function updateJobStatus(requestId, status) {
  try {
    const data = await api("/api/loan-requests", {
      method: "PUT",
      body: JSON.stringify({ request_id: requestId, status }),
    });
    showToast(t("toast.jobUpdated", { id: data.request_id }));
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function updateJobGroupStatus(requestGroupId, status) {
  try {
    const data = await api("/api/loan-requests", {
      method: "PUT",
      body: JSON.stringify({ request_group_id: requestGroupId, status }),
    });
    showToast(state.language === "en"
      ? `Request ${data.request_group_id} updated.`
      : `Förfrågan ${data.request_group_id} uppdaterades.`);
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function markPickupCollected(requestGroupId) {
  await updateJobGroupStatus(requestGroupId, "loaned");
}

async function deleteJob(requestId) {
  const job = state.jobs.find((item) => item.request_id === requestId);
  const label = job ? `${job.object_name} för ${job.user_name}` : `jobb ${requestId}`;
  if (!confirm(`Ta bort ${label}?`)) return;
  try {
    const data = await api(`/api/loan-requests?request_id=${encodeURIComponent(requestId)}`, { method: "DELETE" });
    showToast(`Jobb ${data.request_id} togs bort.`);
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function saveJobDetails(event) {
  event.preventDefault();
  const job = selectedJob();
  if (!job) return;
  try {
    await api("/api/loan-requests/details", {
      method: "PUT",
      body: JSON.stringify({
        request_id: job.request_id,
        engine_id: $("#editJobEngineId").value,
        project_number: $("#editJobProjectNumber").value,
        quantity: Number($("#editJobQuantity").value || job.quantity),
        lending_date: $("#editJobLendingDate").value || job.lending_date,
        return_date: $("#editJobReturnDate").value,
      }),
    });
    showToast(`Jobb ${job.request_id} uppdaterades.`);
    await refreshAll();
    openJobDetail(job.request_id);
  } catch (error) {
    showToast(error.message);
  }
}

async function sendPickupReadyEmail(requestId, button = null) {
  if (button?.disabled) return;
  try {
    if (button) button.disabled = true;
    const data = await api("/api/loan-requests/pickup-email", {
      method: "POST",
      body: JSON.stringify({ request_id: requestId }),
    });
    showToast(state.language === "en" ? `Pickup email sent: ${data.sent}.` : `Hämtningsmail skickat: ${data.sent}.`);
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

async function returnItem(loanId) {
  const loan = state.loans.find((item) => item.loan_id === loanId);
  if (!loan) return;
  setView("return");
  selectReturnUser(loan.user_id);
  const checkbox = $(`[data-return-select="${loanId}"]`);
  if (checkbox) checkbox.checked = true;
  updateReturnButtons();
}

async function saveUser(event) {
  event.preventDefault();
  try {
    sanitizePhoneField("#newUserPhone");
    const payload = {
      first_name: $("#newUserFirstName").value,
      last_name: $("#newUserLastName").value,
      email: $("#newUserEmail").value,
      phone: $("#newUserPhone").value,
      company: $("#newUserCompany").value,
      alias: $("#newUserAlias").value,
      department: $("#newUserDepartment").value,
      department_name: $("#newUserDepartmentName").value,
      role: $("#newUserRole").value,
      active: $("#newUserActive").checked,
    };
    if (!state.editingUserId) {
      payload.privacy_notice_acknowledged = $("#newUserPrivacyAcknowledged").checked;
    }
    if (state.editingUserId) payload.user_id = state.editingUserId;

    const data = await api("/api/users", {
      method: state.editingUserId ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    showToast(state.editingUserId ? `Användare ${data.user_id} uppdaterades.` : t("toast.userCreated", { id: data.user_id }));
    resetUserForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

function startEditUser(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  if (!user) return;
  state.editingUserId = userId;
  $("#newUserFirstName").value = user.first_name || user.name?.split(" ")[0] || "";
  $("#newUserLastName").value = user.last_name || user.name?.split(" ").slice(1).join(" ") || "";
  $("#newUserEmail").value = user.email || "";
  $("#newUserPhone").value = user.phone || "";
	  $("#newUserCompany").value = user.company || "";
	  $("#newUserAlias").value = user.alias || "";
	  $("#newUserDepartment").value = user.department || "";
	  $("#newUserDepartmentName").value = user.department_name || "";
  syncDepartmentFromGroup("#newUserDepartmentName", "#newUserDepartment");
  $("#newUserRole").value = user.role || "operator";
  $("#newUserActive").checked = user.active !== 0;
  $("#newUserPrivacyAcknowledgement").hidden = true;
  $("#newUserPrivacyAcknowledged").required = false;
  $("#saveUserButton").textContent = "Spara ändringar";
  $("#cancelUserEditButton").style.display = "block";
  showAdminSettingsSection("create-user");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetUserForm() {
  state.editingUserId = null;
  $("#addUserForm").reset();
  $("#newUserDepartment").readOnly = false;
  $("#newUserActive").checked = true;
  $("#newUserPrivacyAcknowledgement").hidden = false;
  $("#newUserPrivacyAcknowledged").required = true;
  $("#saveUserButton").textContent = "Skapa användare";
  $("#cancelUserEditButton").style.display = "none";
}

async function removeUser(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  const name = user ? user.name : userId;
  if (!confirm(`Ta bort ${name} (${userId}) från aktiva användare?`)) return;
  try {
    await api(`/api/users?user_id=${encodeURIComponent(userId)}`, { method: "DELETE" });
    showToast(`Användare ${userId} togs bort.`);
    if (state.editingUserId === userId) resetUserForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleBorrowOverride(userId, enabled) {
  const user = state.users.find((item) => item.user_id === userId);
  const name = user?.name || userId;
  const prompt = enabled
    ? `Tillåt ${name} att låna trots sena lån?`
    : `Ta bort manuell lånetillåtelse för ${name}?`;
  if (!confirm(prompt)) return;
  try {
    await api("/api/users/borrow-override", {
      method: "POST",
      body: JSON.stringify({ user_id: userId, enabled }),
    });
    showToast(enabled ? `${name} får låna manuellt.` : `Manuell lånetillåtelse borttagen för ${name}.`);
    await refreshAll();
    showAdminSettingsSection("users");
  } catch (error) {
    showToast(error.message);
  }
}

async function saveGroup(event) {
  event.preventDefault();
  try {
    const payload = {
      name: $("#newGroupName").value,
      department: $("#newGroupDepartment").value,
    };
    if (state.editingGroupId) payload.group_id = state.editingGroupId;
    const data = await api("/api/groups", {
      method: state.editingGroupId ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    showToast(state.editingGroupId ? `Grupp ${data.name} uppdaterades.` : `Grupp ${data.name} skapades.`);
    resetGroupForm();
    await refreshAll();
    showAdminSettingsSection("groups");
  } catch (error) {
    showToast(error.message);
  }
}

async function deleteGroup(groupId) {
  const group = state.groups.find((item) => item.group_id === groupId);
  const name = group?.name || groupId;
  if (!confirm(`Ta bort gruppen ${name}?`)) return;
  try {
    await api(`/api/groups?group_id=${encodeURIComponent(groupId)}`, { method: "DELETE" });
    showToast(`Grupp ${name} togs bort.`);
    if (state.editingGroupId === groupId) resetGroupForm();
    await refreshAll();
    showAdminSettingsSection("groups");
  } catch (error) {
    showToast(error.message);
  }
}

async function saveSystemSettings(event) {
  event?.preventDefault();
  try {
    state.systemSettings = await api("/api/system-settings", {
      method: "PUT",
      body: JSON.stringify({
        modbus_enabled: $("#modbusEnabled").checked,
        modbus_host: $("#modbusHost").value,
        modbus_port: $("#modbusPort").value,
        modbus_unit_id: $("#modbusUnitId").value,
        modbus_register_start: $("#modbusRegisterStart").value,
        smtp_enabled: $("#smtpEnabled").checked,
        smtp_host: $("#smtpHost").value,
        smtp_port: $("#smtpPort").value,
        smtp_username: $("#smtpUsername").value,
        smtp_password: $("#smtpPassword").value,
        smtp_from_address: $("#smtpFromAddress").value,
        smtp_use_tls: $("#smtpUseTls").checked,
        teams_enabled: isChecked("#teamsEnabled"),
        teams_group_recipient: fieldValue("#teamsGroupRecipient"),
        teams_subject_prefix: fieldValue("#teamsSubjectPrefix", "TEAMS"),
        teams_ehlo_name: state.systemSettings.teams_ehlo_name || "mailgot.ut.volvo.com",
        notification_simulation_enabled: isChecked("#notificationSimulationEnabled"),
        notification_simulation_recipient: fieldValue("#notificationSimulationRecipient"),
        notification_recipients: state.systemSettings.notification_recipients || "",
        notification_recipients_new_job: state.systemSettings.notification_recipients_new_job || "",
        notification_recipients_returned_loan: state.systemSettings.notification_recipients_returned_loan || "",
        notification_recipients_low_stock: state.systemSettings.notification_recipients_low_stock || "",
        notification_recipients_empty_stock: state.systemSettings.notification_recipients_empty_stock || "",
        loan_reminder_days: fieldValue("#dueSoonDays", fieldValue("#loanReminderDays", "10")),
        due_soon_days: fieldValue("#dueSoonDays", fieldValue("#loanReminderDays", "10")),
        max_loan_days: fieldValue("#maxLoanDays", "90"),
        overdue_repeat_days: fieldValue("#overdueRepeatDays", "3"),
        overdue_block_enabled: isChecked("#overdueBlockEnabled"),
        overdue_block_limit: fieldValue("#overdueBlockLimit", "3"),
        notify_new_job: isChecked("#notifyNewJobAutomation"),
        notify_pickup_ready: isChecked("#notifyPickupReady"),
        notify_returned_loan: isChecked("#notifyReturnedLoan"),
        notify_low_stock: isChecked("#notifyLowStockAutomation"),
        notify_empty_stock: isChecked("#notifyEmptyStock"),
        notify_loan_reminders: isChecked("#notifyLoanReminders") || isChecked("#notifyDueSoon"),
        notify_due_soon: isChecked("#notifyDueSoon"),
        notify_overdue: isChecked("#notifyOverdue"),
        notify_overdue_repeat: isChecked("#notifyOverdueRepeat"),
        ...messageTemplatePayload(),
      }),
    });
    renderSystemSettings();
    showToast("Systeminställningarna sparades.");
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

function isChecked(selector) {
  return Boolean($(selector)?.checked);
}

function fieldValue(selector, fallback = "") {
  return $(selector)?.value ?? fallback;
}

function messageTemplatePayload() {
  const payload = {};
  messageTemplateFields.forEach(([id, key]) => {
    payload[key] = fieldValue(`#${id}`);
  });
  return payload;
}

async function sendLoanReminders() {
  const button = $("#sendRemindersButton");
  if (button?.disabled) return;
  try {
    if (button) button.disabled = true;
    const data = await api("/api/reminders/send", { method: "POST", body: JSON.stringify({}) });
    const skipped = Number(data.skipped_recent || 0);
    const extra = skipped ? ` ${skipped} hoppades över eftersom de nyligen påmints.` : "";
    showToast(`Påminnelser skickade: ${data.sent} av ${data.matched}.${extra}`);
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

function sanitizePhoneField(selector) {
  const input = $(selector);
  if (!input) return;
  input.value = input.value.replace(/[^0-9+ ()-]/g, "");
}

async function sendTeamsTestMessage() {
  const button = $("#sendTeamsTestButton");
  if (button?.disabled) return;
  try {
    if (button) button.disabled = true;
    await saveSystemSettings();
    const data = await api("/api/teams/test", { method: "POST", body: JSON.stringify({}) });
    showToast(data.simulation ? "Teams-test simulerat i serverloggen." : "Teams-test skickat.");
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

async function sendLoanReminder(loanId, button = null) {
  if (button?.disabled) return;
  try {
    if (button) button.disabled = true;
    const data = await api("/api/loans/reminder", {
      method: "POST",
      body: JSON.stringify({ loan_id: loanId }),
    });
    showToast(state.language === "en" ? `Reminder sent: ${data.sent}.` : `Påminnelse skickad: ${data.sent}.`);
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) button.disabled = false;
  }
}

async function saveQuickUser(event) {
  event.preventDefault();
  try {
    sanitizePhoneField("#quickUserPhone");
    const data = await api("/api/users", {
      method: "POST",
      body: JSON.stringify({
        first_name: $("#quickUserFirstName").value,
        last_name: $("#quickUserLastName").value,
        email: $("#quickUserEmail").value,
        phone: $("#quickUserPhone").value,
        company: $("#quickUserCompany").value,
        alias: $("#quickUserAlias").value,
        department: $("#quickUserDepartment").value,
        department_name: $("#quickUserDepartmentName").value,
        role: "operator",
        active: true,
        privacy_notice_acknowledged: $("#quickUserPrivacyAcknowledged").checked,
      }),
    });
    showToast(t("toast.userCreated", { id: data.user_id }));
    $("#quickUserForm").reset();
    closeQuickUserModal();
    await refreshAll();
    selectCheckoutUser(data.user_id);
  } catch (error) {
    showToast(error.message);
  }
}

function openQuickUserModal() {
  $("#quickUserModal").classList.add("open");
  $("#quickUserModal").setAttribute("aria-hidden", "false");
  $("#quickUserFirstName").focus();
}

function closeQuickUserModal() {
  $("#quickUserModal").classList.remove("open");
  $("#quickUserModal").setAttribute("aria-hidden", "true");
}

function openUserScanModal() {
  $("#userScanModal").classList.add("open");
  $("#userScanModal").setAttribute("aria-hidden", "false");
  $("#closeUserScanButton").focus();
  scanCheckoutUserCard();
}

function closeUserScanModal() {
  $("#userScanModal").classList.remove("open");
  $("#userScanModal").setAttribute("aria-hidden", "true");
  $("#openUserScanButton").focus();
}

function openObjectScanModal() {
  $("#objectScanModal").classList.add("open");
  $("#objectScanModal").setAttribute("aria-hidden", "false");
  $("#closeObjectScanButton").focus();
}

function closeObjectScanModal() {
  $("#objectScanModal").classList.remove("open");
  $("#objectScanModal").setAttribute("aria-hidden", "true");
  $("#openObjectScanButton").focus();
}

async function readSmartcardUid() {
  const data = await api("/api/smartcard/read", { method: "POST", body: "{}" });
  return data.uid || "";
}

function updateAutoUserCardScan() {
  const checkoutIsActive = $("#checkoutView")?.classList.contains("active");
  if (checkoutIsActive && state.role !== "operator" && !window.loanRuntime?.simulation) {
    startAutoUserCardScan();
  } else {
    stopAutoUserCardScan();
  }
}

function startAutoUserCardScan() {
  if (state.autoUserCardScanTimer) return;
  autoScanCheckoutUserCard();
  state.autoUserCardScanTimer = setInterval(autoScanCheckoutUserCard, 1600);
}

function stopAutoUserCardScan() {
  if (!state.autoUserCardScanTimer) return;
  clearInterval(state.autoUserCardScanTimer);
  state.autoUserCardScanTimer = null;
  state.autoUserCardScanBusy = false;
}

function resetAutoUserCardScanMemory() {
  state.lastAutoUserCardUid = "";
  state.lastAutoUserCardAt = 0;
  state.lastUnknownAutoUserCardUid = "";
}

async function autoScanCheckoutUserCard() {
  if (state.autoUserCardScanBusy || !$("#checkoutView")?.classList.contains("active")) return;
  state.autoUserCardScanBusy = true;
  try {
    const data = await api("/api/users/scan-card", { method: "POST", body: "{}" });
    const uid = data.uid || "";
    if (!uid) return;

    const now = Date.now();
    if (uid === state.lastAutoUserCardUid && now - state.lastAutoUserCardAt < 8000 && $("#checkoutUser").value) return;
    state.lastAutoUserCardUid = uid;
    state.lastAutoUserCardAt = now;

    const user = data.user || state.users.find((item) => String(item.rfid_code || "").toLowerCase() === uid.toLowerCase());
    if (!user) {
      if (uid !== state.lastUnknownAutoUserCardUid) {
        state.lastUnknownAutoUserCardUid = uid;
        showToast(`Kort UID ${uid} är inte kopplat till någon aktiv användare.`, "warning");
      }
      return;
    }

    state.lastUnknownAutoUserCardUid = "";
    if ($("#checkoutUser").value !== user.user_id) {
      selectCheckoutUser(user.user_id);
      showToast(`Användare vald: ${user.name}`);
    }
  } catch (error) {
    // Auto-scanning stays quiet while no card is present or the reader is momentarily busy.
  } finally {
    state.autoUserCardScanBusy = false;
  }
}

async function scanUserCardCode() {
  const button = $("#scanUserCardCodeButton");
  const originalText = button?.textContent || "";
  try {
    if (button) {
      button.disabled = true;
      button.textContent = "Läser...";
    }
    const uid = await readSmartcardUid();
    $("#userCardCode").value = uid;
    showToast(`Kort läst: ${uid}`);
  } catch (error) {
    showToast(error.message);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = originalText;
    }
  }
}

async function scanCheckoutUserCard() {
  const button = $("#readUserCardButton");
  const originalText = button?.textContent || "";
  try {
    if (button) {
      button.disabled = true;
      button.textContent = "Läser...";
    }
    $("#userScanStatusTitle").textContent = "Läser kort";
    $("#userScanStatusText").textContent = "Håll kortet stilla på läsaren.";

    const data = await api("/api/users/scan-card", { method: "POST", body: "{}" });
    const uid = data.uid || "";
    const user = data.user || state.users.find((item) => String(item.rfid_code || "").toLowerCase() === uid.toLowerCase());
    if (!user) {
      $("#userScanStatusTitle").textContent = "Kortet hittades inte";
      $("#userScanStatusText").textContent = uid ? `UID ${uid} är inte kopplat till någon aktiv användare.` : "Kortet är inte kopplat till någon aktiv användare.";
      return;
    }

    selectCheckoutUser(user.user_id);
    $("#userScanStatusTitle").textContent = "Användare vald";
    $("#userScanStatusText").textContent = `${user.name} är vald i låneformuläret.`;
    showToast(`Användare vald: ${user.name}`);
    setTimeout(closeUserScanModal, 700);
  } catch (error) {
    $("#userScanStatusTitle").textContent = "Kunde inte läsa kort";
    $("#userScanStatusText").textContent = error.message;
    showToast(error.message);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = originalText;
    }
  }
}

function openUserCardModal(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  if (!user) return;
  state.cardUserId = userId;
  $("#userCardTitle").textContent = `Lägg till kort - ${user.name}`;
  $("#userCardCode").value = user.rfid_code || "";
  $("#userCardModal").classList.add("open");
  $("#userCardModal").setAttribute("aria-hidden", "false");
  $("#userCardCode").focus();
}

function closeUserCardModal() {
  $("#userCardModal").classList.remove("open");
  $("#userCardModal").setAttribute("aria-hidden", "true");
  state.cardUserId = null;
}

function generateUserCardCode() {
  const randomPart = window.crypto?.getRandomValues
    ? Array.from(window.crypto.getRandomValues(new Uint8Array(6)), (value) => value.toString(16).padStart(2, "0")).join("").toUpperCase()
    : String(Date.now());
  $("#userCardCode").value = `KORT-${randomPart}`;
}

async function saveUserCard(event) {
  event.preventDefault();
  if (!state.cardUserId) return;
  try {
    const data = await api("/api/users/card", {
      method: "POST",
      body: JSON.stringify({
        user_id: state.cardUserId,
        rfid_code: $("#userCardCode").value,
      }),
    });
    showToast(`Kortkod sparad: ${data.rfid_code}`);
    closeUserCardModal();
    await refreshAll();
    showAdminSettingsSection("users");
  } catch (error) {
    showToast(error.message);
  }
}

async function saveObject(event) {
  event.preventDefault();
  try {
    const imageData = await readSelectedObjectImage();
    const isEditing = Boolean(state.editingObjectId);
    const data = await api("/api/objects", {
      method: isEditing ? "PUT" : "POST",
      body: JSON.stringify({
        object_id: $("#newObjectId").value,
        name: $("#newObjectName").value,
        category: $("#newObjectCategory").value,
        item_type: $("#newObjectType").value,
        description: $("#newObjectDescription").value,
        article_number: $("#newObjectArticle").value,
        supplier_article_number: $("#newObjectSupplierArticle").value,
        location: $("#newObjectLocation").value,
        storage_location_2: $("#newObjectStorageLocation2").value,
        tornado_id: $("#newObjectTornado").value,
        door_id: $("#newObjectDoor").value,
        belongs_to_instrument: $("#newObjectBelongsToInstrument").value,
        device: $("#newObjectDevice").value,
        belongs_to: $("#newObjectBelongsTo").value,
        last_changed: $("#newObjectLastChanged").value,
        search_words: $("#newObjectSearchWords").value,
        tray_for: $("#newObjectTrayFor").value,
        lift_tray: $("#newObjectLiftTray").value,
        total_quantity: Number($("#newObjectTotal").value),
        available_quantity: Number($("#newObjectAvailable").value),
        min_quantity: Number($("#newObjectMin").value),
        is_consumable: $("#newObjectConsumable").checked,
        image_data: imageData,
        remove_image: $("#removeObjectImage").checked,
      }),
    });
    showToast(t("toast.objectSaved", { id: data.object_id }));
    resetObjectForm();
    await refreshAll();
    setView("objects");
  } catch (error) {
    showToast(error.message);
  }
}

function startEditObject(objectId) {
  if (state.role === "operator") return;
  const item = state.objects.find((objectItem) => objectItem.object_id === objectId);
  if (!item) return;

  state.editingObjectId = objectId;
  $("#objectFormTitle").textContent = `Redigera objekt ${objectId}`;
  $("#saveObjectButton").textContent = "Spara ändringar";
  $("#cancelObjectEditButton").style.display = "block";
  $("#newObjectId").value = item.object_id;
  $("#newObjectId").readOnly = true;
  $("#newObjectName").value = item.name;
  $("#newObjectCategory").value = item.category;
  $("#newObjectType").value = item.item_type || "";
  $("#newObjectDescription").value = item.description || "";
  $("#newObjectArticle").value = item.article_number || "";
  $("#newObjectSupplierArticle").value = item.supplier_article_number || "";
  $("#newObjectLocation").value = item.location;
  $("#newObjectStorageLocation2").value = item.storage_location_2 || "";
  $("#newObjectTornado").value = item.tornado_id;
  $("#newObjectDoor").value = item.door_id;
  $("#newObjectBelongsToInstrument").value = item.belongs_to_instrument || "";
  $("#newObjectDevice").value = item.device || "";
  $("#newObjectBelongsTo").value = item.belongs_to || "";
  $("#newObjectLastChanged").value = item.last_changed || "";
  $("#newObjectSearchWords").value = item.search_words || "";
  $("#newObjectTrayFor").value = item.tray_for || "";
  $("#newObjectLiftTray").value = item.lift_tray || "";
  $("#newObjectTotal").value = item.total_quantity;
  $("#newObjectAvailable").value = item.available_quantity;
  $("#newObjectMin").value = item.min_quantity;
  $("#newObjectConsumable").checked = isConsumableObject(item);
  $("#removeObjectImage").checked = false;

  if (item.image_data) {
    $("#newObjectImagePreview").innerHTML = `<img src="${escapeHtml(item.image_data)}" alt="">`;
  } else {
    $("#newObjectImagePreview").innerHTML = "<span>Ingen bild vald</span>";
  }

  setView("admin");
  showAdminSettingsSection("add-object");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

async function deleteObject(objectId) {
  if (state.role === "operator") return;
  const item = state.objects.find((objectItem) => objectItem.object_id === objectId);
  const name = item ? item.name : objectId;
  if (!confirm(`Ta bort ${name} (${objectId}) från databasen?`)) return;

  try {
    await api(`/api/objects?object_id=${encodeURIComponent(objectId)}`, { method: "DELETE" });
    showToast(t("toast.objectDeleted", { id: objectId }));
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function returnSelectedLoans(all = false) {
  if (state.returnBusy) return;
  const userId = $("#returnUser").value;
  const loanIds = all ? state.loans.filter((loan) => loan.user_id === userId).map((loan) => loan.loan_id)
    : [...document.querySelectorAll("[data-return-select]:checked")].map((input) => Number(input.dataset.returnSelect));
  if (!userId || !loanIds.length) return;
  try {
    const items = loanIds.map((loanId) => {
      const loan = state.loans.find((entry) => entry.loan_id === loanId && entry.user_id === userId);
      if (!loan) throw new Error(t("return.invalid"));
      const remaining = loan.remaining_quantity ?? loan.quantity;
      const quantity = all ? remaining : Number($(`[data-return-quantity="${loanId}"]`).value);
      const damaged = Number($(`[data-return-damaged="${loanId}"]`).value);
      const description = $(`[data-return-description="${loanId}"]`).value.trim();
      if (!Number.isInteger(quantity) || quantity < 1 || quantity > remaining ||
          !Number.isInteger(damaged) || damaged < 0 || damaged > quantity ||
          (damaged > 0 && !description) || (damaged === 0 && description) || description.length > 2000) {
        throw new Error(t("return.invalid"));
      }
      return { loan_id: loanId, quantity, damaged_quantity: damaged, damage_description: description,
        expected_returned_quantity: loan.returned_quantity || 0 };
    });
    const quantity = items.reduce((sum, item) => sum + item.quantity, 0);
    const damaged = items.reduce((sum, item) => sum + item.damaged_quantity, 0);
    if (!confirm(t("return.confirm", { quantity, damaged }))) return;
    state.returnBusy = true;
    updateReturnButtons();
    const data = await api("/api/return", { method: "POST", body: JSON.stringify({ user_id: userId, items }) });
    state.returnSummary = { ...data, user_id: userId };
    renderReturnSummary();
    showToast(t("return.saved"));
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    state.returnBusy = false;
    updateReturnButtons();
  }
}

async function resolveDamage(returnId, resolution) {
  if (state.role === "operator" || state.damageBusy) return;
  const item = state.damagedReturns.find((entry) => entry.return_id === returnId);
  if (!item || !confirm(t(`damage.confirm.${resolution}`, { quantity: item.damaged_quantity, name: item.object_name }))) return;
  state.damageBusy = true;
  renderDamagedReturns();
  try {
    await api("/api/damaged-returns/resolve", { method: "POST",
      body: JSON.stringify({ return_id: returnId, resolution, confirmed: true }) });
    showToast(t("damage.saved"));
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  } finally {
    state.damageBusy = false;
    renderDamagedReturns();
  }
}

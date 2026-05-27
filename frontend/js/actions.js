// API-backed UI actions.
// ============================================================
// HANDLINGAR
// Funktioner som skapar, uppdaterar eller tar bort data via API.
// ============================================================

async function checkout() {
  try {
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
  $("#checkoutObjectId").value = "";
  updateCheckoutInfo();
  $("#checkoutUser").value = "";
  $("#checkoutUserSearch").value = "";
  renderCheckoutUserDetails();
  $("#checkoutEngineId").value = "";
  $("#checkoutProjectNumber").value = "";
  $("#checkoutQuantity").value = "1";
  setDefaultDates();
}

async function requestLoan() {
  try {
    const userId = resolveCheckoutUserId();
    if (!userId) {
      showToast(t("toast.chooseUser"));
      return;
    }
    const data = await api("/api/loan-requests", {
      method: "POST",
      body: JSON.stringify(checkoutPayload(userId)),
    });
    showToast(t("toast.requestCreated", { id: data.request_id }));
    clearCheckoutForm();
    await refreshAll();
  } catch (error) {
    showToast(error.message);
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
    showToast(state.language === "en" ? "Article reported out of stock." : "Artikeln anmäldes som slut på lager.");
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

async function markPickupCollected(requestId) {
  await updateJobStatus(requestId, "loaned");
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

async function returnItem(loanId) {
  try {
    if (!loanId) {
      showToast("Välj ett aktivt lån att återlämna.");
      return;
    }
    const data = await api("/api/return", {
      method: "POST",
      body: JSON.stringify({ identifier: String(loanId) }),
    });
    showToast(t("toast.loanReturned", { id: data.loan_id }));
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

async function saveUser(event) {
  event.preventDefault();
  try {
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
  $("#newUserRole").value = user.role || "operator";
  $("#newUserActive").checked = user.active !== 0;
  $("#saveUserButton").textContent = "Spara ändringar";
  $("#cancelUserEditButton").style.display = "block";
  showAdminSettingsSection("create-user");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function resetUserForm() {
  state.editingUserId = null;
  $("#addUserForm").reset();
  $("#newUserActive").checked = true;
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
        notification_recipients: $("#notificationRecipients").value,
        notification_recipients_new_job: state.systemSettings.notification_recipients_new_job || "",
        notification_recipients_returned_loan: state.systemSettings.notification_recipients_returned_loan || "",
        notification_recipients_low_stock: state.systemSettings.notification_recipients_low_stock || "",
        notification_recipients_empty_stock: state.systemSettings.notification_recipients_empty_stock || "",
        loan_reminder_days: fieldValue("#dueSoonDays", fieldValue("#loanReminderDays", "10")),
        due_soon_days: fieldValue("#dueSoonDays", fieldValue("#loanReminderDays", "10")),
        overdue_repeat_days: fieldValue("#overdueRepeatDays", "3"),
        overdue_block_enabled: isChecked("#overdueBlockEnabled"),
        overdue_block_limit: fieldValue("#overdueBlockLimit", "3"),
        notify_new_job: isChecked("#notifyNewJobAutomation"),
        notify_returned_loan: isChecked("#notifyReturnedLoan"),
        notify_low_stock: isChecked("#notifyLowStockAutomation"),
        notify_empty_stock: isChecked("#notifyEmptyStock"),
        notify_loan_reminders: isChecked("#notifyLoanReminders") || isChecked("#notifyDueSoon"),
        notify_due_soon: isChecked("#notifyDueSoon"),
        notify_overdue: isChecked("#notifyOverdue"),
        notify_overdue_repeat: isChecked("#notifyOverdueRepeat"),
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

async function sendLoanReminders() {
  try {
    const data = await api("/api/reminders/send", { method: "POST", body: JSON.stringify({}) });
    showToast(`Påminnelser skickade: ${data.sent} av ${data.matched}.`);
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }
}

function fillDepartmentFromDepartmentName(departmentNameSelector, departmentSelector) {
  const departmentName = $(departmentNameSelector).value.trim().toLowerCase();
  if (!departmentName) return;
  const match = state.users.find((user) => (user.department_name || "").toLowerCase() === departmentName);
  if (match?.department && !$(departmentSelector).value.trim()) {
    $(departmentSelector).value = match.department;
  }
}

async function saveQuickUser(event) {
  event.preventDefault();
  try {
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

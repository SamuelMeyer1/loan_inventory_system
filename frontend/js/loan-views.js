// Loan, pickup, return, and receipt views.
// ============================================================
// FORMULARINFORMATION
// Uppdaterar informationsrutor nar anvandaren skriver i formular.
// ============================================================

function selectedCheckoutObject() {
  const term = $("#checkoutObjectId").value.trim().toLowerCase();
  const selected = state.objects.find((item) => item.object_id === $("#checkoutObjectInstrumentId").value);
  if (selected && [selected.object_id.toLowerCase(), selected.name.toLowerCase()].includes(term)) return selected;
  return state.objects.find((item) =>
    item.object_id.toLowerCase() === term || item.name.toLowerCase() === term
  );
}

function remainingLoanQuantity(item) {
  const inCart = state.loanCart.reduce((sum, entry) => sum + (entry.object_id === item.object_id ? entry.quantity : 0), 0);
  return Math.max(0, item.available_quantity - inCart);
}

function validateLoanArticle(item, quantity, available = item?.available_quantity) {
  if (!item) throw new Error(t("checkout.articleUnavailable"));
  if (isConsumableObject(item)) throw new Error(t("checkout.consumableNotLoanable"));
  if (!Number.isInteger(quantity) || quantity <= 0) throw new Error(t("checkout.positiveQuantity"));
  if (!Number.isInteger(available) || available < 0) throw new Error(t("checkout.stockUnavailable"));
  if (quantity > available) throw new Error(t("checkout.stockExceeded", { name: item.name, count: available }));
}

function updateCheckoutInfo(selectedItem = null) {
  const item = selectedItem || selectedCheckoutObject();
  const disclosure = $("#checkoutObjectDisclosure");
  if (disclosure) {
    const objectId = item?.object_id || "";
    if (disclosure.dataset.objectId !== objectId) disclosure.open = false;
    disclosure.dataset.objectId = objectId;
    disclosure.hidden = !item;
  }
  $("#checkoutInfo").hidden = !item;
  const quantity = $("#checkoutQuantity");
  const remaining = item ? remainingLoanQuantity(item) : 0;
  const maximum = item && !isConsumableObject(item) ? Math.min(Number(quantity.dataset.max || 20), remaining) : 0;
  const previousQuantity = Number(quantity.value);
  quantity.innerHTML = Array.from({ length: maximum }, (_, index) => `<option value="${index + 1}">${index + 1}</option>`).join("");
  if (!maximum) quantity.innerHTML = `<option value="">${escapeHtml(t(item ? "checkout.noneRemaining" : "checkout.chooseArticle"))}</option>`;
  quantity.disabled = maximum === 0;
  quantity.value = maximum ? String(Math.min(Math.max(previousQuantity || 1, 1), maximum)) : "";
  $("#addLoanArticle").disabled = maximum === 0;
  if (!item) {
    [
      "InstrumentId",
      "Name",
      "Category",
      "Type",
      "Description",
      "Location",
      "Lift",
      "Quantity",
      "Status",
    ].forEach((field) => {
      const input = $(`#checkoutObject${field}`);
      if (input) input.value = "";
    });
    return;
  }
  $("#checkoutObjectInstrumentId").value = item.object_id || "";
  $("#checkoutObjectName").value = item.name || "";
  $("#checkoutObjectCategory").value = item.category || "";
  $("#checkoutObjectType").value = item.item_type || "";
  $("#checkoutObjectDescription").value = item.description || "";
  $("#checkoutObjectLocation").value = item.location || "";
  $("#checkoutObjectLift").value = item.lift_tray || item.door_id || "";
  $("#checkoutObjectQuantity").value = state.language === "en" ? `${remaining} of ${item.total_quantity}` : `${remaining} av ${item.total_quantity}`;
  $("#checkoutObjectStatus").value = statusText(remaining === 0 ? "Slut" : item.status || "");
}

function syncReturnDamageDescription(prefix, loanId) {
  const damaged = Number($(`[data-${prefix}-damaged="${loanId}"]`).value);
  const description = $(`[data-${prefix}-description="${loanId}"]`);
  const hasDamage = damaged > 0;
  description.hidden = !hasDamage;
  description.required = hasDamage;
  const label = description.closest("label");
  if (label) label.hidden = !hasDamage;
  if (!hasDamage) description.value = "";
}

function bindReturnDamageFields(container, prefix) {
  container.querySelectorAll(`[data-${prefix}-damaged]`).forEach((input) => {
    const loanId = input.getAttribute(`data-${prefix}-damaged`);
    syncReturnDamageDescription(prefix, loanId);
    input.addEventListener("input", () => syncReturnDamageDescription(prefix, loanId));
  });
}

function renderJobReturn() {
  $("#jobReturnError").hidden = true;
  $("#jobReturnError").textContent = "";
  $("#jobReturnItems").innerHTML = state.jobReturnLoans.map((loan) => {
    const remaining = loan.remaining_quantity ?? loan.quantity;
    return `<fieldset class="job-return-item">
      <legend>${escapeHtml(loan.object_name)} (${escapeHtml(loan.object_id)})</legend>
      <p>${escapeHtml(t("jobs.returnRemaining", { count: remaining }))}</p>
      <label>${escapeHtml(t("return.quantity"))}
        <input type="number" min="0" max="${remaining}" step="1" value="0" required data-job-return-quantity="${loan.loan_id}">
      </label>
      <label>${escapeHtml(t("return.damaged"))}
        <input type="number" min="0" max="${remaining}" step="1" value="0" required data-job-return-damaged="${loan.loan_id}">
      </label>
      <label hidden>${escapeHtml(t("return.description"))}
        <textarea hidden maxlength="2000" rows="2" data-job-return-description="${loan.loan_id}" placeholder="${escapeHtml(t("return.descriptionHint"))}"></textarea>
      </label>
    </fieldset>`;
  }).join("");
  bindReturnDamageFields($("#jobReturnItems"), "job-return");
}

function setJobReturnBusy(busy) {
  $("#jobReturnForm").querySelectorAll("fieldset, button").forEach((element) => { element.disabled = busy; });
}

function renderReturnLoans(preserveDraft = false) {
  const body = $("#returnLoansBody");
  if (!body) return;
  const draft = preserveDraft ? [...body.querySelectorAll("[data-return-select]")].map((input) => ({
    id: input.dataset.returnSelect, checked: input.checked,
    quantity: $(`[data-return-quantity="${input.dataset.returnSelect}"]`).value,
    damaged: $(`[data-return-damaged="${input.dataset.returnSelect}"]`).value,
    description: $(`[data-return-description="${input.dataset.returnSelect}"]`).value,
  })) : [];
  const selectedUserId = $("#returnUser")?.value || "";
  const empty = $("#returnLoansEmpty");
  const matches = selectedUserId
    ? state.loans.filter((loan) => loan.user_id === selectedUserId)
    : [];

  body.innerHTML = matches.map((loan) => `
    <tr class="${loan.overdue ? "late" : ""}">
      <td><input type="checkbox" data-return-select="${loan.loan_id}" aria-label="${escapeHtml((state.language === 'en' ? 'Return ' : 'Återlämna ') + loan.object_name)}"> ${loan.loan_id}${loan.request_group_id ? `<small class="request-reference">${state.language === "en" ? "Request" : "Förfrågan"} #${loan.request_group_id}</small>` : ""}</td>
      <td>${escapeHtml(loan.object_name)} (${escapeHtml(loan.object_id)})</td>
      <td>${loan.remaining_quantity ?? loan.quantity}<small class="request-reference">${t("return.alreadyReturned", { count: loan.returned_quantity || 0 })}</small></td>
      <td><input class="return-quantity" type="number" min="1" max="${loan.remaining_quantity ?? loan.quantity}" step="1" value="${loan.remaining_quantity ?? loan.quantity}" data-return-quantity="${loan.loan_id}" aria-label="${escapeHtml(t("return.quantity") + ' ' + loan.object_name)}"></td>
      <td><input class="return-quantity" type="number" min="0" max="${loan.remaining_quantity ?? loan.quantity}" step="1" value="0" data-return-damaged="${loan.loan_id}" aria-label="${escapeHtml(t("return.damaged") + ' ' + loan.object_name)}"></td>
      <td><textarea hidden maxlength="2000" rows="2" data-return-description="${loan.loan_id}" aria-label="${escapeHtml(t("return.description") + ' ' + loan.object_name)}" placeholder="${escapeHtml(t("return.descriptionHint"))}"></textarea></td>
      <td>${formatTime(loan.due_time)}</td>
    </tr>
  `).join("");
  draft.forEach((item) => {
    const input = $(`[data-return-select="${item.id}"]`);
    if (!input) return;
    input.checked = item.checked;
    $(`[data-return-quantity="${item.id}"]`).value = item.quantity;
    $(`[data-return-damaged="${item.id}"]`).value = item.damaged;
    $(`[data-return-description="${item.id}"]`).value = item.description;
  });

  bindReturnDamageFields(body, "return");
  body.querySelectorAll("[data-return-quantity], [data-return-damaged], [data-return-description]").forEach((input) => {
    input.addEventListener("input", () => {
      const id = input.dataset.returnQuantity || input.dataset.returnDamaged || input.dataset.returnDescription;
      $(`[data-return-select="${id}"]`).checked = true;
      updateReturnButtons();
    });
  });

  document.querySelectorAll("[data-return-select]").forEach((input) => input.addEventListener("change", updateReturnButtons));
  updateReturnButtons();
  if (empty) {
    empty.textContent = selectedUserId
      ? matches.length
        ? ""
        : t("return.noLoans")
      : t("return.chooseBorrower");
  }
  renderReturnSummary();
}

function returnBorrowers() {
  const users = new Map(state.users.map((user) => [user.user_id, user]));
  state.loans.forEach((loan) => {
    if (!users.has(loan.user_id)) {
      users.set(loan.user_id, { user_id: loan.user_id, name: loan.user_name,
        department: loan.user_department, email: loan.user_email });
    }
  });
  return [...users.values()];
}

function renderReturnUserSuggestions() {
  const term = $("#returnUserSearch").value.trim().toLowerCase();
  const suggestions = $("#returnUserSuggestions");
  $("#returnUser").value = "";
  renderReturnLoans();
  if (!term) {
    suggestions.classList.remove("visible");
    suggestions.innerHTML = "";
    return;
  }

  const labels = userLabels();
  const matches = returnBorrowers().filter((user) => userSearchText(user).includes(term)).slice(0, 8);
  suggestions.innerHTML = matches.map((user) => `
    <button class="suggestion-button" type="button" data-select-return-user="${escapeHtml(user.user_id)}">
      <strong>${escapeHtml(labels.get(user.user_id) || user.name)}</strong>
      <span>${escapeHtml([user.company, user.department_name || user.department, user.alias].filter(Boolean).join(" · "))}</span>
    </button>
  `).join("");
  suggestions.classList.toggle("visible", matches.length > 0);
  document.querySelectorAll("[data-select-return-user]").forEach((button) => {
    button.addEventListener("click", () => selectReturnUser(button.dataset.selectReturnUser));
  });
}

function renderPickupItems() {
  const body = $("#pickupBody");
  if (!body) return;
  const selectedUserId = $("#pickupUser")?.value || resolveUserSearchTerm("#pickupUserSearch");
  const empty = $("#pickupEmpty");
  const matches = selectedUserId
    ? state.jobs.filter((job) => job.user_id === selectedUserId && job.status === "prepared")
    : [];
  const groups = groupLoanRequestRows(matches);

  body.innerHTML = groups.map((group) => {
    const first = group.items[0];
    const objects = group.items.map((job) =>
      `${escapeHtml(job.object_name)} (${escapeHtml(job.object_id)}) × ${job.quantity}`
    ).join("<br>");
    return `
    <tr>
      <td>${group.id}</td>
      <td>${objects}</td>
      <td>${escapeHtml(first.user_name)}</td>
      <td>${escapeHtml(first.user_department || "")}</td>
      <td>${escapeHtml(first.engine_id || "")}</td>
      <td>${escapeHtml(first.project_number || "")}</td>
      <td>${group.items.reduce((sum, job) => sum + Number(job.quantity), 0)}</td>
      <td>${escapeHtml(first.lending_date || "")}</td>
      <td>${escapeHtml(first.return_date || "")}</td>
      <td>${statusBadge("Aktiv")}</td>
      <td><button class="primary-button table-return-button" type="button" data-pickup-group="${group.id}">${state.language === "en" ? "Everything collected" : "Allt hämtat"}</button></td>
    </tr>
  `;
  }).join("");

  document.querySelectorAll("[data-pickup-group]").forEach((button) => {
    button.addEventListener("click", () => markPickupCollected(Number(button.dataset.pickupGroup)));
  });

  if (empty) {
    empty.textContent = selectedUserId
      ? matches.length
        ? ""
        : "Den valda användaren har inga artiklar klara att hämta."
      : "Sök på ditt namn för att se artiklar som är klara att hämta.";
  }
}

function renderPickupUserSuggestions() {
  const term = $("#pickupUserSearch").value.trim().toLowerCase();
  const suggestions = $("#pickupUserSuggestions");
  $("#pickupUser").value = "";
  if (!term) {
    suggestions.classList.remove("visible");
    suggestions.innerHTML = "";
    renderPickupItems();
    return;
  }

  const labels = userLabels();
  const matches = state.users.filter((user) => userSearchText(user).includes(term)).slice(0, 8);
  suggestions.innerHTML = matches.map((user) => `
    <button class="suggestion-button" type="button" data-select-pickup-user="${escapeHtml(user.user_id)}">
      <strong>${escapeHtml(labels.get(user.user_id) || user.name)}</strong>
      <span>${escapeHtml([user.company, user.department_name || user.department, user.alias].filter(Boolean).join(" · "))}</span>
    </button>
  `).join("");
  suggestions.classList.toggle("visible", matches.length > 0);
  document.querySelectorAll("[data-select-pickup-user]").forEach((button) => {
    button.addEventListener("click", () => selectPickupUser(button.dataset.selectPickupUser));
  });
  renderPickupItems();
}

function selectPickupUser(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  if (!user) return;
  const labels = userLabels();
  $("#pickupUser").value = user.user_id;
  $("#pickupUserSearch").value = labels.get(user.user_id) || user.name;
  $("#pickupUserSuggestions").classList.remove("visible");
  renderPickupItems();
}

function renderMyLoans() {
  const body = $("#myLoansBody");
  if (!body) return;
  const selectedUserId = $("#myLoansUser")?.value || resolveUserSearchTerm("#myLoansUserSearch");
  const empty = $("#myLoansEmpty");
  const matches = selectedUserId
    ? state.loans.filter((loan) => loan.user_id === selectedUserId)
    : [];

  body.innerHTML = matches.map((loan) => `
    <tr class="${loan.overdue ? "late" : ""}">
      <td>${loan.loan_id}</td>
      <td>${escapeHtml(loan.object_name)} (${escapeHtml(loan.object_id)})</td>
      <td>${escapeHtml(loan.user_name)}</td>
      <td>${escapeHtml(loan.user_department || "")}</td>
      <td>${escapeHtml(loan.engine_id || "")}</td>
      <td>${escapeHtml(loan.project_number || "")}</td>
      <td>${loan.remaining_quantity ?? loan.quantity}</td>
      <td>${formatTime(loan.checkout_time)}</td>
      <td>${formatTime(loan.due_time)}</td>
      <td><strong>${escapeHtml(daysUntilDueText(loan.due_time))}</strong></td>
      <td>${statusBadge(loan.overdue ? "Sen" : "Aktiv")}</td>
    </tr>
  `).join("");

  if (empty) {
    empty.textContent = selectedUserId
      ? matches.length
        ? ""
        : "Den valda användaren har inga aktiva utlåningar."
      : "Sök på ditt namn för att se dina aktiva utlåningar.";
  }
}

function renderMyLoansUserSuggestions() {
  const term = $("#myLoansUserSearch").value.trim().toLowerCase();
  const suggestions = $("#myLoansUserSuggestions");
  $("#myLoansUser").value = "";
  if (!term) {
    suggestions.classList.remove("visible");
    suggestions.innerHTML = "";
    renderMyLoans();
    return;
  }

  const labels = userLabels();
  const matches = state.users.filter((user) => userSearchText(user).includes(term)).slice(0, 8);
  suggestions.innerHTML = matches.map((user) => `
    <button class="suggestion-button" type="button" data-select-my-loans-user="${escapeHtml(user.user_id)}">
      <strong>${escapeHtml(labels.get(user.user_id) || user.name)}</strong>
      <span>${escapeHtml([user.company, user.department_name || user.department, user.alias].filter(Boolean).join(" · "))}</span>
    </button>
  `).join("");
  suggestions.classList.toggle("visible", matches.length > 0);
  document.querySelectorAll("[data-select-my-loans-user]").forEach((button) => {
    button.addEventListener("click", () => selectMyLoansUser(button.dataset.selectMyLoansUser));
  });
  renderMyLoans();
}

function selectMyLoansUser(userId) {
  const user = state.users.find((item) => item.user_id === userId);
  if (!user) return;
  const labels = userLabels();
  $("#myLoansUser").value = user.user_id;
  $("#myLoansUserSearch").value = labels.get(user.user_id) || user.name;
  $("#myLoansUserSuggestions").classList.remove("visible");
  renderMyLoans();
}

function selectReturnUser(userId) {
  const user = returnBorrowers().find((item) => item.user_id === userId);
  if (!user) return;
  const labels = userLabels();
  $("#returnUser").value = user.user_id;
  $("#returnUserSearch").value = labels.get(user.user_id) || user.name;
  $("#returnUserSuggestions").classList.remove("visible");
  renderReturnLoans();
}

function printLoanReceipt(loanId) {
  const loan = state.loans.find((item) => item.loan_id === loanId);
  if (!loan) {
    showToast(t("toast.noReceiptLoan"));
    return;
  }
  const receipt = $("#printReceipt");
  receipt.innerHTML = `
    <div class="receipt-page">
      <header class="receipt-header">
        <div>
          <h1>Loan receipt</h1>
          <p>Volvo Penta tool and instrument lending</p>
        </div>
        <div class="receipt-id">Loan ID ${loan.loan_id}</div>
      </header>
      <dl class="receipt-grid">
        <dt>Instrument ID</dt><dd>${escapeHtml(loan.object_id)}</dd>
        <dt>Instrument name</dt><dd>${escapeHtml(loan.object_name)}</dd>
        <dt>Engine ID</dt><dd>${escapeHtml(loan.engine_id || "")}</dd>
        <dt>Project Number</dt><dd>${escapeHtml(loan.project_number || "")}</dd>
        <dt>Name of borrower</dt><dd>${escapeHtml(loan.user_name)}</dd>
        <dt>Dept no</dt><dd>${escapeHtml(loan.user_department || "")}</dd>
        <dt>Quantity</dt><dd>${loan.remaining_quantity ?? loan.quantity}</dd>
        <dt>Lending date</dt><dd>${formatTime(loan.checkout_time)}</dd>
        <dt>Return date</dt><dd>${formatTime(loan.due_time)}</dd>
        <dt>Status</dt><dd>${loan.overdue ? "Overdue" : "Active"}</dd>
      </dl>
      <div class="receipt-signatures">
        <div><span></span><p>Borrower signature</p></div>
        <div><span></span><p>Returned/received by</p></div>
      </div>
    </div>
  `;
  window.print();
}

function addLoanArticle() {
  const item = selectedCheckoutObject();
  const quantity = Number($("#checkoutQuantity").value);
  validateLoanArticle(item, quantity, item ? remainingLoanQuantity(item) : 0);
  const existing = state.loanCart.find((entry) => entry.object_id === item.object_id);
  if (existing) existing.quantity += quantity;
  else state.loanCart.push({ object_id: item.object_id, name: item.name, quantity });
  $("#checkoutObjectId").value = "";
  $("#checkoutQuantity").value = "1";
  $("#checkoutObjectSuggestions").classList.remove("visible");
  renderLoanCart();
  $("#checkoutObjectId").focus();
}

function renderLoanCart() {
  const en = state.language === "en";
  $("#addLoanArticle").textContent = en ? "Add article" : "Lägg till artikel";
  $("#loanCartTitle").textContent = en ? "Articles in this request" : "Artiklar i låneförfrågan";
  $("#loanCart").innerHTML = state.loanCart.length ? state.loanCart.map((item, index) => {
    const stock = state.objects.find((object) => object.object_id === item.object_id);
    const available = stock ? stock.available_quantity : 0;
    const invalid = !stock || isConsumableObject(stock) || item.quantity > available;
    const stockText = stock
      ? t("checkout.cartStock", { count: remainingLoanQuantity(stock), available, inCart: item.quantity })
      : t("checkout.articleUnavailable");
    return `
    <div class="loan-cart-row"><span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.object_id)}</small>
      <small>${escapeHtml(stockText)}</small>
      ${invalid ? `<small class="cart-stock-warning" role="status">${escapeHtml(t("checkout.cartStockChanged"))}</small>` : ""}</span>
      <label>${en ? "Quantity" : "Antal"}<input type="number" min="1" max="${available}" step="1" value="${item.quantity}" aria-invalid="${invalid}" data-cart-quantity="${index}"></label>
      <button class="danger-button" type="button" data-cart-remove="${index}" aria-label="${escapeHtml((en ? 'Remove ' : 'Ta bort ') + item.name)}">${en ? "Remove" : "Ta bort"}</button>
    </div>`;
  }).join("") : `<p>${en ? "Select an article and click Add article. Repeat to add more." : "Välj en artikel och tryck Lägg till artikel. Upprepa för att lägga till fler."}</p>`;
  document.querySelectorAll("[data-cart-remove]").forEach((button) => button.addEventListener("click", () => {
    state.loanCart.splice(Number(button.dataset.cartRemove), 1); renderLoanCart();
  }));
  document.querySelectorAll("[data-cart-quantity]").forEach((input) => input.addEventListener("change", () => {
    const item = state.loanCart[Number(input.dataset.cartQuantity)];
    const quantity = Number(input.value);
    try {
      validateLoanArticle(state.objects.find((object) => object.object_id === item.object_id), quantity);
      item.quantity = quantity;
      renderLoanCart();
    } catch (error) {
      input.value = String(item.quantity);
      showToast(error.message);
    }
  }));
  updateCheckoutInfo();
  if ($("#checkoutObjectSuggestions").classList.contains("visible")) renderCheckoutObjectSuggestions();
}

function updateReturnButtons() {
  const selected = document.querySelectorAll("[data-return-select]:checked").length;
  const hasLoans = state.loans.some((loan) => loan.user_id === $("#returnUser").value);
  $("#returnSelectedButton").disabled = state.returnBusy || !selected;
  $("#returnAllButton").disabled = state.returnBusy || !hasLoans;
  $("#returnSelectedButton").textContent = `${state.language === "en" ? "Return selected" : "Lämna tillbaka valda"} (${selected})`;
  $("#returnAllButton").textContent = state.language === "en" ? "Return everything for this user" : "Lämna tillbaka allt för användaren";
  document.querySelectorAll("#returnLoansBody input, #returnLoansBody textarea, #returnUserSearch").forEach((input) => {
    input.disabled = Boolean(state.returnBusy);
  });
}

function renderReturnSummary() {
  const element = $("#returnSummary");
  if (!element) return;
  const summary = state.returnSummary;
  if (!summary || summary.user_id !== $("#returnUser").value) {
    element.innerHTML = "";
    return;
  }
  element.innerHTML = `<h2>${t("return.summary")}</h2>
    <p>${t("return.summaryTotals", { returned: summary.returned_quantity, damaged: summary.damaged_quantity, remaining: summary.remaining_quantity })}</p>
    <ul>${summary.items.map((item) => `<li>${escapeHtml(item.object_name)}:
      ${t("return.summaryLine", { returned: item.quantity, damaged: item.damaged_quantity, remaining: item.remaining_quantity })}</li>`).join("")}</ul>`;
}

function renderDamagedReturns() {
  const list = $("#damagedReturnsList");
  if (!list) return;
  list.innerHTML = (state.damagedReturns || []).length ? state.damagedReturns.map((item) => `
    <article class="damage-report" data-damage-report-id="${item.return_id}" tabindex="-1">
      <h3>${escapeHtml(item.object_name)} (${escapeHtml(item.object_id)}) — ${item.damaged_quantity}</h3>
      <p>#${item.return_id} · ${formatTime(item.returned_at)} · ${t("damage.quarantined")}</p>
      <p class="damage-description">${escapeHtml(item.damage_description)}</p>
      <div class="checkout-submit-actions">
        <button type="button" class="primary-button" data-damage-id="${item.return_id}" data-damage-resolution="repaired" ${state.damageBusy ? "disabled" : ""}>${t("damage.repair")}</button>
        <button type="button" class="danger-button" data-damage-id="${item.return_id}" data-damage-resolution="discarded" ${state.damageBusy ? "disabled" : ""}>${t("damage.discard")}</button>
      </div>
    </article>`).join("") : `<p>${t("damage.empty")}</p>`;
  list.querySelectorAll("[data-damage-resolution]").forEach((button) => {
    button.addEventListener("click", () => resolveDamage(Number(button.dataset.damageId), button.dataset.damageResolution));
  });
}

const JOB_REQUEST_STATUS_ORDER = ["requested", "approved", "prepared", "loaned", "returned", "stocked"];

function groupLoanRequestRows(jobs) {
  const groups = new Map();
  jobs.forEach((job) => {
    const id = Number(job.request_group_id || job.request_id);
    if (!groups.has(id)) groups.set(id, []);
    groups.get(id).push(job);
  });
  return [...groups].map(([id, items]) => {
    const positions = items.map((item) => JOB_REQUEST_STATUS_ORDER.indexOf(item.status));
    const position = Math.min(...positions.filter((value) => value >= 0));
    return {
      id,
      items: items.sort((a, b) => Number(a.request_id) - Number(b.request_id)),
      status: JOB_REQUEST_STATUS_ORDER[position] || items[0].status,
      partial: new Set(items.map((item) => item.status)).size > 1,
    };
  });
}

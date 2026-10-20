// Loan, pickup, return, and receipt views.
// ============================================================
// FORMULARINFORMATION
// Uppdaterar informationsrutor nar anvandaren skriver i formular.
// ============================================================

function updateCheckoutInfo(selectedItem = null) {
  const objectId = $("#checkoutObjectId").value.trim();
  const term = objectId.toLowerCase();
  const item = selectedItem || state.objects.find((objectItem) =>
    objectItem.object_id.toLowerCase() === term || objectItem.name.toLowerCase() === term
  );
  const details = $("#checkoutInfo");
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
  $("#checkoutObjectQuantity").value = state.language === "en" ? `${item.available_quantity} of ${item.total_quantity}` : `${item.available_quantity} av ${item.total_quantity}`;
  $("#checkoutObjectStatus").value = statusText(item.status || "");
}

function renderReturnLoans() {
  const body = $("#returnLoansBody");
  if (!body) return;
  const selectedUserId = $("#returnUser")?.value || "";
  const empty = $("#returnLoansEmpty");
  const matches = selectedUserId
    ? state.loans.filter((loan) => loan.user_id === selectedUserId)
    : [];

  body.innerHTML = matches.map((loan) => `
    <tr class="${loan.overdue ? "late" : ""}">
      <td><input type="checkbox" data-return-select="${loan.loan_id}" aria-label="${escapeHtml((state.language === 'en' ? 'Return ' : 'Återlämna ') + loan.object_name)}"> ${loan.loan_id}${loan.request_group_id ? `<small class="request-reference">${state.language === "en" ? "Request" : "Förfrågan"} #${loan.request_group_id}</small>` : ""}</td>
      <td>${escapeHtml(loan.object_name)} (${escapeHtml(loan.object_id)})</td>
      <td>${escapeHtml(loan.user_name)}</td>
      <td>${escapeHtml(loan.user_department || "")}</td>
      <td>${escapeHtml(loan.engine_id || "")}</td>
      <td>${escapeHtml(loan.project_number || "")}</td>
      <td>${loan.quantity}</td>
      <td>${formatTime(loan.checkout_time)}</td>
      <td>${formatTime(loan.due_time)}</td>
      <td>${statusBadge(loan.overdue ? "Sen" : "Aktiv")}</td>
      <td><button class="primary-button table-return-button" type="button" data-return-loan="${loan.loan_id}">Återlämna</button></td>
    </tr>
  `).join("");

  document.querySelectorAll("[data-return-loan]").forEach((button) => {
    button.addEventListener("click", () => returnItem(Number(button.dataset.returnLoan)));
  });

  document.querySelectorAll("[data-return-select]").forEach((input) => input.addEventListener("change", updateReturnButtons));
  updateReturnButtons();
  if (empty) {
    empty.textContent = selectedUserId
      ? matches.length
        ? ""
        : "Den valda användaren har inga aktiva utlåningar."
      : "Välj en användare för att se aktiva utlåningar.";
  }
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
  const matches = state.users.filter((user) => userSearchText(user).includes(term)).slice(0, 8);
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
      <td>${loan.quantity}</td>
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
  const user = state.users.find((item) => item.user_id === userId);
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
        <dt>Quantity</dt><dd>${loan.quantity}</dd>
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
  const term = $("#checkoutObjectId").value.trim().toLowerCase();
  const selectedId = $("#checkoutObjectInstrumentId").value;
  const selected = state.objects.find((object) => object.object_id === selectedId);
  const item = selected && [selected.object_id.toLowerCase(), selected.name.toLowerCase()].includes(term)
    ? selected : state.objects.find((object) => object.object_id.toLowerCase() === term || object.name.toLowerCase() === term);
  if (!item) throw new Error(state.language === "en" ? "Select an article first." : "Välj en artikel först.");
  if (isConsumableObject(item)) throw new Error(state.language === "en" ? "Consumables cannot be borrowed." : "Förbrukningsvaror kan inte lånas.");
  const quantity = Number($("#checkoutQuantity").value);
  if (!Number.isInteger(quantity) || quantity <= 0) throw new Error(state.language === "en" ? "Enter a positive whole quantity." : "Ange ett positivt heltal.");
  const existing = state.loanCart.find((entry) => entry.object_id === item.object_id);
  if (existing) existing.quantity += quantity;
  else state.loanCart.push({ object_id: item.object_id, name: item.name, quantity });
  $("#checkoutObjectId").value = "";
  $("#checkoutQuantity").value = "1";
  $("#checkoutObjectSuggestions").classList.remove("visible");
  updateCheckoutInfo();
  renderLoanCart();
  $("#checkoutObjectId").focus();
}

function renderLoanCart() {
  const en = state.language === "en";
  $("#addLoanArticle").textContent = en ? "Add article" : "Lägg till artikel";
  $("#loanCartTitle").textContent = en ? "Articles in this request" : "Artiklar i låneförfrågan";
  $("#loanCart").innerHTML = state.loanCart.length ? state.loanCart.map((item, index) => `
    <div class="loan-cart-row"><span><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.object_id)}</small></span>
      <label>${en ? "Quantity" : "Antal"}<input type="number" min="1" step="1" value="${item.quantity}" data-cart-quantity="${index}"></label>
      <button class="danger-button" type="button" data-cart-remove="${index}" aria-label="${escapeHtml((en ? 'Remove ' : 'Ta bort ') + item.name)}">${en ? "Remove" : "Ta bort"}</button>
    </div>`).join("") : `<p>${en ? "Select an article and click Add article. Repeat to add more." : "Välj en artikel och tryck Lägg till artikel. Upprepa för att lägga till fler."}</p>`;
  document.querySelectorAll("[data-cart-remove]").forEach((button) => button.addEventListener("click", () => {
    state.loanCart.splice(Number(button.dataset.cartRemove), 1); renderLoanCart();
  }));
  document.querySelectorAll("[data-cart-quantity]").forEach((input) => input.addEventListener("change", () => {
    const item = state.loanCart[Number(input.dataset.cartQuantity)];
    const quantity = Number(input.value);
    if (Number.isInteger(quantity) && quantity > 0) item.quantity = quantity;
    else input.value = item.quantity;
  }));
}

function updateReturnButtons() {
  const selected = document.querySelectorAll("[data-return-select]:checked").length;
  const hasLoans = state.loans.some((loan) => loan.user_id === $("#returnUser").value);
  $("#returnSelectedButton").disabled = state.returnBusy || !selected;
  $("#returnAllButton").disabled = state.returnBusy || !hasLoans;
  $("#returnSelectedButton").textContent = `${state.language === "en" ? "Return selected" : "Lämna tillbaka valda"} (${selected})`;
  $("#returnAllButton").textContent = state.language === "en" ? "Return everything for this user" : "Lämna tillbaka allt för användaren";
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

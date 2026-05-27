// Search panel rendering and behavior.
// ============================================================
// SOK
// Global sokpanel och sokresultat.
// ============================================================

async function performSearch() {
  const term = $("#globalSearchInput").value.trim();
  $("#searchTitle").textContent = term ? `Sökresultat för "${term}"` : "Sökresultat";
  if (!term) {
    renderSearchResults([]);
    $("#searchEmpty").textContent = "Skriv något för att söka i inventariet.";
    $("#searchEmpty").classList.add("visible");
    return;
  }

  try {
    const results = await searchApi(term);
    renderSearchResults(results);
  } catch (error) {
    showToast(error.message);
  }
}

function renderSearchResults(results) {
  $("#allResultsTab").textContent = `${t("search.all")} (${results.length})`;
  $("#objectResultsTab").textContent = `${t("search.objects")} (${results.length})`;
  $("#searchResultsGrid").innerHTML = results.map((item) => `
    <article class="search-card">
      <div class="search-card-visual">${item.image_data ? `<img src="${escapeHtml(item.image_data)}" alt="">` : escapeHtml(item.category)}</div>
      <div class="search-card-body">
        <div class="search-card-title">${escapeHtml(item.name)}</div>
        <div class="search-card-meta">${escapeHtml(item.article_number || item.object_id)} ${item.supplier_article_number ? `· ${escapeHtml(item.supplier_article_number)}` : ""}</div>
        <div class="search-card-meta">${escapeHtml(item.location)} · Hissbricka ${escapeHtml(item.lift_tray || item.door_id)}</div>
      </div>
      <div class="search-card-footer">
        ${statusBadge(item.status)}
        <button class="search-card-action" type="button" data-object-id="${escapeHtml(item.object_id)}">Låna</button>
      </div>
    </article>
  `).join("");

  $("#searchEmpty").textContent = t("search.noResults");
  $("#searchEmpty").classList.toggle("visible", results.length === 0);

  document.querySelectorAll(".search-card-action").forEach((button) => {
    button.addEventListener("click", () => {
      $("#checkoutObjectId").value = button.dataset.objectId;
      closeSearch();
      setView("checkout");
      updateCheckoutInfo();
    });
  });
}

function openSearch() {
  $("#searchLayer").classList.add("open");
  $("#searchLayer").setAttribute("aria-hidden", "false");
  $("#globalSearchInput").focus();
  performSearch();
}

function closeSearch() {
  $("#searchLayer").classList.remove("open");
  $("#searchLayer").setAttribute("aria-hidden", "true");
}

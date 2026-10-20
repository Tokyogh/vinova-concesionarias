/* ES: Implementa interacción de navegador para static/js/institutions; backend conserva la autoridad. */
/* EN: Implements browser interaction for static/js/institutions; the backend remains authoritative. */
  /* ES: Estado, filtros y mapa se sincronizan desde el DOM; un proveedor ausente conserva la lista utilizable. */
  /* EN: State, filters, and map synchronize from the DOM; a missing provider leaves the list usable. */
document.addEventListener("DOMContentLoaded", () => {
  const root = document.querySelector("[data-institutions-root]");
  if (!root) return;

  /* ES: Estado, filtros y mapa se sincronizan desde el DOM; un proveedor ausente conserva la lista utilizable. */
  /* EN: State, filters, and map synchronize from the DOM; a missing provider leaves the list usable. */
  const cards = Array.from(root.querySelectorAll("[data-establishment-card]"));
  const details = Array.from(root.querySelectorAll("[data-establishment-detail]"));
  const searchInput = root.querySelector("#institutionSearch");
  const typeSelect = root.querySelector("#institutionTypeSelect");
  const filterEmpty = root.querySelector("[data-filter-empty]");
  const typeCards = Array.from(document.querySelectorAll("[data-institution-filter]"));
  const clearFiltersButton = root.querySelector("[data-clear-institution-filters]");
  const mapContainer = root.querySelector("#vinovaInstitutionsMap");
  const mapFallback = root.querySelector("#vinovaInstitutionsMapFallback");
  const markers = new Map();
  let map = null;
  let popup = null;

  const normalize = value => String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();

  const numberOrNull = value => {
    const raw = String(value ?? "").trim().replace(",", ".");
    if (!raw) return null;
    const parsed = Number(raw);
    return Number.isFinite(parsed) ? parsed : null;
  };

  const records = cards.map(card => ({
    id: String(card.dataset.id || ""),
    type: card.dataset.type || "institution",
    name: card.dataset.name || "Establecimiento Vinova",
    typeLabel: card.dataset.typeLabel || "Establecimiento",
    address: card.dataset.address || "Dirección no registrada",
    lat: numberOrNull(card.dataset.lat),
    lng: numberOrNull(card.dataset.lng),
    card,
  }));

  const recordById = id => records.find(record => record.id === String(id));
  const validCoordinates = record => record.lat !== null && record.lng !== null
    && record.lat >= -90 && record.lat <= 90 && record.lng >= -180 && record.lng <= 180
    && !(record.lat === 0 && record.lng === 0);

  const escapeHtml = value => {
    const element = document.createElement("span");
    element.textContent = String(value || "");
    return element.innerHTML;
  };

  function markerIcon(type) {
    if (type === "service_center") {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 13v-1a8 8 0 0 1 16 0v1M4 13v4m16-4v4M8 13v6m8-6v6"/></svg>';
    }
    if (type === "dealership") {
      return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 20V7a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v13M8 10h6m-6 4h6M3 20h18"/></svg>';
    }
    return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m4 10 8-5 8 5M6 10h12M7 10v8m5-8v8m5-8v8M4 19h16"/></svg>';
  }

  function updateMarkerState(activeId) {
    markers.forEach((markerRecord, markerId) => {
      markerRecord.element.classList.toggle("active", markerId === String(activeId));
    });
  }

  function setActive(id, { moveMap = true } = {}) {
    const record = recordById(id);
    if (!record) return;
    cards.forEach(card => {
      const active = String(card.dataset.id) === record.id;
      card.classList.toggle("active", active);
      card.setAttribute("aria-pressed", active ? "true" : "false");
    });
    details.forEach(detail => detail.classList.toggle("is-hidden", detail.dataset.establishmentDetail !== record.id));
    updateMarkerState(record.id);

    const markerRecord = markers.get(record.id);
    if (!map || !markerRecord) return;
    if (moveMap) {
      map.flyTo({center: [record.lng, record.lat], zoom: Math.max(map.getZoom(), 13.5), speed: .8, essential: true});
    }
    if (popup) popup.remove();
    popup = new window.maplibregl.Popup({offset: 32, closeButton: false})
      .setLngLat([record.lng, record.lat])
      .setHTML(`<div class="institution-map-popup"><strong>${escapeHtml(record.name)}</strong><span>${escapeHtml(record.typeLabel)}</span><small>${escapeHtml(record.address)}</small></div>`)
      .addTo(map);
  }

  function visibleCards() {
    return cards.filter(card => !card.hidden);
  }

  function fitVisibleMarkers() {
    if (!map || !window.maplibregl) return;
    const visible = records.filter(record => !record.card.hidden && markers.has(record.id));
    if (!visible.length) return;
    if (visible.length === 1) {
      map.easeTo({center: [visible[0].lng, visible[0].lat], zoom: 13.5, duration: 350});
      return;
    }
    const bounds = new window.maplibregl.LngLatBounds();
    visible.forEach(record => bounds.extend([record.lng, record.lat]));
    map.fitBounds(bounds, {padding: 54, maxZoom: 13.5, duration: 350});
  }

  function applyFilters() {
    const query = normalize(searchInput?.value);
    const selectedType = typeSelect?.value || "";
    let activeVisible = false;
    cards.forEach(card => {
      const searchable = normalize(card.dataset.search);
      const visible = (!query || searchable.includes(query)) && (!selectedType || card.dataset.type === selectedType);
      card.hidden = !visible;
      const markerRecord = markers.get(String(card.dataset.id));
      if (markerRecord) markerRecord.element.hidden = !visible;
      if (visible && card.classList.contains("active")) activeVisible = true;
    });
    const visible = visibleCards();
    if (filterEmpty) filterEmpty.hidden = visible.length > 0;
    if (!activeVisible) {
      if (visible.length) setActive(visible[0].dataset.id, {moveMap: false});
      else {
        cards.forEach(card => { card.classList.remove("active"); card.setAttribute("aria-pressed", "false"); });
        details.forEach(detail => detail.classList.add("is-hidden"));
        updateMarkerState("");
        if (popup) { popup.remove(); popup = null; }
      }
    }
    if (clearFiltersButton) clearFiltersButton.hidden = !query && !selectedType;
    fitVisibleMarkers();
  }

  function setTypeFilter(nextType) {
    if (!typeSelect) return;
    typeSelect.value = nextType;
    const url = new URL(window.location.href);
    if (nextType) url.searchParams.set("tipo", nextType);
    else url.searchParams.delete("tipo");
    window.history.replaceState({}, "", url);
    const headings = {
      "": "Instituciones y establecimientos",
      institution: "Instituciones afiliadas",
      dealership: "Concesionarios",
      service_center: "Centros de atención",
    };
    root.querySelector(".institutions-heading h1").textContent = headings[nextType] || headings[""];
    typeCards.forEach(card => {
      const active = card.dataset.institutionFilter === nextType;
      card.classList.toggle("active", active);
      if (active) card.setAttribute("aria-current", "true");
      else card.removeAttribute("aria-current");
    });
    applyFilters();
  }

  function showMapFallback(message) {
    if (!mapFallback) return;
    mapFallback.hidden = false;
    if (message) {
      const text = mapFallback.querySelector("span");
      if (text) text.textContent = message;
    }
  }

  function initMap() {
    if (!mapContainer) return;
    const publicKey = mapContainer.dataset.maptilerKey || "";
    const externalMediaAllowed = window.VinovaConsent && window.VinovaConsent.allows("external_media");
    if (!externalMediaAllowed || !publicKey || !window.maplibregl) {
      showMapFallback();
      return;
    }
    const mapped = records.filter(validCoordinates);
    if (!mapped.length) {
      showMapFallback("Las sedes publicadas todavía no tienen coordenadas verificadas.");
      return;
    }
    map = new window.maplibregl.Map({
      container: mapContainer,
      style: `https://api.maptiler.com/maps/streets-v2/style.json?key=${encodeURIComponent(publicKey)}`,
      center: [-78.4678, -1.8312],
      zoom: 5.7,
      pitch: 0,
      bearing: 0,
    });
    map.addControl(new window.maplibregl.NavigationControl({showCompass: false}), "bottom-right");
    map.on("load", () => {
      mapFallback.hidden = true;
      mapped.forEach(record => {
        const element = document.createElement("button");
        element.type = "button";
        element.className = "vinova-map-marker";
        element.dataset.type = record.type;
        element.setAttribute("aria-label", `Ver ${record.name}`);
        element.innerHTML = markerIcon(record.type);
        element.addEventListener("click", () => setActive(record.id, {moveMap: false}));
        const marker = new window.maplibregl.Marker({element, anchor: "bottom"})
          .setLngLat([record.lng, record.lat])
          .addTo(map);
        markers.set(record.id, {marker, element});
      });
      applyFilters();
      const first = visibleCards()[0];
      if (first) setActive(first.dataset.id, {moveMap: false});
      window.setTimeout(() => map.resize(), 150);
    });
    map.on("error", () => showMapFallback("No se pudo cargar el mapa. La lista de sedes sigue disponible."));
  }

  cards.forEach(card => {
    card.addEventListener("click", () => setActive(card.dataset.id));
    card.addEventListener("keydown", event => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        setActive(card.dataset.id);
      }
    });
  });
  root.querySelectorAll(".institution-detail-close").forEach(button => {
    button.addEventListener("click", () => {
      const detail = button.closest("[data-establishment-detail]");
      if (detail) detail.classList.add("is-hidden");
      cards.forEach(card => { card.classList.remove("active"); card.setAttribute("aria-pressed", "false"); });
      updateMarkerState("");
      if (popup) { popup.remove(); popup = null; }
    });
  });
  searchInput?.addEventListener("input", applyFilters);
  typeSelect?.addEventListener("change", () => setTypeFilter(typeSelect.value));
  typeCards.forEach(card => {
    card.addEventListener("click", event => {
      event.preventDefault();
      const cardType = card.dataset.institutionFilter || "";
      setTypeFilter(typeSelect?.value === cardType ? "" : cardType);
    });
  });
  clearFiltersButton?.addEventListener("click", () => {
    if (searchInput) searchInput.value = "";
    setTypeFilter("");
    searchInput?.focus();
  });

  if (root.dataset.initialType && typeSelect) typeSelect.value = root.dataset.initialType;
  applyFilters();
  initMap();
});

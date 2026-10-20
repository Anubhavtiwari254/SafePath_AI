/**
 * SafePath AI - Unsafe Area Map Controller
 */

let safetyMap = null;
let markerClusterGroup = null;
let currentHazards = [];

document.addEventListener("DOMContentLoaded", function () {
  initSafetyMap();
});

function initSafetyMap() {
  safetyMap = initBaseMap("safetyMap", 28.6315, 77.2167, 13);
  if (!safetyMap) return;

  // Initialize marker cluster group if library is available, or fall back to standard layer
  if (typeof L.markerClusterGroup === "function") {
    markerClusterGroup = L.markerClusterGroup({
      showCoverageOnHover: false,
      maxClusterRadius: 40,
      spiderfyOnMaxZoom: true
    });
    safetyMap.addLayer(markerClusterGroup);
  } else {
    markerClusterGroup = L.layerGroup().addTo(safetyMap);
  }

  // Bind filter triggers
  ["filterCategory", "filterSeverity", "filterStatus", "filterTimeframe"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("change", fetchAndRenderHazards);
  });

  // Search location jump
  const searchInput = document.getElementById("mapLocationSearch");
  const searchBtn = document.getElementById("mapSearchBtn");
  if (searchBtn && searchInput) {
    searchBtn.addEventListener("click", () => searchLocation(searchInput.value));
    searchInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") searchLocation(searchInput.value);
    });
  }

  // Load all hazards initially
  fetchAndRenderHazards();
}

function searchLocation(query) {
  if (!query || !query.trim()) return;
  fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`)
    .then(res => res.json())
    .then(data => {
      if (data && data.length > 0) {
        const lat = parseFloat(data[0].lat);
        const lon = parseFloat(data[0].lon);
        safetyMap.setView([lat, lon], 14);
      } else {
        alert("Location not found. Please try another query.");
      }
    })
    .catch(err => {
      console.warn("Geocoding error:", err);
    });
}

function fetchAndRenderHazards() {
  const category = document.getElementById("filterCategory")?.value || "";
  const severity = document.getElementById("filterSeverity")?.value || "";
  const status = document.getElementById("filterStatus")?.value || "all";
  const timeframe = document.getElementById("filterTimeframe")?.value || "all";

  const params = new URLSearchParams();
  if (category) params.append("category", category);
  if (severity) params.append("severity", severity);
  if (status) params.append("status", status);
  if (timeframe) params.append("timeframe", timeframe);

  fetch(`/api/hazards?${params.toString()}`)
    .then(res => res.json())
    .then(data => {
      if (!data.success) return;
      currentHazards = data.hazards || [];
      renderHazardsOnMap(currentHazards);
      updateHazardCounter(currentHazards.length);
    })
    .catch(err => {
      console.error("Failed to load hazards:", err);
    });
}

function renderHazardsOnMap(hazards) {
  markerClusterGroup.clearLayers();
  if (!hazards || hazards.length === 0) return;

  const bounds = L.latLngBounds([]);

  hazards.forEach(h => {
    const marker = L.marker([h.latitude, h.longitude], {
      icon: createHazardPinIcon(h.category)
    }).bindPopup(buildHazardPopupContent(h));

    markerClusterGroup.addLayer(marker);
    bounds.extend([h.latitude, h.longitude]);
  });

  if (bounds.isValid() && hazards.length > 0) {
    safetyMap.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 });
  }
}

function updateHazardCounter(count) {
  const counterEl = document.getElementById("hazardCountBadge");
  if (counterEl) {
    counterEl.textContent = `${count} Active Reports`;
  }
}

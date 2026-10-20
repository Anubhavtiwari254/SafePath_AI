/**
 * SafePath AI - Safe Route Finder Controller
 */

let routeMap = null;
let currentRoutes = [];
let routeLayers = [];
let markerLayers = [];
let selectedRouteId = null;

document.addEventListener("DOMContentLoaded", function () {
  initRouteFinder();
});

function initRouteFinder() {
  routeMap = initBaseMap("routeMap", 28.6315, 77.2167, 13);
  if (!routeMap) return;

  const form = document.getElementById("routeSearchForm");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      fetchAndDisplayRoutes();
    });
  }

  // Use My Location button
  const locBtn = document.getElementById("useCurrentLocationBtn");
  if (locBtn) {
    locBtn.addEventListener("click", useCurrentLocationForOrigin);
  }

  // Check URL params for pre-filled search or run default demo
  const urlParams = new URLSearchParams(window.location.search);
  const originParam = urlParams.get("origin");
  const destParam = urlParams.get("destination");

  if (originParam && destParam) {
    document.getElementById("originInput").value = originParam;
    document.getElementById("destInput").value = destParam;
    fetchAndDisplayRoutes();
  } else {
    // Load a default demonstration search so user sees live results immediately!
    loadDemoRoute("Central Station", "India Gate");
  }
}

function loadDemoRoute(origin, destination) {
  const oInput = document.getElementById("originInput");
  const dInput = document.getElementById("destInput");
  if (oInput && dInput) {
    oInput.value = origin;
    dInput.value = destination;
    fetchAndDisplayRoutes();
  }
}

function useCurrentLocationForOrigin() {
  const btn = document.getElementById("useCurrentLocationBtn");
  if (!navigator.geolocation) {
    alert("Geolocation is not supported by your browser.");
    return;
  }

  btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Detecting...';
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;
      document.getElementById("originInput").value = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;
      btn.innerHTML = '<i class="fa-solid fa-location-crosshairs text-primary"></i>';
      // Center map
      if (routeMap) routeMap.setView([lat, lon], 14);
    },
    (err) => {
      console.warn("Geolocation error:", err);
      btn.innerHTML = '<i class="fa-solid fa-location-crosshairs"></i>';
      alert("Unable to retrieve your current location. Please allow location permissions in your browser.");
    },
    { enableHighAccuracy: true, timeout: 8000 }
  );
}

function fetchAndDisplayRoutes() {
  const origin = document.getElementById("originInput").value.trim();
  const destination = document.getElementById("destInput").value.trim();
  const mode = document.getElementById("travelModeSelect").value;
  const preference = document.getElementById("preferenceSelect").value;

  if (!origin || !destination) {
    alert("Please enter both a starting point and a destination.");
    return;
  }

  const resultsContainer = document.getElementById("routeResultsContainer");
  const loadingIndicator = document.getElementById("routeLoadingIndicator");

  if (loadingIndicator) loadingIndicator.classList.remove("d-none");
  if (resultsContainer) resultsContainer.innerHTML = "";

  const params = new URLSearchParams({
    origin: origin,
    destination: destination,
    mode: mode,
    preference: preference
  });

  fetch(`/api/routes?${params.toString()}`)
    .then((res) => res.json())
    .then((data) => {
      if (loadingIndicator) loadingIndicator.classList.add("d-none");

      if (!data.success) {
        if (resultsContainer) {
          resultsContainer.innerHTML = `
            <div class="alert alert-warning border-0 shadow-sm">
              <i class="fa-solid fa-triangle-exclamation me-2"></i>${escapeHtml(data.error || "No route found")}
            </div>
          `;
        }
        return;
      }

      currentRoutes = data.routes || [];
      renderRoutesOnMap(currentRoutes, data.hazards || []);
      renderRouteCards(currentRoutes, resultsContainer);
    })
    .catch((err) => {
      if (loadingIndicator) loadingIndicator.classList.add("d-none");
      console.error("Route search error:", err);
      if (resultsContainer) {
        resultsContainer.innerHTML = `
          <div class="alert alert-danger border-0 shadow-sm">
            <i class="fa-solid fa-circle-exclamation me-2"></i>Failed to calculate routes. Please check your connection or try again.
          </div>
        `;
      }
    });
}

function clearMapLayers() {
  routeLayers.forEach((layer) => routeMap.removeLayer(layer));
  markerLayers.forEach((marker) => routeMap.removeLayer(marker));
  routeLayers = [];
  markerLayers = [];
}

function renderRoutesOnMap(routes, hazards) {
  clearMapLayers();
  if (!routes || routes.length === 0) return;

  const allBounds = L.latLngBounds([]);

  // Plot relevant hazards in corridor
  hazards.forEach((h) => {
    const marker = L.marker([h.latitude, h.longitude], {
      icon: createHazardPinIcon(h.category)
    }).bindPopup(buildHazardPopupContent(h));
    marker.addTo(routeMap);
    markerLayers.push(marker);
  });

  // Color scheme: Safest / selected gets vibrant teal/green, alternatives get slate/blue
  routes.forEach((r, idx) => {
    const isRecommended = r.is_recommended;
    const coords = r.coordinates;
    if (!coords || coords.length === 0) return;

    let color = "#3A506B"; // Default slate
    let weight = 5;
    let opacity = 0.65;

    if (isRecommended) {
      color = r.safety_score >= 75 ? "#06D6A0" : (r.safety_score >= 50 ? "#00B4D8" : "#F59E0B");
      weight = 7;
      opacity = 0.9;
    } else if (idx === 1) {
      color = "#48CAE4";
      weight = 5;
    }

    const polyline = L.polyline(coords, {
      color: color,
      weight: weight,
      opacity: opacity,
      smoothFactor: 1
    }).addTo(routeMap);

    polyline.on("click", () => {
      selectRoute(r.id);
    });

    polyline.bindTooltip(
      `<strong>${escapeHtml(r.name)}</strong><br>Safety: ${r.safety_score}/100 (${escapeHtml(r.category)})<br>${r.duration_minutes} min • ${r.distance_km} km`,
      { sticky: true }
    );

    routeLayers.push(polyline);
    coords.forEach((pt) => allBounds.extend(pt));
  });

  // Start & End markers
  const firstRoute = routes[0];
  if (firstRoute.coordinates.length > 0) {
    const startCoord = firstRoute.coordinates[0];
    const endCoord = firstRoute.coordinates[firstRoute.coordinates.length - 1];

    const startMarker = L.marker(startCoord, {
      icon: L.divIcon({
        className: "start-pin",
        html: `<div style="background: #10B981; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><i class="fa-solid fa-play"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      })
    }).bindPopup("<strong>Starting Location</strong>").addTo(routeMap);
    markerLayers.push(startMarker);

    const endMarker = L.marker(endCoord, {
      icon: L.divIcon({
        className: "end-pin",
        html: `<div style="background: #EF4444; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 4px 10px rgba(0,0,0,0.3);"><i class="fa-solid fa-flag-checkered"></i></div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16]
      })
    }).bindPopup("<strong>Destination</strong>").addTo(routeMap);
    markerLayers.push(endMarker);
  }

  if (allBounds.isValid()) {
    routeMap.fitBounds(allBounds, { padding: [40, 40] });
  }

  // Select top route by default
  selectRoute(routes[0].id, false);
}

function selectRoute(routeId, pan = true) {
  selectedRouteId = routeId;

  // Update card styles
  document.querySelectorAll(".route-card-item").forEach((el) => {
    if (el.getAttribute("data-route-id") === routeId) {
      el.classList.add("border-primary", "shadow");
      el.style.borderWidth = "2px";
    } else {
      el.classList.remove("border-primary", "shadow");
      el.style.borderWidth = "1px";
    }
  });

  // Re-style map polylines
  currentRoutes.forEach((r, idx) => {
    const layer = routeLayers[idx];
    if (!layer) return;

    if (r.id === routeId) {
      layer.setStyle({
        weight: 8,
        opacity: 0.95,
        color: r.safety_score >= 75 ? "#06D6A0" : (r.safety_score >= 50 ? "#00B4D8" : "#F59E0B")
      });
      layer.bringToFront();
      if (pan) {
        routeMap.fitBounds(layer.getBounds(), { padding: [30, 30] });
      }
    } else {
      layer.setStyle({
        weight: 4,
        opacity: 0.45,
        color: "#64748B"
      });
    }
  });
}

function renderRouteCards(routes, container) {
  if (!container) return;
  if (!routes || routes.length === 0) {
    container.innerHTML = `<p class="text-muted">No route alternatives found.</p>`;
    return;
  }

  let html = `<div class="d-flex flex-column gap-3">`;

  routes.forEach((r) => {
    const isRecommended = r.is_recommended;
    const scoreClass = r.safety_score >= 80 ? "score-low-risk" : (r.safety_score >= 50 ? "score-mod-risk" : "score-high-risk");

    let factorItemsHtml = "";
    if (r.factors && r.factors.length > 0) {
      factorItemsHtml = `
        <div class="mt-2 pt-2 border-top">
          <a class="text-decoration-none small fw-semibold text-secondary" data-bs-toggle="collapse" href="#factors-${r.id}" role="button">
            <i class="fa-solid fa-list-check me-1"></i>Explain Risk Factors (${r.factors.length} identified) <i class="fa-solid fa-chevron-down ms-1"></i>
          </a>
          <div class="collapse mt-2" id="factors-${r.id}">
            <ul class="list-group list-group-flush small">
              ${r.factors.map(f => `
                <li class="list-group-item px-0 py-1 d-flex justify-content-between align-items-center bg-transparent border-0">
                  <span><i class="fa-solid ${f.icon || 'fa-circle-exclamation'} text-danger me-1"></i>${escapeHtml(f.explanation)}</span>
                </li>
              `).join("")}
            </ul>
          </div>
        </div>
      `;
    } else {
      factorItemsHtml = `
        <div class="small text-success mt-2">
          <i class="fa-solid fa-shield-check me-1"></i>No community hazards detected along this corridor.
        </div>
      `;
    }

    html += `
      <div class="card sp-card route-card-item cursor-pointer p-3 ${isRecommended ? 'border-primary' : ''}" 
           data-route-id="${r.id}" 
           onclick="selectRoute('${r.id}')"
           style="cursor: pointer;">
        <div class="d-flex justify-content-between align-items-start mb-2">
          <div>
            ${isRecommended ? `<span class="badge bg-primary text-white mb-1"><i class="fa-solid fa-star me-1"></i>${escapeHtml(r.recommendation_tag || 'Recommended')}</span>` : ''}
            <h5 class="mb-0 fw-bold">${escapeHtml(r.name)}</h5>
          </div>
          <div class="safety-score-pill ${scoreClass}">
            <i class="fa-solid fa-shield-heart"></i>
            <span>${r.safety_score}</span> / 100
          </div>
        </div>

        <div class="d-flex gap-3 text-muted small mb-2">
          <span><i class="fa-regular fa-clock me-1 text-primary"></i><strong>${r.duration_minutes} min</strong></span>
          <span><i class="fa-solid fa-route me-1 text-primary"></i><strong>${r.distance_km} km</strong></span>
          <span><i class="fa-solid fa-triangle-exclamation me-1 ${r.hazards_count > 0 ? 'text-warning' : 'text-success'}"></i>${r.hazards_count} Hazards</span>
        </div>

        <p class="small text-muted mb-1">${escapeHtml(r.explanation_summary || '')}</p>

        ${factorItemsHtml}

        <div class="d-flex justify-content-end mt-2">
          <button class="btn btn-sm btn-outline-primary" onclick="selectRoute('${r.id}'); event.stopPropagation();">
            <i class="fa-solid fa-location-arrow me-1"></i>Select & Highlight
          </button>
        </div>
      </div>
    `;
  });

  html += `
    <div class="text-muted small text-center mt-2">
      <i class="fa-solid fa-circle-info me-1"></i>Scores are calculated using community reports and proximity analysis. They do not constitute an absolute guarantee of safety.
    </div>
  </div>`;

  container.innerHTML = html;
}

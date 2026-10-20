/**
 * SafePath AI - Common Map Helpers & Category Definitions
 */

const HAZARD_CONFIG = {
  broken_streetlights: { label: "Broken Streetlight", icon: "fa-lightbulb", color: "#F59E0B" },
  isolated_areas: { label: "Isolated / Poorly Lit", icon: "fa-eye-slash", color: "#8B5CF6" },
  road_damage: { label: "Road Damage / Pothole", icon: "fa-triangle-exclamation", color: "#F97316" },
  suspicious_activity: { label: "Suspicious Activity", icon: "fa-shield-halved", color: "#EF4444" },
  harassment: { label: "Harassment Concern", icon: "fa-hand-dots", color: "#DC2626" },
  blocked_road: { label: "Blocked Road / Work", icon: "fa-road-barrier", color: "#D97706" },
  other_concern: { label: "Safety Concern", icon: "fa-circle-info", color: "#0EA5E9" }
};

function initBaseMap(elementId, centerLat = 28.6315, centerLon = 77.2167, zoom = 14) {
  if (!document.getElementById(elementId)) return null;

  const map = L.map(elementId, {
    zoomControl: true,
    scrollWheelZoom: true
  }).setView([centerLat, centerLon], zoom);

  // Modern clean OpenStreetMap tiles
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(map);

  return map;
}

function createHazardPinIcon(categoryKey) {
  const cfg = HAZARD_CONFIG[categoryKey] || HAZARD_CONFIG.other_concern;
  return L.divIcon({
    className: "custom-hazard-wrapper",
    html: `<div class="custom-hazard-pin" style="background-color: ${cfg.color};" title="${cfg.label}">
            <i class="fa-solid ${cfg.icon}"></i>
           </div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
    popupAnchor: [0, -16]
  });
}

function formatRelativeTime(dateString) {
  if (!dateString) return "Recently";
  const date = new Date(dateString);
  const now = new Date();
  const diffHours = Math.floor((now - date) / (1000 * 60 * 60));
  if (diffHours < 1) return "Just now";
  if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
}

function buildHazardPopupContent(h, onConfirmCallbackName = "confirmHazardReport") {
  const cfg = HAZARD_CONFIG[h.category] || HAZARD_CONFIG.other_concern;
  const sevBadge = h.severity === "high" 
    ? '<span class="badge bg-danger">High Severity</span>'
    : (h.severity === "medium" ? '<span class="badge bg-warning text-dark">Medium Risk</span>' : '<span class="badge bg-info text-dark">Low Concern</span>');

  const statusBadge = h.verification_status === "verified"
    ? '<span class="badge bg-success"><i class="fa-solid fa-check-circle me-1"></i>Verified</span>'
    : '<span class="badge bg-secondary"><i class="fa-solid fa-clock me-1"></i>Pending Review</span>';

  const photoHtml = h.photo_url 
    ? `<div class="mt-2 text-center"><img src="${h.photo_url}" class="img-fluid rounded border" style="max-height: 140px;" alt="Hazard Photo" /></div>` 
    : "";

  return `
    <div class="hazard-popup" style="min-width: 230px; font-family: 'Inter', sans-serif;">
      <div class="d-flex align-items-center justify-content-between mb-2">
        <span class="fw-bold" style="color: ${cfg.color};"><i class="fa-solid ${cfg.icon} me-1"></i>${cfg.label}</span>
      </div>
      <div class="d-flex gap-1 mb-2">
        ${sevBadge}
        ${statusBadge}
      </div>
      <p class="small text-dark mb-2" style="line-height: 1.4;">${escapeHtml(h.description)}</p>
      ${photoHtml}
      <div class="d-flex justify-content-between align-items-center border-top pt-2 mt-2 text-muted small">
        <span><i class="fa-regular fa-clock me-1"></i>${formatRelativeTime(h.incident_datetime || h.created_at)}</span>
        <span id="conf-count-${h.id}"><i class="fa-solid fa-thumbs-up me-1 text-primary"></i>${h.confirmation_count || 0}</span>
      </div>
      <div class="mt-2">
        <button class="btn btn-sm btn-outline-primary w-100 py-1" onclick="${onConfirmCallbackName}(${h.id})">
          <i class="fa-solid fa-check me-1"></i>Confirm This Hazard
        </button>
      </div>
    </div>
  `;
}

function escapeHtml(text) {
  if (!text) return "";
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Global confirm hazard handler for popups
window.confirmHazardReport = function(hazardId) {
  fetch(`/api/hazards/${hazardId}/confirm`, {
    method: "POST",
    headers: { "Content-Type": "application/json" }
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      const countEl = document.getElementById(`conf-count-${hazardId}`);
      if (countEl) {
        countEl.innerHTML = `<i class="fa-solid fa-thumbs-up me-1 text-primary"></i>${data.confirmation_count}`;
      }
      alert("Thank you! You have confirmed this hazard report.");
    } else {
      alert(data.error || "Could not confirm this hazard.");
    }
  })
  .catch(err => {
    console.error("Error confirming report:", err);
    alert("Network error while submitting confirmation.");
  });
};

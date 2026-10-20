/**
 * SafePath AI - Admin Moderation and Analytics Controller
 */

let categoryChart = null;
let statusChart = null;

document.addEventListener("DOMContentLoaded", function () {
  initAdminDashboard();
});

function initAdminDashboard() {
  loadAdminReports();
  loadAnalyticsCharts();

  // Filters
  const statusFilter = document.getElementById("adminStatusFilter");
  const categoryFilter = document.getElementById("adminCategoryFilter");
  if (statusFilter) statusFilter.addEventListener("change", loadAdminReports);
  if (categoryFilter) categoryFilter.addEventListener("change", loadAdminReports);
}

function loadAdminReports() {
  const status = document.getElementById("adminStatusFilter")?.value || "";
  const category = document.getElementById("adminCategoryFilter")?.value || "";
  const tableBody = document.getElementById("adminReportsTableBody");

  if (!tableBody) return;
  tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted"><i class="fa-solid fa-spinner fa-spin me-2"></i>Loading reports...</td></tr>`;

  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (category) params.append("category", category);

  fetch(`/api/admin/reports?${params.toString()}`)
    .then(res => res.json())
    .then(data => {
      if (!data.success) {
        tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Failed to load reports.</td></tr>`;
        return;
      }

      const reports = data.reports || [];
      if (reports.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No hazard reports found matching filters.</td></tr>`;
        return;
      }

      let html = "";
      reports.forEach(r => {
        const statusBadge = r.verification_status === "verified"
          ? '<span class="badge bg-success">Verified</span>'
          : (r.verification_status === "rejected" ? '<span class="badge bg-danger">Rejected</span>' : '<span class="badge bg-warning text-dark">Pending</span>');

        const sevBadge = r.severity === "high"
          ? '<span class="badge bg-danger">High</span>'
          : (r.severity === "medium" ? '<span class="badge bg-warning text-dark">Medium</span>' : '<span class="badge bg-info text-dark">Low</span>');

        const photoBtn = r.photo_url
          ? `<button class="btn btn-sm btn-outline-secondary" onclick="viewReportPhoto('${r.photo_url}')"><i class="fa-solid fa-image"></i> Photo</button>`
          : '<span class="text-muted small">None</span>';

        html += `
          <tr id="admin-report-row-${r.id}">
            <td class="fw-bold">#${r.id}</td>
            <td>
              <div class="fw-semibold">${escapeHtml(r.category)}</div>
              <div class="small text-muted">${escapeHtml(r.description.substring(0, 55))}${r.description.length > 55 ? '...' : ''}</div>
            </td>
            <td>${sevBadge}</td>
            <td>
              <div class="small">${r.latitude.toFixed(4)}, ${r.longitude.toFixed(4)}</div>
              <div class="text-muted small">${r.author_name || 'Guest'}</div>
            </td>
            <td>${photoBtn}</td>
            <td>${statusBadge}</td>
            <td>
              <div class="btn-group btn-group-sm">
                <button class="btn btn-outline-success" title="Verify" onclick="updateReportStatus(${r.id}, 'verified')">
                  <i class="fa-solid fa-check"></i>
                </button>
                <button class="btn btn-outline-danger" title="Reject" onclick="updateReportStatus(${r.id}, 'rejected')">
                  <i class="fa-solid fa-xmark"></i>
                </button>
                <button class="btn btn-outline-dark" title="Delete" onclick="deleteReport(${r.id})">
                  <i class="fa-solid fa-trash"></i>
                </button>
              </div>
            </td>
          </tr>
        `;
      });

      tableBody.innerHTML = html;
    })
    .catch(err => {
      console.error("Admin load error:", err);
      tableBody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Error loading reports table.</td></tr>`;
    });
}

function updateReportStatus(reportId, newStatus) {
  const notes = prompt(`Optional moderation notes for marking as ${newStatus}:`, "");
  if (notes === null) return; // User pressed cancel

  fetch(`/api/admin/reports/${reportId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      verification_status: newStatus,
      moderation_notes: notes || undefined
    })
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        loadAdminReports();
        loadAnalyticsCharts();
      } else {
        alert(data.error || "Failed to update report.");
      }
    })
    .catch(err => {
      console.error("Update error:", err);
    });
}

function deleteReport(reportId) {
  if (!confirm(`Are you sure you want to permanently delete report #${reportId}?`)) return;

  fetch(`/api/admin/reports/${reportId}`, {
    method: "DELETE"
  })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        const row = document.getElementById(`admin-report-row-${reportId}`);
        if (row) row.remove();
        loadAnalyticsCharts();
      } else {
        alert(data.error || "Failed to delete report.");
      }
    })
    .catch(err => {
      console.error("Delete error:", err);
    });
}

function viewReportPhoto(url) {
  const imgEl = document.getElementById("adminPhotoModalImg");
  if (imgEl) {
    imgEl.src = url;
    const modal = new bootstrap.Modal(document.getElementById("adminPhotoModal"));
    modal.show();
  }
}

function loadAnalyticsCharts() {
  fetch("/api/admin/analytics")
    .then(res => res.json())
    .then(data => {
      if (!data.success) return;

      renderCategoryChart(data.category_counts);
      renderStatusChart(data.status_counts);
    })
    .catch(err => {
      console.warn("Analytics error:", err);
    });
}

function renderCategoryChart(counts) {
  const ctx = document.getElementById("adminCategoryChart");
  if (!ctx || typeof Chart === "undefined") return;

  const labels = Object.keys(counts).map(k => k.replace(/_/g, " ").toUpperCase());
  const values = Object.values(counts);

  if (categoryChart) categoryChart.destroy();

  categoryChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: [
          "#F59E0B", "#8B5CF6", "#F97316", "#EF4444", "#DC2626", "#D97706", "#0EA5E9"
        ]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom" }
      }
    }
  });
}

function renderStatusChart(counts) {
  const ctx = document.getElementById("adminStatusChart");
  if (!ctx || typeof Chart === "undefined") return;

  if (statusChart) statusChart.destroy();

  statusChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Pending", "Verified", "Rejected"],
      datasets: [{
        label: "Reports",
        data: [counts.pending || 0, counts.verified || 0, counts.rejected || 0],
        backgroundColor: ["#F59E0B", "#10B981", "#EF4444"],
        borderRadius: 8
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } }
      }
    }
  });
}

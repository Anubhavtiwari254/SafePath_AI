/**
 * SafePath AI - Emergency SOS & Location Sharing Controller
 */

let activeCountdownTimer = null;
let currentCoords = null;
let currentShareToken = null;

document.addEventListener("DOMContentLoaded", function () {
  initEmergencyControls();
});

function initEmergencyControls() {
  const triggerBtn = document.getElementById("triggerSosBtn");
  if (triggerBtn) {
    triggerBtn.addEventListener("click", startSosWorkflow);
  }

  const cancelBtn = document.getElementById("cancelSosCountdownBtn");
  if (cancelBtn) {
    cancelBtn.addEventListener("click", cancelSosWorkflow);
  }

  const revokeBtn = document.getElementById("revokeActiveShareBtn");
  if (revokeBtn) {
    revokeBtn.addEventListener("click", revokeCurrentShare);
  }

  // Trusted contact creation form
  const addContactForm = document.getElementById("addContactForm");
  if (addContactForm) {
    addContactForm.addEventListener("submit", handleAddContactSubmit);
  }
}

function startSosWorkflow() {
  const statusBox = document.getElementById("sosStatusBox");
  const stepGeo = document.getElementById("sosStepAcquiring");
  const stepCountdown = document.getElementById("sosStepCountdown");
  const stepActive = document.getElementById("sosStepActive");

  if (!navigator.geolocation) {
    alert("Geolocation is not supported by your device browser.");
    return;
  }

  // Step 1: Request Location
  if (statusBox) statusBox.classList.remove("d-none");
  if (stepGeo) stepGeo.classList.remove("d-none");
  if (stepCountdown) stepCountdown.classList.add("d-none");
  if (stepActive) stepActive.classList.add("d-none");

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      currentCoords = {
        latitude: pos.coords.latitude,
        longitude: pos.coords.longitude,
        accuracy_meters: pos.coords.accuracy
      };

      // Display coordinates preview
      const coordsText = document.getElementById("sosCoordsPreview");
      if (coordsText) {
        coordsText.textContent = `${currentCoords.latitude.toFixed(5)}, ${currentCoords.longitude.toFixed(5)} (±${Math.round(currentCoords.accuracy_meters)}m)`;
      }

      // Step 2: Show 5-second countdown with cancel option
      if (stepGeo) stepGeo.classList.add("d-none");
      if (stepCountdown) stepCountdown.classList.remove("d-none");

      let secondsLeft = 5;
      const timerEl = document.getElementById("sosCountdownSeconds");
      if (timerEl) timerEl.textContent = secondsLeft;

      activeCountdownTimer = setInterval(() => {
        secondsLeft--;
        if (timerEl) timerEl.textContent = secondsLeft;

        if (secondsLeft <= 0) {
          clearInterval(activeCountdownTimer);
          activeCountdownTimer = null;
          dispatchEmergencyAlert();
        }
      }, 1000);
    },
    (err) => {
      console.error("SOS Geolocation error:", err);
      if (statusBox) statusBox.classList.add("d-none");
      alert("Unable to acquire your GPS location. Please check browser location permissions and try again.");
    },
    { enableHighAccuracy: true, timeout: 10000 }
  );
}

function cancelSosWorkflow() {
  if (activeCountdownTimer) {
    clearInterval(activeCountdownTimer);
    activeCountdownTimer = null;
  }
  const statusBox = document.getElementById("sosStatusBox");
  if (statusBox) statusBox.classList.add("d-none");
  alert("Emergency SOS sharing was cancelled.");
}

function dispatchEmergencyAlert() {
  const stepCountdown = document.getElementById("sosStepCountdown");
  const stepActive = document.getElementById("sosStepActive");

  if (stepCountdown) stepCountdown.classList.add("d-none");
  if (stepActive) stepActive.classList.remove("d-none");

  const customMessage = document.getElementById("sosMessageInput")?.value || "Emergency SOS activated. Please check my live location.";

  fetch("/api/emergency/share", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      latitude: currentCoords.latitude,
      longitude: currentCoords.longitude,
      accuracy_meters: currentCoords.accuracy_meters,
      message: customMessage
    })
  })
    .then((res) => res.json())
    .then((data) => {
      if (!data.success) {
        alert(data.error || "Failed to activate emergency sharing.");
        return;
      }

      currentShareToken = data.token;

      // Populate UI with sharing links
      const shareUrlInput = document.getElementById("sosShareUrlInput");
      if (shareUrlInput) shareUrlInput.value = data.share_url;

      const viewBtn = document.getElementById("sosViewActiveLinkBtn");
      if (viewBtn) viewBtn.href = data.share_url;

      const smsBtn = document.getElementById("sosNativeSmsBtn");
      if (smsBtn) smsBtn.href = data.native_sms_url || `sms:?body=${encodeURIComponent(data.share_url)}`;

      const waBtn = document.getElementById("sosWhatsappBtn");
      if (waBtn) waBtn.href = data.whatsapp_url || `https://wa.me/?text=${encodeURIComponent(data.share_url)}`;

      // Setup native web share
      const webShareBtn = document.getElementById("sosWebShareBtn");
      if (webShareBtn) {
        if (navigator.share) {
          webShareBtn.classList.remove("d-none");
          webShareBtn.onclick = () => {
            navigator.share({
              title: "EMERGENCY: SafePath AI SOS",
              text: customMessage,
              url: data.share_url
            }).catch(e => console.warn("Share cancelled or failed", e));
          };
        } else {
          webShareBtn.classList.add("d-none");
        }
      }

      // Display delivery summary
      const deliveryBox = document.getElementById("sosDeliveryNotice");
      if (deliveryBox) {
        deliveryBox.innerHTML = `
          <div class="alert ${data.is_simulated ? 'alert-info' : 'alert-success'} border-0 small">
            <i class="fa-solid fa-circle-info me-1"></i>${escapeHtml(data.notification_summary || '')}
          </div>
        `;
      }
    })
    .catch((err) => {
      console.error("SOS Dispatch error:", err);
      alert("Error sending emergency signal. Please call local emergency numbers directly.");
    });
}

function copySosLink() {
  const input = document.getElementById("sosShareUrlInput");
  if (!input || !input.value) return;

  navigator.clipboard.writeText(input.value).then(() => {
    alert("Emergency link copied to clipboard! You can paste it into any messenger.");
  }).catch(() => {
    input.select();
    document.execCommand("copy");
    alert("Emergency link copied!");
  });
}

function revokeCurrentShare() {
  if (!currentShareToken) {
    alert("No active share token to revoke.");
    return;
  }

  if (!confirm("Are you sure you want to deactivate and revoke this live location link?")) {
    return;
  }

  fetch("/api/emergency/revoke", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ token: currentShareToken })
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        alert("Emergency location sharing has been permanently deactivated.");
        window.location.reload();
      } else {
        alert(data.error || "Failed to revoke link.");
      }
    })
    .catch((err) => {
      console.error("Revoke error:", err);
    });
}

function handleAddContactSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("contactNameInput").value.trim();
  const method = document.getElementById("contactMethodSelect").value;
  const val = document.getElementById("contactValueInput").value.trim();

  if (!name || !val) {
    alert("Please provide contact name and phone number/email.");
    return;
  }

  fetch("/api/contacts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      contact_name: name,
      contact_method: method,
      contact_value: val
    })
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        alert("Trusted contact added!");
        window.location.reload();
      } else {
        alert(data.error || "Could not add contact.");
      }
    })
    .catch((err) => {
      console.error("Contact add error:", err);
      alert("Network error adding contact.");
    });
}

function deleteTrustedContact(contactId) {
  if (!confirm("Remove this trusted contact?")) return;

  fetch(`/api/contacts/${contactId}`, {
    method: "DELETE"
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.success) {
        const row = document.getElementById(`contact-row-${contactId}`);
        if (row) row.remove();
      } else {
        alert(data.error || "Could not remove contact.");
      }
    })
    .catch((err) => {
      console.error("Delete contact error:", err);
    });
}

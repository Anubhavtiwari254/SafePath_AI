/**
 * SafePath AI - Report Hazard Form Controller
 */

let reportMap = null;
let reportPin = null;

document.addEventListener("DOMContentLoaded", function () {
  initReportHazardMap();
  initPhotoPreview();
});

function initReportHazardMap() {
  reportMap = initBaseMap("reportMap", 28.6315, 77.2167, 14);
  if (!reportMap) return;

  const latInput = document.getElementById("latitudeInput");
  const lngInput = document.getElementById("longitudeInput");
  const addrPreview = document.getElementById("selectedAddressPreview");

  function updatePin(lat, lon, updateInputs = true) {
    if (updateInputs) {
      if (latInput) latInput.value = lat.toFixed(6);
      if (lngInput) lngInput.value = lon.toFixed(6);
    }

    if (!reportPin) {
      reportPin = L.marker([lat, lon], {
        draggable: true,
        icon: L.divIcon({
          className: "report-draggable-pin",
          html: `<div style="background: #EF4444; color: white; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: 3px solid white; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.4);"><i class="fa-solid fa-location-dot"></i></div>`,
          iconSize: [34, 34],
          iconAnchor: [17, 34]
        })
      }).addTo(reportMap);

      reportPin.on("dragend", function (e) {
        const pos = e.target.getLatLng();
        updatePin(pos.lat, pos.lng, true);
      });
    } else {
      reportPin.setLatLng([lat, lon]);
    }

    // Reverse geocode preview
    if (addrPreview) {
      addrPreview.innerHTML = '<span class="text-muted"><i class="fa-solid fa-spinner fa-spin me-1"></i>Fetching address...</span>';
      fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`)
        .then(res => res.json())
        .then(data => {
          addrPreview.textContent = data.display_name || `Coordinates (${lat.toFixed(4)}, ${lon.toFixed(4)})`;
        })
        .catch(() => {
          addrPreview.textContent = `Coordinates: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
        });
    }
  }

  // Click on map to place/move pin
  reportMap.on("click", function (e) {
    updatePin(e.latlng.lat, e.latlng.lng, true);
  });

  // Current location button
  const locBtn = document.getElementById("reportCurrentLocationBtn");
  if (locBtn) {
    locBtn.addEventListener("click", function () {
      if (!navigator.geolocation) {
        alert("Geolocation not supported by your browser.");
        return;
      }
      locBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin me-1"></i>Finding you...';
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          reportMap.setView([lat, lon], 16);
          updatePin(lat, lon, true);
          locBtn.innerHTML = '<i class="fa-solid fa-crosshairs me-1"></i>Pin My Location';
        },
        (err) => {
          console.warn("Geolocation error:", err);
          alert("Unable to acquire location. Please click directly on the map to set location.");
          locBtn.innerHTML = '<i class="fa-solid fa-crosshairs me-1"></i>Pin My Location';
        },
        { enableHighAccuracy: true, timeout: 8000 }
      );
    });
  }

  // Default initial pin at center
  updatePin(28.6315, 77.2167, true);
}

function initPhotoPreview() {
  const photoInput = document.getElementById("photoInput");
  const previewContainer = document.getElementById("photoPreviewContainer");
  const previewImg = document.getElementById("photoPreview");

  if (!photoInput || !previewContainer || !previewImg) return;

  photoInput.addEventListener("change", function () {
    const file = this.files[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        alert("Photo exceeds 5MB size limit. Please choose a smaller image.");
        this.value = "";
        previewContainer.classList.add("d-none");
        return;
      }

      const reader = new FileReader();
      reader.onload = function (e) {
        previewImg.src = e.target.result;
        previewContainer.classList.remove("d-none");
      };
      reader.readAsDataURL(file);
    } else {
      previewContainer.classList.add("d-none");
    }
  });
}

import logging
import requests
from typing import Optional, List, Dict, Any
from config import Config

logger = logging.getLogger(__name__)

# Sample well-known coordinates for instant demo/fallback when offline or rate-limited
KNOWN_FALLBACKS: Dict[str, Dict[str, Any]] = {
    "connaught place": {"lat": 28.6315, "lon": 77.2167, "display_name": "Connaught Place, New Delhi, Delhi, India"},
    "india gate": {"lat": 28.6129, "lon": 77.2295, "display_name": "India Gate, Rajpath, New Delhi, Delhi, India"},
    "delhi university": {"lat": 28.6892, "lon": 77.2106, "display_name": "University of Delhi, North Campus, Delhi, India"},
    "central station": {"lat": 28.6430, "lon": 77.2197, "display_name": "New Delhi Central Railway Station, Delhi, India"},
    "times square": {"lat": 40.7580, "lon": -73.9855, "display_name": "Times Square, Manhattan, New York, NY, USA"},
    "central park": {"lat": 40.7851, "lon": -73.9683, "display_name": "Central Park, New York, NY, USA"},
    "brooklyn bridge": {"lat": 40.7061, "lon": -73.9969, "display_name": "Brooklyn Bridge, New York, NY, USA"},
    "hyde park": {"lat": 51.5073, "lon": -0.1657, "display_name": "Hyde Park, London, United Kingdom"},
    "big ben": {"lat": 51.5007, "lon": -0.1246, "display_name": "Big Ben, Westminster, London, United Kingdom"},
    "koramangala": {"lat": 12.9352, "lon": 77.6245, "display_name": "Koramangala, Bengaluru, Karnataka, India"},
    "indiranagar": {"lat": 12.9784, "lon": 77.6408, "display_name": "Indiranagar, Bengaluru, Karnataka, India"},
    "mg road": {"lat": 12.9753, "lon": 77.6066, "display_name": "MG Road, Bengaluru, Karnataka, India"},
}


class GeocodingService:
    """Geocoding service using OpenStreetMap Nominatim with offline fallback."""

    USER_AGENT = "SafePathAI/1.0 (safety_routing_app)"

    @classmethod
    def search(cls, query: str) -> List[Dict[str, Any]]:
        """Geocode text address into coordinates."""
        query_clean = query.strip()
        if not query_clean:
            return []

        # Check known fallback locations first for instant exact match
        query_lower = query_clean.lower()
        matched_fallbacks = [
            v for k, v in KNOWN_FALLBACKS.items() if k in query_lower or query_lower in k
        ]
        
        try:
            url = f"{Config.NOMINATIM_BASE_URL}/search"
            headers = {"User-Agent": cls.USER_AGENT}
            params = {
                "q": query_clean,
                "format": "json",
                "limit": 5,
                "addressdetails": 1
            }
            resp = requests.get(url, params=params, headers=headers, timeout=4)
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    return [
                        {
                            "lat": float(item["lat"]),
                            "lon": float(item["lon"]),
                            "display_name": item.get("display_name", query_clean),
                            "type": item.get("type", "location")
                        }
                        for item in results
                    ]
        except Exception as e:
            logger.warning("Nominatim geocoding lookup failed: %s. Using fallback if available.", e)

        # Fallback to predefined demo locations or simulated coordinate point
        if matched_fallbacks:
            return matched_fallbacks

        # If user entered coordinate pair e.g. "28.63, 77.21"
        try:
            parts = [float(p.strip()) for p in query_clean.split(",")]
            if len(parts) == 2 and -90 <= parts[0] <= 90 and -180 <= parts[1] <= 180:
                return [{
                    "lat": parts[0],
                    "lon": parts[1],
                    "display_name": f"Coordinates ({parts[0]:.4f}, {parts[1]:.4f})",
                    "type": "coordinate"
                }]
        except ValueError:
            pass

        return []

    @classmethod
    def reverse(cls, lat: float, lon: float) -> str:
        """Reverse geocode coordinates into readable street address."""
        try:
            url = f"{Config.NOMINATIM_BASE_URL}/reverse"
            headers = {"User-Agent": cls.USER_AGENT}
            params = {
                "lat": lat,
                "lon": lon,
                "format": "json"
            }
            resp = requests.get(url, params=params, headers=headers, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                if "display_name" in data:
                    return data["display_name"]
        except Exception as e:
            logger.warning("Nominatim reverse geocoding failed: %s", e)

        # Formatted fallback
        lat_dir = "N" if lat >= 0 else "S"
        lon_dir = "E" if lon >= 0 else "W"
        return f"Location near {abs(lat):.4f}° {lat_dir}, {abs(lon):.4f}° {lon_dir}"

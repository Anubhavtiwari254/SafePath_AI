import math
import logging
import requests
from typing import List, Dict, Any, Tuple
from config import Config

logger = logging.getLogger(__name__)


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two lat/lon coordinates."""
    r = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


class RoutingService:
    """Routing service integrating OSRM with realistic simulation fallback."""

    PROFILE_MAP = {
        "walking": "foot",
        "foot": "foot",
        "cycling": "bike",
        "bike": "bike",
        "driving": "car",
        "car": "car"
    }

    SPEEDS_MPS = {
        "foot": 1.35,   # ~4.8 km/h
        "bike": 4.15,   # ~15 km/h
        "car": 11.1     # ~40 km/h in urban streets
    }

    @classmethod
    def get_routes(
        cls,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        mode: str = "walking"
    ) -> List[Dict[str, Any]]:
        """Fetch multiple route options between two points."""
        osrm_profile = cls.PROFILE_MAP.get(mode.lower(), "foot")
        routes = []

        try:
            # OSRM expects coordinates in lng,lat format
            coord_str = f"{start_lng:.6f},{start_lat:.6f};{end_lng:.6f},{end_lat:.6f}"
            url = f"{Config.OSRM_BASE_URL}/route/v1/{osrm_profile}/{coord_str}"
            params = {
                "overview": "full",
                "geometries": "geojson",
                "alternatives": "true",
                "steps": "true"
            }
            
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == "Ok" and "routes" in data:
                    for i, r in enumerate(data["routes"]):
                        # GeoJSON coordinates are [lon, lat], convert to [lat, lon] for Leaflet
                        geojson_coords = r.get("geometry", {}).get("coordinates", [])
                        leaflet_coords = [[pt[1], pt[0]] for pt in geojson_coords]
                        
                        dist_m = float(r.get("distance", 0.0))
                        dur_s = float(r.get("duration", 0.0))
                        
                        name = f"Route {chr(65 + i)}"
                        if i == 0:
                            name = "Primary Thoroughfare"
                        elif i == 1:
                            name = "Secondary Boulevard"
                        else:
                            name = f"Alternative Path {i}"

                        routes.append({
                            "id": f"route_{i + 1}",
                            "name": name,
                            "distance_meters": dist_m,
                            "distance_km": round(dist_m / 1000.0, 2),
                            "duration_seconds": dur_s,
                            "duration_minutes": max(1, round(dur_s / 60.0)),
                            "coordinates": leaflet_coords,
                            "mode": mode,
                            "source": "osrm"
                        })
                    if routes:
                        return routes
        except Exception as e:
            logger.warning("OSRM routing request failed: %s. Using internal routing generator.", e)

        # Fallback generator: create 2-3 realistic alternative paths
        return cls._generate_fallback_routes(start_lat, start_lng, end_lat, end_lng, osrm_profile, mode)

    @classmethod
    def _generate_fallback_routes(
        cls,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        osrm_profile: str,
        mode: str
    ) -> List[Dict[str, Any]]:
        """Generate realistic route trajectories when external routing engine is unreachable."""
        direct_dist = calculate_haversine_distance(start_lat, start_lng, end_lat, end_lng)
        speed = cls.SPEEDS_MPS.get(osrm_profile, 1.4)
        num_steps = max(8, min(24, int(direct_dist / 80)))

        routes = []

        # Route 1: Direct main road (slight S-curve)
        coords1 = []
        for i in range(num_steps + 1):
            t = i / float(num_steps)
            # Add subtle natural curve
            lat_offset = math.sin(t * math.pi) * 0.0004
            lon_offset = math.sin(t * math.pi * 2) * 0.0003
            lat = start_lat + t * (end_lat - start_lat) + lat_offset
            lon = start_lng + t * (end_lng - start_lng) + lon_offset
            coords1.append([round(lat, 6), round(lon, 6)])
        
        dist1 = direct_dist * 1.08
        dur1 = dist1 / speed
        routes.append({
            "id": "route_1",
            "name": "Main Transit Corridor",
            "distance_meters": round(dist1, 1),
            "distance_km": round(dist1 / 1000.0, 2),
            "duration_seconds": round(dur1, 0),
            "duration_minutes": max(1, round(dur1 / 60.0)),
            "coordinates": coords1,
            "mode": mode,
            "source": "simulated"
        })

        # Route 2: Well-lit boulevard detour (arcing north/east)
        coords2 = []
        dlat = end_lat - start_lat
        dlon = end_lng - start_lng
        perp_lat = -dlon * 0.18
        perp_lon = dlat * 0.18

        for i in range(num_steps + 1):
            t = i / float(num_steps)
            arc = math.sin(t * math.pi)
            lat = start_lat + t * dlat + arc * perp_lat
            lon = start_lng + t * dlon + arc * perp_lon
            coords2.append([round(lat, 6), round(lon, 6)])

        dist2 = direct_dist * 1.22
        dur2 = dist2 / speed
        routes.append({
            "id": "route_2",
            "name": "Perimeter Avenue (Well-Lit)",
            "distance_meters": round(dist2, 1),
            "distance_km": round(dist2 / 1000.0, 2),
            "duration_seconds": round(dur2, 0),
            "duration_minutes": max(1, round(dur2 / 60.0)),
            "coordinates": coords2,
            "mode": mode,
            "source": "simulated"
        })

        # Route 3: Shorter interior pathway
        coords3 = []
        for i in range(num_steps + 1):
            t = i / float(num_steps)
            arc = -math.sin(t * math.pi)
            lat = start_lat + t * dlat + arc * (perp_lat * 0.75)
            lon = start_lng + t * dlon + arc * (perp_lon * 0.75)
            coords3.append([round(lat, 6), round(lon, 6)])

        dist3 = direct_dist * 1.14
        dur3 = dist3 / speed
        routes.append({
            "id": "route_3",
            "name": "Inner Connecting Stretches",
            "distance_meters": round(dist3, 1),
            "distance_km": round(dist3 / 1000.0, 2),
            "duration_seconds": round(dur3, 0),
            "duration_minutes": max(1, round(dur3 / 60.0)),
            "coordinates": coords3,
            "mode": mode,
            "source": "simulated"
        })

        return routes

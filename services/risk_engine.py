import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from config import Config
from .routing_service import calculate_haversine_distance


def distance_point_to_segment(
    px: float, py: float,
    ax: float, ay: float,
    bx: float, by: float
) -> float:
    """
    Calculate shortest distance in meters from point P (lat, lon)
    to line segment AB (lat1, lon1) -> (lat2, lon2).
    """
    # Convert lat/lon degrees to approximate local meter projection
    # 1 deg lat ~ 111,000 m
    # 1 deg lon ~ 111,000 * cos(lat) m
    mean_lat_rad = math.radians((ax + bx + px) / 3.0)
    lat_scale = 111000.0
    lon_scale = 111000.0 * math.cos(mean_lat_rad)

    # Segment vector in local meters
    dx = (bx - ax) * lat_scale
    dy = (by - ay) * lon_scale
    seg_len_sq = dx * dx + dy * dy

    if seg_len_sq < 1e-6:
        # Segment is essentially a single point
        return calculate_haversine_distance(px, py, ax, ay)

    # Project point P onto segment AB
    px_m = (px - ax) * lat_scale
    py_m = (py - ay) * lon_scale
    t = max(0.0, min(1.0, (px_m * dx + py_m * dy) / seg_len_sq))

    proj_lat = ax + t * (bx - ax)
    proj_lon = ay + t * (by - ay)

    return calculate_haversine_distance(px, py, proj_lat, proj_lon)


def distance_point_to_polyline(point_lat: float, point_lon: float, polyline: List[List[float]]) -> float:
    """Find the minimum distance in meters from point to any segment in the polyline."""
    if not polyline:
        return float("inf")
    if len(polyline) == 1:
        return calculate_haversine_distance(point_lat, point_lon, polyline[0][0], polyline[0][1])

    min_dist = float("inf")
    for i in range(len(polyline) - 1):
        dist = distance_point_to_segment(
            point_lat, point_lon,
            polyline[i][0], polyline[i][1],
            polyline[i + 1][0], polyline[i + 1][1]
        )
        if dist < min_dist:
            min_dist = dist
            if min_dist < 5.0:  # Early exit if right on the path
                break

    return min_dist


class RiskEngine:
    """
    Explainable Risk and Safety Scoring Engine.
    
    Evaluates routes against community hazard reports within a 250m corridor.
    Applies transparent, documented penalties weighted by category, severity,
    proximity, recency, and verification.
    """

    MAX_BUFFER_METERS = 250.0  # Hazards beyond 250m from path are not considered

    @classmethod
    def evaluate_route(cls, route: Dict[str, Any], hazards: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate safety score and generate detailed factor explanation for a single route.
        """
        polyline = route.get("coordinates", [])
        if not polyline:
            return {
                "safety_score": 50,
                "category": "Moderate Reported Risk",
                "badge_color": "warning",
                "status": "insufficient_data",
                "explanation_summary": "Insufficient route geometry to evaluate risk.",
                "factors": [],
                "hazards_count": 0,
                "total_penalty": 0
            }

        nearby_hazards = []
        factors = []
        total_deduction = 0.0
        now = datetime.now(timezone.utc)

        # Baseline starting score is 100 (clean route)
        baseline_score = 100.0

        for h in hazards:
            # Skip rejected reports
            if h.get("verification_status") == "rejected":
                continue

            h_lat = float(h.get("latitude", 0.0))
            h_lon = float(h.get("longitude", 0.0))

            dist_meters = distance_point_to_polyline(h_lat, h_lon, polyline)

            if dist_meters <= cls.MAX_BUFFER_METERS:
                category_key = h.get("category", "other_concern")
                category_cfg = Config.HAZARD_CATEGORIES.get(category_key, Config.HAZARD_CATEGORIES["other_concern"])
                base_penalty = float(category_cfg.get("base_penalty", 10))

                # 1. Severity multiplier
                severity_key = h.get("severity", "medium").lower()
                sev_cfg = Config.SEVERITY_LEVELS.get(severity_key, Config.SEVERITY_LEVELS["medium"])
                severity_mult = float(sev_cfg.get("multiplier", 1.0))

                # 2. Proximity decay
                if dist_meters <= 50:
                    proximity_mult = 1.0
                    prox_desc = "directly on/adjacent to route (<50m)"
                elif dist_meters <= 150:
                    proximity_mult = 0.65
                    prox_desc = f"nearby (~{int(dist_meters)}m)"
                else:
                    proximity_mult = 0.35
                    prox_desc = f"in corridor perimeter (~{int(dist_meters)}m)"

                # 3. Recency decay
                inc_dt = h.get("incident_datetime")
                recency_mult = 1.0
                recency_desc = "recently reported"
                if inc_dt:
                    try:
                        if isinstance(inc_dt, str):
                            dt = datetime.fromisoformat(inc_dt)
                        else:
                            dt = inc_dt
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        days_old = max(0, (now - dt).days)
                        if days_old <= 3:
                            recency_mult = 1.0
                            recency_desc = "reported in last 3 days"
                        elif days_old <= 14:
                            recency_mult = 0.8
                            recency_desc = f"reported {days_old} days ago"
                        elif days_old <= 30:
                            recency_mult = 0.6
                            recency_desc = f"reported {days_old} days ago"
                        else:
                            recency_mult = 0.4
                            recency_desc = "older historical report (>30d)"
                    except Exception:
                        recency_mult = 0.8

                # 4. Verification multiplier
                status = h.get("verification_status", "pending")
                confirmations = int(h.get("confirmation_count", 0))
                if status == "verified":
                    # Verified reports carry full weight + minor boost per confirmation
                    verification_mult = min(1.25, 1.0 + (confirmations * 0.05))
                    status_desc = "Verified"
                else:
                    verification_mult = 0.55
                    status_desc = "Community Pending"

                penalty = base_penalty * severity_mult * proximity_mult * recency_mult * verification_mult
                penalty = round(penalty, 1)

                total_deduction += penalty

                factor_item = {
                    "hazard_id": h.get("id"),
                    "category": category_key,
                    "category_label": category_cfg.get("label"),
                    "icon": category_cfg.get("icon"),
                    "severity": severity_key,
                    "distance_meters": round(dist_meters, 1),
                    "penalty": penalty,
                    "status": status_desc,
                    "explanation": f"{sev_cfg['label']} '{category_cfg['label']}' located {prox_desc} ({status_desc}, {recency_desc}): -{penalty:.1f} pts"
                }
                factors.append(factor_item)
                nearby_hazards.append({
                    "id": h.get("id"),
                    "category": category_key,
                    "latitude": h_lat,
                    "longitude": h_lon,
                    "distance": round(dist_meters, 1)
                })

        # Calculate final normalized safety score
        safety_score = max(5.0, min(100.0, baseline_score - total_deduction))
        safety_score = round(safety_score, 1)

        # Categorization & explanation summary
        if len(factors) == 0:
            category = "Lower Reported Risk"
            badge_color = "success"
            summary = "No community-reported hazards along this corridor. Safe travel conditions based on available reports."
            status = "clean"
        elif safety_score >= 80:
            category = "Lower Reported Risk"
            badge_color = "success"
            summary = f"Favorable conditions. Only {len(factors)} minor safety concern(s) noted nearby."
            status = "good"
        elif safety_score >= 50:
            category = "Moderate Reported Risk"
            badge_color = "warning"
            summary = f"Moderate caution advised. Route has {len(factors)} reported hazard(s) in the vicinity."
            status = "caution"
        else:
            category = "Higher Reported Risk"
            badge_color = "danger"
            summary = f"Higher reported hazard concentration ({len(factors)} reports nearby). Consider alternative paths if walking alone."
            status = "warning"

        # Check if corridor is completely empty in an area with zero community coverage
        if len(hazards) == 0:
            status = "insufficient_data"
            category = "Insufficient Safety Data"
            badge_color = "secondary"
            summary = "No community hazard reports are available for this area yet. Exercise general personal awareness."

        return {
            "safety_score": safety_score,
            "category": category,
            "badge_color": badge_color,
            "status": status,
            "explanation_summary": summary,
            "factors": factors,
            "hazards_count": len(factors),
            "total_penalty": round(total_deduction, 1),
            "nearby_hazards": nearby_hazards
        }

    @classmethod
    def rank_routes(
        cls,
        routes: List[Dict[str, Any]],
        hazards: List[Dict[str, Any]],
        preference: str = "safest"
    ) -> List[Dict[str, Any]]:
        """
        Evaluate and rank all route alternatives according to user preference:
        - 'safest': Prioritize highest safety score
        - 'fastest': Prioritize lowest travel duration
        - 'balanced': Optimal balance between safety score and travel time
        """
        evaluated_routes = []
        for r in routes:
            eval_result = cls.evaluate_route(r, hazards)
            # Combine route data with risk evaluation
            combined = {**r, **eval_result}
            evaluated_routes.append(combined)

        if not evaluated_routes:
            return []

        # Find min/max duration for normalization in balanced mode
        durations = [r["duration_seconds"] for r in evaluated_routes]
        min_dur = min(durations) if durations else 1.0
        max_dur = max(durations) if durations else 1.0

        for r in evaluated_routes:
            # Time efficiency score (100 = fastest among choices, down to 50 for slowest)
            if max_dur > min_dur:
                time_efficiency = 100.0 - ((r["duration_seconds"] - min_dur) / (max_dur - min_dur) * 40.0)
            else:
                time_efficiency = 100.0

            # Composite score calculation
            r["time_efficiency_score"] = round(time_efficiency, 1)
            r["composite_score"] = round(
                (r["safety_score"] * 0.70) + (time_efficiency * 0.30), 1
            )

        # Sort according to preference
        pref = preference.lower()
        if pref == "safest":
            evaluated_routes.sort(key=lambda x: (x["safety_score"], -x["duration_seconds"]), reverse=True)
        elif pref == "fastest":
            evaluated_routes.sort(key=lambda x: (x["duration_seconds"], -x["safety_score"]))
        else:  # balanced
            evaluated_routes.sort(key=lambda x: x["composite_score"], reverse=True)

        # Mark top route as recommended
        for idx, r in enumerate(evaluated_routes):
            r["rank"] = idx + 1
            r["is_recommended"] = (idx == 0)
            if idx == 0:
                if pref == "safest":
                    r["recommendation_tag"] = "Safest Option"
                elif pref == "fastest":
                    r["recommendation_tag"] = "Fastest Option"
                else:
                    r["recommendation_tag"] = "Best Balanced Route"

        return evaluated_routes

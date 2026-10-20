from flask import Blueprint, render_template, request, jsonify
from config import Config
from models import HazardReport
from services.geocoding_service import GeocodingService
from services.routing_service import RoutingService
from services.risk_engine import RiskEngine

route_bp = Blueprint("routes", __name__)


@route_bp.route("/routes")
def route_finder_page():
    """Dedicated Safe Route Finder page."""
    return render_template("route_finder.html", categories=Config.HAZARD_CATEGORIES)


@route_bp.route("/api/routes", methods=["GET"])
def get_routes_api():
    """
    Search routes and compute explainable risk scores.
    Accepts coordinates or text addresses for origin and destination.
    """
    origin_text = request.args.get("origin", "").strip()
    dest_text = request.args.get("destination", "").strip()
    mode = request.args.get("mode", "walking").lower()
    preference = request.args.get("preference", "safest").lower()

    start_lat = request.args.get("start_lat", type=float)
    start_lng = request.args.get("start_lng", type=float)
    end_lat = request.args.get("end_lat", type=float)
    end_lng = request.args.get("end_lng", type=float)

    origin_info = {}
    destination_info = {}

    # Resolve coordinates if not provided directly
    if start_lat is None or start_lng is None:
        if not origin_text:
            return jsonify({"success": False, "error": "Starting location is required."}), 400
        geo_results = GeocodingService.search(origin_text)
        if not geo_results:
            return jsonify({"success": False, "error": f"Could not find coordinates for origin: '{origin_text}'"}), 404
        start_lat = geo_results[0]["lat"]
        start_lng = geo_results[0]["lon"]
        origin_info = geo_results[0]
    else:
        origin_info = {
            "lat": start_lat,
            "lon": start_lng,
            "display_name": origin_text or f"Point ({start_lat:.4f}, {start_lng:.4f})"
        }

    if end_lat is None or end_lng is None:
        if not dest_text:
            return jsonify({"success": False, "error": "Destination is required."}), 400
        geo_results = GeocodingService.search(dest_text)
        if not geo_results:
            return jsonify({"success": False, "error": f"Could not find coordinates for destination: '{dest_text}'"}), 404
        end_lat = geo_results[0]["lat"]
        end_lng = geo_results[0]["lon"]
        destination_info = geo_results[0]
    else:
        destination_info = {
            "lat": end_lat,
            "lon": end_lng,
            "display_name": dest_text or f"Point ({end_lat:.4f}, {end_lng:.4f})"
        }

    # Fetch relevant active community hazard reports
    # In production with massive datasets, filter by spatial bounding box + buffer.
    # Here, we fetch non-rejected reports and pass them to the corridor filter.
    active_reports = HazardReport.query.filter(HazardReport.verification_status != "rejected").all()
    hazards_data = [r.to_dict(public_view=True) for r in active_reports]

    # Generate route alternatives
    raw_routes = RoutingService.get_routes(start_lat, start_lng, end_lat, end_lng, mode=mode)
    if not raw_routes:
        return jsonify({"success": False, "error": "No route could be found between these locations."}), 404

    # Rank and evaluate routes with Risk Engine
    ranked_routes = RiskEngine.rank_routes(raw_routes, hazards_data, preference=preference)

    return jsonify({
        "success": True,
        "origin": origin_info,
        "destination": destination_info,
        "mode": mode,
        "preference": preference,
        "routes_count": len(ranked_routes),
        "routes": ranked_routes,
        "hazards": hazards_data,
        "disclaimer": "Safety scores are estimates derived from community-reported hazards and are not guarantees of personal safety."
    })


@route_bp.route("/api/routes/safety-score", methods=["POST"])
def calculate_safety_score_api():
    """Direct safety score calculation for an arbitrary polyline."""
    data = request.get_json() or {}
    coordinates = data.get("coordinates", [])

    if not coordinates or not isinstance(coordinates, list):
        return jsonify({"success": False, "error": "Valid polyline coordinates array required."}), 400

    active_reports = HazardReport.query.filter(HazardReport.verification_status != "rejected").all()
    hazards_data = [r.to_dict(public_view=True) for r in active_reports]

    route_mock = {"coordinates": coordinates, "duration_seconds": 600}
    result = RiskEngine.evaluate_route(route_mock, hazards_data)

    return jsonify({
        "success": True,
        "evaluation": result
    })

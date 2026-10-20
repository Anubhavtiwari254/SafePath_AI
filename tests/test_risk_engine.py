from services.risk_engine import RiskEngine, distance_point_to_polyline
from services.routing_service import calculate_haversine_distance


def test_haversine_and_distance_calculations():
    # Distance between CP and India Gate ~2.2 km
    dist = calculate_haversine_distance(28.6315, 77.2167, 28.6129, 77.2295)
    assert 2000 < dist < 2600

    # Point directly on a line segment
    line = [[28.6300, 77.2100], [28.6300, 77.2200]]
    d = distance_point_to_polyline(28.6300, 77.2150, line)
    assert d < 5.0  # Should be practically 0 meters


def test_clean_route_evaluation():
    route = {
        "id": "r1",
        "coordinates": [[28.6300, 77.2100], [28.6350, 77.2150]],
        "duration_seconds": 600
    }
    # No hazards
    eval_result = RiskEngine.evaluate_route(route, [])
    assert eval_result["safety_score"] == 100.0
    assert eval_result["status"] == "insufficient_data"


def test_hazard_deduction_in_corridor():
    route = {
        "id": "r1",
        "coordinates": [[28.6300, 77.2100], [28.6350, 77.2150]],
        "duration_seconds": 600
    }
    # Hazard right on corridor (~20m)
    hazards = [{
        "id": 1,
        "latitude": 28.6301,
        "longitude": 77.2101,
        "category": "harassment",
        "severity": "high",
        "verification_status": "verified",
        "confirmation_count": 2
    }]

    eval_result = RiskEngine.evaluate_route(route, hazards)
    assert eval_result["safety_score"] < 100.0
    assert eval_result["hazards_count"] == 1
    assert len(eval_result["factors"]) == 1
    assert "Harassment" in eval_result["factors"][0]["explanation"]


def test_hazard_outside_buffer_ignored():
    route = {
        "id": "r1",
        "coordinates": [[28.6300, 77.2100], [28.6350, 77.2150]],
        "duration_seconds": 600
    }
    # Hazard far away (> 1 km away)
    hazards = [{
        "id": 2,
        "latitude": 28.6500,
        "longitude": 77.2300,
        "category": "broken_streetlights",
        "severity": "high",
        "verification_status": "verified"
    }]

    eval_result = RiskEngine.evaluate_route(route, hazards)
    assert eval_result["safety_score"] == 100.0
    assert eval_result["hazards_count"] == 0


def test_route_ranking_preferences():
    # Route 1: North loop (longer duration, but completely clean of hazards)
    r1 = {
        "id": "safe_but_longer",
        "name": "Route 1 (North Loop)",
        "coordinates": [[28.6400, 77.2100], [28.6450, 77.2150], [28.6400, 77.2200]],
        "duration_seconds": 900
    }
    # Route 2: Direct path (fast duration, but has a high hazard right on it)
    r2 = {
        "id": "fast_but_hazard",
        "name": "Route 2 (Direct South)",
        "coordinates": [[28.6200, 77.2100], [28.6200, 77.2150], [28.6200, 77.2200]],
        "duration_seconds": 400
    }

    # Place hazard directly on r2's southern line
    hazards = [{
        "id": 3,
        "latitude": 28.6200,
        "longitude": 77.2150,
        "category": "harassment",
        "severity": "high",
        "verification_status": "verified"
    }]

    # When preference = 'safest', r1 should rank first (it has no hazards nearby, score = 100)
    ranked_safe = RiskEngine.rank_routes([r1, r2], hazards, preference="safest")
    assert ranked_safe[0]["id"] == "safe_but_longer"

    # When preference = 'fastest', r2 should rank first (duration 400s < 900s)
    ranked_fast = RiskEngine.rank_routes([r1, r2], hazards, preference="fastest")
    assert ranked_fast[0]["id"] == "fast_but_hazard"

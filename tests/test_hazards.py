import json


def test_submit_hazard_report(client):
    res = client.post("/api/hazards", json={
        "latitude": 28.6315,
        "longitude": 77.2167,
        "category": "broken_streetlights",
        "description": "Streetlight broken on east corridor walkway.",
        "severity": "medium"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["report"]["category"] == "broken_streetlights"
    assert data["report"]["verification_status"] == "pending"


def test_submit_hazard_invalid_category(client):
    res = client.post("/api/hazards", json={
        "latitude": 28.6315,
        "longitude": 77.2167,
        "category": "non_existent_category",
        "description": "Testing category validation rejection.",
        "severity": "medium"
    })
    assert res.status_code == 400


def test_hazard_confirmation(client):
    # Create report
    res_create = client.post("/api/hazards", json={
        "latitude": 28.6320,
        "longitude": 77.2170,
        "category": "isolated_areas",
        "description": "Dark pathway with no security monitoring.",
        "severity": "high"
    })
    report_id = res_create.get_json()["report"]["id"]

    # Confirm report
    res_conf = client.post(f"/api/hazards/{report_id}/confirm")
    assert res_conf.status_code == 200
    assert res_conf.get_json()["confirmation_count"] == 1

    # Duplicate confirmation from same client should fail
    res_dup = client.post(f"/api/hazards/{report_id}/confirm")
    assert res_dup.status_code == 400


def test_get_hazards_filtering(client):
    # Add two reports with different categories
    client.post("/api/hazards", json={
        "latitude": 28.6300,
        "longitude": 77.2100,
        "category": "broken_streetlights",
        "description": "Report one for filter test.",
        "severity": "low"
    })
    client.post("/api/hazards", json={
        "latitude": 28.6400,
        "longitude": 77.2200,
        "category": "road_damage",
        "description": "Report two for filter test.",
        "severity": "high"
    })

    res = client.get("/api/hazards?category=road_damage")
    assert res.status_code == 200
    hazards = res.get_json()["hazards"]
    assert all(h["category"] == "road_damage" for h in hazards)

import json


def test_activate_and_query_emergency_share(client):
    # Activate SOS
    res = client.post("/api/emergency/share", json={
        "latitude": 28.6315,
        "longitude": 77.2167,
        "accuracy_meters": 15.0,
        "message": "Testing emergency broadcast"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data
    assert "share_url" in data
    assert data["is_simulated"] is True  # In test mode without twilio credentials
    assert "simulated" in data["notification_summary"].lower()

    token = data["token"]

    # Query location via token
    res_loc = client.get(f"/api/emergency/location/{token}")
    assert res_loc.status_code == 200
    loc_data = res_loc.get_json()["share"]
    assert loc_data["current_lat"] == 28.6315
    assert loc_data["is_active"] is True

    # Revoke share
    res_rev = client.post("/api/emergency/revoke", json={"token": token})
    assert res_rev.status_code == 200

    # Query location after revocation should return 410 Gone / inactive
    res_rev_loc = client.get(f"/api/emergency/location/{token}")
    assert res_rev_loc.status_code == 410

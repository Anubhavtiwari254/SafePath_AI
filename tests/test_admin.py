from models import HazardReport, ModerationLog


def test_admin_access_control(client, auth_user, admin_user):
    # Unauthenticated user cannot access admin
    res_guest = client.get("/admin")
    assert res_guest.status_code == 302  # redirects to login

    # Normal user gets 403 Forbidden
    client.post("/api/auth/login", json={"email": auth_user["email"], "password": auth_user["password"]})
    res_user = client.get("/admin")
    assert res_user.status_code == 403
    client.post("/api/auth/logout")

    # Admin user can access
    client.post("/api/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})
    res_admin = client.get("/admin")
    assert res_admin.status_code == 200


def test_admin_report_moderation(client, admin_user):
    # Log in as admin
    client.post("/api/auth/login", json={"email": admin_user["email"], "password": admin_user["password"]})

    # Submit a report
    res_create = client.post("/api/hazards", json={
        "latitude": 28.6315,
        "longitude": 77.2167,
        "category": "road_damage",
        "description": "Deep ditch on street.",
        "severity": "low"
    })
    report_id = res_create.get_json()["report"]["id"]

    # Verify report via admin PATCH API
    res_mod = client.patch(f"/api/admin/reports/{report_id}", json={
        "verification_status": "verified",
        "severity": "high",
        "moderation_notes": "Verified by street inspection team."
    })
    assert res_mod.status_code == 200
    data = res_mod.get_json()["report"]
    assert data["verification_status"] == "verified"
    assert data["severity"] == "high"

    # Check analytics API
    res_an = client.get("/api/admin/analytics")
    assert res_an.status_code == 200
    an_data = res_an.get_json()
    assert an_data["status_counts"]["verified"] >= 1

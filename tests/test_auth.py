import json


def test_register_success(client):
    res = client.post("/api/auth/register", json={
        "name": "Jane Doe",
        "email": "jane@example.com",
        "password": "securepassword123"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert data["user"]["email"] == "jane@example.com"


def test_register_duplicate_email(client, auth_user):
    res = client.post("/api/auth/register", json={
        "name": "Duplicate Tester",
        "email": auth_user["email"],
        "password": "password123"
    })
    assert res.status_code == 409
    data = res.get_json()
    assert data["success"] is False


def test_login_success_and_logout(client, auth_user):
    # Login
    res = client.post("/api/auth/login", json={
        "email": auth_user["email"],
        "password": auth_user["password"]
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True

    # Profile should now be accessible
    res_prof = client.get("/api/profile")
    assert res_prof.status_code == 200

    # Logout
    res_out = client.post("/api/auth/logout")
    assert res_out.status_code == 200


def test_login_invalid_credentials(client, auth_user):
    res = client.post("/api/auth/login", json={
        "email": auth_user["email"],
        "password": "wrongpassword"
    })
    assert res.status_code == 401

def test_login_and_me(client, test_user):
    login_response = client.post(
        "/api/auth/login",
        json={
            "org_slug": test_user["org_slug"],
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )

    assert login_response.status_code == 200
    assert login_response.json()["user"]["username"] == test_user["username"]

    me_response = client.get("/api/auth/me")
    assert me_response.status_code == 200
    assert me_response.json()["user"]["org_slug"] == test_user["org_slug"]


def test_step_up_marks_session(client, test_user):
    client.post(
        "/api/auth/login",
        json={
            "org_slug": test_user["org_slug"],
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )

    csrf_token = client.cookies.get("trailforge_csrf")

    step_up_response = client.post(
        "/api/auth/step-up",
        json={"password": test_user["password"]},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert step_up_response.status_code == 200
    assert step_up_response.json()["user"]["step_up_valid_until"] is not None


def test_step_up_rejects_without_csrf(client, test_user):
    client.post(
        "/api/auth/login",
        json={
            "org_slug": test_user["org_slug"],
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )

    step_up_response = client.post("/api/auth/step-up", json={"password": test_user["password"]})
    assert step_up_response.status_code == 403
    assert step_up_response.json()["detail"] == "CSRF token missing"


def test_api_token_lifecycle(client, test_user):
    client.post(
        "/api/auth/login",
        json={
            "org_slug": test_user["org_slug"],
            "username": test_user["username"],
            "password": test_user["password"],
        },
    )

    csrf_token = client.cookies.get("trailforge_csrf")

    create_response = client.post(
        "/api/auth/tokens",
        json={"label": "pytest-token"},
        headers={"X-CSRF-Token": csrf_token},
    )
    assert create_response.status_code == 201
    assert create_response.json()["token"]

    list_response = client.get("/api/auth/tokens")
    assert list_response.status_code == 200
    token_id = list_response.json()[0]["id"]

    delete_response = client.delete(
        f"/api/auth/tokens/{token_id}",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert delete_response.status_code == 204

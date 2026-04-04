from __future__ import annotations

from sqlalchemy import select

from app.models.organization import Organization
from app.models.user import User
from app.services.message_center import create_template as create_template_service
from app.services.message_center import send_message
from app.services.governance import create_project as create_project_service

def login(client, creds: dict[str, str]) -> str:
    response = client.post(
        "/api/auth/login",
        json={
            "org_slug": creds["org_slug"],
            "username": creds["username"],
            "password": creds["password"],
        },
    )
    assert response.status_code == 200
    csrf_token = client.cookies.get("trailforge_csrf")
    assert csrf_token
    return csrf_token


def step_up(client, csrf: str, *, password: str) -> None:
    response = client.post("/api/auth/step-up", headers={"X-CSRF-Token": csrf}, json={"password": password})
    assert response.status_code == 200


def create_project(client, csrf: str, *, suffix: str) -> str:
    response = client.post(
        "/api/projects",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": f"pytest-msg-project-{suffix}",
            "code": f"PMSG-{suffix}",
            "description": "message center",
            "status": "active",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_itinerary(client, csrf: str, *, project_id: str, suffix: str) -> str:
    response = client.post(
        f"/api/projects/{project_id}/itineraries",
        headers={"X-CSRF-Token": csrf},
        json={"name": f"pytest-msg-itinerary-{suffix}", "status": "draft"},
    )
    assert response.status_code == 201
    return response.json()["id"]


def create_template(
    client,
    csrf: str,
    *,
    project_id: str,
    name: str,
    category: str,
    channel: str = "in_app",
    body_template: str = "Hello {{traveler_name}}, departure at {{departure_time}}.",
) -> dict:
    response = client.post(
        f"/api/projects/{project_id}/message-center/templates",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": name,
            "category": category,
            "channel": channel,
            "body_template": body_template,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_message_center_template_preview_send_timeline_and_caps(client, test_user):
    csrf = login(client, test_user)
    project_id = create_project(client, csrf, suffix="flow")
    itinerary_id = create_itinerary(client, csrf, project_id=project_id, suffix="flow")

    template_departure = create_template(
        client,
        csrf,
        project_id=project_id,
        name="pytest-msg-departure",
        category="departure",
    )
    assert "traveler_name" in template_departure["variables"]
    assert "departure_time" in template_departure["variables"]

    preview = client.post(
        f"/api/projects/{project_id}/message-center/preview",
        json={
            "template_id": template_departure["id"],
            "itinerary_id": itinerary_id,
            "variables": {"traveler_name": "Ava", "departure_time": "09:30"},
        },
    )
    assert preview.status_code == 200
    assert preview.json()["missing_variables"] == []
    assert "Ava" in preview.json()["rendered_body"]
    assert "09:30" in preview.json()["rendered_body"]

    send_1 = client.post(
        f"/api/projects/{project_id}/message-center/send",
        headers={"X-CSRF-Token": csrf},
        json={
            "template_id": template_departure["id"],
            "recipient_user_id": "traveler-100",
            "itinerary_id": itinerary_id,
            "variables": {"traveler_name": "Ava", "departure_time": "09:30"},
        },
    )
    assert send_1.status_code == 200
    assert send_1.json()["send_status"] == "sent"
    assert send_1.json()["attempts"][0]["connector_key"] == "in_app"
    assert send_1.json()["attempts"][0]["attempt_status"] == "sent"

    same_category_within_hour = client.post(
        f"/api/projects/{project_id}/message-center/send",
        headers={"X-CSRF-Token": csrf},
        json={
            "template_id": template_departure["id"],
            "recipient_user_id": "traveler-100",
            "variables": {"traveler_name": "Ava", "departure_time": "10:00"},
        },
    )
    assert same_category_within_hour.status_code == 422
    assert "Hourly category cap" in same_category_within_hour.json()["detail"]

    template_checkin = create_template(
        client,
        csrf,
        project_id=project_id,
        name="pytest-msg-checkin",
        category="checkin",
    )
    template_safety = create_template(
        client,
        csrf,
        project_id=project_id,
        name="pytest-msg-safety",
        category="safety",
    )
    template_update = create_template(
        client,
        csrf,
        project_id=project_id,
        name="pytest-msg-update",
        category="update",
    )

    update_template = client.patch(
        f"/api/projects/{project_id}/message-center/templates/{template_update['id']}",
        headers={"X-CSRF-Token": csrf},
        json={
            "name": "pytest-msg-update-renamed",
            "category": "update",
            "channel": "in_app",
            "body_template": "Updated {{traveler_name}} at {{departure_time}}",
            "is_active": True,
        },
    )
    assert update_template.status_code == 200
    assert update_template.json()["name"] == "pytest-msg-update-renamed"
    template_update = update_template.json()

    send_2 = client.post(
        f"/api/projects/{project_id}/message-center/send",
        headers={"X-CSRF-Token": csrf},
        json={
            "template_id": template_checkin["id"],
            "recipient_user_id": "traveler-100",
            "variables": {"traveler_name": "Ava", "departure_time": "11:00"},
        },
    )
    assert send_2.status_code == 200
    assert send_2.json()["send_status"] == "sent"

    send_3 = client.post(
        f"/api/projects/{project_id}/message-center/send",
        headers={"X-CSRF-Token": csrf},
        json={
            "template_id": template_safety["id"],
            "recipient_user_id": "traveler-100",
            "variables": {"traveler_name": "Ava", "departure_time": "12:00"},
        },
    )
    assert send_3.status_code == 200
    assert send_3.json()["send_status"] == "sent"

    daily_cap_block = client.post(
        f"/api/projects/{project_id}/message-center/send",
        headers={"X-CSRF-Token": csrf},
        json={
            "template_id": template_update["id"],
            "recipient_user_id": "traveler-100",
            "variables": {"traveler_name": "Ava", "departure_time": "13:00"},
        },
    )
    assert daily_cap_block.status_code == 422
    assert "Daily frequency cap" in daily_cap_block.json()["detail"]

    timeline = client.get(f"/api/projects/{project_id}/message-center/timeline")
    assert timeline.status_code == 200
    rows = timeline.json()
    assert len(rows) == 3
    assert rows[0]["attempts"]
    assert all(row["recipient_user_id"] == "traveler-100" for row in rows)

    template_sms = create_template(
        client,
        csrf,
        project_id=project_id,
        name="pytest-msg-sms-offline",
        category="ops_sms",
        channel="sms",
        body_template="SMS ping for {{traveler_name}} at {{departure_time}}",
    )
    send_sms = client.post(
        f"/api/projects/{project_id}/message-center/send",
        headers={"X-CSRF-Token": csrf},
        json={
            "template_id": template_sms["id"],
            "recipient_user_id": "traveler-sms-1",
            "variables": {"traveler_name": "Ava", "departure_time": "14:00"},
        },
    )
    assert send_sms.status_code == 200
    assert send_sms.json()["send_status"] == "failed"
    assert send_sms.json()["attempts"][0]["connector_key"] == "sms"


def test_message_center_read_only_project_member_can_view_but_not_mutate(client, test_user, planner_user):
    admin_csrf = login(client, test_user)
    step_up(client, admin_csrf, password=test_user["password"])
    project_id = create_project(client, admin_csrf, suffix="readonly")
    template = create_template(
        client,
        admin_csrf,
        project_id=project_id,
        name="pytest-msg-readonly-template",
        category="ops",
    )

    users = client.get("/api/admin/users")
    assert users.status_code == 200
    planner_id = next(user["id"] for user in users.json() if user["username"] == planner_user["username"])

    add_member = client.post(
        f"/api/projects/{project_id}/members",
        headers={"X-CSRF-Token": admin_csrf},
        json={"user_id": planner_id, "role_in_project": "planner", "can_edit": False},
    )
    assert add_member.status_code == 201

    planner_csrf = login(client, planner_user)

    list_templates = client.get(f"/api/projects/{project_id}/message-center/templates")
    assert list_templates.status_code == 200
    assert len(list_templates.json()) == 1

    forbidden_create = client.post(
        f"/api/projects/{project_id}/message-center/templates",
        headers={"X-CSRF-Token": planner_csrf},
        json={
            "name": "pytest-msg-readonly-denied",
            "category": "ops",
            "channel": "in_app",
            "body_template": "Hello {{traveler_name}}",
            "is_active": True,
        },
    )
    assert forbidden_create.status_code == 403

    forbidden_send = client.post(
        f"/api/projects/{project_id}/message-center/send",
        headers={"X-CSRF-Token": planner_csrf},
        json={
            "template_id": template["id"],
            "recipient_user_id": "traveler-200",
            "variables": {"traveler_name": "Read Only", "departure_time": "08:00"},
        },
    )
    assert forbidden_send.status_code == 403


def test_message_send_serializes_frequency_check_with_org_lock(db, test_user, monkeypatch):
    user = db.execute(select(User).where(User.id == test_user["user_id"])).scalars().one()
    org = db.execute(select(Organization).where(Organization.id == user.org_id)).scalars().one()
    project = create_project_service(
        db,
        org_id=org.id,
        name="pytest-msg-lock-project",
        code="MSGLOCK",
        description="lock",
        status="active",
    )
    template = create_template_service(
        db,
        org_id=org.id,
        project_id=project.id,
        user=user,
        name="pytest-msg-lock-template",
        category="lockcheck",
        channel="in_app",
        body_template="Hello {{traveler_name}} at {{departure_time}}",
        is_active=True,
    )

    original_execute = db.execute
    saw_for_update = False

    def tracked_execute(statement, *args, **kwargs):
        nonlocal saw_for_update
        if getattr(statement, "_for_update_arg", None) is not None and "organizations" in str(statement):
            saw_for_update = True
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", tracked_execute)

    dispatch = send_message(
        db,
        org_id=org.id,
        project_id=project.id,
        template_id=template.id,
        recipient_user_id="traveler-lock-1",
        itinerary_id=None,
        variables={"traveler_name": "Ava", "departure_time": "08:30"},
        user=user,
    )

    assert dispatch is not None
    assert saw_for_update is True

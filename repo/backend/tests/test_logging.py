from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.logging import RedactionFilter
from app.models.operations import AuditEvent
from app.models.organization import Organization
from app.services.audit import _redact, record_audit_event


def test_redaction_filter_masks_sensitive_tokens_in_log_messages():
    record = logging.LogRecord(
        name="trailforge.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="password=hunter2 token=abc123 authorization=Bearer123 plain=value",
        args=(),
        exc_info=None,
    )

    assert RedactionFilter().filter(record) is True
    assert "password=[REDACTED]" in record.msg
    assert "token=[REDACTED]" in record.msg
    assert "authorization=[REDACTED]" in record.msg
    assert "plain=value" in record.msg


def test_audit_redact_masks_nested_sensitive_metadata():
    payload = {
        "password": "topsecret",
        "nested": {"token": "abc123", "safe": "ok"},
        "items": [{"authorization": "Bearer xyz"}, {"csrf_token": "csrf-value", "note": "visible"}],
    }

    redacted = _redact(payload)

    assert redacted["password"] == "[REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "ok"
    assert redacted["items"][0]["authorization"] == "[REDACTED]"
    assert redacted["items"][1]["csrf_token"] == "[REDACTED]"
    assert redacted["items"][1]["note"] == "visible"


def test_record_audit_event_persists_redacted_metadata(db, test_user):
    org = db.execute(select(Organization).where(Organization.slug == test_user["org_slug"])).scalars().one()

    event = record_audit_event(
        db,
        org_id=org.id,
        actor_user_id=test_user["user_id"],
        action_type="pytest.audit_redaction",
        resource_type="test_resource",
        resource_id="resource-1",
        request_method="POST",
        request_path="/pytest/audit-redaction",
        status_code=200,
        metadata_json={
            "token": "secret-token",
            "safe": "visible",
            "nested": {"password": "hunter2"},
        },
    )

    stored = db.execute(select(AuditEvent).where(AuditEvent.id == event.id)).scalars().one()
    assert stored.metadata_json == {
        "token": "[REDACTED]",
        "safe": "visible",
        "nested": {"password": "[REDACTED]"},
    }

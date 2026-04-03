from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4


@dataclass(slots=True)
class MessageDeliveryRequest:
    message_dispatch_id: str
    channel: str
    recipient_user_id: str
    rendered_body: str
    variables: dict[str, str]


@dataclass(slots=True)
class MessageDeliveryResult:
    connector_key: str
    status: str
    detail: str
    provider_message_id: str | None = None
    response_payload: dict | None = None


class MessageConnector(Protocol):
    connector_key: str
    channel: str

    def deliver(self, request: MessageDeliveryRequest) -> MessageDeliveryResult:
        ...


class InAppMessageConnector:
    connector_key = "in_app"
    channel = "in_app"

    def deliver(self, request: MessageDeliveryRequest) -> MessageDeliveryResult:
        return MessageDeliveryResult(
            connector_key=self.connector_key,
            status="sent",
            detail=f"Stored in-app message for recipient {request.recipient_user_id}",
            provider_message_id=str(uuid4()),
            response_payload={"delivery_surface": "workspace_message_center"},
        )


class OfflineUnavailableConnector:
    def __init__(self, *, connector_key: str, channel: str) -> None:
        self.connector_key = connector_key
        self.channel = channel

    def deliver(self, request: MessageDeliveryRequest) -> MessageDeliveryResult:
        return MessageDeliveryResult(
            connector_key=self.connector_key,
            status="failed",
            detail=(
                f"Connector '{self.connector_key}' for channel '{self.channel}' is not configured for offline runtime"
            ),
            provider_message_id=None,
            response_payload={"offline_mode": True},
        )


def build_default_connector_registry() -> dict[str, MessageConnector]:
    return {
        "in_app": InAppMessageConnector(),
        "sms": OfflineUnavailableConnector(connector_key="sms", channel="sms"),
        "email": OfflineUnavailableConnector(connector_key="email", channel="email"),
        "push": OfflineUnavailableConnector(connector_key="push", channel="push"),
    }

from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from src.domain.entities import OutboxEvent, OutboxStatus
from src.infra.message.sns_publisher import SnsEventPublisher


def test_publish_call_sns_client_with_topic_and_payload():
    client = MagicMock()
    publisher = SnsEventPublisher(
        topic_arn="arn:aws:sns:sa-east-1:000000000000:order-created", client=client
    )
    event = OutboxEvent(
        id=uuid4(),
        aggregate_type="Order",
        aggregate_id=uuid4(),
        event_type="OrderCreated",
        payload={"numero_ordem": "OS-1"},
        status=OutboxStatus.PENDING,
        attempts=0,
        create_at=datetime.now(timezone.utc),
    )

    publisher.publish(event)

    client.publish.assert_called_once()
    _, kwargs = client.publish.call_args
    assert kwargs["TopicArn"] == "arn:aws:sns:sa-east-1:000000000000:order-created"
    assert "OS-1" in kwargs["Message"]
    assert kwargs["MessageAttributes"]["event_type"]["StringValue"] == "OrderCreated"

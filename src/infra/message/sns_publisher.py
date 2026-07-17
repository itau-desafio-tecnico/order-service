import json

import boto3

from src.domain.entities import OutboxEvent
from src.domain.ports import EventPublisher


class SnsEventPublisher(EventPublisher):

    def __init__(self, topic_arn: str, region_name: str | None = None, client=None) -> None:
        self._topic_arn = topic_arn
        self._client = client or boto3.client("sns", region_name=region_name)

    def publish(self, event: OutboxEvent) -> None:
        self._client.publish(
            TopicArn=self._topic_arn,
            Message=json.dumps(event.payload),
            MessageAttributes={
                "event_type": {"DataType": "String", "StringValue": event.event_type},
                "event_id": {"DataType": "String", "StringValue": str(event.id)},
            },
        )

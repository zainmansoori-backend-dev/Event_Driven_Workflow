# redis_service.py
import redis
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import os

load_dotenv(".env")

class RedisStreamService:
    """Service for publishing and consuming events via Redis Streams"""
    
    def __init__(self):
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD", None)
        
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )
        self.stream_name = os.getenv("REDIS_STREAM_NAME", "workflow_events")
    
    def publish_event(self, event_type: str, payload: Dict[str, Any], org_id: Optional[str] = None) -> str:
        """
        Publish an event to Redis Stream
        
        Args:
            event_type: Type of event (e.g., "form_submitted")
            payload: Event payload data
            org_id: Optional organization ID
            
        Returns:
            Message ID from Redis Stream
        """
        message = {
            "event_type": event_type,
            "payload": json.dumps(payload),
            "org_id": org_id or "0"
        }
        
        message_id = self.redis_client.xadd(
            self.stream_name,
            message,
            maxlen=10000  # Keep last 10000 messages
        )
        return message_id
    
    def read_events(self, consumer_group: str, consumer_name: str, count: int = 10, block: int = 1000):
        """
        Read events from Redis Stream using consumer group
        
        Args:
            consumer_group: Consumer group name
            consumer_name: Consumer name within the group
            count: Maximum number of messages to read
            block: Block time in milliseconds (0 = no blocking)
            
        Returns:
            List of messages
        """
        try:
            # Ensure consumer group exists
            self.redis_client.xgroup_create(
                name=self.stream_name,
                groupname=consumer_group,
                id="0",
                mkstream=True
            )
        except redis.exceptions.ResponseError as e:
            # Group already exists, ignore
            if "BUSYGROUP" not in str(e):
                raise
        
        # Read pending messages first
        pending = self.redis_client.xreadgroup(
            groupname=consumer_group,
            consumername=consumer_name,
            streams={self.stream_name: "0"},
            count=count,
            block=block
        )
        
        if pending:
            return pending
        
        # Read new messages
        messages = self.redis_client.xreadgroup(
            groupname=consumer_group,
            consumername=consumer_name,
            streams={self.stream_name: ">"},
            count=count,
            block=block
        )
        
        return messages
    
    def acknowledge_event(self, consumer_group: str, message_id: str):
        """
        Acknowledge that a message has been processed
        
        Args:
            consumer_group: Consumer group name
            message_id: Message ID to acknowledge
        """
        self.redis_client.xack(self.stream_name, consumer_group, message_id)
    
    def get_pending_count(self, consumer_group: str, consumer_name: str) -> int:
        """Get count of pending messages for a consumer"""
        pending_info = self.redis_client.xpending_range(
            name=self.stream_name,
            groupname=consumer_group,
            min="-",
            max="+",
            count=100
        )
        return len([p for p in pending_info if p.get("consumer") == consumer_name])


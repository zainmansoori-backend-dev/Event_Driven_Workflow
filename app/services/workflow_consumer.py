# workflow_consumer.py
import json
import logging
import time
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.db_config.database import SessionLocal
from app.services.redis_service import RedisStreamService
from app.services.workflow_engine import WorkflowEngine

logger = logging.getLogger(__name__)

class WorkflowConsumer:
    """Consumer that processes events from Redis Streams and executes workflows"""
    
    def __init__(self, consumer_group: str = "workflow_workers", consumer_name: str = "worker_1"):
        self.redis_service = RedisStreamService()
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name
        self.running = False
    
    def process_event(self, stream_name: str, message_id: str, message_data: Dict[str, str]):
        """
        Process a single event message
        
        Args:
            stream_name: Name of the Redis stream
            message_id: Message ID
            message_data: Message data dictionary
        """
        try:
            # Parse event data
            event_type = message_data.get("event_type")
            payload_str = message_data.get("payload")
            org_id = message_data.get("org_id", "0")
            
            if not event_type or not payload_str:
                logger.warning(f"Invalid message format: {message_data}")
                return
            
            # Parse payload
            try:
                payload = json.loads(payload_str)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse payload JSON: {payload_str}")
                return
            
            logger.info(f"Processing event: {event_type}, payload: {payload}")
            
            # Get database session
            db = SessionLocal()
            try:
                # Create workflow engine
                engine = WorkflowEngine(db)
                
                # Find matching workflows
                matching_workflows = engine.find_matching_workflows(event_type, payload)
                
                if not matching_workflows:
                    logger.info(f"No matching workflows found for event: {event_type}")
                    return
                
                # Execute each matching workflow
                for workflow in matching_workflows:
                    try:
                        logger.info(f"Executing workflow: {workflow.name} (ID: {workflow.id})")
                        instance = engine.execute_workflow(workflow, payload)
                        
                        if instance:
                            logger.info(f"Workflow instance created: {instance.id}, status: {instance.status}")
                        else:
                            logger.warning(f"Workflow execution returned no instance")
                            
                    except Exception as e:
                        logger.error(f"Error executing workflow {workflow.id}: {str(e)}", exc_info=True)
                        continue
                
                # Acknowledge message after successful processing
                self.redis_service.acknowledge_event(self.consumer_group, message_id)
                logger.info(f"Event {message_id} processed and acknowledged")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error processing event {message_id}: {str(e)}", exc_info=True)
            # Don't acknowledge on error - message will be retried
    
    def start(self, poll_interval: int = 1, batch_size: int = 10):
        """
        Start consuming events from Redis Streams
        
        Args:
            poll_interval: Seconds to wait between polls
            batch_size: Number of messages to read per poll
        """
        self.running = True
        logger.info(f"Starting workflow consumer: {self.consumer_name} in group {self.consumer_group}")
        
        while self.running:
            try:
                # Read events from stream
                messages = self.redis_service.read_events(
                    consumer_group=self.consumer_group,
                    consumer_name=self.consumer_name,
                    count=batch_size,
                    block=1000  # Block for 1 second
                )
                
                if messages:
                    # Process each stream's messages
                    for stream_messages in messages:
                        stream_name, message_list = stream_messages
                        
                        for message_id, message_data in message_list:
                            self.process_event(stream_name, message_id, message_data)
                else:
                    # No messages, sleep briefly
                    time.sleep(poll_interval)
                    
            except KeyboardInterrupt:
                logger.info("Received interrupt signal, stopping consumer...")
                self.stop()
                break
            except Exception as e:
                logger.error(f"Error in consumer loop: {str(e)}", exc_info=True)
                time.sleep(poll_interval)
    
    def stop(self):
        """Stop the consumer"""
        self.running = False
        logger.info("Workflow consumer stopped")


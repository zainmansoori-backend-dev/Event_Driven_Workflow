# consumer_worker.py
"""
Standalone worker script to run the workflow consumer
Run this as a separate process: python -m app.workers.consumer_worker
"""
import logging
import sys
from app.services.workflow_consumer import WorkflowConsumer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

if __name__ == "__main__":
    # Create and start consumer
    consumer = WorkflowConsumer(
        consumer_group="workflow_workers",
        consumer_name="worker_1"
    )
    
    try:
        consumer.start(poll_interval=1, batch_size=10)
    except KeyboardInterrupt:
        consumer.stop()


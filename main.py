# main.py
import json
import datetime
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import select
from app.db_config.database import get_db
from app.models.models import FormSubmission, Outbox, WorkflowDefinition
from app.schemas.schemas import SubmitPayload, WorkflowCreate
from app.services.redis_service import RedisStreamService
from uuid import uuid4
from sqlalchemy.orm import Session

app = FastAPI(title="Event-driven workflows demo")

# Initialize Redis Stream service
redis_service = RedisStreamService()

@app.post("/submit")
async def submit(payload: SubmitPayload, db: Session = Depends(get_db)):
    """
    Submit a form. This will:
    1. Save the form submission to database
    2. Publish an event to Redis Streams
    3. Workflow consumer will pick up the event and execute matching workflows
    """
    # validate minimal
    if not payload.template_id:
        raise HTTPException(400, "template_id required")
    
    submission_id = str(uuid4())
    submission = FormSubmission(
        id=submission_id,
        template_id=payload.template_id,
        data=payload.data,
        org_id=payload.org_id
    )
    
    # Save to database
    db.add(submission)
    db.commit()
    db.refresh(submission)
    
    # Prepare event payload
    event_payload = {
        "submission_id": submission_id,
        "template_id": payload.template_id,
        "data": payload.data,
        "org_id": payload.org_id
    }
    
    # Publish event to Redis Streams
    try:
        message_id = redis_service.publish_event(
            event_type="form_submitted",
            payload=event_payload,
            org_id=payload.org_id
        )
        
        # Also save to outbox for audit trail (optional)
        outbox = Outbox(
            id=str(uuid4()),
            event_type="form_submitted",
            payload=event_payload,
            org_id=payload.org_id,
            published_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db.add(outbox)
        db.commit()
        
        return {
            "submission_id": submission_id,
            "message_id": message_id,
            "status": "submitted"
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to publish event: {str(e)}")

@app.post("/workflows")
async def create_workflow(w: WorkflowCreate, db: Session = Depends(get_db)):
    """Create a new workflow definition"""
    wf = WorkflowDefinition(
        id=str(uuid4()),
        name=w.name,
        definition=w.definition
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return {"workflow_id": wf.id, "name": wf.name}

@app.get("/workflows")
async def list_workflows(db: Session = Depends(get_db)):
    """List all active workflow definitions"""
    q = db.execute(select(WorkflowDefinition).where(WorkflowDefinition.is_active == True))
    rows = q.scalars().all()
    return [{"id": r.id, "name": r.name, "definition": r.definition} for r in rows]

@app.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    """Get a specific workflow definition"""
    workflow = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
    if not workflow:
        raise HTTPException(404, "Workflow not found")
    return {"id": workflow.id, "name": workflow.name, "definition": workflow.definition}
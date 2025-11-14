# models.py
import datetime
import uuid
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Text
from app.db_config.database import Base


class FormSubmission(Base):
    __tablename__ = "form_submissions"
    id = Column(String, primary_key=True, index=True)
    template_id = Column(String, nullable=False)
    data = Column(JSON, nullable=False)
    org_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class WorkflowDefinition(Base):
    __tablename__ = "workflow_definitions"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    # JSON like: {"trigger": {"type": "form_submitted", "conditions": {"path":"template_id","op":"==","value":"form_submitted"}} , "steps":[...]}
    definition = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    id = Column(String, primary_key=True, index=True)
    workflow_id = Column(String, nullable=False)
    current_step = Column(String, nullable=True)
    status = Column(String, default="pending")
    context = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Outbox(Base):
    __tablename__ = "outbox"
    id = Column(String, primary_key=True, index=True)
    event_type = Column(String, nullable=False)
    payload = Column(JSON, nullable=False)
    org_id = Column(String, nullable=True)
    published_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

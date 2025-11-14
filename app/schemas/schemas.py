# schemas.py
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

class SubmitPayload(BaseModel):
    template_id: str
    data: Dict[str, Any]
    org_id: Optional[str] = "0"

class WorkflowCreate(BaseModel):
    name: str
    definition: Dict[str, Any]  # keep simple; validate before production

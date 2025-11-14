# workflow_engine.py
import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.models import WorkflowDefinition, WorkflowInstance
from app.services.email_service import EmailService
from uuid import uuid4

logger = logging.getLogger(__name__)

class WorkflowEngine:
    """Engine for executing workflow definitions"""
    
    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()
    
    def evaluate_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """
        Evaluate a condition against context
        
        Supports:
        - Simple: {"path": "template_id", "op": "==", "value": "form_submitted"}
        - Complex: {"all": [...]} or {"any": [...]}
        
        Args:
            condition: Condition definition
            context: Context data to evaluate against
            
        Returns:
            True if condition is met, False otherwise
        """
        if not condition:
            return True
        
        # Handle "all" (AND) conditions
        if "all" in condition:
            return all(self.evaluate_condition(c, context) for c in condition["all"])
        
        # Handle "any" (OR) conditions
        if "any" in condition:
            return any(self.evaluate_condition(c, context) for c in condition["any"])
        
        # Handle simple condition
        if "path" in condition and "op" in condition:
            path = condition["path"]
            op = condition["op"]
            value = condition.get("value")
            
            # Navigate path (supports dot notation like "form.data.email")
            context_value = self._get_path_value(context, path)
            
            if op == "==":
                return context_value == value
            elif op == "!=":
                return context_value != value
            elif op == "in":
                return context_value in value if isinstance(value, list) else False
            elif op == ">":
                return context_value > value
            elif op == ">=":
                return context_value >= value
            elif op == "<":
                return context_value < value
            elif op == "<=":
                return context_value <= value
            elif op == "contains":
                return value in str(context_value) if context_value else False
        
        return False
    
    def _get_path_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation"""
        keys = path.split(".")
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    
    def find_matching_workflows(self, event_type: str, event_payload: Dict[str, Any]) -> List[WorkflowDefinition]:
        """
        Find workflow definitions that match the event
        
        Args:
            event_type: Type of event (e.g., "form_submitted")
            event_payload: Event payload data
            
        Returns:
            List of matching WorkflowDefinition objects
        """
        # Get all active workflow definitions
        query = select(WorkflowDefinition).where(WorkflowDefinition.is_active == True)
        result = self.db.execute(query)
        all_workflows = result.scalars().all()
        
        matching_workflows = []
        
        for workflow in all_workflows:
            definition = workflow.definition
            trigger = definition.get("trigger", {})
            
            # Check if event type matches
            if trigger.get("type") != event_type:
                continue
            
            # Check conditions if any
            conditions = trigger.get("conditions")
            if conditions:
                # Build context from event payload
                context = {
                    "event_type": event_type,
                    **event_payload
                }
                
                if not self.evaluate_condition(conditions, context):
                    continue
            
            matching_workflows.append(workflow)
        
        return matching_workflows
    
    def execute_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a workflow action
        
        Args:
            action: Action definition
            context: Workflow context
            
        Returns:
            Result of action execution
        """
        action_type = action.get("type")
        
        if action_type == "send_notification" or action_type == "send_email":
            return self._execute_send_email(action, context)
        elif action_type == "create_ticket":
            return self._execute_create_ticket(action, context)
        elif action_type == "update_ticket":
            return self._execute_update_ticket(action, context)
        elif action_type == "create_task":
            return self._execute_create_task(action, context)
        elif action_type == "update_task":
            return self._execute_update_task(action, context)
        elif action_type == "webhook":
            return self._execute_webhook(action, context)
        else:
            logger.warning(f"Unknown action type: {action_type}")
            return {"status": "skipped", "reason": f"Unknown action type: {action_type}"}
    
    def _execute_send_email(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute send email action"""
        try:
            # Get email configuration from action
            config = action.get("config", {})
            
            # Get recipient - can be from config or context
            to_email = config.get("to") or self._get_path_value(context, config.get("to_path", "form.data.email"))
            
            if not to_email:
                return {"status": "failed", "reason": "No recipient email found"}
            
            # Get subject and body
            subject = config.get("subject", "Notification")
            body = config.get("body", "You have a new notification.")
            
            # Substitute template variables from context
            template_data = {**context, **config.get("template_data", {})}
            try:
                subject = subject.format(**template_data)
                body = body.format(**template_data)
            except KeyError:
                pass  # Use as-is if formatting fails
            
            # Send email
            success = self.email_service.send_email(to_email, subject, body)
            
            if success:
                return {"status": "success", "action": "send_email", "to": to_email}
            else:
                return {"status": "failed", "action": "send_email", "reason": "Email sending failed"}
                
        except Exception as e:
            logger.error(f"Error executing send_email action: {str(e)}")
            return {"status": "error", "action": "send_email", "error": str(e)}
    
    def _execute_create_ticket(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create ticket action (placeholder - implement based on your ticket model)"""
        logger.info(f"Create ticket action: {action}, context: {context}")
        return {"status": "success", "action": "create_ticket", "note": "Not implemented yet"}
    
    def _execute_update_ticket(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute update ticket action (placeholder)"""
        logger.info(f"Update ticket action: {action}, context: {context}")
        return {"status": "success", "action": "update_ticket", "note": "Not implemented yet"}
    
    def _execute_create_task(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute create task action (placeholder)"""
        logger.info(f"Create task action: {action}, context: {context}")
        return {"status": "success", "action": "create_task", "note": "Not implemented yet"}
    
    def _execute_update_task(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute update task action (placeholder)"""
        logger.info(f"Update task action: {action}, context: {context}")
        return {"status": "success", "action": "update_task", "note": "Not implemented yet"}
    
    def _execute_webhook(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute webhook action (placeholder)"""
        logger.info(f"Webhook action: {action}, context: {context}")
        return {"status": "success", "action": "webhook", "note": "Not implemented yet"}
    
    def execute_workflow(self, workflow: WorkflowDefinition, event_payload: Dict[str, Any]) -> WorkflowInstance:
        """
        Execute a workflow definition
        
        Args:
            workflow: WorkflowDefinition to execute
            event_payload: Event payload data
            
        Returns:
            Created WorkflowInstance
        """
        definition = workflow.definition
        steps = definition.get("steps", [])
        initial_step_id = definition.get("initial_step_id")
        
        if not steps:
            logger.warning(f"Workflow {workflow.id} has no steps")
            return None
        
        # Create workflow instance
        instance = WorkflowInstance(
            id=str(uuid4()),
            workflow_id=str(workflow.id),
            current_step=initial_step_id,
            status="active",
            context=event_payload
        )
        
        self.db.add(instance)
        self.db.commit()
        
        # Execute initial step
        self._execute_step(instance, steps, initial_step_id)
        
        return instance
    
    def _execute_step(self, instance: WorkflowInstance, steps: List[Dict[str, Any]], step_id: str):
        """Execute a workflow step"""
        # Find step definition
        step_def = next((s for s in steps if s.get("id") == step_id), None)
        
        if not step_def:
            logger.error(f"Step {step_id} not found in workflow")
            instance.status = "error"
            self.db.commit()
            return
        
        # Execute all actions in the step
        actions = step_def.get("actions", [])
        results = []
        
        for action in actions:
            result = self.execute_action(action, instance.context)
            results.append(result)
        
        # Update instance
        instance.current_step = step_id
        self.db.commit()
        
        # Check if step is auto_action and should auto-advance
        step_type = step_def.get("type", "human_task")
        
        if step_type == "auto_action":
            # Find next step based on transitions
            transitions = step_def.get("transitions", [])
            next_step_id = None
            
            for transition in transitions:
                condition = transition.get("condition")
                if not condition or self.evaluate_condition(condition, instance.context):
                    next_step_id = transition.get("to_step_id")
                    break
            
            if next_step_id:
                # Auto-advance to next step
                self._execute_step(instance, steps, next_step_id)
            else:
                # No more steps, workflow is complete
                instance.status = "completed"
                self.db.commit()
        # else: human_task - wait for manual completion
        
        return results


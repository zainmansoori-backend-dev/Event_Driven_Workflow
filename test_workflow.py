"""
Test script to create a workflow and submit a form
Run this after starting the FastAPI server and workflow consumer
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Create a workflow definition
workflow_def = {
    "name": "Send Email on Form Submission",
    "definition": {
        "trigger": {
            "type": "form_submitted",
            "conditions": {
                "path": "template_id",
                "op": "==",
                "value": "form_submitted"
            }
        },
        "initial_step_id": "step1",
        "steps": [
            {
                "id": "step1",
                "name": "Send Email Notification",
                "type": "auto_action",
                "actions": [
                    {
                        "type": "send_email",
                        "config": {
                            "to_path": "data.email",
                            "subject": "Form Submission Confirmation - {template_id}",
                            "body": "Hello,\n\nYour form submission has been received successfully.\n\nSubmission ID: {submission_id}\nTemplate: {template_id}\n\nThank you!"
                        }
                    }
                ],
                "transitions": []
            }
        ]
    }
}

print("Creating workflow...")
response = requests.post(f"{BASE_URL}/workflows", json=workflow_def)
if response.status_code == 200:
    workflow = response.json()
    print(f"✓ Workflow created: {workflow['workflow_id']}")
    print(f"  Name: {workflow['name']}")
else:
    print(f"✗ Failed to create workflow: {response.status_code}")
    print(response.text)
    exit(1)

# 2. List workflows
print("\nListing workflows...")
response = requests.get(f"{BASE_URL}/workflows")
if response.status_code == 200:
    workflows = response.json()
    print(f"✓ Found {len(workflows)} active workflow(s)")
    for wf in workflows:
        print(f"  - {wf['name']} (ID: {wf['id']})")
else:
    print(f"✗ Failed to list workflows: {response.status_code}")

# 3. Submit a form
print("\nSubmitting form...")
form_data = {
    "template_id": "form_submitted",
    "data": {
        "email": "test@example.com",  # Change this to your email
        "name": "Test User",
        "message": "This is a test form submission"
    },
    "org_id": "org_123"
}

response = requests.post(f"{BASE_URL}/submit", json=form_data)
if response.status_code == 200:
    result = response.json()
    print(f"✓ Form submitted successfully")
    print(f"  Submission ID: {result['submission_id']}")
    print(f"  Message ID: {result['message_id']}")
    print(f"  Status: {result['status']}")
    print("\n✓ Event published to Redis Streams")
    print("  The workflow consumer should pick it up and send an email!")
else:
    print(f"✗ Failed to submit form: {response.status_code}")
    print(response.text)

print("\nDone! Check your email inbox.")


# Event-Driven Workflow System

An event-driven workflow system using Redis Streams for processing form submissions and executing workflows (e.g., sending emails).

## Architecture

1. **Form Submission** → FastAPI endpoint receives form data
2. **Event Publishing** → Event published to Redis Streams
3. **Workflow Consumer** → Background worker consumes events from Redis Streams
4. **Workflow Engine** → Matches events to workflow definitions and executes actions
5. **Actions** → Executes actions like sending emails, creating tickets, etc.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_STREAM_NAME=workflow_events

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_USE_TLS=true
FROM_EMAIL=your-email@gmail.com
```

### 3. Database Setup

Make sure your database tables are created. You can use Alembic or create them manually based on the models in `app/models/models.py`.

### 4. Start the Application

**Terminal 1 - Start FastAPI server:**
```bash
uvicorn main:app --reload
```

**Terminal 2 - Start workflow consumer:**
```bash
python -m app.workers.consumer_worker
```

## Usage

### 1. Create a Workflow Definition

POST `/workflows`

Example payload:
```json
{
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
              "body": "Hello,\n\nYour form submission has been received.\n\nSubmission ID: {submission_id}\nTemplate: {template_id}\n\nThank you!"
            }
          }
        ],
        "transitions": []
      }
    ]
  }
}
```

### 2. Submit a Form

POST `/submit`

Example payload:
```json
{
  "template_id": "form_submitted",
  "data": {
    "email": "user@example.com",
    "name": "John Doe",
    "message": "Hello world"
  },
  "org_id": "org_123"
}
```

When this form is submitted:
1. It's saved to the database
2. An event is published to Redis Streams
3. The workflow consumer picks up the event
4. If a workflow matches (template_id == "form_submitted"), it executes
5. The email action sends an email to the address in `data.email`

## Workflow Definition Structure

### Trigger
```json
{
  "type": "form_submitted",
  "conditions": {
    "path": "template_id",
    "op": "==",
    "value": "form_submitted"
  }
}
```

Supported operators: `==`, `!=`, `in`, `>`, `>=`, `<`, `<=`, `contains`

### Steps

**Auto Action Step** (executes immediately):
```json
{
  "id": "step1",
  "name": "Step Name",
  "type": "auto_action",
  "actions": [...],
  "transitions": [...]
}
```

**Human Task Step** (waits for manual completion):
```json
{
  "id": "step1",
  "name": "Step Name",
  "type": "human_task",
  "actions": [...],
  "transitions": [...]
}
```

### Actions

**Send Email:**
```json
{
  "type": "send_email",
  "config": {
    "to": "email@example.com",  // Direct email
    "to_path": "data.email",     // Or path to email in context
    "subject": "Subject {variable}",
    "body": "Body with {variable} substitution"
  }
}
```

**Other action types** (placeholders for now):
- `create_ticket`
- `update_ticket`
- `create_task`
- `update_task`
- `webhook`

## API Endpoints

- `POST /submit` - Submit a form
- `POST /workflows` - Create a workflow definition
- `GET /workflows` - List all active workflows
- `GET /workflows/{workflow_id}` - Get a specific workflow

## Notes

- The workflow consumer runs as a separate process and continuously polls Redis Streams
- Events are acknowledged after successful processing
- Failed events remain in the stream for retry
- Multiple consumers can run in parallel for scalability


# dbbasic-objects-queue

**Message queue triggers for dbbasic Object Primitives (Task Queues)**

Part of the [dbbasic](https://dbbasic.com) ecosystem.

## What is it?

Message queue layer for Object Primitives - provides priority task queues with visibility timeouts, retries, and dead letter queues.

## Installation

```bash
pip install dbbasic-objects-queue
```

This will also install:
- `dbbasic-objects-core` (runtime)

## Quick Start

### 1. Create Queue Object

```python
# examples/triggers/queue.py
# (Use the included queue.py or create your own)
```

### 2. Use Queue via API

```bash
# Enqueue message
curl -X POST http://localhost:8000/objects/triggers_queue -d '{
  "queue_name": "email_queue",
  "message": {"to": "user@example.com", "subject": "Welcome"},
  "priority": "high"
}'

# Dequeue message (get next message)
curl "http://localhost:8000/objects/triggers_queue?queue_name=email_queue"

# Acknowledge message (mark as completed)
curl -X DELETE "http://localhost:8000/objects/triggers_queue?message_id=abc123"

# Requeue message (on failure)
curl -X PUT "http://localhost:8000/objects/triggers_queue?message_id=abc123"

# Get queue status
curl "http://localhost:8000/objects/triggers_queue?queue_name=email_queue&status=true"
```

## Features

### Priority Levels

```python
# 4 priority levels (higher = processed first)
"critical"    # Highest priority
"high"        # High priority
"normal"      # Default priority
"low"         # Lowest priority
```

### Message Lifecycle

```
1. PENDING    → Message enqueued, waiting to be processed
2. PROCESSING → Message dequeued, being processed (invisible to other workers)
3. COMPLETED  → Message acknowledged (processing succeeded)
4. FAILED     → Message failed after max attempts (moved to DLQ)
5. EXPIRED    → Message TTL expired
```

### Priority Ordering

Messages are dequeued in this order:
1. **Priority** (critical → high → normal → low)
2. **FIFO** within same priority (oldest first)

### Visibility Timeout

When a message is dequeued:
- Status changes to `processing`
- Message becomes invisible for `visibility_timeout` seconds
- If not acknowledged, message becomes visible again
- Allows automatic retry if worker crashes

Default: 300 seconds (5 minutes)

### Retry Logic

If message processing fails:
- Use PUT to requeue message
- Increments attempt counter
- After `max_attempts` (default 3), message moves to dead letter queue
- Failed messages have `status: "failed"`

### Message TTL

Messages expire after TTL (Time To Live):
- Default: 86400 seconds (24 hours)
- Expired messages have `status: "expired"`
- Prevents stale messages from being processed

## API Reference

### POST /objects/triggers_queue

Enqueue message.

**Request:**
```json
{
  "queue_name": "email_queue",
  "message": {"to": "user@example.com", "body": "Hello"},
  "priority": "high",
  "ttl": 3600
}
```

**Parameters:**
- `queue_name` (required) - Queue name
- `message` (required) - Message payload (dict)
- `priority` (optional) - Priority level (default: "normal")
- `ttl` (optional) - Time to live in seconds (default: 86400)

**Response:**
```json
{
  "status": "ok",
  "message_id": "abc123def456",
  "queue_name": "email_queue",
  "message": "Message enqueued"
}
```

### GET /objects/triggers_queue

Dequeue message or get queue status.

**Query params:**
- `queue_name` (required) - Queue name
- `visibility_timeout` (optional) - Visibility timeout in seconds (default: 300)
- `status` (optional) - If "true", returns queue status instead of dequeuing

**Response (Dequeue):**
```json
{
  "status": "ok",
  "message": {
    "id": "abc123",
    "queue_name": "email_queue",
    "message": {"to": "user@example.com"},
    "priority": "high",
    "status": "processing",
    "attempts": 0
  }
}
```

**Response (Empty Queue):**
```json
{
  "status": "ok",
  "message": "No messages available",
  "queue_name": "email_queue"
}
```

**Response (Status):**
```json
{
  "status": "ok",
  "queue_name": "email_queue",
  "total": 10,
  "pending": 5,
  "processing": 3,
  "completed": 2,
  "failed": 0,
  "expired": 0
}
```

### DELETE /objects/triggers_queue

Acknowledge message (mark as completed).

**Query params:**
- `message_id` (required) - Message ID

**Response:**
```json
{
  "status": "ok",
  "message": "Message acknowledged: abc123"
}
```

### PUT /objects/triggers_queue

Requeue message (on failure).

**Query params:**
- `message_id` (required) - Message ID
- `delay` (optional) - Delay before message becomes visible again (seconds)

**Response (Success):**
```json
{
  "status": "ok",
  "message": "Message requeued: abc123",
  "attempts": 1
}
```

**Response (Max Attempts):**
```json
{
  "status": "error",
  "message": "Message failed after 3 attempts",
  "message_id": "abc123"
}
```

## Example Use Cases

### 1. Email Queue (Worker Pattern)

**Producer (enqueue emails):**
```bash
curl -X POST http://localhost:8000/objects/triggers_queue -d '{
  "queue_name": "email_queue",
  "message": {
    "to": "user@example.com",
    "subject": "Welcome!",
    "body": "Thanks for signing up"
  },
  "priority": "normal"
}'
```

**Consumer (worker that sends emails):**
```python
import time
import requests

while True:
    # Dequeue message
    response = requests.get('http://localhost:8000/objects/triggers_queue',
                          params={'queue_name': 'email_queue'})

    data = response.json()

    if 'message' not in data or 'No messages' in data.get('message', ''):
        time.sleep(1)  # Wait if queue is empty
        continue

    message = data['message']
    message_id = message['id']
    email_data = message['message']

    try:
        # Process message (send email)
        send_email(email_data['to'], email_data['subject'], email_data['body'])

        # Acknowledge success
        requests.delete('http://localhost:8000/objects/triggers_queue',
                       params={'message_id': message_id})

    except Exception as e:
        # Requeue on failure (will retry)
        requests.put('http://localhost:8000/objects/triggers_queue',
                    params={'message_id': message_id})
```

### 2. Image Processing Pipeline

```bash
# High priority: User uploads
curl -X POST http://localhost:8000/objects/triggers_queue -d '{
  "queue_name": "image_queue",
  "message": {"image_id": "123", "user_id": "alice"},
  "priority": "high"
}'

# Normal priority: Batch processing
curl -X POST http://localhost:8000/objects/triggers_queue -d '{
  "queue_name": "image_queue",
  "message": {"image_id": "456", "batch_id": "batch_1"},
  "priority": "normal"
}'

# Low priority: Cleanup
curl -X POST http://localhost:8000/objects/triggers_queue -d '{
  "queue_name": "image_queue",
  "message": {"task": "cleanup_old_images"},
  "priority": "low"
}'
```

### 3. Background Jobs

```bash
# Report generation (critical)
curl -X POST http://localhost:8000/objects/triggers_queue -d '{
  "queue_name": "jobs_queue",
  "message": {"job_type": "generate_report", "report_id": "Q4_2024"},
  "priority": "critical"
}'

# Data export (normal)
curl -X POST http://localhost:8000/objects/triggers_queue -d '{
  "queue_name": "jobs_queue",
  "message": {"job_type": "export_data", "format": "csv"},
  "priority": "normal"
}'
```

## How It Works

### 1. Queue Storage

Messages are stored in TSV via StateManager:
- Key format: `msg_{queue_name}_{priority_level}_{timestamp}_{message_id}`
- Automatic priority sorting (higher priority first)
- FIFO within same priority level

### 2. Worker Pattern

```
┌─────────────┐
│  Producer   │
│  (API)      │
└──────┬──────┘
       │ POST (enqueue)
       ↓
┌─────────────────┐
│ queue.py        │ ← Stores messages in TSV
│ (Queue)         │
└─────────────────┘
       ↑
       │ GET (dequeue)
       │
┌─────────────────┐
│ Worker(s)       │ ← Process messages in background
│ (Python/CLI)    │
└─────────────────┘
       │
       │ DELETE (acknowledge) or PUT (requeue)
       ↓
┌─────────────────┐
│ queue.py        │ ← Updates message status
└─────────────────┘
```

### 3. Visibility Timeout

```
Worker 1 dequeues message:
- Message status → "processing"
- Message.visible_after = now + 300 seconds

Worker 2 tries to dequeue:
- Message is invisible (visible_after > now)
- Gets next available message or "No messages"

If Worker 1 crashes:
- After 300 seconds, message becomes visible again
- Worker 2 can dequeue and retry
```

### 4. Dead Letter Queue

```
Attempt 1: Dequeue → Process → Fail → PUT (requeue)
Attempt 2: Dequeue → Process → Fail → PUT (requeue)
Attempt 3: Dequeue → Process → Fail → PUT (max attempts)
           ↓
Message status → "failed" (moved to DLQ)
```

Query failed messages:
```bash
curl "http://localhost:8000/objects/triggers_queue?queue_name=email_queue&status=true"
# Returns: {"failed": 3}
```

## Development

```bash
# Install in editable mode
pip install -e packages/queue[dev]

# Run tests
pytest packages/queue/tests

# All 18 tests should pass
```

## Architecture

```
dbbasic-objects-queue     # This package (Layer 1c - Queue trigger)
├── queue.py              # REST API for task queues
└── __init__.py

Depends on:
└── dbbasic-objects-core  # Layer 0 - Runtime
```

## Comparison to Other Queues

| Feature | dbbasic-queue | Celery | RabbitMQ | AWS SQS |
|---------|---------------|--------|----------|---------|
| Setup | Zero config | Redis/Broker | Install | AWS account |
| Priority | 4 levels | Yes | Yes | Limited |
| Visibility Timeout | Yes | No | Yes | Yes |
| Dead Letter Queue | Yes | Manual | Yes | Yes |
| Storage | TSV files | Redis/DB | In-memory | Managed |
| Cost | Free | Infrastructure | Infrastructure | Pay-per-request |
| Retries | Automatic | Manual | Manual | Automatic |

## Worker Examples

### Python Worker

```python
import time
import requests

def process_message(message):
    """Your message processing logic"""
    print(f"Processing: {message}")
    # ... do work ...

def worker(queue_name):
    while True:
        # Dequeue
        response = requests.get('http://localhost:8000/objects/triggers_queue',
                              params={'queue_name': queue_name})

        data = response.json()

        if 'message' not in data:
            time.sleep(1)
            continue

        message = data['message']
        message_id = message['id']

        try:
            process_message(message['message'])

            # Success - acknowledge
            requests.delete('http://localhost:8000/objects/triggers_queue',
                          params={'message_id': message_id})

        except Exception as e:
            print(f"Error: {e}")

            # Failure - requeue
            requests.put('http://localhost:8000/objects/triggers_queue',
                        params={'message_id': message_id})

if __name__ == '__main__':
    worker('email_queue')
```

### CLI Worker

```bash
#!/bin/bash

QUEUE_NAME="email_queue"
BASE_URL="http://localhost:8000/objects/triggers_queue"

while true; do
    # Dequeue
    RESPONSE=$(curl -s "$BASE_URL?queue_name=$QUEUE_NAME")

    MESSAGE_ID=$(echo "$RESPONSE" | jq -r '.message.id // empty')

    if [ -z "$MESSAGE_ID" ]; then
        sleep 1
        continue
    fi

    # Process message
    echo "$RESPONSE" | jq '.message.message' | your_processing_script.sh

    if [ $? -eq 0 ]; then
        # Success - acknowledge
        curl -X DELETE "$BASE_URL?message_id=$MESSAGE_ID"
    else
        # Failure - requeue
        curl -X PUT "$BASE_URL?message_id=$MESSAGE_ID"
    fi
done
```

## Dependencies

- `dbbasic-objects-core` - Core runtime

## License

MIT

## Links

- [Documentation](https://github.com/danthegoodman/object-primitive)
- [Source Code](https://github.com/danthegoodman/object-primitive)
- [Issue Tracker](https://github.com/danthegoodman/object-primitive/issues)

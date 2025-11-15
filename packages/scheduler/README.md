# dbbasic-objects-scheduler

**Scheduled execution for dbbasic Object Primitives (Time-Based Triggers)**

Part of the [dbbasic](https://dbbasic.com) ecosystem.

## What is it?

Time-based trigger layer for Object Primitives - provides cron-style recurring tasks and one-time scheduled execution.

## Installation

```bash
pip install dbbasic-objects-scheduler
```

This will also install:
- `dbbasic-objects-core` (runtime)
- `croniter` (cron syntax parsing)

## Quick Start

### 1. Create Scheduler Object

```python
# examples/triggers/scheduler.py
# (Use the included scheduler.py or create your own)
```

### 2. Start Scheduler Daemon

```bash
dbbasic-objects-scheduler
# Or with custom settings:
dbbasic-objects-scheduler --data-dir ./data --interval 10
```

### 3. Schedule Tasks via API

```bash
# Schedule cron task (every 6 hours)
curl -X POST http://localhost:8000/objects/triggers_scheduler -d '{
  "object_id": "cleanup",
  "schedule": "0 */6 * * *",
  "payload": {"max_age_days": 30}
}'

# Schedule one-time task
curl -X POST http://localhost:8000/objects/triggers_scheduler -d '{
  "object_id": "report_generator",
  "schedule": "2025-12-01T14:30:00Z",
  "payload": {"report_type": "monthly"}
}'

# List all scheduled tasks
curl http://localhost:8000/objects/triggers_scheduler

# Cancel task
curl -X DELETE http://localhost:8000/objects/triggers_scheduler?task_id=abc123
```

## Features

### Cron Syntax Support

```python
"0 */6 * * *"     # Every 6 hours
"0 2 * * *"       # Daily at 2am
"0 0 * * 0"       # Weekly on Sunday
"*/15 * * * *"    # Every 15 minutes
"0 9-17 * * 1-5"  # Business hours (9am-5pm, Mon-Fri)
```

### One-Time Execution

```python
"2025-12-01T14:30:00Z"      # Specific datetime (UTC)
"2025-12-01T14:30:00-08:00" # With timezone
```

### Task Management

- **Create** - POST with schedule and payload
- **List** - GET all tasks
- **Cancel** - DELETE by task_id
- **Status** - Track active/completed/cancelled tasks

## How It Works

### 1. Scheduler Object (REST API)

`scheduler.py` is an Object Primitive that:
- Stores tasks in state (TSV)
- Provides REST API for task management
- Validates cron syntax and ISO datetimes

### 2. Scheduler Daemon (Background Process)

`daemon.py` is a background process that:
- Polls for tasks every 10 seconds (configurable)
- Checks if tasks are due to run
- Executes objects via ObjectRuntime
- Updates task status (last_run, next_run, run_count)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /objects/triggers_scheduler
       ↓
┌─────────────────┐
│ scheduler.py    │ ← Stores tasks in state (TSV)
│ (REST API)      │
└─────────────────┘
       ↑
       │ Reads tasks
       │
┌─────────────────┐
│ daemon.py       │ ← Polls every 10s, executes objects
│ (Background)    │
└─────────────────┘
```

## Example Use Cases

### 1. Nightly Cleanup

```bash
curl -X POST http://localhost:8000/objects/triggers_scheduler -d '{
  "object_id": "advanced_blog",
  "method": "POST",
  "schedule": "0 3 * * *",
  "payload": {"action": "cleanup", "max_age_days": 90}
}'
```

### 2. Weekly Reports

```bash
curl -X POST http://localhost:8000/objects/triggers_scheduler -d '{
  "object_id": "report_generator",
  "schedule": "0 9 * * 1",
  "payload": {"report_type": "weekly", "email": "team@company.com"}
}'
```

### 3. One-Time Reminder

```bash
curl -X POST http://localhost:8000/objects/triggers_scheduler -d '{
  "object_id": "email_sender",
  "schedule": "2025-12-25T09:00:00Z",
  "payload": {"to": "user@example.com", "subject": "Merry Christmas!"}
}'
```

## API Reference

### POST /objects/triggers_scheduler

Create scheduled task.

**Request:**
```json
{
  "object_id": "cleanup",
  "method": "POST",
  "schedule": "0 2 * * *",
  "payload": {"max_age_days": 30}
}
```

**Response:**
```json
{
  "status": "ok",
  "task_id": "abc123def456",
  "message": "Task scheduled: 0 2 * * *"
}
```

### GET /objects/triggers_scheduler

List all tasks or get specific task.

**Query params:**
- `task_id` - Get specific task
- `status` - Filter by status (active, completed, cancelled)

**Response:**
```json
{
  "status": "ok",
  "tasks": [...],
  "count": 5
}
```

### DELETE /objects/triggers_scheduler?task_id=abc123

Cancel scheduled task.

**Response:**
```json
{
  "status": "ok",
  "message": "Task cancelled: abc123"
}
```

## Development

```bash
# Install in editable mode
pip install -e packages/scheduler[dev]

# Install croniter dependency
pip install croniter

# Run tests
pytest packages/scheduler/tests

# Start daemon
python -m object_primitive_scheduler.daemon
```

## Architecture

```
dbbasic-objects-scheduler  # This package (Layer 1b - Time trigger)
├── scheduler.py           # REST API for task management
├── daemon.py              # Background execution daemon
└── __init__.py

Depends on:
├── dbbasic-objects-core   # Layer 0 - Runtime
└── croniter               # Cron syntax parsing
```

## Cron Syntax

Standard cron syntax (5 or 6 fields):

```
* * * * * *
│ │ │ │ │ │
│ │ │ │ │ └─ Day of week (0-6, 0=Sunday)
│ │ │ │ └─── Month (1-12)
│ │ │ └───── Day of month (1-31)
│ │ └─────── Hour (0-23)
│ └───────── Minute (0-59)
└─────────── Second (0-59, optional)
```

## Dependencies

- `dbbasic-objects-core` - Core runtime
- `croniter` - Cron syntax parsing

## License

MIT

## Links

- [Documentation](https://github.com/danthegoodman/object-primitive)
- [Source Code](https://github.com/danthegoodman/object-primitive)
- [Issue Tracker](https://github.com/danthegoodman/object-primitive/issues)

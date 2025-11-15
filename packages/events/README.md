# dbbasic-objects-events

**Event-based triggers for dbbasic Object Primitives (Pub/Sub System)**

Part of the [dbbasic](https://dbbasic.com) ecosystem.

## What is it?

Event-based trigger layer for Object Primitives - provides publish/subscribe event system for decoupled communication between objects.

## Installation

```bash
pip install dbbasic-objects-events
```

This will also install:
- `dbbasic-objects-core` (runtime)

## Quick Start

### 1. Create Events Object

```python
# examples/triggers/events.py
# (Use the included events.py or create your own)
```

### 2. Publish Events via API

```bash
# Publish event
curl -X POST http://localhost:8000/objects/triggers_events -d '{
  "event_type": "user.created",
  "payload": {"user_id": "123", "username": "alice"},
  "source": "auth"
}'

# Subscribe to event type
curl "http://localhost:8000/objects/triggers_events?subscribe=user.created&subscriber_id=my_app&callback_url=http://localhost:9000/webhook"

# Query event history
curl "http://localhost:8000/objects/triggers_events?event_type=user.created&limit=10"

# Query events since timestamp
curl "http://localhost:8000/objects/triggers_events?event_type=user.created&since=1699000000"

# Unsubscribe
curl -X DELETE "http://localhost:8000/objects/triggers_events?event_type=user.created&subscriber_id=my_app"
```

## Features

### Event Publishing

```python
# Publish event
{
  "event_type": "post.published",
  "payload": {"post_id": "456", "title": "Hello World"},
  "source": "blog"
}
```

### Event Types (Naming Convention)

```python
"user.created"          # User created
"user.updated"          # User updated
"user.deleted"          # User deleted
"post.published"        # Blog post published
"order.completed"       # Order completed
"payment.received"      # Payment received
```

Use dot notation: `resource.action`

### Event Querying

```python
# All events
GET /objects/triggers_events

# Filter by event type
GET /objects/triggers_events?event_type=user.created

# Filter by timestamp (since)
GET /objects/triggers_events?since=1699000000

# Limit results
GET /objects/triggers_events?limit=50

# Combine filters
GET /objects/triggers_events?event_type=user.created&since=1699000000&limit=10
```

### Event Subscription

```python
# Subscribe to event type
GET /objects/triggers_events?subscribe=user.created&subscriber_id=my_app

# Subscribe with callback URL (for webhook notifications)
GET /objects/triggers_events?subscribe=user.created&subscriber_id=my_app&callback_url=http://localhost:9000/webhook

# Unsubscribe
DELETE /objects/triggers_events?event_type=user.created&subscriber_id=my_app
```

## How It Works

### 1. Immutable Event Log

Events are stored in an append-only log (TSV):
- Events are never deleted or modified
- Complete audit trail of all events
- Can replay events from any point in time

### 2. Pub/Sub Pattern

```
┌─────────────┐
│  Publisher  │
│  (auth)     │
└──────┬──────┘
       │ POST /objects/triggers_events
       ↓
┌─────────────────┐
│ events.py       │ ← Stores events in immutable log (TSV)
│ (Event Store)   │
└─────────────────┘
       ↑
       │ Reads events
       │
┌─────────────────┐
│ Subscriber      │ ← Polls for new events
│ (blog)          │
└─────────────────┘
```

### 3. Event Structure

Each event contains:
```json
{
  "id": "a1b2c3d4e5f6g7h8",
  "event_type": "user.created",
  "payload": {"user_id": "123", "username": "alice"},
  "source": "auth",
  "timestamp": 1699000000
}
```

## Example Use Cases

### 1. User Registration Workflow

```bash
# Auth object publishes "user.created" event
curl -X POST http://localhost:8000/objects/triggers_events -d '{
  "event_type": "user.created",
  "payload": {"user_id": "123", "email": "alice@example.com"},
  "source": "auth"
}'

# Email service subscribes and sends welcome email
# Analytics service subscribes and tracks new users
# Profile service subscribes and creates user profile
```

### 2. Blog Post Publishing

```bash
# Blog object publishes "post.published" event
curl -X POST http://localhost:8000/objects/triggers_events -d '{
  "event_type": "post.published",
  "payload": {"post_id": "456", "title": "New Article", "author": "alice"},
  "source": "blog"
}'

# Notification service subscribes and notifies followers
# Search indexer subscribes and updates search index
# Analytics subscribes and tracks page views
```

### 3. Order Processing

```bash
# Order service publishes "order.completed" event
curl -X POST http://localhost:8000/objects/triggers_events -d '{
  "event_type": "order.completed",
  "payload": {"order_id": "789", "total": 99.99, "customer_id": "123"},
  "source": "orders"
}'

# Inventory service subscribes and updates stock
# Shipping service subscribes and creates shipping label
# Email service subscribes and sends confirmation email
```

## API Reference

### POST /objects/triggers_events

Publish event.

**Request:**
```json
{
  "event_type": "user.created",
  "payload": {"user_id": "123"},
  "source": "auth"
}
```

**Response:**
```json
{
  "status": "ok",
  "event_id": "abc123def456",
  "timestamp": 1699000000,
  "message": "Event published: user.created"
}
```

### GET /objects/triggers_events

Query event history or subscribe to event type.

**Query params:**
- `event_type` - Filter by event type
- `since` - Filter by timestamp (Unix timestamp)
- `limit` - Limit number of results (default: 100)
- `subscribe` - Subscribe to event type
- `subscriber_id` - Unique subscriber identifier
- `callback_url` - Webhook URL for notifications (optional)

**Response (Query):**
```json
{
  "status": "ok",
  "events": [...],
  "count": 5
}
```

**Response (Subscribe):**
```json
{
  "status": "ok",
  "subscriber_id": "my_app",
  "event_type": "user.created",
  "message": "Subscribed to user.created"
}
```

### DELETE /objects/triggers_events

Unsubscribe from event type.

**Query params:**
- `event_type` - Event type to unsubscribe from
- `subscriber_id` - Subscriber identifier

**Response:**
```json
{
  "status": "ok",
  "message": "Unsubscribed from user.created"
}
```

## Event Replay

Since events are immutable, you can replay events from any point in time:

```bash
# Get all events since timestamp
curl "http://localhost:8000/objects/triggers_events?since=1699000000"

# Replay user.created events
curl "http://localhost:8000/objects/triggers_events?event_type=user.created&since=0"
```

This is useful for:
- Rebuilding state from scratch
- Debugging issues
- Analytics and reporting
- Data migration

## Development

```bash
# Install in editable mode
pip install -e packages/events[dev]

# Run tests
pytest packages/events/tests

# All 16 tests should pass
```

## Architecture

```
dbbasic-objects-events    # This package (Layer 1b - Event trigger)
├── events.py             # REST API for pub/sub events
└── __init__.py

Depends on:
└── dbbasic-objects-core  # Layer 0 - Runtime
```

## Event Ordering

Events are returned in chronological order (newest first):
- Sorted by timestamp
- Consistent ordering across queries
- Reliable for event replay

## Subscription Model

Current implementation uses **polling** model:
- Subscribers query for new events periodically
- Best-effort notification on publish
- No guaranteed delivery (yet)

**Future:** Add event daemon for push-based notifications with guaranteed delivery.

## Comparison to Other Systems

| Feature | dbbasic-events | Kafka | RabbitMQ | AWS EventBridge |
|---------|----------------|-------|----------|-----------------|
| Setup | Zero config | Complex | Medium | AWS account |
| Storage | TSV files | Log segments | In-memory | Managed |
| Replay | Built-in | Built-in | No | Limited |
| Ordering | Guaranteed | Per-partition | Per-queue | Best-effort |
| Cost | Free | Infrastructure | Infrastructure | Pay-per-event |

## Dependencies

- `dbbasic-objects-core` - Core runtime

## License

MIT

## Links

- [Documentation](https://github.com/danthegoodman/object-primitive)
- [Source Code](https://github.com/danthegoodman/object-primitive)
- [Issue Tracker](https://github.com/danthegoodman/object-primitive/issues)

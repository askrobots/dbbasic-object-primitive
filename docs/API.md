# API Reference

Quick reference for all endpoints.

## Objects

### List All Objects

```bash
GET /objects
```

Returns all available objects with metadata.

### Execute Object

```bash
GET  /objects/{id}
POST /objects/{id}
PUT  /objects/{id}
DELETE /objects/{id}
```

Executes the corresponding HTTP method on the object.

### View Source Code

```bash
GET /objects/{id}?source=true
```

Returns the Python source code.

### View Metadata

```bash
GET /objects/{id}?metadata=true
```

Returns version count, log count, last modified, etc.

### View Logs

```bash
GET /objects/{id}?logs=true
GET /objects/{id}?logs=true&limit=50
```

Returns object's event logs.

### View Version History

```bash
GET /objects/{id}?versions=true
```

Returns all saved versions with timestamps.

## Cluster

### Cluster Status

```bash
GET /cluster/stations
```

Returns all stations in cluster with status.

Response:
```json
{
  "status": "ok",
  "station_id": "station1",
  "is_master": true,
  "stations": [
    {
      "station_id": "station1",
      "host": "localhost",
      "port": 8001,
      "is_active": true,
      "metrics": {
        "cpu_percent": 25.0,
        "memory_percent": 30.0,
        "object_count": 13
      }
    }
  ]
}
```

### Send Heartbeat

```bash
POST /cluster/heartbeat
```

Workers send this every 10 seconds to master.

Request body:
```json
{
  "station_id": "station2",
  "metrics": {
    "cpu_percent": 15.0,
    "memory_percent": 45.0,
    "object_count": 13
  }
}
```

### Station Info

```bash
GET /cluster/info
```

Returns info about current station.

### Migrate Object

```bash
POST /cluster/migrate
```

Move an object to a different station.

Request body:
```json
{
  "object_id": "counter",
  "target_station": "station2"
}
```

### Replicate State

```bash
POST /cluster/replicate
```

Receive state replication from another station (automatic).

Request body:
```json
{
  "object_id": "counter",
  "key": "count",
  "value": "42",
  "timestamp": 1234567890.123,
  "source_station": "station1"
}
```

## Dashboard

### Main Dashboard

```
GET /dashboard
```

Visual interface showing all objects and cluster status.

### Object Inspector

```
GET /dashboard/object/{id}
```

Detailed view of a specific object with tabs for source, logs, metrics, and versions.

## Special Injected Variables

Available in all object functions:

### _state_manager

Persistent key-value storage:
```python
_state_manager.set('key', 'value')
value = _state_manager.get('key', default='')
```

### _logger

Event logging:
```python
_logger.log('event_type', {
    'user': 'alice',
    'action': 'login'
})
```

### _runtime

Cross-object calls:
```python
result = _runtime.call_object('other_object', 'GET', {})
```

## Request Object

Available as `request` parameter:

```python
def POST(request):
    # Get field from request
    value = request.get('field_name', default='')

    # Access raw body
    body = request.body

    # Return dict (becomes JSON)
    return {"status": "ok", "value": value}
```

## Examples

See [EXAMPLES.md](EXAMPLES.md) for complete working examples.

# Quickstart

Create your first object in 2 minutes.

## 1. Start the Server

```bash
python run_server.py --port 8001
```

## 2. Create an Object

Create `examples/hello.py`:

```python
def GET(request):
    """Simple hello world object"""
    return {"message": "Hello, World!"}
```

That's it. The file is now a REST API.

## 3. Call It

```bash
curl http://localhost:8001/objects/hello
```

Response:
```json
{"message": "Hello, World!"}
```

## How It Works

- Server watches `examples/` directory
- Any `.py` file with HTTP method functions (GET, POST, etc.) becomes an object
- Object ID = file path without `.py` (e.g., `examples/hello.py` → `hello`)
- Call it at `/objects/{object_id}`

## Add State

Objects can remember things between calls:

```python
def GET(request):
    """Counter that increments on each call"""
    count = int(_state_manager.get('count', 0))
    count += 1
    _state_manager.set('count', count)
    return {"count": count}
```

State persists across server restarts.

## Add Logging

Objects can log events:

```python
def POST(request):
    """Log user actions"""
    user = request.get('user')
    action = request.get('action')

    _logger.log('user_action', {
        'user': user,
        'action': action
    })

    return {"status": "logged"}
```

View logs:
```bash
curl http://localhost:8001/objects/myobject?logs=true
```

## Next Steps

- [Examples](EXAMPLES.md) - More complete examples
- [API Reference](API.md) - All available endpoints
- [Cluster Setup](CLUSTER.md) - Run across multiple machines

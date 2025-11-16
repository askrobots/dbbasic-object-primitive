# Examples

Copy-paste examples with test commands.

## Tutorial Examples

Located in `examples/tutorial/`

### 1. Hello World

File: `examples/tutorial/01_hello.py`

Test:
```bash
curl http://localhost:8001/objects/tutorial_01_hello
```

### 2. Hello with Logging

File: `examples/tutorial/02_hello_with_logging.py`

Test:
```bash
curl http://localhost:8001/objects/tutorial_02_hello_with_logging
```

View logs:
```bash
curl http://localhost:8001/objects/tutorial_02_hello_with_logging?logs=true
```

### 3. Counter

File: `examples/tutorial/03_counter.py`

Increment counter:
```bash
curl http://localhost:8001/objects/tutorial_03_counter
curl http://localhost:8001/objects/tutorial_03_counter
curl http://localhost:8001/objects/tutorial_03_counter
```

Each call increments the count.

### 4. Calculator

File: `examples/tutorial/04_calculator.py`

Add:
```bash
curl -X POST http://localhost:8001/objects/tutorial_04_calculator \
  -H "Content-Type: application/json" \
  -d '{"operation": "add", "value": 5}'
```

Multiply:
```bash
curl -X POST http://localhost:8001/objects/tutorial_04_calculator \
  -H "Content-Type: application/json" \
  -d '{"operation": "multiply", "value": 3}'
```

Get result:
```bash
curl http://localhost:8001/objects/tutorial_04_calculator
```

### 5. User Registry

File: `examples/tutorial/05_user_registry.py`

Register user:
```bash
curl -X POST http://localhost:8001/objects/tutorial_05_user_registry \
  -H "Content-Type: application/json" \
  -d '{"action": "register", "username": "alice", "email": "alice@example.com"}'
```

List users:
```bash
curl http://localhost:8001/objects/tutorial_05_user_registry
```

### 6. Task Queue

File: `examples/tutorial/06_task_queue.py`

Add task:
```bash
curl -X POST http://localhost:8001/objects/tutorial_06_task_queue \
  -H "Content-Type: application/json" \
  -d '{"action": "add", "task": "Process invoice"}'
```

Get next task:
```bash
curl http://localhost:8001/objects/tutorial_06_task_queue?action=next
```

## Advanced Examples

### Auth System

File: `examples/advanced/auth.py`

Register:
```bash
curl -X POST http://localhost:8001/objects/advanced_auth \
  -H "Content-Type: application/json" \
  -d '{"action": "register", "email": "user@example.com", "password": "secret123", "password_confirm": "secret123"}'
```

Login:
```bash
curl -X POST http://localhost:8001/objects/advanced_auth \
  -H "Content-Type: application/json" \
  -d '{"action": "login", "email": "user@example.com", "password": "secret123"}'
```

Returns a token. Use it for authenticated requests.

### Blog System

File: `examples/advanced/blog.py`

Create post:
```bash
curl -X POST http://localhost:8001/objects/advanced_blog \
  -H "Content-Type: application/json" \
  -d '{
    "action": "create",
    "title": "My First Post",
    "content": "This is the content of my first blog post.",
    "author": "alice",
    "tags": ["intro", "test"]
  }'
```

List posts:
```bash
curl http://localhost:8001/objects/advanced_blog
```

Search:
```bash
curl "http://localhost:8001/objects/advanced_blog?search=first"
```

## Creating Your Own

Basic template:
```python
def GET(request):
    """Handle GET requests"""
    return {"status": "ok"}

def POST(request):
    """Handle POST requests"""
    data = request.get('data')
    return {"received": data}
```

With state:
```python
def POST(request):
    """Save and retrieve data"""
    key = request.get('key')
    value = request.get('value')

    if value:
        _state_manager.set(key, value)
        return {"saved": key}
    else:
        stored = _state_manager.get(key, '')
        return {"value": stored}
```

With logging:
```python
def POST(request):
    """Log all actions"""
    action = request.get('action')

    _logger.log('action', {
        'type': action,
        'timestamp': time.time()
    })

    return {"logged": action}
```

## Next Steps

- [API Reference](API.md) - All available endpoints
- [Cluster Setup](CLUSTER.md) - Distribute your objects

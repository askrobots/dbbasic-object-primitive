# dbbasic-objects-web

**REST API for dbbasic Object Primitives (HTTP Trigger Layer)**

Part of the [dbbasic](https://dbbasic.com) ecosystem.

## What is it?

HTTP trigger layer for Object Primitives - provides REST API for executing, inspecting, and modifying objects over HTTP.

## Installation

```bash
pip install dbbasic-objects-web
```

This will also install:
- `dbbasic-objects-core` (runtime)
- `dbbasic-web` (web framework)
- `uvicorn` (ASGI server)

## Quick Start

```bash
# Start server
dbbasic-objects-serve

# Or with Python
python -m object_primitive_web.server
```

Server starts on `http://localhost:8000`

## API Endpoints

### List Objects
```bash
GET /objects
# Returns list of all available objects
```

### Execute Object
```bash
POST /objects/{id}
Content-Type: application/json

{"key": "value"}

# Executes object's POST method with request data
```

### View Source
```bash
GET /objects/{id}?source=true
# Returns object's source code
```

### View Metadata
```bash
GET /objects/{id}?metadata=true
# Returns object metadata (logs count, versions count, state keys)
```

### View Logs
```bash
GET /objects/{id}?logs=true
GET /objects/{id}?logs=true&level=ERROR&limit=50
# Returns object's logs (with optional filtering)
```

### View Versions
```bash
GET /objects/{id}?versions=true
# Returns version history
```

### Get Specific Version
```bash
GET /objects/{id}?version=3
# Returns version 3 of the object
```

### Modify Source
```bash
PUT /objects/{id}?source=true
Content-Type: text/plain

# New source code here

# Updates object's source code (creates new version)
```

### Rollback
```bash
POST /objects/{id}
Content-Type: application/json

{
  "action": "rollback",
  "version_id": 3,
  "author": "admin",
  "message": "Rollback to stable version"
}

# Rolls back to version 3 (creates new version)
```

## Example Objects

Create `examples/basics/counter.py`:

```python
def POST(request):
    \"\"\"Increment counter\"\"\"
    count = _state_manager.get('count', 0)
    count += 1
    _state_manager.set('count', count)

    if _logger:
        _logger.info('Counter incremented', count=count)

    return {'count': count}

def GET(request):
    \"\"\"Get current count\"\"\"
    count = _state_manager.get('count', 0)
    return {'count': count}
```

Use it:

```bash
# Increment counter
curl -X POST http://localhost:8000/objects/basics_counter
# {"count": 1}

# Get count
curl http://localhost:8000/objects/basics_counter
# {"count": 1}

# View logs
curl http://localhost:8000/objects/basics_counter?logs=true

# View source
curl http://localhost:8000/objects/basics_counter?source=true
```

## Architecture

```
dbbasic-objects-web       # This package (Layer 1a - HTTP trigger)
├── objects.py            # List all objects
├── objects/[id].py       # Individual object operations
└── server.py             # Uvicorn server

Depends on:
├── dbbasic-objects-core  # Layer 0 - Runtime
└── dbbasic-web           # Web framework
```

## Configuration

Set environment variables:

```bash
export HOST=0.0.0.0       # Bind address (default: 0.0.0.0)
export PORT=8001          # Port (default: 8000)
```

## Development

```bash
# Install in editable mode
pip install -e packages/web[dev]

# Run tests
pytest packages/web/tests

# Start server
python -m object_primitive_web.server
```

## Dependencies

- `dbbasic-objects-core` - Core runtime
- `dbbasic-web` - Web framework
- `uvicorn` - ASGI server

## License

MIT

## Links

- [Documentation](https://github.com/danthegoodman/object-primitive)
- [Source Code](https://github.com/danthegoodman/object-primitive)
- [Issue Tracker](https://github.com/danthegoodman/object-primitive/issues)

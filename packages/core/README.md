# dbbasic-objects-core

**Core runtime for dbbasic Object Primitives**

Part of the [dbbasic](https://dbbasic.com) ecosystem.

## What is it?

The foundation layer for Object Primitives - executable network objects with built-in state management, self-logging, and versioning.

## Features

- **ObjectRuntime** - Load and execute Python objects from .py files
- **StateManager** - Persistent state in TSV files (human-readable, git-friendly)
- **SelfLogger** - Objects log to themselves (append-only TSV)
- **VersionManager** - Automatic code versioning with rollback
- **Endpoint Loader** - Load .py files as executable objects

## Installation

```bash
pip install dbbasic-objects-core
```

## Quick Start

```python
from object_primitive_core import ObjectRuntime

# Create runtime
runtime = ObjectRuntime(data_dir='data')

# Load an object
obj = runtime.load_object('path/to/my_object.py')

# Execute it
result = obj.execute('POST', {'key': 'value'})

# Check logs
logs = obj.logger.get_recent_logs(limit=10)

# Get version history
versions = obj.version_manager.get_history(obj.object_id)
```

## What's an Object Primitive?

An Object Primitive is a `.py` file that:
- Defines HTTP-style methods (GET, POST, PUT, DELETE)
- Has persistent state via `_state_manager`
- Logs to itself via `_logger`
- Is automatically versioned
- Is network-accessible

Example object:

```python
# my_counter.py
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

## Architecture

```
dbbasic-objects-core      # This package (Layer 0)
├── ObjectRuntime          # Loads and executes objects
├── StateManager           # Persistent state (TSV)
├── SelfLogger             # Self-logging (TSV)
├── VersionManager         # Code versioning (TSV)
└── Endpoint Loader        # Import .py files as modules

dbbasic-objects-web       # Layer 1a - HTTP trigger
dbbasic-objects-scheduler # Layer 1b - Time trigger
dbbasic-objects-events    # Layer 1c - Event trigger
dbbasic-queue             # Layer 1d - Queue trigger (already exists!)
```

## Dependencies

None - only uses Python standard library.

## License

MIT

## Links

- [Documentation](https://github.com/danthegoodman/object-primitive)
- [Source Code](https://github.com/danthegoodman/object-primitive)
- [Issue Tracker](https://github.com/danthegoodman/object-primitive/issues)

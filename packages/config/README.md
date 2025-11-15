# dbbasic-objects-config

**Configuration management for dbbasic Object Primitives (Multi-source Config)**

Part of the [dbbasic](https://dbbasic.com) ecosystem.

## What is it?

Configuration management layer for Object Primitives - provides multi-source configuration with priority ordering, type validation, and runtime overrides.

## Installation

```bash
pip install dbbasic-objects-config
```

This will also install:
- `dbbasic-objects-core` (runtime)

## Quick Start

### 1. Create Config Object

```python
# examples/config/environment.py
# (Use the included environment.py or create your own)
```

### 2. Use Config via API

```bash
# Set config value (persistent)
curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/mydb"
}'

# Get config value
curl "http://localhost:8000/objects/config_environment?key=DATABASE_URL"

# Set runtime override (temporary, for testing)
curl -X PUT http://localhost:8000/objects/config_environment -d '{
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/testdb",
  "ttl": 3600
}'

# Delete config
curl -X DELETE "http://localhost:8000/objects/config_environment?key=DATABASE_URL"

# List all config
curl "http://localhost:8000/objects/config_environment?list=true"
```

## Features

### Multi-Source Priority

Config values are resolved in this order (highest to lowest priority):

1. **Runtime Overrides** (temporary, for testing)
2. **Environment Variables** (process env vars)
3. **Persistent Config** (set via API)
4. **Default Values** (fallback)

```python
# Example: DATABASE_URL resolution
1. Check runtime override (set via PUT)
2. Check environment variable (DATABASE_URL=...)
3. Check persistent config (set via POST)
4. Return default value (or error if no default)
```

### Type Validation

Supports type validation:
- `string` - String value (default)
- `int` - Integer value
- `float` - Float value
- `bool` - Boolean value (true/false, 1/0, yes/no)
- `json` - JSON object or array

```bash
# Integer with validation
curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "PORT",
  "value": "8000",
  "type": "int"
}'

# Boolean with validation
curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "DEBUG",
  "value": "true",
  "type": "bool"
}'

# JSON with validation
curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "SETTINGS",
  "value": {"timeout": 30, "retries": 3},
  "type": "json"
}'
```

### Runtime Overrides (Testing)

Set temporary config values with TTL:

```bash
# Override for 1 hour
curl -X PUT http://localhost:8000/objects/config_environment -d '{
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/testdb",
  "ttl": 3600
}'
```

Overrides automatically expire after TTL and fall back to next priority source.

### Default Values

Provide default if config not found:

```bash
curl "http://localhost:8000/objects/config_environment?key=PORT&default=8000"
```

## API Reference

### POST /objects/config_environment

Set persistent config value.

**Request:**
```json
{
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/mydb",
  "type": "string"
}
```

**Parameters:**
- `key` (required) - Config key
- `value` (required) - Config value
- `type` (optional) - Value type for validation (default: "string")

**Response:**
```json
{
  "status": "ok",
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/mydb",
  "message": "Config set: DATABASE_URL"
}
```

### GET /objects/config_environment

Get config value or list all config.

**Query params:**
- `key` (required unless list=true) - Config key
- `default` (optional) - Default value if not found
- `list` (optional) - If "true", list all config

**Response (Get):**
```json
{
  "status": "ok",
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/mydb",
  "source": "config"
}
```

**Response (List):**
```json
{
  "status": "ok",
  "config": {
    "DATABASE_URL": "postgresql://localhost/mydb",
    "PORT": 8000
  },
  "overrides": {
    "DATABASE_URL": "postgresql://localhost/testdb"
  },
  "environment": {}
}
```

### PUT /objects/config_environment

Set runtime override (temporary).

**Request:**
```json
{
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/testdb",
  "ttl": 3600
}
```

**Parameters:**
- `key` (required) - Config key
- `value` (required) - Override value
- `ttl` (optional) - Time to live in seconds (default: 3600)

**Response:**
```json
{
  "status": "ok",
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/testdb",
  "ttl": 3600,
  "message": "Runtime override set: DATABASE_URL (expires in 3600s)"
}
```

### DELETE /objects/config_environment

Delete config value or override.

**Query params:**
- `key` (required) - Config key
- `override_only` (optional) - If true, only delete override (keep persistent config)

**Response:**
```json
{
  "status": "ok",
  "message": "Config deleted: DATABASE_URL",
  "override_deleted": true,
  "config_deleted": true
}
```

## Example Use Cases

### 1. Application Configuration

```bash
# Production config
curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "DATABASE_URL",
  "value": "postgresql://prod.example.com/mydb"
}'

curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "PORT",
  "value": "8000",
  "type": "int"
}'

curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "DEBUG",
  "value": "false",
  "type": "bool"
}'
```

### 2. Testing with Overrides

```bash
# Override for testing (expires in 1 hour)
curl -X PUT http://localhost:8000/objects/config_environment -d '{
  "key": "DATABASE_URL",
  "value": "postgresql://localhost/testdb",
  "ttl": 3600
}'

# Run tests...

# Delete override to return to production config
curl -X DELETE "http://localhost:8000/objects/config_environment?key=DATABASE_URL&override_only=true"
```

### 3. Environment-Specific Config

```bash
# Development
export DATABASE_URL=postgresql://localhost/devdb
export DEBUG=true

# Production
export DATABASE_URL=postgresql://prod.example.com/mydb
export DEBUG=false

# Application reads from environment variables
curl "http://localhost:8000/objects/config_environment?key=DATABASE_URL"
# Returns environment variable if set, otherwise persistent config
```

### 4. Feature Flags

```bash
# Set feature flags
curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "FEATURE_NEW_UI",
  "value": "true",
  "type": "bool"
}'

curl -X POST http://localhost:8000/objects/config_environment -d '{
  "key": "FEATURE_BETA_SEARCH",
  "value": "false",
  "type": "bool"
}'

# Read in application
curl "http://localhost:8000/objects/config_environment?key=FEATURE_NEW_UI"
```

## How It Works

### Priority Resolution

```
┌─────────────────────┐
│ Runtime Override    │ ← Highest priority (temporary)
└─────────┬───────────┘
          │ If not found...
          ↓
┌─────────────────────┐
│ Environment Var     │ ← Second priority (process env)
└─────────┬───────────┘
          │ If not found...
          ↓
┌─────────────────────┐
│ Persistent Config   │ ← Third priority (TSV storage)
└─────────┬───────────┘
          │ If not found...
          ↓
┌─────────────────────┐
│ Default Value       │ ← Lowest priority (or error)
└─────────────────────┘
```

### Storage

- **Persistent Config**: Stored in TSV via StateManager
- **Runtime Overrides**: Stored in TSV with expiration timestamps
- **Environment Variables**: Read from process environment
- **Defaults**: Provided in request or hardcoded

### Type Validation

```python
# String (default)
"hello" → "hello"

# Integer
"8000" → 8000
"not_a_number" → Error

# Float
"3.14" → 3.14

# Boolean
"true" → True
"false" → False
"1" → True
"0" → False

# JSON
{"key": "value"} → {"key": "value"}
'{"key": "value"}' → {"key": "value"}
```

## Development

```bash
# Install in editable mode
pip install -e packages/config[dev]

# Run tests
pytest packages/config/tests

# All 19 tests should pass
```

## Architecture

```
dbbasic-objects-config     # This package (Layer 1d - Config)
├── environment.py         # REST API for config management
└── __init__.py

Depends on:
└── dbbasic-objects-core   # Layer 0 - Runtime
```

## Testing Best Practices

### Use Runtime Overrides for Tests

```python
import requests

def test_database_connection():
    # Override database URL for testing
    requests.put('http://localhost:8000/objects/config_environment', json={
        'key': 'DATABASE_URL',
        'value': 'postgresql://localhost/testdb',
        'ttl': 60,  # 1 minute
    })

    # Run test...

    # Override expires automatically
```

### Use Environment Variables for CI

```bash
# .github/workflows/test.yml
env:
  DATABASE_URL: postgresql://localhost/testdb
  REDIS_URL: redis://localhost:6379
  DEBUG: true
```

### Use Persistent Config for Production

```bash
# Deploy script
curl -X POST http://prod.example.com/objects/config_environment -d '{
  "key": "DATABASE_URL",
  "value": "$DATABASE_URL"
}'
```

## Comparison to Other Config Systems

| Feature | dbbasic-config | python-decouple | dynaconf | dotenv |
|---------|----------------|-----------------|----------|--------|
| Multi-source | Yes (4 sources) | Yes (3 sources) | Yes | Limited |
| Priority Order | Yes | Yes | Yes | No |
| Type Validation | Yes | Manual | Yes | No |
| Runtime Overrides | Yes (with TTL) | No | No | No |
| REST API | Yes | No | No | No |
| Storage | TSV | Files | Files | .env |
| Hot Reload | Yes | No | Yes | No |

## Dependencies

- `dbbasic-objects-core` - Core runtime

## License

MIT

## Links

- [Documentation](https://github.com/danthegoodman/object-primitive)
- [Source Code](https://github.com/danthegoodman/object-primitive)
- [Issue Tracker](https://github.com/danthegoodman/object-primitive/issues)

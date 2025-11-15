"""
Environment Config Object - Multi-source configuration for Object Primitives

This object provides configuration management with multiple sources:
1. Runtime overrides (highest priority - for testing)
2. Environment variables
3. Persistent config values (via API)
4. Default values (lowest priority)

Example usage:
    # Get config value
    GET /objects/environment?key=DATABASE_URL

    # Set config value (persistent)
    POST /objects/environment
    {
        "key": "DATABASE_URL",
        "value": "postgresql://localhost/mydb"
    }

    # Set runtime override (temporary, for testing)
    PUT /objects/environment
    {
        "key": "DATABASE_URL",
        "value": "postgresql://localhost/testdb",
        "ttl": 3600
    }

    # Delete config value
    DELETE /objects/environment?key=DATABASE_URL

    # List all config values
    GET /objects/environment?list=true
"""

import os
import time
import json
from typing import Any, Dict, Optional

# These will be injected by ObjectRuntime
_logger = None
_state_manager = None


def GET(request: Dict[str, Any]) -> Dict[str, Any]:
    """Get config value or list all config"""

    # List all config
    if request.get('list'):
        return _list_all_config()

    # Get specific config value
    key = request.get('key', '').strip()

    if not key:
        return {'status': 'error', 'message': 'key is required'}

    default = request.get('default')

    # Get value from all sources (priority order)
    value, source = _get_config_value(key, default)

    if value is None and default is None:
        return {
            'status': 'error',
            'message': f'Config not found: {key}',
        }

    if _logger:
        _logger.info('Config retrieved',
                    key=key,
                    source=source,
                    has_value=value is not None)

    return {
        'status': 'ok',
        'key': key,
        'value': value,
        'source': source,
    }


def POST(request: Dict[str, Any]) -> Dict[str, Any]:
    """Set config value (persistent)"""
    key = request.get('key', '').strip()
    value = request.get('value')

    if not key:
        return {'status': 'error', 'message': 'key is required'}

    if value is None:
        return {'status': 'error', 'message': 'value is required'}

    # Validate value type
    value_type = request.get('type', 'string')
    validated_value, error = _validate_value(value, value_type)

    if error:
        return {'status': 'error', 'message': error}

    # Save to persistent config
    config_entry = {
        'key': key,
        'value': validated_value,
        'type': value_type,
        'created_at': int(time.time()),
        'updated_at': int(time.time()),
    }

    _save_config(config_entry)

    if _logger:
        _logger.info('Config set',
                    key=key,
                    type=value_type)

    return {
        'status': 'ok',
        'key': key,
        'value': validated_value,
        'message': f'Config set: {key}',
    }


def PUT(request: Dict[str, Any]) -> Dict[str, Any]:
    """Set runtime override (temporary, for testing)"""
    key = request.get('key', '').strip()
    value = request.get('value')
    ttl = request.get('ttl', 3600)  # Default 1 hour

    if not key:
        return {'status': 'error', 'message': 'key is required'}

    if value is None:
        return {'status': 'error', 'message': 'value is required'}

    try:
        ttl = int(ttl)
    except (ValueError, TypeError):
        ttl = 3600

    # Save as runtime override
    override = {
        'key': key,
        'value': value,
        'created_at': int(time.time()),
        'expires_at': int(time.time()) + ttl,
    }

    _save_override(override)

    if _logger:
        _logger.info('Runtime override set',
                    key=key,
                    ttl=ttl)

    return {
        'status': 'ok',
        'key': key,
        'value': value,
        'ttl': ttl,
        'message': f'Runtime override set: {key} (expires in {ttl}s)',
    }


def DELETE(request: Dict[str, Any]) -> Dict[str, Any]:
    """Delete config value or override"""
    key = request.get('key', '').strip()
    override_only = request.get('override_only', False)

    if not key:
        return {'status': 'error', 'message': 'key is required'}

    # Delete override
    override_deleted = _delete_override(key)

    # Delete persistent config (unless override_only)
    config_deleted = False
    if not override_only:
        config_deleted = _delete_config(key)

    if not override_deleted and not config_deleted:
        return {
            'status': 'error',
            'message': f'Config not found: {key}',
        }

    if _logger:
        _logger.info('Config deleted',
                    key=key,
                    override_deleted=override_deleted,
                    config_deleted=config_deleted)

    return {
        'status': 'ok',
        'message': f'Config deleted: {key}',
        'override_deleted': override_deleted,
        'config_deleted': config_deleted,
    }


# Helper functions

def _get_config_value(key: str, default: Any = None) -> tuple[Any, str]:
    """
    Get config value from all sources (priority order):
    1. Runtime overrides (highest priority)
    2. Environment variables
    3. Persistent config
    4. Default value (lowest priority)
    """

    # 1. Check runtime overrides first
    override = _get_override(key)
    if override:
        # Check if expired
        if override['expires_at'] <= int(time.time()):
            _delete_override(key)
        else:
            return override['value'], 'override'

    # 2. Check environment variables
    env_value = os.environ.get(key)
    if env_value is not None:
        return env_value, 'environment'

    # 3. Check persistent config
    config = _get_config(key)
    if config:
        return config['value'], 'config'

    # 4. Return default
    return default, 'default'


def _validate_value(value: Any, value_type: str) -> tuple[Any, Optional[str]]:
    """Validate value matches expected type"""

    if value_type == 'string':
        return str(value), None

    elif value_type == 'int':
        try:
            return int(value), None
        except (ValueError, TypeError):
            return None, f'Invalid int: {value}'

    elif value_type == 'float':
        try:
            return float(value), None
        except (ValueError, TypeError):
            return None, f'Invalid float: {value}'

    elif value_type == 'bool':
        if isinstance(value, bool):
            return value, None
        if isinstance(value, str):
            if value.lower() in ('true', '1', 'yes'):
                return True, None
            if value.lower() in ('false', '0', 'no'):
                return False, None
        return None, f'Invalid bool: {value}'

    elif value_type == 'json':
        if isinstance(value, (dict, list)):
            return value, None
        try:
            return json.loads(value), None
        except (ValueError, TypeError):
            return None, f'Invalid JSON: {value}'

    else:
        return None, f'Unknown type: {value_type}'


def _save_config(config: Dict[str, Any]) -> None:
    """Save config to persistent storage"""
    if not _state_manager:
        return

    key = config['key']
    _state_manager.set(f'config_{key}', json.dumps(config))


def _get_config(key: str) -> Optional[Dict[str, Any]]:
    """Get config from persistent storage"""
    if not _state_manager:
        return None

    config_json = _state_manager.get(f'config_{key}')
    if not config_json:
        return None

    return json.loads(config_json)


def _delete_config(key: str) -> bool:
    """Delete config from persistent storage"""
    if not _state_manager:
        return False

    config = _get_config(key)
    if not config:
        return False

    _state_manager.delete(f'config_{key}')
    return True


def _save_override(override: Dict[str, Any]) -> None:
    """Save runtime override"""
    if not _state_manager:
        return

    key = override['key']
    _state_manager.set(f'override_{key}', json.dumps(override))


def _get_override(key: str) -> Optional[Dict[str, Any]]:
    """Get runtime override"""
    if not _state_manager:
        return None

    override_json = _state_manager.get(f'override_{key}')
    if not override_json:
        return None

    return json.loads(override_json)


def _delete_override(key: str) -> bool:
    """Delete runtime override"""
    if not _state_manager:
        return False

    override = _get_override(key)
    if not override:
        return False

    _state_manager.delete(f'override_{key}')
    return True


def _list_all_config() -> Dict[str, Any]:
    """List all config values from all sources"""
    if not _state_manager:
        return {
            'status': 'ok',
            'config': {},
            'overrides': {},
            'environment': {},
        }

    all_state = _state_manager.get_all()

    # Get persistent config
    config_values = {}
    for key, value in all_state.items():
        if key.startswith('config_'):
            config = json.loads(value)
            config_key = config['key']
            config_values[config_key] = config['value']

    # Get runtime overrides
    override_values = {}
    now = int(time.time())
    for key, value in all_state.items():
        if key.startswith('override_'):
            override = json.loads(value)

            # Skip expired
            if override['expires_at'] < now:
                continue

            override_key = override['key']
            override_values[override_key] = override['value']

    # Get environment variables (only those that match config keys)
    env_values = {}
    all_keys = set(config_values.keys()) | set(override_values.keys())
    for key in all_keys:
        env_value = os.environ.get(key)
        if env_value is not None:
            env_values[key] = env_value

    return {
        'status': 'ok',
        'config': config_values,
        'overrides': override_values,
        'environment': env_values,
    }

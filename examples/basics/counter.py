"""
Counter Endpoint - A living object primitive

This endpoint demonstrates the complete Object Primitive System:
- Self-logging (logs all requests to itself)
- Self-versioning (tracks changes to its own code)
- Self-contained state (maintains own counter)
- Network accessible (can be called via HTTP)

The counter:
- Increments on GET requests
- Can be reset via POST
- Logs every operation to its own log file
- Versions changes to its code
"""

# This will be injected by the runtime
_logger = None
_state_manager = None


def GET(request):
    """
    Increment counter and return current value.

    Args:
        request: HTTP request dict

    Returns:
        Dict with counter value
    """
    # Get current count
    if _state_manager:
        count = _state_manager.get('count', 0)
        count += 1
        _state_manager.set('count', count)
    else:
        # Fallback if no state manager
        count = 1

    # Log the operation
    if _logger:
        _logger.info(
            'Counter incremented',
            method='GET',
            count=count,
            user_id=request.get('user_id'),
            request_id=request.get('request_id'),
        )

    return {
        'status': 'ok',
        'count': count,
        'message': f'Counter is now at {count}',
    }


def POST(request):
    """
    Reset counter to 0 (or specified value).

    Args:
        request: HTTP request dict with optional 'value' field

    Returns:
        Dict with new counter value
    """
    # Get reset value (default to 0)
    new_value = request.get('value', 0)

    # Reset count
    if _state_manager:
        old_value = _state_manager.get('count', 0)
        _state_manager.set('count', new_value)
    else:
        old_value = 0

    # Log the reset
    if _logger:
        _logger.warning(
            'Counter reset',
            method='POST',
            old_value=old_value,
            new_value=new_value,
            user_id=request.get('user_id'),
            request_id=request.get('request_id'),
        )

    return {
        'status': 'ok',
        'count': new_value,
        'message': f'Counter reset from {old_value} to {new_value}',
    }


def DELETE(request):
    """
    Delete counter state (reset to uninitialized).

    Args:
        request: HTTP request dict

    Returns:
        Dict with status
    """
    if _state_manager:
        old_value = _state_manager.get('count', 0)
        _state_manager.delete('count')
    else:
        old_value = 0

    # Log the deletion
    if _logger:
        _logger.critical(
            'Counter state deleted',
            method='DELETE',
            old_value=old_value,
            user_id=request.get('user_id'),
            request_id=request.get('request_id'),
        )

    return {
        'status': 'ok',
        'message': f'Counter state deleted (was {old_value})',
    }


__endpoint__ = {
    'name': 'counter',
    'description': 'A self-logging, self-versioning counter endpoint',
    'version': '1.0.0',
    'author': 'Object Primitive System',
    'methods': ['GET', 'POST', 'DELETE'],
    'self_logging': True,
    'self_versioning': True,
    'state': {
        'count': 'Integer counter value',
    },
    'examples': {
        'GET': {
            'description': 'Increment counter',
            'request': {},
            'response': {'status': 'ok', 'count': 1, 'message': 'Counter is now at 1'},
        },
        'POST': {
            'description': 'Reset counter',
            'request': {'value': 0},
            'response': {'status': 'ok', 'count': 0, 'message': 'Counter reset from 5 to 0'},
        },
        'DELETE': {
            'description': 'Delete counter state',
            'request': {},
            'response': {'status': 'ok', 'message': 'Counter state deleted (was 5)'},
        },
    },
}

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
- Tracks execution time for performance monitoring
"""
import time

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
    start_time = time.time()

    # Get current count
    if _state_manager:
        count = _state_manager.get('count', 0)
        count += 1
        _state_manager.set('count', count)
    else:
        # Fallback if no state manager
        count = 1

    # Calculate execution time
    exec_time_ms = (time.time() - start_time) * 1000

    # Log the operation with execution time
    if _logger:
        _logger.info(
            f'Counter incremented - completed in {exec_time_ms:.2f}ms',
            method='GET',
            count=count,
            exec_time_ms=exec_time_ms,
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
    start_time = time.time()

    # Get reset value (default to 0)
    new_value = request.get('value', 0)

    # Reset count
    if _state_manager:
        old_value = _state_manager.get('count', 0)
        _state_manager.set('count', new_value)
    else:
        old_value = 0

    # Calculate execution time
    exec_time_ms = (time.time() - start_time) * 1000

    # Log the reset with execution time
    if _logger:
        _logger.warning(
            f'Counter reset - completed in {exec_time_ms:.2f}ms',
            method='POST',
            old_value=old_value,
            new_value=new_value,
            exec_time_ms=exec_time_ms,
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


def test_increment():
    """
    Test that counter increments correctly.

    Objects can test themselves! This is dogfooding at its finest.
    """
    if not _state_manager:
        return {'status': 'skip', 'reason': 'No state manager available'}

    # Reset to known state
    _state_manager.set('count', 10)

    # Increment
    result = GET({'test': True})

    # Verify
    assert result['count'] == 11, f"Expected count=11, got {result['count']}"
    assert result['status'] == 'ok', f"Expected status=ok, got {result['status']}"

    if _logger:
        _logger.info('test_increment passed', test='test_increment', result='pass')

    return {'status': 'pass', 'test': 'test_increment'}


def test_reset():
    """Test that counter resets to specified value."""
    if not _state_manager:
        return {'status': 'skip', 'reason': 'No state manager available'}

    # Set to some value
    _state_manager.set('count', 99)

    # Reset to 0
    result = POST({'value': 0})

    # Verify
    assert result['count'] == 0, f"Expected count=0, got {result['count']}"
    assert _state_manager.get('count') == 0, "State not actually reset"

    if _logger:
        _logger.info('test_reset passed', test='test_reset', result='pass')

    return {'status': 'pass', 'test': 'test_reset'}


def test_state_persistence():
    """Test that state persists across calls."""
    if not _state_manager:
        return {'status': 'skip', 'reason': 'No state manager available'}

    # Set known value
    _state_manager.set('count', 42)

    # Get it back
    value = _state_manager.get('count')

    # Verify
    assert value == 42, f"Expected count=42, got {value}"

    if _logger:
        _logger.info('test_state_persistence passed', test='test_state_persistence', result='pass')

    return {'status': 'pass', 'test': 'test_state_persistence'}


__endpoint__ = {
    'name': 'counter',
    'description': 'A self-logging, self-versioning counter endpoint',
    'version': '1.0.0',
    'author': 'Object Primitive System',
    'methods': ['GET', 'POST', 'DELETE'],
    'self_logging': True,
    'self_versioning': True,
    'self_testing': True,  # Objects can test themselves!
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

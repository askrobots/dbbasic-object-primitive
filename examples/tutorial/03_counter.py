"""
03_counter.py - Stateful counter
"""

_logger = None
_state_manager = None


def GET(request):
    """Increment counter and return current value"""

    # Get current count from persistent state
    if _state_manager:
        count = _state_manager.get('count', 0)
        count += 1
        _state_manager.set('count', count)
    else:
        count = 1

    # Log the increment
    if _logger:
        _logger.info(
            'Counter incremented',
            count=count,
            user_id=request.get('user_id'),
        )

    return {
        'status': 'ok',
        'count': count,
        'message': f'Counter is now at {count}',
    }


def POST(request):
    """Reset counter to 0"""

    # Get old value
    if _state_manager:
        old_value = _state_manager.get('count', 0)
        _state_manager.set('count', 0)
    else:
        old_value = 0

    # Log the reset
    if _logger:
        _logger.warning(
            'Counter reset',
            old_value=old_value,
            user_id=request.get('user_id'),
        )

    return {
        'status': 'ok',
        'count': 0,
        'message': f'Counter reset from {old_value} to 0',
    }


# Metadata
__endpoint__ = {
    'name': 'counter',
    'description': 'A simple counter that increments on GET, resets on POST',
    'version': '1.0.0',
    'author': 'tutorial',
}

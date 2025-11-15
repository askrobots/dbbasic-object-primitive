"""
02_hello_with_logging.py - Object with self-logging
"""

# The runtime will inject these
_logger = None
_state_manager = None


def GET(request):
    """Return a greeting with logging"""

    # Extract user info from request
    user_id = request.get('user_id', 'anonymous')
    ip_address = request.get('ip_address', 'unknown')

    # Log the request
    if _logger:
        _logger.info(
            'Greeting requested',
            user_id=user_id,
            ip_address=ip_address,
        )

    # Return greeting
    return {
        'status': 'ok',
        'message': f'Hello, {user_id}!',
    }

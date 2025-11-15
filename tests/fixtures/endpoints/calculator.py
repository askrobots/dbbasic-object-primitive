"""
Test fixture: Calculator endpoint with validation

This endpoint demonstrates:
- Input validation
- Error handling
- Self-logging (to be implemented)
"""


def GET(request):
    """Get calculator info"""
    return {
        'status': 'ok',
        'name': 'calculator',
        'operations': ['add', 'subtract', 'multiply', 'divide'],
    }


def POST(request):
    """Perform calculation"""
    operation = request.get('operation')
    a = request.get('a')
    b = request.get('b')

    # Validation
    if operation not in ['add', 'subtract', 'multiply', 'divide']:
        return {
            'status': 'error',
            'error': f'Invalid operation: {operation}',
            'valid_operations': ['add', 'subtract', 'multiply', 'divide'],
        }

    if a is None or b is None:
        return {
            'status': 'error',
            'error': 'Missing parameters: a and b are required',
        }

    try:
        a = float(a)
        b = float(b)
    except (ValueError, TypeError):
        return {
            'status': 'error',
            'error': 'Parameters a and b must be numbers',
        }

    # Perform operation
    if operation == 'add':
        result = a + b
    elif operation == 'subtract':
        result = a - b
    elif operation == 'multiply':
        result = a * b
    elif operation == 'divide':
        if b == 0:
            return {
                'status': 'error',
                'error': 'Division by zero',
            }
        result = a / b

    return {
        'status': 'ok',
        'operation': operation,
        'a': a,
        'b': b,
        'result': result,
    }


__endpoint__ = {
    'name': 'calculator',
    'description': 'Calculator endpoint with validation',
    'version': '1.0.0',
    'author': 'test',
}

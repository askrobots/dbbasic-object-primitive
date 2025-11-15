"""
04_calculator.py - Calculator with validation
"""

_logger = None
_state_manager = None


def GET(request):
    """
    Perform arithmetic operations.

    Request format:
        {
            'a': <number>,
            'b': <number>,
            'operation': 'add' | 'subtract' | 'multiply' | 'divide'
        }
    """

    # Validate input
    validation_error = _validate_input(request)
    if validation_error:
        if _logger:
            _logger.error(
                'Validation failed',
                error=validation_error,
                request=request,
            )
        return {'status': 'error', 'message': validation_error}

    # Extract validated values
    a = request['a']
    b = request['b']
    operation = request['operation']

    # Perform calculation
    try:
        result = _calculate(a, b, operation)

        # Track usage
        if _state_manager:
            usage = _state_manager.get('usage_count', 0)
            _state_manager.set('usage_count', usage + 1)

        # Log success
        if _logger:
            _logger.info(
                'Calculation performed',
                a=a,
                b=b,
                operation=operation,
                result=result,
            )

        return {
            'status': 'ok',
            'result': result,
            'operation': f'{a} {_get_symbol(operation)} {b} = {result}',
        }

    except Exception as e:
        # Log error
        if _logger:
            _logger.error(
                'Calculation failed',
                error=str(e),
                a=a,
                b=b,
                operation=operation,
            )

        return {
            'status': 'error',
            'message': str(e),
        }


def POST(request):
    """Get usage statistics"""

    if _state_manager:
        usage_count = _state_manager.get('usage_count', 0)
    else:
        usage_count = 0

    return {
        'status': 'ok',
        'usage_count': usage_count,
        'message': f'Calculator used {usage_count} times',
    }


def _validate_input(request):
    """Validate request input. Returns error message or None."""

    # Check required fields
    if 'a' not in request:
        return 'Missing required field: a'

    if 'b' not in request:
        return 'Missing required field: b'

    if 'operation' not in request:
        return 'Missing required field: operation'

    # Validate types
    try:
        float(request['a'])
    except (ValueError, TypeError):
        return f"Field 'a' must be a number, got: {request['a']}"

    try:
        float(request['b'])
    except (ValueError, TypeError):
        return f"Field 'b' must be a number, got: {request['b']}"

    # Validate operation
    valid_operations = ['add', 'subtract', 'multiply', 'divide']
    if request['operation'] not in valid_operations:
        return f"Invalid operation: {request['operation']}. Valid: {valid_operations}"

    # Division by zero check
    if request['operation'] == 'divide' and float(request['b']) == 0:
        return 'Cannot divide by zero'

    return None  # All valid


def _calculate(a, b, operation):
    """Perform the calculation"""
    a = float(a)
    b = float(b)

    if operation == 'add':
        return a + b
    elif operation == 'subtract':
        return a - b
    elif operation == 'multiply':
        return a * b
    elif operation == 'divide':
        return a / b
    else:
        raise ValueError(f'Unknown operation: {operation}')


def _get_symbol(operation):
    """Get math symbol for operation"""
    symbols = {
        'add': '+',
        'subtract': '-',
        'multiply': '×',
        'divide': '÷',
    }
    return symbols.get(operation, '?')


__endpoint__ = {
    'name': 'calculator',
    'description': 'Arithmetic calculator with validation',
    'version': '1.0.0',
    'author': 'tutorial',
    'methods': ['GET', 'POST'],
}

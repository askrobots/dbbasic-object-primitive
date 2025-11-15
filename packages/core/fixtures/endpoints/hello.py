"""
Simple hello world endpoint for testing
"""


def GET(request):
    """Return a simple greeting"""
    return {
        'status': 'ok',
        'message': 'Hello, World!',
        'method': 'GET',
    }


def POST(request):
    """Return a personalized greeting"""
    name = request.get('name', 'World')
    return {
        'status': 'ok',
        'message': f'Hello, {name}!',
        'method': 'POST',
    }


__endpoint__ = {
    'name': 'hello',
    'description': 'Simple hello world endpoint for testing',
    'version': '1.0.0',
    'author': 'test',
}

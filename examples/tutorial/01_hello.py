"""
01_hello.py - The simplest object
"""


def GET(request):
    """Return a greeting"""
    return {
        'status': 'ok',
        'message': 'Hello from the Object Primitive System!',
    }

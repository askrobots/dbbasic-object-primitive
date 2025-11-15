"""
API handler for listing all objects

GET /objects - List all available objects
"""
import json
from pathlib import Path
from dbbasic_web.responses import json as json_response, json_error


def GET(request):
    """List all available objects"""
    # Find all .py files in examples directory
    examples_dir = Path('examples')

    if not examples_dir.exists():
        return json_response(json.dumps({
            'status': 'ok',
            'objects': [],
            'count': 0,
            'message': 'No objects found (examples directory does not exist)',
        }))

    objects = []

    # Scan for .py files
    for py_file in examples_dir.rglob('*.py'):
        # Skip __init__.py and __pycache__
        if py_file.name == '__init__.py' or '__pycache__' in str(py_file):
            continue

        # Get relative path from examples/
        rel_path = py_file.relative_to(examples_dir)
        object_id = str(rel_path).replace('.py', '').replace('/', '_')

        objects.append({
            'object_id': object_id,
            'path': str(rel_path),
            'file': str(py_file),
        })

    # Sort by object_id
    objects.sort(key=lambda x: x['object_id'])

    return json_response(json.dumps({
        'status': 'ok',
        'objects': objects,
        'count': len(objects),
    }))

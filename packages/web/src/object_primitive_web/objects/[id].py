"""
API handler for individual objects

GET /objects/{id} - Execute object's GET method
GET /objects/{id}?source=true - View object's source code
GET /objects/{id}?metadata=true - View object metadata
GET /objects/{id}?logs=true - View object logs
GET /objects/{id}?versions=true - View version history
GET /objects/{id}?version=N - Get specific version

POST /objects/{id} - Execute object's POST method
POST /objects/{id} (action=rollback) - Rollback to specific version
PUT /objects/{id} - Execute object's PUT method or update code
DELETE /objects/{id} - Execute object's DELETE method
"""
import json
from pathlib import Path
from dbbasic_web.responses import json as json_response, json_error

from object_primitive_core.object_runtime import ObjectRuntime


# Initialize runtime (shared across requests)
_runtime = None


def get_runtime():
    """Get or create the ObjectRuntime instance"""
    global _runtime
    if _runtime is None:
        _runtime = ObjectRuntime(base_dir='./data')
    return _runtime


def find_object_file(object_id: str) -> Path | None:
    """Find object file by ID"""
    # Convert object_id back to path
    # basics_counter -> basics/counter.py
    # tutorial_03_counter -> tutorial/03_counter.py

    examples_dir = Path('examples')

    # Try direct path first
    parts = object_id.split('_', 1)
    if len(parts) == 2:
        subdir, filename = parts
        py_file = examples_dir / subdir / f'{filename}.py'
        if py_file.exists():
            return py_file

    # Try as single file
    py_file = examples_dir / f'{object_id}.py'
    if py_file.exists():
        return py_file

    # Scan for match
    for py_file in examples_dir.rglob('*.py'):
        if py_file.name == '__init__.py' or '__pycache__' in str(py_file):
            continue

        rel_path = py_file.relative_to(examples_dir)
        found_id = str(rel_path).replace('.py', '').replace('/', '_')

        if found_id == object_id:
            return py_file

    return None


def GET(request, id: str):
    """
    Get object information or execute GET method

    Query parameters:
    - source: Return source code
    - metadata: Return metadata
    - logs: Return logs
    - versions: Return version history
    - (default): Execute GET method
    """
    # Find object file
    obj_file = find_object_file(id)
    if not obj_file:
        return json_error(f'Object not found: {id}', status=404)

    # Load object
    try:
        runtime = get_runtime()
        obj = runtime.load_object(str(obj_file))
    except Exception as e:
        return json_error(f'Failed to load object: {e}', status=500)

    # Check query parameters
    query = request.GET

    # View source code
    if query.get('source') == 'true':
        try:
            source = obj.get_source_code()
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': id,
                'source': source,
            }))
        except Exception as e:
            return json_error(f'Failed to get source: {e}', status=500)

    # View metadata
    if query.get('metadata') == 'true':
        try:
            metadata = obj.get_metadata()
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': id,
                'metadata': metadata,
            }))
        except Exception as e:
            return json_error(f'Failed to get metadata: {e}', status=500)

    # View logs
    if query.get('logs') == 'true':
        try:
            level = query.get('level')  # Optional log level filter
            limit_str = query.get('limit', '100')
            limit = int(limit_str) if limit_str else 100

            logs = obj.get_logs(level=level, limit=limit)
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': id,
                'logs': logs,
                'count': len(logs),
            }))
        except Exception as e:
            return json_error(f'Failed to get logs: {e}', status=500)

    # View version history
    if query.get('versions') == 'true':
        try:
            limit_str = query.get('limit', '10')
            limit = int(limit_str) if limit_str else 10

            history = obj.get_version_history(limit=limit)
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': id,
                'versions': history,
                'count': len(history),
            }))
        except Exception as e:
            return json_error(f'Failed to get version history: {e}', status=500)

    # Get specific version
    if query.get('version'):
        try:
            version_id = int(query.get('version'))
            version_data = obj.get_version(version_id)

            if not version_data:
                return json_error(f'Version not found: {version_id}', status=404)

            return json_response(json.dumps({
                'status': 'ok',
                'object_id': id,
                'version': version_data,
            }))
        except ValueError:
            return json_error('Invalid version number', status=400)
        except Exception as e:
            return json_error(f'Failed to get version: {e}', status=500)

    # Execute GET method (default)
    try:
        # Build request data from query parameters
        req_data = dict(query)

        result = obj.execute('GET', req_data)
        return json_response(json.dumps(result))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return json_error(f'Execution failed: {e}\n\n{tb}', status=500)


def POST(request, id: str):
    """Execute object's POST method"""
    # Find object file
    obj_file = find_object_file(id)
    if not obj_file:
        return json_error(f'Object not found: {id}', status=404)

    # Load object
    try:
        runtime = get_runtime()
        obj = runtime.load_object(str(obj_file))
    except Exception as e:
        return json_error(f'Failed to load object: {e}', status=500)

    # Parse request body as JSON
    try:
        if request.body:
            req_data = json.loads(request.body.decode('utf-8'))
        else:
            # Fall back to form data or query params
            req_data = dict(request.POST) if request.POST else dict(request.GET)
    except json.JSONDecodeError as e:
        return json_error(f'Invalid JSON: {e}', status=400)

    # Check for special actions
    action = req_data.get('action')

    # Rollback to specific version
    if action == 'rollback':
        try:
            version_id = req_data.get('version_id')
            if not version_id:
                return json_error('version_id required for rollback', status=400)

            version_id = int(version_id)
            author = req_data.get('author', 'api_user')
            message = req_data.get('message', f'Rollback to version {version_id}')

            obj.rollback_to_version(version_id, author=author, message=message)

            return json_response(json.dumps({
                'status': 'ok',
                'message': f'Rolled back to version {version_id}',
                'version_id': version_id,
            }))
        except ValueError as e:
            return json_error(f'Invalid version_id: {e}', status=400)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return json_error(f'Rollback failed: {e}\n\n{tb}', status=500)

    # Execute POST method (default)
    try:
        result = obj.execute('POST', req_data)
        return json_response(json.dumps(result))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return json_error(f'Execution failed: {e}\n\n{tb}', status=500)


def PUT(request, id: str):
    """Execute object's PUT method or update code"""
    # Find object file
    obj_file = find_object_file(id)
    if not obj_file:
        return json_error(f'Object not found: {id}', status=404)

    # Load object
    try:
        runtime = get_runtime()
        obj = runtime.load_object(str(obj_file))
    except Exception as e:
        return json_error(f'Failed to load object: {e}', status=500)

    # Check if this is a code update
    query = request.GET
    if query.get('source') == 'true':
        # Update source code
        try:
            if not request.body:
                return json_error('Missing request body', status=400)

            data = json.loads(request.body.decode('utf-8'))

            new_code = data.get('code')
            author = data.get('author', 'api')
            message = data.get('message', 'Updated via API')

            if not new_code:
                return json_error('Missing field: code', status=400)

            version_id = obj.update_code(
                new_code=new_code,
                author=author,
                message=message,
            )

            return json_response(json.dumps({
                'status': 'ok',
                'message': f'Code updated to version {version_id}',
                'version_id': version_id,
                'object_id': id,
            }))
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return json_error(f'Update failed: {e}\n\n{tb}', status=500)

    # Execute PUT method (default)
    try:
        if request.body:
            req_data = json.loads(request.body.decode('utf-8'))
        else:
            req_data = dict(request.POST) if request.POST else dict(request.GET)

        result = obj.execute('PUT', req_data)
        return json_response(json.dumps(result))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return json_error(f'Execution failed: {e}\n\n{tb}', status=500)


def DELETE(request, id: str):
    """Execute object's DELETE method"""
    # Find object file
    obj_file = find_object_file(id)
    if not obj_file:
        return json_error(f'Object not found: {id}', status=404)

    # Load object
    try:
        runtime = get_runtime()
        obj = runtime.load_object(str(obj_file))
    except Exception as e:
        return json_error(f'Failed to load object: {e}', status=500)

    # Parse request data
    try:
        if request.body:
            req_data = json.loads(request.body.decode('utf-8'))
        else:
            req_data = dict(request.POST) if request.POST else dict(request.GET)
    except json.JSONDecodeError as e:
        return json_error(f'Invalid JSON: {e}', status=400)

    # Execute DELETE method
    try:
        result = obj.execute('DELETE', req_data)
        return json_response(json.dumps(result))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return json_error(f'Execution failed: {e}\n\n{tb}', status=500)

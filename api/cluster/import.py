"""
Object Import API

POST /cluster/import - Receive object files from another station

Used by the migration system to receive files during object migration.
This endpoint is called by the source station to push files to the destination.

Example:
    POST /cluster/import
    {
        "object_id": "calculator",
        "code_file": "examples/calculator.py",
        "code_content": "<base64>",
        "state_files": {
            "state.tsv": "<base64>",
            "logs.tsv": "<base64>"
        },
        "version_files": {
            "v1.txt": "<base64>",
            "metadata.tsv": "<base64>"
        }
    }

    Response:
    {
        "status": "ok",
        "message": "Object imported successfully",
        "files_copied": {
            "code": "examples/calculator.py",
            "state": ["state.tsv", "logs.tsv"],
            "versions": 1
        }
    }
"""
import json
import base64
from pathlib import Path
from dbbasic_web.responses import json as json_response, json_error


def POST(request):
    """
    Import object files from another station

    Request body:
        {
            "object_id": str,
            "code_file": str,                  # Path where code should be written
            "code_content": str,               # Base64-encoded code
            "state_files": {                   # Base64-encoded state files
                "state.tsv": str,
                "logs.tsv": str,
                ...
            },
            "version_files": {                 # Base64-encoded version files
                "v1.txt": str,
                "metadata.tsv": str,
                ...
            }
        }

    Response:
        {
            "status": "ok",
            "message": "Object imported successfully",
            "files_copied": {
                "code": str,
                "state": [str],
                "versions": int
            }
        }

    Errors:
        400 - Missing required fields or invalid base64
        500 - File write failed
    """
    # Parse request body
    try:
        if request.body:
            data = json.loads(request.body.decode('utf-8'))
        else:
            return json_error('Missing request body', status=400)
    except json.JSONDecodeError as e:
        return json_error(f'Invalid JSON: {e}', status=400)

    # Validate required fields
    object_id = data.get('object_id')
    code_file_path = data.get('code_file')
    code_content_b64 = data.get('code_content')
    state_files_b64 = data.get('state_files', {})
    version_files_b64 = data.get('version_files', {})

    if not object_id:
        return json_error('object_id is required', status=400)
    if not code_file_path:
        return json_error('code_file is required', status=400)
    if not code_content_b64:
        return json_error('code_content is required', status=400)

    # Decode files
    try:
        code_content = base64.b64decode(code_content_b64)

        state_files = {
            name: base64.b64decode(content)
            for name, content in state_files_b64.items()
        }

        version_files = {
            name: base64.b64decode(content)
            for name, content in version_files_b64.items()
        }
    except Exception as e:
        return json_error(f'Failed to decode base64: {e}', status=400)

    # Write files to filesystem
    try:
        files_dict = {
            'code_file': code_file_path,
            'code_content': code_content,
            'state_files': state_files,
            'version_files': version_files
        }

        result = write_files(object_id, files_dict)

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        return json_error(f'Failed to write files: {e}\n\n{tb}', status=500)

    return json_response(json.dumps({
        'status': 'ok',
        'message': 'Object imported successfully',
        'files_copied': result['files_copied']
    }))


def write_files(object_id: str, files: dict) -> dict:
    """
    Write files to local filesystem

    Args:
        object_id: Object ID
        files: {
            'code_file': str,
            'code_content': bytes,
            'state_files': {name: bytes},
            'version_files': {rel_path: bytes}
        }

    Returns:
        {
            'files_copied': {
                'code': str,
                'state': [str],
                'versions': int
            }
        }
    """
    # Write code file
    code_file = Path(files['code_file'])
    code_file.parent.mkdir(parents=True, exist_ok=True)

    with open(code_file, 'wb') as f:
        f.write(files['code_content'])

    # Write state files
    state_dir = Path('data') / object_id
    state_dir.mkdir(parents=True, exist_ok=True)

    state_files_written = []
    for filename, content in files['state_files'].items():
        file_path = state_dir / filename
        with open(file_path, 'wb') as f:
            f.write(content)
        state_files_written.append(filename)

    # Write version files
    version_dir = Path('data/versions') / object_id
    version_dir.mkdir(parents=True, exist_ok=True)

    version_count = 0
    for rel_path, content in files['version_files'].items():
        file_path = version_dir / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'wb') as f:
            f.write(content)

        # Count actual version files (not metadata)
        if rel_path.endswith('.txt'):
            version_count += 1

    return {
        'files_copied': {
            'code': str(code_file),
            'state': state_files_written,
            'versions': version_count
        }
    }

"""
Object Migration API

POST /cluster/migrate - Migrate object from one station to another

Migrates an object by copying:
- Code file (examples/path/to/object.py)
- State directory (data/object_id/)
  - state.tsv
  - logs.tsv
  - versions/

Example:
    POST /cluster/migrate
    {
        "object_id": "calculator",
        "from_station": "station2",
        "to_station": "station3"
    }

    Response:
    {
        "status": "ok",
        "message": "Object migrated successfully",
        "object_id": "calculator",
        "from_station": "station2",
        "to_station": "station3",
        "files_copied": {
            "code": "examples/calculator.py",
            "state": ["state.tsv", "logs.tsv"],
            "versions": 5
        }
    }
"""
import json
import os
import time
import base64
import requests
from pathlib import Path
from dbbasic_web.responses import json as json_response, json_error


def POST(request):
    """
    Migrate object from one station to another

    Request body:
        {
            "object_id": str,        # Object to migrate
            "from_station": str,     # Source station ID
            "to_station": str,       # Destination station ID
            "copy_only": bool        # If true, don't delete from source (default: false)
        }

    Response:
        {
            "status": "ok",
            "message": "Object migrated successfully",
            "object_id": str,
            "from_station": str,
            "to_station": str,
            "files_copied": {
                "code": str,                    # Code file path
                "state": [str],                 # List of state files
                "versions": int                 # Number of versions copied
            },
            "duration_seconds": float
        }

    Errors:
        400 - Missing required fields
        404 - Object not found
        503 - Station not found or offline
        500 - Migration failed
    """
    start_time = time.time()

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
    from_station = data.get('from_station')
    to_station = data.get('to_station')
    copy_only = data.get('copy_only', False)

    if not object_id:
        return json_error('object_id is required', status=400)
    if not from_station:
        return json_error('from_station is required', status=400)
    if not to_station:
        return json_error('to_station is required', status=400)

    # Get local station ID
    local_station = os.environ.get('STATION_ID', 'unknown')

    # TODO: If this is not the master, forward to master
    # For now, assume this runs on master (station1)

    # Step 1: Collect files from source station
    try:
        source_files = collect_object_files(object_id, from_station, local_station)
    except FileNotFoundError as e:
        return json_error(f'Object not found: {e}', status=404)
    except Exception as e:
        return json_error(f'Failed to collect files from source: {e}', status=500)

    # Step 2: Send files to destination station
    try:
        result = send_files_to_station(object_id, source_files, to_station, local_station)
    except requests.RequestException as e:
        return json_error(f'Failed to send files to destination: {e}', status=503)
    except Exception as e:
        return json_error(f'Failed to send files: {e}', status=500)

    # Step 3: (Optional) Delete from source if not copy_only
    if not copy_only:
        # TODO: Implement source deletion
        pass

    duration = time.time() - start_time

    return json_response(json.dumps({
        'status': 'ok',
        'message': 'Object migrated successfully' if not copy_only else 'Object copied successfully',
        'object_id': object_id,
        'from_station': from_station,
        'to_station': to_station,
        'files_copied': result['files_copied'],
        'duration_seconds': round(duration, 3)
    }))


def collect_object_files(object_id: str, source_station: str, local_station: str) -> dict:
    """
    Collect all files for an object from source station

    Args:
        object_id: Object ID to collect
        source_station: Station where object currently lives
        local_station: This station's ID

    Returns:
        {
            'code_file': str,              # Path to code file
            'code_content': bytes,         # Code file content
            'state_files': {               # State files (path -> content)
                'state.tsv': bytes,
                'logs.tsv': bytes,
                ...
            },
            'version_files': {             # Version files (path -> content)
                'v1.txt': bytes,
                'v2.txt': bytes,
                'metadata.tsv': bytes
            }
        }
    """
    if source_station == local_station:
        # Local collection - read files directly
        return collect_local_files(object_id)
    else:
        # Remote collection - request files via HTTP
        return collect_remote_files(object_id, source_station)


def collect_local_files(object_id: str) -> dict:
    """Collect files from local filesystem"""
    import importlib.util

    # Load the [id].py module
    module_path = Path(__file__).parent.parent / 'objects' / '[id].py'
    spec = importlib.util.spec_from_file_location('objects_id_api', module_path)
    objects_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(objects_api)

    # Find object code file
    obj_file = objects_api.find_object_file(object_id)
    if not obj_file:
        raise FileNotFoundError(f'Object not found: {object_id}')

    # Read code file
    with open(obj_file, 'rb') as f:
        code_content = f.read()

    # Collect state files
    state_dir = Path('data') / object_id
    state_files = {}

    if state_dir.exists():
        for file_path in state_dir.iterdir():
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    rel_path = file_path.name
                    state_files[rel_path] = f.read()

    # Collect version files
    version_dir = Path('data/versions') / object_id
    version_files = {}

    if version_dir.exists():
        for file_path in version_dir.rglob('*'):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    rel_path = str(file_path.relative_to(version_dir))
                    version_files[rel_path] = f.read()

    return {
        'code_file': str(obj_file),
        'code_content': code_content,
        'state_files': state_files,
        'version_files': version_files
    }


def collect_remote_files(object_id: str, source_station: str) -> dict:
    """Collect files from remote station via HTTP"""
    import importlib.util

    # Load the [id].py module
    module_path = Path(__file__).parent.parent / 'objects' / '[id].py'
    spec = importlib.util.spec_from_file_location('objects_id_api', module_path)
    objects_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(objects_api)

    # Look up source station
    station_info = objects_api.get_station_info(source_station)

    if not station_info:
        raise ValueError(f'Station not found or offline: {source_station}')

    # Request files from source station
    # TODO: Create /cluster/export endpoint on source station
    # For now, raise NotImplementedError
    raise NotImplementedError('Remote file collection not yet implemented')


def send_files_to_station(object_id: str, files: dict, dest_station: str, local_station: str) -> dict:
    """
    Send files to destination station

    Args:
        object_id: Object ID
        files: Files dict from collect_object_files()
        dest_station: Destination station ID
        local_station: This station's ID

    Returns:
        {
            'files_copied': {
                'code': str,
                'state': [str],
                'versions': int
            }
        }
    """
    if dest_station == local_station:
        # Local write - write files directly
        return write_local_files(object_id, files)
    else:
        # Remote write - send files via HTTP
        return send_remote_files(object_id, files, dest_station)


def write_local_files(object_id: str, files: dict) -> dict:
    """Write files to local filesystem"""
    # Determine where to write code file
    # For now, write to examples/ directory
    code_file = Path(files['code_file'])

    # Create parent directory if needed
    code_file.parent.mkdir(parents=True, exist_ok=True)

    # Write code file
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
        if rel_path.endswith('.txt'):  # Count version files, not metadata
            version_count += 1

    return {
        'files_copied': {
            'code': str(code_file),
            'state': state_files_written,
            'versions': version_count
        }
    }


def send_remote_files(object_id: str, files: dict, dest_station: str) -> dict:
    """Send files to remote station via HTTP"""
    import importlib.util

    # Load the [id].py module
    module_path = Path(__file__).parent.parent / 'objects' / '[id].py'
    spec = importlib.util.spec_from_file_location('objects_id_api', module_path)
    objects_api = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(objects_api)

    # Look up destination station
    station_info = objects_api.get_station_info(dest_station)

    if not station_info:
        raise ValueError(f'Station not found or offline: {dest_station}')

    # Prepare payload (encode binary files as base64)
    payload = {
        'object_id': object_id,
        'code_file': files['code_file'],
        'code_content': base64.b64encode(files['code_content']).decode('utf-8'),
        'state_files': {
            name: base64.b64encode(content).decode('utf-8')
            for name, content in files['state_files'].items()
        },
        'version_files': {
            name: base64.b64encode(content).decode('utf-8')
            for name, content in files['version_files'].items()
        }
    }

    # Send to destination station
    url = f"{station_info['url']}/cluster/import"
    response = requests.post(url, json=payload, timeout=60)

    if response.status_code != 200:
        raise ValueError(f'Destination returned error: {response.status_code}')

    result = response.json()
    return result

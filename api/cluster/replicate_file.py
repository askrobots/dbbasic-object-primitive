"""
Cluster File Replication

POST /cluster/replicate_file - Receive file replication from another station

Used for high availability: when an object stores a file on station1,
it automatically replicates to station2 and station3. If station1 fails,
files can be accessed from replicas.
"""
import json
import os
import time
from pathlib import Path
from dbbasic_web.responses import json as json_response, json_error


def POST(request):
    """
    Receive file replication from another station

    Request (multipart/form-data):
        file: uploaded file data
        object_id: str (form field)
        filename: str (form field)
        source_station: str (form field)

    Response:
        {
            "status": "ok",
            "message": "File replicated",
            "object_id": str,
            "filename": str,
            "size": int
        }
    """
    # Get form data
    try:
        object_id = request.forms.get('object_id')
        filename = request.forms.get('filename')
        source_station = request.forms.get('source_station')
    except Exception as e:
        return json_error(f'Failed to parse form data: {e}', status=400)

    if not all([object_id, filename, source_station]):
        return json_error(
            'Missing required fields: object_id, filename, source_station',
            status=400
        )

    # Get uploaded file
    if not request.files or 'file' not in request.files:
        return json_error('No file uploaded', status=400)

    upload = request.files.get('file')
    file_content = upload.file.read()

    # Write to local file storage (replica)
    files_dir = Path(f'data/files/{object_id}')
    files_dir.mkdir(parents=True, exist_ok=True)
    file_path = files_dir / filename

    # Write file (last-write-wins, no timestamp checking needed for files)
    try:
        with open(file_path, 'wb') as f:
            f.write(file_content)
    except Exception as e:
        return json_error(f'Failed to write file: {e}', status=500)

    return json_response(json.dumps({
        'status': 'ok',
        'message': 'File replicated',
        'object_id': object_id,
        'filename': filename,
        'size': len(file_content),
        'source_station': source_station,
        'timestamp': time.time()
    }))


def GET(request):
    """
    Get file replication status for monitoring

    Response:
        {
            "status": "ok",
            "station_id": str,
            "message": "File replication endpoint active"
        }
    """
    station_id = os.environ.get('STATION_ID', 'unknown')

    return json_response(json.dumps({
        'status': 'ok',
        'station_id': station_id,
        'message': 'File replication endpoint active',
        'timestamp': time.time()
    }))

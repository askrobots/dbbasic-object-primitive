"""
Cluster Log Replication

POST /cluster/append_log - Receive log entry replication from another station

Used for distributed logging: when an object logs on station1, it automatically
replicates to station2 and station3 so all stations have complete audit trail.

Key difference from state replication:
- State: Last-write-wins (replace)
- Logs: Append-only (never overwrite)
"""
import json
import csv
from pathlib import Path
from dbbasic_web.responses import json as json_response, json_error


def POST(request):
    """
    Receive log entry from another station and append it

    Request body:
        {
            "object_id": str,
            "entry_id": str,  # Unique ID to prevent duplicates
            "log_entry": dict,  # Log entry with timestamp, level, message, etc.
            "source_station": str
        }

    Response:
        {
            "status": "ok" | "duplicate",
            "message": str,
            "object_id": str
        }
    """
    try:
        if request.body:
            data = json.loads(request.body.decode('utf-8'))
        else:
            return json_error('Request body required', status=400)
    except json.JSONDecodeError:
        return json_error('Invalid JSON', status=400)

    object_id = data.get('object_id')
    entry_id = data.get('entry_id')
    log_entry = data.get('log_entry')
    source_station = data.get('source_station')

    if not all([object_id, entry_id, log_entry, source_station]):
        return json_error(
            'Missing required fields: object_id, entry_id, log_entry, source_station',
            status=400
        )

    # Setup log directory
    log_dir = Path(f'data/logs/{object_id}')
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'log.tsv'

    # Check for duplicate (already have this entry_id)
    if _has_entry(log_file, entry_id):
        return json_response(json.dumps({
            'status': 'duplicate',
            'message': 'Log entry already exists',
            'object_id': object_id,
            'entry_id': entry_id
        }))

    # Append log entry
    _append_log_entry(log_file, entry_id, log_entry)

    return json_response(json.dumps({
        'status': 'ok',
        'message': 'Log entry appended',
        'object_id': object_id,
        'entry_id': entry_id,
        'source_station': source_station
    }))


def _has_entry(log_file: Path, entry_id: str) -> bool:
    """Check if log file already contains this entry_id"""
    if not log_file.exists():
        return False

    try:
        with open(log_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                if row.get('entry_id') == entry_id:
                    return True
    except:
        pass

    return False


def _append_log_entry(log_file: Path, entry_id: str, log_entry: dict) -> None:
    """Append log entry to file"""

    # Add entry_id to log entry
    entry = {'entry_id': entry_id, **log_entry}

    # Get existing fieldnames if file exists
    fieldnames = _get_fieldnames(log_file)

    # Add any new fields from this entry
    for key in entry.keys():
        if key not in fieldnames:
            fieldnames.append(key)

    # Append to file
    is_new_file = not log_file.exists()

    with open(log_file, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')

        if is_new_file:
            writer.writeheader()

        writer.writerow(entry)


def _get_fieldnames(log_file: Path) -> list:
    """Get existing fieldnames from log file"""
    if not log_file.exists():
        return ['entry_id', 'timestamp', 'level', 'message']

    try:
        with open(log_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            return list(reader.fieldnames or ['entry_id', 'timestamp', 'level', 'message'])
    except:
        return ['entry_id', 'timestamp', 'level', 'message']


def GET(request):
    """
    Get log replication status for monitoring

    Response:
        {
            "status": "ok",
            "message": "Log replication endpoint active"
        }
    """
    return json_response(json.dumps({
        'status': 'ok',
        'message': 'Log replication endpoint active'
    }))

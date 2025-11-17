"""
Cluster State Replication

POST /cluster/replicate - Receive state replication from another station

Used for high availability: when an object updates its state on station1,
it automatically replicates to station2 and station3. If station1 fails,
objects can read state from replicas.
"""
import json
import os
import time
from pathlib import Path
from dbbasic_web.responses import json as json_response, json_error


def POST(request):
    """
    Receive state replication from another station

    Request body:
        {
            "object_id": str,
            "key": str,
            "value": str,
            "timestamp": float,
            "source_station": str
        }

    Response:
        {
            "status": "ok",
            "message": "State replicated",
            "object_id": str,
            "key": str
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
    key = data.get('key')
    value = data.get('value')
    timestamp = data.get('timestamp')
    source_station = data.get('source_station')

    if not all([object_id, key, value is not None, timestamp, source_station]):
        return json_error(
            'Missing required fields: object_id, key, value, timestamp, source_station',
            status=400
        )

    # Write to local state (replica)
    state_dir = Path(f'data/state/{object_id}')
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / 'state.tsv'

    # Read existing state
    existing = {}
    if state_file.exists():
        with open(state_file, 'r') as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split('\t')
                    if len(parts) >= 3:
                        k, v, ts = parts[0], parts[1], float(parts[2])
                        existing[k] = (v, ts)

    # Check if we should accept this update (last-write-wins)
    if key in existing:
        _, existing_ts = existing[key]
        if timestamp <= existing_ts:
            # Existing value is newer, reject this update
            return json_response(json.dumps({
                'status': 'ok',
                'message': 'Replica already has newer value',
                'object_id': object_id,
                'key': key,
                'rejected': True
            }))

    # Update with new value
    existing[key] = (value, timestamp)

    # Write back to file
    with open(state_file, 'w') as f:
        for k, (v, ts) in sorted(existing.items()):
            f.write(f'{k}\t{v}\t{ts}\n')

    return json_response(json.dumps({
        'status': 'ok',
        'message': 'State replicated',
        'object_id': object_id,
        'key': key,
        'source_station': source_station,
        'timestamp': timestamp
    }))


def GET(request):
    """
    Get replication status for monitoring

    Response:
        {
            "status": "ok",
            "station_id": str,
            "message": "Replication endpoint active"
        }
    """
    station_id = os.environ.get('STATION_ID', 'unknown')

    return json_response(json.dumps({
        'status': 'ok',
        'station_id': station_id,
        'message': 'Replication endpoint active',
        'timestamp': time.time()
    }))

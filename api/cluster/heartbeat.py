"""
Cluster Heartbeat

POST /cluster/heartbeat - Send heartbeat to master

Workers send periodic heartbeats to master to stay in registry.
Master updates last_heartbeat timestamp for the station.
"""
import json
import os
import time
from pathlib import Path
from dbbasic_web.responses import json as json_response


def POST(request):
    """Send heartbeat to master"""
    # Parse JSON from request body
    try:
        if request.body:
            data = json.loads(request.body.decode('utf-8'))
        else:
            data = {}
    except json.JSONDecodeError:
        data = {}

    station_id = data.get('station_id')
    host = data.get('host')
    port = data.get('port', 8001)
    metrics = data.get('metrics', {})

    if not station_id or not host:
        return json_response(json.dumps({
            'status': 'error',
            'message': 'station_id and host are required'
        }))

    # Update registry with heartbeat
    data_dir = Path('data/cluster')
    data_dir.mkdir(parents=True, exist_ok=True)
    registry_file = data_dir / 'stations.tsv'

    current_time = time.time()

    # Read existing registry
    existing = {}
    if registry_file.exists():
        with open(registry_file, 'r') as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        sid = parts[0]
                        existing[sid] = parts

    # Update this station's heartbeat (with metrics as JSON in 5th column)
    metrics_json = json.dumps(metrics) if metrics else '{}'
    existing[station_id] = [station_id, host, str(port), str(current_time), metrics_json]

    # Write back
    with open(registry_file, 'w') as f:
        for sid, parts in sorted(existing.items()):
            f.write('\t'.join(parts) + '\n')

    return json_response(json.dumps({
        'status': 'ok',
        'message': 'Heartbeat received',
        'station_id': station_id,
        'timestamp': current_time
    }))


def GET(request):
    """Get heartbeat status (for monitoring)"""
    my_station_id = os.environ.get('STATION_ID', 'unknown')

    return json_response(json.dumps({
        'status': 'ok',
        'station_id': my_station_id,
        'timestamp': time.time(),
        'message': 'Heartbeat endpoint active'
    }))

"""
Cluster Stations Registry

GET /cluster/stations - List all active stations in the cluster
POST /cluster/stations - Register a new station

Master node maintains the registry of all stations.
Workers send heartbeats to stay in the registry.
"""
import json
import os
import time
from pathlib import Path
from dbbasic_web.responses import json as json_response


def GET(request):
    """List all active stations in the cluster"""
    station_id = os.environ.get('STATION_ID', 'unknown')

    # Read station registry from TSV
    data_dir = Path('data/cluster')
    data_dir.mkdir(parents=True, exist_ok=True)
    registry_file = data_dir / 'stations.tsv'

    stations = []
    current_time = time.time()

    if registry_file.exists():
        with open(registry_file, 'r') as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split('\t')
                    if len(parts) >= 4:
                        sid, host, port, last_heartbeat = parts[:4]
                        metrics_json = parts[4] if len(parts) > 4 else '{}'

                        # Parse metrics
                        try:
                            metrics = json.loads(metrics_json)
                        except:
                            metrics = {}

                        # Station is active if heartbeat within last 30 seconds
                        is_active = (current_time - float(last_heartbeat)) < 30

                        station_info = {
                            'station_id': sid,
                            'host': host,
                            'port': int(port),
                            'last_heartbeat': float(last_heartbeat),
                            'is_active': is_active,
                            'url': f'http://{host}:{port}'
                        }

                        # Add metrics if available
                        if metrics:
                            station_info['metrics'] = metrics

                        stations.append(station_info)

    # Always include ourselves if we're the master
    if station_id == 'station1':
        # Check if we're already in the list
        if not any(s['station_id'] == station_id for s in stations):
            stations.insert(0, {
                'station_id': station_id,
                'host': 'localhost',
                'port': 8001,
                'last_heartbeat': current_time,
                'is_active': True,
                'url': 'http://localhost:8001'
            })

    return json_response(json.dumps({
        'status': 'ok',
        'station_id': station_id,
        'is_master': station_id == 'station1',
        'stations': stations,
        'count': len(stations),
        'active_count': sum(1 for s in stations if s['is_active'])
    }))


def POST(request):
    """Register a station with the cluster"""
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

    if not station_id or not host:
        return json_response(json.dumps({
            'status': 'error',
            'message': 'station_id and host are required'
        }))

    # Write to registry
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

    # Update or add this station
    existing[station_id] = [station_id, host, str(port), str(current_time)]

    # Write back
    with open(registry_file, 'w') as f:
        for sid, parts in sorted(existing.items()):
            f.write('\t'.join(parts) + '\n')

    return json_response(json.dumps({
        'status': 'ok',
        'message': f'Station {station_id} registered',
        'station_id': station_id,
        'host': host,
        'port': port
    }))

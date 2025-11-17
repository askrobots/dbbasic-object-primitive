"""
Cluster Info

GET /cluster/info - Get information about this station

Returns station ID, role (master/worker), and cluster configuration.
"""
import json
import os
import socket
from dbbasic_web.responses import json as json_response


def GET(request):
    """Get information about this station"""
    station_id = os.environ.get('STATION_ID', 'unknown')
    is_master = station_id == 'station1'

    # Try to get local IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = '127.0.0.1'

    return json_response(json.dumps({
        'status': 'ok',
        'station_id': station_id,
        'is_master': is_master,
        'role': 'master' if is_master else 'worker',
        'host': local_ip,
        'port': 8001,
        'url': f'http://{local_ip}:8001',
        'cluster_endpoint': 'http://localhost:8001/cluster/stations' if is_master else None
    }))

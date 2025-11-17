#!/usr/bin/env python3
"""
Cluster Heartbeat Daemon

Runs on worker stations to send periodic heartbeats to master.

Usage:
    python cluster_heartbeat_daemon.py <master_host>

Example:
    python cluster_heartbeat_daemon.py localhost
    python cluster_heartbeat_daemon.py 192.0.2.1
"""
import os
import sys
import time
import socket
import requests
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None


def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return '127.0.0.1'


def get_load_metrics():
    """
    Collect current load metrics

    Returns:
        {
            'cpu_percent': float,      # CPU usage (0-100)
            'memory_percent': float,   # Memory usage (0-100)
            'memory_used_mb': float,   # Memory used in MB
            'memory_total_mb': float,  # Total memory in MB
            'object_count': int        # Number of objects available
        }
    """
    metrics = {}

    if psutil:
        # CPU usage (averaged over 1 second)
        metrics['cpu_percent'] = psutil.cpu_percent(interval=0.1)

        # Memory usage
        mem = psutil.virtual_memory()
        metrics['memory_percent'] = mem.percent
        metrics['memory_used_mb'] = round(mem.used / (1024 * 1024), 1)
        metrics['memory_total_mb'] = round(mem.total / (1024 * 1024), 1)
    else:
        # Fallback if psutil not available
        metrics['cpu_percent'] = 0
        metrics['memory_percent'] = 0
        metrics['memory_used_mb'] = 0
        metrics['memory_total_mb'] = 0

    # Count objects (count .py files in examples/)
    try:
        examples_dir = Path('examples')
        if examples_dir.exists():
            object_count = len([
                f for f in examples_dir.rglob('*.py')
                if f.name != '__init__.py' and '__pycache__' not in str(f)
            ])
            metrics['object_count'] = object_count
        else:
            metrics['object_count'] = 0
    except:
        metrics['object_count'] = 0

    return metrics


def get_version():
    """Read version from VERSION file"""
    try:
        version_file = Path('VERSION')
        if version_file.exists():
            return version_file.read_text().strip()
    except:
        pass
    return 'unknown'


def send_heartbeat(master_host, master_port, station_id, local_ip, station_port):
    """Send heartbeat to master with load metrics and version"""
    try:
        # Collect load metrics
        metrics = get_load_metrics()

        # Get version
        version = get_version()

        url = f'http://{master_host}:{master_port}/cluster/heartbeat'
        data = {
            'station_id': station_id,
            'host': local_ip,
            'port': station_port,
            'metrics': metrics,
            'version': version
        }
        response = requests.post(url, json=data, timeout=5)

        if response.status_code == 200:
            result = response.json()
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat sent: {result.get('message')}")
            return True
        else:
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Heartbeat error: {e}")
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Cluster Heartbeat Daemon")
    parser.add_argument("master_host", help="Master station hostname or IP")
    parser.add_argument("--master-port", type=int, default=8001, help="Master station port (default: 8001)")
    parser.add_argument("--station-port", type=int, default=8001, help="This station's port (default: 8001)")
    parser.add_argument("--station-id", help="Station ID (overrides STATION_ID env var)")
    args = parser.parse_args()

    master_host = args.master_host
    master_port = args.master_port
    station_port = args.station_port
    station_id = args.station_id or os.environ.get('STATION_ID')

    if not station_id:
        print("Error: STATION_ID not provided via --station-id or STATION_ID environment variable")
        sys.exit(1)

    if station_id == 'station1':
        print("This is the master station - no need to run heartbeat daemon")
        sys.exit(0)

    local_ip = get_local_ip()

    print("=" * 60)
    print("Cluster Heartbeat Daemon")
    print("=" * 60)
    print(f"Station ID: {station_id}")
    print(f"Local IP: {local_ip}")
    print(f"Station Port: {station_port}")
    print(f"Master: {master_host}:{master_port}")
    print(f"Heartbeat interval: 10 seconds")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    # Initial registration
    print(f"Registering with master...")
    send_heartbeat(master_host, master_port, station_id, local_ip, station_port)

    # Send heartbeats every 10 seconds
    try:
        while True:
            time.sleep(10)
            send_heartbeat(master_host, master_port, station_id, local_ip, station_port)
    except KeyboardInterrupt:
        print("\nHeartbeat daemon stopped")


if __name__ == "__main__":
    main()

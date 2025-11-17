#!/usr/bin/env python3
"""
Cluster configuration loader

Reads cluster.tsv to get station configuration for the distributed cluster.
Falls back to environment variables or defaults if config file doesn't exist.
"""

import os
import csv
from pathlib import Path
from typing import List, Dict, Optional


class ClusterConfig:
    """Load and manage cluster configuration"""

    def __init__(self, config_file: str = "cluster.tsv"):
        self.config_file = Path(config_file)
        self.stations = []
        self._load()

    def _load(self):
        """Load configuration from TSV file"""
        if not self.config_file.exists():
            # Fallback to single-station mode with environment variables
            self.stations = [{
                'station_id': os.environ.get('STATION_ID', 'station1'),
                'host': os.environ.get('STATION_HOST', 'localhost'),
                'port': int(os.environ.get('STATION_PORT', '8001')),
                'user': os.environ.get('STATION_USER', os.environ.get('USER', 'user')),
                'role': os.environ.get('STATION_ROLE', 'master')
            }]
            return

        # Read TSV file
        with open(self.config_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(
                (line for line in f if not line.startswith('#')),
                delimiter='\t'
            )

            for row in reader:
                # Skip empty rows
                if not row.get('station_id'):
                    continue

                self.stations.append({
                    'station_id': row['station_id'].strip(),
                    'host': row['host'].strip(),
                    'port': int(row['port']),
                    'user': row['user'].strip(),
                    'role': row['role'].strip()
                })

    def get_station(self, station_id: str) -> Optional[Dict]:
        """Get configuration for a specific station"""
        for station in self.stations:
            if station['station_id'] == station_id:
                return station
        return None

    def get_master(self) -> Optional[Dict]:
        """Get the master station configuration"""
        for station in self.stations:
            if station['role'] == 'master':
                return station
        return None

    def get_workers(self) -> List[Dict]:
        """Get all worker station configurations"""
        return [s for s in self.stations if s['role'] == 'worker']

    def get_all_stations(self) -> List[Dict]:
        """Get all station configurations"""
        return self.stations

    def get_ssh_target(self, station_id: str) -> Optional[str]:
        """Get SSH target string (user@host) for a station"""
        station = self.get_station(station_id)
        if station:
            return f"{station['user']}@{station['host']}"
        return None

    def get_url(self, station_id: str, path: str = "") -> Optional[str]:
        """Get full URL for a station"""
        station = self.get_station(station_id)
        if station:
            return f"http://{station['host']}:{station['port']}{path}"
        return None


# Global instance (lazy loaded)
_config = None


def get_config() -> ClusterConfig:
    """Get the global cluster configuration"""
    global _config
    if _config is None:
        _config = ClusterConfig()
    return _config


def reload_config():
    """Reload configuration from file"""
    global _config
    _config = ClusterConfig()


if __name__ == "__main__":
    # Test/debug the configuration
    config = get_config()

    print("Cluster Configuration:")
    print(f"Total stations: {len(config.stations)}")
    print()

    master = config.get_master()
    if master:
        print(f"Master: {master['station_id']} at {master['host']}:{master['port']}")

    workers = config.get_workers()
    if workers:
        print(f"Workers: {len(workers)}")
        for worker in workers:
            print(f"  - {worker['station_id']} at {worker['host']}:{worker['port']}")

    print()
    print("All stations:")
    for station in config.get_all_stations():
        print(f"  {station['station_id']}: {station['user']}@{station['host']}:{station['port']} ({station['role']})")

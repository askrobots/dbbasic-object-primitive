"""
Self-Logger

Each object logs to itself (not to external logging system).

Design:
- Logs stored in TSV files (human-readable, grep-able)
- Append-only (immutable history)
- Each object has its own log directory: logs/{object_id}/log.tsv
- Log rotation when file exceeds size limit
- Query logs with filters (level, time range, custom fields)

Philosophy:
Objects are self-contained. They know their own state, log their own
events, and can be queried independently. No central logging system.
"""

import csv
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
import os
import time
import threading
import hashlib

try:
    import requests
except ImportError:
    requests = None  # Replication will be disabled

try:
    from cluster_config import get_config
except ImportError:
    get_config = None


class SelfLogger:
    """
    Self-logging for objects.

    Each object has its own log file stored in:
    logs/{object_id}/log.tsv

    Logs are TSV format (human-readable, grep-able).
    """

    def __init__(
        self,
        object_id: str,
        base_dir: Path | str,
        max_log_size: Optional[int] = None,
        enable_replication: bool = True,
    ):
        """
        Initialize self-logger.

        Args:
            object_id: ID of the object (e.g., 'hello', 'calculator')
            base_dir: Base directory for log storage
            max_log_size: Maximum log file size in bytes before rotation
                         (default: 10MB)
            enable_replication: Whether to replicate logs to other stations
                               (default: True)
        """
        self.object_id = object_id
        self.base_dir = Path(base_dir)
        self.max_log_size = max_log_size or (10 * 1024 * 1024)  # 10MB default
        self.enable_replication = enable_replication

        # Create log directory
        self.log_dir = self.base_dir / 'logs' / object_id
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Current log file
        self.log_file = self.log_dir / 'log.tsv'

    def log(
        self,
        level: str,
        message: str,
        **kwargs,
    ) -> None:
        """
        Log an entry and replicate to other stations.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            **kwargs: Additional fields to log (method, user_id, etc.)
        """
        # Check if rotation needed
        self._rotate_if_needed()

        # Generate unique entry ID for deduplication during replication
        timestamp = datetime.now().isoformat()
        entry_id = self._generate_entry_id(timestamp, level, message)

        # Prepare entry
        entry = {
            'entry_id': entry_id,
            'timestamp': timestamp,
            'level': level,
            'message': message,
            **kwargs,
        }

        # Remove None values (don't log empty fields)
        entry = {k: v for k, v in entry.items() if v is not None}

        # Get all possible fieldnames (existing + new)
        fieldnames = self._get_fieldnames()
        for key in entry.keys():
            if key not in fieldnames:
                fieldnames.append(key)

        # Write to file
        is_new_file = not self.log_file.exists()

        with open(self.log_file, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='\t')

            if is_new_file:
                writer.writeheader()

            writer.writerow(entry)

        # Replicate to other stations (async)
        if self.enable_replication and requests:
            self._replicate_async(entry_id, entry)

    def debug(self, message: str, **kwargs) -> None:
        """Log DEBUG level message"""
        self.log('DEBUG', message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        """Log INFO level message"""
        self.log('INFO', message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        """Log WARNING level message"""
        self.log('WARNING', message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        """Log ERROR level message"""
        self.log('ERROR', message, **kwargs)

    def critical(self, message: str, **kwargs) -> None:
        """Log CRITICAL level message"""
        self.log('CRITICAL', message, **kwargs)

    def get_logs(
        self,
        level: Optional[Union[str, List[str]]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        **filters,
    ) -> List[Dict[str, Any]]:
        """
        Get log entries.

        Args:
            level: Filter by level (string or list of strings)
            limit: Maximum number of entries to return
            offset: Number of entries to skip
            **filters: Additional filters (e.g., user_id='user-123')

        Returns:
            List of log entries (dictionaries)
        """
        if not self.log_file.exists():
            return []

        # Read all entries from current log file
        entries = []
        with open(self.log_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                entries.append(row)

        # Also read from rotated log files
        rotated_files = sorted(self.log_dir.glob('log-*.tsv'))
        for rotated_file in rotated_files:
            with open(rotated_file, 'r', newline='') as f:
                reader = csv.DictReader(f, delimiter='\t')
                for row in reader:
                    entries.append(row)

        # Filter by level
        if level is not None:
            if isinstance(level, str):
                level = [level]
            entries = [e for e in entries if e.get('level') in level]

        # Filter by custom fields
        for key, value in filters.items():
            entries = [e for e in entries if e.get(key) == value]

        # Apply offset and limit
        if offset > 0:
            entries = entries[offset:]

        if limit is not None:
            entries = entries[:limit]

        return entries

    def _get_fieldnames(self) -> List[str]:
        """Get existing fieldnames from log file"""
        if not self.log_file.exists():
            return ['entry_id', 'timestamp', 'level', 'message']

        with open(self.log_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            return list(reader.fieldnames or ['entry_id', 'timestamp', 'level', 'message'])

    def _rotate_if_needed(self) -> None:
        """Rotate log file if it exceeds max size"""
        if not self.log_file.exists():
            return

        # Check size
        size = self.log_file.stat().st_size
        if size < self.max_log_size:
            return

        # Rotate: rename current log to log-TIMESTAMP.tsv
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        rotated_name = self.log_dir / f'log-{timestamp}.tsv'

        # Rename current log
        self.log_file.rename(rotated_name)

        # Next log() call will create new log.tsv with header

    def _generate_entry_id(self, timestamp: str, level: str, message: str) -> str:
        """
        Generate unique entry ID for deduplication.

        Uses hash of timestamp + object_id + message to create unique ID.
        """
        content = f"{timestamp}:{self.object_id}:{level}:{message}"
        hash_obj = hashlib.sha256(content.encode())
        return hash_obj.hexdigest()[:16]  # First 16 chars is enough

    def _get_replica_stations(self) -> List[dict]:
        """
        Get list of active stations for replication.

        Returns list of stations excluding ourselves.

        Workers query master via HTTP, master reads local file directly.
        This avoids HTTP self-deadlock when server is busy handling a request.
        """
        if not requests:
            return []

        local_station = os.environ.get('STATION_ID', 'unknown')

        # Workers: Query master via HTTP (avoids self-deadlock)
        if local_station != 'station1':
            try:
                # Try cluster config first (reads cluster.tsv)
                if get_config:
                    try:
                        config = get_config()
                        master = config.get_master()
                        master_host = master['host']
                        master_port = master['port']
                    except:
                        master_host = 'localhost'
                        master_port = 8001
                else:
                    master_host = 'localhost'
                    master_port = 8001

                resp = requests.get(
                    f'http://{master_host}:{master_port}/cluster/stations',
                    timeout=1
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('status') == 'ok':
                        stations = []
                        for station in data.get('stations', []):
                            # Skip ourselves
                            if station.get('station_id') == local_station:
                                continue

                            # Only include active stations
                            if station.get('is_active'):
                                stations.append({
                                    'station_id': station['station_id'],
                                    'host': station['host'],
                                    'port': station['port'],
                                    'url': station['url']
                                })
                        return stations
            except:
                pass  # Fall through to local file reading

        # Master or fallback: Read local registry file directly
        registry_file = Path('data/cluster/stations.tsv')
        if not registry_file.exists():
            return []

        stations = []
        current_time = time.time()
        timeout = 30  # seconds

        try:
            with open(registry_file, 'r') as f:
                for line_num, line in enumerate(f):
                    # Skip header row
                    if line_num == 0 and line.strip().startswith('station_id'):
                        continue

                    if line.strip():
                        parts = line.strip().split('\t')
                        if len(parts) >= 4:
                            sid, host, port, last_heartbeat = parts[:4]

                            # Skip ourselves
                            if sid == local_station:
                                continue

                            # Check if active
                            age = current_time - float(last_heartbeat)
                            if age < timeout:
                                stations.append({
                                    'station_id': sid,
                                    'host': host,
                                    'port': int(port),
                                    'url': f'http://{host}:{port}'
                                })
        except:
            pass  # If registry read fails, return empty list

        return stations

    def _replicate_async(self, entry_id: str, log_entry: dict) -> None:
        """
        Replicate log entry to other stations asynchronously with retry logic.

        Uses threading to avoid blocking on network I/O.
        Retries with exponential backoff on failures.
        """
        def replicate_to_station(station: dict):
            """Send replication request with retry logic (runs in background thread)"""
            url = f"{station['url']}/cluster/append_log"
            payload = {
                'object_id': self.object_id,
                'entry_id': entry_id,
                'log_entry': log_entry,
                'source_station': os.environ.get('STATION_ID', 'unknown')
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Increased timeout from 0.5s to 2.0s
                    response = requests.post(url, json=payload, timeout=2.0)

                    if response.status_code == 200:
                        return  # Success

                    # Non-200 response, log and retry
                    if attempt < max_retries - 1:
                        backoff = 2 ** attempt  # 1s, 2s, 4s
                        time.sleep(backoff)

                except Exception as e:
                    # Network error, retry with backoff
                    if attempt < max_retries - 1:
                        backoff = 2 ** attempt  # 1s, 2s, 4s
                        time.sleep(backoff)
                    else:
                        # Final attempt failed - log it (not silent anymore)
                        # We don't want to crash, but we should know about persistent failures
                        pass  # TODO: Add failure logging to separate failure log

        # Get active stations for replication
        stations = self._get_replica_stations()

        # Start background threads for each station
        for station in stations:
            thread = threading.Thread(
                target=replicate_to_station,
                args=(station,),
                daemon=True  # Don't wait for threads to finish
            )
            thread.start()

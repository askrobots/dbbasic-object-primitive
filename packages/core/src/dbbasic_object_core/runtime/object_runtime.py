"""
Object Runtime

Integrates all core primitives into a unified runtime for Object Primitives.

An Object is:
- Code (executable endpoint)
- Logs (self-logging)
- Versions (automatic versioning)
- State (persistent state)
- Network-accessible (can be called remotely)

The runtime:
- Loads objects from files
- Injects logger and state manager
- Executes methods
- Logs all operations
- Versions code changes
- Provides introspection
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import importlib.util
import sys
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor

try:
    import requests
except ImportError:
    requests = None  # Replication will be disabled

try:
    from cluster_config import get_config
except ImportError:
    get_config = None

# Global thread pool for replication (shared across all managers)
# Limits concurrent replication threads to prevent "can't start new thread" errors
_replication_executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="repl")

from dbbasic_object_core.core.endpoint_loader import load_endpoint, execute_endpoint
from dbbasic_object_core.core.self_logger import SelfLogger
from dbbasic_object_core.core.version_manager import VersionManager
import shutil
import hashlib


class ObjectRuntime:
    """
    Runtime for Object Primitives.

    Provides integrated execution environment for objects.
    """

    def __init__(self, base_dir: Path | str):
        """
        Initialize runtime.

        Args:
            base_dir: Base directory for logs, versions, state
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Loaded objects cache
        self._objects: Dict[str, 'ObjectPrimitive'] = {}

        # Scheduler for periodic execution
        self._schedules: Dict[str, List[Dict]] = {}  # object_id -> [{method, interval, next_run}, ...]
        self._scheduler_running = False
        self._scheduler_thread = None
        self._start_scheduler()

    def load_object(self, path: str | Path, object_id: str = None) -> 'ObjectPrimitive':
        """
        Load an object from file.

        Args:
            path: Path to object file (.py)
            object_id: Optional object ID (defaults to filename stem)

        Returns:
            ObjectPrimitive instance
        """
        path = Path(path)

        # Use provided object_id or derive from filename
        if object_id is None:
            object_id = path.stem  # Filename without extension

        # Check cache
        if object_id in self._objects:
            return self._objects[object_id]

        # Create object
        obj = ObjectPrimitive(
            object_id=object_id,
            source_path=path,
            runtime=self,
        )

        # Cache it
        self._objects[object_id] = obj

        return obj

    def _start_scheduler(self) -> None:
        """Start the background scheduler thread"""
        if not self._scheduler_running:
            self._scheduler_running = True
            self._scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True,
                name="ObjectScheduler"
            )
            self._scheduler_thread.start()

    def _scheduler_loop(self) -> None:
        """Background thread that executes scheduled tasks"""
        while self._scheduler_running:
            now = time.time()

            # Check all scheduled tasks
            for object_id, schedules in list(self._schedules.items()):
                for schedule in schedules:
                    if schedule['next_run'] <= now:
                        # Execute the scheduled method
                        try:
                            obj = self._objects.get(object_id)
                            if obj:
                                method_name = schedule['method']
                                if hasattr(obj.endpoint, method_name):
                                    method = getattr(obj.endpoint, method_name)
                                    method()  # Call the scheduled method

                                    # Update next run time
                                    schedule['next_run'] = now + schedule['interval']
                        except Exception as e:
                            # Log error but don't crash scheduler
                            pass

            # Sleep for 1 second
            time.sleep(1)

    def schedule(self, object_id: str, method_name: str, interval_seconds: float) -> None:
        """
        Schedule a method to run periodically

        Args:
            object_id: ID of the object
            method_name: Name of the method to call
            interval_seconds: How often to run (in seconds)
        """
        if object_id not in self._schedules:
            self._schedules[object_id] = []

        # Check if already scheduled
        for schedule in self._schedules[object_id]:
            if schedule['method'] == method_name:
                # Update interval
                schedule['interval'] = interval_seconds
                schedule['next_run'] = time.time() + interval_seconds
                return

        # Add new schedule
        self._schedules[object_id].append({
            'method': method_name,
            'interval': interval_seconds,
            'next_run': time.time() + interval_seconds
        })

    def unschedule(self, object_id: str, method_name: Optional[str] = None) -> None:
        """
        Remove scheduled execution

        Args:
            object_id: ID of the object
            method_name: Method to unschedule (None = all methods)
        """
        if object_id not in self._schedules:
            return

        if method_name is None:
            # Remove all schedules for this object
            self._schedules[object_id] = []
        else:
            # Remove specific method
            self._schedules[object_id] = [
                s for s in self._schedules[object_id]
                if s['method'] != method_name
            ]

    def get_schedules(self, object_id: str) -> List[Dict]:
        """Get active schedules for an object"""
        return self._schedules.get(object_id, [])


class StateManager:
    """
    Simple state manager for object state.

    Stores state in TSV file for persistence.
    Automatically replicates state to other stations for high availability.
    """

    def __init__(self, object_id: str, base_dir: Path, enable_replication: bool = True):
        """
        Initialize state manager.

        Args:
            object_id: ID of the object
            base_dir: Base directory for state storage
            enable_replication: Whether to enable state replication (default: True)
        """
        self.object_id = object_id
        self.base_dir = Path(base_dir)
        self.enable_replication = enable_replication

        # State directory
        self.state_dir = self.base_dir / 'state' / object_id
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # State file (simple JSON-like format in TSV)
        self.state_file = self.state_dir / 'state.tsv'

        # Load state
        self._state = self._load_state()

    def get(self, key: str, default: Any = None) -> Any:
        """Get state value"""
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        Set state value and replicate to other stations

        Replication is async (fire-and-forget) and includes timestamp
        for last-write-wins conflict resolution.
        """
        self._state[key] = value
        timestamp = time.time()

        self._save_state_with_timestamp(timestamp)

        # Replicate async to other stations
        if self.enable_replication and requests:
            self._replicate_async(key, value, timestamp)

    def delete(self, key: str) -> None:
        """Delete state value"""
        if key in self._state:
            del self._state[key]
            timestamp = time.time()
            self._save_state_with_timestamp(timestamp)

    def get_all(self) -> Dict[str, Any]:
        """Get all state"""
        return self._state.copy()

    def _get_replica_stations(self) -> List[dict]:
        """
        Get list of active stations for replication

        Fetches from master station's /cluster/stations endpoint
        Returns list of stations excluding ourselves
        """
        if not requests:
            return []

        local_station = os.environ.get('STATION_ID', 'unknown')

        try:
            # If we're the master station, read registry file directly to avoid self-HTTP-call deadlock
            if local_station == 'station1':
                registry_file = self.base_dir / 'cluster' / 'stations.tsv'
                all_stations = []

                if registry_file.exists():
                    with open(registry_file, 'r') as f:
                        for line in f:
                            if line.strip() and not line.startswith('station_id'):
                                parts = line.strip().split('\t')
                                if len(parts) >= 3:
                                    station_id, host, port = parts[0], parts[1], int(parts[2])
                                    last_heartbeat = float(parts[3]) if len(parts) > 3 else 0

                                    # Station is active if heartbeat within last 30 seconds
                                    import time
                                    is_active = (time.time() - last_heartbeat) < 30

                                    url = f"http://{host}:{port}"
                                    all_stations.append({
                                        'station_id': station_id,
                                        'host': host,
                                        'port': port,
                                        'is_active': is_active,
                                        'url': url
                                    })
            else:
                # Worker station - fetch from master via HTTP
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

                master_url = f'http://{master_host}:{master_port}'
                response = requests.get(f'{master_url}/cluster/stations', timeout=2)

                if response.status_code != 200:
                    return []

                data = response.json()
                all_stations = data.get('stations', [])

            # Filter to only active stations, excluding ourselves
            stations = []
            for station in all_stations:
                # Skip ourselves
                if station.get('station_id') == local_station:
                    continue

                # Only include active stations
                if station.get('is_active', False):
                    stations.append({
                        'station_id': station['station_id'],
                        'host': station['host'],
                        'port': station['port'],
                        'url': station['url']
                    })

            return stations

        except Exception as e:
            # If we can't reach master, fall back to empty list
            # (replication will be retried on next state change)
            return []

    def _replicate_async(self, key: str, value: Any, timestamp: float) -> None:
        """
        Replicate state to other stations asynchronously with retry logic

        Uses threading to avoid blocking on network I/O
        Retries with exponential backoff on failures
        """
        def replicate_to_station(station: dict):
            """Send replication request with retry logic (runs in background thread)"""
            url = f"{station['url']}/cluster/replicate"
            payload = {
                'object_id': self.object_id,
                'key': key,
                'value': str(value),
                'timestamp': timestamp,
                'source_station': os.environ.get('STATION_ID', 'unknown')
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Increased timeout from 0.5s to 2.0s
                    response = requests.post(url, json=payload, timeout=2.0)

                    if response.status_code == 200:
                        return  # Success

                    # Non-200 response, retry with backoff
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

        # Submit replication tasks to thread pool (limits concurrent threads)
        for station in stations:
            _replication_executor.submit(replicate_to_station, station)

    def _load_state(self) -> Dict[str, Any]:
        """
        Load state from file

        Supports both old format (key\tvalue) and new format (key\tvalue\ttimestamp)
        """
        if not self.state_file.exists():
            return {}

        state = {}
        with open(self.state_file, 'r') as f:
            for line in f:
                if line.strip():
                    parts = line.strip().split('\t')

                    # Skip header line if present
                    if parts[0] == 'key':
                        continue

                    if len(parts) >= 2:
                        key = parts[0]
                        value = parts[1]

                        # Try to convert to int/float
                        try:
                            value = int(value)
                        except ValueError:
                            try:
                                value = float(value)
                            except ValueError:
                                pass  # Keep as string

                        state[key] = value

        return state

    def _save_state(self) -> None:
        """Save state to file (backward compatible, no timestamp)"""
        self._save_state_with_timestamp(time.time())

    def _save_state_with_timestamp(self, timestamp: float) -> None:
        """
        Save state to file with timestamp

        Format: key \t value \t timestamp
        Timestamp used for last-write-wins conflict resolution
        """
        with open(self.state_file, 'w') as f:
            for key, value in sorted(self._state.items()):
                f.write(f'{key}\t{value}\t{timestamp}\n')


class FileManager:
    """
    File storage manager for objects.

    Stores files in data/files/{object_id}/ directory.
    Automatically replicates files to other stations.
    """

    def __init__(self, object_id: str, base_dir: Path, enable_replication: bool = True):
        """
        Initialize file manager.

        Args:
            object_id: ID of the object
            base_dir: Base directory for file storage
            enable_replication: Whether to enable file replication (default: True)
        """
        self.object_id = object_id
        self.base_dir = Path(base_dir)
        self.enable_replication = enable_replication

        # File directory
        self.files_dir = self.base_dir / 'files' / object_id
        self.files_dir.mkdir(parents=True, exist_ok=True)

    def put(self, filename: str, content: bytes) -> None:
        """
        Store a file

        Args:
            filename: Name of the file
            content: File contents as bytes
        """
        file_path = self.files_dir / filename

        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)

        # Replicate to other stations
        if self.enable_replication and requests:
            self._replicate_async(filename, content)

    def get(self, filename: str) -> bytes:
        """
        Retrieve a file

        Args:
            filename: Name of the file

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self.files_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f'File not found: {filename}')

        with open(file_path, 'rb') as f:
            return f.read()

    def delete(self, filename: str) -> None:
        """
        Delete a file

        Args:
            filename: Name of the file
        """
        file_path = self.files_dir / filename

        if file_path.exists():
            file_path.unlink()

    def list(self) -> list:
        """
        List all files

        Returns:
            List of dicts with file metadata: [{name, size, modified}, ...]
        """
        files = []

        for file_path in self.files_dir.iterdir():
            if file_path.is_file():
                stat = file_path.stat()
                files.append({
                    'name': file_path.name,
                    'size': stat.st_size,
                    'modified': stat.st_mtime
                })

        return files

    def exists(self, filename: str) -> bool:
        """Check if file exists"""
        return (self.files_dir / filename).exists()

    def _get_replica_stations(self) -> List[dict]:
        """
        Get list of active stations for replication

        Uses same logic as StateManager
        """
        if not requests:
            return []

        local_station = os.environ.get('STATION_ID', 'unknown')

        try:
            # If we're the master station, read registry file directly
            if local_station == 'station1':
                registry_file = self.base_dir / 'cluster' / 'stations.tsv'
                all_stations = []

                if registry_file.exists():
                    with open(registry_file, 'r') as f:
                        for line in f:
                            if line.strip() and not line.startswith('station_id'):
                                parts = line.strip().split('\t')
                                if len(parts) >= 3:
                                    station_id, host, port = parts[0], parts[1], int(parts[2])
                                    last_heartbeat = float(parts[3]) if len(parts) > 3 else 0

                                    is_active = (time.time() - last_heartbeat) < 30

                                    url = f"http://{host}:{port}"
                                    all_stations.append({
                                        'station_id': station_id,
                                        'host': host,
                                        'port': port,
                                        'is_active': is_active,
                                        'url': url
                                    })
            else:
                # Worker station - fetch from master via HTTP
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

                master_url = f'http://{master_host}:{master_port}'
                response = requests.get(f'{master_url}/cluster/stations', timeout=2)

                if response.status_code != 200:
                    return []

                data = response.json()
                all_stations = data.get('stations', [])

            # Filter to only active stations, excluding ourselves
            stations = []
            for station in all_stations:
                if station.get('station_id') == local_station:
                    continue

                if station.get('is_active', False):
                    stations.append({
                        'station_id': station['station_id'],
                        'host': station['host'],
                        'port': station['port'],
                        'url': station['url']
                    })

            return stations

        except Exception as e:
            return []

    def _replicate_async(self, filename: str, content: bytes) -> None:
        """
        Replicate file to other stations asynchronously

        Uses threading to avoid blocking on network I/O
        """
        def replicate_to_station(station: dict):
            """Send file to station (runs in background thread)"""
            url = f"{station['url']}/cluster/replicate_file"

            files = {'file': (filename, content)}
            data = {
                'object_id': self.object_id,
                'filename': filename,
                'source_station': os.environ.get('STATION_ID', 'unknown')
            }

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = requests.post(url, files=files, data=data, timeout=5.0)

                    if response.status_code == 200:
                        return  # Success

                    if attempt < max_retries - 1:
                        backoff = 2 ** attempt
                        time.sleep(backoff)

                except Exception as e:
                    if attempt < max_retries - 1:
                        backoff = 2 ** attempt
                        time.sleep(backoff)

        # Get active stations for replication
        stations = self._get_replica_stations()

        # Submit replication tasks to thread pool (limits concurrent threads)
        for station in stations:
            _replication_executor.submit(replicate_to_station, station)


class ObjectPrimitive:
    """
    An Object Primitive.

    Combines:
    - Code (executable)
    - Logs (self-logging)
    - Versions (code history)
    - State (persistent state)
    """

    def __init__(
        self,
        object_id: str,
        source_path: Path,
        runtime: ObjectRuntime,
    ):
        """
        Initialize object.

        Args:
            object_id: Unique ID for this object
            source_path: Path to source file
            runtime: Parent runtime
        """
        self.object_id = object_id
        self.source_path = Path(source_path)
        self.runtime = runtime

        # Initialize primitives
        self.logger = SelfLogger(
            object_id=object_id,
            base_dir=runtime.base_dir,
        )

        self.version_manager = VersionManager(
            base_dir=runtime.base_dir,
        )

        self.state_manager = StateManager(
            object_id=object_id,
            base_dir=runtime.base_dir,
        )

        self.file_manager = FileManager(
            object_id=object_id,
            base_dir=runtime.base_dir,
        )

        # Load the endpoint
        self._load_endpoint()

        # Save initial version
        self._save_initial_version()

    def _load_endpoint(self, reload: bool = False) -> None:
        """Load endpoint from file"""
        self.endpoint = load_endpoint(self.source_path, reload=reload)

        # Inject logger, state manager, file manager, and runtime into module
        if hasattr(self.endpoint, '__dict__'):
            self.endpoint._logger = self.logger
            self.endpoint._state_manager = self.state_manager
            self.endpoint._files = self.file_manager
            self.endpoint._runtime = self.runtime  # Enable object composition

            # Inject schedule helper function
            def schedule(interval_seconds: float, method_name: str) -> None:
                """Schedule this object's method to run periodically"""
                self.runtime.schedule(self.object_id, method_name, interval_seconds)

            def unschedule(method_name: str = None) -> None:
                """Stop scheduled execution"""
                self.runtime.unschedule(self.object_id, method_name)

            self.endpoint._schedule = schedule
            self.endpoint._unschedule = unschedule

    def _save_initial_version(self) -> None:
        """Save initial version of code"""
        # Check if any versions exist
        history = self.version_manager.get_history(self.object_id)
        if not history:
            # Save v1
            source_code = self.source_path.read_text()
            self.version_manager.save_version(
                object_id=self.object_id,
                content=source_code,
                author='system',
                message='Initial version',
            )

    def execute(self, method: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a method on this object.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            request: Request data

        Returns:
            Response data
        """
        # Log the execution
        self.logger.info(
            f'Executing {method}',
            method=method,
            user_id=request.get('user_id'),
            request_id=request.get('request_id'),
        )

        try:
            # Execute
            result = execute_endpoint(self.endpoint, method, request)

            # Log success
            self.logger.debug(
                f'{method} completed successfully',
                method=method,
                status='success',
            )

            return result

        except Exception as e:
            # Log error
            self.logger.error(
                f'{method} failed: {str(e)}',
                method=method,
                status='error',
                error=str(e),
            )
            raise

    def update_code(self, new_code: str, author: str, message: str) -> int:
        """
        Update object's code.

        Args:
            new_code: New source code
            author: Who is making the change
            message: Commit message

        Returns:
            New version ID
        """
        # Save current version
        version_id = self.version_manager.save_version(
            object_id=self.object_id,
            content=new_code,
            author=author,
            message=message,
        )

        # Write new code to file
        self.source_path.write_text(new_code)

        # Reload endpoint (force reload to bypass cache)
        self._load_endpoint(reload=True)

        # Log the update
        self.logger.warning(
            'Code updated',
            author=author,
            commit_message=message,
            version=version_id,
        )

        return version_id

    def rollback_to_version(
        self,
        version_id: int,
        author: str,
        message: str,
    ) -> int:
        """
        Rollback to a previous version.

        Args:
            version_id: Version to rollback to
            author: Who is performing the rollback
            message: Rollback message

        Returns:
            New version ID (rollback creates new version)
        """
        # Rollback via version manager
        new_version_id = self.version_manager.rollback(
            object_id=self.object_id,
            to_version=version_id,
            author=author,
            message=message,
        )

        # Get the rolled-back code
        version = self.version_manager.get_version(self.object_id, new_version_id)
        code = version['content']

        # Write to file
        self.source_path.write_text(code)

        # Reload endpoint (force reload to bypass cache)
        self._load_endpoint(reload=True)

        # Log the rollback
        self.logger.critical(
            f'Rolled back to version {version_id}',
            author=author,
            commit_message=message,
            from_version=version_id,
            to_version=new_version_id,
        )

        return new_version_id

    def get_logs(
        self,
        level: Optional[str] = None,
        limit: Optional[int] = None,
        **filters,
    ) -> List[Dict[str, Any]]:
        """Get object's logs"""
        return self.logger.get_logs(level=level, limit=limit, **filters)

    def get_state(self) -> Dict[str, Any]:
        """Get object's current state"""
        return self.state_manager.get_all()

    def get_metadata(self) -> Dict[str, Any]:
        """Get object metadata"""
        from dbbasic_object_core.core.endpoint_loader import get_endpoint_metadata

        metadata = get_endpoint_metadata(self.endpoint)

        # Add runtime metadata
        metadata['object_id'] = self.object_id
        metadata['source_path'] = str(self.source_path)
        metadata['log_count'] = len(self.get_logs())
        metadata['version_count'] = len(self.get_version_history())
        metadata['state_keys'] = list(self.get_state().keys())

        return metadata

    def get_source_code(self) -> str:
        """Get object's source code"""
        return self.source_path.read_text()

    def get_version_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get version history"""
        return self.version_manager.get_history(self.object_id, limit=limit)

    def get_version(self, version_id: int) -> Optional[Dict[str, Any]]:
        """Get specific version"""
        return self.version_manager.get_version(self.object_id, version_id=version_id)

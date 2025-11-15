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

from .endpoint_loader import load_endpoint, execute_endpoint
from .self_logger import SelfLogger
from .version_manager import VersionManager


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

    def load_object(self, path: str | Path) -> 'ObjectPrimitive':
        """
        Load an object from file.

        Args:
            path: Path to object file (.py)

        Returns:
            ObjectPrimitive instance
        """
        path = Path(path)
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


class StateManager:
    """
    Simple state manager for object state.

    Stores state in TSV file for persistence.
    """

    def __init__(self, object_id: str, base_dir: Path):
        """
        Initialize state manager.

        Args:
            object_id: ID of the object
            base_dir: Base directory for state storage
        """
        self.object_id = object_id
        self.base_dir = Path(base_dir)

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
        """Set state value"""
        self._state[key] = value
        self._save_state()

    def delete(self, key: str) -> None:
        """Delete state value"""
        if key in self._state:
            del self._state[key]
            self._save_state()

    def get_all(self) -> Dict[str, Any]:
        """Get all state"""
        return self._state.copy()

    def _load_state(self) -> Dict[str, Any]:
        """Load state from file"""
        if not self.state_file.exists():
            return {}

        import csv
        state = {}
        with open(self.state_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                key = row['key']
                value = row['value']
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
        """Save state to file"""
        import csv
        with open(self.state_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['key', 'value'], delimiter='\t')
            writer.writeheader()
            for key, value in self._state.items():
                writer.writerow({'key': key, 'value': value})


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

        # Load the endpoint
        self._load_endpoint()

        # Save initial version
        self._save_initial_version()

    def _load_endpoint(self, reload: bool = False) -> None:
        """Load endpoint from file"""
        self.endpoint = load_endpoint(self.source_path, reload=reload)

        # Inject logger, state manager, and runtime into module
        if hasattr(self.endpoint, '__dict__'):
            self.endpoint._logger = self.logger
            self.endpoint._state_manager = self.state_manager
            self.endpoint._runtime = self.runtime  # Enable object composition

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
        from .endpoint_loader import get_endpoint_metadata

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

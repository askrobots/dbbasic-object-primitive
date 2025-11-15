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
    ):
        """
        Initialize self-logger.

        Args:
            object_id: ID of the object (e.g., 'hello', 'calculator')
            base_dir: Base directory for log storage
            max_log_size: Maximum log file size in bytes before rotation
                         (default: 10MB)
        """
        self.object_id = object_id
        self.base_dir = Path(base_dir)
        self.max_log_size = max_log_size or (10 * 1024 * 1024)  # 10MB default

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
        Log an entry.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            message: Log message
            **kwargs: Additional fields to log (method, user_id, etc.)
        """
        # Check if rotation needed
        self._rotate_if_needed()

        # Prepare entry
        entry = {
            'timestamp': datetime.now().isoformat(),
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
            return ['timestamp', 'level', 'message']

        with open(self.log_file, 'r', newline='') as f:
            reader = csv.DictReader(f, delimiter='\t')
            return reader.fieldnames or ['timestamp', 'level', 'message']

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

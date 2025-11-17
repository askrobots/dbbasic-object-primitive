#!/usr/bin/env python3
"""
Process Manager - PID file-based process management

Best practices:
- PID files prevent duplicate processes
- Clean shutdown using actual process IDs
- Automatic stale PID file cleanup
- Process status checking
"""
import os
import sys
import signal
import time
from pathlib import Path


class ProcessManager:
    """Manage processes using PID files"""

    def __init__(self, name: str, pid_dir: Path = None):
        """
        Initialize process manager

        Args:
            name: Process name (used for PID filename)
            pid_dir: Directory for PID files (default: ./pids/)
        """
        self.name = name
        self.pid_dir = pid_dir or Path('pids')
        self.pid_dir.mkdir(exist_ok=True)
        self.pid_file = self.pid_dir / f'{name}.pid'

    def is_running(self) -> bool:
        """Check if process is currently running"""
        if not self.pid_file.exists():
            return False

        try:
            pid = int(self.pid_file.read_text().strip())
            # Check if process exists
            os.kill(pid, 0)  # Signal 0 doesn't kill, just checks
            return True
        except (ValueError, ProcessLookupError, PermissionError):
            # PID file is stale (process doesn't exist)
            self._cleanup_stale_pid()
            return False

    def get_pid(self) -> int | None:
        """Get PID of running process (None if not running)"""
        if not self.pid_file.exists():
            return None

        try:
            pid = int(self.pid_file.read_text().strip())
            # Verify process exists
            os.kill(pid, 0)
            return pid
        except (ValueError, ProcessLookupError, PermissionError):
            self._cleanup_stale_pid()
            return None

    def write_pid(self, pid: int = None):
        """Write PID file for current or specified process"""
        if pid is None:
            pid = os.getpid()

        if self.is_running():
            existing_pid = self.get_pid()
            raise RuntimeError(
                f'{self.name} already running with PID {existing_pid}'
            )

        self.pid_file.write_text(str(pid))

    def stop(self, timeout: int = 10) -> bool:
        """
        Stop process gracefully

        Args:
            timeout: Seconds to wait before force kill

        Returns:
            True if stopped successfully
        """
        pid = self.get_pid()
        if pid is None:
            print(f'{self.name} not running')
            return True

        print(f'Stopping {self.name} (PID {pid})...')

        try:
            # Try SIGTERM first (graceful shutdown)
            os.kill(pid, signal.SIGTERM)

            # Wait for process to exit
            for i in range(timeout * 10):
                try:
                    os.kill(pid, 0)  # Check if still running
                    time.sleep(0.1)
                except ProcessLookupError:
                    print(f'✓ {self.name} stopped')
                    self._cleanup_stale_pid()
                    return True

            # Force kill if still running
            print(f'Force killing {self.name}...')
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
            self._cleanup_stale_pid()
            print(f'✓ {self.name} force killed')
            return True

        except ProcessLookupError:
            # Already stopped
            self._cleanup_stale_pid()
            print(f'✓ {self.name} already stopped')
            return True
        except PermissionError:
            print(f'✗ Permission denied to stop {self.name} (PID {pid})')
            return False

    def restart(self):
        """Restart process (must be implemented by subclass)"""
        raise NotImplementedError('Subclass must implement restart()')

    def status(self) -> dict:
        """Get process status"""
        pid = self.get_pid()

        if pid is None:
            return {
                'name': self.name,
                'running': False,
                'pid': None,
            }

        return {
            'name': self.name,
            'running': True,
            'pid': pid,
            'pid_file': str(self.pid_file),
        }

    def _cleanup_stale_pid(self):
        """Remove stale PID file"""
        if self.pid_file.exists():
            self.pid_file.unlink()


def main():
    """CLI interface for process management"""
    if len(sys.argv) < 3:
        print('Usage: python process_manager.py <process_name> <command>')
        print('Commands: status, stop, pid')
        sys.exit(1)

    process_name = sys.argv[1]
    command = sys.argv[2]

    pm = ProcessManager(process_name)

    if command == 'status':
        status = pm.status()
        if status['running']:
            print(f'{process_name}: RUNNING (PID {status["pid"]})')
        else:
            print(f'{process_name}: NOT RUNNING')

    elif command == 'stop':
        pm.stop()

    elif command == 'pid':
        pid = pm.get_pid()
        if pid:
            print(pid)
        else:
            print('NOT RUNNING', file=sys.stderr)
            sys.exit(1)

    else:
        print(f'Unknown command: {command}')
        sys.exit(1)


if __name__ == '__main__':
    main()

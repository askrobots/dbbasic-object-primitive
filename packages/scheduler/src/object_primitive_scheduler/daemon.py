"""
Scheduler Daemon - Background process that executes scheduled tasks

This daemon:
- Polls for scheduled tasks every 10 seconds
- Checks if tasks are due to run
- Executes objects via ObjectRuntime
- Updates task status (last_run, next_run, run_count)
- Handles cron (recurring) and one-time tasks

Usage:
    dbbasic-objects-scheduler

Or programmatically:
    from object_primitive_scheduler.daemon import SchedulerDaemon
    daemon = SchedulerDaemon(data_dir='data')
    daemon.run_forever()
"""

import time
import json
import sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from croniter import croniter
except ImportError:
    print("Error: croniter not installed")
    print("Install with: pip install croniter")
    sys.exit(1)

from object_primitive_core.object_runtime import ObjectRuntime


class SchedulerDaemon:
    """Background daemon that executes scheduled tasks"""

    def __init__(self, data_dir: str = 'data', check_interval: int = 10):
        """
        Initialize scheduler daemon

        Args:
            data_dir: Directory for object runtime data
            check_interval: Seconds between checks (default 10)
        """
        self.data_dir = Path(data_dir)
        self.check_interval = check_interval
        self.runtime = ObjectRuntime(base_dir=self.data_dir)

        # Load scheduler object to access tasks
        self.scheduler_path = self._find_scheduler_object()
        if not self.scheduler_path:
            print("Warning: scheduler.py object not found")
            print("Place it in examples/ or provide custom path")

    def _find_scheduler_object(self) -> Optional[str]:
        """Find scheduler.py object"""
        # Check common locations
        candidates = [
            'examples/triggers/scheduler.py',
            'packages/scheduler/src/object_primitive_scheduler/scheduler.py',
        ]

        for path in candidates:
            if Path(path).exists():
                return path

        return None

    def run_forever(self):
        """Main loop - check for tasks and execute"""
        print("=" * 60)
        print("Scheduler Daemon Started")
        print("=" * 60)
        print(f"Data directory: {self.data_dir}")
        print(f"Check interval: {self.check_interval}s")
        print()

        while True:
            try:
                self._check_and_execute_tasks()
            except KeyboardInterrupt:
                print("\nShutting down scheduler daemon...")
                break
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                import traceback
                traceback.print_exc()

            time.sleep(self.check_interval)

    def _check_and_execute_tasks(self):
        """Check for tasks due to run and execute them"""
        now = datetime.now(timezone.utc)
        now_ts = int(now.timestamp())

        # Get all tasks from scheduler object
        tasks = self._get_all_tasks()

        for task in tasks:
            if task.get('status') != 'active':
                continue  # Skip cancelled/completed tasks

            # Check if task should run
            if self._should_execute(task, now, now_ts):
                self._execute_task(task, now_ts)

    def _should_execute(self, task: Dict[str, Any], now: datetime, now_ts: int) -> bool:
        """Determine if task should execute now"""
        task_type = task.get('type')

        if task_type == 'cron':
            # Cron task - check if schedule matches
            return self._should_execute_cron(task, now)

        elif task_type == 'onetime':
            # One-time task - check if scheduled time has passed
            return self._should_execute_onetime(task, now_ts)

        return False

    def _should_execute_cron(self, task: Dict[str, Any], now: datetime) -> bool:
        """Check if cron task should execute"""
        schedule = task.get('schedule')
        last_run = task.get('last_run')

        try:
            cron = croniter(schedule, now)

            # Get previous execution time
            prev = cron.get_prev(datetime)

            if last_run is None:
                # Never run before - execute if prev time was recent (within check interval + buffer)
                time_since_prev = (now - prev).total_seconds()
                return time_since_prev <= (self.check_interval + 60)

            else:
                # Check if prev execution is after last_run
                last_run_dt = datetime.fromtimestamp(last_run, tz=timezone.utc)
                return prev > last_run_dt

        except Exception as e:
            print(f"Error checking cron schedule for task {task.get('id')}: {e}")
            return False

    def _should_execute_onetime(self, task: Dict[str, Any], now_ts: int) -> bool:
        """Check if one-time task should execute"""
        if task.get('executed'):
            return False  # Already executed

        schedule = task.get('schedule')

        try:
            # Parse ISO datetime
            scheduled_dt = datetime.fromisoformat(schedule.replace('Z', '+00:00'))
            scheduled_ts = int(scheduled_dt.timestamp())

            # Execute if scheduled time has passed
            return now_ts >= scheduled_ts

        except Exception as e:
            print(f"Error parsing schedule for task {task.get('id')}: {e}")
            return False

    def _execute_task(self, task: Dict[str, Any], now_ts: int):
        """Execute a scheduled task"""
        task_id = task.get('id')
        object_id = task.get('object_id')
        method = task.get('method', 'POST')
        payload = task.get('payload', {})

        print(f"[{datetime.now()}] Executing task {task_id}: {object_id}.{method}")

        try:
            # Find object file
            object_path = self._find_object_file(object_id)
            if not object_path:
                print(f"  Error: Object file not found: {object_id}")
                return

            # Load and execute object
            obj = self.runtime.load_object(str(object_path))
            result = obj.execute(method, payload)

            # Update task status
            task['last_run'] = now_ts
            task['run_count'] = task.get('run_count', 0) + 1

            if task.get('type') == 'onetime':
                task['executed'] = True
                task['status'] = 'completed'

            self._save_task(task)

            print(f"  Success: {result.get('status', 'ok')}")

        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

            # Update error count
            task['error_count'] = task.get('error_count', 0) + 1
            task['last_error'] = str(e)
            self._save_task(task)

    def _find_object_file(self, object_id: str) -> Optional[Path]:
        """Find object file by ID"""
        # Convert object_id to path
        # e.g. "basics_counter" -> "examples/basics/counter.py"
        parts = object_id.split('_', 1)

        if len(parts) == 2:
            subdir, filename = parts
            candidates = [
                Path('examples') / subdir / f'{filename}.py',
                Path(f'{subdir}/{filename}.py'),
            ]

            for path in candidates:
                if path.exists():
                    return path

        # Try direct path
        direct = Path(f'{object_id}.py')
        if direct.exists():
            return direct

        return None

    def _get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from scheduler object"""
        if not self.scheduler_path:
            return []

        try:
            # Load scheduler object
            scheduler = self.runtime.load_object(self.scheduler_path)

            # Get tasks via GET method
            result = scheduler.execute('GET', {})

            if result.get('status') == 'ok':
                return result.get('tasks', [])

        except Exception as e:
            print(f"Error getting tasks: {e}")

        return []

    def _save_task(self, task: Dict[str, Any]):
        """Save updated task back to scheduler object"""
        if not self.scheduler_path:
            return

        try:
            # Load scheduler object
            scheduler = self.runtime.load_object(self.scheduler_path)

            # Access state manager directly to update task
            state_mgr = scheduler.state_manager
            task_id = task['id']
            state_mgr.set(f'task_{task_id}', json.dumps(task))

        except Exception as e:
            print(f"Error saving task: {e}")


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Scheduler Daemon for Object Primitives')
    parser.add_argument('--data-dir', default='data', help='Data directory (default: data)')
    parser.add_argument('--interval', type=int, default=10, help='Check interval in seconds (default: 10)')

    args = parser.parse_args()

    daemon = SchedulerDaemon(data_dir=args.data_dir, check_interval=args.interval)
    daemon.run_forever()


if __name__ == '__main__':
    main()

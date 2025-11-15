"""
Tests for Scheduler package

Tests scheduler.py (REST API) and daemon.py (background execution)
"""

import pytest
import json
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone


class TestSchedulerAPI:
    """Test scheduler REST API (scheduler.py)"""

    @pytest.fixture
    def scheduler_obj(self, tmp_path):
        """Load scheduler object"""
        from object_primitive_core.object_runtime import ObjectRuntime

        # Create runtime with temp directory
        runtime = ObjectRuntime(base_dir=str(tmp_path))

        # Load scheduler object
        scheduler_path = 'examples/triggers/scheduler.py'
        obj = runtime.load_object(scheduler_path)

        return obj

    def test_create_cron_task(self, scheduler_obj):
        """Should create cron task"""
        result = scheduler_obj.execute('POST', {
            'object_id': 'cleanup',
            'schedule': '0 2 * * *',  # Daily at 2am
            'payload': {'max_age_days': 30},
        })

        assert result['status'] == 'ok'
        assert 'task_id' in result
        assert 'Task scheduled' in result['message']

    def test_create_onetime_task(self, scheduler_obj):
        """Should create one-time task"""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        schedule = future_time.isoformat()

        result = scheduler_obj.execute('POST', {
            'object_id': 'report_generator',
            'schedule': schedule,
            'payload': {'report_type': 'weekly'},
        })

        assert result['status'] == 'ok'
        assert 'task_id' in result

    def test_invalid_schedule_rejected(self, scheduler_obj):
        """Should reject invalid schedule"""
        result = scheduler_obj.execute('POST', {
            'object_id': 'cleanup',
            'schedule': 'not a valid schedule',
            'payload': {},
        })

        assert result['status'] == 'error'
        assert 'Invalid schedule' in result['message']

    def test_missing_object_id_rejected(self, scheduler_obj):
        """Should reject missing object_id"""
        result = scheduler_obj.execute('POST', {
            'schedule': '0 2 * * *',
            'payload': {},
        })

        assert result['status'] == 'error'
        assert 'object_id is required' in result['message']

    def test_list_all_tasks(self, scheduler_obj):
        """Should list all tasks"""
        # Create a task
        scheduler_obj.execute('POST', {
            'object_id': 'cleanup',
            'schedule': '0 2 * * *',
            'payload': {},
        })

        # List tasks
        result = scheduler_obj.execute('GET', {})

        assert result['status'] == 'ok'
        assert 'tasks' in result
        assert len(result['tasks']) >= 1
        assert result['count'] >= 1

    def test_get_specific_task(self, scheduler_obj):
        """Should get specific task by ID"""
        # Create task
        create_result = scheduler_obj.execute('POST', {
            'object_id': 'cleanup',
            'schedule': '0 2 * * *',
            'payload': {'key': 'value'},
        })

        task_id = create_result['task_id']

        # Get task
        result = scheduler_obj.execute('GET', {'task_id': task_id})

        assert result['status'] == 'ok'
        assert result['task']['id'] == task_id
        assert result['task']['object_id'] == 'cleanup'
        assert result['task']['schedule'] == '0 2 * * *'

    def test_cancel_task(self, scheduler_obj):
        """Should cancel task"""
        # Create task
        create_result = scheduler_obj.execute('POST', {
            'object_id': 'cleanup',
            'schedule': '0 2 * * *',
            'payload': {},
        })

        task_id = create_result['task_id']

        # Cancel task
        result = scheduler_obj.execute('DELETE', {'task_id': task_id})

        assert result['status'] == 'ok'
        assert 'cancelled' in result['message']

        # Verify cancelled
        get_result = scheduler_obj.execute('GET', {'task_id': task_id})
        assert get_result['task']['status'] == 'cancelled'

    def test_task_persistence(self, scheduler_obj):
        """Tasks should persist in state"""
        # Create task
        create_result = scheduler_obj.execute('POST', {
            'object_id': 'cleanup',
            'schedule': '0 2 * * *',
            'payload': {'data': 'test'},
        })

        task_id = create_result['task_id']

        # Access state manager directly
        state_mgr = scheduler_obj.state_manager
        task_json = state_mgr.get(f'task_{task_id}')

        assert task_json is not None
        task = json.loads(task_json)
        assert task['id'] == task_id
        assert task['payload']['data'] == 'test'


class TestSchedulerDaemon:
    """Test scheduler daemon (daemon.py)"""

    @pytest.fixture
    def daemon(self, tmp_path):
        """Create scheduler daemon"""
        from object_primitive_scheduler.daemon import SchedulerDaemon

        # Create daemon with temp directory
        daemon = SchedulerDaemon(data_dir=str(tmp_path), check_interval=1)

        return daemon

    def test_daemon_initialization(self, daemon):
        """Should initialize daemon"""
        assert daemon is not None
        assert daemon.check_interval == 1

    def test_cron_schedule_detection(self, daemon):
        """Should detect when cron task should execute"""
        from datetime import datetime, timezone

        # Create task that should run now
        now = datetime.now(timezone.utc)

        # Task with schedule that just passed
        task = {
            'id': 'test123',
            'type': 'cron',
            'schedule': '* * * * *',  # Every minute
            'last_run': None,
        }

        should_run = daemon._should_execute_cron(task, now)
        assert should_run is True

    def test_cron_not_run_twice(self, daemon):
        """Should not run cron task twice in same period"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # Task that just ran
        task = {
            'id': 'test123',
            'type': 'cron',
            'schedule': '0 2 * * *',  # Daily at 2am
            'last_run': int(now.timestamp()),
        }

        should_run = daemon._should_execute_cron(task, now)
        assert should_run is False

    def test_onetime_schedule_detection(self, daemon):
        """Should detect when one-time task should execute"""
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)

        # Task scheduled in the past
        past_time = now - timedelta(minutes=5)
        task = {
            'id': 'test123',
            'type': 'onetime',
            'schedule': past_time.isoformat(),
            'executed': False,
        }

        should_run = daemon._should_execute_onetime(task, int(now.timestamp()))
        assert should_run is True

    def test_onetime_not_run_twice(self, daemon):
        """Should not run one-time task twice"""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)

        # Task already executed
        task = {
            'id': 'test123',
            'type': 'onetime',
            'schedule': '2025-01-01T12:00:00Z',
            'executed': True,
        }

        should_run = daemon._should_execute_onetime(task, int(now.timestamp()))
        assert should_run is False

    def test_onetime_future_not_run(self, daemon):
        """Should not run one-time task scheduled in future"""
        from datetime import datetime, timezone, timedelta

        now = datetime.now(timezone.utc)

        # Task scheduled in the future
        future_time = now + timedelta(hours=1)
        task = {
            'id': 'test123',
            'type': 'onetime',
            'schedule': future_time.isoformat(),
            'executed': False,
        }

        should_run = daemon._should_execute_onetime(task, int(now.timestamp()))
        assert should_run is False


class TestSchedulerIntegration:
    """Integration tests for scheduler + daemon"""

    @pytest.fixture
    def setup(self, tmp_path):
        """Setup scheduler object and daemon"""
        from object_primitive_core.object_runtime import ObjectRuntime
        from object_primitive_scheduler.daemon import SchedulerDaemon

        # Create runtime
        runtime = ObjectRuntime(base_dir=str(tmp_path))

        # Load scheduler object
        scheduler_path = 'examples/triggers/scheduler.py'
        scheduler_obj = runtime.load_object(scheduler_path)

        # Create daemon
        daemon = SchedulerDaemon(data_dir=str(tmp_path), check_interval=1)

        return {
            'runtime': runtime,
            'scheduler': scheduler_obj,
            'daemon': daemon,
            'tmp_path': tmp_path,
        }

    def test_create_and_list_via_daemon(self, setup):
        """Should create task and daemon should see it"""
        scheduler = setup['scheduler']
        daemon = setup['daemon']

        # Create task
        scheduler.execute('POST', {
            'object_id': 'cleanup',
            'schedule': '0 2 * * *',
            'payload': {},
        })

        # Daemon should see task
        tasks = daemon._get_all_tasks()
        assert len(tasks) >= 1
        assert tasks[0]['object_id'] == 'cleanup'

    def test_task_type_detection(self, setup):
        """Should correctly detect task types"""
        scheduler = setup['scheduler']

        # Cron task
        result1 = scheduler.execute('POST', {
            'object_id': 'cleanup',
            'schedule': '0 2 * * *',
            'payload': {},
        })

        task_id1 = result1['task_id']
        task1 = scheduler.execute('GET', {'task_id': task_id1})
        assert task1['task']['type'] == 'cron'

        # One-time task
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        result2 = scheduler.execute('POST', {
            'object_id': 'report',
            'schedule': future.isoformat(),
            'payload': {},
        })

        task_id2 = result2['task_id']
        task2 = scheduler.execute('GET', {'task_id': task_id2})
        assert task2['task']['type'] == 'onetime'

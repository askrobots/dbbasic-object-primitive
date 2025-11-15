"""
Scheduler Object - REST API for managing scheduled tasks

This object can be executed via HTTP to create, list, and cancel scheduled tasks.
The actual execution happens in daemon.py (background process).

Example usage:
    # Create cron task (every 6 hours)
    POST /objects/scheduler
    {
        "object_id": "cleanup",
        "schedule": "0 */6 * * *",
        "payload": {"max_age_days": 30}
    }

    # Create one-time task
    POST /objects/scheduler
    {
        "object_id": "report_generator",
        "schedule": "2025-12-01T14:30:00Z",
        "payload": {"report_type": "monthly"}
    }

    # List all scheduled tasks
    GET /objects/scheduler

    # Cancel task
    DELETE /objects/scheduler?task_id=abc123
"""

import time
import json
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# These will be injected by ObjectRuntime
_logger = None
_state_manager = None


def POST(request: Dict[str, Any]) -> Dict[str, Any]:
    """Create scheduled task"""
    object_id = request.get('object_id', '').strip()
    method = request.get('method', 'POST')
    schedule = request.get('schedule', '').strip()
    payload = request.get('payload', {})

    if not object_id:
        return {'status': 'error', 'message': 'object_id is required'}

    if not schedule:
        return {'status': 'error', 'message': 'schedule is required'}

    # Determine task type (cron vs one-time)
    task_type = _determine_task_type(schedule)

    if task_type == 'invalid':
        return {'status': 'error', 'message': f'Invalid schedule format: {schedule}'}

    # Create task
    task_id = secrets.token_hex(8)
    task = {
        'id': task_id,
        'object_id': object_id,
        'method': method,
        'schedule': schedule,
        'payload': payload,
        'type': task_type,
        'created_at': int(time.time()),
        'last_run': None,
        'next_run': None,  # Will be calculated by daemon
        'run_count': 0,
        'status': 'active',
    }

    # Save to state
    _save_task(task)

    if _logger:
        _logger.info('Scheduled task created',
                    task_id=task_id,
                    object_id=object_id,
                    schedule=schedule,
                    task_type=task_type)

    return {
        'status': 'ok',
        'task_id': task_id,
        'message': f'Task scheduled: {schedule}',
    }


def GET(request: Dict[str, Any]) -> Dict[str, Any]:
    """List scheduled tasks or get specific task"""
    task_id = request.get('task_id')

    if task_id:
        # Get specific task
        task = _get_task(task_id)
        if not task:
            return {'status': 'error', 'message': f'Task not found: {task_id}'}
        return {'status': 'ok', 'task': task}

    else:
        # List all tasks
        tasks = _get_all_tasks()

        # Filter by status if requested
        status_filter = request.get('status')
        if status_filter:
            tasks = [t for t in tasks if t.get('status') == status_filter]

        return {
            'status': 'ok',
            'tasks': tasks,
            'count': len(tasks),
        }


def DELETE(request: Dict[str, Any]) -> Dict[str, Any]:
    """Cancel scheduled task"""
    task_id = request.get('task_id', '').strip()

    if not task_id:
        return {'status': 'error', 'message': 'task_id is required'}

    task = _get_task(task_id)
    if not task:
        return {'status': 'error', 'message': f'Task not found: {task_id}'}

    # Mark as cancelled
    task['status'] = 'cancelled'
    task['cancelled_at'] = int(time.time())
    _save_task(task)

    if _logger:
        _logger.info('Scheduled task cancelled', task_id=task_id)

    return {
        'status': 'ok',
        'message': f'Task cancelled: {task_id}',
    }


# Helper functions

def _determine_task_type(schedule: str) -> str:
    """Determine if schedule is cron or one-time"""
    # Check if it looks like ISO timestamp (one-time)
    if 'T' in schedule or schedule.count('-') >= 2:
        try:
            # Try parsing as ISO datetime
            datetime.fromisoformat(schedule.replace('Z', '+00:00'))
            return 'onetime'
        except:
            pass

    # Check if it looks like cron (5 or 6 fields separated by spaces)
    parts = schedule.split()
    if len(parts) in [5, 6]:
        # Basic cron syntax check
        try:
            from croniter import croniter
            croniter(schedule)  # Will raise if invalid
            return 'cron'
        except:
            pass

    return 'invalid'


def _save_task(task: Dict[str, Any]) -> None:
    """Save task to state"""
    if not _state_manager:
        return

    task_id = task['id']
    _state_manager.set(f'task_{task_id}', json.dumps(task))


def _get_task(task_id: str) -> Optional[Dict[str, Any]]:
    """Get task from state"""
    if not _state_manager:
        return None

    task_json = _state_manager.get(f'task_{task_id}')
    if not task_json:
        return None

    return json.loads(task_json)


def _get_all_tasks() -> List[Dict[str, Any]]:
    """Get all tasks from state"""
    if not _state_manager:
        return []

    tasks = []
    all_state = _state_manager.get_all()

    for key, value in all_state.items():
        if key.startswith('task_'):
            task = json.loads(value)
            tasks.append(task)

    # Sort by created_at (newest first)
    tasks.sort(key=lambda t: t.get('created_at', 0), reverse=True)

    return tasks

"""
06_task_queue.py - Task queue with priorities
"""

import json
from datetime import datetime
from typing import List, Dict, Any

_logger = None
_state_manager = None


def POST(request):
    """
    Add a task to the queue.

    Request:
        {
            'title': 'Task title',
            'priority': 'HIGH' | 'NORMAL' | 'LOW',  # Optional, default: NORMAL
            'description': 'Task description'        # Optional
        }
    """

    # Validate
    if 'title' not in request:
        return {'status': 'error', 'message': 'Missing field: title'}

    title = request['title']
    priority = request.get('priority', 'NORMAL')
    description = request.get('description', '')

    # Validate priority
    valid_priorities = ['HIGH', 'NORMAL', 'LOW']
    if priority not in valid_priorities:
        return {
            'status': 'error',
            'message': f'Invalid priority: {priority}. Valid: {valid_priorities}',
        }

    # Create task
    tasks = _get_tasks()
    task_id = _get_next_task_id()

    task = {
        'task_id': task_id,
        'title': title,
        'description': description,
        'priority': priority,
        'status': 'PENDING',
        'created_at': datetime.now().isoformat(),
    }

    tasks.append(task)
    _save_tasks(tasks)

    if _logger:
        _logger.info('Task added', task_id=task_id, title=title, priority=priority)

    return {
        'status': 'ok',
        'message': f'Task added: {task_id}',
        'task': task,
    }


def GET(request):
    """
    Get tasks.

    Request:
        {}                            # Get all tasks
        {'status': 'PENDING'}         # Filter by status
        {'priority': 'HIGH'}          # Filter by priority
        {'task_id': 1}                # Get specific task
    """

    tasks = _get_tasks()

    # Filter by task_id
    if 'task_id' in request:
        task_id = int(request['task_id'])
        task = _find_task(tasks, task_id)

        if not task:
            return {'status': 'error', 'message': f'Task not found: {task_id}'}

        return {'status': 'ok', 'task': task}

    # Filter by status
    if 'status' in request:
        tasks = [t for t in tasks if t['status'] == request['status']]

    # Filter by priority
    if 'priority' in request:
        tasks = [t for t in tasks if t['priority'] == request['priority']]

    # Sort by priority (HIGH > NORMAL > LOW)
    priority_order = {'HIGH': 0, 'NORMAL': 1, 'LOW': 2}
    tasks_sorted = sorted(tasks, key=lambda t: priority_order[t['priority']])

    if _logger:
        _logger.info('Tasks retrieved', count=len(tasks_sorted), filters=request)

    return {
        'status': 'ok',
        'tasks': tasks_sorted,
        'count': len(tasks_sorted),
    }


def PUT(request):
    """
    Update task status.

    Request:
        {
            'task_id': 1,
            'status': 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED'
        }
    """

    if 'task_id' not in request:
        return {'status': 'error', 'message': 'Missing field: task_id'}

    if 'status' not in request:
        return {'status': 'error', 'message': 'Missing field: status'}

    task_id = int(request['task_id'])
    new_status = request['status']

    # Validate status
    valid_statuses = ['PENDING', 'IN_PROGRESS', 'COMPLETED', 'CANCELLED']
    if new_status not in valid_statuses:
        return {
            'status': 'error',
            'message': f'Invalid status: {new_status}. Valid: {valid_statuses}',
        }

    # Find task
    tasks = _get_tasks()
    task = _find_task(tasks, task_id)

    if not task:
        return {'status': 'error', 'message': f'Task not found: {task_id}'}

    # Update status
    old_status = task['status']
    task['status'] = new_status
    task['updated_at'] = datetime.now().isoformat()

    if new_status == 'COMPLETED':
        task['completed_at'] = datetime.now().isoformat()

    _save_tasks(tasks)

    if _logger:
        _logger.info(
            'Task status updated',
            task_id=task_id,
            old_status=old_status,
            new_status=new_status,
        )

    return {
        'status': 'ok',
        'message': f'Task {task_id} status: {old_status} → {new_status}',
        'task': task,
    }


def DELETE(request):
    """
    Delete a task.

    Request:
        {'task_id': 1}
    """

    if 'task_id' not in request:
        return {'status': 'error', 'message': 'Missing field: task_id'}

    task_id = int(request['task_id'])

    # Find and remove task
    tasks = _get_tasks()
    task = _find_task(tasks, task_id)

    if not task:
        return {'status': 'error', 'message': f'Task not found: {task_id}'}

    tasks = [t for t in tasks if t['task_id'] != task_id]
    _save_tasks(tasks)

    if _logger:
        _logger.warning('Task deleted', task_id=task_id, title=task['title'])

    return {
        'status': 'ok',
        'message': f'Task deleted: {task_id}',
        'task': task,
    }


def _get_tasks() -> List[Dict[str, Any]]:
    """Get all tasks from state"""
    if _state_manager:
        tasks_json = _state_manager.get('tasks', '[]')
        return json.loads(tasks_json)
    else:
        return []


def _save_tasks(tasks: List[Dict[str, Any]]) -> None:
    """Save tasks to state"""
    if _state_manager:
        tasks_json = json.dumps(tasks)
        _state_manager.set('tasks', tasks_json)


def _get_next_task_id() -> int:
    """Get next task ID"""
    if _state_manager:
        next_id = _state_manager.get('next_task_id', 1)
        _state_manager.set('next_task_id', next_id + 1)
        return next_id
    else:
        return 1


def _find_task(tasks: List[Dict[str, Any]], task_id: int) -> Dict[str, Any]:
    """Find task by ID"""
    for task in tasks:
        if task['task_id'] == task_id:
            return task
    return None


__endpoint__ = {
    'name': 'task_queue',
    'description': 'Task queue with priorities and status tracking',
    'version': '1.0.0',
    'author': 'tutorial',
    'methods': ['GET', 'POST', 'PUT', 'DELETE'],
}

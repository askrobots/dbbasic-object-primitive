"""
Queue Object - Message queue system for Object Primitives

This object provides message queue capabilities for async task processing.
Supports priority queues, visibility timeouts, and dead letter queues.

Example usage:
    # Enqueue message
    POST /objects/queue
    {
        "queue_name": "email_queue",
        "message": {"to": "user@example.com", "subject": "Welcome"},
        "priority": "high"
    }

    # Dequeue message (get next message)
    GET /objects/queue?queue_name=email_queue

    # Acknowledge message (mark as completed)
    DELETE /objects/queue?message_id=abc123

    # Requeue message (return to queue on failure)
    PUT /objects/queue?message_id=abc123

    # Get queue status
    GET /objects/queue?queue_name=email_queue&status=true
"""

import time
import json
import secrets
from typing import Any, Dict, List, Optional

# These will be injected by ObjectRuntime
_logger = None
_state_manager = None

# Priority levels (higher number = higher priority)
PRIORITY_LEVELS = {
    'critical': 4,
    'high': 3,
    'normal': 2,
    'low': 1,
}

# Default visibility timeout (seconds)
DEFAULT_VISIBILITY_TIMEOUT = 300  # 5 minutes

# Default message TTL (seconds)
DEFAULT_TTL = 86400  # 24 hours


def POST(request: Dict[str, Any]) -> Dict[str, Any]:
    """Enqueue message"""
    queue_name = request.get('queue_name', '').strip()
    message = request.get('message', {})
    priority = request.get('priority', 'normal').lower()
    ttl = request.get('ttl', DEFAULT_TTL)

    if not queue_name:
        return {'status': 'error', 'message': 'queue_name is required'}

    if priority not in PRIORITY_LEVELS:
        return {'status': 'error', 'message': f'Invalid priority. Must be one of: {list(PRIORITY_LEVELS.keys())}'}

    # Create message
    message_id = secrets.token_hex(8)
    timestamp = int(time.time())

    queue_message = {
        'id': message_id,
        'queue_name': queue_name,
        'message': message,
        'priority': priority,
        'priority_level': PRIORITY_LEVELS[priority],
        'status': 'pending',
        'created_at': timestamp,
        'visible_after': timestamp,  # When message becomes visible
        'expires_at': timestamp + ttl,
        'attempts': 0,
        'max_attempts': 3,
    }

    # Save to queue
    _save_message(queue_message)

    if _logger:
        _logger.info('Message enqueued',
                    message_id=message_id,
                    queue_name=queue_name,
                    priority=priority)

    return {
        'status': 'ok',
        'message_id': message_id,
        'queue_name': queue_name,
        'message': 'Message enqueued',
    }


def GET(request: Dict[str, Any]) -> Dict[str, Any]:
    """Dequeue message or get queue status"""
    queue_name = request.get('queue_name', '').strip()

    if not queue_name:
        return {'status': 'error', 'message': 'queue_name is required'}

    # Get queue status
    if request.get('status'):
        return _get_queue_status(queue_name)

    # Dequeue message
    visibility_timeout = request.get('visibility_timeout', DEFAULT_VISIBILITY_TIMEOUT)

    try:
        visibility_timeout = int(visibility_timeout)
    except (ValueError, TypeError):
        visibility_timeout = DEFAULT_VISIBILITY_TIMEOUT

    message = _dequeue_message(queue_name, visibility_timeout)

    if not message:
        return {
            'status': 'ok',
            'message': 'No messages available',
            'queue_name': queue_name,
        }

    if _logger:
        _logger.info('Message dequeued',
                    message_id=message['id'],
                    queue_name=queue_name,
                    priority=message['priority'])

    return {
        'status': 'ok',
        'message': message,
    }


def DELETE(request: Dict[str, Any]) -> Dict[str, Any]:
    """Acknowledge message (mark as completed and remove from queue)"""
    message_id = request.get('message_id', '').strip()

    if not message_id:
        return {'status': 'error', 'message': 'message_id is required'}

    message = _get_message(message_id)
    if not message:
        return {'status': 'error', 'message': f'Message not found: {message_id}'}

    # Mark as completed
    message['status'] = 'completed'
    message['completed_at'] = int(time.time())
    _save_message(message)

    if _logger:
        _logger.info('Message acknowledged',
                    message_id=message_id,
                    queue_name=message['queue_name'])

    return {
        'status': 'ok',
        'message': f'Message acknowledged: {message_id}',
    }


def PUT(request: Dict[str, Any]) -> Dict[str, Any]:
    """Requeue message (return to queue, increment attempts)"""
    message_id = request.get('message_id', '').strip()
    delay = request.get('delay', 0)  # Delay before message becomes visible again

    if not message_id:
        return {'status': 'error', 'message': 'message_id is required'}

    message = _get_message(message_id)
    if not message:
        return {'status': 'error', 'message': f'Message not found: {message_id}'}

    try:
        delay = int(delay)
    except (ValueError, TypeError):
        delay = 0

    # Increment attempts
    message['attempts'] += 1

    # Check max attempts
    if message['attempts'] >= message.get('max_attempts', 3):
        # Move to dead letter queue
        message['status'] = 'failed'
        message['failed_at'] = int(time.time())
        _save_message(message)

        if _logger:
            _logger.error('Message failed (max attempts exceeded)',
                         message_id=message_id,
                         attempts=message['attempts'])

        return {
            'status': 'error',
            'message': f'Message failed after {message["attempts"]} attempts',
            'message_id': message_id,
        }

    # Requeue message
    message['status'] = 'pending'
    message['visible_after'] = int(time.time()) + delay
    _save_message(message)

    if _logger:
        _logger.info('Message requeued',
                    message_id=message_id,
                    attempts=message['attempts'],
                    delay=delay)

    return {
        'status': 'ok',
        'message': f'Message requeued: {message_id}',
        'attempts': message['attempts'],
    }


# Helper functions

def _save_message(message: Dict[str, Any]) -> None:
    """Save message to state"""
    if not _state_manager:
        return

    message_id = message['id']
    queue_name = message['queue_name']
    priority_level = message['priority_level']
    created_at = message['created_at']

    # Store with composite key for sorting: queue_priority_timestamp_id
    # This ensures messages are retrieved in priority order, then FIFO
    key = f'msg_{queue_name}_{priority_level}_{created_at}_{message_id}'
    _state_manager.set(key, json.dumps(message))


def _get_message(message_id: str) -> Optional[Dict[str, Any]]:
    """Get message by ID"""
    if not _state_manager:
        return None

    all_state = _state_manager.get_all()

    for key, value in all_state.items():
        if key.startswith('msg_') and message_id in key:
            message = json.loads(value)
            if message['id'] == message_id:
                return message

    return None


def _dequeue_message(queue_name: str, visibility_timeout: int) -> Optional[Dict[str, Any]]:
    """Get next available message from queue"""
    if not _state_manager:
        return None

    now = int(time.time())
    all_state = _state_manager.get_all()

    # Find all pending messages for this queue
    messages = []
    prefix = f'msg_{queue_name}_'

    for key, value in all_state.items():
        if key.startswith(prefix):
            message = json.loads(value)

            # Only pending messages
            if message['status'] != 'pending':
                continue

            # Check expiration
            if message['expires_at'] < now:
                message['status'] = 'expired'
                _save_message(message)
                continue

            # Check visibility
            if message['visible_after'] > now:
                continue

            messages.append(message)

    # No messages available
    if not messages:
        return None

    # Sort by priority (highest first), then timestamp (oldest first)
    messages.sort(key=lambda m: (-m['priority_level'], m['created_at']))

    # Get first message
    message = messages[0]

    # Mark as processing and set visibility timeout
    message['status'] = 'processing'
    message['visible_after'] = now + visibility_timeout
    message['dequeued_at'] = now
    _save_message(message)

    return message


def _get_queue_status(queue_name: str) -> Dict[str, Any]:
    """Get queue status (counts by status)"""
    if not _state_manager:
        return {
            'status': 'ok',
            'queue_name': queue_name,
            'total': 0,
            'pending': 0,
            'processing': 0,
            'completed': 0,
            'failed': 0,
        }

    all_state = _state_manager.get_all()
    prefix = f'msg_{queue_name}_'

    counts = {
        'total': 0,
        'pending': 0,
        'processing': 0,
        'completed': 0,
        'failed': 0,
        'expired': 0,
    }

    for key, value in all_state.items():
        if key.startswith(prefix):
            message = json.loads(value)
            counts['total'] += 1
            status = message.get('status', 'unknown')
            if status in counts:
                counts[status] += 1

    return {
        'status': 'ok',
        'queue_name': queue_name,
        **counts,
    }

"""
Events Object - Pub/Sub event system for Object Primitives

This object provides event publishing and subscription capabilities.
Objects can publish events and subscribe to event types.

Example usage:
    # Publish event
    POST /objects/events
    {
        "event_type": "user.created",
        "payload": {"user_id": "123", "username": "alice"},
        "source": "auth"
    }

    # Subscribe to event type
    GET /objects/events?subscribe=user.created

    # Query event history
    GET /objects/events?event_type=user.created&since=1234567890&limit=10

    # Get all events
    GET /objects/events
"""

import time
import json
import secrets
from typing import Any, Dict, List, Optional

# These will be injected by ObjectRuntime
_logger = None
_state_manager = None


def POST(request: Dict[str, Any]) -> Dict[str, Any]:
    """Publish event"""
    event_type = request.get('event_type', '').strip()
    payload = request.get('payload', {})
    source = request.get('source', 'unknown')

    if not event_type:
        return {'status': 'error', 'message': 'event_type is required'}

    # Create event
    event_id = secrets.token_hex(8)
    timestamp = int(time.time())

    event = {
        'id': event_id,
        'event_type': event_type,
        'payload': payload,
        'source': source,
        'timestamp': timestamp,
    }

    # Save to immutable event log (append-only)
    _save_event(event)

    # Notify subscribers (best-effort)
    _notify_subscribers(event)

    if _logger:
        _logger.info('Event published',
                    event_id=event_id,
                    event_type=event_type,
                    source=source)

    return {
        'status': 'ok',
        'event_id': event_id,
        'timestamp': timestamp,
        'message': f'Event published: {event_type}',
    }


def GET(request: Dict[str, Any]) -> Dict[str, Any]:
    """Query events or subscribe to event type"""

    # Subscribe to event type
    subscribe_to = request.get('subscribe')
    if subscribe_to:
        return _subscribe(subscribe_to, request)

    # Query event history
    event_type = request.get('event_type')
    since = request.get('since')  # Unix timestamp
    limit = request.get('limit', 100)

    try:
        limit = int(limit)
    except (ValueError, TypeError):
        limit = 100

    try:
        since = int(since) if since else None
    except (ValueError, TypeError):
        since = None

    # Get all events
    events = _get_all_events()

    # Filter by event_type
    if event_type:
        events = [e for e in events if e.get('event_type') == event_type]

    # Filter by timestamp (inclusive - events >= since)
    if since:
        events = [e for e in events if e.get('timestamp', 0) >= since]

    # Apply limit
    events = events[:limit]

    return {
        'status': 'ok',
        'events': events,
        'count': len(events),
    }


def DELETE(request: Dict[str, Any]) -> Dict[str, Any]:
    """Unsubscribe from event type"""
    event_type = request.get('event_type', '').strip()
    subscriber_id = request.get('subscriber_id', '').strip()

    if not event_type:
        return {'status': 'error', 'message': 'event_type is required'}

    if not subscriber_id:
        return {'status': 'error', 'message': 'subscriber_id is required'}

    # Remove subscription
    subscription = _get_subscription(event_type, subscriber_id)
    if not subscription:
        return {'status': 'error', 'message': 'Subscription not found'}

    _delete_subscription(event_type, subscriber_id)

    if _logger:
        _logger.info('Unsubscribed from event',
                    event_type=event_type,
                    subscriber_id=subscriber_id)

    return {
        'status': 'ok',
        'message': f'Unsubscribed from {event_type}',
    }


# Helper functions

def _subscribe(event_type: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """Subscribe to event type"""
    subscriber_id = request.get('subscriber_id', secrets.token_hex(8))
    callback_url = request.get('callback_url', '')

    subscription = {
        'id': subscriber_id,
        'event_type': event_type,
        'callback_url': callback_url,
        'created_at': int(time.time()),
        'last_event_id': None,
    }

    _save_subscription(subscription)

    if _logger:
        _logger.info('Subscribed to event',
                    event_type=event_type,
                    subscriber_id=subscriber_id)

    return {
        'status': 'ok',
        'subscriber_id': subscriber_id,
        'event_type': event_type,
        'message': f'Subscribed to {event_type}',
    }


def _save_event(event: Dict[str, Any]) -> None:
    """Save event to immutable log (append-only)"""
    if not _state_manager:
        return

    event_id = event['id']
    timestamp = event['timestamp']

    # Store with timestamp prefix for chronological ordering
    key = f'event_{timestamp}_{event_id}'
    _state_manager.set(key, json.dumps(event))


def _get_all_events() -> List[Dict[str, Any]]:
    """Get all events from log"""
    if not _state_manager:
        return []

    events = []
    all_state = _state_manager.get_all()

    for key, value in all_state.items():
        if key.startswith('event_'):
            event = json.loads(value)
            events.append(event)

    # Sort by timestamp (newest first)
    events.sort(key=lambda e: e.get('timestamp', 0), reverse=True)

    return events


def _save_subscription(subscription: Dict[str, Any]) -> None:
    """Save subscription"""
    if not _state_manager:
        return

    event_type = subscription['event_type']
    subscriber_id = subscription['id']

    key = f'sub_{event_type}_{subscriber_id}'
    _state_manager.set(key, json.dumps(subscription))


def _get_subscription(event_type: str, subscriber_id: str) -> Optional[Dict[str, Any]]:
    """Get subscription"""
    if not _state_manager:
        return None

    key = f'sub_{event_type}_{subscriber_id}'
    sub_json = _state_manager.get(key)

    if not sub_json:
        return None

    return json.loads(sub_json)


def _delete_subscription(event_type: str, subscriber_id: str) -> None:
    """Delete subscription"""
    if not _state_manager:
        return

    key = f'sub_{event_type}_{subscriber_id}'
    _state_manager.delete(key)


def _get_subscriptions_for_event(event_type: str) -> List[Dict[str, Any]]:
    """Get all subscriptions for an event type"""
    if not _state_manager:
        return []

    subscriptions = []
    all_state = _state_manager.get_all()

    prefix = f'sub_{event_type}_'
    for key, value in all_state.items():
        if key.startswith(prefix):
            subscription = json.loads(value)
            subscriptions.append(subscription)

    return subscriptions


def _notify_subscribers(event: Dict[str, Any]) -> None:
    """Notify subscribers of event (best-effort)"""
    event_type = event['event_type']
    subscriptions = _get_subscriptions_for_event(event_type)

    for subscription in subscriptions:
        callback_url = subscription.get('callback_url')

        if callback_url:
            # In a real implementation, this would make HTTP POST to callback_url
            # For now, we just log it
            if _logger:
                _logger.info('Notifying subscriber',
                           event_id=event['id'],
                           event_type=event_type,
                           subscriber_id=subscription['id'],
                           callback_url=callback_url)

        # Update last_event_id
        subscription['last_event_id'] = event['id']
        _save_subscription(subscription)

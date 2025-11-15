"""
Tests for Events package

Tests events.py (REST API for pub/sub events)
"""

import pytest
import json
import time
from pathlib import Path


class TestEventsAPI:
    """Test events REST API (events.py)"""

    @pytest.fixture
    def events_obj(self, tmp_path):
        """Load events object"""
        from object_primitive_core.object_runtime import ObjectRuntime

        # Create runtime with temp directory
        runtime = ObjectRuntime(base_dir=str(tmp_path))

        # Load events object
        events_path = 'examples/triggers/events.py'
        obj = runtime.load_object(events_path)

        return obj

    def test_publish_event(self, events_obj):
        """Should publish event"""
        result = events_obj.execute('POST', {
            'event_type': 'user.created',
            'payload': {'user_id': '123', 'username': 'alice'},
            'source': 'auth',
        })

        assert result['status'] == 'ok'
        assert 'event_id' in result
        assert 'timestamp' in result
        assert 'Event published' in result['message']

    def test_publish_event_requires_event_type(self, events_obj):
        """Should reject event without event_type"""
        result = events_obj.execute('POST', {
            'payload': {'data': 'test'},
            'source': 'test',
        })

        assert result['status'] == 'error'
        assert 'event_type is required' in result['message']

    def test_query_all_events(self, events_obj):
        """Should query all events"""
        # Publish event
        events_obj.execute('POST', {
            'event_type': 'user.created',
            'payload': {'user_id': '123'},
            'source': 'auth',
        })

        # Query events
        result = events_obj.execute('GET', {})

        assert result['status'] == 'ok'
        assert 'events' in result
        assert len(result['events']) >= 1
        assert result['count'] >= 1

    def test_query_events_by_type(self, events_obj):
        """Should filter events by event_type"""
        # Publish multiple events
        events_obj.execute('POST', {
            'event_type': 'user.created',
            'payload': {'user_id': '123'},
            'source': 'auth',
        })

        events_obj.execute('POST', {
            'event_type': 'post.published',
            'payload': {'post_id': '456'},
            'source': 'blog',
        })

        # Query user.created events
        result = events_obj.execute('GET', {'event_type': 'user.created'})

        assert result['status'] == 'ok'
        assert result['count'] >= 1
        for event in result['events']:
            assert event['event_type'] == 'user.created'

    def test_query_events_since_timestamp(self, events_obj):
        """Should filter events by timestamp"""
        # Publish first event
        result1 = events_obj.execute('POST', {
            'event_type': 'test.event',
            'payload': {'seq': 1},
            'source': 'test',
        })

        timestamp1 = result1['timestamp']

        # Wait a moment
        time.sleep(0.1)

        # Publish second event
        events_obj.execute('POST', {
            'event_type': 'test.event',
            'payload': {'seq': 2},
            'source': 'test',
        })

        # Query events since timestamp1
        result = events_obj.execute('GET', {
            'event_type': 'test.event',
            'since': str(timestamp1),
        })

        assert result['status'] == 'ok'
        # Should get events from timestamp1 onwards (inclusive)
        assert result['count'] >= 1
        for event in result['events']:
            assert event['timestamp'] >= timestamp1

    def test_query_events_with_limit(self, events_obj):
        """Should limit number of events returned"""
        # Publish multiple events
        for i in range(5):
            events_obj.execute('POST', {
                'event_type': 'test.event',
                'payload': {'seq': i},
                'source': 'test',
            })

        # Query with limit
        result = events_obj.execute('GET', {
            'event_type': 'test.event',
            'limit': '2',
        })

        assert result['status'] == 'ok'
        assert result['count'] == 2
        assert len(result['events']) == 2

    def test_subscribe_to_event_type(self, events_obj):
        """Should subscribe to event type"""
        result = events_obj.execute('GET', {
            'subscribe': 'user.created',
            'subscriber_id': 'test_subscriber',
            'callback_url': 'http://localhost:8000/webhook',
        })

        assert result['status'] == 'ok'
        assert result['subscriber_id'] == 'test_subscriber'
        assert result['event_type'] == 'user.created'
        assert 'Subscribed' in result['message']

    def test_subscribe_auto_generates_id(self, events_obj):
        """Should auto-generate subscriber_id if not provided"""
        result = events_obj.execute('GET', {
            'subscribe': 'user.created',
        })

        assert result['status'] == 'ok'
        assert 'subscriber_id' in result
        assert len(result['subscriber_id']) > 0

    def test_unsubscribe_from_event_type(self, events_obj):
        """Should unsubscribe from event type"""
        # Subscribe first
        sub_result = events_obj.execute('GET', {
            'subscribe': 'user.created',
            'subscriber_id': 'test_subscriber',
        })

        assert sub_result['status'] == 'ok'

        # Unsubscribe
        result = events_obj.execute('DELETE', {
            'event_type': 'user.created',
            'subscriber_id': 'test_subscriber',
        })

        assert result['status'] == 'ok'
        assert 'Unsubscribed' in result['message']

    def test_unsubscribe_requires_event_type(self, events_obj):
        """Should reject unsubscribe without event_type"""
        result = events_obj.execute('DELETE', {
            'subscriber_id': 'test_subscriber',
        })

        assert result['status'] == 'error'
        assert 'event_type is required' in result['message']

    def test_unsubscribe_requires_subscriber_id(self, events_obj):
        """Should reject unsubscribe without subscriber_id"""
        result = events_obj.execute('DELETE', {
            'event_type': 'user.created',
        })

        assert result['status'] == 'error'
        assert 'subscriber_id is required' in result['message']

    def test_unsubscribe_nonexistent_subscription(self, events_obj):
        """Should handle unsubscribe for non-existent subscription"""
        result = events_obj.execute('DELETE', {
            'event_type': 'user.created',
            'subscriber_id': 'nonexistent',
        })

        assert result['status'] == 'error'
        assert 'not found' in result['message']

    def test_event_immutability(self, events_obj):
        """Events should be immutable (append-only log)"""
        # Publish event
        result1 = events_obj.execute('POST', {
            'event_type': 'test.event',
            'payload': {'data': 'original'},
            'source': 'test',
        })

        event_id1 = result1['event_id']

        # Publish another event
        result2 = events_obj.execute('POST', {
            'event_type': 'test.event',
            'payload': {'data': 'second'},
            'source': 'test',
        })

        # Query all events - both should still exist
        result = events_obj.execute('GET', {'event_type': 'test.event'})

        assert result['count'] >= 2
        event_ids = [e['id'] for e in result['events']]
        assert event_id1 in event_ids
        assert result2['event_id'] in event_ids

    def test_event_persistence(self, events_obj):
        """Events should persist in state"""
        # Publish event
        result = events_obj.execute('POST', {
            'event_type': 'test.event',
            'payload': {'data': 'test'},
            'source': 'test',
        })

        event_id = result['event_id']

        # Access state manager directly
        state_mgr = events_obj.state_manager
        all_state = state_mgr.get_all()

        # Find event in state
        event_keys = [k for k in all_state.keys() if k.startswith('event_')]
        assert len(event_keys) >= 1

        # Verify event data
        for key in event_keys:
            event_json = all_state[key]
            event = json.loads(event_json)
            if event['id'] == event_id:
                assert event['event_type'] == 'test.event'
                assert event['payload']['data'] == 'test'
                break

    def test_subscription_persistence(self, events_obj):
        """Subscriptions should persist in state"""
        # Subscribe
        result = events_obj.execute('GET', {
            'subscribe': 'user.created',
            'subscriber_id': 'test_sub',
            'callback_url': 'http://localhost:8000/webhook',
        })

        assert result['status'] == 'ok'

        # Access state manager directly
        state_mgr = events_obj.state_manager
        sub_json = state_mgr.get('sub_user.created_test_sub')

        assert sub_json is not None
        subscription = json.loads(sub_json)
        assert subscription['id'] == 'test_sub'
        assert subscription['event_type'] == 'user.created'
        assert subscription['callback_url'] == 'http://localhost:8000/webhook'

    def test_event_ordering(self, events_obj):
        """Events should be returned in chronological order (newest first)"""
        # Publish events with delay
        for i in range(3):
            events_obj.execute('POST', {
                'event_type': 'test.event',
                'payload': {'seq': i},
                'source': 'test',
            })
            time.sleep(0.05)  # Small delay to ensure different timestamps

        # Query events
        result = events_obj.execute('GET', {'event_type': 'test.event'})

        events = result['events']
        assert len(events) >= 3

        # Verify newest first (timestamps descending)
        for i in range(len(events) - 1):
            assert events[i]['timestamp'] >= events[i + 1]['timestamp']

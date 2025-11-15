"""
Tests for Queue package

Tests queue.py (REST API for message queues)
"""

import pytest
import json
import time
from pathlib import Path


class TestQueueAPI:
    """Test queue REST API (queue.py)"""

    @pytest.fixture
    def queue_obj(self, tmp_path):
        """Load queue object"""
        from object_primitive_core.object_runtime import ObjectRuntime

        # Create runtime with temp directory
        runtime = ObjectRuntime(base_dir=str(tmp_path))

        # Load queue object
        queue_path = 'examples/triggers/queue.py'
        obj = runtime.load_object(queue_path)

        return obj

    def test_enqueue_message(self, queue_obj):
        """Should enqueue message"""
        result = queue_obj.execute('POST', {
            'queue_name': 'email_queue',
            'message': {'to': 'user@example.com', 'subject': 'Welcome'},
            'priority': 'high',
        })

        assert result['status'] == 'ok'
        assert 'message_id' in result
        assert result['queue_name'] == 'email_queue'
        assert 'Message enqueued' in result['message']

    def test_enqueue_requires_queue_name(self, queue_obj):
        """Should reject enqueue without queue_name"""
        result = queue_obj.execute('POST', {
            'message': {'data': 'test'},
        })

        assert result['status'] == 'error'
        assert 'queue_name is required' in result['message']

    def test_enqueue_default_priority(self, queue_obj):
        """Should use default priority if not specified"""
        result = queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'data': 'test'},
        })

        assert result['status'] == 'ok'

        # Dequeue to check priority
        dequeue_result = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert dequeue_result['message']['priority'] == 'normal'

    def test_enqueue_invalid_priority(self, queue_obj):
        """Should reject invalid priority"""
        result = queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'data': 'test'},
            'priority': 'invalid',
        })

        assert result['status'] == 'error'
        assert 'Invalid priority' in result['message']

    def test_dequeue_message(self, queue_obj):
        """Should dequeue message"""
        # Enqueue first
        enqueue_result = queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'task': 'send_email'},
            'priority': 'normal',
        })

        assert enqueue_result['status'] == 'ok'

        # Dequeue
        result = queue_obj.execute('GET', {'queue_name': 'test_queue'})

        assert result['status'] == 'ok'
        assert 'message' in result
        assert result['message']['queue_name'] == 'test_queue'
        assert result['message']['message']['task'] == 'send_email'
        assert result['message']['status'] == 'processing'

    def test_dequeue_empty_queue(self, queue_obj):
        """Should handle dequeue from empty queue"""
        result = queue_obj.execute('GET', {'queue_name': 'empty_queue'})

        assert result['status'] == 'ok'
        assert 'No messages available' in result['message']

    def test_dequeue_requires_queue_name(self, queue_obj):
        """Should reject dequeue without queue_name"""
        result = queue_obj.execute('GET', {})

        assert result['status'] == 'error'
        assert 'queue_name is required' in result['message']

    def test_acknowledge_message(self, queue_obj):
        """Should acknowledge message (mark as completed)"""
        # Enqueue message
        enqueue_result = queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'task': 'process'},
        })

        message_id = enqueue_result['message_id']

        # Dequeue message
        queue_obj.execute('GET', {'queue_name': 'test_queue'})

        # Acknowledge
        result = queue_obj.execute('DELETE', {'message_id': message_id})

        assert result['status'] == 'ok'
        assert 'acknowledged' in result['message']

    def test_acknowledge_requires_message_id(self, queue_obj):
        """Should reject acknowledge without message_id"""
        result = queue_obj.execute('DELETE', {})

        assert result['status'] == 'error'
        assert 'message_id is required' in result['message']

    def test_acknowledge_nonexistent_message(self, queue_obj):
        """Should handle acknowledge for non-existent message"""
        result = queue_obj.execute('DELETE', {'message_id': 'nonexistent'})

        assert result['status'] == 'error'
        assert 'not found' in result['message']

    def test_requeue_message(self, queue_obj):
        """Should requeue message on failure"""
        # Enqueue message
        enqueue_result = queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'task': 'retry_me'},
        })

        message_id = enqueue_result['message_id']

        # Dequeue message
        queue_obj.execute('GET', {'queue_name': 'test_queue'})

        # Requeue (simulate failure)
        result = queue_obj.execute('PUT', {'message_id': message_id})

        assert result['status'] == 'ok'
        assert 'requeued' in result['message']
        assert result['attempts'] == 1

    def test_requeue_max_attempts(self, queue_obj):
        """Should move to dead letter queue after max attempts"""
        # Enqueue message
        enqueue_result = queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'task': 'always_fails'},
        })

        message_id = enqueue_result['message_id']

        # Attempt 3 times
        for i in range(3):
            # Dequeue
            queue_obj.execute('GET', {'queue_name': 'test_queue'})

            # Requeue
            result = queue_obj.execute('PUT', {'message_id': message_id})

            if i < 2:
                assert result['status'] == 'ok'
                assert result['attempts'] == i + 1
            else:
                # Third attempt should fail
                assert result['status'] == 'error'
                assert 'failed after' in result['message']

    def test_priority_ordering(self, queue_obj):
        """Should dequeue messages by priority"""
        # Enqueue messages with different priorities
        queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'task': 'low_priority'},
            'priority': 'low',
        })

        queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'task': 'high_priority'},
            'priority': 'high',
        })

        queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'task': 'critical_priority'},
            'priority': 'critical',
        })

        # Dequeue should get critical first
        result1 = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert result1['message']['message']['task'] == 'critical_priority'

        # Then high
        result2 = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert result2['message']['message']['task'] == 'high_priority'

        # Then low
        result3 = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert result3['message']['message']['task'] == 'low_priority'

    def test_fifo_within_priority(self, queue_obj):
        """Should maintain FIFO order within same priority"""
        # Enqueue multiple messages with same priority
        for i in range(3):
            queue_obj.execute('POST', {
                'queue_name': 'test_queue',
                'message': {'seq': i},
                'priority': 'normal',
            })
            time.sleep(0.01)  # Small delay to ensure different timestamps

        # Dequeue should get messages in FIFO order
        result1 = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert result1['message']['message']['seq'] == 0

        result2 = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert result2['message']['message']['seq'] == 1

        result3 = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert result3['message']['message']['seq'] == 2

    def test_visibility_timeout(self, queue_obj):
        """Should hide message during visibility timeout"""
        # Enqueue message
        queue_obj.execute('POST', {
            'queue_name': 'test_queue',
            'message': {'task': 'test'},
        })

        # Dequeue with short visibility timeout
        result1 = queue_obj.execute('GET', {
            'queue_name': 'test_queue',
            'visibility_timeout': '1',  # 1 second
        })

        assert result1['status'] == 'ok'
        assert result1['message']['status'] == 'processing'

        # Immediate dequeue should get nothing (message is invisible)
        result2 = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert 'No messages available' in result2['message']

        # Wait for visibility timeout to expire
        time.sleep(1.1)

        # Now should get message again
        result3 = queue_obj.execute('GET', {'queue_name': 'test_queue'})
        assert result3['status'] == 'ok'
        assert 'message' in result3

    def test_queue_status(self, queue_obj):
        """Should get queue status"""
        # Enqueue some messages
        queue_obj.execute('POST', {
            'queue_name': 'status_queue',
            'message': {'task': 'task1'},
        })

        queue_obj.execute('POST', {
            'queue_name': 'status_queue',
            'message': {'task': 'task2'},
        })

        # Get status
        result = queue_obj.execute('GET', {
            'queue_name': 'status_queue',
            'status': 'true',
        })

        assert result['status'] == 'ok'
        assert result['queue_name'] == 'status_queue'
        assert result['total'] >= 2
        assert result['pending'] >= 2

    def test_multiple_queues_isolated(self, queue_obj):
        """Should keep different queues isolated"""
        # Enqueue to queue1
        queue_obj.execute('POST', {
            'queue_name': 'queue1',
            'message': {'data': 'queue1_data'},
        })

        # Enqueue to queue2
        queue_obj.execute('POST', {
            'queue_name': 'queue2',
            'message': {'data': 'queue2_data'},
        })

        # Dequeue from queue1
        result1 = queue_obj.execute('GET', {'queue_name': 'queue1'})
        assert result1['message']['message']['data'] == 'queue1_data'

        # Dequeue from queue2
        result2 = queue_obj.execute('GET', {'queue_name': 'queue2'})
        assert result2['message']['message']['data'] == 'queue2_data'

    def test_message_persistence(self, queue_obj):
        """Messages should persist in state"""
        # Enqueue message
        result = queue_obj.execute('POST', {
            'queue_name': 'persist_queue',
            'message': {'data': 'test'},
        })

        message_id = result['message_id']

        # Access state manager directly
        state_mgr = queue_obj.state_manager
        all_state = state_mgr.get_all()

        # Find message in state
        message_keys = [k for k in all_state.keys() if k.startswith('msg_persist_queue_')]
        assert len(message_keys) >= 1

        # Verify message data
        for key in message_keys:
            message_json = all_state[key]
            message = json.loads(message_json)
            if message['id'] == message_id:
                assert message['message']['data'] == 'test'
                assert message['queue_name'] == 'persist_queue'
                break

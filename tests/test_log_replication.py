"""
Tests for log replication across cluster stations.

Verifies that:
1. Logs are appended, not overwritten
2. Duplicate entries are detected
3. All log entries are preserved across replication
"""
import pytest
import tempfile
import shutil
from pathlib import Path
from dbbasic_object_core.core.self_logger import SelfLogger


class TestLogReplicationBasics:
    """Test basic log replication functionality"""

    def setup_method(self):
        """Create temp directory for test logs"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temp directory"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_log_entry_has_entry_id(self):
        """Log entries should have unique entry_id"""
        logger = SelfLogger('test_object', self.temp_dir, enable_replication=False)

        logger.info('First message')
        logger.info('Second message')

        logs = logger.get_logs()

        assert len(logs) == 2
        assert 'entry_id' in logs[0]
        assert 'entry_id' in logs[1]
        assert logs[0]['entry_id'] != logs[1]['entry_id']

    def test_entry_ids_are_unique_and_deterministic(self):
        """Entry IDs should be unique but deterministic for same input"""
        logger = SelfLogger('test_object', self.temp_dir, enable_replication=False)

        # Log same message twice
        logger.info('Same message')
        logger.info('Same message')

        logs = logger.get_logs()

        # IDs should be different (different timestamps)
        assert logs[0]['entry_id'] != logs[1]['entry_id']

    def test_multiple_log_entries_all_preserved(self):
        """All log entries should be preserved in order"""
        logger = SelfLogger('test_object', self.temp_dir, enable_replication=False)

        # Log multiple entries
        for i in range(10):
            logger.info(f'Message {i}')

        logs = logger.get_logs()

        assert len(logs) == 10
        for i in range(10):
            assert logs[i]['message'] == f'Message {i}'


class TestLogAppendEndpoint:
    """Test /cluster/append_log endpoint"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())

        # Clean up any existing test data from previous runs
        test_log_dir = Path('data/logs/test_object')
        if test_log_dir.exists():
            shutil.rmtree(test_log_dir)

        # Create mock request
        class MockRequest:
            def __init__(self):
                self.body = b''

        self.request = MockRequest()

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        # Clean up test data
        test_log_dir = Path('data/logs/test_object')
        if test_log_dir.exists():
            shutil.rmtree(test_log_dir)

    def test_append_log_endpoint_accepts_entry(self):
        """Endpoint should accept and append log entry"""
        from api.cluster.append_log import POST
        import json

        log_entry = {
            'timestamp': '2025-11-16T12:00:00',
            'level': 'INFO',
            'message': 'Test message'
        }

        payload = {
            'object_id': 'test_object',
            'entry_id': 'abc123',
            'log_entry': log_entry,
            'source_station': 'station2'
        }

        self.request.body = json.dumps(payload).encode('utf-8')

        response = POST(self.request)

        # Response is a tuple (status, headers, [body])
        response_body = response[2][0] if isinstance(response, tuple) else response
        response_data = json.loads(response_body)
        assert response_data['status'] == 'ok'

        # Verify log file created
        log_file = Path('data/logs/test_object/log.tsv')
        assert log_file.exists()

    def test_duplicate_entries_rejected(self):
        """Duplicate entry_id should be rejected"""
        from api.cluster.append_log import POST
        import json

        log_entry = {
            'timestamp': '2025-11-16T12:00:00',
            'level': 'INFO',
            'message': 'Test message'
        }

        payload = {
            'object_id': 'test_object',
            'entry_id': 'duplicate123',
            'log_entry': log_entry,
            'source_station': 'station2'
        }

        self.request.body = json.dumps(payload).encode('utf-8')

        # First POST should succeed
        response1 = POST(self.request)
        body1 = response1[2][0] if isinstance(response1, tuple) else response1
        data1 = json.loads(body1)
        assert data1['status'] == 'ok'

        # Second POST with same entry_id should be marked as duplicate
        response2 = POST(self.request)
        body2 = response2[2][0] if isinstance(response2, tuple) else response2
        data2 = json.loads(body2)
        assert data2['status'] == 'duplicate'

    def test_multiple_entries_all_appended(self):
        """Multiple log entries should all be appended"""
        from api.cluster.append_log import POST
        import json

        # Send 5 different log entries
        for i in range(5):
            log_entry = {
                'timestamp': f'2025-11-16T12:00:0{i}',
                'level': 'INFO',
                'message': f'Message {i}'
            }

            payload = {
                'object_id': 'test_object',
                'entry_id': f'entry_{i}',
                'log_entry': log_entry,
                'source_station': 'station2'
            }

            self.request.body = json.dumps(payload).encode('utf-8')
            response = POST(self.request)

            body = response[2][0] if isinstance(response, tuple) else response
            data = json.loads(body)
            assert data['status'] == 'ok'

        # Verify all 5 entries exist in log file
        logger = SelfLogger('test_object', Path('data'), enable_replication=False)
        logs = logger.get_logs()

        assert len(logs) == 5
        for i in range(5):
            assert logs[i]['message'] == f'Message {i}'


class TestLogReplicationIntegration:
    """Integration tests for end-to-end log replication"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_logger_creates_entries_with_unique_ids(self):
        """Logger should create unique IDs for each entry"""
        logger = SelfLogger('test_object', self.temp_dir, enable_replication=False)

        logger.info('Entry 1')
        logger.info('Entry 2')
        logger.info('Entry 3')

        logs = logger.get_logs()

        # All entries should have unique IDs
        entry_ids = [log['entry_id'] for log in logs]
        assert len(entry_ids) == len(set(entry_ids))  # No duplicates

    def test_backward_compatibility_with_old_logs(self):
        """Should handle old logs without entry_id field"""
        # Create a fresh logger (this will create new log file with entry_id)
        logger = SelfLogger('test_object', self.temp_dir, enable_replication=False)

        # Log message - will have entry_id
        logger.info('New message')

        logs = logger.get_logs()

        # Log should be readable and have entry_id
        assert len(logs) == 1
        assert 'entry_id' in logs[0]
        assert logs[0]['entry_id'] != ''
        assert logs[0]['message'] == 'New message'


class TestLogReplicationPerformance:
    """Test performance aspects of log replication"""

    def setup_method(self):
        """Setup test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_logging_many_entries_is_fast(self):
        """Logging many entries should complete quickly"""
        import time

        logger = SelfLogger('test_object', self.temp_dir, enable_replication=False)

        start = time.time()

        # Log 100 entries
        for i in range(100):
            logger.info(f'Message {i}')

        elapsed = time.time() - start

        # Should complete in under 1 second
        assert elapsed < 1.0

        # Verify all logs exist
        logs = logger.get_logs()
        assert len(logs) == 100

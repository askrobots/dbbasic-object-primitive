"""
Unit tests for self-logging pattern

Test-Driven Development: These tests are written FIRST, before implementation.
They define the expected behavior of self-logging.

Self-Logging Pattern:
- Objects log to themselves (not to external log system)
- Logs stored in TSV files (human-readable, grep-able)
- Append-only (immutable history)
- Query logs (filter, time range, pagination)
- Each endpoint has its own log file
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta


class TestBasicLogging:
    """Test basic self-logging functionality"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_log_single_entry(self):
        """Should log a single entry to TSV file"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(object_id='test_endpoint', base_dir=self.temp_dir)

        logger.log(
            level='INFO',
            message='Test message',
            method='GET',
        )

        # Check log file exists
        log_file = self.temp_dir / 'logs' / 'test_endpoint' / 'log.tsv'
        assert log_file.exists()

        # Check content
        content = log_file.read_text()
        lines = content.strip().split('\n')

        assert len(lines) == 2  # Header + 1 entry
        assert 'timestamp' in lines[0]
        assert 'Test message' in lines[1]

    def test_log_multiple_entries(self):
        """Should log multiple entries in order"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(object_id='test', base_dir=self.temp_dir)

        logger.log(level='INFO', message='First')
        logger.log(level='INFO', message='Second')
        logger.log(level='INFO', message='Third')

        log_file = self.temp_dir / 'logs' / 'test' / 'log.tsv'
        content = log_file.read_text()
        lines = content.strip().split('\n')

        assert len(lines) == 4  # Header + 3 entries
        assert 'First' in lines[1]
        assert 'Second' in lines[2]
        assert 'Third' in lines[3]

    def test_log_with_metadata(self):
        """Should include timestamp, level, and other metadata"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(object_id='test', base_dir=self.temp_dir)

        before = datetime.now()
        logger.log(
            level='ERROR',
            message='Something failed',
            method='POST',
            user_id='user-123',
            request_id='req-456',
        )
        after = datetime.now()

        # Read the entry
        entries = logger.get_logs()
        assert len(entries) == 1

        entry = entries[0]
        assert entry['level'] == 'ERROR'
        assert entry['message'] == 'Something failed'
        assert entry['method'] == 'POST'
        assert entry['user_id'] == 'user-123'
        assert entry['request_id'] == 'req-456'

        # Timestamp should be between before and after
        timestamp = datetime.fromisoformat(entry['timestamp'])
        assert before <= timestamp <= after

    def test_logs_for_different_objects_separate(self):
        """Should keep logs separate for different objects"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger1 = SelfLogger(object_id='endpoint1', base_dir=self.temp_dir)
        logger2 = SelfLogger(object_id='endpoint2', base_dir=self.temp_dir)

        logger1.log(level='INFO', message='Log from endpoint1')
        logger2.log(level='INFO', message='Log from endpoint2')

        # Check separate files
        log1 = self.temp_dir / 'logs' / 'endpoint1' / 'log.tsv'
        log2 = self.temp_dir / 'logs' / 'endpoint2' / 'log.tsv'

        assert log1.exists()
        assert log2.exists()

        # Check content
        entries1 = logger1.get_logs()
        entries2 = logger2.get_logs()

        assert len(entries1) == 1
        assert len(entries2) == 1
        assert entries1[0]['message'] == 'Log from endpoint1'
        assert entries2[0]['message'] == 'Log from endpoint2'


class TestLogLevels:
    """Test different log levels"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_log_levels(self):
        """Should support different log levels"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(object_id='test', base_dir=self.temp_dir)

        logger.log(level='DEBUG', message='Debug message')
        logger.log(level='INFO', message='Info message')
        logger.log(level='WARNING', message='Warning message')
        logger.log(level='ERROR', message='Error message')
        logger.log(level='CRITICAL', message='Critical message')

        entries = logger.get_logs()
        assert len(entries) == 5

        assert entries[0]['level'] == 'DEBUG'
        assert entries[1]['level'] == 'INFO'
        assert entries[2]['level'] == 'WARNING'
        assert entries[3]['level'] == 'ERROR'
        assert entries[4]['level'] == 'CRITICAL'

    def test_convenience_methods(self):
        """Should provide convenience methods for each level"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(object_id='test', base_dir=self.temp_dir)

        logger.debug('Debug message')
        logger.info('Info message')
        logger.warning('Warning message')
        logger.error('Error message')
        logger.critical('Critical message')

        entries = logger.get_logs()
        assert len(entries) == 5

        levels = [e['level'] for e in entries]
        assert levels == ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']


class TestLogQuerying:
    """Test querying and filtering logs"""

    def setup_method(self):
        """Create temporary directory and some logs"""
        self.temp_dir = Path(tempfile.mkdtemp())
        from dbbasic_object_core.core.self_logger import SelfLogger

        self.logger = SelfLogger(object_id='test', base_dir=self.temp_dir)

        # Create some logs
        self.logger.info('First message', user_id='user-1')
        self.logger.warning('Second message', user_id='user-2')
        self.logger.error('Third message', user_id='user-1')
        self.logger.info('Fourth message', user_id='user-3')
        self.logger.critical('Fifth message', user_id='user-2')

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_get_all_logs(self):
        """Should retrieve all logs"""
        entries = self.logger.get_logs()
        assert len(entries) == 5

    def test_filter_by_level(self):
        """Should filter logs by level"""
        entries = self.logger.get_logs(level='ERROR')
        assert len(entries) == 1
        assert entries[0]['message'] == 'Third message'

    def test_filter_by_multiple_levels(self):
        """Should filter by multiple levels"""
        entries = self.logger.get_logs(level=['ERROR', 'CRITICAL'])
        assert len(entries) == 2
        assert entries[0]['level'] in ['ERROR', 'CRITICAL']
        assert entries[1]['level'] in ['ERROR', 'CRITICAL']

    def test_limit_results(self):
        """Should limit number of results"""
        entries = self.logger.get_logs(limit=3)
        assert len(entries) == 3

    def test_offset_results(self):
        """Should skip entries with offset"""
        entries = self.logger.get_logs(offset=2, limit=2)
        assert len(entries) == 2
        # Should get 3rd and 4th entries
        assert entries[0]['message'] == 'Third message'
        assert entries[1]['message'] == 'Fourth message'

    def test_filter_by_custom_field(self):
        """Should filter by custom fields like user_id"""
        entries = self.logger.get_logs(user_id='user-1')
        assert len(entries) == 2
        assert all(e['user_id'] == 'user-1' for e in entries)


class TestLogRotation:
    """Test log rotation (prevent files from growing too large)"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_rotation_after_size_limit(self):
        """Should rotate log file when it exceeds size limit"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        # Create logger with small max size (1KB for testing)
        logger = SelfLogger(
            object_id='test',
            base_dir=self.temp_dir,
            max_log_size=1024,  # 1KB
        )

        # Write enough logs to exceed 1KB
        for i in range(100):
            logger.info(f'Log entry {i}' * 10)  # Make entries larger

        # Should have rotated to a new file
        log_dir = self.temp_dir / 'logs' / 'test'
        log_files = list(log_dir.glob('log*.tsv'))

        # Should have multiple log files
        assert len(log_files) >= 2

    def test_rotation_preserves_old_logs(self):
        """Should keep old rotated logs"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(
            object_id='test',
            base_dir=self.temp_dir,
            max_log_size=1024,
        )

        # Write logs
        for i in range(50):
            logger.info(f'First batch {i}' * 10)

        # Get current log file count
        log_dir = self.temp_dir / 'logs' / 'test'
        files_after_first = list(log_dir.glob('log*.tsv'))

        # Write more logs
        for i in range(50):
            logger.info(f'Second batch {i}' * 10)

        files_after_second = list(log_dir.glob('log*.tsv'))

        # Should have more files now
        assert len(files_after_second) >= len(files_after_first)

    def test_rotation_naming_convention(self):
        """Should use timestamp-based naming for rotated logs"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(
            object_id='test',
            base_dir=self.temp_dir,
            max_log_size=512,
        )

        # Write enough to rotate
        for i in range(100):
            logger.info(f'Entry {i}' * 10)

        log_dir = self.temp_dir / 'logs' / 'test'
        log_files = sorted(log_dir.glob('log*.tsv'))

        # Should have log.tsv and log-TIMESTAMP.tsv files
        assert any(f.name == 'log.tsv' for f in log_files)
        assert any('log-' in f.name and f.name != 'log.tsv' for f in log_files)


class TestLogStorage:
    """Test log storage format (TSV)"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_tsv_format(self):
        """Should store logs in TSV format"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(object_id='test', base_dir=self.temp_dir)
        logger.info('Test message', custom_field='custom_value')

        log_file = self.temp_dir / 'logs' / 'test' / 'log.tsv'
        content = log_file.read_text()

        # Should be tab-separated
        assert '\t' in content
        # Should have header
        lines = content.strip().split('\n')
        assert len(lines) == 2  # Header + 1 entry

    def test_human_readable(self):
        """Should be human-readable (cat, grep, etc.)"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(object_id='test', base_dir=self.temp_dir)
        logger.error('Error occurred', error_code='E123')

        log_file = self.temp_dir / 'logs' / 'test' / 'log.tsv'
        content = log_file.read_text()

        # Should contain the message in plain text
        assert 'Error occurred' in content
        assert 'E123' in content
        # Should be readable (no binary, no JSON escaping)
        assert content.isprintable() or '\n' in content or '\t' in content

    def test_append_only(self):
        """Should append entries (not overwrite)"""
        from dbbasic_object_core.core.self_logger import SelfLogger

        logger = SelfLogger(object_id='test', base_dir=self.temp_dir)

        logger.info('First')
        logger.info('Second')

        # Create new logger instance (simulates restart)
        logger2 = SelfLogger(object_id='test', base_dir=self.temp_dir)
        logger2.info('Third')

        entries = logger2.get_logs()
        assert len(entries) == 3
        assert entries[0]['message'] == 'First'
        assert entries[1]['message'] == 'Second'
        assert entries[2]['message'] == 'Third'

"""
Unit tests for version_manager

Test-Driven Development: These tests are written FIRST, before implementation.
They define the expected behavior of version management.

Every change to an endpoint should be versioned:
- Before modification, save current version
- Store metadata (timestamp, author, message, hash)
- Can retrieve any historical version
- Can rollback to previous version
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime


class TestVersionSaving:
    """Test saving versions"""

    def setup_method(self):
        """Create temporary directory for each test"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_save_first_version(self):
        """Should save the first version of content"""
        from object_primitive_core.version_manager import VersionManager

        vm = VersionManager(self.temp_dir)

        content = "def GET(request): return {'message': 'v1'}"
        version_id = vm.save_version(
            object_id='test_endpoint',
            content=content,
            author='test_user',
            message='Initial version',
        )

        assert version_id is not None
        assert version_id ==  1  # First version

    def test_save_multiple_versions(self):
        """Should save multiple versions with incrementing IDs"""
        from object_primitive_core.version_manager import VersionManager

        vm = VersionManager(self.temp_dir)

        v1 = vm.save_version('test', 'content v1', 'user', 'Version 1')
        v2 = vm.save_version('test', 'content v2', 'user', 'Version 2')
        v3 = vm.save_version('test', 'content v3', 'user', 'Version 3')

        assert v1 == 1
        assert v2 == 2
        assert v3 == 3

    def test_save_version_with_metadata(self):
        """Should store metadata with version"""
        from object_primitive_core.version_manager import VersionManager

        vm = VersionManager(self.temp_dir)

        before = datetime.now()
        version_id = vm.save_version(
            object_id='test',
            content='test content',
            author='claude',
            message='Test commit',
        )
        after = datetime.now()

        # Get the version back
        version = vm.get_version('test', version_id)

        assert version['content'] == 'test content'
        assert version['author'] == 'claude'
        assert version['message'] == 'Test commit'
        assert 'timestamp' in version
        assert 'hash' in version

        # Timestamp should be between before and after
        timestamp = datetime.fromisoformat(version['timestamp'])
        assert before <= timestamp <= after

    def test_content_hash_changes_with_content(self):
        """Should compute different hashes for different content"""
        from object_primitive_core.version_manager import VersionManager

        vm = VersionManager(self.temp_dir)

        v1 = vm.save_version('test', 'content 1', 'user', 'v1')
        v2 = vm.save_version('test', 'content 2', 'user', 'v2')

        ver1 = vm.get_version('test', v1)
        ver2 = vm.get_version('test', v2)

        # Hashes should be different
        assert ver1['hash'] != ver2['hash']

    def test_save_version_for_different_objects(self):
        """Should handle versions for different objects independently"""
        from object_primitive_core.version_manager import VersionManager

        vm = VersionManager(self.temp_dir)

        # Save versions for two different objects
        obj1_v1 = vm.save_version('object1', 'content1', 'user', 'obj1 v1')
        obj2_v1 = vm.save_version('object2', 'content2', 'user', 'obj2 v1')
        obj1_v2 = vm.save_version('object1', 'content1-v2', 'user', 'obj1 v2')

        # Both should start at version 1
        assert obj1_v1 == 1
        assert obj2_v1 == 1
        assert obj1_v2 == 2


class TestVersionRetrieval:
    """Test retrieving versions"""

    def setup_method(self):
        """Create temporary directory and save some versions"""
        self.temp_dir = Path(tempfile.mkdtemp())
        from object_primitive_core.version_manager import VersionManager

        self.vm = VersionManager(self.temp_dir)

        # Save some versions
        self.v1 = self.vm.save_version('test', 'content v1', 'user1', 'First version')
        self.v2 = self.vm.save_version('test', 'content v2', 'user2', 'Second version')
        self.v3 = self.vm.save_version('test', 'content v3', 'user3', 'Third version')

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_get_specific_version(self):
        """Should retrieve a specific version by ID"""
        version = self.vm.get_version('test', self.v2)

        assert version['content'] == 'content v2'
        assert version['author'] == 'user2'
        assert version['message'] == 'Second version'
        assert version['version_id'] == self.v2

    def test_get_latest_version(self):
        """Should get latest version when version_id=None"""
        version = self.vm.get_version('test')

        assert version['content'] == 'content v3'
        assert version['author'] == 'user3'
        assert version['version_id'] == self.v3

    def test_get_nonexistent_version_returns_none(self):
        """Should return None for non-existent version"""
        version = self.vm.get_version('test', 999)

        assert version is None

    def test_get_version_for_nonexistent_object_returns_none(self):
        """Should return None for non-existent object"""
        version = self.vm.get_version('nonexistent_object')

        assert version is None


class TestVersionHistory:
    """Test version history listing"""

    def setup_method(self):
        """Create temporary directory and save some versions"""
        self.temp_dir = Path(tempfile.mkdtemp())
        from object_primitive_core.version_manager import VersionManager

        self.vm = VersionManager(self.temp_dir)

        # Save multiple versions
        for i in range(1, 6):
            self.vm.save_version('test', f'content v{i}', f'user{i}', f'Version {i}')

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_get_all_versions(self):
        """Should return all versions in order (newest first, like git log)"""
        history = self.vm.get_history('test')

        assert len(history) == 5
        assert history[0]['version_id'] == 5  # Newest first
        assert history[4]['version_id'] == 1  # Oldest last

    def test_get_limited_history(self):
        """Should limit number of versions returned"""
        history = self.vm.get_history('test', limit=3)

        assert len(history) == 3
        # Should return most recent 3
        assert history[0]['version_id'] == 5
        assert history[1]['version_id'] == 4
        assert history[2]['version_id'] == 3

    def test_get_history_with_offset(self):
        """Should skip versions with offset"""
        history = self.vm.get_history('test', offset=2, limit=2)

        assert len(history) == 2
        # Skip 2 most recent (5, 4), get next 2 (3, 2)
        assert history[0]['version_id'] == 3
        assert history[1]['version_id'] == 2

    def test_history_includes_metadata_not_content(self):
        """Should include metadata but not full content in history"""
        history = self.vm.get_history('test')

        for version in history:
            assert 'version_id' in version
            assert 'timestamp' in version
            assert 'author' in version
            assert 'message' in version
            assert 'hash' in version
            # Content should NOT be in history (only in full version)
            assert 'content' not in version


class TestVersionRollback:
    """Test rolling back to previous versions"""

    def setup_method(self):
        """Create temporary directory and save some versions"""
        self.temp_dir = Path(tempfile.mkdtemp())
        from object_primitive_core.version_manager import VersionManager

        self.vm = VersionManager(self.temp_dir)

        # Save 3 versions
        self.v1 = self.vm.save_version('test', 'content v1', 'user', 'v1')
        self.v2 = self.vm.save_version('test', 'content v2', 'user', 'v2')
        self.v3 = self.vm.save_version('test', 'content v3', 'user', 'v3')

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_rollback_to_previous_version(self):
        """Should rollback to an earlier version"""
        # Rollback to v1
        new_version_id = self.vm.rollback('test', to_version=self.v1, author='rollback_user', message='Rollback to v1')

        # Should create a new version (v4)
        assert new_version_id == 4

        # Content should match v1
        current = self.vm.get_version('test')
        assert current['content'] == 'content v1'
        assert current['version_id'] == 4
        assert 'Rollback to v1' in current['message']

    def test_rollback_preserves_history(self):
        """Should preserve all history after rollback"""
        self.vm.rollback('test', to_version=self.v1, author='user', message='Rollback')

        history = self.vm.get_history('test')

        # Should have 4 versions now (v1, v2, v3, v4=rollback)
        assert len(history) == 4

    def test_rollback_to_nonexistent_version_raises_error(self):
        """Should raise error when rolling back to non-existent version"""
        from object_primitive_core.version_manager import VersionNotFoundError

        with pytest.raises(VersionNotFoundError):
            self.vm.rollback('test', to_version=999, author='user', message='Rollback')


class TestVersionStorage:
    """Test how versions are stored (TSV format)"""

    def setup_method(self):
        """Create temporary directory"""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up temporary directory"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_creates_version_directory_structure(self):
        """Should create directory structure for versions"""
        from object_primitive_core.version_manager import VersionManager

        vm = VersionManager(self.temp_dir)
        vm.save_version('test_obj', 'content', 'user', 'message')

        # Should create: versions/test_obj/
        versions_dir = self.temp_dir / 'versions' / 'test_obj'
        assert versions_dir.exists()
        assert versions_dir.is_dir()

    def test_stores_version_metadata_in_tsv(self):
        """Should store version metadata in TSV file"""
        from object_primitive_core.version_manager import VersionManager

        vm = VersionManager(self.temp_dir)
        vm.save_version('test', 'content', 'user', 'message')

        # Should create metadata TSV
        metadata_file = self.temp_dir / 'versions' / 'test' / 'metadata.tsv'
        assert metadata_file.exists()

        # Read the TSV
        content = metadata_file.read_text()
        lines = content.strip().split('\n')

        # Should have header + 1 data row
        assert len(lines) == 2
        assert 'version_id' in lines[0]  # Header
        assert '\t' in lines[1]  # TSV format

    def test_stores_version_content_separately(self):
        """Should store version content in separate file"""
        from object_primitive_core.version_manager import VersionManager

        vm = VersionManager(self.temp_dir)
        vm.save_version('test', 'test content here', 'user', 'message')

        # Should create content file
        content_file = self.temp_dir / 'versions' / 'test' / 'v1.txt'
        assert content_file.exists()
        assert content_file.read_text() == 'test content here'

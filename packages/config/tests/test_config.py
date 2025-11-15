"""
Tests for Config package

Tests environment.py (REST API for multi-source configuration)
"""

import pytest
import json
import os
import time
from pathlib import Path


class TestConfigAPI:
    """Test config REST API (environment.py)"""

    @pytest.fixture
    def config_obj(self, tmp_path):
        """Load config object"""
        from object_primitive_core.object_runtime import ObjectRuntime

        # Create runtime with temp directory
        runtime = ObjectRuntime(base_dir=str(tmp_path))

        # Load config object
        config_path = 'examples/config/environment.py'
        obj = runtime.load_object(config_path)

        return obj

    def test_set_config_value(self, config_obj):
        """Should set persistent config value"""
        result = config_obj.execute('POST', {
            'key': 'DATABASE_URL',
            'value': 'postgresql://localhost/mydb',
        })

        assert result['status'] == 'ok'
        assert result['key'] == 'DATABASE_URL'
        assert result['value'] == 'postgresql://localhost/mydb'
        assert 'Config set' in result['message']

    def test_get_config_value(self, config_obj):
        """Should get config value"""
        # Set first
        config_obj.execute('POST', {
            'key': 'API_KEY',
            'value': 'secret123',
        })

        # Get
        result = config_obj.execute('GET', {'key': 'API_KEY'})

        assert result['status'] == 'ok'
        assert result['key'] == 'API_KEY'
        assert result['value'] == 'secret123'
        assert result['source'] == 'config'

    def test_get_config_requires_key(self, config_obj):
        """Should reject get without key"""
        result = config_obj.execute('GET', {})

        assert result['status'] == 'error'
        assert 'key is required' in result['message']

    def test_get_nonexistent_config(self, config_obj):
        """Should return error for nonexistent config"""
        result = config_obj.execute('GET', {'key': 'NONEXISTENT'})

        assert result['status'] == 'error'
        assert 'not found' in result['message']

    def test_get_config_with_default(self, config_obj):
        """Should return default value if config not found"""
        result = config_obj.execute('GET', {
            'key': 'NONEXISTENT',
            'default': 'default_value',
        })

        assert result['status'] == 'ok'
        assert result['value'] == 'default_value'
        assert result['source'] == 'default'

    def test_set_runtime_override(self, config_obj):
        """Should set runtime override (temporary)"""
        result = config_obj.execute('PUT', {
            'key': 'TEST_MODE',
            'value': 'true',
            'ttl': 10,
        })

        assert result['status'] == 'ok'
        assert result['key'] == 'TEST_MODE'
        assert result['value'] == 'true'
        assert result['ttl'] == 10
        assert 'override set' in result['message']

    def test_override_has_priority(self, config_obj):
        """Runtime override should have priority over persistent config"""
        # Set persistent config
        config_obj.execute('POST', {
            'key': 'MODE',
            'value': 'production',
        })

        # Set runtime override
        config_obj.execute('PUT', {
            'key': 'MODE',
            'value': 'testing',
            'ttl': 10,
        })

        # Get should return override
        result = config_obj.execute('GET', {'key': 'MODE'})

        assert result['status'] == 'ok'
        assert result['value'] == 'testing'
        assert result['source'] == 'override'

    def test_environment_variable_priority(self, config_obj, monkeypatch):
        """Environment variable should have priority over persistent config"""
        # Set persistent config
        config_obj.execute('POST', {
            'key': 'ENV_TEST',
            'value': 'from_config',
        })

        # Set environment variable
        monkeypatch.setenv('ENV_TEST', 'from_env')

        # Get should return env var
        result = config_obj.execute('GET', {'key': 'ENV_TEST'})

        assert result['status'] == 'ok'
        assert result['value'] == 'from_env'
        assert result['source'] == 'environment'

    def test_override_expires(self, config_obj):
        """Runtime override should expire after TTL"""
        # Set persistent config first
        config_obj.execute('POST', {
            'key': 'EXPIRES',
            'value': 'persistent',
        })

        # Set override with short TTL
        config_obj.execute('PUT', {
            'key': 'EXPIRES',
            'value': 'temporary',
            'ttl': 1,
        })

        # Immediately get - should have override
        result1 = config_obj.execute('GET', {'key': 'EXPIRES'})
        assert result1['value'] == 'temporary'
        assert result1['source'] == 'override'

        # Wait for expiration
        time.sleep(1.1)

        # Get again - should fall back to persistent config
        result2 = config_obj.execute('GET', {'key': 'EXPIRES'})
        assert result2['status'] == 'ok'
        assert result2['value'] == 'persistent'
        assert result2['source'] == 'config'

    def test_delete_config(self, config_obj):
        """Should delete config value"""
        # Set config
        config_obj.execute('POST', {
            'key': 'TO_DELETE',
            'value': 'delete_me',
        })

        # Delete
        result = config_obj.execute('DELETE', {'key': 'TO_DELETE'})

        assert result['status'] == 'ok'
        assert 'deleted' in result['message']

        # Verify deleted
        get_result = config_obj.execute('GET', {'key': 'TO_DELETE'})
        assert get_result['status'] == 'error'

    def test_delete_override_only(self, config_obj):
        """Should delete only override, not persistent config"""
        # Set persistent config
        config_obj.execute('POST', {
            'key': 'KEEP_CONFIG',
            'value': 'persistent',
        })

        # Set override
        config_obj.execute('PUT', {
            'key': 'KEEP_CONFIG',
            'value': 'override',
            'ttl': 10,
        })

        # Delete override only
        result = config_obj.execute('DELETE', {
            'key': 'KEEP_CONFIG',
            'override_only': True,
        })

        assert result['status'] == 'ok'
        assert result['override_deleted'] is True
        assert result['config_deleted'] is False

        # Get should return persistent config
        get_result = config_obj.execute('GET', {'key': 'KEEP_CONFIG'})
        assert get_result['value'] == 'persistent'
        assert get_result['source'] == 'config'

    def test_type_validation_string(self, config_obj):
        """Should validate string type"""
        result = config_obj.execute('POST', {
            'key': 'STRING_VAR',
            'value': 'hello',
            'type': 'string',
        })

        assert result['status'] == 'ok'
        assert result['value'] == 'hello'

    def test_type_validation_int(self, config_obj):
        """Should validate int type"""
        result = config_obj.execute('POST', {
            'key': 'PORT',
            'value': '8000',
            'type': 'int',
        })

        assert result['status'] == 'ok'
        assert result['value'] == 8000

    def test_type_validation_int_invalid(self, config_obj):
        """Should reject invalid int"""
        result = config_obj.execute('POST', {
            'key': 'PORT',
            'value': 'not_a_number',
            'type': 'int',
        })

        assert result['status'] == 'error'
        assert 'Invalid int' in result['message']

    def test_type_validation_bool(self, config_obj):
        """Should validate bool type"""
        result = config_obj.execute('POST', {
            'key': 'DEBUG',
            'value': 'true',
            'type': 'bool',
        })

        assert result['status'] == 'ok'
        assert result['value'] is True

    def test_type_validation_json(self, config_obj):
        """Should validate JSON type"""
        result = config_obj.execute('POST', {
            'key': 'SETTINGS',
            'value': {'timeout': 30, 'retries': 3},
            'type': 'json',
        })

        assert result['status'] == 'ok'
        assert result['value'] == {'timeout': 30, 'retries': 3}

    def test_list_all_config(self, config_obj):
        """Should list all config values"""
        # Set some config
        config_obj.execute('POST', {
            'key': 'CONFIG1',
            'value': 'value1',
        })

        config_obj.execute('POST', {
            'key': 'CONFIG2',
            'value': 'value2',
        })

        # List
        result = config_obj.execute('GET', {'list': 'true'})

        assert result['status'] == 'ok'
        assert 'config' in result
        assert 'CONFIG1' in result['config']
        assert 'CONFIG2' in result['config']
        assert result['config']['CONFIG1'] == 'value1'
        assert result['config']['CONFIG2'] == 'value2'

    def test_list_shows_overrides(self, config_obj):
        """List should show runtime overrides separately"""
        # Set config
        config_obj.execute('POST', {
            'key': 'VAR1',
            'value': 'config_value',
        })

        # Set override
        config_obj.execute('PUT', {
            'key': 'VAR1',
            'value': 'override_value',
            'ttl': 10,
        })

        # List
        result = config_obj.execute('GET', {'list': 'true'})

        assert result['status'] == 'ok'
        assert 'config' in result
        assert 'overrides' in result
        assert result['config']['VAR1'] == 'config_value'
        assert result['overrides']['VAR1'] == 'override_value'

    def test_config_persistence(self, config_obj):
        """Config should persist in state"""
        # Set config
        result = config_obj.execute('POST', {
            'key': 'PERSIST_TEST',
            'value': 'persisted',
        })

        assert result['status'] == 'ok'

        # Access state manager directly
        state_mgr = config_obj.state_manager
        config_json = state_mgr.get('config_PERSIST_TEST')

        assert config_json is not None
        config = json.loads(config_json)
        assert config['key'] == 'PERSIST_TEST'
        assert config['value'] == 'persisted'

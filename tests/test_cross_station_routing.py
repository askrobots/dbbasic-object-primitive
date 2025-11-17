"""
Tests for cross-station object routing (Phase 7.2)

Tests the object_id@station_id routing syntax that allows
calling objects on remote stations in the cluster.
"""
import json
import os
import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import requests
import importlib.util
# import sys


# Helper function to load the [id].py module
def load_objects_id_module():
    """Load the api/objects/[id].py module"""
    module_path = Path(__file__).parent.parent / 'api' / 'objects' / '[id].py'
    spec = importlib.util.spec_from_file_location('objects_id_api', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRoutingSyntaxParsing:
    """Test parsing of object_id@station_id syntax"""

    def test_parse_local_object(self):
        """Test parsing object ID without station routing"""
        obj_api = load_objects_id_module()

        object_id, station_id = obj_api.parse_object_routing('calculator')

        assert object_id == 'calculator'
        assert station_id is None

    def test_parse_remote_object(self):
        """Test parsing object ID with station routing"""
        obj_api = load_objects_id_module()

        object_id, station_id = obj_api.parse_object_routing('calculator@station2')

        assert object_id == 'calculator'
        assert station_id == 'station2'

    def test_parse_object_with_underscores(self):
        """Test parsing complex object IDs with underscores"""
        obj_api = load_objects_id_module()

        object_id, station_id = obj_api.parse_object_routing('tutorial_04_calculator@station3')

        assert object_id == 'tutorial_04_calculator'
        assert station_id == 'station3'

    def test_parse_multiple_at_signs(self):
        """Test parsing with multiple @ signs (only first is used)"""
        obj_api = load_objects_id_module()

        # Only split on first @
        object_id, station_id = obj_api.parse_object_routing('obj@station2@invalid')

        assert object_id == 'obj'
        assert station_id == 'station2@invalid'


class TestStationLookup:
    """Test looking up stations in cluster registry"""

    @pytest.fixture
    def mock_registry_file(self, tmp_path):
        """Create a mock cluster registry file"""
        registry_dir = tmp_path / 'data' / 'cluster'
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry_file = registry_dir / 'stations.tsv'

        current_time = time.time()

        # Write registry with 3 stations
        # Using RFC 5737 TEST-NET-1 addresses (192.0.2.0/24)
        # station1: active (master)
        # station2: active (worker)
        # station3: inactive (old heartbeat)
        with open(registry_file, 'w') as f:
            f.write(f'station1\t192.0.2.1\t8001\t{current_time}\n')
            f.write(f'station2\t192.0.2.2\t8001\t{current_time - 10}\n')
            f.write(f'station3\t192.0.2.3\t8001\t{current_time - 100}\n')

        return registry_file

    def test_lookup_active_station(self, mock_registry_file):
        """Test looking up an active station"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        # Temporarily change data path
        original_cwd = os.getcwd()
        os.chdir(mock_registry_file.parent.parent.parent)

        try:
            station_info = obj_api.get_station_info('station2')

            assert station_info is not None
            assert station_info['station_id'] == 'station2'
            assert station_info['host'] == '192.0.2.2'
            assert station_info['port'] == 8001
            assert station_info['is_active'] is True
            assert station_info['url'] == 'http://192.0.2.2:8001'
        finally:
            os.chdir(original_cwd)

    def test_lookup_inactive_station(self, mock_registry_file):
        """Test looking up an inactive station (old heartbeat)"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        original_cwd = os.getcwd()
        os.chdir(mock_registry_file.parent.parent.parent)

        try:
            station_info = obj_api.get_station_info('station3')

            # Should return None because station3 has old heartbeat (100 seconds ago)
            assert station_info is None
        finally:
            os.chdir(original_cwd)

    def test_lookup_nonexistent_station(self, mock_registry_file):
        """Test looking up a station that doesn't exist"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        original_cwd = os.getcwd()
        os.chdir(mock_registry_file.parent.parent.parent)

        try:
            station_info = obj_api.get_station_info('station99')

            assert station_info is None
        finally:
            os.chdir(original_cwd)


class TestRequestForwarding:
    """Test forwarding HTTP requests to remote stations"""

    def test_forward_get_request(self):
        """Test forwarding a GET request"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        station_info = {
            'station_id': 'station2',
            'host': '192.0.2.2',
            'port': 8001,
            'url': 'http://192.0.2.2:8001',
            'is_active': True
        }

        # Mock the requests.get call
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                'status': 'ok',
                'result': 8.0,
                'object_id': 'calculator'
            }
            mock_get.return_value = mock_response

            result = obj_api.forward_request(
                station_info=station_info,
                object_id='calculator',
                method='GET',
                query_params={'operation': 'add', 'a': '5', 'b': '3'}
            )

            # Verify request was made correctly
            mock_get.assert_called_once_with(
                'http://192.0.2.2:8001/objects/calculator',
                params={'operation': 'add', 'a': '5', 'b': '3'},
                timeout=30
            )

            # Verify routing metadata added
            assert result['_routed_to'] == 'station2'
            assert '_routed_from' in result

    def test_forward_post_request(self):
        """Test forwarding a POST request with body data"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        station_info = {
            'station_id': 'station3',
            'host': '192.0.2.3',
            'port': 8001,
            'url': 'http://192.0.2.3:8001',
            'is_active': True
        }

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {
                'status': 'ok',
                'count': 5
            }
            mock_post.return_value = mock_response

            body_data = {'action': 'increment', 'amount': 5}

            result = obj_api.forward_request(
                station_info=station_info,
                object_id='counter',
                method='POST',
                body_data=body_data
            )

            # Verify request was made correctly
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args[1]['json'] == body_data
            assert call_args[1]['headers']['Content-Type'] == 'application/json'

    def test_forward_request_timeout(self):
        """Test handling timeout when forwarding request"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        station_info = {
            'station_id': 'station2',
            'host': '192.0.2.2',
            'port': 8001,
            'url': 'http://192.0.2.2:8001',
            'is_active': True
        }

        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.Timeout('Connection timeout')

            with pytest.raises(requests.Timeout):
                obj_api.forward_request(
                    station_info=station_info,
                    object_id='calculator',
                    method='GET'
                )

    def test_forward_request_network_error(self):
        """Test handling network errors when forwarding request"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        station_info = {
            'station_id': 'station2',
            'host': '192.0.2.2',
            'port': 8001,
            'url': 'http://192.0.2.2:8001',
            'is_active': True
        }

        with patch('requests.get') as mock_get:
            mock_get.side_effect = requests.ConnectionError('Connection refused')

            with pytest.raises(requests.ConnectionError):
                obj_api.forward_request(
                    station_info=station_info,
                    object_id='calculator',
                    method='GET'
                )


class TestEndToEndRouting:
    """Test complete routing flow from request to response"""

    @pytest.fixture
    def setup_test_env(self, tmp_path, monkeypatch):
        """Set up test environment with registry"""
        # Create registry
        registry_dir = tmp_path / 'data' / 'cluster'
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry_file = registry_dir / 'stations.tsv'

        current_time = time.time()
        with open(registry_file, 'w') as f:
            f.write(f'station1\t192.0.2.1\t8001\t{current_time}\n')
            f.write(f'station2\t192.0.2.2\t8001\t{current_time}\n')

        # Change to test directory
        original_cwd = os.getcwd()
        os.chdir(tmp_path)

        # Set station ID
        monkeypatch.setenv('STATION_ID', 'station1')

        yield tmp_path

        # Restore
        os.chdir(original_cwd)

    def test_route_to_remote_station(self, setup_test_env):
        """Test routing object@station2 from station1"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        # Mock HTTP request
        mock_request = Mock()
        mock_request.GET = {'operation': 'add', 'a': '5', 'b': '3'}

        # Mock the actual HTTP call to station2
        with patch('requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                'status': 'ok',
                'result': 8.0
            }
            mock_get.return_value = mock_response

            # Call the GET handler with calculator@station2
            response = obj_api.GET(mock_request, 'calculator@station2')

            # Verify it made the remote call
            mock_get.assert_called_once()

            # Verify response contains routing metadata
            # Response is a tuple (status_code, headers, body)
            status_code, headers, body = response; body = body[0] if isinstance(body, list) else body
            response_data = json.loads(body)
            assert response_data['_routed_to'] == 'station2'
            assert response_data['_routed_from'] == 'station1'

    def test_route_to_local_station(self, setup_test_env):
        """Test routing object@station1 (local) from station1"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        mock_request = Mock()
        mock_request.GET = {}

        # When routing to self, should execute locally
        # Mock find_object_file to return None (object not found)
        with patch.object(obj_api, 'find_object_file', return_value=None):
            response = obj_api.GET(mock_request, 'nonexistent@station1')

            # Should get 404 (local execution attempted)
            status_code, headers, body = response; body = body[0] if isinstance(body, list) else body
            response_data = json.loads(body)
            # Error response has 'error' key
            assert 'error' in response_data
            assert 'not found' in response_data['error'].lower()

    def test_route_to_offline_station(self, setup_test_env):
        """Test routing to a station that's offline"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        # Add offline station to registry
        registry_file = setup_test_env / 'data' / 'cluster' / 'stations.tsv'
        with open(registry_file, 'a') as f:
            f.write(f'station3\t192.0.2.3\t8001\t{time.time() - 100}\n')

        mock_request = Mock()
        mock_request.GET = {}

        # Route to offline station
        response = obj_api.GET(mock_request, 'calculator@station3')

        # Should get 503 Service Unavailable
        status_code, headers, body = response; body = body[0] if isinstance(body, list) else body
        response_data = json.loads(body)
        assert 'error' in response_data
        assert 'offline' in response_data['error'].lower()

    def test_route_to_nonexistent_station(self, setup_test_env):
        """Test routing to a station that doesn't exist"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        mock_request = Mock()
        mock_request.GET = {}

        # Route to nonexistent station
        response = obj_api.GET(mock_request, 'calculator@station99')

        # Should get 503 Service Unavailable
        status_code, headers, body = response; body = body[0] if isinstance(body, list) else body
        response_data = json.loads(body)
        assert 'error' in response_data
        assert 'not found' in response_data['error'].lower()


class TestAllHTTPMethods:
    """Test routing works for all HTTP methods"""

    @pytest.fixture
    def setup_test_env(self, tmp_path, monkeypatch):
        """Set up test environment"""
        registry_dir = tmp_path / 'data' / 'cluster'
        registry_dir.mkdir(parents=True, exist_ok=True)
        registry_file = registry_dir / 'stations.tsv'

        current_time = time.time()
        with open(registry_file, 'w') as f:
            f.write(f'station1\t192.0.2.1\t8001\t{current_time}\n')
            f.write(f'station2\t192.0.2.2\t8001\t{current_time}\n')

        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        monkeypatch.setenv('STATION_ID', 'station1')

        yield tmp_path

        os.chdir(original_cwd)

    def test_post_routing(self, setup_test_env):
        """Test POST request routing"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        mock_request = Mock()
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.body = json.dumps({'action': 'increment'}).encode('utf-8')

        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.json.return_value = {'status': 'ok'}
            mock_post.return_value = mock_response

            response = obj_api.POST(mock_request, 'counter@station2')

            mock_post.assert_called_once()
            status_code, headers, body = response; body = body[0] if isinstance(body, list) else body
            response_data = json.loads(body)
            assert response_data['_routed_to'] == 'station2'

    def test_put_routing(self, setup_test_env):
        """Test PUT request routing"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        mock_request = Mock()
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.body = json.dumps({'value': 42}).encode('utf-8')

        with patch('requests.put') as mock_put:
            mock_response = Mock()
            mock_response.json.return_value = {'status': 'ok'}
            mock_put.return_value = mock_response

            response = obj_api.PUT(mock_request, 'config@station2')

            mock_put.assert_called_once()
            status_code, headers, body = response; body = body[0] if isinstance(body, list) else body
            response_data = json.loads(body)
            assert response_data['_routed_to'] == 'station2'

    def test_delete_routing(self, setup_test_env):
        """Test DELETE request routing"""
        # import sys
        # sys.path.insert(0, str(Path(__file__).parent.parent))
        obj_api = load_objects_id_module()

        mock_request = Mock()
        mock_request.GET = {}
        mock_request.POST = {}
        mock_request.body = json.dumps({'confirm': True}).encode('utf-8')

        with patch('requests.delete') as mock_delete:
            mock_response = Mock()
            mock_response.json.return_value = {'status': 'ok'}
            mock_delete.return_value = mock_response

            response = obj_api.DELETE(mock_request, 'temp_data@station2')

            mock_delete.assert_called_once()
            status_code, headers, body = response; body = body[0] if isinstance(body, list) else body
            response_data = json.loads(body)
            assert response_data['_routed_to'] == 'station2'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

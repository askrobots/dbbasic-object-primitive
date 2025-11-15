"""
Unit tests for endpoint_loader

Test-Driven Development: These tests are written FIRST, before implementation.
They define the expected behavior of the endpoint loader.
"""

import pytest
import os
from pathlib import Path


class TestEndpointLoaderBasics:
    """Test basic endpoint loading functionality"""

    def test_import_endpoint_module(self):
        """Should import an endpoint file as a Python module"""
        from src.object_primitive.core.endpoint_loader import load_endpoint

        # Load the hello endpoint fixture
        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py'
        endpoint = load_endpoint(endpoint_path)

        assert endpoint is not None
        assert hasattr(endpoint, 'GET')
        assert hasattr(endpoint, 'POST')
        # hello.py only has GET and POST, not PUT/DELETE

    def test_load_endpoint_by_string_path(self):
        """Should accept path as string"""
        from src.object_primitive.core.endpoint_loader import load_endpoint

        endpoint_path = str(Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py')
        endpoint = load_endpoint(endpoint_path)

        assert endpoint is not None

    def test_load_nonexistent_endpoint_raises_error(self):
        """Should raise error when endpoint file doesn't exist"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, EndpointNotFoundError

        with pytest.raises(EndpointNotFoundError):
            load_endpoint('/nonexistent/path/to/endpoint.py')

    def test_load_invalid_python_raises_error(self):
        """Should raise error when endpoint file has syntax errors"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, EndpointLoadError

        # Create a temporary file with invalid Python
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def invalid syntax here\n')
            temp_path = f.name

        try:
            with pytest.raises(EndpointLoadError):
                load_endpoint(temp_path)
        finally:
            os.unlink(temp_path)


class TestEndpointExecution:
    """Test executing endpoint methods"""

    def test_execute_get_method(self):
        """Should execute GET method and return result"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, execute_endpoint

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py'
        endpoint = load_endpoint(endpoint_path)

        result = execute_endpoint(endpoint, 'GET', {})

        assert result['status'] == 'ok'
        assert result['message'] == 'Hello, World!'
        assert result['method'] == 'GET'

    def test_execute_post_method(self):
        """Should execute POST method with data"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, execute_endpoint

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py'
        endpoint = load_endpoint(endpoint_path)

        result = execute_endpoint(endpoint, 'POST', {'name': 'Claude'})

        assert result['status'] == 'ok'
        assert result['message'] == 'Hello, Claude!'
        assert result['method'] == 'POST'

    def test_execute_unsupported_method_raises_error(self):
        """Should raise error for unsupported HTTP methods"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, execute_endpoint, MethodNotSupportedError

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py'
        endpoint = load_endpoint(endpoint_path)

        with pytest.raises(MethodNotSupportedError):
            execute_endpoint(endpoint, 'PATCH', {})

    def test_execute_method_that_raises_exception(self):
        """Should catch and wrap exceptions from endpoint code"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, execute_endpoint, EndpointExecutionError

        # Create a temporary endpoint that raises an error
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('''
def GET(request):
    raise ValueError("Something went wrong")
''')
            temp_path = f.name

        try:
            endpoint = load_endpoint(temp_path)
            with pytest.raises(EndpointExecutionError) as exc_info:
                execute_endpoint(endpoint, 'GET', {})

            # Should include the original exception
            assert 'ValueError' in str(exc_info.value)
            assert 'Something went wrong' in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestEndpointMetadata:
    """Test reading endpoint metadata"""

    def test_read_endpoint_metadata(self):
        """Should read __endpoint__ metadata from endpoint"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, get_endpoint_metadata

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py'
        endpoint = load_endpoint(endpoint_path)

        metadata = get_endpoint_metadata(endpoint)

        assert metadata['name'] == 'hello'
        assert metadata['description'] == 'Simple hello world endpoint for testing'
        assert metadata['version'] == '1.0.0'
        assert metadata['author'] == 'test'

    def test_endpoint_without_metadata_returns_defaults(self):
        """Should return default metadata if __endpoint__ not present"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, get_endpoint_metadata

        # Create a temporary endpoint without metadata
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write('def GET(request): return {}')
            temp_path = f.name

        try:
            endpoint = load_endpoint(temp_path)
            metadata = get_endpoint_metadata(endpoint)

            assert 'name' in metadata
            assert 'version' in metadata
        finally:
            os.unlink(temp_path)


class TestEndpointValidation:
    """Test validation of calculator endpoint"""

    def test_calculator_add_operation(self):
        """Should perform addition correctly"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, execute_endpoint

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'calculator.py'
        endpoint = load_endpoint(endpoint_path)

        result = execute_endpoint(endpoint, 'POST', {
            'operation': 'add',
            'a': 5,
            'b': 3,
        })

        assert result['status'] == 'ok'
        assert result['result'] == 8

    def test_calculator_division_by_zero(self):
        """Should handle division by zero gracefully"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, execute_endpoint

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'calculator.py'
        endpoint = load_endpoint(endpoint_path)

        result = execute_endpoint(endpoint, 'POST', {
            'operation': 'divide',
            'a': 10,
            'b': 0,
        })

        assert result['status'] == 'error'
        assert 'Division by zero' in result['error']

    def test_calculator_invalid_operation(self):
        """Should reject invalid operations"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, execute_endpoint

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'calculator.py'
        endpoint = load_endpoint(endpoint_path)

        result = execute_endpoint(endpoint, 'POST', {
            'operation': 'power',
            'a': 2,
            'b': 3,
        })

        assert result['status'] == 'error'
        assert 'Invalid operation' in result['error']

    def test_calculator_missing_parameters(self):
        """Should reject missing parameters"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, execute_endpoint

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'calculator.py'
        endpoint = load_endpoint(endpoint_path)

        result = execute_endpoint(endpoint, 'POST', {
            'operation': 'add',
            'a': 5,
        })

        assert result['status'] == 'error'
        assert 'Missing parameters' in result['error']


class TestEndpointCaching:
    """Test caching of loaded endpoints"""

    def test_cache_loaded_endpoints(self):
        """Should cache endpoints to avoid reloading"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, clear_cache, get_cache_stats

        clear_cache()

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py'

        # First load
        endpoint1 = load_endpoint(endpoint_path)
        stats1 = get_cache_stats()

        # Second load (should hit cache)
        endpoint2 = load_endpoint(endpoint_path)
        stats2 = get_cache_stats()

        # Should be the same object (from cache)
        assert endpoint1 is endpoint2
        assert stats2['hits'] > stats1['hits']

    def test_clear_cache(self):
        """Should clear the endpoint cache"""
        from src.object_primitive.core.endpoint_loader import load_endpoint, clear_cache, get_cache_stats

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py'
        load_endpoint(endpoint_path)

        clear_cache()
        stats = get_cache_stats()

        assert stats['size'] == 0

    def test_reload_endpoint_bypasses_cache(self):
        """Should reload endpoint when reload=True"""
        from src.object_primitive.core.endpoint_loader import load_endpoint

        endpoint_path = Path(__file__).parent.parent / 'fixtures' / 'endpoints' / 'hello.py'

        endpoint1 = load_endpoint(endpoint_path)
        endpoint2 = load_endpoint(endpoint_path, reload=True)

        # Should be different objects (reloaded)
        assert endpoint1 is not endpoint2

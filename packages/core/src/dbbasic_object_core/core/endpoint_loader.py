"""
Endpoint Loader

Loads endpoint Python files as modules and executes their HTTP methods.

Design principles:
- Endpoints are Python files with GET/POST/PUT/DELETE functions
- Each endpoint is a module that can be imported
- Endpoints are cached for performance
- Errors are caught and wrapped with context
"""

import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, Optional
import traceback


# Custom exceptions
class EndpointError(Exception):
    """Base exception for endpoint-related errors"""
    pass


class EndpointNotFoundError(EndpointError):
    """Raised when endpoint file doesn't exist"""
    pass


class EndpointLoadError(EndpointError):
    """Raised when endpoint file can't be loaded (syntax error, import error)"""
    pass


class MethodNotSupportedError(EndpointError):
    """Raised when HTTP method not supported by endpoint"""
    pass


class EndpointExecutionError(EndpointError):
    """Raised when endpoint execution fails"""
    pass


# Endpoint cache
_endpoint_cache: Dict[str, Any] = {}
_cache_stats = {'hits': 0, 'misses': 0}


def load_endpoint(path: str | Path, reload: bool = False) -> Any:
    """
    Load an endpoint Python file as a module.

    Args:
        path: Path to the endpoint .py file
        reload: If True, bypass cache and reload the module

    Returns:
        The loaded module object

    Raises:
        EndpointNotFoundError: If file doesn't exist
        EndpointLoadError: If file can't be loaded (syntax error, etc.)
    """
    # Convert to Path object
    path = Path(path)
    path_str = str(path.absolute())

    # Check cache (unless reload=True)
    if not reload and path_str in _endpoint_cache:
        _cache_stats['hits'] += 1
        return _endpoint_cache[path_str]

    _cache_stats['misses'] += 1

    # Check if file exists
    if not path.exists():
        raise EndpointNotFoundError(f"Endpoint file not found: {path}")

    if not path.is_file():
        raise EndpointNotFoundError(f"Path is not a file: {path}")

    # Load the module
    try:
        # Create a module spec
        module_name = f"endpoint_{path.stem}_{id(path)}"
        spec = importlib.util.spec_from_file_location(module_name, path)

        if spec is None or spec.loader is None:
            raise EndpointLoadError(f"Could not create module spec for: {path}")

        # Create the module
        module = importlib.util.module_from_spec(spec)

        # Add to sys.modules temporarily
        sys.modules[module_name] = module

        # Execute the module (loads it)
        spec.loader.exec_module(module)

        # Cache it
        _endpoint_cache[path_str] = module

        return module

    except SyntaxError as e:
        raise EndpointLoadError(f"Syntax error in endpoint {path}: {e}")
    except Exception as e:
        raise EndpointLoadError(f"Failed to load endpoint {path}: {e}\n{traceback.format_exc()}")


def execute_endpoint(endpoint: Any, method: str, request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute an HTTP method on an endpoint.

    Args:
        endpoint: The loaded endpoint module
        method: HTTP method name (GET, POST, PUT, DELETE, etc.)
        request: Request data dictionary

    Returns:
        Response dictionary from the endpoint

    Raises:
        MethodNotSupportedError: If method not supported
        EndpointExecutionError: If execution fails
    """
    # Check if method exists
    if not hasattr(endpoint, method):
        raise MethodNotSupportedError(
            f"Method {method} not supported by endpoint. "
            f"Available methods: {_get_available_methods(endpoint)}"
        )

    # Get the method function
    method_func = getattr(endpoint, method)

    # Execute it
    try:
        result = method_func(request)
        return result
    except Exception as e:
        # Wrap the exception with context
        raise EndpointExecutionError(
            f"Endpoint execution failed for {method}: {type(e).__name__}: {e}\n"
            f"{traceback.format_exc()}"
        )


def get_endpoint_metadata(endpoint: Any) -> Dict[str, Any]:
    """
    Get metadata from an endpoint module.

    Looks for __endpoint__ dict in the module.

    Args:
        endpoint: The loaded endpoint module

    Returns:
        Metadata dictionary (with defaults if not present)
    """
    if hasattr(endpoint, '__endpoint__'):
        return getattr(endpoint, '__endpoint__')

    # Return defaults
    return {
        'name': getattr(endpoint, '__name__', 'unknown'),
        'version': '0.0.0',
        'description': '',
        'author': 'unknown',
    }


def clear_cache():
    """Clear the endpoint cache"""
    global _endpoint_cache, _cache_stats
    _endpoint_cache.clear()
    _cache_stats = {'hits': 0, 'misses': 0}


def get_cache_stats() -> Dict[str, int]:
    """
    Get cache statistics.

    Returns:
        Dict with 'hits', 'misses', 'size'
    """
    return {
        'hits': _cache_stats['hits'],
        'misses': _cache_stats['misses'],
        'size': len(_endpoint_cache),
    }


def _get_available_methods(endpoint: Any) -> list[str]:
    """Helper: Get list of available HTTP methods on endpoint"""
    http_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
    return [m for m in http_methods if hasattr(endpoint, m)]

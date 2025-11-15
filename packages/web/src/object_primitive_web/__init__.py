"""
dbbasic-objects-web: REST API for Object Primitives

HTTP trigger layer - provides REST API for executing, inspecting,
and modifying objects over HTTP.
"""

__version__ = "0.1.0"
__author__ = "Dan Quellhorst"
__license__ = "MIT"

# Main exports
from .server import main

__all__ = ["main"]

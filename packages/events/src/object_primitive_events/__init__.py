"""
dbbasic-objects-events: Event-based triggers for Object Primitives

Pub/Sub event system - publish events and subscribe to event types.
"""

__version__ = "0.1.0"
__author__ = "Dan Quellhorst"
__license__ = "MIT"

# No daemon for events (unlike scheduler)
# Events are handled synchronously via REST API
# Future: Add async event delivery daemon

__all__ = []

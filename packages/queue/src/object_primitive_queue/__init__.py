"""
dbbasic-objects-queue: Message queue triggers for Object Primitives

Task queue system - enqueue messages, dequeue with priority, acknowledgement.
"""

__version__ = "0.1.0"
__author__ = "Dan Quellhorst"
__license__ = "MIT"

# No daemon needed for queue (workers poll via GET)
# Workers handle their own polling and processing

__all__ = []

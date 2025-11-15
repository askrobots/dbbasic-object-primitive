"""
Object Primitive: A new computing paradigm.

Where code, data, and execution are unified into network-accessible objects.

The Object Primitive System provides:
- Protocol-agnostic access (REST, gRPC, WebSocket, MQTT, 9P, etc.)
- Implementation-agnostic execution (Python, C, Rust, GPU, ASIC)
- OS-agnostic deployment (Linux, macOS, Windows, BSD, Plan 9, etc.)
- Self-logging objects (objects log to themselves)
- Automatic versioning (complete history)
- Self-healing and resilient (designed for chaos from the start)

Core Philosophy:
- The endpoint is the eternal truth (business logic)
- Everything else is swappable (protocols, implementations, storage, OS)
- This is NOT an ORM (we isolate stability, not hide complexity)
- We don't care what changes (vendors, hardware, protocols, databases)

Example:
    >>> from object_primitive import ObjectPrimitive
    >>>
    >>> # Define an endpoint
    >>> def GET(request):
    ...     return {"result": process(request)}
    >>>
    >>> # Create object primitive
    >>> obj = ObjectPrimitive("/myservice", GET)
    >>>
    >>> # Accessible via any protocol
    >>> # - HTTP: curl http://server/myservice
    >>> # - 9P: mount server:/endpoints /mnt
    >>> # - WebSocket: ws://server/myservice
    >>> # - MQTT: pub/sub to myservice

Architecture:
    The stable invariant (endpoint logic) sits at the center.
    Three dimensions of abstraction surround it:
    - Protocol (how accessed)
    - Implementation (how executed)
    - OS (where runs)

    Write once. Access anywhere. Execute with anything. Run everywhere.
"""

__version__ = "0.1.0"
__author__ = "Dan Q"
__email__ = "danq@dbbasic.com"

# Core exports (will be populated as we implement)
__all__ = [
    "__version__",
    # Core primitives (to be added in Phase 1)
    # "ObjectPrimitive",
    # "EndpointLoader",
    # "VersionManager",
]

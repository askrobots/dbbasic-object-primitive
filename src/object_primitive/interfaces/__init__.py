"""
Protocol interfaces for the Object Primitive System.

This module contains adapters for different protocols:
- REST: HTTP/REST interface (via dbbasic-web)
- gRPC: High-performance RPC interface
- WebSocket: Real-time bidirectional communication
- MQTT: Pub/sub messaging for IoT
- TCP: Raw TCP socket interface
- Events: Event-driven interface
- 9P: Plan 9 filesystem protocol
- Unix Sockets: Local IPC

The endpoint code doesn't know or care which protocol is used.
Protocol adapters translate between protocols and the universal interface.

Philosophy:
    Protocols are just transport. They come and go (REST, gRPC, ???).
    The endpoint stays stable. We add protocols without changing logic.

    Same endpoint, accessed via:
    - curl http://server/endpoint (REST)
    - mount server:/endpoints /mnt (9P)
    - ws://server/endpoint (WebSocket)
    - mqtt pub endpoint (MQTT)
"""

__all__ = [
    # To be implemented in Phase 2+
    # "RESTInterface",
    # "WebSocketInterface",
    # "gRPCInterface",
    # "MQTTInterface",
    # "Plan9Interface",
]

"""
Runtime execution engine for the Object Primitive System.

This module handles the execution of endpoint code:
- Endpoint execution (run user code)
- Compilation (Python bytecode compilation)
- Caching (compiled endpoint caching)
- Hot reload (update code without restart)
- Sandboxing (security isolation)
- Resource limits (CPU, memory, time)

Philosophy:
    The runtime executes endpoint code efficiently and safely.
    It should be fast, secure, and isolated.

    Endpoint code is untrusted - we must sandbox it.
    But we also want performance - cache compiled code.

    Hot reload enables live updates without downtime.
"""

__all__ = [
    # To be implemented in Phase 4+
    # "EndpointExecutor",
    # "CodeCompiler",
    # "EndpointCache",
    # "HotReloader",
    # "Sandbox",
]

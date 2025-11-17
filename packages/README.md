# dbbasic Object Packages

This directory contains the modular components of dbbasic object system as separate, installable packages.

## Packages

### dbbasic-object-core
Core runtime for objects with state, logs, and versions.

**Contains:**
- Runtime (object execution, lifecycle)
- State management (TSV-based state storage)
- Log management (append-only logs)
- Version management (code versioning, rollback)

**Dependencies:** None (pure Python)

### dbbasic-object-web
HTTP server and REST API for dbbasic objects.

**Contains:**
- HTTP server (Bottle-based)
- REST API endpoints (GET, POST, PUT, DELETE)
- Object routing

**Dependencies:** `dbbasic-object-core>=0.8.2`, `bottle>=0.12.0`

### dbbasic-object-cluster
Distributed cluster management.

**Contains:**
- Cluster registry (station tracking)
- Heartbeat system (health monitoring)
- State replication (fire-and-forget)
- Log replication
- Object migration
- Load balancing

**Dependencies:** `dbbasic-object-core>=0.8.2`

## Installation (Development)

Install all packages in editable mode:

```bash
cd multiplexing
pip install -e packages/core
pip install -e packages/web
pip install -e packages/cluster
```

## Usage

```python
# Import from packages
from dbbasic_object_core import StateManager, LogManager
from dbbasic_object_web import Server
from dbbasic_object_cluster import ClusterManager

# Use as before, but with clean module boundaries
```

## Migration Status

**Current (2025-11-16):** Package structure created, code not yet moved.

**Next steps:**
1. Move `src/object_primitive/*` → `packages/core/src/dbbasic_object_core/`
2. Move `api/*` → `packages/web/src/dbbasic_object_web/`
3. Extract cluster code → `packages/cluster/src/dbbasic_object_cluster/`
4. Update all imports
5. Run tests to verify everything still works

## Publishing (Future)

When ready, publish to PyPI:
```bash
cd packages/core && python -m build && twine upload dist/*
cd packages/web && python -m build && twine upload dist/*
cd packages/cluster && python -m build && twine upload dist/*
```

Then users can: `pip install dbbasic-object-web dbbasic-object-cluster`

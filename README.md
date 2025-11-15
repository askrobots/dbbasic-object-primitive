# Object Primitive

A distributed computing system that treats computation as objects with REST APIs. Write a Python function, get automatic clustering, load balancing, and state replication.

## What We Accomplished

This system demonstrates that distributed computing doesn't require containers, orchestration platforms, or complex microservices frameworks. We built:

**Phase 1-6: Core Runtime**
- Object-as-API: Python functions become REST endpoints automatically
- State management: TSV-based persistence with versioning
- Self-logging: Queryable event logs built-in
- Version control: Track object code changes over time

**Phase 7: Distributed Computing**
- **Automatic Clustering:** Self-organizing multi-station mesh
- **Cross-Station Calls:** Objects call each other across the network transparently
- **Object Migration:** Move running objects between stations on demand
- **Load-Aware Routing:** Application-layer load balancing using actual CPU/memory metrics
- **State Replication:** Automatic async replication with last-write-wins conflict resolution

## What It Replaces

| Traditional Stack | Object Primitive |
|------------------|------------------|
| Docker + Kubernetes | Built-in runtime |
| F5 Load Balancer | Automatic load routing |
| Redis/Memcached | Built-in state management |
| RabbitMQ/Kafka | Cross-object calls |
| Service mesh | Automatic routing |

**Total cost comparison:** Traditional stack $100k+/year vs $0 for Object Primitive.

## Current Status

**⚠️ NON-PRODUCTION USE ONLY**

This is a research prototype demonstrating distributed computing primitives. It is **not production-ready**.

**Known limitations:**
- **No built-in authentication/authorization:** The runtime doesn't enforce auth (though you can build it as objects - see `examples/advanced/auth.py`)
- **No permissions system:** No access control enforced by the runtime
- **No rate limiting:** Objects can be overwhelmed
- **No encryption:** All communication is plaintext HTTP
- **No input validation:** Runtime trusts all incoming data
- **No resource limits:** Objects can consume unlimited memory/CPU

**Before production use, we need:**
- Runtime-level authentication and authorization enforcement
- Fine-grained permissions system (object-to-object, user-to-object)
- Resource quotas and limits
- TLS/encryption for network communication
- Input validation and sanitization
- Rate limiting and DoS protection
- Audit logging for security events

## Quick Start

### Single Station

```bash
# Install dependencies
python3 -m pip install -r requirements.txt

# Run server
python run_server.py
```

Server runs on http://localhost:8001

### Create an Object

```python
# examples/hello.py
def GET(request):
    return {"message": "Hello, World!"}
```

### Call It

```bash
curl http://localhost:8001/objects/hello
# {"message": "Hello, World!"}
```

### Run a Cluster

Configure hostnames in `start_cluster.sh`:
```bash
STATION1_HOST="station1.local"
STATION2_HOST="station2.local"
STATION3_HOST="station3.local"
```

Then:
```bash
./start_cluster.sh
```

Objects automatically distribute across stations based on load.

## Examples

See `examples/` directory:

- **basics/counter.py** - Stateful counter
- **tutorial/04_calculator.py** - Stateful calculator with operations
- **advanced/auth.py** - User authentication (450 lines, complete system)
- **advanced/blog.py** - Blog with posts, tags, pagination (400 lines)

## Architecture

- **No Containers:** Direct Python execution
- **No Config Files:** Just write Python functions
- **No Database:** State in TSV files (human-readable, git-friendly)
- **No Orchestration:** Self-organizing cluster
- **No Service Discovery:** Built into runtime

## How It Works

1. Write a Python function with HTTP method names (GET, POST, etc.)
2. Runtime loads it and exposes as REST API
3. Functions get `_state_manager`, `_logger`, `_runtime` injected
4. State persists automatically across requests
5. In cluster mode, runtime handles routing and replication

## Performance Notes

- Zero serialization overhead for local calls
- Async state replication (doesn't block requests)
- Load-based routing (CPU/memory aware)
- No container tax

## License

MIT License - see LICENSE file

## Contributing

This is a research prototype. We're demonstrating concepts, not building a product (yet).

Issues and discussions welcome at: https://github.com/askrobots/dbbasic-object-primitive

---

**Built by Ask Robots / dbbasic.com**

*Making distributed computing simple again.*

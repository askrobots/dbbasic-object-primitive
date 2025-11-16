# FAQ

## General

**Q: What is this?**

A: A distributed computing system where Python functions automatically become distributed REST APIs with built-in state, logging, and clustering.

**Q: Can I use this in production?**

A: Not yet. Missing authentication, permissions, encryption, and resource limits. Research prototype only.

**Q: What does it replace?**

A: Docker + Kubernetes for orchestration, F5/HAProxy for load balancing, Redis for state, Kafka for messaging. All built-in.

## Installation

**Q: What Python version?**

A: Python 3.10 or higher.

**Q: Do I need Docker?**

A: No. No containers needed.

**Q: What dependencies?**

A: Just `pip install -r requirements.txt`

## Usage

**Q: How do I create an object?**

A: Create a `.py` file in `examples/` with GET/POST/etc functions. Done.

**Q: Where is state stored?**

A: TSV files in `data/state/{object_id}/`. Human-readable, git-friendly.

**Q: How do I view logs?**

A: `curl http://localhost:8001/objects/{id}?logs=true`

**Q: Can objects call each other?**

A: Yes. `_runtime.call_object('other_object', 'GET', {})`

## Cluster

**Q: How many stations can I run?**

A: Tested with 3. Should work with more.

**Q: Why is a station showing offline?**

A: Heartbeat not received in 30 seconds. Check network and server process.

**Q: How does load balancing work?**

A: Automatic routing based on actual CPU/memory usage, not round-robin.

**Q: How is state replicated?**

A: Async fire-and-forget to all active stations. Last-write-wins conflict resolution.

**Q: What if two stations update the same key?**

A: Last write wins (based on timestamp). Eventual consistency.

**Q: Can I deploy code without restart?**

A: Yes. Server runs with auto-reload. Just rsync or use `./deploy.sh`

## Troubleshooting

**Q: Port 8001 already in use**

A: Kill existing process: `killall python` or change port in scripts.

**Q: Object not found**

A: Check file exists in `examples/` and has HTTP method functions (GET, POST, etc.).

**Q: State not persisting**

A: Check `data/` directory exists and is writable.

**Q: Cluster not connecting**

A: Verify SSH keys, hostnames in scripts, and network connectivity.

**Q: Changes not appearing**

A: Server auto-reloads. Wait 2 seconds or restart manually.

## Development

**Q: How do I add a new object?**

A: Create `.py` file in `examples/` with method functions. Server watches directory.

**Q: Can I use external libraries?**

A: Yes. Import normally. Add to requirements.txt if needed.

**Q: How do I debug?**

A: Check server logs, use `_logger.log()`, view with `?logs=true`

**Q: Can I run tests?**

A: Yes. `python -m pytest tests/`

## Advanced

**Q: How does object migration work?**

A: POST to `/cluster/migrate` with object_id and target_station. Object moves.

**Q: Can I customize routing?**

A: Yes. See `src/object_primitive/runtime/object_runtime.py`

**Q: What about WebSockets?**

A: Not yet implemented. On roadmap.

**Q: Can I add authentication?**

A: See `examples/advanced/auth.py` for object-level auth. Runtime-level auth coming soon.

**Q: Is there a limit on object size?**

A: No hard limit. Large objects will be slower to load/replicate.

**Q: Can objects be stateless?**

A: Yes. Just don't use `_state_manager`.

## Support

**Q: Where do I report bugs?**

A: https://github.com/askrobots/dbbasic-object-primitive/issues

**Q: Can I contribute?**

A: Yes. Fork, make changes, submit PR.

**Q: Is there a community?**

A: Check GitHub issues and discussions.

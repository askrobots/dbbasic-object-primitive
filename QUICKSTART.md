# Quick Start

Get running in 5 minutes (single station) or 15 minutes (3-station cluster).

## Prerequisites

- Python 3.9+
- `pip` for package management
- SSH access between stations (for multi-station clusters)

## Single Station Setup (5 minutes)

Perfect for development and testing.

### 1. Install Dependencies

```bash
python3 -m pip install -r requirements.txt
```

### 2. Start Server

```bash
python run_server.py
```

Server runs on `http://localhost:8001`

### 3. Create Your First Object

Create `examples/hello.py`:

```python
def GET(request):
    return {"message": "Hello, World!"}
```

### 4. Call It

```bash
curl http://localhost:8001/objects/hello
```

Output:
```json
{"message": "Hello, World!"}
```

### 5. View Dashboard

Open `http://localhost:8001/dashboard` in your browser.

**Done!** You have a running object primitive system.

---

## Multi-Station Cluster (15 minutes)

Distributed setup with automatic load balancing and replication.

### Prerequisites

- 3 machines on same network (or VMs)
- SSH access from master to workers
- Same Python version on all machines

### 1. Install on All Stations

On each machine:

```bash
git clone <repository-url>
cd dbbasic-object-primitive
python3 -m pip install -r requirements.txt
```

### 2. Configure Cluster (Master Only)

On the master station:

```bash
cp cluster.example.tsv cluster.tsv
```

Edit `cluster.tsv`:

```tsv
station_id	host	port	user	role
station1	192.168.1.10	8001	youruser	master
station2	192.168.1.11	8001	youruser	worker
station3	192.168.1.12	8001	youruser	worker
```

Replace:
- `192.168.1.X` with your actual IPs
- `youruser` with your SSH username
- Port `8001` if needed

### 3. Test SSH Connectivity

From master station, verify passwordless SSH works:

```bash
ssh youruser@192.168.1.11 echo "OK"
ssh youruser@192.168.1.12 echo "OK"
```

If prompted for password, set up SSH keys:

```bash
ssh-copy-id youruser@192.168.1.11
ssh-copy-id youruser@192.168.1.12
```

### 4. Start Cluster

On master station:

```bash
./start_cluster.sh
```

This will:
- Start servers on worker stations
- Start heartbeat daemons
- Display cluster status

### 5. Verify Cluster

```bash
curl http://localhost:8001/cluster/stations | python3 -m json.tool
```

Should show all 3 stations active.

### 6. Deploy Your First Object

Create `examples/counter.py`:

```python
def GET(request, _state_manager):
    count = _state_manager.get('count', 0)
    count += 1
    _state_manager.set('count', count)
    return {"count": count}
```

### 7. Test Cross-Station Access

From any machine:

```bash
# Hit master
curl http://192.168.1.10:8001/objects/counter

# Hit worker 1
curl http://192.168.1.11:8001/objects/counter

# Hit worker 2
curl http://192.168.1.12:8001/objects/counter
```

All should return incremented counts - state replicates automatically.

### 8. View Cluster Dashboard

Open any station's dashboard:
- Master: `http://192.168.1.10:8001/dashboard`
- Worker 1: `http://192.168.1.11:8001/dashboard`
- Worker 2: `http://192.168.1.12:8001/dashboard`

**Done!** You have a 3-station distributed cluster.

---

## Cluster Management Commands

```bash
# Start cluster (from master)
./start_cluster.sh

# Stop cluster (from master)
./stop_cluster.sh

# Restart heartbeat daemons (after code changes)
./restart_cluster.sh

# Deploy code to all stations
./deploy.sh
```

---

## Common Issues

### Workers not showing as active

Check heartbeat daemons are running:

```bash
ssh youruser@192.168.1.11 'ps aux | grep cluster_heartbeat_daemon'
```

Restart if needed:

```bash
./restart_cluster.sh
```

### "Connection refused" errors

Verify servers are running on all stations:

```bash
curl http://192.168.1.11:8001/cluster/info
curl http://192.168.1.12:8001/cluster/info
```

### State not replicating

Objects must explicitly replicate state. Use `_state_manager`:

```python
def POST(request, _state_manager):
    value = request.json.get('value')
    _state_manager.set('data', value)  # Auto-replicates
    return {"status": "saved"}
```

---

## Next Steps

- **Examples**: See `examples/` directory for counter, calculator, auth, blog
- **API Docs**: Check `/cluster/stations` and `/cluster/info` endpoints
- **Architecture**: Read README.md for system design details

---

## Need Help?

- Issues: https://github.com/askrobots/dbbasic-object-primitive/issues
- Discussions: https://github.com/askrobots/dbbasic-object-primitive/discussions

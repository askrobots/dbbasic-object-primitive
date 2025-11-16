# Cluster Setup

Run Object Primitive across multiple machines.

## Requirements

- 2+ machines on same network
- SSH access between machines
- Python 3.10+ on all machines

## Setup

### 1. Install on All Machines

On each machine:
```bash
git clone https://github.com/askrobots/dbbasic-object-primitive.git
cd dbbasic-object-primitive
python3 -m pip install -r requirements.txt
```

### 2. Configure SSH Keys

From master machine:
```bash
ssh-copy-id user@station2.local
ssh-copy-id user@station3.local
```

Test passwordless SSH works:
```bash
ssh user@station2.local 'echo OK'
```

### 3. Edit start_cluster.sh

Edit the hostnames in `start_cluster.sh`:
```bash
STATION1_HOST="station1.local"    # Master (this machine)
STATION2_HOST="station2.local"     # Worker 1
STATION3_HOST="station3.local"     # Worker 2
INSTALL_DIR="~/dbbasic-object-primitive"
```

### 4. Start Cluster

On master machine:
```bash
./start_cluster.sh
```

This will:
- Prompt you to start station1 manually
- Start station2 via SSH
- Start station3 via SSH

Start station1 in a separate terminal:
```bash
cd ~/dbbasic-object-primitive
python run_server.py --port 8001
```

### 5. Verify Cluster

Check cluster status:
```bash
curl http://localhost:8001/cluster/stations | python3 -m json.tool
```

You should see all 3 stations listed.

Open dashboard:
```
http://localhost:8001/dashboard
```

## Deploy Code Changes

After changing code, deploy to all stations:
```bash
./deploy.sh
```

Server auto-reloads. Changes are live immediately.

## Stop Cluster

```bash
./stop_cluster.sh
```

## How It Works

- **Master (station1)**: Maintains cluster registry, receives heartbeats
- **Workers (station2, station3)**: Send heartbeats every 10s, execute objects
- **Load Balancing**: Automatic routing based on CPU/memory
- **State Replication**: Automatic async replication across all stations

## Troubleshooting

**"Station offline"**
- Check heartbeat within 30 seconds
- Verify network connectivity
- Check server logs on that station

**"SSH connection failed"**
- Verify SSH keys are set up
- Check hostname resolution
- Test manual SSH connection

**"Port already in use"**
- Kill existing processes: `killall python`
- Or change port in scripts

## Next Steps

- [Examples](EXAMPLES.md) - Try distributed examples
- [API Reference](API.md) - Cluster endpoints

# Installation

## Requirements

- Python 3.10 or higher
- SSH access to cluster machines (for multi-station setup)

## Install

```bash
git clone https://github.com/askrobots/dbbasic-object-primitive.git
cd dbbasic-object-primitive
python3 -m pip install -r requirements.txt
```

## Verify Installation

Start the server:
```bash
python run_server.py --port 8001
```

Test it works:
```bash
curl http://localhost:8001/objects
```

You should see a JSON response listing available objects.

Open the dashboard:
```
http://localhost:8001/dashboard
```

## Next Steps

- [Quickstart](QUICKSTART.md) - Create your first object
- [Cluster Setup](CLUSTER.md) - Run on multiple machines

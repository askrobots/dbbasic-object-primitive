# Building Web Apps with Object Primitives

**Status:** Living document - sections marked PASS are placeholders for future work

A practical guide to building distributed web applications using dbbasic-object-primitive.

---

## Table of Contents

1. [Hello World](#hello-world)
2. [How This System Works](#how-this-system-works)
3. [Objects as HTTP Endpoints](#objects-as-http-endpoints)
4. [State Management](#state-management)
5. [Multi-part Forms & File Uploads](#multi-part-forms--file-uploads)
6. [URLs for Code Management](#urls-for-code-management)
7. [Using curl and HTTP Clients](#using-curl-and-http-clients)
8. [Authentication](#authentication)
9. [Background Tasks & Scheduling](#background-tasks--scheduling)
10. [Email & External Services](#email--external-services)
11. [Security](#security)
12. [Performance](#performance)

---

## Hello World

### Returning JSON

Create `examples/hello.py`:

```python
def GET(request):
    return {"message": "Hello, World!"}
```

Call it:
```bash
curl http://localhost:8001/objects/hello
# {"message": "Hello, World!"}
```

### Returning HTML

Create `examples/hello_html.py`:

```python
def GET(request):
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Hello World</title></head>
    <body>
        <h1>Hello, World!</h1>
        <p>This is served from an object primitive.</p>
    </body>
    </html>
    """
    request.response.content_type = 'text/html'
    return html
```

Visit in browser: `http://localhost:8001/objects/hello_html`

### Returning Plain Text

```python
def GET(request):
    request.response.content_type = 'text/plain'
    return "Hello, World!"
```

---

## How This System Works

### Core Concepts

**Objects are network-native:**
- Each Python file in `examples/` becomes an HTTP endpoint
- Objects have built-in state, logs, and version history
- Objects automatically replicate across cluster stations

**Architecture:**

```
Request → Routing → Object Execution → Response
                         ↓
              State Manager (TSV files)
              Logger (TSV files)
              Version Manager (source files)
```

**Storage Model:**

All data stored in human-readable TSV files:

```
data/
  state/{object_id}/state.tsv      # Key-value state
  logs/{object_id}/log.tsv         # Append-only logs
  versions/{object_id}/v1.txt      # Source code versions
  versions/{object_id}/metadata.tsv # Version metadata
  files/{object_id}/               # File storage
```

**Replication:**

- State changes replicate to all active stations (fire-and-forget)
- Log entries replicate to all active stations
- Files replicate on write
- Eventually consistent (no distributed transactions)

**Discovery:**

- Objects find each other via cluster registry
- No service discovery needed - everything is on the network
- URLs follow pattern: `http://{station}:{port}/objects/{object_id}`

---

## Objects as HTTP Endpoints

### HTTP Methods

Objects support standard HTTP methods:

```python
def GET(request):
    return {"action": "read"}

def POST(request):
    return {"action": "create"}

def PUT(request):
    return {"action": "update"}

def DELETE(request):
    return {"action": "delete"}

def PATCH(request):
    return {"action": "partial update"}
```

### Request Object

The `request` object provides:

```python
def POST(request):
    # URL parameters
    name = request.query.get('name', 'Anonymous')

    # JSON body
    data = request.json  # Automatically parsed

    # Form data
    form_data = request.forms

    # Headers
    auth = request.get_header('Authorization')

    # Raw body
    raw = request.body.read()

    # Response control
    request.response.status = 201
    request.response.content_type = 'application/json'

    return {"received": data}
```

### Query Parameters

```python
def GET(request):
    # GET /objects/search?q=python&limit=10
    query = request.query.get('q', '')
    limit = int(request.query.get('limit', '20'))

    return {
        "query": query,
        "limit": limit,
        "results": []  # Search implementation
    }
```

---

## State Management

### Basic State Operations

Objects get automatic state management via `_state_manager`:

```python
def GET(request, _state_manager):
    # Read state
    count = _state_manager.get('count', 0)

    # Write state (replicates automatically)
    _state_manager.set('count', count + 1)

    return {"count": count + 1}
```

### State is Replicated

State changes automatically replicate to all active cluster stations:

```python
def POST(request, _state_manager):
    # This write replicates to station2 and station3
    _state_manager.set('user_count', 42)

    # Read from any station - eventually consistent
    return {"status": "saved"}
```

### Complex State

State values can be any JSON-serializable type:

```python
def POST(request, _state_manager):
    # Store complex objects
    _state_manager.set('user', {
        'name': 'Alice',
        'email': 'alice@example.com',
        'created': '2025-11-17'
    })

    # Store lists
    _state_manager.set('tags', ['python', 'distributed', 'web'])

    # Store numbers
    _state_manager.set('score', 98.5)

    return {"status": "ok"}
```

### Viewing State

State stored in TSV files:

```bash
# Local station
cat data/state/myobject/state.tsv

# Remote station
ssh user@station2 'cat ~/multiplexing/data/state/myobject/state.tsv'
```

---

## Multi-part Forms & File Uploads

### File Upload Endpoint

```python
def POST(request, _file_storage):
    """
    Upload files - automatically replicates across cluster
    """
    # Get uploaded file
    upload = request.files.get('file')

    if not upload:
        request.response.status = 400
        return {"error": "No file provided"}

    # Save file (replicates to all stations)
    file_id = _file_storage.save(
        filename=upload.filename,
        content=upload.file.read()
    )

    return {
        "status": "uploaded",
        "file_id": file_id,
        "filename": upload.filename,
        "url": f"/objects/gallery?file={file_id}"
    }
```

### Upload from curl

```bash
# Upload a file
curl -X POST \
  -F "file=@photo.jpg" \
  http://localhost:8001/objects/gallery

# Response:
# {
#   "status": "uploaded",
#   "file_id": "abc123...",
#   "filename": "photo.jpg"
# }
```

### Serving Uploaded Files

```python
def GET(request, _file_storage):
    """
    Serve uploaded files
    """
    file_id = request.query.get('file')

    if not file_id:
        return {"error": "file parameter required"}

    # Load file
    file_data = _file_storage.load(file_id)

    if not file_data:
        request.response.status = 404
        return {"error": "File not found"}

    # Set content type based on extension
    filename = file_data['filename']
    if filename.endswith('.jpg') or filename.endswith('.jpeg'):
        request.response.content_type = 'image/jpeg'
    elif filename.endswith('.png'):
        request.response.content_type = 'image/png'
    elif filename.endswith('.gif'):
        request.response.content_type = 'image/gif'

    # Return binary content
    return file_data['content']
```

### Multi-part Form with Multiple Fields

```python
def POST(request, _state_manager):
    """
    Handle form with both text fields and file uploads
    """
    # Text fields
    title = request.forms.get('title', '')
    description = request.forms.get('description', '')

    # File upload
    image = request.files.get('image')

    # Process
    post_id = f"post_{int(time.time())}"

    _state_manager.set(post_id, {
        'title': title,
        'description': description,
        'has_image': image is not None,
        'created': time.time()
    })

    return {
        "status": "created",
        "post_id": post_id
    }
```

---

## URLs for Code Management

### View Object Code

```bash
# View current version
curl http://localhost:8001/objects/counter?code=true
```

### View Object History

```bash
# Get version history
curl http://localhost:8001/objects/counter?versions=true

# Response:
# {
#   "object_id": "counter",
#   "versions": [
#     {"version": 1, "timestamp": "2025-11-17T10:30:00", "changes": "Initial version"},
#     {"version": 2, "timestamp": "2025-11-17T11:45:00", "changes": "Added logging"}
#   ]
# }
```

### View Object Logs

```bash
# Get execution logs
curl http://localhost:8001/objects/counter?logs=true

# With filters
curl "http://localhost:8001/objects/counter?logs=true&level=ERROR&limit=50"
```

### Edit Object Code

PASS - Planning web-based code editor interface

```
# Future:
# POST /objects/counter?action=edit
# Body: new source code
# Response: new version number
```

### Dashboard URL

View object in dashboard:
```
http://localhost:8001/dashboard/object/counter
```

Shows:
- Current state
- Recent logs
- Version history
- Performance metrics
- Cluster distribution

---

## Using curl and HTTP Clients

### curl Examples

**GET requests:**
```bash
# Simple GET
curl http://localhost:8001/objects/hello

# With query parameters
curl "http://localhost:8001/objects/search?q=python&limit=10"

# With headers
curl -H "Authorization: Bearer token123" \
  http://localhost:8001/objects/protected
```

**POST requests:**
```bash
# JSON POST
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"name": "Alice", "age": 30}' \
  http://localhost:8001/objects/users

# Form POST
curl -X POST \
  -d "username=alice" \
  -d "email=alice@example.com" \
  http://localhost:8001/objects/register

# File upload
curl -X POST \
  -F "file=@document.pdf" \
  -F "title=My Document" \
  http://localhost:8001/objects/documents
```

**Other methods:**
```bash
# PUT
curl -X PUT \
  -H "Content-Type: application/json" \
  -d '{"status": "published"}' \
  http://localhost:8001/objects/posts/123

# DELETE
curl -X DELETE \
  http://localhost:8001/objects/posts/123

# PATCH
curl -X PATCH \
  -H "Content-Type: application/json" \
  -d '{"views": 100}' \
  http://localhost:8001/objects/posts/123
```

### Python requests Library

```python
import requests

# GET
response = requests.get('http://localhost:8001/objects/hello')
data = response.json()

# POST JSON
response = requests.post(
    'http://localhost:8001/objects/users',
    json={'name': 'Alice', 'age': 30}
)

# POST file
files = {'file': open('photo.jpg', 'rb')}
response = requests.post(
    'http://localhost:8001/objects/gallery',
    files=files
)

# With auth
headers = {'Authorization': 'Bearer token123'}
response = requests.get(
    'http://localhost:8001/objects/protected',
    headers=headers
)
```

### JavaScript fetch

```javascript
// GET
const response = await fetch('http://localhost:8001/objects/hello');
const data = await response.json();

// POST JSON
const response = await fetch('http://localhost:8001/objects/users', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({name: 'Alice', age: 30})
});

// POST file
const formData = new FormData();
formData.append('file', fileInput.files[0]);

const response = await fetch('http://localhost:8001/objects/gallery', {
  method: 'POST',
  body: formData
});
```

---

## Authentication

PASS - Security system in development

### Current Status

⚠️ **WARNING:** No authentication or authorization currently implemented.

Do NOT expose to public internet without:
- Reverse proxy with authentication (nginx + basic auth, oauth2-proxy, etc.)
- VPN or private network
- Firewall rules restricting access

### Planned Authentication

```python
# Future implementation sketch:

def POST(request, _auth):
    """Login endpoint"""
    username = request.json.get('username')
    password = request.json.get('password')

    # Verify credentials
    if _auth.verify(username, password):
        token = _auth.create_token(username)
        return {"token": token}
    else:
        request.response.status = 401
        return {"error": "Invalid credentials"}

def GET(request, _auth):
    """Protected endpoint"""
    # Require authentication
    user = _auth.require_token(request)

    # Check permissions
    if not _auth.has_permission(user, 'read:data'):
        request.response.status = 403
        return {"error": "Forbidden"}

    return {"data": "sensitive information"}
```

### Temporary Solutions

**1. SSH tunneling:**
```bash
# Access cluster through SSH tunnel
ssh -L 8001:localhost:8001 user@remote-station
# Then access http://localhost:8001 locally
```

**2. nginx basic auth:**
```nginx
location /objects/ {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8001;
}
```

**3. Tailscale/WireGuard:**
Use VPN to access cluster on private network.

---

## Background Tasks & Scheduling

PASS - Task system in development

### Planned Features

**Auto-run on start:**
```python
# Future: objects/startup_tasks.py
def ON_STARTUP():
    """Runs once when station starts"""
    # Initialize caches
    # Warm up connections
    # Health checks
    pass
```

**Scheduled tasks:**
```python
# Future: objects/cleanup.py
def SCHEDULE():
    return {
        'interval': '1 hour',  # or cron: '0 * * * *'
        'function': 'cleanup_old_files'
    }

def cleanup_old_files(_state_manager, _file_storage):
    """Runs every hour"""
    # Delete files older than 30 days
    pass
```

**Background jobs:**
```python
# Future: objects/email_queue.py
def POST(request, _background):
    """Queue background job"""
    email_data = request.json

    # Queue for background processing
    job_id = _background.enqueue('send_email', email_data)

    return {"job_id": job_id, "status": "queued"}

def send_email(email_data):
    """Runs in background"""
    # Send email without blocking HTTP request
    pass
```

### Current Workarounds

**1. External cron:**
```bash
# Add to crontab
0 * * * * curl http://localhost:8001/objects/cleanup
```

**2. Thread-based tasks:**
```python
import threading
import time

def POST(request, _state_manager):
    """Start long-running task"""
    def background_work():
        time.sleep(60)  # Long operation
        _state_manager.set('job_done', True)

    thread = threading.Thread(target=background_work)
    thread.daemon = True
    thread.start()

    return {"status": "started"}
```

---

## Email & External Services

PASS - Integration patterns in development

### Sending Email (Manual Implementation)

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def POST(request, _logger):
    """Send email via SMTP"""
    to_email = request.json.get('to')
    subject = request.json.get('subject')
    body = request.json.get('body')

    try:
        msg = MIMEMultipart()
        msg['From'] = 'noreply@example.com'
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        # Configure SMTP
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('your-email@gmail.com', 'app-password')
        server.send_message(msg)
        server.quit()

        _logger.info(f"Email sent to {to_email}")
        return {"status": "sent"}

    except Exception as e:
        _logger.error(f"Email failed: {e}")
        request.response.status = 500
        return {"error": str(e)}
```

### Calling External APIs

```python
import requests

def GET(request, _logger, _state_manager):
    """Fetch data from external API"""
    try:
        response = requests.get(
            'https://api.example.com/data',
            headers={'Authorization': 'Bearer YOUR_TOKEN'},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()

            # Cache the result
            _state_manager.set('cached_data', data)
            _state_manager.set('cache_time', time.time())

            return data
        else:
            _logger.error(f"API error: {response.status_code}")
            return {"error": "API request failed"}

    except Exception as e:
        _logger.error(f"External API error: {e}")
        return {"error": str(e)}
```

### Webhooks

```python
def POST(request, _logger, _state_manager):
    """Receive webhook from external service"""
    # Verify webhook signature (important!)
    signature = request.get_header('X-Webhook-Signature')

    # TODO: Implement signature verification

    event_type = request.json.get('event')
    event_data = request.json.get('data')

    _logger.info(f"Webhook received: {event_type}")

    # Process event
    if event_type == 'payment.success':
        order_id = event_data.get('order_id')
        _state_manager.set(f'order_{order_id}_status', 'paid')

    return {"status": "received"}
```

---

## Security

PASS - Security hardening in progress

### Current Security Status

⚠️ **DEVELOPMENT ONLY - NOT PRODUCTION READY**

**Missing:**
- No authentication system
- No authorization/permissions
- No rate limiting
- No input validation framework
- No CSRF protection
- No XSS protection
- No SQL injection protection (we don't use SQL, but still)
- No secrets management

### Security Checklist (TODO)

**Authentication & Authorization:**
- [ ] User authentication system
- [ ] Token-based auth (JWT or similar)
- [ ] Role-based access control (RBAC)
- [ ] Permission system for objects
- [ ] API key management

**Input Validation:**
- [ ] Request size limits
- [ ] Input sanitization
- [ ] Content-Type validation
- [ ] File upload restrictions (size, type)
- [ ] Query parameter validation

**Network Security:**
- [ ] HTTPS/TLS support
- [ ] Certificate management
- [ ] mTLS for station-to-station communication
- [ ] CORS configuration
- [ ] CSP headers

**Rate Limiting:**
- [ ] Per-IP rate limiting
- [ ] Per-user rate limiting
- [ ] Per-object rate limiting
- [ ] Burst protection

**Data Security:**
- [ ] Secrets management (don't store in state.tsv!)
- [ ] Encryption at rest
- [ ] Encryption in transit
- [ ] Secure file storage
- [ ] Log sanitization (no passwords in logs)

**Monitoring & Auditing:**
- [ ] Audit logs for sensitive operations
- [ ] Failed auth attempt tracking
- [ ] Anomaly detection
- [ ] Security event alerting

### Current Best Practices

**1. Network isolation:**
```bash
# Use firewall to restrict access
sudo ufw allow from 192.168.0.0/24 to any port 8001
sudo ufw deny 8001
```

**2. Reverse proxy with auth:**
```nginx
# nginx with basic auth
location /objects/ {
    auth_basic "Restricted";
    auth_basic_user_file /etc/nginx/.htpasswd;
    proxy_pass http://localhost:8001;
}
```

**3. Input validation:**
```python
def POST(request):
    # Validate inputs manually
    name = request.json.get('name', '')

    if len(name) > 100:
        request.response.status = 400
        return {"error": "Name too long"}

    if not name.isalnum():
        request.response.status = 400
        return {"error": "Name must be alphanumeric"}

    return {"status": "ok"}
```

**4. Don't store secrets in state:**
```python
# BAD - secrets in state.tsv (human-readable!)
_state_manager.set('api_key', 'secret123')

# BETTER - use environment variables
import os
api_key = os.environ.get('API_KEY')

# FUTURE - secrets manager integration
```

---

## Performance

### Current Performance Characteristics

**Single Station:**
- Requests handled by Bottle WSGI server
- Python GIL limits parallelism
- File I/O is synchronous
- Good for: 10-100 req/sec per object

**Cluster (3 stations):**
- Load balances across stations
- Replication is async (fire-and-forget)
- Eventually consistent
- Good for: 30-300 req/sec total

### Optimization Strategies

**1. Use state wisely:**
```python
# SLOW - writes to disk on every request
def GET(request, _state_manager):
    count = _state_manager.get('count', 0)
    _state_manager.set('count', count + 1)  # TSV write + replication
    return {"count": count}

# BETTER - batch writes
def GET(request, _state_manager):
    # Use memory for high-frequency data
    # Periodic checkpoint to state
    return {"count": get_counter()}  # In-memory
```

**2. Cache expensive operations:**
```python
def GET(request, _state_manager):
    # Check cache
    cache_time = _state_manager.get('cache_time', 0)

    if time.time() - cache_time < 300:  # 5 min cache
        return _state_manager.get('cached_data')

    # Expensive operation
    data = compute_expensive_thing()

    # Update cache
    _state_manager.set('cached_data', data)
    _state_manager.set('cache_time', time.time())

    return data
```

**3. Minimize state replication:**
```python
# SLOW - replicates large data on every update
_state_manager.set('large_dataset', [... 10MB of data ...])

# BETTER - use file storage for large data
_file_storage.save('dataset.json', json.dumps(large_data))
_state_manager.set('dataset_file_id', file_id)  # Just replicate ID
```

**4. Use appropriate HTTP methods:**
```python
# Optimize read-heavy endpoints
def GET(request):
    # No state writes, no logging (for high-traffic endpoints)
    return {"data": "static response"}
```

### Monitoring Performance

**Check response times:**
```bash
# Use time
time curl http://localhost:8001/objects/slow_endpoint

# Use curl verbose
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8001/objects/test

# curl-format.txt:
#   time_total: %{time_total}s
#   time_connect: %{time_connect}s
#   time_starttransfer: %{time_starttransfer}s
```

**Check object logs:**
```bash
# Look for slow operations
curl "http://localhost:8001/objects/myobject?logs=true" | grep "duration"
```

**Dashboard metrics:**
Visit `http://localhost:8001/dashboard/object/myobject` to see:
- Request count
- Average response time
- Error rate
- State size
- Log size

### Scaling Strategies

**Horizontal scaling:**
- Add more worker stations to cluster
- Each station handles ~10-100 req/sec
- State replicates automatically

**Vertical scaling:**
- More CPU cores per station
- More RAM for caching
- SSD storage for TSV files

**Future optimizations:**
- PASS - Connection pooling for replication
- PASS - Batch replication (reduce HTTP overhead)
- PASS - Compression for state/logs
- PASS - Read replicas (don't write to all stations)
- PASS - Smarter load balancing (current: least-loaded by CPU)

---

## Next Steps

1. **Try the examples:** Start with hello world and work through state, files, forms
2. **Build something:** Counter app, image gallery, simple blog
3. **Add authentication:** Use nginx basic auth or VPN for now
4. **Monitor:** Watch dashboard, check logs
5. **Contribute:** Help fill in the PASS sections!

---

## Contributing to This Guide

This guide is a living document. Sections marked PASS need:
- Working code examples
- Best practices
- Common pitfalls
- Integration guides

Submit PRs with:
- New sections
- Better examples
- Security improvements
- Performance tips

---

**Last Updated:** 2025-11-17
**Status:** Beta - Sections marked PASS are planned but not implemented
**Repository:** https://github.com/askrobots/dbbasic-object-primitive

"""
API handler for individual objects

GET /objects/{id} - Execute object's GET method
GET /objects/{id}?source=true - View object's source code
GET /objects/{id}?metadata=true - View object metadata
GET /objects/{id}?logs=true - View object logs
GET /objects/{id}?versions=true - View version history
GET /objects/{id}?version=N - Get specific version

POST /objects/{id} - Execute object's POST method
POST /objects/{id} (action=rollback) - Rollback to specific version
PUT /objects/{id} - Execute object's PUT method or update code
DELETE /objects/{id} - Execute object's DELETE method

Cross-station routing (Phase 7.2):
GET /objects/{id}@{station_id} - Execute object on remote station
"""
import json
import os
import time
import requests
from pathlib import Path
from dbbasic_web.responses import json as json_response, json_error

from dbbasic_object_core.runtime.object_runtime import ObjectRuntime


# Initialize runtime (shared across requests)
_runtime = None


def get_runtime():
    """Get or create the ObjectRuntime instance"""
    global _runtime
    if _runtime is None:
        _runtime = ObjectRuntime(base_dir='./data')
    return _runtime


def find_object_file(object_id: str) -> Path | None:
    """Find object file by ID"""
    # Convert object_id back to path
    # basics_counter -> basics/counter.py
    # tutorial_03_counter -> tutorial/03_counter.py

    examples_dir = Path('examples')

    # Try direct path first
    parts = object_id.split('_', 1)
    if len(parts) == 2:
        subdir, filename = parts
        py_file = examples_dir / subdir / f'{filename}.py'
        if py_file.exists():
            return py_file

    # Try as single file
    py_file = examples_dir / f'{object_id}.py'
    if py_file.exists():
        return py_file

    # Scan for match
    for py_file in examples_dir.rglob('*.py'):
        if py_file.name == '__init__.py' or '__pycache__' in str(py_file):
            continue

        rel_path = py_file.relative_to(examples_dir)
        found_id = str(rel_path).replace('.py', '').replace('/', '_')

        if found_id == object_id:
            return py_file

    return None


def parse_object_routing(id_param: str) -> tuple[str, str | None]:
    """
    Parse object_id@station_id syntax

    Returns:
        (object_id, station_id) - station_id is None if no @ in id_param

    Examples:
        'calculator' -> ('calculator', None)
        'calculator@station2' -> ('calculator', 'station2')
    """
    if '@' in id_param:
        object_id, station_id = id_param.split('@', 1)
        return object_id, station_id
    return id_param, None


def get_station_info(station_id: str) -> dict | None:
    """
    Look up station in cluster registry

    Returns:
        Station info dict or None if not found/inactive
        {
            'station_id': 'station2',
            'host': '192.0.2.2',
            'port': 8001,
            'last_heartbeat': 1234567890.123,
            'is_active': True,
            'url': 'http://192.0.2.2:8001',
            'metrics': {...}  # Optional
        }
    """
    registry_file = Path('data/cluster/stations.tsv')

    if not registry_file.exists():
        return None

    current_time = time.time()
    timeout = 30  # seconds

    with open(registry_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    sid, host, port, last_heartbeat = parts[:4]
                    metrics_json = parts[4] if len(parts) > 4 else '{}'

                    if sid == station_id:
                        # Check if active
                        age = current_time - float(last_heartbeat)
                        is_active = age < timeout

                        if not is_active:
                            return None  # Station offline

                        # Parse metrics
                        try:
                            metrics = json.loads(metrics_json)
                        except:
                            metrics = {}

                        station_info = {
                            'station_id': sid,
                            'host': host,
                            'port': int(port),
                            'last_heartbeat': float(last_heartbeat),
                            'is_active': is_active,
                            'url': f'http://{host}:{port}'
                        }

                        if metrics:
                            station_info['metrics'] = metrics

                        return station_info

    return None


def get_all_active_stations() -> list[dict]:
    """
    Get list of all active stations in cluster

    Returns:
        List of station info dicts (same format as get_station_info)
    """
    registry_file = Path('data/cluster/stations.tsv')

    if not registry_file.exists():
        return []

    current_time = time.time()
    timeout = 30  # seconds
    stations = []

    with open(registry_file, 'r') as f:
        for line in f:
            if line.strip():
                parts = line.strip().split('\t')
                if len(parts) >= 4:
                    sid, host, port, last_heartbeat = parts[:4]
                    metrics_json = parts[4] if len(parts) > 4 else '{}'

                    # Check if active
                    age = current_time - float(last_heartbeat)
                    is_active = age < timeout

                    if is_active:
                        # Parse metrics
                        try:
                            metrics = json.loads(metrics_json)
                        except:
                            metrics = {}

                        station_info = {
                            'station_id': sid,
                            'host': host,
                            'port': int(port),
                            'last_heartbeat': float(last_heartbeat),
                            'is_active': True,
                            'url': f'http://{host}:{port}'
                        }

                        if metrics:
                            station_info['metrics'] = metrics

                        stations.append(station_info)

    # Always include ourselves if we're station1
    local_station = os.environ.get('STATION_ID', 'unknown')
    if local_station == 'station1':
        if not any(s['station_id'] == local_station for s in stations):
            stations.insert(0, {
                'station_id': local_station,
                'host': 'localhost',
                'port': 8001,
                'last_heartbeat': current_time,
                'is_active': True,
                'url': 'http://localhost:8001'
            })

    return stations


def calculate_load_score(metrics: dict) -> float:
    """
    Calculate load score from metrics (lower is better)

    Score = (cpu_percent * 0.6) + (memory_percent * 0.4)

    Range: 0-100 (0 = idle, 100 = fully loaded)
    """
    if not metrics:
        return 50.0  # Default middle score if no metrics

    cpu = metrics.get('cpu_percent', 50.0)
    mem = metrics.get('memory_percent', 50.0)

    # Weighted average (CPU weighted higher than memory)
    return (cpu * 0.6) + (mem * 0.4)


def find_best_station(object_id: str) -> dict | None:
    """
    Find the best station to execute an object based on load

    Strategy:
    1. Get all active stations
    2. Check which ones have the object
    3. Select the one with lowest load score
    4. If no remote stations have it, return None (execute locally)

    Returns:
        Station info dict or None if should execute locally
    """
    local_station = os.environ.get('STATION_ID', 'unknown')
    stations = get_all_active_stations()

    if len(stations) <= 1:
        return None  # No remote stations, execute locally

    # For now, assume all stations have all objects (deployed via rsync)
    # Future: Check which stations actually have the object

    # Find station with lowest load (excluding ourselves)
    best_station = None
    best_score = float('inf')

    for station in stations:
        # Skip ourselves - we want to offload if possible
        if station['station_id'] == local_station:
            continue

        metrics = station.get('metrics', {})
        score = calculate_load_score(metrics)

        if score < best_score:
            best_score = score
            best_station = station

    # Only route if remote station is significantly less loaded (> 20% better)
    local_metrics = {}
    for station in stations:
        if station['station_id'] == local_station:
            local_metrics = station.get('metrics', {})
            break

    local_score = calculate_load_score(local_metrics)

    # Route if remote is at least 20 points better, or if local is > 70% loaded
    if best_station and (local_score - best_score > 20 or local_score > 70):
        return best_station

    return None  # Execute locally


def forward_request(station_info: dict, object_id: str, method: str,
                   query_params: dict = None, body_data: dict = None,
                   timeout: int = 30) -> dict:
    """
    Forward HTTP request to remote station

    Args:
        station_info: Station info from get_station_info()
        object_id: Object ID (without @station_id)
        method: HTTP method (GET, POST, PUT, DELETE)
        query_params: Query parameters dict
        body_data: Request body data (for POST/PUT/DELETE)
        timeout: Request timeout in seconds

    Returns:
        Response JSON dict

    Raises:
        requests.RequestException: If request fails
    """
    url = f"{station_info['url']}/objects/{object_id}"

    # Prepare request
    headers = {'Content-Type': 'application/json'}
    params = query_params or {}

    # Make request
    if method == 'GET':
        response = requests.get(url, params=params, timeout=timeout)
    elif method == 'POST':
        response = requests.post(url, params=params, json=body_data, headers=headers, timeout=timeout)
    elif method == 'PUT':
        response = requests.put(url, params=params, json=body_data, headers=headers, timeout=timeout)
    elif method == 'DELETE':
        response = requests.delete(url, params=params, json=body_data, headers=headers, timeout=timeout)
    else:
        raise ValueError(f'Unsupported method: {method}')

    # Parse response
    try:
        result = response.json()
        # Add routing metadata
        result['_routed_to'] = station_info['station_id']
        result['_routed_from'] = os.environ.get('STATION_ID', 'unknown')
        return result
    except json.JSONDecodeError:
        # Return raw response if not JSON
        return {
            'status': 'error',
            'error': 'Invalid JSON response from remote station',
            'raw_response': response.text,
            '_routed_to': station_info['station_id'],
            '_routed_from': os.environ.get('STATION_ID', 'unknown')
        }


def GET(request, id: str):
    """
    Get object information or execute GET method

    Query parameters:
    - source: Return source code
    - metadata: Return metadata
    - logs: Return logs
    - versions: Return version history
    - (default): Execute GET method

    Cross-station routing:
    - id can be 'object_id' or 'object_id@station_id'
    - If @station_id is present, route to that station
    """
    # Parse routing syntax (Phase 7.2)
    object_id, target_station = parse_object_routing(id)

    # Check if this should be routed to another station
    if target_station:
        local_station = os.environ.get('STATION_ID', 'unknown')

        # If target is local station, execute locally
        if target_station == local_station:
            # Continue to local execution below
            pass
        else:
            # Route to remote station
            station_info = get_station_info(target_station)

            if not station_info:
                return json_error(
                    f'Station not found or offline: {target_station}',
                    status=503  # Service Unavailable
                )

            # Forward request to remote station
            try:
                result = forward_request(
                    station_info=station_info,
                    object_id=object_id,
                    method='GET',
                    query_params=dict(request.GET),
                    timeout=30
                )
                return json_response(json.dumps(result))
            except requests.Timeout:
                return json_error(
                    f'Timeout calling station {target_station}',
                    status=504  # Gateway Timeout
                )
            except requests.RequestException as e:
                return json_error(
                    f'Failed to call station {target_station}: {e}',
                    status=502  # Bad Gateway
                )

    # Smart load balancing (Phase 7.4)
    # If no explicit station was specified, consider load-based routing
    if not target_station:
        # Check if this is an execution request (not metadata/source/logs/test)
        is_execution = not any(param in request.GET for param in ['source', 'metadata', 'logs', 'versions', 'test', 'state', 'status'])

        if is_execution:
            # Try to find a better station based on load
            best_station = find_best_station(object_id)

            if best_station:
                # Route to best station
                try:
                    result = forward_request(
                        station_info=best_station,
                        object_id=object_id,
                        method='GET',
                        query_params=dict(request.GET),
                        timeout=30
                    )
                    result['_load_balanced'] = True
                    result['_original_station'] = os.environ.get('STATION_ID', 'unknown')
                    return json_response(json.dumps(result))
                except (requests.Timeout, requests.RequestException):
                    # If routing fails, fall through to local execution
                    pass

    # Local execution (either no @station_id or @local_station)
    # Find object file
    obj_file = find_object_file(object_id)
    if not obj_file:
        return json_error(f'Object not found: {object_id}', status=404)

    # Load object
    try:
        runtime = get_runtime()
        obj = runtime.load_object(str(obj_file), object_id=object_id)
    except Exception as e:
        return json_error(f'Failed to load object: {e}', status=500)

    # Check query parameters
    query = request.GET

    # View source code
    if query.get('source') == 'true':
        try:
            source = obj.get_source_code()
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': object_id,
                'source': source,
            }))
        except Exception as e:
            return json_error(f'Failed to get source: {e}', status=500)

    # View metadata
    if query.get('metadata') == 'true':
        try:
            metadata = obj.get_metadata()
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': object_id,
                'metadata': metadata,
            }))
        except Exception as e:
            return json_error(f'Failed to get metadata: {e}', status=500)

    # View state
    if query.get('state') == 'true':
        try:
            state = obj.get_state()
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': object_id,
                'state': state,
            }))
        except Exception as e:
            return json_error(f'Failed to get state: {e}', status=500)

    # Get schedule status
    if query.get('status') == 'true':
        try:
            schedules = runtime.get_schedules(object_id)
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': object_id,
                'running': len(schedules) > 0,
                'schedules': schedules
            }))
        except Exception as e:
            return json_error(f'Failed to get status: {e}', status=500)

    # Download file
    if query.get('file'):
        filename = query.get('file')
        try:
            content = obj.file_manager.get(filename)

            # Detect content type from file extension
            import mimetypes
            content_type, _ = mimetypes.guess_type(filename)
            if content_type is None:
                content_type = 'application/octet-stream'

            # Build headers
            headers = [
                ('content-type', content_type),
            ]

            # For images, use inline; for others, use attachment
            if content_type.startswith('image/'):
                headers.append(('content-disposition', f'inline; filename="{filename}"'))
            else:
                headers.append(('content-disposition', f'attachment; filename="{filename}"'))

            # Return binary response (status, headers, body)
            return 200, headers, [content]

        except FileNotFoundError:
            return json_error(f'File not found: {filename}', status=404)
        except Exception as e:
            return json_error(f'Failed to get file: {e}', status=500)

    # List files
    if query.get('files') == 'true':
        try:
            files = obj.file_manager.list()
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': object_id,
                'files': files,
                'count': len(files)
            }))
        except Exception as e:
            return json_error(f'Failed to list files: {e}', status=500)

    # Run tests (dogfooding - objects test themselves!)
    if query.get('test') == 'true':
        try:
            # Get the underlying module (obj.endpoint contains the actual loaded module)
            module = obj.endpoint

            # Find all test methods (functions starting with test_)
            test_methods = []
            for name in dir(module):
                if name.startswith('test_') and callable(getattr(module, name)):
                    test_methods.append(name)

            if not test_methods:
                return json_response(json.dumps({
                    'status': 'ok',
                    'object_id': object_id,
                    'message': 'No tests found (no test_* methods)',
                    'test_count': 0,
                    'results': []
                }))

            # Run each test
            results = []
            passed = 0
            failed = 0
            skipped = 0

            for test_name in test_methods:
                test_func = getattr(module, test_name)

                start_time = time.time()
                try:
                    result = test_func()
                    exec_time_ms = (time.time() - start_time) * 1000

                    # Normalize result
                    if isinstance(result, dict):
                        status = result.get('status', 'pass')
                    else:
                        status = 'pass'

                    if status == 'pass':
                        passed += 1
                    elif status == 'skip':
                        skipped += 1
                    else:
                        failed += 1

                    results.append({
                        'test': test_name,
                        'status': status,
                        'exec_time_ms': round(exec_time_ms, 2),
                        'result': result if isinstance(result, dict) else {'status': status}
                    })

                except AssertionError as e:
                    exec_time_ms = (time.time() - start_time) * 1000
                    failed += 1
                    results.append({
                        'test': test_name,
                        'status': 'fail',
                        'exec_time_ms': round(exec_time_ms, 2),
                        'error': str(e),
                        'error_type': 'AssertionError'
                    })

                except Exception as e:
                    exec_time_ms = (time.time() - start_time) * 1000
                    failed += 1
                    results.append({
                        'test': test_name,
                        'status': 'error',
                        'exec_time_ms': round(exec_time_ms, 2),
                        'error': str(e),
                        'error_type': type(e).__name__
                    })

            # Determine overall status
            overall_status = 'pass' if failed == 0 else 'fail'

            return json_response(json.dumps({
                'status': overall_status,
                'object_id': object_id,
                'test_count': len(test_methods),
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'results': results
            }))
        except Exception as e:
            return json_error(f'Failed to run tests: {e}', status=500)

    # View logs
    if query.get('logs') == 'true':
        try:
            level = query.get('level')  # Optional log level filter
            limit_str = query.get('limit', '100')
            limit = int(limit_str) if limit_str else 100

            logs = obj.get_logs(level=level, limit=limit)
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': object_id,
                'logs': logs,
                'count': len(logs),
            }))
        except Exception as e:
            return json_error(f'Failed to get logs: {e}', status=500)

    # View version history
    if query.get('versions') == 'true':
        try:
            limit_str = query.get('limit', '10')
            limit = int(limit_str) if limit_str else 10

            history = obj.get_version_history(limit=limit)
            return json_response(json.dumps({
                'status': 'ok',
                'object_id': object_id,
                'versions': history,
                'count': len(history),
            }))
        except Exception as e:
            return json_error(f'Failed to get version history: {e}', status=500)

    # Get specific version
    if query.get('version'):
        try:
            version_id = int(query.get('version'))
            version_data = obj.get_version(version_id)

            if not version_data:
                return json_error(f'Version not found: {version_id}', status=404)

            return json_response(json.dumps({
                'status': 'ok',
                'object_id': object_id,
                'version': version_data,
            }))
        except ValueError:
            return json_error('Invalid version number', status=400)
        except Exception as e:
            return json_error(f'Failed to get version: {e}', status=500)

    # Execute GET method (default)
    try:
        # Build request data from query parameters
        req_data = dict(query)

        result = obj.execute('GET', req_data)

        # Check if result specifies a content type (for HTML, images, etc.)
        if isinstance(result, dict) and result.get('content_type'):
            content_type = result.get('content_type')
            body = result.get('body', b'')

            # Build headers
            headers = [('content-type', content_type)]

            # Return binary/text response
            if isinstance(body, bytes):
                return 200, headers, [body]
            else:
                from dbbasic_web.responses import html as html_response
                return html_response(body)

        return json_response(json.dumps(result))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()

        # Log error to object's own logs (self-contained debugging)
        try:
            obj.logger.error(f'GET execution failed: {e}',
                           error=str(e),
                           traceback=tb)
        except:
            pass  # Don't fail if logging fails

        return json_error(f'Execution failed: {e}\n\n{tb}', status=500)


def POST(request, id: str):
    """Execute object's POST method (supports cross-station routing)"""
    # Parse routing syntax (Phase 7.2)
    object_id, target_station = parse_object_routing(id)

    # Check if this should be routed to another station
    if target_station:
        local_station = os.environ.get('STATION_ID', 'unknown')

        # If target is not local station, route to remote
        if target_station != local_station:
            station_info = get_station_info(target_station)

            if not station_info:
                return json_error(
                    f'Station not found or offline: {target_station}',
                    status=503
                )

            # Parse request body
            try:
                if request.body:
                    body_data = json.loads(request.body.decode('utf-8'))
                else:
                    body_data = dict(request.POST) if request.POST else dict(request.GET)
            except json.JSONDecodeError as e:
                return json_error(f'Invalid JSON: {e}', status=400)

            # Forward request
            try:
                result = forward_request(
                    station_info=station_info,
                    object_id=object_id,
                    method='POST',
                    query_params=dict(request.GET),
                    body_data=body_data,
                    timeout=30
                )
                return json_response(json.dumps(result))
            except requests.Timeout:
                return json_error(f'Timeout calling station {target_station}', status=504)
            except requests.RequestException as e:
                return json_error(f'Failed to call station {target_station}: {e}', status=502)

    # Local execution
    # Find object file
    obj_file = find_object_file(object_id)
    if not obj_file:
        return json_error(f'Object not found: {object_id}', status=404)

    # Load object
    try:
        runtime = get_runtime()
        obj = runtime.load_object(str(obj_file), object_id=object_id)
    except Exception as e:
        return json_error(f'Failed to load object: {e}', status=500)

    # Check for file upload (multipart/form-data)
    files = request.get('files', {})
    if files and len(files) > 0:
        try:
            uploaded_files = []

            for field_name, file_data in files.items():
                # file_data is a dict with 'filename', 'content', 'content_type'
                filename = file_data.get('filename', field_name)
                content = file_data.get('content', b'')

                # Store using FileManager
                obj.file_manager.put(filename, content)

                uploaded_files.append({
                    'filename': filename,
                    'size': len(content),
                    'field': field_name
                })

            return json_response(json.dumps({
                'status': 'ok',
                'message': f'Uploaded {len(uploaded_files)} file(s)',
                'object_id': object_id,
                'files': uploaded_files
            }))
        except Exception as e:
            return json_error(f'File upload failed: {e}', status=500)

    # Parse request body as JSON
    try:
        if request.body:
            req_data = json.loads(request.body.decode('utf-8'))
        else:
            # Fall back to form data or query params
            req_data = dict(request.POST) if request.POST else dict(request.GET)
    except UnicodeDecodeError as e:
        # Binary data (file upload) that wasn't caught above
        return json_error(f'Binary data in request body. Use ?file= parameter for file upload or ensure request.files is properly set. Debug: {e}', status=400)
    except json.JSONDecodeError as e:
        return json_error(f'Invalid JSON: {e}', status=400)

    # Check for special actions
    action = req_data.get('action')

    # Rollback to specific version
    if action == 'rollback':
        try:
            version_id = req_data.get('version_id')
            if not version_id:
                return json_error('version_id required for rollback', status=400)

            version_id = int(version_id)
            author = req_data.get('author', 'api_user')
            message = req_data.get('message', f'Rollback to version {version_id}')

            obj.rollback_to_version(version_id, author=author, message=message)

            return json_response(json.dumps({
                'status': 'ok',
                'message': f'Rolled back to version {version_id}',
                'version_id': version_id,
                'object_id': object_id,
            }))

        except Exception as e:
            return json_error(f'Rollback failed: {e}', status=500)

    # Start scheduled execution
    if action == 'start':
        try:
            # Call the object's start() method if it exists
            if hasattr(obj.endpoint, 'start'):
                result = obj.endpoint.start(req_data)
                return json_response(json.dumps({
                    'status': 'ok',
                    'message': 'Object started',
                    'object_id': object_id,
                    'result': result
                }))
            else:
                return json_error('Object has no start() method', status=400)
        except Exception as e:
            return json_error(f'Start failed: {e}', status=500)

    # Stop scheduled execution
    if action == 'stop':
        try:
            # Call the object's stop() method if it exists
            if hasattr(obj.endpoint, 'stop'):
                result = obj.endpoint.stop(req_data)
                return json_response(json.dumps({
                    'status': 'ok',
                    'message': 'Object stopped',
                    'object_id': object_id,
                    'result': result
                }))
            else:
                return json_error('Object has no stop() method', status=400)
        except Exception as e:
            return json_error(f'Stop failed: {e}', status=500)

    # Execute POST method (default - no special action)
    try:
        result = obj.execute('POST', req_data)
        return json_response(json.dumps(result))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()

        # Log error to object's own logs (self-contained debugging)
        try:
            obj.logger.error(f'POST execution failed: {e}',
                           error=str(e),
                           traceback=tb)
        except:
            pass  # Don't fail if logging fails

        return json_error(f'Execution failed: {e}\n\n{tb}', status=500)


def PUT(request, id: str):
    """Execute object's PUT method or update code (supports cross-station routing)"""
    # Parse routing syntax (Phase 7.2)
    object_id, target_station = parse_object_routing(id)

    # Check if this should be routed to another station
    if target_station:
        local_station = os.environ.get('STATION_ID', 'unknown')

        # If target is not local station, route to remote
        if target_station != local_station:
            station_info = get_station_info(target_station)

            if not station_info:
                return json_error(
                    f'Station not found or offline: {target_station}',
                    status=503
                )

            # Parse request body
            try:
                if request.body:
                    body_data = json.loads(request.body.decode('utf-8'))
                else:
                    body_data = dict(request.POST) if request.POST else dict(request.GET)
            except json.JSONDecodeError as e:
                return json_error(f'Invalid JSON: {e}', status=400)

            # Forward request
            try:
                result = forward_request(
                    station_info=station_info,
                    object_id=object_id,
                    method='PUT',
                    query_params=dict(request.GET),
                    body_data=body_data,
                    timeout=30
                )
                return json_response(json.dumps(result))
            except requests.Timeout:
                return json_error(f'Timeout calling station {target_station}', status=504)
            except requests.RequestException as e:
                return json_error(f'Failed to call station {target_station}: {e}', status=502)

    # Local execution
    # Find object file
    obj_file = find_object_file(object_id)
    if not obj_file:
        return json_error(f'Object not found: {object_id}', status=404)

    # Load object
    try:
        runtime = get_runtime()
        obj = runtime.load_object(str(obj_file), object_id=object_id)
    except Exception as e:
        return json_error(f'Failed to load object: {e}', status=500)

    # Check if this is a code update
    query = request.GET
    if query.get('source') == 'true':
        # Update source code
        try:
            if not request.body:
                return json_error('Missing request body', status=400)

            data = json.loads(request.body.decode('utf-8'))

            new_code = data.get('code')
            author = data.get('author', 'api')
            message = data.get('message', 'Updated via API')

            if not new_code:
                return json_error('Missing field: code', status=400)

            version_id = obj.update_code(
                new_code=new_code,
                author=author,
                message=message,
            )

            return json_response(json.dumps({
                'status': 'ok',
                'message': f'Code updated to version {version_id}',
                'version_id': version_id,
                'object_id': object_id,
            }))
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return json_error(f'Update failed: {e}\n\n{tb}', status=500)

    # Execute PUT method (default)
    try:
        if request.body:
            req_data = json.loads(request.body.decode('utf-8'))
        else:
            req_data = dict(request.POST) if request.POST else dict(request.GET)

        result = obj.execute('PUT', req_data)
        return json_response(json.dumps(result))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()

        # Log error to object's own logs (self-contained debugging)
        try:
            obj.logger.error(f'PUT execution failed: {e}',
                           error=str(e),
                           traceback=tb)
        except:
            pass  # Don't fail if logging fails

        return json_error(f'Execution failed: {e}\n\n{tb}', status=500)


def DELETE(request, id: str):
    """Execute object's DELETE method (supports cross-station routing)"""
    # Parse routing syntax (Phase 7.2)
    object_id, target_station = parse_object_routing(id)

    # Check if this should be routed to another station
    if target_station:
        local_station = os.environ.get('STATION_ID', 'unknown')

        # If target is not local station, route to remote
        if target_station != local_station:
            station_info = get_station_info(target_station)

            if not station_info:
                return json_error(
                    f'Station not found or offline: {target_station}',
                    status=503
                )

            # Parse request body
            try:
                if request.body:
                    body_data = json.loads(request.body.decode('utf-8'))
                else:
                    body_data = dict(request.POST) if request.POST else dict(request.GET)
            except json.JSONDecodeError as e:
                return json_error(f'Invalid JSON: {e}', status=400)

            # Forward request
            try:
                result = forward_request(
                    station_info=station_info,
                    object_id=object_id,
                    method='DELETE',
                    query_params=dict(request.GET),
                    body_data=body_data,
                    timeout=30
                )
                return json_response(json.dumps(result))
            except requests.Timeout:
                return json_error(f'Timeout calling station {target_station}', status=504)
            except requests.RequestException as e:
                return json_error(f'Failed to call station {target_station}: {e}', status=502)

    # Local execution
    # Find object file
    obj_file = find_object_file(object_id)
    if not obj_file:
        return json_error(f'Object not found: {object_id}', status=404)

    # Load object
    try:
        runtime = get_runtime()
        obj = runtime.load_object(str(obj_file), object_id=object_id)
    except Exception as e:
        return json_error(f'Failed to load object: {e}', status=500)

    # Parse request data
    try:
        if request.body:
            req_data = json.loads(request.body.decode('utf-8'))
        else:
            req_data = dict(request.POST) if request.POST else dict(request.GET)
    except json.JSONDecodeError as e:
        return json_error(f'Invalid JSON: {e}', status=400)

    # Execute DELETE method
    try:
        result = obj.execute('DELETE', req_data)
        return json_response(json.dumps(result))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()

        # Log error to object's own logs (self-contained debugging)
        try:
            obj.logger.error(f'DELETE execution failed: {e}',
                           error=str(e),
                           traceback=tb)
        except:
            pass  # Don't fail if logging fails

        return json_error(f'Execution failed: {e}\n\n{tb}', status=500)

"""
Object Inspector - Detailed view of a single object

Shows:
- Source code with syntax highlighting
- Recent logs
- Performance metrics
- Version history
- Actions (execute, rollback)

Access: http://localhost:8001/dashboard/object/{id}
"""
from dbbasic_web.responses import html as html_response


def GET(request, id=None):
    """Render object inspector HTML"""
    object_id = id or 'unknown'

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{object_id} - Object Inspector</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px 30px;
            border-radius: 12px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        h1 {{ font-size: 28px; }}
        .back-btn {{
            padding: 10px 20px;
            background: rgba(255,255,255,0.2);
            border: none;
            border-radius: 6px;
            color: white;
            cursor: pointer;
            text-decoration: none;
        }}
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }}
        .tab {{
            padding: 12px 24px;
            background: #1a1a1a;
            border: 1px solid #333;
            border-radius: 8px 8px 0 0;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tab.active {{
            background: #2a2a2a;
            border-color: #667eea;
            border-bottom-color: #2a2a2a;
        }}
        .content {{
            background: #2a2a2a;
            padding: 30px;
            border-radius: 0 8px 8px 8px;
            border: 1px solid #333;
            min-height: 500px;
        }}
        .tab-content {{
            display: none;
        }}
        .tab-content.active {{
            display: block;
        }}
        pre {{
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 14px;
            line-height: 1.6;
        }}
        .log-entry {{
            padding: 12px;
            margin-bottom: 8px;
            background: #1a1a1a;
            border-left: 4px solid #667eea;
            border-radius: 4px;
            font-family: monospace;
            font-size: 13px;
        }}
        .log-entry.error {{
            border-left-color: #ef4444;
            background: #2a1a1a;
        }}
        .log-entry.warn {{
            border-left-color: #fbbf24;
        }}
        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .metric-card {{
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #333;
        }}
        .metric-value {{ font-size: 32px; font-weight: bold; color: #667eea; }}
        .metric-label {{ color: #999; margin-top: 5px; font-size: 14px; }}
        .version-list {{
            list-style: none;
        }}
        .version-item {{
            padding: 15px;
            background: #1a1a1a;
            border-radius: 6px;
            margin-bottom: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .version-info {{
            flex: 1;
        }}
        .version-number {{
            font-weight: bold;
            color: #667eea;
        }}
        .version-date {{
            color: #999;
            font-size: 12px;
        }}
        .btn {{
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }}
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        .btn-primary:hover {{
            background: #5568d3;
        }}
        .btn-danger {{
            background: #ef4444;
            color: white;
        }}
        .btn-danger:hover {{
            background: #dc2626;
        }}
        .loading {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
        .chart-container {{
            height: 300px;
            background: #1a1a1a;
            border-radius: 8px;
            padding: 20px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 {object_id}</h1>
        <a href="/dashboard" class="back-btn">← Back to Dashboard</a>
    </div>

    <div class="tabs">
        <div class="tab active" onclick="switchTab('overview')">Overview</div>
        <div class="tab" onclick="switchTab('source')">Source Code</div>
        <div class="tab" onclick="switchTab('logs')">Logs</div>
        <div class="tab" onclick="switchTab('metrics')">Metrics</div>
        <div class="tab" onclick="switchTab('versions')">Versions</div>
    </div>

    <div class="content">
        <div id="overview" class="tab-content active">
            <h2 style="margin-bottom: 20px;">Object Overview</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value" id="version-count">-</div>
                    <div class="metric-label">Total Versions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="log-count">-</div>
                    <div class="metric-label">Total Logs</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="current-version">-</div>
                    <div class="metric-label">Current Version</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="last-modified">-</div>
                    <div class="metric-label">Last Modified</div>
                </div>
            </div>
            <div style="margin-top: 30px;">
                <h3 style="margin-bottom: 15px;">Quick Actions</h3>
                <button class="btn btn-primary" onclick="executeObject()">Execute (GET)</button>
                <button class="btn btn-primary" onclick="viewRawJSON()">View Raw JSON</button>
            </div>
        </div>

        <div id="source" class="tab-content">
            <h2 style="margin-bottom: 20px;">Source Code</h2>
            <pre id="source-code"><div class="loading">Loading source...</div></pre>
        </div>

        <div id="logs" class="tab-content">
            <h2 style="margin-bottom: 20px;">Recent Logs</h2>
            <div id="logs-container">
                <div class="loading">Loading logs...</div>
            </div>
        </div>

        <div id="metrics" class="tab-content">
            <h2 style="margin-bottom: 20px;">Performance Metrics</h2>
            <p style="color: #999; margin-bottom: 20px;">
                Extracted from object logs - useful for AI scheduling and debugging
            </p>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value" id="total-executions">-</div>
                    <div class="metric-label">Total Executions</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="error-rate">-</div>
                    <div class="metric-label">Error Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="avg-exec-time">-</div>
                    <div class="metric-label">Avg Execution (ms)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value" id="last-execution">-</div>
                    <div class="metric-label">Last Execution</div>
                </div>
            </div>
            <div style="margin-top: 30px;">
                <h3 style="margin-bottom: 15px;">Recent Performance</h3>
                <div id="recent-performance" style="background: #1a1a1a; padding: 20px; border-radius: 8px;">
                    <div class="loading">Loading performance data...</div>
                </div>
            </div>
        </div>

        <div id="versions" class="tab-content">
            <h2 style="margin-bottom: 20px;">Version History</h2>
            <ul id="versions-list" class="version-list">
                <li class="loading">Loading versions...</li>
            </ul>
        </div>
    </div>

    <script>
        const objectId = '{object_id}';

        function switchTab(tabName) {{
            // Update tab buttons
            document.querySelectorAll('.tab').forEach(tab => {{
                tab.classList.remove('active');
            }});
            event.target.classList.add('active');

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {{
                content.classList.remove('active');
            }});
            document.getElementById(tabName).classList.add('active');

            // Load content if needed
            if (tabName === 'source' && !window.sourceLoaded) {{
                loadSource();
                window.sourceLoaded = true;
            }}
            if (tabName === 'logs' && !window.logsLoaded) {{
                loadLogs();
                window.logsLoaded = true;
            }}
            if (tabName === 'metrics' && !window.metricsLoaded) {{
                loadMetrics();
                window.metricsLoaded = true;
            }}
            if (tabName === 'versions' && !window.versionsLoaded) {{
                loadVersions();
                window.versionsLoaded = true;
            }}
        }}

        async function loadMetadata() {{
            try {{
                const response = await fetch(`/objects/${{objectId}}?metadata=true`);
                const data = await response.json();

                document.getElementById('version-count').textContent = data.version_count || 0;
                document.getElementById('log-count').textContent = data.log_count || 0;
                document.getElementById('current-version').textContent = data.current_version || 1;
                document.getElementById('last-modified').textContent =
                    data.last_modified ? new Date(data.last_modified * 1000).toLocaleString() : 'Unknown';
            }} catch (e) {{
                console.error('Error loading metadata:', e);
            }}
        }}

        async function loadSource() {{
            try {{
                const response = await fetch(`/objects/${{objectId}}?source=true`);
                const data = await response.json();
                const source = data.source || 'No source found';
                document.getElementById('source-code').textContent = source;
            }} catch (e) {{
                document.getElementById('source-code').textContent = 'Error loading source: ' + e.message;
            }}
        }}

        async function loadLogs() {{
            try {{
                const response = await fetch(`/objects/${{objectId}}?logs=true&limit=50`);
                const data = await response.json();

                const container = document.getElementById('logs-container');
                container.innerHTML = '';

                if (!data.logs || data.logs.length === 0) {{
                    container.innerHTML = '<p style="color: #999;">No logs found</p>';
                    return;
                }}

                data.logs.forEach(log => {{
                    const entry = document.createElement('div');
                    entry.className = 'log-entry';
                    if (log.level === 'ERROR') entry.classList.add('error');
                    if (log.level === 'WARN') entry.classList.add('warn');

                    const timestamp = new Date(log.timestamp * 1000).toLocaleString();
                    entry.innerHTML = `
                        <strong>${{log.level || 'INFO'}}</strong> ${{timestamp}}<br>
                        ${{log.message || JSON.stringify(log)}}
                    `;
                    container.appendChild(entry);
                }});
            }} catch (e) {{
                document.getElementById('logs-container').innerHTML =
                    '<p style="color: #ef4444;">Error loading logs: ' + e.message + '</p>';
            }}
        }}

        async function loadVersions() {{
            try {{
                const response = await fetch(`/objects/${{objectId}}?versions=true`);
                const data = await response.json();

                const list = document.getElementById('versions-list');
                list.innerHTML = '';

                if (!data.versions || data.versions.length === 0) {{
                    list.innerHTML = '<li style="color: #999;">No versions found</li>';
                    return;
                }}

                data.versions.forEach(version => {{
                    const item = document.createElement('li');
                    item.className = 'version-item';
                    item.innerHTML = `
                        <div class="version-info">
                            <div class="version-number">Version ${{version.version}}</div>
                            <div class="version-date">${{new Date(version.timestamp * 1000).toLocaleString()}}</div>
                        </div>
                        <button class="btn btn-primary" onclick="rollbackTo(${{version.version}})">
                            Rollback
                        </button>
                    `;
                    list.appendChild(item);
                }});
            }} catch (e) {{
                document.getElementById('versions-list').innerHTML =
                    '<li style="color: #ef4444;">Error loading versions: ' + e.message + '</li>';
            }}
        }}

        async function loadMetrics() {{
            try {{
                const response = await fetch(`/objects/${{objectId}}?logs=true&limit=1000`);
                const data = await response.json();

                if (!data.logs || data.logs.length === 0) {{
                    document.getElementById('total-executions').textContent = '0';
                    document.getElementById('error-rate').textContent = '0%';
                    document.getElementById('avg-exec-time').textContent = 'N/A';
                    document.getElementById('last-execution').textContent = 'Never';
                    document.getElementById('recent-performance').innerHTML =
                        '<p style="color: #999;">No execution data available</p>';
                    return;
                }}

                const logs = data.logs;
                const total = logs.length;
                const errors = logs.filter(log => log.level === 'ERROR').length;
                const errorRate = total > 0 ? ((errors / total) * 100).toFixed(1) : 0;

                // Extract execution times from log messages (if present)
                const executionTimes = [];
                logs.forEach(log => {{
                    const match = log.message?.match(/(\d+(?:\.\d+)?)\s*ms/);
                    if (match) {{
                        executionTimes.push(parseFloat(match[1]));
                    }}
                }});

                const avgTime = executionTimes.length > 0
                    ? (executionTimes.reduce((a, b) => a + b, 0) / executionTimes.length).toFixed(2)
                    : 'N/A';

                // Last execution
                const lastLog = logs[0];  // logs are sorted newest first
                const lastExecution = lastLog ? new Date(lastLog.timestamp * 1000).toLocaleString() : 'Never';

                // Update metrics display
                document.getElementById('total-executions').textContent = total;
                document.getElementById('error-rate').textContent = errorRate + '%';
                document.getElementById('avg-exec-time').textContent = avgTime;
                document.getElementById('last-execution').textContent = lastExecution;

                // Build performance trend chart (last 10 executions with timing data)
                const recentPerf = executionTimes.slice(0, 10).reverse();
                let perfHTML = '';

                if (recentPerf.length > 0) {{
                    const maxTime = Math.max(...recentPerf);
                    perfHTML = '<div style="display: flex; gap: 10px; align-items: flex-end; height: 150px;">';
                    recentPerf.forEach((time, i) => {{
                        const height = (time / maxTime) * 100;
                        const color = time > avgTime * 1.5 ? '#ef4444' : (time > avgTime ? '#fbbf24' : '#4ade80');
                        perfHTML += `
                            <div style="flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end;">
                                <div style="font-size: 10px; color: #999; margin-bottom: 4px;">${{time.toFixed(1)}}ms</div>
                                <div style="width: 100%; background: ${{color}}; height: ${{height}}%; min-height: 5px; border-radius: 4px 4px 0 0;"></div>
                            </div>
                        `;
                    }});
                    perfHTML += '</div>';
                    perfHTML += '<div style="margin-top: 10px; font-size: 12px; color: #999;">Last 10 executions (green=fast, yellow=avg, red=slow)</div>';
                }} else {{
                    perfHTML = '<p style="color: #999;">No execution time data found in logs</p>';
                    perfHTML += '<p style="color: #666; font-size: 12px; margin-top: 10px;">Tip: Log execution times like "Completed in 42.5ms" to see performance trends</p>';
                }}

                document.getElementById('recent-performance').innerHTML = perfHTML;

            }} catch (e) {{
                console.error('Error loading metrics:', e);
                document.getElementById('recent-performance').innerHTML =
                    '<p style="color: #ef4444;">Error loading metrics: ' + e.message + '</p>';
            }}
        }}

        async function executeObject() {{
            try {{
                const response = await fetch(`/objects/${{objectId}}`);
                const result = await response.json();
                alert('Execution result:\\n' + JSON.stringify(result, null, 2));
            }} catch (e) {{
                alert('Error executing object: ' + e.message);
            }}
        }}

        function viewRawJSON() {{
            window.open(`/objects/${{objectId}}?metadata=true`, '_blank');
        }}

        async function rollbackTo(version) {{
            if (!confirm(`Rollback to version ${{version}}?`)) return;

            try {{
                const response = await fetch(`/objects/${{objectId}}`, {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ action: 'rollback', to: version }})
                }});
                const result = await response.json();
                alert('Rollback successful!');
                location.reload();
            }} catch (e) {{
                alert('Error rolling back: ' + e.message);
            }}
        }}

        // Initial load
        loadMetadata();
    </script>
</body>
</html>
    """

    return html_response(html)

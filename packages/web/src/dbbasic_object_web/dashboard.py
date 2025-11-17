"""
Dashboard - HTML interface for Object Primitive system

Provides visual interface to:
- See all objects
- View object details (code, logs, metrics)
- Monitor performance
- Trigger actions (execute, rollback)

Access: http://localhost:8001/dashboard
"""
from dbbasic_web.responses import html as html_response


def GET(request):
    """Render dashboard HTML"""

    html = """
<!DOCTYPE html>
<html>
<head>
    <title>Object Primitive Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #0a0a0a;
            color: #e0e0e0;
            padding: 20px;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
        }
        h1 { font-size: 32px; margin-bottom: 10px; }
        .subtitle { opacity: 0.9; font-size: 16px; }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #333;
        }
        .stat-value { font-size: 36px; font-weight: bold; color: #667eea; }
        .stat-label { color: #999; margin-top: 5px; }
        .objects-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .object-card {
            background: #1a1a1a;
            padding: 20px;
            border-radius: 8px;
            border: 1px solid #333;
            transition: all 0.3s;
            cursor: pointer;
        }
        .object-card:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }
        .object-name { font-size: 20px; font-weight: bold; margin-bottom: 10px; }
        .object-meta {
            display: flex;
            gap: 15px;
            margin: 10px 0;
            font-size: 14px;
            color: #999;
        }
        .object-actions {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .btn {
            padding: 8px 16px;
            border-radius: 4px;
            border: none;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.2s;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5568d3;
        }
        .btn-secondary {
            background: #333;
            color: #e0e0e0;
        }
        .btn-secondary:hover {
            background: #444;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        .metric {
            display: inline-block;
            background: #2a2a2a;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 8px;
        }
        .metric-good { color: #4ade80; }
        .metric-warn { color: #fbbf24; }
        .metric-error { color: #ef4444; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔮 Object Primitive Dashboard</h1>
        <div class="subtitle">Multi-system compute. Unix only solved single-system.</div>
    </div>

    <div class="stats">
        <div class="stat-card">
            <div class="stat-value" id="object-count">-</div>
            <div class="stat-label">Total Objects</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="station-count">-</div>
            <div class="stat-label">Active Stations</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="cluster-cpu">-</div>
            <div class="stat-label">Cluster CPU</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" id="cluster-memory">-</div>
            <div class="stat-label">Cluster Memory</div>
        </div>
    </div>

    <div id="cluster-stations" style="margin-bottom: 30px;">
        <h2 style="margin-bottom: 15px; color: #667eea;">Cluster Stations</h2>
        <div id="stations-grid" class="objects-grid">
            <div class="loading">Loading cluster status...</div>
        </div>
    </div>

    <h2 style="margin-bottom: 15px; color: #667eea;">Objects</h2>
    <div id="objects-container" class="objects-grid">
        <div class="loading">Loading objects...</div>
    </div>

    <script>
        // Fetch cluster stations
        async function loadClusterStats() {
            try {
                const response = await fetch('/cluster/stations');
                const data = await response.json();

                if (!data.stations) {
                    console.error('No stations found');
                    return;
                }

                // Update cluster stats
                const activeStations = data.stations.filter(s => s.is_active);
                document.getElementById('station-count').textContent =
                    `${activeStations.length}/${data.stations.length}`;

                // Calculate cluster-wide metrics
                let totalCpu = 0, totalMemory = 0, stationsWithMetrics = 0;
                for (const station of activeStations) {
                    if (station.metrics && station.metrics.cpu_percent !== undefined) {
                        totalCpu += station.metrics.cpu_percent;
                        totalMemory += station.metrics.memory_percent;
                        stationsWithMetrics++;
                    }
                }

                if (stationsWithMetrics > 0) {
                    const avgCpu = (totalCpu / stationsWithMetrics).toFixed(1);
                    const avgMemory = (totalMemory / stationsWithMetrics).toFixed(1);
                    document.getElementById('cluster-cpu').textContent = `${avgCpu}%`;
                    document.getElementById('cluster-memory').textContent = `${avgMemory}%`;
                } else {
                    document.getElementById('cluster-cpu').textContent = 'N/A';
                    document.getElementById('cluster-memory').textContent = 'N/A';
                }

                // Render stations grid
                const container = document.getElementById('stations-grid');
                container.innerHTML = '';

                for (const station of data.stations) {
                    const card = createStationCard(station);
                    container.appendChild(card);
                }

            } catch (error) {
                console.error('Error loading cluster stats:', error);
                document.getElementById('stations-grid').innerHTML =
                    '<div class="loading">Error loading cluster</div>';
            }
        }

        function createStationCard(station) {
            const card = document.createElement('div');
            card.className = 'object-card';

            // Master gets a crown, workers get colored circles
            const isMaster = station.station_id === 'station1';
            const statusClass = station.is_active ? 'metric-good' : 'metric-error';
            const statusText = station.is_active
                ? (isMaster ? '👑 Master' : '🟢 Active')
                : '🔴 Offline';

            let metricsHtml = '';
            if (station.metrics) {
                const m = station.metrics;
                metricsHtml = `
                    <div style="margin: 10px 0;">
                        <span class="metric">CPU: ${m.cpu_percent?.toFixed(1) || 0}%</span>
                        <span class="metric">RAM: ${m.memory_percent?.toFixed(1) || 0}%</span>
                        <span class="metric">Objects: ${m.object_count || 0}</span>
                    </div>
                `;
            }

            const version = station.version || 'unknown';
            const versionClass = version === 'unknown' ? 'metric-warning' : 'metric';

            card.innerHTML = `
                <div class="object-name">${station.station_id}</div>
                <div class="object-meta">
                    <span class="${statusClass}">${statusText}</span>
                    <span>${station.host}:${station.port}</span>
                    <span class="${versionClass}">v${version}</span>
                </div>
                ${metricsHtml}
                <div class="object-actions">
                    <button class="btn btn-primary" onclick="window.open('${station.url}/dashboard', '_blank')">
                        Open Dashboard
                    </button>
                    <button class="btn btn-secondary" onclick="window.open('${station.url}/objects', '_blank')">
                        View Objects
                    </button>
                </div>
            `;

            return card;
        }

        // Fetch all objects
        async function loadObjects() {
            try {
                const response = await fetch('/objects');
                const data = await response.json();

                if (!data.objects) {
                    console.error('No objects found');
                    return;
                }

                // Update stats
                document.getElementById('object-count').textContent = data.objects.length;

                // Render objects
                const container = document.getElementById('objects-container');
                container.innerHTML = '';

                for (const obj of data.objects) {
                    const card = await createObjectCard(obj);
                    container.appendChild(card);
                }

            } catch (error) {
                console.error('Error loading objects:', error);
                document.getElementById('objects-container').innerHTML =
                    '<div class="loading">Error loading objects</div>';
            }
        }

        async function createObjectCard(obj) {
            const card = document.createElement('div');
            card.className = 'object-card';

            // Fetch metadata for this object
            let metadata = {};
            try {
                const response = await fetch(`/objects/${obj.object_id}?metadata=true`);
                metadata = await response.json();
            } catch (e) {
                console.error(`Error fetching metadata for ${obj.object_id}:`, e);
            }

            card.innerHTML = `
                <div class="object-name">${obj.object_id}</div>
                <div class="object-meta">
                    <span>📝 ${metadata.version_count || 0} versions</span>
                    <span>📊 ${metadata.log_count || 0} logs</span>
                </div>
                <div style="margin: 10px 0;">
                    <span class="metric">Python Object</span>
                    ${obj.path ? '<span class="metric">' + obj.path + '</span>' : ''}
                </div>
                <div class="object-actions">
                    <button class="btn btn-primary" onclick="viewObject('${obj.object_id}')">
                        View Details
                    </button>
                    <button class="btn btn-secondary" onclick="viewLogs('${obj.object_id}')">
                        Logs
                    </button>
                    <button class="btn btn-secondary" onclick="viewSource('${obj.object_id}')">
                        Source
                    </button>
                </div>
            `;

            return card;
        }

        function viewObject(id) {
            window.location.href = `/dashboard/object/${id}`;
        }

        function viewLogs(id) {
            window.open(`/objects/${id}?logs=true`, '_blank');
        }

        function viewSource(id) {
            window.open(`/objects/${id}?source=true`, '_blank');
        }

        // Auto-refresh every 5 seconds
        setInterval(() => {
            loadClusterStats();
            loadObjects();
        }, 5000);

        // Initial load
        loadClusterStats();
        loadObjects();
    </script>
</body>
</html>
    """

    return html_response(html)

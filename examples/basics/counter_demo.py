"""
Counter Demo Page

Demonstrates the image counter with live updates.
"""


def GET(request):
    """Return HTML demo page with counter image"""

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Counter Demo</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                background: #0a0a0a;
                color: #e0e0e0;
                padding: 40px;
                margin: 0;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
            }
            h1 {
                color: #fff;
                margin-bottom: 20px;
            }
            .demo-box {
                background: #1a1a1a;
                padding: 40px;
                border-radius: 12px;
                border: 1px solid #333;
                text-align: center;
                max-width: 600px;
            }
            .counter-container {
                margin: 30px 0;
                padding: 20px;
                background: #0a0a0a;
                border-radius: 8px;
            }
            img {
                display: block;
                margin: 0 auto;
                border: 2px solid #0ea5e9;
                border-radius: 6px;
            }
            .info {
                color: #999;
                margin-top: 20px;
                font-size: 14px;
                line-height: 1.6;
            }
            button {
                background: #0ea5e9;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 16px;
                font-weight: 500;
                margin: 10px;
            }
            button:hover {
                background: #0284c7;
            }
            .url-box {
                background: #0a0a0a;
                padding: 15px;
                border-radius: 6px;
                margin-top: 20px;
                font-family: monospace;
                font-size: 13px;
                color: #0ea5e9;
                word-break: break-all;
            }
        </style>
    </head>
    <body>
        <div class="demo-box">
            <h1>📊 Image Counter Demo</h1>

            <div class="counter-container">
                <img id="counter" src="/objects/basics_counter_image@station1" alt="Hit Counter">
            </div>

            <button onclick="reloadCounter()">🔄 Reload (Increment)</button>
            <button onclick="resetCounter()">🔁 Reset Counter</button>

            <div class="info">
                <p><strong>How it works:</strong></p>
                <p>Every time the image is loaded, the counter increments.</p>
                <p>The count is stored in the object's state and persisted to disk.</p>
                <p>The image is generated on-the-fly using PIL (Python Imaging Library).</p>
            </div>

            <div class="url-box">
                &lt;img src="http://localhost:8001/objects/basics_counter_image"&gt;
            </div>
        </div>

        <script>
            function reloadCounter() {
                const img = document.getElementById('counter');
                // Add timestamp to bypass cache
                img.src = '/objects/basics_counter_image@station1?t=' + new Date().getTime();
            }

            function resetCounter() {
                fetch('/objects/basics_counter_image@station1', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({action: 'reset'})
                })
                .then(response => response.json())
                .then(data => {
                    alert(data.message);
                    reloadCounter();
                })
                .catch(err => alert('Error: ' + err));
            }

            // Auto-refresh every 5 seconds
            setInterval(reloadCounter, 5000);
        </script>
    </body>
    </html>
    """

    return {
        'status': 'ok',
        'content_type': 'text/html',
        'body': html
    }

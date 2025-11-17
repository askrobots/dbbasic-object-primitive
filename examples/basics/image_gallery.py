"""
Image Gallery Object

Demonstrates file storage with image display.
Shows uploaded images in an HTML gallery.
"""


def GET(request):
    """Return HTML gallery of uploaded images"""

    # Get list of files
    files = _files.list()

    # Filter for images
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
    images = [f for f in files if any(f['name'].lower().endswith(ext) for ext in image_extensions)]

    # Build HTML gallery
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Gallery</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
                background: #0a0a0a;
                color: #e0e0e0;
                padding: 40px;
                margin: 0;
            }
            h1 {
                color: #fff;
                margin-bottom: 30px;
            }
            .gallery {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }
            .image-card {
                background: #1a1a1a;
                border-radius: 8px;
                overflow: hidden;
                border: 1px solid #333;
                transition: transform 0.2s;
            }
            .image-card:hover {
                transform: scale(1.02);
                border-color: #0ea5e9;
            }
            .image-card img {
                width: 100%;
                height: 200px;
                object-fit: cover;
                display: block;
            }
            .image-info {
                padding: 15px;
            }
            .image-name {
                font-weight: 600;
                color: #fff;
                margin-bottom: 8px;
                word-break: break-word;
            }
            .image-size {
                color: #999;
                font-size: 13px;
            }
            .upload-form {
                background: #1a1a1a;
                padding: 25px;
                border-radius: 8px;
                border: 1px solid #333;
                margin-bottom: 30px;
            }
            .upload-form h2 {
                margin-top: 0;
                color: #fff;
            }
            input[type="file"] {
                display: block;
                margin: 15px 0;
                color: #e0e0e0;
            }
            button {
                background: #0ea5e9;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 500;
            }
            button:hover {
                background: #0284c7;
            }
            .empty {
                text-align: center;
                padding: 60px 20px;
                color: #999;
            }
        </style>
    </head>
    <body>
        <h1>Image Gallery</h1>

        <div class="upload-form">
            <h2>Upload Image</h2>
            <form action="/objects/basics_image_gallery" method="POST" enctype="multipart/form-data">
                <input type="file" name="file" accept="image/*" required>
                <button type="submit">Upload</button>
            </form>
        </div>

        <div class="gallery">
    """

    if len(images) == 0:
        html += """
            <div class="empty">No images uploaded yet. Use the form above to upload images.</div>
        """
    else:
        for img in images:
            size_kb = img['size'] / 1024
            html += f"""
            <div class="image-card">
                <a href="/objects/basics_image_gallery?file={img['name']}" target="_blank">
                    <img src="/objects/basics_image_gallery?file={img['name']}" alt="{img['name']}">
                </a>
                <div class="image-info">
                    <div class="image-name">{img['name']}</div>
                    <div class="image-size">{size_kb:.1f} KB</div>
                </div>
            </div>
            """

    html += """
        </div>
    </body>
    </html>
    """

    return {
        'status': 'ok',
        'content_type': 'text/html',
        'body': html
    }


def POST(request):
    """Handle image upload"""
    # The API handler will process file uploads automatically
    # and store them using _files.put()

    return {
        'status': 'ok',
        'message': 'Image uploaded successfully',
        'redirect': '/objects/basics_image_gallery'
    }

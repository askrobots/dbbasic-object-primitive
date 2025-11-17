"""
Image Counter Object

Classic web counter that serves a PNG image with the hit count.
Increments on every request.

Usage:
    <img src="http://localhost:8001/objects/basics_counter_image">
"""
from PIL import Image, ImageDraw, ImageFont
import io


def GET(request):
    """Return counter image and increment count"""

    # Get current count (default to 0)
    count = _state_manager.get('hits', 0)

    # Increment counter
    count += 1
    _state_manager.set('hits', count)

    # Log the hit
    _logger.info(f'Counter hit #{count}')

    # Create image with counter
    width = 200
    height = 60

    # Create image with gradient background
    img = Image.new('RGB', (width, height), color='#1a1a1a')
    draw = ImageDraw.Draw(img)

    # Draw border
    draw.rectangle([0, 0, width-1, height-1], outline='#0ea5e9', width=3)

    # Draw "HITS:" label
    try:
        # Try to use a nice font
        font_label = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial.ttf', 16)
        font_count = ImageFont.truetype('/System/Library/Fonts/Supplemental/Arial Bold.ttf', 28)
    except:
        # Fallback to default font
        font_label = ImageFont.load_default()
        font_count = ImageFont.load_default()

    # Draw label
    label_text = "HITS:"
    draw.text((15, 12), label_text, fill='#999999', font=font_label)

    # Draw count
    count_text = f"{count:,}"  # Format with commas

    # Center the count text
    bbox = draw.textbbox((0, 0), count_text, font=font_count)
    text_width = bbox[2] - bbox[0]
    text_x = (width - text_width) // 2

    draw.text((text_x, 28), count_text, fill='#0ea5e9', font=font_count)

    # Convert image to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    content = img_bytes.read()

    # Return image with proper headers
    return {
        'status': 'ok',
        'content_type': 'image/png',
        'body': content,
        'count': count
    }


def POST(request):
    """Reset counter"""
    action = request.get('action')

    if action == 'reset':
        _state_manager.set('hits', 0)
        _logger.warning('Counter reset to 0')

        return {
            'status': 'ok',
            'message': 'Counter reset to 0'
        }

    return {
        'status': 'error',
        'message': 'Unknown action'
    }

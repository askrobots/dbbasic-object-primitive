#!/usr/bin/env python3
"""
Run the dbbasic-web server for the Object Primitive System

Usage:
    python run_server.py

Then access:
    http://localhost:8000/objects - List all objects
    http://localhost:8000/objects/basics_counter - Execute counter object
"""
import os
import uvicorn
from pathlib import Path

# Set station ID (station1 is master)
os.environ['STATION_ID'] = 'station1'

# Set the base directory for dbbasic-web routing
import dbbasic_web.settings
dbbasic_web.settings.BASE_DIR = Path(__file__).parent

if __name__ == "__main__":
    print("=" * 60)
    print("Object Primitive System REST API Server")
    print("=" * 60)
    print()
    print("Server starting on http://localhost:8000")
    print()
    print("Available endpoints:")
    print("  GET  /objects - List all objects")
    print("  GET  /objects/{id} - Execute object's GET method")
    print("  GET  /objects/{id}?source=true - View source code")
    print("  GET  /objects/{id}?metadata=true - View metadata")
    print("  GET  /objects/{id}?logs=true - View logs")
    print("  GET  /objects/{id}?versions=true - View version history")
    print("  POST /objects/{id} - Execute object's POST method")
    print("  PUT  /objects/{id} - Execute object's PUT method")
    print("  PUT  /objects/{id}?source=true - Update code")
    print("  DELETE /objects/{id} - Execute object's DELETE method")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    uvicorn.run(
        "dbbasic_web.asgi:app",
        host="0.0.0.0",
        port=8001,
        reload=True,  # Auto-reload on code changes
        log_level="info",
    )

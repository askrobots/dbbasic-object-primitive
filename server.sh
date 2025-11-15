#!/bin/bash
# Server management script with PID file support

PID_FILE=".server.pid"
LOG_FILE="server.log"

case "$1" in
    start)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "Server is already running (PID: $PID)"
                exit 1
            else
                echo "Removing stale PID file"
                rm "$PID_FILE"
            fi
        fi

        echo "Starting server..."
        .venv/bin/python run_server.py > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        echo "Server started (PID: $(cat $PID_FILE))"
        echo "Logs: tail -f $LOG_FILE"
        ;;

    stop)
        if [ ! -f "$PID_FILE" ]; then
            echo "PID file not found. Server not running?"
            exit 1
        fi

        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Stopping server (PID: $PID)..."
            kill "$PID"
            rm "$PID_FILE"
            echo "Server stopped"
        else
            echo "Server not running (stale PID file)"
            rm "$PID_FILE"
        fi
        ;;

    restart)
        $0 stop
        sleep 2
        $0 start
        ;;

    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat "$PID_FILE")
            if ps -p "$PID" > /dev/null 2>&1; then
                echo "Server is running (PID: $PID)"
            else
                echo "Server is not running (stale PID file)"
            fi
        else
            echo "Server is not running"
        fi
        ;;

    logs)
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            echo "Log file not found"
        fi
        ;;

    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac

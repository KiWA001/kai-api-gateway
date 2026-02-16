#!/bin/bash
# Run K-AI API as a Background Daemon
# ===================================
# This script runs the API in the background with auto-restart

cd ~/kai-api

APP_NAME="kai-api"
PID_FILE="/tmp/kai-api.pid"
LOG_FILE="/tmp/kai-api.log"

start() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "✅ $APP_NAME is already running (PID: $(cat $PID_FILE))"
        return
    fi
    
    echo "🚀 Starting $APP_NAME..."
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Set environment
    export PYTHONUNBUFFERED=1
    export ENVIRONMENT=production
    
    # Load .env if exists
    if [ -f ".env" ]; then
        export $(cat .env | grep -v '^#' | xargs)
    fi
    
    # Start with nohup
    nohup uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 > "$LOG_FILE" 2>&1 &
    
    # Save PID
    echo $! > "$PID_FILE"
    
    echo "✅ $APP_NAME started (PID: $(cat $PID_FILE))"
    echo "📄 Logs: $LOG_FILE"
    echo "🌐 API: http://$(curl -s ifconfig.me):8000"
    echo "🔧 Admin: http://$(curl -s ifconfig.me):8000/qazmlp"
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "❌ $APP_NAME is not running"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    echo "🛑 Stopping $APP_NAME (PID: $PID)..."
    
    kill $PID 2>/dev/null
    sleep 2
    
    if kill -0 $PID 2>/dev/null; then
        echo "💥 Force killing..."
        kill -9 $PID 2>/dev/null
    fi
    
    rm -f "$PID_FILE"
    echo "✅ $APP_NAME stopped"
}

restart() {
    stop
    sleep 2
    start
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 $(cat "$PID_FILE") 2>/dev/null; then
        echo "✅ $APP_NAME is running (PID: $(cat $PID_FILE))"
        echo "🌐 API: http://$(curl -s ifconfig.me):8000"
        echo ""
        echo "📊 Recent logs:"
        tail -20 "$LOG_FILE"
    else
        echo "❌ $APP_NAME is not running"
        rm -f "$PID_FILE"
    fi
}

logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "❌ No log file found"
    fi
}

case "${1:-start}" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac

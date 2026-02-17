#!/bin/bash
# Deploy OpenCode Microservice to AWS
# ===================================

set -e

EC2_IP="44.201.146.74"
KEY_PATH="${1:-~/Downloads/kai-api-server.pem}"

echo "🚀 Deploying OpenCode Microservice to AWS..."
echo "IP: $EC2_IP"
echo "Key: $KEY_PATH"

# 1. Upload microservice
echo "📤 Uploading microservice..."
scp -i "$KEY_PATH" opencode_microservice.py requirements.txt ubuntu@$EC2_IP:~/

# 2. Setup and run on EC2
echo "🔧 Setting up on EC2..."
ssh -i "$KEY_PATH" ubuntu@$EC2_IP << 'REMOTE'

cd ~

# Install dependencies if needed
pip3 install fastapi uvicorn aiohttp -q 2>/dev/null || true

# Kill any existing server
pkill -f "opencode_microservice" 2>/dev/null || true
sleep 2

# Start microservice in background
echo "🚀 Starting OpenCode Microservice..."
nohup python3 opencode_microservice.py > /tmp/opencode-service.log 2>&1 &

sleep 3

# Check if running
if pgrep -f "opencode_microservice" > /dev/null; then
    echo "✅ Microservice is running!"
    echo ""
    echo "🌐 Service URL: http://$(curl -s ifconfig.me):8000"
    echo "🧪 Test: curl http://$(curl -s ifconfig.me):8000/health"
else
    echo "❌ Failed to start. Check logs:"
    echo "   cat /tmp/opencode-service.log"
fi

REMOTE

echo ""
echo "========================================"
echo "✅ DEPLOYMENT COMPLETE!"
echo "========================================"
echo ""
echo "OpenCode Microservice is running at:"
echo "  http://$EC2_IP:8000"
echo ""
echo "Test it:"
echo "  curl http://$EC2_IP:8000/health"
echo ""
echo "Next: Update HuggingFace provider to use this URL"

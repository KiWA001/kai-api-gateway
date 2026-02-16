#!/bin/bash
# AWS Deployment Script - Automatic Upload and Setup
# ==================================================
# This script uploads files to EC2 and sets everything up automatically

set -e  # Exit on error

# Configuration
EC2_IP="44.201.146.74"
EC2_USER="ubuntu"
KEY_PATH=""  # Will be set interactively
REMOTE_DIR="/home/ubuntu/kai-api"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running from KAI_API directory
if [ ! -f "main.py" ] || [ ! -d "providers" ]; then
    print_error "Please run this script from the KAI_API directory"
    exit 1
fi

# Get SSH key path
read -p "Enter path to your .pem key file (e.g., ~/Downloads/kai-api-key.pem): " KEY_PATH
KEY_PATH="${KEY_PATH/#\~/$HOME}"  # Expand ~ to home directory

if [ ! -f "$KEY_PATH" ]; then
    print_error "Key file not found: $KEY_PATH"
    exit 1
fi

# Fix key permissions
chmod 600 "$KEY_PATH"
print_success "Key permissions set to 600"

print_status "Starting deployment to EC2 instance: $EC2_IP"
print_status "This will upload files and set up the server automatically..."

echo ""
read -p "Press Enter to continue..."

# Step 1: Test SSH connection
print_status "Testing SSH connection..."
if ssh -i "$KEY_PATH" -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$EC2_USER@$EC2_IP" "echo 'SSH connection successful'" 2>/dev/null; then
    print_success "SSH connection successful"
else
    print_error "Cannot connect to EC2 instance. Please check:"
    print_error "  1. Instance is running"
    print_error "  2. Security group allows port 22 from your IP"
    print_error "  3. Key file is correct"
    exit 1
fi

# Step 2: Create remote directory
print_status "Creating remote directory..."
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" "mkdir -p $REMOTE_DIR"

# Step 3: Upload files
print_status "Uploading files to EC2 (this may take a few minutes)..."
print_status "Uploading application files..."

# Create a list of files to upload (excluding unnecessary files)
cat > /tmp/upload_list.txt << 'EOF'
main.py
config.py
models.py
engine.py
services.py
db.py
auth.py
v1_router.py
admin_router.py
copilot_portal.py
copilot_session.py
browser_portal.py
opencode_terminal.py
proxy_manager.py
provider_state.py
provider_sessions.py
search_engine.py
error_handling.py
utils.py
sanitizer.py
useragent.py
requirements.txt
aws-setup.sh
start-production.sh
run-daemon.sh
Dockerfile
EOF

# Upload the list and files
rsync -avz --progress \
    -e "ssh -i $KEY_PATH" \
    --files-from=/tmp/upload_list.txt \
    . \
    "$EC2_USER@$EC2_IP:$REMOTE_DIR/"

print_status "Uploading providers directory..."
rsync -avz --progress \
    -e "ssh -i $KEY_PATH" \
    providers/ \
    "$EC2_USER@$EC2_IP:$REMOTE_DIR/providers/"

print_status "Uploading static directory..."
rsync -avz --progress \
    -e "ssh -i $KEY_PATH" \
    static/ \
    "$EC2_USER@$EC2_IP:$REMOTE_DIR/static/"

print_success "All files uploaded successfully!"

# Step 4: Run setup on EC2
print_status "Running setup on EC2 instance..."
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" << 'REMOTE_SCRIPT'

cd ~/kai-api

echo "=========================================="
echo "🚀 Starting K-AI API Setup"
echo "=========================================="

# Update system
echo "📦 Updating system packages..."
sudo apt-get update -y

# Install dependencies
echo "🔧 Installing dependencies..."
sudo apt-get install -y \
    git curl wget build-essential \
    python3 python3-pip python3-venv \
    nginx certbot python3-certbot-nginx \
    software-properties-common \
    apt-transport-https ca-certificates \
    gnupg lsb-release

# Install Node.js 18.x
echo "⬇️ Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

echo "✅ Node.js version: $(node --version)"
echo "✅ npm version: $(npm --version)"

# Install Docker
echo "🐳 Installing Docker..."
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Playwright dependencies
echo "🎭 Installing Playwright dependencies..."
sudo apt-get install -y \
    libnss3 libatk-bridge2.0-0 libxss1 \
    libgtk-3-0 libgbm1 libasound2

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "📥 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
echo "🎭 Installing Playwright browsers..."
playwright install chromium

echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "To start the server, run:"
echo "  cd ~/kai-api && ./start-production.sh"
echo ""
echo "Or run as background daemon:"
echo "  cd ~/kai-api && ./run-daemon.sh start"
echo ""

REMOTE_SCRIPT

print_success "Setup completed on EC2!"

# Step 5: Start the server
print_status "Starting the server..."
ssh -i "$KEY_PATH" "$EC2_USER@$EC2_IP" << 'REMOTE_SCRIPT'

cd ~/kai-api

# Kill any existing processes
pkill -f uvicorn 2>/dev/null || true

# Start the server in background
nohup ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 > /tmp/kai-api.log 2>&1 &

# Wait a moment for startup
sleep 5

# Check if it's running
if pgrep -f uvicorn > /dev/null; then
    echo "✅ Server is running!"
    echo ""
    echo "🌐 Your API is available at:"
    echo "   http://$(curl -s ifconfig.me):8000"
    echo ""
    echo "🔧 Admin Portal:"
    echo "   http://$(curl -s ifconfig.me):8000/qazmlp"
    echo ""
    echo "📚 API Docs:"
    echo "   http://$(curl -s ifconfig.me):8000/docs"
else
    echo "❌ Server failed to start. Check logs:"
    echo "   cat /tmp/kai-api.log"
fi

REMOTE_SCRIPT

echo ""
echo "=========================================="
print_success "DEPLOYMENT COMPLETE!"
echo "=========================================="
echo ""
echo "🌐 Your K-AI API is now running at:"
echo "   http://$EC2_IP:8000"
echo ""
echo "🔧 Admin Portal (OpenCode Terminal):"
echo "   http://$EC2_IP:8000/qazmlp"
echo ""
echo "📚 API Documentation:"
echo "   http://$EC2_IP:8000/docs"
echo ""
echo "📊 To check server status:"
echo "   ssh -i $KEY_PATH $EC2_USER@$EC2_IP 'cd ~/kai-api && ./run-daemon.sh status'"
echo ""
echo "📝 To view logs:"
echo "   ssh -i $KEY_PATH $EC2_USER@$EC2_IP 'tail -f /tmp/kai-api.log'"
echo ""

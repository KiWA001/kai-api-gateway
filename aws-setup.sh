#!/bin/bash
# AWS EC2 Deployment Script for K-AI API
# ======================================
# This script sets up the K-AI API on an AWS EC2 instance
# Run this on your EC2 instance after creating it

set -e  # Exit on error

echo "🚀 Starting K-AI API deployment on AWS EC2..."

# Update system
echo "📦 Updating system packages..."
sudo apt-get update && sudo apt-get upgrade -y

# Install essential packages
echo "🔧 Installing dependencies..."
sudo apt-get install -y \
    git \
    curl \
    wget \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    certbot \
    python3-certbot-nginx \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install Node.js 18.x (required for OpenCode)
echo "⬇️ Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify installations
echo "✅ Checking installations..."
python3 --version
node --version
npm --version

# Install Docker
echo "🐳 Installing Docker..."
sudo apt-get install -y docker.io docker-compose
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER

# Install Playwright dependencies (for browser portals)
echo "🎭 Installing Playwright dependencies..."
sudo apt-get install -y \
    libnss3 \
    libatk-bridge2.0-0 \
    libxss1 \
    libgtk-3-0 \
    libgbm1 \
    libasound2

# Create app directory
echo "📁 Creating app directory..."
mkdir -p ~/kai-api
cd ~/kai-api

# Clone your repository (you'll need to replace this URL)
echo "📥 Cloning repository..."
# git clone https://github.com/YOUR_USERNAME/KAI_API.git .
# OR if using SCP/SFTP to upload files:
echo "⏳ Waiting for application files..."
echo "Please upload your K-AI API files to ~/kai-api/"
echo "You can use: scp -r /local/path/to/KAI_API/* ubuntu@YOUR_EC2_IP:~/kai-api/"

# Create a flag file to indicate setup is complete
touch ~/kai-api/.setup-complete

echo ""
echo "=========================================="
echo "✅ EC2 Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Upload your K-AI API files to ~/kai-api/"
echo "2. Run: cd ~/kai-api && ./start-production.sh"
echo ""
echo "Your EC2 instance is ready!"

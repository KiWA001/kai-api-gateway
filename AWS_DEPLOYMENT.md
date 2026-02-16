# AWS Deployment Guide for K-AI API

This guide will help you deploy the K-AI API to AWS EC2 with OpenCode in **Anonymous + Disposable Mode**.

## Overview

- **Platform**: AWS EC2 (Ubuntu 22.04 LTS)
- **Instance Type**: t3.medium minimum (2 vCPU, 4GB RAM)
- **Port**: 8000 (HTTP)
- **Mode**: Anonymous + Disposable (auto-reset after 20 messages)

## Key Features

### 🔒 Anonymous Mode
- No login required
- No credentials stored anywhere
- Fresh device identity for each session
- Random device/session IDs generated on startup

### 🗑️ Disposable Mode
- **Auto-reset after 20 messages** - Complete wipe and fresh start
- **New chat between each message** - No context carryover
- **Aggressive cleanup** - Removes ALL traces (config files, cache, temp files)
- **Appears as new device** - OpenCode sees a completely different device

### 🧹 What Gets Cleaned
- All config directories
- All cache and temp files
- NPM/npx cache
- Session directories
- Any stored identifiers

## Prerequisites

1. **AWS Account** with EC2 access
2. **SSH Key Pair** created in AWS
3. **Local terminal** with SSH access

## Step 1: Create EC2 Instance

1. Go to AWS Console → EC2 → Launch Instance
2. **Name**: `kai-api-server`
3. **AMI**: Ubuntu 22.04 LTS (64-bit)
4. **Instance Type**: t3.medium or larger
5. **Key Pair**: Select your existing key pair or create new
6. **Network Settings**:
   - Create security group
   - Allow SSH (port 22) from your IP
   - Allow HTTP (port 80) from anywhere
   - Allow Custom TCP (port 8000) from anywhere

7. **Storage**: 20 GB gp3 (minimum)
8. Click **Launch Instance**

## Step 2: Get Your EC2 Details

Once the instance is running, note down:
- **Public IPv4 address** (e.g., `54.123.456.789`)
- **Key pair file path** on your local machine (e.g., `~/Downloads/kai-api-key.pem`)

## Step 3: Deploy to AWS (Easy Method)

We provide a simple deployment script. Run this from your local machine:

```bash
# Make scripts executable
chmod +x deploy-to-aws.sh aws-setup.sh start-production.sh run-daemon.sh

# Run deployment
./deploy-to-aws.sh -i ~/Downloads/kai-api-key.pem -h 54.123.456.789 -u ubuntu
```

This will:
1. Upload all files to your EC2 instance
2. Run the setup automatically
3. Install all dependencies
4. Start the server

## Step 4: Access Your API

Once deployed:
- **API**: http://YOUR_EC2_IP:8000
- **Admin Portal**: http://YOUR_EC2_IP:8000/qazmlp
- **API Docs**: http://YOUR_EC2_IP:8000/docs

## Managing the Server

SSH into your EC2 instance:
```bash
ssh -i ~/Downloads/kai-api-key.pem ubuntu@54.123.456.789
```

### Server Commands

```bash
cd ~/kai-api

# Start in foreground (good for testing)
./start-production.sh

# Run as background daemon
./run-daemon.sh start

# Check status
./run-daemon.sh status

# View logs
./run-daemon.sh logs

# Stop server
./run-daemon.sh stop

# Restart server
./run-daemon.sh restart
```

## Using OpenCode in Disposable Mode

### From the Admin Portal (/qazmlp):

1. Go to **Browser Portal** section
2. Select **"🖥️ OpenCode (Kimi K2.5 Free)"** from dropdown
3. Click **Connect**
4. You'll see the **Disposable Mode Status Bar** showing:
   - Message count (0/20)
   - Progress bar
   - Reset timer
   - Manual reset button

### Disposable Mode Features:

✅ **Automatic**:
- New chat starts before EVERY message (no context carryover)
- After 20 messages: Complete reset automatically
- Fresh device identity generated
- All traces wiped clean

✅ **Manual Control**:
- Click **"🔄 Reset Now"** anytime to force a reset
- Status bar shows messages remaining
- Visual warning when approaching reset (last 5 messages)

### What Happens During Reset:

1. Current session closed
2. ALL files cleaned up:
   - Config files
   - Cache files
   - Temp files
   - Session directories
   - NPM cache
3. Fresh identity generated
4. New session started
5. OpenCode sees a **completely new device**

### API Endpoints for Disposable Mode:

```bash
# Check disposable status
curl "http://YOUR_EC2_IP:8000/qaz/terminal/status?model=kimi-k2.5-free"

# Response:
# {
#   "status": "success",
#   "data": {
#     "message_count": 5,
#     "max_messages": 20,
#     "messages_remaining": 15,
#     "auto_reset_enabled": true,
#     "new_chat_between_messages": true,
#     "is_running": true,
#     "anonymous_mode": true
#   }
# }

# Manual reset (wipe everything and start fresh)
curl -X POST http://YOUR_EC2_IP:8000/qaz/terminal/reset \
  -H "Content-Type: application/json" \
  -d '{"model": "kimi-k2.5-free"}'

# Response:
# {
#   "status": "success",
#   "message": "Full disposable reset completed - OpenCode sees a brand new device!",
#   "model": "kimi-k2.5-free"
# }
```

## How It Works

### Message Flow:
1. User sends message
2. System starts **new chat** (clears context)
3. Message sent to OpenCode
4. Response received
5. Message counter incremented
6. If counter >= 20 → **Full reset triggered**

### Reset Process:
```
[20 messages reached]
    ↓
[Close session]
    ↓
[Delete ALL files]
    ↓
[Clear ALL caches]
    ↓
[Generate new identity]
    ↓
[Start fresh session]
    ↓
[OpenCode sees new device]
```

## Security & Privacy

🔒 **Anonymous Mode Guarantees**:
- No credentials stored
- No login required
- No persistent identifiers
- Fresh identity each session

🗑️ **Disposable Mode Guarantees**:
- All traces removed after reset
- No tracking possible between sessions
- Context never carries over
- Appears as completely different device

## Available Free Models

All models work in disposable mode:

- **kimi-k2.5-free** (Kimi K2.5 Free)
- **minimax-m2.5-free** (MiniMax M2.5 Free)
- **big-pickle** (Big Pickle)
- **glm-4.7** (GLM 4.7)

## Troubleshooting

### Can't connect to EC2:
```bash
chmod 600 ~/Downloads/kai-api-key.pem
```

### Server not starting:
```bash
./run-daemon.sh logs
# Or run in foreground
./start-production.sh
```

### OpenCode not resetting:
- Check status: `curl "http://IP:8000/qaz/terminal/status"`
- Manual reset: Use the "🔄 Reset Now" button
- Check logs: `./run-daemon.sh logs`

### Too many resets happening?
- Default is 20 messages per reset
- You can change this in `opencode_terminal.py`:
```python
MAX_MESSAGES_BEFORE_RESET = 20  # Change this number
```

## Cost Estimation

- **t3.medium**: ~$30/month (on-demand)
- **t3.large**: ~$60/month (on-demand)
- **Data transfer**: Variable

Use Reserved Instances for 30-60% savings.

## Files You Can Modify

- `opencode_terminal.py` - Change disposable mode settings
- `aws-setup.sh` - Change EC2 setup
- `start-production.sh` - Change how server starts
- `run-daemon.sh` - Change daemon behavior

## Need Help?

1. Check logs: `./run-daemon.sh logs`
2. Verify EC2 security group allows port 8000
3. Ensure Node.js 18+ is installed
4. Check disposable status endpoint

---

## Summary

Your OpenCode integration now:
✅ Requires NO login
✅ Stores NO credentials  
✅ Auto-resets every 20 messages
✅ Starts new chat between messages
✅ Wipes ALL traces on reset
✅ Appears as new device to OpenCode

**You get fresh free tokens automatically with each reset!**

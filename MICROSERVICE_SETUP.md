# OpenCode Microservice Setup Guide

## Your New Architecture
```
HuggingFace Space (Free Forever)
├── All browser providers (Copilot, Gemini, HuggingChat)
├── Main API endpoints
└── OpenCode calls → AWS

AWS EC2 (t3.micro - Free Tier)
└── OpenCode Microservice Only
    └── Disposable mode, terminal access
```

## What You Need to Do (Lazy Mode)

### Step 1: Remove GitHub Auto-Deploy (2 minutes)
Go to: https://github.com/KiWA001/kai-api-gateway/settings/secrets/actions

Click "Remove" on these 3 secrets:
- [ ] EC2_SSH_KEY
- [ ] EC2_HOST
- [ ] EC2_USER

### Step 2: Deploy OpenCode Microservice (5 minutes)

In your terminal (on your Mac), run:

```bash
cd /Users/mac/KAI_API
chmod +x deploy-microservice.sh
./deploy-microservice.sh ~/Downloads/kai-api-server.pem
```

This uploads only the microservice to AWS and starts it.

### Step 3: Update HuggingFace Space (5 minutes)

1. Go to your HuggingFace Space
2. Go to Files → providers/opencode_provider.py
3. Edit the file and replace line 11:
   ```python
   AWS_OPENCODE_URL = "http://44.201.146.74:8000"
   ```
4. Save and commit

**OR** use this easier method:

```bash
# On your Mac, edit the file
code providers/opencode_provider.py

# Make sure line 11 has your AWS IP:
# AWS_OPENCODE_URL = "http://44.201.146.74:8000"

# Then push to GitHub
git add providers/opencode_provider.py
git commit -m "Connect OpenCode to AWS microservice"
git push origin main
```

HuggingFace will auto-deploy from GitHub.

### Step 4: Test Everything (2 minutes)

1. **Test AWS Microservice**:
   ```bash
   curl http://44.201.146.74:8000/health
   ```
   Should return: `{"status":"healthy"}`

2. **Test via HuggingFace**:
   - Go to your HF Space admin portal
   - Select OpenCode provider
   - Send a message
   - Should work!

## What Each Part Does

### AWS EC2 (t3.micro - FREE)
- **Only runs**: `opencode_microservice.py`
- **Memory**: ~500MB RAM (fits in t3.micro's 1GB)
- **Features**:
  - Disposable mode (auto-reset after 20 messages)
  - Anonymous mode (no credentials)
  - Direct terminal access to OpenCode
- **Cost**: $0/month (free tier)

### HuggingFace Space (FREE FOREVER)
- **Runs**: Everything else
- **Providers**: Copilot, Gemini, HuggingChat, etc.
- **For OpenCode**: Calls AWS microservice via HTTP
- **Cost**: $0/month (always free)

## Benefits

✅ **HuggingFace**: Reliable, working, no terminal issues
✅ **AWS**: Only handles OpenCode (lightweight, disposable)
✅ **Cost**: Both are FREE
✅ **Simple**: No complex deployment, just 2 services
✅ **Works**: Best of both worlds

## Troubleshooting

### AWS Microservice Not Responding?
```bash
# SSH to EC2 and check
ssh -i ~/Downloads/kai-api-server.pem ubuntu@44.201.146.74
tail -f /tmp/opencode-service.log
```

### HuggingFace Can't Connect to AWS?
- Check AWS security group allows port 8000
- Verify the URL in `opencode_provider.py` matches your EC2 IP

### OpenCode Not Working?
- Check if npx is installed: `which npx`
- Check OpenCode: `opencode --version`

## Architecture Diagram

```
User Request
    │
    ▼
┌─────────────────┐
│ HuggingFace     │
│ Space           │
│ (Free Forever)  │
└─────────────────┘
    │
    ├─ Copilot → Browser (local)
    ├─ Gemini → Browser (local)
    ├─ HuggingChat → Browser (local)
    └─ OpenCode → HTTP Request
                  │
                  ▼
          ┌──────────────┐
          │ AWS EC2      │
          │ t3.micro     │
          │ (Free Tier)  │
          └──────────────┘
                  │
                  ▼
          OpenCode Terminal
          (Disposable Mode)
```

## Summary

- **HuggingFace**: Handles web UI, browsers, API
- **AWS**: Handles OpenCode terminal only
- **Result**: Everything works, both are free!

**Start with Step 1 now!** Remove those GitHub secrets.

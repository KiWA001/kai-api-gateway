# GitHub Auto-Deployment Setup Guide

## Overview
Your code is now on GitHub and ready for auto-deployment to AWS EC2!

**What happens now:**
1. You push code to GitHub → GitHub Actions automatically deploys to EC2
2. No more manual SSH or file uploads needed!

## Step 1: Add GitHub Secrets (Required)

You need to add 3 secrets to your GitHub repository:

### 1. Go to GitHub Repository Settings
1. Open: https://github.com/KiWA001/kai-api-gateway
2. Click **"Settings"** tab (top right)
3. In left sidebar, click **"Secrets and variables"** → **"Actions"**
4. Click **"New repository secret"**

### 2. Add These 3 Secrets:

**Secret 1: EC2_SSH_KEY**
- Name: `EC2_SSH_KEY`
- Value: Copy and paste the ENTIRE contents of your .pem key file
- (Open the .pem file in a text editor, select all, copy, paste)

**Secret 2: EC2_HOST**
- Name: `EC2_HOST`
- Value: `44.201.146.74`

**Secret 3: EC2_USER**
- Name: `EC2_USER`
- Value: `ubuntu`

### 3. Verify Secrets
You should see these 3 secrets listed:
- EC2_SSH_KEY
- EC2_HOST  
- EC2_USER

## Step 2: Prepare Your EC2 Server

SSH into your EC2 instance and run these commands:

```bash
# SSH into your server (replace with your key path)
ssh -i ~/Downloads/YOUR_KEY.pem ubuntu@44.201.146.74

# Once inside, run these commands:

# 1. Install git
sudo apt-get update
sudo apt-get install -y git

# 2. Clone your repository
cd ~
git clone https://github.com/KiWA001/kai-api-gateway.git kai-api

# 3. Run initial setup
cd kai-api
chmod +x aws-setup.sh
./aws-setup.sh

# 4. Start the server for the first time
./start-production.sh

# Or run as daemon:
# ./run-daemon.sh start
```

## Step 3: Test Auto-Deployment

1. Make a small change to any file (e.g., edit README.md)
2. Commit and push:
   ```bash
   git add .
   git commit -m "Test auto-deployment"
   git push origin main
   ```
3. Go to GitHub → Actions tab
4. Watch the deployment happen automatically!

## What Happens During Auto-Deployment?

Every time you push to GitHub:

1. GitHub Actions triggers automatically
2. It connects to your EC2 via SSH
3. Runs `git pull` to get latest code
4. Installs any new dependencies
5. Restarts the server
6. Verifies the deployment

## Troubleshooting

### Deployment Failed?
1. Check GitHub Actions logs: GitHub → Actions tab
2. Common issues:
   - SSH key not set correctly in secrets
   - EC2 instance not running
   - Security group blocking SSH

### Server Not Starting?
SSH into EC2 and check logs:
```bash
ssh -i ~/Downloads/YOUR_KEY.pem ubuntu@44.201.146.74
tail -f /tmp/kai-api.log
```

### Permission Denied?
Make sure your .pem key has correct permissions:
```bash
chmod 600 ~/Downloads/YOUR_KEY.pem
```

## Manual Deployment (If Needed)

If auto-deployment fails, you can always deploy manually:

```bash
ssh -i ~/Downloads/YOUR_KEY.pem ubuntu@44.201.146.74
cd ~/kai-api
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
pkill -f uvicorn
nohup ./venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1 > /tmp/kai-api.log 2>&1 &
```

## Important Notes

✅ **Security:**
- Never commit your .pem key to GitHub
- The SSH key in GitHub secrets is encrypted and secure
- Only GitHub Actions can access these secrets

✅ **Best Practices:**
- Always test locally before pushing
- Check GitHub Actions logs after each push
- Keep your EC2 security group updated

✅ **Cost:**
- EC2 t3.micro is free for 12 months
- GitHub Actions has 2,000 free minutes/month
- You won't be charged for deployments

## Next Steps

1. **Add the 3 GitHub secrets** (most important!)
2. **Prepare your EC2 server** (run the commands above)
3. **Test with a small push**
4. **Start using your auto-deployment!**

Once set up, every `git push` will automatically update your live server! 🚀

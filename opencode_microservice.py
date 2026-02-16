"""
OpenCode Microservice - Tmux Screen Capture Approach
====================================================
Uses tmux to capture terminal output
"""

import asyncio
import logging
import os
import json
import random
import string
import subprocess
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opencode_microservice")

app = FastAPI(title="OpenCode Microservice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OpenCodeSession:
    def __init__(self):
        self.tmux_session = "opencode"
        self.message_count = 0
        self.max_messages = 20
        self.session_id = None
        self.is_running = False
        
    def generate_identity(self):
        return {
            "device_id": ''.join(random.choices(string.hexdigits.lower(), k=32)),
            "session_id": ''.join(random.choices(string.hexdigits.lower(), k=16)),
        }
    
    def run_tmux_cmd(self, cmd):
        """Run tmux command"""
        try:
            result = subprocess.run(
                ['tmux', '-L', self.tmux_session] + cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            logger.error(f"Tmux error: {e}")
            return "", str(e), 1
    
    async def start(self):
        """Start OpenCode in tmux session"""
        if self.is_running:
            await self.stop()
        
        identity = self.generate_identity()
        self.session_id = identity["session_id"][:8]
        
        # Cleanup
        auth_paths = [
            os.path.expanduser("~/.local/share/opencode"),
            os.path.expanduser("~/.config/opencode"),
        ]
        for path in auth_paths:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
        
        # Kill existing tmux session
        subprocess.run(['tmux', 'kill-session', '-t', self.tmux_session], capture_output=True)
        
        # Create config
        session_dir = f"/tmp/opencode_micro_{self.session_id}"
        os.makedirs(session_dir, exist_ok=True)
        
        config = {
            "$schema": "https://opencode.ai/config.json",
            "theme": "opencode",
            "provider": {
                "opencode-zen": {
                    "npm": "@ai-sdk/openai-compatible",
                    "options": {"baseURL": "https://opencode.ai/zen/v1"},
                    "models": {
                        "kimi-k2.5-free": {"name": "Kimi K2.5 Free"},
                        "minimax-m2.5-free": {"name": "MiniMax M2.5 Free"},
                        "big-pickle": {"name": "Big Pickle"},
                        "glm-4.7": {"name": "GLM 4.7"}
                    }
                }
            },
            "model": "opencode-zen/kimi-k2.5-free",
            "autoshare": False,
            "autoupdate": False,
            "anonymous": True,
        }
        
        with open(f"{session_dir}/config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        try:
            # Create tmux session with OpenCode
            env_vars = f"export OPENCODE_CONFIG={session_dir}/config.json; export OPENCODE_NO_AUTH=1;"
            cmd = f'{env_vars} npx -y opencode-ai'
            
            subprocess.Popen([
                'tmux', 'new-session', '-d', '-s', self.tmux_session,
                '-c', session_dir,
                'bash', '-c', cmd
            ])
            
            self.is_running = True
            self.message_count = 0
            
            # Wait for startup
            await asyncio.sleep(5)
            
            # Select model
            self.run_tmux_cmd(['send-keys', 'C-x'])
            await asyncio.sleep(0.5)
            self.run_tmux_cmd(['send-keys', 'm'])
            await asyncio.sleep(1)
            self.run_tmux_cmd(['send-keys', 'Enter'])
            await asyncio.sleep(2)
            
            logger.info(f"✅ OpenCode started in tmux - Session: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start OpenCode: {e}")
            return False
    
    def capture_screen(self):
        """Capture tmux pane content"""
        stdout, _, code = self.run_tmux_cmd(['capture-pane', '-p', '-S', '-100'])
        if code == 0:
            return stdout
        return ""
    
    async def chat(self, message: str) -> str:
        """Send message and capture response"""
        if not self.is_running:
            success = await self.start()
            if not success:
                return "Failed to start OpenCode"
        
        try:
            # Get current screen before message
            before_screen = self.capture_screen()
            before_lines = set(before_screen.split('\n'))
            
            # Send message
            self.run_tmux_cmd(['send-keys', message])
            self.run_tmux_cmd(['send-keys', 'Enter'])
            
            # Wait for AI response
            await asyncio.sleep(15)
            
            # Get screen after response
            after_screen = self.capture_screen()
            after_lines = after_screen.split('\n')
            
            # Find new lines (the response)
            response_lines = []
            for line in after_lines:
                line = line.strip()
                # Skip empty lines, prompts, and old lines
                if line and line not in before_lines and not line.startswith(('>', '$', '┌', '│', '└', '╭', '╰')):
                    # Skip the user's question
                    if message not in line:
                        response_lines.append(line)
            
            self.message_count += 1
            
            # Auto-reset
            if self.message_count >= self.max_messages:
                logger.info("🔄 Auto-reset triggered")
                await self.stop()
                await self.start()
            
            if response_lines:
                # Return last few lines (most recent response)
                return '\n'.join(response_lines[-15:])
            else:
                # Return full screen if we can't parse
                return after_screen[-2000:]  # Last 2000 chars
                
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"Error: {str(e)}"
    
    async def stop(self):
        """Stop tmux session"""
        subprocess.run(['tmux', 'kill-session', '-t', self.tmux_session], capture_output=True)
        self.is_running = False
        self.message_count = 0
        logger.info("🛑 OpenCode stopped")

# Global session
session = OpenCodeSession()

class ChatRequest(BaseModel):
    message: str
    model: str = "kimi-k2.5-free"

@app.get("/")
def root():
    return {"status": "OpenCode Microservice Running"}

@app.get("/health")
def health():
    return {"status": "healthy", "session_active": session.is_running}

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    try:
        response = await session.chat(req.message)
        return {
            "response": response,
            "session_id": session.session_id or "",
            "message_count": session.message_count,
            "max_messages": session.max_messages
        }
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def status_endpoint():
    return {
        "is_running": session.is_running,
        "message_count": session.message_count,
        "max_messages": session.max_messages,
        "session_id": session.session_id
    }

@app.post("/reset")
async def reset_endpoint():
    await session.stop()
    success = await session.start()
    return {"status": "reset_complete" if success else "reset_failed"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

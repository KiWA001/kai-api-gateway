"""
OpenCode Microservice - Proper Terminal Capture
===============================================
Uses pexpect to properly interact with OpenCode TUI
"""

import asyncio
import logging
import os
import json
import random
import string
import pexpect
import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil

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
        self.process: Optional[pexpect.spawn] = None
        self.message_count = 0
        self.max_messages = 20
        self.session_id = None
        self.is_running = False
        self.output_buffer = []
        
    def generate_identity(self):
        return {
            "device_id": ''.join(random.choices(string.hexdigits.lower(), k=32)),
            "session_id": ''.join(random.choices(string.hexdigits.lower(), k=16)),
        }
    
    async def start(self):
        """Start fresh OpenCode session with proper terminal"""
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
            # Start OpenCode with pexpect (proper PTY)
            env = os.environ.copy()
            env['OPENCODE_CONFIG'] = f"{session_dir}/config.json"
            env['OPENCODE_NO_AUTH'] = '1'
            env['TERM'] = 'xterm-256color'
            
            self.process = pexpect.spawn(
                'npx -y opencode-ai',
                env=env,
                timeout=30,
                maxread=50000,
                encoding='utf-8',
                codec_errors='ignore'
            )
            
            # Wait for startup
            await asyncio.sleep(4)
            
            # Wait for TUI to load
            try:
                self.process.expect(['OpenCode', 'Ask anything', 'What can I help'], timeout=10)
            except:
                pass  # Continue anyway
            
            # Select model
            self.process.sendcontrol('x')
            await asyncio.sleep(0.5)
            self.process.send('m')
            await asyncio.sleep(1)
            self.process.send('\n')
            await asyncio.sleep(2)
            
            self.is_running = True
            self.message_count = 0
            self.output_buffer = []
            
            logger.info(f"✅ OpenCode started - Session: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start OpenCode: {e}")
            return False
    
    async def chat(self, message: str) -> str:
        """Send message and capture response"""
        if not self.is_running:
            success = await self.start()
            if not success:
                return "Failed to start OpenCode"
        
        try:
            # Clear any pending output first
            try:
                while self.process.readline_nonblocking(size=1000, timeout=0.1):
                    pass
            except:
                pass
            
            # Send message
            self.process.sendline(message)
            
            # Wait for response generation (AI needs time)
            await asyncio.sleep(12)  # Increased wait time
            
            # Read all output with multiple attempts
            output_parts = []
            for _ in range(5):  # Try multiple times
                try:
                    # Read available output
                    available = self.process.read_nonblocking(size=10000, timeout=2)
                    if available:
                        output_parts.append(available)
                except pexpect.TIMEOUT:
                    break
                except:
                    break
                await asyncio.sleep(1)
            
            output = "".join(output_parts)
            
            # Clean up output
            import re
            # Remove ANSI escape codes
            clean_output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
            # Remove other control characters
            clean_output = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', clean_output)
            # Normalize whitespace
            clean_output = re.sub(r'\r\n', '\n', clean_output)
            clean_output = re.sub(r'\n+', '\n', clean_output)
            clean_output = clean_output.strip()
            
            self.message_count += 1
            
            # Auto-reset
            if self.message_count >= self.max_messages:
                logger.info("🔄 Auto-reset triggered")
                await self.stop()
                await self.start()
            
            # Return last few lines (the response)
            lines = clean_output.strip().split('\n')
            # Filter out empty lines and prompts
            response_lines = [l for l in lines if l.strip() and not l.startswith(('>', '$', '┌', '│', '└'))]
            
            if response_lines:
                return '\n'.join(response_lines[-10:])  # Return last 10 lines
            else:
                return "Response received (check terminal for full output)"
                
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"Error: {str(e)}"
    
    async def stop(self):
        if self.process:
            try:
                self.process.sendline('/exit')
                await asyncio.sleep(1)
            except:
                pass
            
            if self.process.isalive():
                self.process.terminate()
                await asyncio.sleep(2)
                if self.process.isalive():
                    self.process.kill()
            
            self.process = None
        
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

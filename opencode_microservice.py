"""
OpenCode Microservice - Minimal AWS Service
==========================================
Just handles OpenCode terminal with disposable mode
"""

import asyncio
import logging
import subprocess
import os
import json
import random
import string
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import shutil

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opencode_microservice")

app = FastAPI(title="OpenCode Microservice")

# Allow CORS from HuggingFace
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your HF space
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
class OpenCodeSession:
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.message_count = 0
        self.max_messages = 20
        self.session_id = None
        self.is_running = False
        
    def generate_identity(self):
        return {
            "device_id": ''.join(random.choices(string.hexdigits.lower(), k=32)),
            "session_id": ''.join(random.choices(string.hexdigits.lower(), k=16)),
        }
    
    async def start(self):
        """Start fresh OpenCode session"""
        if self.is_running:
            await self.stop()
        
        identity = self.generate_identity()
        self.session_id = identity["session_id"][:8]
        
        # Cleanup any existing auth
        auth_paths = [
            os.path.expanduser("~/.local/share/opencode"),
            os.path.expanduser("~/.config/opencode"),
            "/tmp/opencode_session_*",
        ]
        for path_pattern in auth_paths:
            try:
                import glob
                for p in glob.glob(path_pattern):
                    if os.path.exists(p):
                        shutil.rmtree(p, ignore_errors=True)
            except:
                pass
        
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
            "autoupdate": True,
            "anonymous": True,
            "deviceId": identity["device_id"],
            "sessionId": identity["session_id"]
        }
        
        with open(f"{session_dir}/config.json", 'w') as f:
            json.dump(config, f, indent=2)
        
        # Start OpenCode
        env = os.environ.copy()
        env['OPENCODE_CONFIG'] = f"{session_dir}/config.json"
        env['OPENCODE_NO_AUTH'] = '1'
        env['TERM_SESSION_ID'] = self.session_id
        
        try:
            self.process = subprocess.Popen(
                ['npx', '-y', 'opencode-ai'],
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self.is_running = True
            self.message_count = 0
            
            # Wait for startup
            await asyncio.sleep(3)
            
            # Select model (Ctrl+X then M then Enter)
            await self.send_key('ctrl+x')
            await asyncio.sleep(0.5)
            await self.send_input('m')
            await asyncio.sleep(1)
            await self.send_key('return')
            await asyncio.sleep(1)
            
            logger.info(f"✅ OpenCode started - Session: {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start OpenCode: {e}")
            return False
    
    async def send_input(self, text: str):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(text + '\n')
                self.process.stdin.flush()
                return True
            except:
                return False
        return False
    
    async def send_key(self, key: str):
        if self.process and self.process.poll() is None:
            try:
                key_map = {
                    'return': '\n',
                    'enter': '\n',
                    'ctrl+x': '\x18',
                    'ctrl+c': '\x03',
                    'tab': '\t',
                }
                char = key_map.get(key.lower(), key)
                self.process.stdin.write(char)
                self.process.stdin.flush()
                return True
            except:
                return False
        return False
    
    async def chat(self, message: str) -> str:
        """Send message and get response"""
        if not self.is_running:
            await self.start()
        
        # Start new chat
        await self.send_key('ctrl+x')
        await asyncio.sleep(0.3)
        await self.send_input('n')
        await asyncio.sleep(0.5)
        
        # Send message
        await self.send_input(message)
        
        # Wait for response
        await asyncio.sleep(3)
        
        # Read output
        output = ""
        try:
            import select
            while True:
                if self.process.stdout in select.select([self.process.stdout], [], [], 0.5)[0]:
                    line = self.process.stdout.readline()
                    if line:
                        output += line
                    else:
                        break
                else:
                    break
        except:
            pass
        
        self.message_count += 1
        
        # Auto-reset after 20 messages
        if self.message_count >= self.max_messages:
            logger.info("🔄 Auto-reset triggered")
            await self.stop()
            await self.start()
        
        return output or "Message sent successfully"
    
    async def stop(self):
        if self.process:
            try:
                self.process.stdin.write('/exit\n')
                self.process.stdin.flush()
                await asyncio.sleep(1)
            except:
                pass
            
            if self.process.poll() is None:
                self.process.terminate()
                await asyncio.sleep(2)
                if self.process.poll() is None:
                    self.process.kill()
            
            self.process = None
        
        self.is_running = False
        self.message_count = 0
        
        # Cleanup
        try:
            import glob
            for d in glob.glob("/tmp/opencode_micro_*"):
                shutil.rmtree(d, ignore_errors=True)
        except:
            pass
        
        logger.info("🛑 OpenCode stopped")

# Global session
session = OpenCodeSession()

# API Models
class ChatRequest(BaseModel):
    message: str
    model: str = "kimi-k2.5-free"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    message_count: int
    max_messages: int

class StatusResponse(BaseModel):
    is_running: bool
    message_count: int
    max_messages: int
    session_id: Optional[str]

@app.get("/")
def root():
    return {"status": "OpenCode Microservice Running", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "healthy", "session_active": session.is_running}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        response = await session.chat(req.message)
        return ChatResponse(
            response=response,
            session_id=session.session_id or "",
            message_count=session.message_count,
            max_messages=session.max_messages
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status", response_model=StatusResponse)
async def status_endpoint():
    return StatusResponse(
        is_running=session.is_running,
        message_count=session.message_count,
        max_messages=session.max_messages,
        session_id=session.session_id
    )

@app.post("/reset")
async def reset_endpoint():
    """Manually reset session"""
    await session.stop()
    success = await session.start()
    return {"status": "reset_complete" if success else "reset_failed"}

@app.post("/start")
async def start_endpoint():
    """Start OpenCode session"""
    if session.is_running:
        return {"status": "already_running"}
    
    success = await session.start()
    return {"status": "started" if success else "failed"}

@app.post("/stop")
async def stop_endpoint():
    """Stop OpenCode session"""
    await session.stop()
    return {"status": "stopped"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

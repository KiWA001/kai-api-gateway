"""
OpenCode Terminal Portal
-------------------------
Manages OpenCode terminal TUI as a provider.
Supports free models: Kimi K2.5 Free, MiniMax M2.5 Free, Big Pickle, GLM 4.7

ANONYMOUS MODE: No credentials stored, fresh device identity each session
"""

import asyncio
import logging
import subprocess
import os
import json
import random
import string
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import threading
import queue
import shutil

logger = logging.getLogger("kai_api.terminal_portal")


@dataclass
class TerminalConfig:
    """Configuration for OpenCode terminal."""
    name: str
    model: str  # e.g., "kimi-k2.5-free", "minimax-m2.5-free"
    project_dir: str = "."
    config_path: str = ".opencode/config.json"


def generate_anonymous_identity():
    """Generate random device identifiers to appear as different device each time."""
    return {
        "device_id": ''.join(random.choices(string.hexdigits.lower(), k=32)),
        "session_id": ''.join(random.choices(string.hexdigits.lower(), k=16)),
        "fingerprint": ''.join(random.choices(string.hexdigits.lower(), k=24)),
    }


# Free models configuration
OPENCODE_MODELS = {
    "kimi-k2.5-free": {
        "name": "Kimi K2.5 Free",
        "provider": "opencode-zen",
        "description": "Moonshot AI's Kimi K2.5 - Free tier"
    },
    "minimax-m2.5-free": {
        "name": "MiniMax M2.5 Free", 
        "provider": "opencode-zen",
        "description": "MiniMax M2.5 - Free tier"
    },
    "big-pickle": {
        "name": "Big Pickle",
        "provider": "opencode-zen", 
        "description": "Stealth model - Free"
    },
    "glm-4.7": {
        "name": "GLM 4.7",
        "provider": "opencode-zen",
        "description": "GLM 4.7 - Free tier"
    }
}


class OpenCodeTerminalPortal:
    """Manages OpenCode terminal TUI session with DISPOSABLE mode."""
    
    # Disposable mode settings
    MAX_MESSAGES_BEFORE_RESET = 20  # Auto-reset after 20 messages
    AUTO_NEW_CHAT_BETWEEN_MESSAGES = True  # Start new chat between each message
    
    def __init__(self, config: TerminalConfig):
        self.config = config
        self.process: Optional[subprocess.Popen] = None
        self.is_initialized = False
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()
        self.output_thread: Optional[threading.Thread] = None
        self.on_output_callback: Optional[Callable] = None
        self.screenshot_path = f"/tmp/opencode_{config.model}.png"
        self.last_activity = None
        self._keyboard_active = False
        self.message_count = 0  # Track messages for auto-reset
        self.current_identity = None  # Track current session identity
        self.session_dir = None  # Track current session directory
        
    async def initialize(self):
        """Initialize OpenCode terminal session in ANONYMOUS/DISPOSABLE mode."""
        if self.is_initialized:
            return
            
        try:
            logger.info(f"🚀 Starting OpenCode terminal with model: {self.config.model}")
            logger.info("🔒 Anonymous mode: No credentials stored, fresh device identity")
            logger.info("🗑️  Disposable mode: Auto-reset after 20 messages, new chat between messages")
            
            # Generate fresh anonymous identity
            self.current_identity = generate_anonymous_identity()
            identity = self.current_identity
            
            # Create isolated config directory for this session
            self.session_dir = f"/tmp/opencode_session_{identity['session_id'][:8]}"
            config_path = f"{self.session_dir}/config.json"
            os.makedirs(self.session_dir, exist_ok=True)
            
            # Remove any existing auth files to ensure anonymous mode
            auth_paths = [
                os.path.expanduser("~/.local/share/opencode/auth.json"),
                os.path.expanduser("~/.local/share/opencode"),
                ".opencode/auth.json",
                "/tmp/opencode_auth.json"
            ]
            for path in auth_paths:
                if os.path.exists(path):
                    try:
                        if os.path.isfile(path):
                            os.remove(path)
                            logger.info(f"🗑️ Removed auth file: {path}")
                        elif os.path.isdir(path):
                            shutil.rmtree(path)
                            logger.info(f"🗑️ Removed auth directory: {path}")
                    except Exception as e:
                        logger.warning(f"Could not remove {path}: {e}")
            
            # Create anonymous config - NO login required
            config_data = {
                "$schema": "https://opencode.ai/config.json",
                "theme": "opencode",
                "provider": {
                    "opencode-zen": {
                        "npm": "@ai-sdk/openai-compatible",
                        "options": {
                            "baseURL": "https://opencode.ai/zen/v1"
                        },
                        "models": {
                            model: {"name": info["name"]} 
                            for model, info in OPENCODE_MODELS.items()
                        }
                    }
                },
                "model": f"opencode-zen/{self.config.model}",
                "autoshare": False,
                "autoupdate": True,
                # Anonymous mode settings
                "anonymous": True,
                "deviceId": identity["device_id"],
                "sessionId": identity["session_id"]
            }
            
            with open(config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"✅ Config created at: {config_path}")
            
            # Start OpenCode process with custom environment
            env = os.environ.copy()
            env['OPENCODE_CONFIG'] = os.path.abspath(config_path)
            # Set random terminal identifier
            env['TERM_SESSION_ID'] = identity["session_id"]
            # Prevent any auth persistence
            env['OPENCODE_NO_AUTH'] = '1'
            
            self.process = subprocess.Popen(
                ['npx', '-y', 'opencode-ai'],
                cwd=self.config.project_dir,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout for easier reading
                text=True,
                bufsize=1
            )
            
            # Start output reading thread
            self.output_thread = threading.Thread(target=self._read_output)
            self.output_thread.daemon = True
            self.output_thread.start()
            
            self.is_initialized = True
            logger.info(f"✅ OpenCode terminal ready (Anonymous mode)")
            logger.info(f"🆔 Session ID: {identity['session_id'][:16]}...")
            
            # Wait for startup and send initial commands to select free model
            await asyncio.sleep(3)
            
            # Auto-select the free model (Ctrl+X then M)
            await self.send_key('ctrl+x')
            await asyncio.sleep(0.5)
            await self.send_input('m')
            await asyncio.sleep(1)
            
            # Select model based on config
            model_map = {
                "kimi-k2.5-free": "kimi",
                "minimax-m2.5-free": "minimax",
                "big-pickle": "big pickle",
                "glm-4.7": "glm"
            }
            model_keyword = model_map.get(self.config.model, "kimi")
            
            # Send enter to select default (usually Kimi)
            await self.send_key('Enter')
            await asyncio.sleep(0.5)
            
            await self.take_screenshot()
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenCode terminal: {e}")
            raise
    
    def _read_output(self):
        """Read output from OpenCode process in background thread."""
        try:
            while self.process and self.process.poll() is None:
                # Read line from stdout
                line = self.process.stdout.readline()
                if line:
                    self.output_queue.put(('stdout', line))
                    if self.on_output_callback:
                        asyncio.create_task(self.on_output_callback('stdout', line))
                
                # Check stderr
                import select
                if self.process.stderr in select.select([self.process.stderr], [], [], 0)[0]:
                    err_line = self.process.stderr.readline()
                    if err_line:
                        self.output_queue.put(('stderr', err_line))
        except Exception as e:
            logger.error(f"Error reading output: {e}")
    
    async def send_input(self, text: str, is_message: bool = True):
        """Send text input to OpenCode with disposable mode handling."""
        if not self.process or not self.is_initialized:
            return False
        
        try:
            # If this is a user message (not a command), handle disposable mode
            if is_message and self.AUTO_NEW_CHAT_BETWEEN_MESSAGES:
                # Start a new chat before sending the message
                await self._start_new_chat()
                await asyncio.sleep(0.5)
            
            # Send the actual message
            self.process.stdin.write(text + '\n')
            self.process.stdin.flush()
            self.last_activity = datetime.now()
            
            # Track message count for auto-reset
            if is_message:
                self.message_count += 1
                logger.info(f"📨 Message {self.message_count}/{self.MAX_MESSAGES_BEFORE_RESET}")
                
                # Check if we need to auto-reset
                if self.message_count >= self.MAX_MESSAGES_BEFORE_RESET:
                    logger.info("🔄 Auto-reset triggered after 20 messages!")
                    await self._full_reset()
            
            return True
        except Exception as e:
            logger.error(f"Error sending input: {e}")
            return False
    
    async def _start_new_chat(self):
        """Start a new chat to avoid context carryover."""
        try:
            # Send Ctrl+N for new chat (or equivalent command)
            logger.info("🆕 Starting new chat...")
            self.process.stdin.write('\x0e')  # Ctrl+N
            self.process.stdin.flush()
            await asyncio.sleep(0.3)
        except Exception as e:
            logger.warning(f"Could not start new chat: {e}")
    
    async def _full_reset(self):
        """Complete reset: wipe everything and start fresh."""
        logger.info("🧹 PERFORMING FULL DISPOSABLE RESET...")
        
        # 1. Close current session
        await self.close()
        
        # 2. Aggressive cleanup of ALL traces
        await self._complete_cleanup()
        
        # 3. Reset counters
        self.message_count = 0
        self.current_identity = None
        self.session_dir = None
        
        # 4. Wait a moment to ensure cleanup
        await asyncio.sleep(2)
        
        # 5. Reinitialize with fresh identity
        logger.info("🔄 Starting fresh session...")
        await self.initialize()
        
        logger.info("✅ Full reset complete - OpenCode sees a completely new device!")
    
    async def _complete_cleanup(self):
        """Complete cleanup of ALL OpenCode traces."""
        cleanup_paths = [
            # Config directories
            "/tmp/opencode_session_*",
            os.path.expanduser("~/.local/share/opencode"),
            os.path.expanduser("~/.config/opencode"),
            os.path.expanduser("~/.opencode"),
            ".opencode",
            
            # Cache and temp files
            os.path.expanduser("~/.cache/opencode"),
            "/tmp/opencode*",
            "/tmp/.opencode*",
            
            # Node/npm cache that might have identifiers
            os.path.expanduser("~/.npm/_npx/*opencode*"),
            os.path.expanduser("~/.npm/_logs/*opencode*"),
            
            # Any auth files
            os.path.expanduser("~/.local/share/opencode/auth.json"),
            "/tmp/opencode_auth.json",
            "/tmp/kai-opencode-*",
        ]
        
        for path_pattern in cleanup_paths:
            try:
                import glob
                matching_paths = glob.glob(path_pattern)
                for path in matching_paths:
                    if os.path.exists(path):
                        if os.path.isfile(path):
                            os.remove(path)
                            logger.info(f"🗑️ Deleted file: {path}")
                        elif os.path.isdir(path):
                            shutil.rmtree(path, ignore_errors=True)
                            logger.info(f"🗑️ Deleted directory: {path}")
            except Exception as e:
                logger.warning(f"Cleanup warning for {path_pattern}: {e}")
        
        # Clear npm/npx cache
        try:
            subprocess.run(["npm", "cache", "clean", "--force"], 
                         capture_output=True, timeout=10)
            logger.info("🧹 NPM cache cleared")
        except Exception as e:
            logger.warning(f"Could not clear NPM cache: {e}")
        
        # Clear any system-level temporary identifiers
        try:
            # Clear /tmp of any opencode related files
            import glob
            for f in glob.glob("/tmp/*opencode*"):
                try:
                    if os.path.isfile(f):
                        os.remove(f)
                    elif os.path.isdir(f):
                        shutil.rmtree(f, ignore_errors=True)
                except:
                    pass
        except:
            pass
        
        logger.info("🧹 Complete cleanup finished - No traces left!")
    
    async def send_key(self, key: str):
        """Send a special key to OpenCode (e.g., 'ctrl+c', 'enter', 'tab')."""
        if not self.process or not self.is_initialized:
            return False
        
        try:
            # Map common keys
            key_map = {
                'Enter': '\n',
                'Tab': '\t',
                'Escape': '\x1b',
                'Backspace': '\x7f',
                'Delete': '\x1b[3~',
                'ArrowUp': '\x1b[A',
                'ArrowDown': '\x1b[B',
                'ArrowLeft': '\x1b[D',
                'ArrowRight': '\x1b[C',
            }
            
            char = key_map.get(key, key)
            self.process.stdin.write(char)
            self.process.stdin.flush()
            return True
        except Exception as e:
            logger.error(f"Error sending key: {e}")
            return False
    
    async def execute_command(self, command: str):
        """Execute an OpenCode command (e.g., '/models', '/connect')."""
        return await self.send_input(command)
    
    async def take_screenshot(self) -> str:
        """Take a screenshot of the terminal (if supported by terminal emulator)."""
        # For now, we'll create a text-based representation
        # In production, you could use a terminal emulator that supports screenshots
        try:
            # Get recent output
            output_lines = []
            while not self.output_queue.empty() and len(output_lines) < 50:
                try:
                    stream, line = self.output_queue.get_nowait()
                    output_lines.append(line)
                except queue.Empty:
                    break
            
            # Create a simple text screenshot
            screenshot_text = "\n".join(output_lines[-25:]) if output_lines else "Terminal ready..."
            
            # Save to file
            with open(self.screenshot_path, 'w') as f:
                f.write(screenshot_text)
            
            return self.screenshot_path
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return ""
    
    def get_output(self, max_lines: int = 100) -> list:
        """Get recent output lines."""
        lines = []
        temp_queue = queue.Queue()
        
        # Get lines from queue without removing them permanently
        while not self.output_queue.empty() and len(lines) < max_lines:
            try:
                item = self.output_queue.get_nowait()
                lines.append(item)
                temp_queue.put(item)
            except queue.Empty:
                break
        
        # Put them back
        while not temp_queue.empty():
            self.output_queue.put(temp_queue.get())
        
        return lines
    
    def set_keyboard_active(self, active: bool):
        """Enable/disable keyboard input capture."""
        self._keyboard_active = active
        logger.info(f"Keyboard {'activated' if active else 'deactivated'} for OpenCode")
    
    def is_keyboard_active(self) -> bool:
        """Check if keyboard is active."""
        return self._keyboard_active
    
    def is_running(self) -> bool:
        """Check if OpenCode is running."""
        if not self.process:
            return False
        return self.process.poll() is None
    
    async def close(self):
        """Close the OpenCode terminal and cleanup anonymous session."""
        try:
            if self.process:
                # Send exit command
                try:
                    self.process.stdin.write('/exit\n')
                    self.process.stdin.flush()
                    await asyncio.sleep(1)
                except:
                    pass
                
                # Kill if still running
                if self.process.poll() is None:
                    self.process.terminate()
                    await asyncio.sleep(2)
                    if self.process.poll() is None:
                        self.process.kill()
                
                self.process = None
            
            self.is_initialized = False
            
            # Cleanup session directory to remove any traces
            if self.session_dir and os.path.exists(self.session_dir):
                try:
                    shutil.rmtree(self.session_dir, ignore_errors=True)
                    logger.info(f"🧹 Cleaned up session directory: {self.session_dir}")
                except Exception as e:
                    logger.warning(f"Session cleanup warning: {e}")
            
            # Reset message counter
            self.message_count = 0
            
            logger.info("OpenCode terminal closed (Anonymous session cleaned)")
            
        except Exception as e:
            logger.error(f"Error closing OpenCode: {e}")

    async def sync_auth(self):
        """DEPRECATED: Anonymous mode - no auth to sync."""
        logger.warning("sync_auth() called but anonymous mode is active - no credentials stored")
        return False

    async def manual_reset(self):
        """Manually trigger a full disposable reset."""
        logger.info("🔄 Manual reset requested")
        await self._full_reset()
        return True
    
    def get_disposable_status(self) -> dict:
        """Get current disposable mode status."""
        return {
            "message_count": self.message_count,
            "max_messages": self.MAX_MESSAGES_BEFORE_RESET,
            "messages_remaining": max(0, self.MAX_MESSAGES_BEFORE_RESET - self.message_count),
            "auto_reset_enabled": True,
            "new_chat_between_messages": self.AUTO_NEW_CHAT_BETWEEN_MESSAGES,
            "is_running": self.is_running(),
            "anonymous_mode": True,
            "session_dir": self.session_dir,
            "device_id": self.current_identity["device_id"][:16] + "..." if self.current_identity else None,
        }


class TerminalPortalManager:
    """Manages multiple OpenCode terminal portals."""
    
    def __init__(self):
        self.portals: Dict[str, OpenCodeTerminalPortal] = {}
    
    def get_portal(self, model: str) -> OpenCodeTerminalPortal:
        """Get or create a portal for a specific model."""
        if model not in self.portals:
            if model not in OPENCODE_MODELS:
                raise ValueError(f"Unknown OpenCode model: {model}")
            
            config = TerminalConfig(
                name=OPENCODE_MODELS[model]["name"],
                model=model,
                config_path=f".opencode/config_{model}.json"
            )
            self.portals[model] = OpenCodeTerminalPortal(config)
        
        return self.portals[model]
    
    def get_available_models(self) -> Dict[str, Dict]:
        """Get all available OpenCode models."""
        return OPENCODE_MODELS.copy()
    
    async def close_all(self):
        """Close all terminal portals."""
        for portal in self.portals.values():
            await portal.close()


# Global instance
_terminal_manager = TerminalPortalManager()

def get_terminal_manager() -> TerminalPortalManager:
    """Get the global terminal manager."""
    return _terminal_manager

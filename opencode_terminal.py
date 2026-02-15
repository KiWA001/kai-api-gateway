"""
OpenCode Terminal Portal
-------------------------
Manages OpenCode terminal TUI as a provider.
Supports free models: Kimi K2.5 Free, MiniMax M2.5 Free, Big Pickle, GLM 4.7
"""

import asyncio
import logging
import subprocess
import os
import json
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from datetime import datetime
import threading
import queue

logger = logging.getLogger("kai_api.terminal_portal")


@dataclass
class TerminalConfig:
    """Configuration for OpenCode terminal."""
    name: str
    model: str  # e.g., "kimi-k2.5-free", "minimax-m2.5-free"
    project_dir: str = "."
    config_path: str = ".opencode/config.json"


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
    """Manages OpenCode terminal TUI session."""
    
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
        
    async def initialize(self):
        """Initialize OpenCode terminal session."""
        if self.is_initialized:
            return
            
        try:
            logger.info(f"🚀 Starting OpenCode terminal with model: {self.config.model}")
            
            # Ensure config directory exists
            os.makedirs(".opencode", exist_ok=True)
            
            # Create config file for this model
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
                "autoupdate": True
            }
            
            with open(self.config.config_path, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Start OpenCode process
            env = os.environ.copy()
            env['OPENCODE_CONFIG'] = os.path.abspath(self.config.config_path)
            
            self.process = subprocess.Popen(
                ['npx', '-y', 'opencode-ai'],
                cwd=self.config.project_dir,
                env=env,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # Start output reading thread
            self.output_thread = threading.Thread(target=self._read_output)
            self.output_thread.daemon = True
            self.output_thread.start()
            
            self.is_initialized = True
            logger.info(f"✅ OpenCode terminal ready with {self.config.model}")
            
            await asyncio.sleep(2)  # Give it time to start
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
    
    async def send_input(self, text: str):
        """Send text input to OpenCode."""
        if not self.process or not self.is_initialized:
            return False
        
        try:
            self.process.stdin.write(text + '\n')
            self.process.stdin.flush()
            self.last_activity = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error sending input: {e}")
            return False
    
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
        """Close the OpenCode terminal."""
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
            logger.info("OpenCode terminal closed")
            
        except Exception as e:
            logger.error(f"Error closing OpenCode: {e}")


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

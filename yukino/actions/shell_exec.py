"""
Shell command execution with allowlist security.

Executes shell commands that are on the allowlist, with timeout
protection and output capture.
"""

import subprocess
import logging
from typing import Dict, Any, List, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class ShellExec:
    """
    Shell command executor with allowlist security.
    
    Features:
    - Allowlist-based command filtering
    - 30-second timeout protection
    - Output capture (stdout/stderr)
    - Non-reversible logging to undo stack
    """
    
    def __init__(self, undo_stack, allowlist_file: Path):
        """
        Initialize shell executor.
        
        Args:
            undo_stack: UndoStack instance for logging
            allowlist_file: Path to command allowlist file
        """
        self._undo_stack = undo_stack
        self._allowlist_file = Path(allowlist_file)
        self._allowlist: Set[str] = set()
        self._timeout = 30  # seconds
        
        self._load_allowlist()
        logger.info(f"ShellExec initialized ({len(self._allowlist)} allowed commands)")
    
    def _load_allowlist(self) -> None:
        """Load command allowlist from file."""
        if not self._allowlist_file.exists():
            logger.warning(f"Allowlist file not found: {self._allowlist_file}")
            logger.info("Using default allowlist")
            self._allowlist = self._get_default_allowlist()
            return
        
        try:
            with open(self._allowlist_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith('#'):
                        # Handle comma-separated commands on same line
                        commands = [cmd.strip() for cmd in line.split(',')]
                        self._allowlist.update(commands)
            
            logger.info(f"Loaded allowlist from {self._allowlist_file}")
            logger.debug(f"Allowed commands: {sorted(self._allowlist)}")
        
        except Exception as e:
            logger.error(f"Failed to load allowlist: {e}", exc_info=True)
            logger.info("Using default allowlist")
            self._allowlist = self._get_default_allowlist()
    
    def _get_default_allowlist(self) -> Set[str]:
        """Get default command allowlist."""
        return {
            # File operations
            "ls", "dir", "cat", "type", "echo", "mkdir",
            "pwd", "cd", "clear", "cls",
            
            # Development
            "python", "python3", "pip", "pip3",
            "git", "code", "notepad",
            
            # System info
            "whoami", "date", "time", "hostname",
            "ipconfig", "ifconfig", "ping",
            
            # Package managers
            "npm", "node", "cargo", "rustc",
        }
    
    def _is_command_allowed(self, command: str) -> bool:
        """
        Check if command is on allowlist.
        
        Args:
            command: Full command string
        
        Returns:
            True if command is allowed, False otherwise
        """
        # Tokenize command and get first token (the actual command)
        tokens = command.strip().split()
        
        if not tokens:
            return False
        
        # Get the base command (first token)
        base_command = tokens[0].lower()
        
        # Handle paths (e.g., "./script.py" or "C:\path\python.exe")
        if '\\' in base_command or '/' in base_command:
            # Extract just the command name
            base_command = Path(base_command).name.lower()
        
        # Remove .exe extension on Windows
        if base_command.endswith('.exe'):
            base_command = base_command[:-4]
        
        return base_command in self._allowlist
    
    def execute(self, command: str) -> Dict[str, Any]:
        """
        Execute a shell command if it's on the allowlist.
        
        Args:
            command: Command string to execute
        
        Returns:
            Result dict with success, message, output, and optional error
        """
        if not command or not command.strip():
            return {
                "success": False,
                "message": "...you need to specify a command."
            }
        
        command = command.strip()
        
        # Check if command is allowed
        if not self._is_command_allowed(command):
            logger.warning(f"Blocked command not on allowlist: {command}")
            return {
                "success": False,
                "message": "No. I won't run that command. It's not on the allowlist."
            }
        
        logger.info(f"Executing command: {command}")
        
        try:
            # Log to undo stack (non-reversible)
            self._undo_stack.push(
                action_type="shell",
                snapshot={"command": command},
                description=f"Executed: {command[:50]}"
            )
            
            # Execute command with timeout
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self._timeout
            )
            
            # Check return code
            if result.returncode == 0:
                output = result.stdout.strip()
                logger.info(f"Command succeeded: {command}")
                
                if output:
                    return {
                        "success": True,
                        "message": f"Done. Output: {output[:200]}",
                        "output": output
                    }
                else:
                    return {
                        "success": True,
                        "message": "Done. The command completed successfully.",
                        "output": ""
                    }
            else:
                # Command failed
                error = result.stderr.strip()
                logger.warning(f"Command failed: {command} (exit {result.returncode})")
                
                return {
                    "success": False,
                    "message": f"That command failed. {error[:200] if error else 'Check the syntax.'}",
                    "error": error,
                    "exit_code": result.returncode
                }
        
        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {command}")
            return {
                "success": False,
                "message": f"That command took too long. It timed out after {self._timeout} seconds.",
                "error": "Timeout"
            }
        
        except FileNotFoundError:
            logger.error(f"Command not found: {command}")
            return {
                "success": False,
                "message": "...that command doesn't exist on this system.",
                "error": "Command not found"
            }
        
        except PermissionError:
            logger.error(f"Permission denied: {command}")
            return {
                "success": False,
                "message": "...I don't have permission to run that command.",
                "error": "Permission denied"
            }
        
        except Exception as e:
            logger.error(f"Error executing command: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong executing that command.",
                "error": str(e)
            }
    
    def get_allowlist(self) -> List[str]:
        """
        Get list of allowed commands.
        
        Returns:
            Sorted list of allowed command names
        """
        return sorted(self._allowlist)
    
    def add_to_allowlist(self, command: str) -> bool:
        """
        Add a command to the allowlist (runtime only, not persisted).
        
        Args:
            command: Command to add
        
        Returns:
            True if added, False if already present
        """
        command = command.strip().lower()
        if command in self._allowlist:
            return False
        
        self._allowlist.add(command)
        logger.info(f"Added to allowlist: {command}")
        return True


def create_shell_exec(undo_stack, allowlist_file: Path) -> ShellExec:
    """
    Factory function to create ShellExec instance.
    
    Args:
        undo_stack: UndoStack instance
        allowlist_file: Path to command allowlist file
    
    Returns:
        Initialized ShellExec instance
    """
    return ShellExec(undo_stack, allowlist_file)

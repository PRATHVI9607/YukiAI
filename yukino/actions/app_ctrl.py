"""
Application control module.

Opens and closes applications, lists running applications.
"""

import subprocess
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Try importing psutil for better process management
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - using basic process management")


class AppCtrl:
    """
    Application control for opening and closing apps.
    
    Features:
    - Open applications by common name
    - Close running applications
    - List running applications
    - Cross-platform command mappings
    """
    
    # Common application mappings
    APP_MAPPINGS = {
        # Browsers
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "brave": "brave.exe",
        "opera": "opera.exe",
        
        # Development
        "vscode": "code",
        "code": "code",
        "visual studio code": "code",
        "pycharm": "pycharm64.exe",
        "sublime": "sublime_text.exe",
        "atom": "atom.exe",
        "notepad++": "notepad++.exe",
        
        # System
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "terminal": "wt.exe",
        
        # Communication
        "discord": "Discord.exe",
        "slack": "slack.exe",
        "teams": "Teams.exe",
        "zoom": "Zoom.exe",
        "skype": "Skype.exe",
        
        # Media
        "spotify": "Spotify.exe",
        "vlc": "vlc.exe",
        "media player": "wmplayer.exe",
        
        # Productivity
        "word": "WINWORD.EXE",
        "excel": "EXCEL.EXE",
        "powerpoint": "POWERPNT.EXE",
        "outlook": "OUTLOOK.EXE",
    }
    
    def __init__(self):
        """Initialize application controller."""
        logger.info("AppCtrl initialized")
    
    def _normalize_app_name(self, name: str) -> str:
        """
        Normalize application name to lowercase for matching.
        
        Args:
            name: Application name
        
        Returns:
            Normalized name
        """
        return name.strip().lower()
    
    def _get_app_command(self, app_name: str) -> Optional[str]:
        """
        Get executable command for application name.
        
        Args:
            app_name: Application name
        
        Returns:
            Executable command or None if not found
        """
        normalized = self._normalize_app_name(app_name)
        return self.APP_MAPPINGS.get(normalized)
    
    def open_app(self, name: str) -> Dict[str, Any]:
        """
        Open an application by name.
        
        Args:
            name: Application name (e.g., "chrome", "notepad")
        
        Returns:
            Result dict with success status and message
        """
        if not name:
            return {
                "success": False,
                "message": "...you need to specify an application name."
            }
        
        # Get command for app
        command = self._get_app_command(name)
        
        if not command:
            # Try using the name directly
            logger.info(f"App not in mappings, trying direct: {name}")
            command = name
        
        try:
            # Open application
            if command == "code":
                # VS Code has special handling
                subprocess.Popen([command], shell=True)
            elif command.endswith(".exe"):
                subprocess.Popen([command], shell=True)
            else:
                subprocess.Popen(command, shell=True)
            
            logger.info(f"Opened application: {name} ({command})")
            return {
                "success": True,
                "message": f"Done. Opening {name}."
            }
        
        except FileNotFoundError:
            logger.warning(f"Application not found: {name}")
            return {
                "success": False,
                "message": f"...I couldn't find {name}. Make sure it's installed."
            }
        
        except PermissionError:
            logger.error(f"Permission denied opening: {name}")
            return {
                "success": False,
                "message": f"...I don't have permission to open {name}."
            }
        
        except Exception as e:
            logger.error(f"Error opening application: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"...something went wrong opening {name}."
            }
    
    def close_app(self, name: str) -> Dict[str, Any]:
        """
        Close a running application by name.
        
        Args:
            name: Application name (e.g., "chrome", "notepad")
        
        Returns:
            Result dict with success status and message
        """
        if not name:
            return {
                "success": False,
                "message": "...you need to specify an application name."
            }
        
        # Get command/process name for app
        command = self._get_app_command(name)
        
        if not command:
            # Try using the name directly
            command = name if name.endswith(".exe") else f"{name}.exe"
        
        try:
            if PSUTIL_AVAILABLE:
                # Use psutil for better process management
                killed_any = False
                process_name = command.lower()
                
                for proc in psutil.process_iter(['name']):
                    try:
                        if proc.info['name'].lower() == process_name:
                            proc.terminate()
                            killed_any = True
                            logger.info(f"Terminated process: {proc.info['name']} (PID {proc.pid})")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                if killed_any:
                    return {
                        "success": True,
                        "message": f"Done. Closed {name}."
                    }
                else:
                    return {
                        "success": False,
                        "message": f"...{name} isn't running."
                    }
            else:
                # Fallback to taskkill
                result = subprocess.run(
                    ["taskkill", "/F", "/IM", command],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    logger.info(f"Closed application: {name}")
                    return {
                        "success": True,
                        "message": f"Done. Closed {name}."
                    }
                else:
                    if "not found" in result.stderr.lower():
                        return {
                            "success": False,
                            "message": f"...{name} isn't running."
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"...I couldn't close {name}."
                        }
        
        except PermissionError:
            logger.error(f"Permission denied closing: {name}")
            return {
                "success": False,
                "message": f"...I don't have permission to close {name}."
            }
        
        except Exception as e:
            logger.error(f"Error closing application: {e}", exc_info=True)
            return {
                "success": False,
                "message": f"...something went wrong closing {name}."
            }
    
    def list_running(self) -> Dict[str, Any]:
        """
        List currently running applications.
        
        Returns:
            Result dict with list of running applications
        """
        try:
            if PSUTIL_AVAILABLE:
                # Use psutil for detailed process info
                processes = set()
                
                for proc in psutil.process_iter(['name']):
                    try:
                        name = proc.info['name']
                        # Filter out system processes
                        if name and not name.startswith('svchost'):
                            processes.add(name)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                app_list = sorted(processes)
                logger.debug(f"Found {len(app_list)} running processes")
                
                return {
                    "success": True,
                    "applications": app_list,
                    "message": f"There are {len(app_list)} applications running."
                }
            else:
                # Fallback to tasklist
                result = subprocess.run(
                    ["tasklist"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    # Parse tasklist output
                    lines = result.stdout.split('\n')
                    processes = set()
                    
                    for line in lines[3:]:  # Skip header lines
                        if line.strip():
                            parts = line.split()
                            if parts:
                                processes.add(parts[0])
                    
                    app_list = sorted(processes)
                    
                    return {
                        "success": True,
                        "applications": app_list,
                        "message": f"There are {len(app_list)} applications running."
                    }
                else:
                    return {
                        "success": False,
                        "message": "...I couldn't list running applications."
                    }
        
        except Exception as e:
            logger.error(f"Error listing applications: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong listing applications."
            }


def create_app_ctrl() -> AppCtrl:
    """
    Factory function to create AppCtrl instance.
    
    Returns:
        Initialized AppCtrl instance
    """
    return AppCtrl()

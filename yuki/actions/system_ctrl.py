"""
System control module for Windows.

Controls volume, brightness, WiFi, and Bluetooth with undo support.
"""

import subprocess
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try importing Windows-specific libraries
try:
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from comtypes import CLSCTX_ALL
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False
    logger.warning("pycaw not available - volume control disabled")

try:
    import screen_brightness_control as sbc
    SBC_AVAILABLE = True
except ImportError:
    SBC_AVAILABLE = False
    logger.warning("screen-brightness-control not available - brightness control disabled")


class SystemCtrl:
    """
    System controls for Windows.
    
    Features:
    - Volume control (pycaw)
    - Brightness control (screen-brightness-control)
    - WiFi toggle (netsh)
    - Bluetooth toggle (Windows commands)
    - Undo support for all changes
    """
    
    def __init__(self, undo_stack):
        """
        Initialize system controls.
        
        Args:
            undo_stack: UndoStack instance for reversible operations
        """
        self._undo_stack = undo_stack
        
        # Volume control setup
        self._volume_interface: Optional[Any] = None
        if PYCAW_AVAILABLE:
            try:
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(
                    IAudioEndpointVolume._iid_, CLSCTX_ALL, None
                )
                self._volume_interface = interface.QueryInterface(IAudioEndpointVolume)
                logger.info("Volume control initialized")
            except Exception as e:
                logger.error(f"Failed to initialize volume control: {e}")
        
        logger.info("SystemCtrl initialized")
    
    def set_volume(self, percent: int) -> Dict[str, Any]:
        """
        Set system volume level.
        
        Args:
            percent: Volume level 0-100
        
        Returns:
            Result dict with success status and message
        """
        if not PYCAW_AVAILABLE or not self._volume_interface:
            return {
                "success": False,
                "message": "...volume control isn't available on this system."
            }
        
        if not 0 <= percent <= 100:
            return {
                "success": False,
                "message": "Volume must be between 0 and 100 percent."
            }
        
        try:
            # Get current volume for undo
            current_volume = int(
                self._volume_interface.GetMasterVolumeLevelScalar() * 100
            )
            
            # Push to undo stack
            self._undo_stack.push(
                action_type="volume_change",
                snapshot={"previous": current_volume},
                description=f"Set volume to {percent}% (was {current_volume}%)"
            )
            
            # Set new volume
            self._volume_interface.SetMasterVolumeLevelScalar(
                percent / 100.0, None
            )
            
            logger.info(f"Set volume: {current_volume}% -> {percent}%")
            return {
                "success": True,
                "message": f"Done. Volume set to {percent} percent."
            }
        
        except Exception as e:
            logger.error(f"Error setting volume: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong changing the volume."
            }
    
    def get_volume(self) -> Dict[str, Any]:
        """
        Get current system volume level.
        
        Returns:
            Result dict with volume level
        """
        if not PYCAW_AVAILABLE or not self._volume_interface:
            return {
                "success": False,
                "message": "...volume control isn't available on this system."
            }
        
        try:
            volume = int(
                self._volume_interface.GetMasterVolumeLevelScalar() * 100
            )
            
            logger.debug(f"Current volume: {volume}%")
            return {
                "success": True,
                "volume": volume,
                "message": f"The volume is at {volume} percent."
            }
        
        except Exception as e:
            logger.error(f"Error getting volume: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...I couldn't check the volume."
            }
    
    def set_brightness(self, percent: int) -> Dict[str, Any]:
        """
        Set display brightness level.
        
        Args:
            percent: Brightness level 0-100
        
        Returns:
            Result dict with success status and message
        """
        if not SBC_AVAILABLE:
            return {
                "success": False,
                "message": "...brightness control isn't available on this system."
            }
        
        if not 0 <= percent <= 100:
            return {
                "success": False,
                "message": "Brightness must be between 0 and 100 percent."
            }
        
        try:
            # Get current brightness for undo
            current_brightness = sbc.get_brightness()[0]
            
            # Push to undo stack
            self._undo_stack.push(
                action_type="brightness_change",
                snapshot={"previous": current_brightness},
                description=f"Set brightness to {percent}% (was {current_brightness}%)"
            )
            
            # Set new brightness
            sbc.set_brightness(percent)
            
            logger.info(f"Set brightness: {current_brightness}% -> {percent}%")
            return {
                "success": True,
                "message": f"Done. Brightness set to {percent} percent."
            }
        
        except Exception as e:
            logger.error(f"Error setting brightness: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong changing the brightness."
            }
    
    def get_brightness(self) -> Dict[str, Any]:
        """
        Get current display brightness level.
        
        Returns:
            Result dict with brightness level
        """
        if not SBC_AVAILABLE:
            return {
                "success": False,
                "message": "...brightness control isn't available on this system."
            }
        
        try:
            brightness = sbc.get_brightness()[0]
            
            logger.debug(f"Current brightness: {brightness}%")
            return {
                "success": True,
                "brightness": brightness,
                "message": f"The brightness is at {brightness} percent."
            }
        
        except Exception as e:
            logger.error(f"Error getting brightness: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...I couldn't check the brightness."
            }
    
    def toggle_wifi(self) -> Dict[str, Any]:
        """
        Toggle WiFi on/off using Windows netsh command.
        
        Returns:
            Result dict with success status and message
        """
        try:
            # Check current WiFi status
            result = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # Look for WiFi interfaces
            lines = result.stdout.lower()
            wifi_enabled = "wi-fi" in lines and "connected" in lines
            
            if wifi_enabled:
                # Disable WiFi
                cmd = ["netsh", "interface", "set", "interface", "Wi-Fi", "disabled"]
                action = "disabled"
            else:
                # Enable WiFi
                cmd = ["netsh", "interface", "set", "interface", "Wi-Fi", "enabled"]
                action = "enabled"
            
            # Execute toggle
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"WiFi {action}")
                return {
                    "success": True,
                    "message": f"Done. WiFi {action}."
                }
            else:
                logger.error(f"Failed to toggle WiFi: {result.stderr}")
                return {
                    "success": False,
                    "message": "...I couldn't toggle WiFi. Check if you have a WiFi adapter."
                }
        
        except FileNotFoundError:
            return {
                "success": False,
                "message": "...WiFi control isn't available on this system."
            }
        except PermissionError:
            return {
                "success": False,
                "message": "...I don't have permission to control WiFi. Run as administrator."
            }
        except Exception as e:
            logger.error(f"Error toggling WiFi: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong toggling WiFi."
            }
    
    def toggle_bluetooth(self) -> Dict[str, Any]:
        """
        Toggle Bluetooth on/off using Windows commands.
        
        Returns:
            Result dict with success status and message
        """
        try:
            # Try using PowerShell to toggle Bluetooth
            # This is more complex and may require administrator privileges
            
            # Check if Bluetooth service is available
            result = subprocess.run(
                ["powershell", "-Command", "Get-Service", "bthserv"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "message": "...Bluetooth isn't available on this system."
                }
            
            # Note: Toggling Bluetooth programmatically on Windows is complex
            # and often requires admin privileges or third-party tools
            # This is a simplified implementation
            
            logger.warning("Bluetooth toggle not fully implemented")
            return {
                "success": False,
                "message": "...Bluetooth control isn't fully implemented yet. Use Windows settings."
            }
        
        except Exception as e:
            logger.error(f"Error toggling Bluetooth: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong with Bluetooth control."
            }


def create_system_ctrl(undo_stack) -> SystemCtrl:
    """
    Factory function to create SystemCtrl instance.
    
    Args:
        undo_stack: UndoStack instance
    
    Returns:
        Initialized SystemCtrl instance
    """
    return SystemCtrl(undo_stack)

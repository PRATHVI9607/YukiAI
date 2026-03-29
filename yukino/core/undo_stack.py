"""
Thread-safe undo stack for reversible actions.

Supports snapshots for file operations, system settings, and shell commands.
Maximum depth of 20 actions with automatic trimming.
"""

import os
import shutil
import threading
import logging
from typing import Dict, Any, Optional, List, Callable
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class UndoAction:
    """Represents a single undoable action."""
    action_type: str
    snapshot: Dict[str, Any]
    description: str
    timestamp: datetime
    rollback_func: Optional[Callable] = None


class UndoStack:
    """
    Thread-safe undo stack for reversible actions.
    
    Supports various action types with automatic rollback:
    - file_create: Remove created file
    - file_delete: Restore deleted file from snapshot
    - folder_create: Remove created folder
    - folder_delete: Restore deleted folder tree
    - file_move: Move file back to original location
    - volume_change: Restore previous volume level
    - brightness_change: Restore previous brightness level
    - shell: Non-reversible, log only
    """
    
    def __init__(self, max_depth: int = 20):
        """
        Initialize undo stack.
        
        Args:
            max_depth: Maximum number of actions to keep in stack
        """
        self._stack: List[UndoAction] = []
        self._max_depth = max_depth
        self._lock = threading.Lock()
        logger.info(f"UndoStack initialized with max_depth={max_depth}")
    
    def push(
        self,
        action_type: str,
        snapshot: Dict[str, Any],
        description: str,
        rollback_func: Optional[Callable] = None
    ) -> None:
        """
        Push a new action onto the undo stack.
        
        Args:
            action_type: Type of action (file_create, file_delete, etc.)
            snapshot: Data needed to undo the action
            description: Human-readable description of the action
            rollback_func: Optional custom rollback function
        """
        with self._lock:
            action = UndoAction(
                action_type=action_type,
                snapshot=snapshot,
                description=description,
                timestamp=datetime.now(),
                rollback_func=rollback_func
            )
            
            self._stack.append(action)
            
            # Trim stack if it exceeds max depth
            if len(self._stack) > self._max_depth:
                removed = self._stack.pop(0)
                logger.debug(f"Trimmed oldest action from stack: {removed.description}")
            
            logger.info(f"Pushed action to undo stack: {action_type} - {description}")
            logger.debug(f"Stack depth: {len(self._stack)}/{self._max_depth}")
    
    def pop_and_undo(self) -> Dict[str, Any]:
        """
        Pop the most recent action and execute its rollback.
        
        Returns:
            Dict with keys:
                - success (bool): Whether undo was successful
                - message (str): Yukino's spoken response
                - error (str, optional): Error message if failed
        """
        with self._lock:
            if not self._stack:
                logger.warning("Undo called but stack is empty")
                return {
                    "success": False,
                    "message": "...there's nothing to undo. You haven't done anything yet."
                }
            
            action = self._stack.pop()
            logger.info(f"Undoing action: {action.action_type} - {action.description}")
        
        # Execute rollback outside of lock to avoid deadlock
        try:
            if action.rollback_func:
                # Custom rollback function
                action.rollback_func(action.snapshot)
            else:
                # Built-in rollback based on action type
                self._execute_rollback(action)
            
            logger.info(f"Successfully undid action: {action.description}")
            return {
                "success": True,
                "message": f"Done. I've undone that action. {action.description}"
            }
            
        except Exception as e:
            logger.error(f"Failed to undo action: {e}", exc_info=True)
            # Put action back on stack since undo failed
            with self._lock:
                self._stack.append(action)
            
            return {
                "success": False,
                "message": "...I made an error trying to undo that. It's still as it was.",
                "error": str(e)
            }
    
    def _execute_rollback(self, action: UndoAction) -> None:
        """Execute built-in rollback based on action type."""
        action_type = action.action_type
        snapshot = action.snapshot
        
        if action_type == "file_create":
            self._undo_file_create(snapshot)
        elif action_type == "file_delete":
            self._undo_file_delete(snapshot)
        elif action_type == "folder_create":
            self._undo_folder_create(snapshot)
        elif action_type == "folder_delete":
            self._undo_folder_delete(snapshot)
        elif action_type == "file_move":
            self._undo_file_move(snapshot)
        elif action_type == "volume_change":
            self._undo_volume_change(snapshot)
        elif action_type == "brightness_change":
            self._undo_brightness_change(snapshot)
        elif action_type == "shell":
            self._undo_shell(snapshot)
        else:
            raise ValueError(f"Unknown action type: {action_type}")
    
    def _undo_file_create(self, snapshot: Dict[str, Any]) -> None:
        """Undo file creation by deleting the file."""
        path = Path(snapshot["path"])
        if path.exists() and path.is_file():
            os.remove(path)
            logger.debug(f"Removed created file: {path}")
        else:
            logger.warning(f"File to remove doesn't exist: {path}")
    
    def _undo_file_delete(self, snapshot: Dict[str, Any]) -> None:
        """Undo file deletion by restoring from snapshot."""
        path = Path(snapshot["path"])
        content = snapshot["content"]
        
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Restore file content
        if isinstance(content, bytes):
            with open(path, "wb") as f:
                f.write(content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        
        logger.debug(f"Restored deleted file: {path}")
    
    def _undo_folder_create(self, snapshot: Dict[str, Any]) -> None:
        """Undo folder creation by removing the folder."""
        path = Path(snapshot["path"])
        if path.exists() and path.is_dir():
            shutil.rmtree(path)
            logger.debug(f"Removed created folder: {path}")
        else:
            logger.warning(f"Folder to remove doesn't exist: {path}")
    
    def _undo_folder_delete(self, snapshot: Dict[str, Any]) -> None:
        """Undo folder deletion by recreating the folder tree."""
        path = Path(snapshot["path"])
        tree = snapshot["tree"]
        
        def recreate_tree(base_path: Path, tree_dict: Dict[str, Any]) -> None:
            """Recursively recreate folder structure."""
            for name, content in tree_dict.items():
                item_path = base_path / name
                
                if isinstance(content, dict):
                    # It's a directory
                    item_path.mkdir(parents=True, exist_ok=True)
                    recreate_tree(item_path, content)
                else:
                    # It's a file
                    if isinstance(content, bytes):
                        with open(item_path, "wb") as f:
                            f.write(content)
                    else:
                        with open(item_path, "w", encoding="utf-8") as f:
                            f.write(content)
        
        path.mkdir(parents=True, exist_ok=True)
        recreate_tree(path, tree)
        logger.debug(f"Restored deleted folder: {path}")
    
    def _undo_file_move(self, snapshot: Dict[str, Any]) -> None:
        """Undo file move by moving back to original location."""
        src = Path(snapshot["src"])
        dst = Path(snapshot["dst"])
        
        if dst.exists():
            shutil.move(str(dst), str(src))
            logger.debug(f"Moved file back: {dst} -> {src}")
        else:
            logger.warning(f"File to move back doesn't exist: {dst}")
    
    def _undo_volume_change(self, snapshot: Dict[str, Any]) -> None:
        """Undo volume change by restoring previous level."""
        previous_volume = snapshot["previous"]
        
        try:
            # Import here to avoid Windows-specific import errors
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            from comtypes import CLSCTX_ALL
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(
                IAudioEndpointVolume._iid_, CLSCTX_ALL, None
            )
            volume = interface.QueryInterface(IAudioEndpointVolume)
            volume.SetMasterVolumeLevelScalar(previous_volume / 100.0, None)
            
            logger.debug(f"Restored volume to {previous_volume}%")
        except Exception as e:
            logger.error(f"Failed to restore volume: {e}")
            raise
    
    def _undo_brightness_change(self, snapshot: Dict[str, Any]) -> None:
        """Undo brightness change by restoring previous level."""
        previous_brightness = snapshot["previous"]
        
        try:
            import screen_brightness_control as sbc
            sbc.set_brightness(previous_brightness)
            logger.debug(f"Restored brightness to {previous_brightness}%")
        except Exception as e:
            logger.error(f"Failed to restore brightness: {e}")
            raise
    
    def _undo_shell(self, snapshot: Dict[str, Any]) -> None:
        """Shell commands are non-reversible, just log."""
        command = snapshot["command"]
        logger.warning(f"Cannot undo shell command: {command}")
        # This will be caught and return appropriate message
        raise ValueError("Shell commands cannot be undone")
    
    def clear(self) -> None:
        """Clear the entire undo stack."""
        with self._lock:
            count = len(self._stack)
            self._stack.clear()
            logger.info(f"Cleared undo stack ({count} actions removed)")
    
    def get_depth(self) -> int:
        """Get current stack depth."""
        with self._lock:
            return len(self._stack)
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Get undo history without modifying stack.
        
        Returns:
            List of action descriptions, most recent first
        """
        with self._lock:
            return [
                {
                    "type": action.action_type,
                    "description": action.description,
                    "timestamp": action.timestamp.isoformat()
                }
                for action in reversed(self._stack)
            ]

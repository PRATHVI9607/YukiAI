"""
File operations module with security checks and undo support.

Handles file and folder creation, deletion, and moving with
strict security boundaries (home directory only).
"""

import os
import shutil
import logging
from typing import Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class FileOps:
    """
    File and folder operations with security and undo support.
    
    Features:
    - Create/delete files and folders
    - Move files between locations
    - Security: Operations restricted to user home directory
    - Undo stack integration for all destructive operations
    """
    
    def __init__(self, undo_stack):
        """
        Initialize file operations handler.
        
        Args:
            undo_stack: UndoStack instance for reversible operations
        """
        self._undo_stack = undo_stack
        self._home_dir = Path(os.path.expanduser("~"))
        logger.info(f"FileOps initialized (home dir: {self._home_dir})")
    
    def _is_safe_path(self, path: str) -> bool:
        """
        Check if path is within user home directory.
        
        Args:
            path: Path to check
        
        Returns:
            True if path is safe, False otherwise
        """
        try:
            resolved_path = Path(path).resolve()
            return resolved_path.is_relative_to(self._home_dir)
        except (ValueError, RuntimeError):
            return False
    
    def create_file(self, path: str, content: str = "") -> Dict[str, Any]:
        """
        Create a new file with optional content.
        
        Args:
            path: File path to create
            content: File content (default: empty string)
        
        Returns:
            Result dict with success status and message
        """
        if not path:
            return {
                "success": False,
                "message": "...you need to specify a path."
            }
        
        path_obj = Path(path)
        
        # Security check
        if not self._is_safe_path(path):
            logger.warning(f"Blocked file creation outside home: {path}")
            return {
                "success": False,
                "message": "No. I won't access files outside your home directory."
            }
        
        # Check if file already exists
        if path_obj.exists():
            logger.warning(f"File already exists: {path}")
            return {
                "success": False,
                "message": "That file already exists. Choose a different name."
            }
        
        try:
            # Create parent directories if needed
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Push to undo stack before creating
            self._undo_stack.push(
                action_type="file_create",
                snapshot={"path": str(path_obj)},
                description=f"Created file: {path_obj.name}"
            )
            
            # Create file
            with open(path_obj, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Created file: {path}")
            return {
                "success": True,
                "message": f"Done. I created {path_obj.name}."
            }
        
        except PermissionError:
            logger.error(f"Permission denied creating file: {path}")
            return {
                "success": False,
                "message": "...I don't have permission to create that file."
            }
        except Exception as e:
            logger.error(f"Error creating file: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong. I couldn't create that file."
            }
    
    def create_folder(self, path: str) -> Dict[str, Any]:
        """
        Create a new folder.
        
        Args:
            path: Folder path to create
        
        Returns:
            Result dict with success status and message
        """
        if not path:
            return {
                "success": False,
                "message": "...you need to specify a path."
            }
        
        path_obj = Path(path)
        
        # Security check
        if not self._is_safe_path(path):
            logger.warning(f"Blocked folder creation outside home: {path}")
            return {
                "success": False,
                "message": "No. I won't access folders outside your home directory."
            }
        
        # Check if folder already exists
        if path_obj.exists():
            logger.warning(f"Folder already exists: {path}")
            return {
                "success": False,
                "message": "That folder already exists."
            }
        
        try:
            # Push to undo stack before creating
            self._undo_stack.push(
                action_type="folder_create",
                snapshot={"path": str(path_obj)},
                description=f"Created folder: {path_obj.name}"
            )
            
            # Create folder
            path_obj.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Created folder: {path}")
            return {
                "success": True,
                "message": f"Done. I created the folder {path_obj.name}."
            }
        
        except PermissionError:
            logger.error(f"Permission denied creating folder: {path}")
            return {
                "success": False,
                "message": "...I don't have permission to create that folder."
            }
        except Exception as e:
            logger.error(f"Error creating folder: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong. I couldn't create that folder."
            }
    
    def delete_file(self, path: str) -> Dict[str, Any]:
        """
        Delete a file.
        
        Args:
            path: File path to delete
        
        Returns:
            Result dict with success status and message
        """
        if not path:
            return {
                "success": False,
                "message": "...you need to specify a path."
            }
        
        path_obj = Path(path)
        
        # Security check
        if not self._is_safe_path(path):
            logger.warning(f"Blocked file deletion outside home: {path}")
            return {
                "success": False,
                "message": "No. I won't access files outside your home directory."
            }
        
        # Check if file exists
        if not path_obj.exists():
            logger.warning(f"File doesn't exist: {path}")
            return {
                "success": False,
                "message": "...that file doesn't exist. Check the path."
            }
        
        if not path_obj.is_file():
            logger.warning(f"Path is not a file: {path}")
            return {
                "success": False,
                "message": "That's not a file. Use folder delete instead."
            }
        
        try:
            # Read file content for undo
            with open(path_obj, 'rb') as f:
                content = f.read()
            
            # Push to undo stack before deleting
            self._undo_stack.push(
                action_type="file_delete",
                snapshot={
                    "path": str(path_obj),
                    "content": content
                },
                description=f"Deleted file: {path_obj.name}"
            )
            
            # Delete file
            os.remove(path_obj)
            
            logger.info(f"Deleted file: {path}")
            return {
                "success": True,
                "message": f"Done. I deleted {path_obj.name}."
            }
        
        except PermissionError:
            logger.error(f"Permission denied deleting file: {path}")
            return {
                "success": False,
                "message": "...I don't have permission to delete that file."
            }
        except Exception as e:
            logger.error(f"Error deleting file: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong. I couldn't delete that file."
            }
    
    def delete_folder(self, path: str) -> Dict[str, Any]:
        """
        Delete a folder and all its contents.
        
        Args:
            path: Folder path to delete
        
        Returns:
            Result dict with success status and message
        """
        if not path:
            return {
                "success": False,
                "message": "...you need to specify a path."
            }
        
        path_obj = Path(path)
        
        # Security check
        if not self._is_safe_path(path):
            logger.warning(f"Blocked folder deletion outside home: {path}")
            return {
                "success": False,
                "message": "No. I won't access folders outside your home directory."
            }
        
        # Check if folder exists
        if not path_obj.exists():
            logger.warning(f"Folder doesn't exist: {path}")
            return {
                "success": False,
                "message": "...that folder doesn't exist. Check the path."
            }
        
        if not path_obj.is_dir():
            logger.warning(f"Path is not a folder: {path}")
            return {
                "success": False,
                "message": "That's not a folder. Use file delete instead."
            }
        
        try:
            # Build folder tree for undo
            def build_tree(dir_path: Path) -> Dict[str, Any]:
                """Recursively build folder structure."""
                tree = {}
                for item in dir_path.iterdir():
                    if item.is_file():
                        with open(item, 'rb') as f:
                            tree[item.name] = f.read()
                    elif item.is_dir():
                        tree[item.name] = build_tree(item)
                return tree
            
            tree = build_tree(path_obj)
            
            # Push to undo stack before deleting
            self._undo_stack.push(
                action_type="folder_delete",
                snapshot={
                    "path": str(path_obj),
                    "tree": tree
                },
                description=f"Deleted folder: {path_obj.name}"
            )
            
            # Delete folder
            shutil.rmtree(path_obj)
            
            logger.info(f"Deleted folder: {path}")
            return {
                "success": True,
                "message": f"Done. I deleted the folder {path_obj.name}."
            }
        
        except PermissionError:
            logger.error(f"Permission denied deleting folder: {path}")
            return {
                "success": False,
                "message": "...I don't have permission to delete that folder."
            }
        except Exception as e:
            logger.error(f"Error deleting folder: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong. I couldn't delete that folder."
            }
    
    def move(self, src: str, dst: str) -> Dict[str, Any]:
        """
        Move a file or folder to a new location.
        
        Args:
            src: Source path
            dst: Destination path
        
        Returns:
            Result dict with success status and message
        """
        if not src or not dst:
            return {
                "success": False,
                "message": "...you need to specify both source and destination."
            }
        
        src_obj = Path(src)
        dst_obj = Path(dst)
        
        # Security checks
        if not self._is_safe_path(src):
            logger.warning(f"Blocked move from outside home: {src}")
            return {
                "success": False,
                "message": "No. I won't access the source outside your home directory."
            }
        
        if not self._is_safe_path(dst):
            logger.warning(f"Blocked move to outside home: {dst}")
            return {
                "success": False,
                "message": "No. I won't move files outside your home directory."
            }
        
        # Check if source exists
        if not src_obj.exists():
            logger.warning(f"Source doesn't exist: {src}")
            return {
                "success": False,
                "message": "...the source doesn't exist. Check the path."
            }
        
        # Check if destination already exists
        if dst_obj.exists():
            logger.warning(f"Destination already exists: {dst}")
            return {
                "success": False,
                "message": "The destination already exists. Choose a different location."
            }
        
        try:
            # Push to undo stack before moving
            self._undo_stack.push(
                action_type="file_move",
                snapshot={
                    "src": str(src_obj),
                    "dst": str(dst_obj)
                },
                description=f"Moved {src_obj.name} to {dst_obj.parent.name}"
            )
            
            # Create destination parent directory if needed
            dst_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Move file/folder
            shutil.move(str(src_obj), str(dst_obj))
            
            logger.info(f"Moved {src} to {dst}")
            return {
                "success": True,
                "message": f"Done. I moved {src_obj.name} to {dst_obj.parent.name}."
            }
        
        except PermissionError:
            logger.error(f"Permission denied moving: {src} -> {dst}")
            return {
                "success": False,
                "message": "...I don't have permission to move that."
            }
        except Exception as e:
            logger.error(f"Error moving: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong. I couldn't move that."
            }


def create_file_ops(undo_stack) -> FileOps:
    """
    Factory function to create FileOps instance.
    
    Args:
        undo_stack: UndoStack instance
    
    Returns:
        Initialized FileOps instance
    """
    return FileOps(undo_stack)

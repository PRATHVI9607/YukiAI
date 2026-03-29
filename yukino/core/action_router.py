"""
Action router - dispatches intents to action modules.

Parses LLM JSON intents and routes them to appropriate action modules
for execution. Handles confirmation flow and response formatting.
"""

import logging
from typing import Dict, Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger(__name__)


class ActionRouter:
    """
    Routes parsed intents to appropriate action modules.
    
    Handles:
    - Intent validation
    - Action module dispatch
    - Confirmation flow
    - Response formatting
    - Error handling
    """
    
    def __init__(self, undo_stack, action_modules: Optional[Dict[str, Any]] = None):
        """
        Initialize action router.
        
        Args:
            undo_stack: UndoStack instance for reversible actions
            action_modules: Dict of action module instances (optional, for later phases)
        """
        self._undo_stack = undo_stack
        self._action_modules = action_modules or {}
        
        # Map intent types to handler methods
        self._intent_handlers: Dict[str, Callable] = {
            "file_create": self._handle_file_create,
            "file_delete": self._handle_file_delete,
            "file_move": self._handle_file_move,
            "folder_create": self._handle_folder_create,
            "folder_delete": self._handle_folder_delete,
            "shell": self._handle_shell,
            "volume_set": self._handle_volume_set,
            "volume_get": self._handle_volume_get,
            "wifi_toggle": self._handle_wifi_toggle,
            "bluetooth_toggle": self._handle_bluetooth_toggle,
            "brightness_set": self._handle_brightness_set,
            "app_open": self._handle_app_open,
            "app_close": self._handle_app_close,
            "browser_open": self._handle_browser_open,
            "undo": self._handle_undo,
            "chat": self._handle_chat,
        }
        
        logger.info("Action router initialized")
    
    def register_action_module(self, name: str, module: Any) -> None:
        """
        Register an action module for use by router.
        
        Args:
            name: Module name (e.g., "file_ops", "system_ctrl")
            module: Module instance
        """
        self._action_modules[name] = module
        logger.debug(f"Registered action module: {name}")
    
    def route_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route parsed intent to appropriate handler.
        
        Args:
            intent: Parsed intent dict with keys:
                - intent: Intent type string
                - params: Dict of parameters
                - confirmation_message: Yukino's confirmation question (optional)
                - spoken_response: Yukino's response after action (optional)
        
        Returns:
            Result dict with keys:
                - success: bool
                - message: str (Yukino's spoken response)
                - needs_confirmation: bool (optional)
                - confirmation_message: str (optional)
                - error: str (optional)
        """
        intent_type = intent.get("intent")
        
        if not intent_type:
            logger.error("Intent missing 'intent' field")
            return {
                "success": False,
                "message": "...I don't understand what you want me to do.",
                "error": "Missing intent type"
            }
        
        # Get handler for this intent type
        handler = self._intent_handlers.get(intent_type)
        
        if not handler:
            logger.warning(f"Unknown intent type: {intent_type}")
            return {
                "success": False,
                "message": f"...I don't know how to do that yet.",
                "error": f"Unknown intent type: {intent_type}"
            }
        
        # Check if confirmation is needed
        if "confirmation_message" in intent and intent["confirmation_message"]:
            return {
                "success": True,
                "needs_confirmation": True,
                "confirmation_message": intent["confirmation_message"],
                "intent": intent  # Store intent for later execution
            }
        
        # Execute handler
        try:
            logger.info(f"Routing intent: {intent_type}")
            result = handler(intent)
            
            # Use spoken_response from intent if provided
            if "spoken_response" in intent and result.get("success"):
                result["message"] = intent["spoken_response"]
            
            return result
            
        except Exception as e:
            logger.error(f"Error handling intent {intent_type}: {e}", exc_info=True)
            return {
                "success": False,
                "message": "...something went wrong. I couldn't complete that.",
                "error": str(e)
            }
    
    def execute_confirmed_intent(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an intent that has been confirmed by user.
        
        Args:
            intent: Intent dict (same format as route_intent)
        
        Returns:
            Result dict (same format as route_intent)
        """
        # Remove confirmation message to prevent re-asking
        intent_copy = intent.copy()
        intent_copy.pop("confirmation_message", None)
        
        return self.route_intent(intent_copy)
    
    # Intent handlers (stubs for now, full implementation in Phase 3)
    
    def _handle_file_create(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file creation intent."""
        if "file_ops" not in self._action_modules:
            return self._module_not_ready("file operations")
        
        params = intent.get("params", {})
        file_ops = self._action_modules["file_ops"]
        
        return file_ops.create_file(
            path=params.get("path"),
            content=params.get("content", "")
        )
    
    def _handle_file_delete(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file deletion intent."""
        if "file_ops" not in self._action_modules:
            return self._module_not_ready("file operations")
        
        params = intent.get("params", {})
        file_ops = self._action_modules["file_ops"]
        
        return file_ops.delete_file(path=params.get("path"))
    
    def _handle_file_move(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file move intent."""
        if "file_ops" not in self._action_modules:
            return self._module_not_ready("file operations")
        
        params = intent.get("params", {})
        file_ops = self._action_modules["file_ops"]
        
        return file_ops.move(
            src=params.get("src"),
            dst=params.get("dst")
        )
    
    def _handle_folder_create(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle folder creation intent."""
        if "file_ops" not in self._action_modules:
            return self._module_not_ready("file operations")
        
        params = intent.get("params", {})
        file_ops = self._action_modules["file_ops"]
        
        return file_ops.create_folder(path=params.get("path"))
    
    def _handle_folder_delete(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle folder deletion intent."""
        if "file_ops" not in self._action_modules:
            return self._module_not_ready("file operations")
        
        params = intent.get("params", {})
        file_ops = self._action_modules["file_ops"]
        
        return file_ops.delete_folder(path=params.get("path"))
    
    def _handle_shell(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle shell command intent."""
        if "shell_exec" not in self._action_modules:
            return self._module_not_ready("shell commands")
        
        params = intent.get("params", {})
        shell_exec = self._action_modules["shell_exec"]
        
        return shell_exec.execute(command=params.get("command"))
    
    def _handle_volume_set(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle volume set intent."""
        if "system_ctrl" not in self._action_modules:
            return self._module_not_ready("system controls")
        
        params = intent.get("params", {})
        system_ctrl = self._action_modules["system_ctrl"]
        
        return system_ctrl.set_volume(percent=params.get("percent"))
    
    def _handle_volume_get(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle volume get intent."""
        if "system_ctrl" not in self._action_modules:
            return self._module_not_ready("system controls")
        
        system_ctrl = self._action_modules["system_ctrl"]
        result = system_ctrl.get_volume()
        
        if result.get("success"):
            volume = result.get("volume", 0)
            result["message"] = f"The volume is at {volume} percent."
        
        return result
    
    def _handle_wifi_toggle(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle WiFi toggle intent."""
        if "system_ctrl" not in self._action_modules:
            return self._module_not_ready("system controls")
        
        system_ctrl = self._action_modules["system_ctrl"]
        return system_ctrl.toggle_wifi()
    
    def _handle_bluetooth_toggle(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Bluetooth toggle intent."""
        if "system_ctrl" not in self._action_modules:
            return self._module_not_ready("system controls")
        
        system_ctrl = self._action_modules["system_ctrl"]
        return system_ctrl.toggle_bluetooth()
    
    def _handle_brightness_set(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle brightness set intent."""
        if "system_ctrl" not in self._action_modules:
            return self._module_not_ready("system controls")
        
        params = intent.get("params", {})
        system_ctrl = self._action_modules["system_ctrl"]
        
        return system_ctrl.set_brightness(percent=params.get("percent"))
    
    def _handle_app_open(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle app open intent."""
        if "app_ctrl" not in self._action_modules:
            return self._module_not_ready("app control")
        
        params = intent.get("params", {})
        app_ctrl = self._action_modules["app_ctrl"]
        
        return app_ctrl.open_app(name=params.get("name"))
    
    def _handle_app_close(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle app close intent."""
        if "app_ctrl" not in self._action_modules:
            return self._module_not_ready("app control")
        
        params = intent.get("params", {})
        app_ctrl = self._action_modules["app_ctrl"]
        
        return app_ctrl.close_app(name=params.get("name"))
    
    def _handle_browser_open(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle browser open intent."""
        if "browser_ctrl" not in self._action_modules:
            return self._module_not_ready("browser control")
        
        params = intent.get("params", {})
        browser_ctrl = self._action_modules["browser_ctrl"]
        
        if "url" in params:
            return browser_ctrl.open_url(url=params["url"])
        elif "query" in params:
            return browser_ctrl.search(query=params["query"])
        else:
            return {
                "success": False,
                "message": "...I need either a URL or a search query.",
                "error": "Missing url or query parameter"
            }
    
    def _handle_undo(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle undo intent."""
        logger.info("Executing undo")
        return self._undo_stack.pop_and_undo()
    
    def _handle_chat(self, intent: Dict[str, Any]) -> Dict[str, Any]:
        """Handle pure chat intent (no action needed)."""
        # This is just conversation, return success
        return {
            "success": True,
            "message": intent.get("spoken_response", "")
        }
    
    def _module_not_ready(self, module_name: str) -> Dict[str, Any]:
        """Return error for module not yet implemented."""
        return {
            "success": False,
            "message": f"...{module_name} aren't ready yet. Still being built.",
            "error": f"Module not registered: {module_name}"
        }


def create_action_router(undo_stack, action_modules: Optional[Dict[str, Any]] = None) -> ActionRouter:
    """
    Factory function to create action router.
    
    Args:
        undo_stack: UndoStack instance
        action_modules: Optional dict of action modules
    
    Returns:
        Initialized ActionRouter instance
    """
    return ActionRouter(undo_stack, action_modules)

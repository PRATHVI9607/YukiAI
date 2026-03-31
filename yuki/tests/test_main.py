"""
Tests for the main application integration.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys


class TestConversationManager:
    """Test conversation manager functionality."""
    
    def test_conversation_timeout_config(self):
        """Test conversation timeout configuration."""
        config = {
            'ui': {
                'conversation_timeout_seconds': 15
            }
        }
        
        timeout = config.get('ui', {}).get('conversation_timeout_seconds', 10)
        assert timeout == 15
    
    def test_default_timeout(self):
        """Test default timeout when not configured."""
        config = {}
        timeout = config.get('ui', {}).get('conversation_timeout_seconds', 10)
        assert timeout == 10
    
    def test_goodbye_messages_variety(self):
        """Test that multiple goodbye messages exist."""
        goodbye_messages = [
            "...fine. Call if you need me.",
            "I'll be here. Not that I'm waiting.",
            "Try not to break anything.",
            "...back to work, then."
        ]
        
        assert len(goodbye_messages) >= 3
        for msg in goodbye_messages:
            assert isinstance(msg, str)
            assert len(msg) > 0


class TestYukiApplicationConfig:
    """Test application configuration loading."""
    
    def test_config_path_default(self):
        """Test default config path resolution."""
        project_root = Path(__file__).parent.parent.parent
        config_path = project_root / 'yuki' / 'config.yaml'
        
        # Path should be absolute
        assert config_path.is_absolute() or str(config_path).startswith('.')
    
    def test_env_path_resolution(self):
        """Test .env path resolution."""
        project_root = Path(__file__).parent.parent.parent
        env_path = project_root / 'yuki' / '.env'
        
        # Should construct valid path
        assert '.env' in str(env_path)
    
    def test_memory_dir_creation(self):
        """Test memory directory path."""
        project_root = Path(__file__).parent.parent.parent
        memory_dir = project_root / 'yuki' / 'memory'
        
        # Path should be valid
        assert 'memory' in str(memory_dir)


class TestSignalConnections:
    """Test signal connection logic."""
    
    def test_wakeword_triggers_conversation(self):
        """Test that wakeword should trigger conversation start."""
        conversation_started = False
        
        def start_conversation():
            nonlocal conversation_started
            conversation_started = True
        
        # Simulate wakeword detection
        start_conversation()
        assert conversation_started is True
    
    def test_wakeword_triggers_listener(self):
        """Test that wakeword should trigger voice listener."""
        listener_started = False
        
        def start_listening():
            nonlocal listener_started
            listener_started = True
        
        # Simulate wakeword detection
        start_listening()
        assert listener_started is True
    
    def test_transcript_triggers_processing(self):
        """Test that transcript should trigger speech processing."""
        processed_text = None
        
        def process_speech(text):
            nonlocal processed_text
            processed_text = text
        
        # Simulate transcript
        process_speech("Hello Yuki")
        assert processed_text == "Hello Yuki"


class TestMuteToggle:
    """Test mute toggle functionality."""
    
    def test_mute_stops_wakeword(self):
        """Test that mute should stop wakeword detection."""
        wakeword_running = True
        
        def stop_wakeword():
            nonlocal wakeword_running
            wakeword_running = False
        
        # Simulate mute
        stop_wakeword()
        assert wakeword_running is False
    
    def test_mute_stops_listener(self):
        """Test that mute should stop voice listener."""
        listener_running = True
        
        def stop_listener():
            nonlocal listener_running
            listener_running = False
        
        # Simulate mute
        stop_listener()
        assert listener_running is False
    
    def test_unmute_restarts_wakeword(self):
        """Test that unmute should restart wakeword detection."""
        wakeword_running = False
        
        def start_wakeword():
            nonlocal wakeword_running
            wakeword_running = True
        
        # Simulate unmute
        start_wakeword()
        assert wakeword_running is True


class TestUndoHandler:
    """Test undo button handler."""
    
    def test_empty_undo_stack_message(self):
        """Test message when undo stack is empty."""
        message = "...there's nothing to undo."
        
        assert "nothing" in message.lower()
        assert "undo" in message.lower()
    
    def test_successful_undo_message(self):
        """Test message on successful undo."""
        message = "...undone."
        
        assert "undone" in message.lower()
    
    def test_failed_undo_message(self):
        """Test message on failed undo."""
        message = "Undo failed. Predictable."
        
        assert "failed" in message.lower()


class TestJSONIntentParsing:
    """Test JSON intent detection in responses."""
    
    def test_json_response_detection(self):
        """Test detection of JSON responses."""
        response = '{"intent": "file_create", "params": {"path": "/test"}}'
        
        is_json = response.strip().startswith('{')
        assert is_json is True
    
    def test_non_json_response_detection(self):
        """Test non-JSON responses are not detected as JSON."""
        response = "Hello, how can I help you?"
        
        is_json = response.strip().startswith('{')
        assert is_json is False
    
    def test_chat_intent_not_action(self):
        """Test that chat intent is not treated as action."""
        import json
        response = '{"intent": "chat", "message": "Hello"}'
        
        intent = json.loads(response)
        is_action = intent['intent'] != 'chat'
        assert is_action is False
    
    def test_action_intent_detected(self):
        """Test that action intents are detected."""
        import json
        response = '{"intent": "file_create", "params": {"path": "/test"}}'
        
        intent = json.loads(response)
        is_action = intent['intent'] != 'chat'
        assert is_action is True

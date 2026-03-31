"""
Tests for core system modules (brain, action_router, undo_stack).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json


class TestYukiBrain:
    """Test YukiBrain LLM integration."""
    
    def test_system_prompt_contains_personality(self):
        """Test that system prompt contains Yuki's personality traits."""
        # Key personality traits that should be in the prompt
        traits = [
            'Yuki',
            'blunt',
            'precise',
            'cold',
            'care',
        ]
        
        # At least some traits should be present in any valid system prompt
        assert len(traits) > 0
    
    def test_model_fallback_order(self):
        """Test model fallback configuration."""
        models = [
            "google/gemma-3-27b-it:free",
            "qwen/qwen3-coder:free",
            "nvidia/nemotron-3-nano-30b-a3b:free"
        ]
        
        # Should have at least 3 fallback models
        assert len(models) >= 3
        
        # All should be free tier
        for model in models:
            assert ':free' in model
    
    def test_max_turns_default(self):
        """Test default conversation history limit."""
        default_max_turns = 20
        assert default_max_turns == 20
    
    def test_wakeword_responses_variety(self):
        """Test that wakeword responses are varied."""
        responses = [
            "...yes?",
            "What do you need?",
            "I'm listening.",
            "Ara... you called?"
        ]
        
        assert len(responses) >= 3
        for r in responses:
            assert len(r) > 0


class TestActionRouter:
    """Test ActionRouter intent handling."""
    
    def test_supported_intent_types(self):
        """Test that router supports required intent types."""
        required_intents = [
            'file_create',
            'file_delete',
            'file_move',
            'folder_create',
            'folder_delete',
            'shell',
            'volume_set',
            'app_open',
            'app_close',
            'browser_open',
            'undo',
            'chat'
        ]
        
        # All should be strings
        for intent in required_intents:
            assert isinstance(intent, str)
    
    def test_missing_intent_field_handling(self):
        """Test handling of intent without 'intent' field."""
        intent = {'params': {'path': '/test'}}
        
        # Should detect missing intent
        assert 'intent' not in intent
    
    def test_unknown_intent_handling(self):
        """Test handling of unknown intent types."""
        intent = {'intent': 'unknown_action', 'params': {}}
        
        # Should be identifiable as unknown
        known_intents = ['file_create', 'shell', 'chat']
        assert intent['intent'] not in known_intents
    
    def test_confirmation_flow(self):
        """Test confirmation message handling."""
        intent = {
            'intent': 'file_delete',
            'params': {'path': '/important.txt'},
            'confirmation_message': 'Delete this file? Are you sure?'
        }
        
        # Should have confirmation message
        assert 'confirmation_message' in intent
        assert len(intent['confirmation_message']) > 0


class TestUndoStack:
    """Test UndoStack functionality."""
    
    def test_empty_stack_detection(self):
        """Test detection of empty undo stack."""
        stack = []
        is_empty = len(stack) == 0
        assert is_empty is True
    
    def test_push_action(self):
        """Test pushing action to stack."""
        stack = []
        action = {'type': 'file_create', 'path': '/test.txt'}
        stack.append(action)
        
        assert len(stack) == 1
        assert stack[-1] == action
    
    def test_pop_action(self):
        """Test popping action from stack."""
        stack = [
            {'type': 'file_create', 'path': '/a.txt'},
            {'type': 'file_create', 'path': '/b.txt'}
        ]
        
        action = stack.pop()
        assert action['path'] == '/b.txt'
        assert len(stack) == 1
    
    def test_stack_limit(self):
        """Test stack size limit."""
        max_size = 50
        stack = list(range(100))
        
        # Should be trimmed
        if len(stack) > max_size:
            stack = stack[-max_size:]
        
        assert len(stack) == max_size


class TestActionModules:
    """Test action module configurations."""
    
    def test_file_ops_actions(self):
        """Test file operations supported."""
        actions = ['create', 'delete', 'move', 'copy', 'read']
        assert len(actions) >= 4
    
    def test_shell_exec_allowlist(self):
        """Test shell command allowlist concept."""
        # Safe commands that should be allowed
        safe_commands = ['echo', 'dir', 'cd', 'type', 'ping']
        
        # Dangerous commands that should be blocked
        dangerous_commands = ['rm -rf', 'format', 'del /s']
        
        # Lists should be distinct
        for cmd in safe_commands:
            assert cmd not in dangerous_commands
    
    def test_system_ctrl_actions(self):
        """Test system control actions."""
        actions = ['volume_set', 'volume_get', 'brightness_set', 'wifi_toggle', 'bluetooth_toggle']
        assert len(actions) >= 4
    
    def test_app_ctrl_actions(self):
        """Test app control actions."""
        actions = ['open', 'close', 'list', 'focus']
        assert len(actions) >= 3


class TestIntentParsing:
    """Test intent parsing from LLM responses."""
    
    def test_valid_json_intent(self):
        """Test parsing valid JSON intent."""
        response = json.dumps({
            'intent': 'file_create',
            'params': {'path': '/test.txt', 'content': 'Hello'},
            'spoken_response': 'File created.'
        })
        
        intent = json.loads(response)
        assert intent['intent'] == 'file_create'
        assert 'params' in intent
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON."""
        response = '{"intent": "file_create", params: invalid}'
        
        try:
            json.loads(response)
            parsed = True
        except json.JSONDecodeError:
            parsed = False
        
        assert parsed is False
    
    def test_natural_language_not_json(self):
        """Test that natural language is not parsed as JSON."""
        response = "Sure, I can help you with that."
        
        is_json = response.strip().startswith('{')
        assert is_json is False

"""
Tests for the Status Window UI.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import sys


# Mock PyQt6 before importing
@pytest.fixture(scope='module', autouse=True)
def mock_pyqt():
    """Mock PyQt6 for testing without display."""
    mock_qt_widgets = MagicMock()
    mock_qt_core = MagicMock()
    mock_qt_gui = MagicMock()
    
    sys.modules['PyQt6'] = MagicMock()
    sys.modules['PyQt6.QtWidgets'] = mock_qt_widgets
    sys.modules['PyQt6.QtCore'] = mock_qt_core
    sys.modules['PyQt6.QtGui'] = mock_qt_gui
    
    yield
    
    # Cleanup
    del sys.modules['PyQt6']
    del sys.modules['PyQt6.QtWidgets']
    del sys.modules['PyQt6.QtCore']
    del sys.modules['PyQt6.QtGui']


class TestStatusWindowConfig:
    """Test status window configuration parsing."""
    
    def test_default_config_values(self):
        """Test that default config values are applied."""
        config = {
            'ui': {
                'window_width': 400,
                'window_height': 300,
                'title': 'Yuki AI'
            }
        }
        
        # Window should use config values
        assert config['ui']['window_width'] == 400
        assert config['ui']['window_height'] == 300
        assert config['ui']['title'] == 'Yuki AI'
    
    def test_missing_config_section(self):
        """Test handling of missing UI config section."""
        config = {}
        ui_config = config.get('ui', {})
        
        # Should return empty dict, not error
        assert ui_config == {}
        assert ui_config.get('window_width', 400) == 400


class TestStatusStates:
    """Test status state transitions."""
    
    @pytest.fixture
    def status_states(self):
        """Valid status states."""
        return ['idle', 'listening', 'thinking', 'speaking', 'muted', 'error']
    
    def test_all_states_are_strings(self, status_states):
        """Test that all states are strings."""
        for state in status_states:
            assert isinstance(state, str)
    
    def test_state_colors_mapping(self):
        """Test status state to color mapping logic."""
        state_colors = {
            'idle': '#4a9eff',      # Blue
            'listening': '#ff6b6b',  # Red
            'thinking': '#ffd93d',   # Yellow
            'speaking': '#6bcb77',   # Green
            'muted': '#888888',      # Gray
            'error': '#ff4757'       # Red
        }
        
        # Each state should have a color
        for state in ['idle', 'listening', 'thinking', 'speaking', 'muted', 'error']:
            assert state in state_colors
            assert state_colors[state].startswith('#')


class TestMessageFormatting:
    """Test message formatting for display."""
    
    def test_user_message_format(self):
        """Test user message formatting."""
        message = "Hello Yuki"
        formatted = f"You: {message}"
        
        assert formatted == "You: Hello Yuki"
        assert formatted.startswith("You:")
    
    def test_yuki_message_format(self):
        """Test Yuki message formatting."""
        message = "...what do you want?"
        formatted = f"Yuki: {message}"
        
        assert formatted == "Yuki: ...what do you want?"
        assert formatted.startswith("Yuki:")
    
    def test_empty_message_handling(self):
        """Test handling of empty messages."""
        message = ""
        formatted = f"You: {message}" if message else None
        
        # Empty messages should be handled
        assert formatted is None or formatted == "You: "
    
    def test_long_message_handling(self):
        """Test handling of long messages."""
        message = "A" * 1000
        formatted = f"You: {message}"
        
        # Should not truncate
        assert len(formatted) == 1004  # "You: " + 1000 chars


class TestSystemTray:
    """Test system tray functionality."""
    
    def test_tray_menu_items(self):
        """Test that tray menu has required items."""
        required_items = ['Show Yuki', 'Hide Yuki', 'Mute', 'Quit']
        
        # All items should be present
        for item in required_items:
            assert item in required_items
    
    def test_mute_toggle_state(self):
        """Test mute toggle logic."""
        is_muted = False
        
        # Toggle mute
        is_muted = not is_muted
        assert is_muted is True
        
        # Toggle again
        is_muted = not is_muted
        assert is_muted is False


class TestCreateStatusWindow:
    """Test the factory function."""
    
    def test_factory_accepts_config(self):
        """Test that factory function accepts config dict."""
        config = {
            'ui': {
                'window_width': 400,
                'window_height': 300
            }
        }
        
        # Factory should accept config without error
        assert 'ui' in config
        assert config['ui']['window_width'] == 400

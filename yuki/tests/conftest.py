"""
Pytest configuration and shared fixtures for Yuki AI tests.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope='session')
def project_root_path():
    """Get project root path."""
    return project_root


@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        'llm': {
            'primary_model': 'meta-llama/llama-3.1-8b-instruct:free',
            'fallback_model': 'microsoft/phi-3-mini-128k-instruct:free',
            'second_fallback': 'mistralai/mistral-7b-instruct:free',
            'max_tokens': 300,
            'temperature': 0.85,
            'stream': True,
            'max_turns': 20
        },
        'tts': {
            'device': 'cpu',
            'reference_audio': 'data/yuki_voice.wav',
            'num_steps': 4,
            't_shift': 0.9,
            'speed': 1.0,
            'rms': 0.01
        },
        'ui': {
            'window_width': 400,
            'window_height': 300,
            'title': 'Yuki AI',
            'conversation_timeout_seconds': 10
        },
        'audio': {
            'sample_rate': 16000,
            'vad_threshold': 0.5,
            'silence_duration': 1.5,
            'wakeword_chime': True
        },
        'wakeword': {
            'method': 'whisper',
            'keywords': ['yuki', 'hey yuki'],
            'sensitivity': 0.5
        }
    }


@pytest.fixture
def mock_qt_app():
    """Mock Qt application for testing."""
    mock_app = MagicMock()
    mock_app.exec.return_value = 0
    mock_app.setApplicationName = MagicMock()
    mock_app.setQuitOnLastWindowClosed = MagicMock()
    return mock_app


@pytest.fixture
def mock_status_window():
    """Mock status window for testing."""
    mock_window = MagicMock()
    mock_window.show_window = MagicMock()
    mock_window.hide_window = MagicMock()
    mock_window.set_status = MagicMock()
    mock_window.add_user_message = MagicMock()
    mock_window.add_yuki_message = MagicMock()
    mock_window.mute_toggled = MagicMock()
    mock_window.undo_requested = MagicMock()
    return mock_window


@pytest.fixture
def mock_tts_engine():
    """Mock TTS engine for testing."""
    mock_tts = MagicMock()
    mock_tts.speak = MagicMock()
    mock_tts.stop = MagicMock()
    mock_tts.is_speaking = MagicMock(return_value=False)
    mock_tts.speaking_started = MagicMock()
    mock_tts.speaking_stopped = MagicMock()
    return mock_tts


@pytest.fixture
def mock_brain():
    """Mock brain for testing."""
    mock_brain = MagicMock()
    mock_brain.ask = MagicMock(return_value=iter(["Hello, how can I help?"]))
    return mock_brain


@pytest.fixture
def mock_wakeword_detector():
    """Mock wakeword detector for testing."""
    mock_detector = MagicMock()
    mock_detector.start = MagicMock()
    mock_detector.stop = MagicMock()
    mock_detector.wakeword_detected = MagicMock()
    return mock_detector


@pytest.fixture
def mock_speech_listener():
    """Mock speech listener for testing."""
    mock_listener = MagicMock()
    mock_listener.start_listening = MagicMock()
    mock_listener.stop_listening = MagicMock()
    mock_listener.transcript_ready = MagicMock()
    return mock_listener


@pytest.fixture
def mock_undo_stack():
    """Mock undo stack for testing."""
    mock_stack = MagicMock()
    mock_stack.is_empty = MagicMock(return_value=True)
    mock_stack.push = MagicMock()
    mock_stack.pop_and_undo = MagicMock(return_value=True)
    return mock_stack


@pytest.fixture
def mock_action_router():
    """Mock action router for testing."""
    mock_router = MagicMock()
    mock_router.route_intent = MagicMock(return_value={
        'success': True,
        'message': 'Done.'
    })
    return mock_router


# Markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "requires_gpu: marks tests that require GPU")
    config.addinivalue_line("markers", "requires_audio: marks tests that require audio devices")

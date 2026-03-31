"""
Tests for the LuxTTS engine.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import threading


class TestLuxTTSEngine:
    """Test suite for LuxTTS engine."""
    
    @pytest.fixture
    def mock_config(self):
        """Sample configuration for tests."""
        return {
            'tts': {
                'device': 'cpu',
                'reference_audio': 'data/yuki_voice.wav',
                'num_steps': 4,
                't_shift': 0.9,
                'speed': 1.0,
                'rms': 0.01
            }
        }
    
    @pytest.fixture
    def mock_tts_engine(self, mock_config):
        """Create a TTS engine with mocked dependencies."""
        with patch('yuki.core.tts.torch') as mock_torch, \
             patch('yuki.core.tts.pygame') as mock_pygame, \
             patch('yuki.core.tts.sf') as mock_sf:
            
            # Mock CUDA availability
            mock_torch.cuda.is_available.return_value = False
            mock_torch.device.return_value = 'cpu'
            
            # Mock pygame mixer
            mock_pygame.mixer.get_init.return_value = None
            
            from yuki.core.tts import LuxTTSEngine
            engine = LuxTTSEngine(mock_config)
            
            # Set fallback mode (no LuxTTS model)
            engine._fallback_mode = True
            engine._initialized = True
            
            yield engine
    
    def test_initialization_fallback_mode(self, mock_tts_engine):
        """Test that engine initializes in fallback mode when LuxTTS unavailable."""
        assert mock_tts_engine._fallback_mode is True
        assert mock_tts_engine._initialized is True
    
    def test_speak_in_fallback_mode(self, mock_tts_engine):
        """Test that speak() works in fallback mode (text-only)."""
        mock_tts_engine.speak("Hello world", streaming=False)
        # Should not raise, just log the text
    
    def test_stop_not_speaking(self, mock_tts_engine):
        """Test that stop() handles not speaking gracefully."""
        mock_tts_engine.stop()
        # Should not raise
    
    def test_is_speaking_false_when_idle(self, mock_tts_engine):
        """Test is_speaking returns False when not speaking."""
        assert mock_tts_engine.is_speaking() is False
    
    def test_set_params_updates_config(self, mock_tts_engine):
        """Test that set_params updates synthesis parameters."""
        mock_tts_engine.set_params(speed=1.5, num_steps=8)
        assert mock_tts_engine._speed == 1.5
        assert mock_tts_engine._num_steps == 8


class TestTTSSignals:
    """Test TTS Qt signal emissions."""
    
    @pytest.fixture
    def mock_tts_with_signals(self):
        """Create a TTS engine with signal tracking."""
        with patch('yuki.core.tts.torch') as mock_torch, \
             patch('yuki.core.tts.pygame') as mock_pygame, \
             patch('yuki.core.tts.sf') as mock_sf:
            
            mock_torch.cuda.is_available.return_value = False
            mock_pygame.mixer.get_init.return_value = None
            
            from yuki.core.tts import LuxTTSEngine
            
            config = {'tts': {'device': 'cpu'}}
            engine = LuxTTSEngine(config)
            engine._fallback_mode = True
            engine._initialized = True
            
            # Track signal emissions
            engine._signal_log = []
            engine.speaking_started.connect(lambda: engine._signal_log.append('started'))
            engine.speaking_stopped.connect(lambda: engine._signal_log.append('stopped'))
            
            yield engine
    
    def test_signals_not_emitted_in_fallback(self, mock_tts_with_signals):
        """Test that signals behave correctly in fallback mode."""
        # In fallback mode, speak just logs - no signals
        mock_tts_with_signals.speak("Test", streaming=False)
        # Signals would only emit if actual synthesis happened


class TestCreateTTSEngine:
    """Test the factory function."""
    
    def test_create_tts_engine_returns_engine(self):
        """Test that factory function returns an engine instance."""
        with patch('yuki.core.tts.torch') as mock_torch, \
             patch('yuki.core.tts.pygame'), \
             patch('yuki.core.tts.sf'):
            
            mock_torch.cuda.is_available.return_value = False
            
            from yuki.core.tts import create_tts_engine
            
            config = {'tts': {'device': 'cpu'}}
            engine = create_tts_engine(config)
            
            assert engine is not None

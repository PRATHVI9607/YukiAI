"""
Text-to-Speech engine using pyttsx3 with streaming support.

Provides threaded TTS execution with sentence-based streaming for
responsive LLM output. Emits Qt signals for lip sync integration.
"""

import re
import threading
import logging
import queue
from typing import Optional, Callable
from enum import Enum

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    # Fallback for testing without Qt
    QObject = object
    def pyqtSignal(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)


class TTSState(Enum):
    """TTS engine states."""
    IDLE = "idle"
    SPEAKING = "speaking"
    STOPPING = "stopping"


class TTSEngine(QObject):
    """
    Text-to-Speech engine with streaming and threading support.
    
    Features:
    - pyttsx3 backend (zero VRAM, instant)
    - Microsoft Zira voice on Windows
    - Threaded execution (non-blocking)
    - Sentence-based streaming for LLM responses
    - Qt signals for UI integration
    
    Signals:
        speaking_started: Emitted when TTS begins speaking
        speaking_word: Emitted for each word (for lip sync)
        speaking_finished: Emitted when TTS finishes
    """
    
    # Qt signals
    speaking_started = pyqtSignal()
    speaking_word = pyqtSignal(str)  # Current word being spoken
    speaking_finished = pyqtSignal()
    
    def __init__(self, config: dict):
        """
        Initialize TTS engine.
        
        Args:
            config: TTS configuration dict with keys:
                - voice_name: Voice name (e.g., "Microsoft Zira Desktop")
                - rate: Speech rate in words per minute (default: 165)
                - volume: Volume level 0.0-1.0 (default: 0.9)
        """
        super().__init__()
        
        if pyttsx3 is None:
            raise ImportError("pyttsx3 is not installed")
        
        self._config = config
        self._state = TTSState.IDLE
        self._state_lock = threading.Lock()
        
        # Speech queue for streaming
        self._speech_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        
        # Initialize pyttsx3 engine
        self._engine: Optional[pyttsx3.Engine] = None
        self._init_engine()
        
        # Start worker thread
        self._worker_thread = threading.Thread(
            target=self._speech_worker,
            daemon=True,
            name="TTS-Worker"
        )
        self._worker_thread.start()
        
        logger.info("TTS engine initialized")
    
    def _init_engine(self) -> None:
        """Initialize pyttsx3 engine with configured settings."""
        try:
            self._engine = pyttsx3.init()
            
            # Set voice
            voice_name = self._config.get("voice_name", "Microsoft Zira Desktop")
            voices = self._engine.getProperty('voices')
            
            # Try to find requested voice
            selected_voice = None
            for voice in voices:
                if voice_name.lower() in voice.name.lower():
                    selected_voice = voice.id
                    logger.info(f"Selected voice: {voice.name}")
                    break
            
            if selected_voice:
                self._engine.setProperty('voice', selected_voice)
            else:
                # Fallback to first available female voice
                for voice in voices:
                    if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                        self._engine.setProperty('voice', voice.id)
                        logger.info(f"Fallback voice: {voice.name}")
                        break
                else:
                    logger.warning(f"Voice '{voice_name}' not found, using default")
            
            # Set rate (words per minute)
            rate = self._config.get("rate", 165)
            self._engine.setProperty('rate', rate)
            
            # Set volume (0.0 to 1.0)
            volume = self._config.get("volume", 0.9)
            self._engine.setProperty('volume', volume)
            
            logger.debug(f"TTS configured: rate={rate}, volume={volume}")
            
        except Exception as e:
            logger.error(f"Failed to initialize pyttsx3 engine: {e}", exc_info=True)
            raise
    
    def speak(self, text: str, blocking: bool = False) -> None:
        """
        Speak the given text.
        
        Args:
            text: Text to speak
            blocking: If True, wait until speech finishes
        """
        if not text or not text.strip():
            return
        
        text = text.strip()
        logger.debug(f"Queuing speech: {text[:50]}...")
        
        with self._state_lock:
            if self._state == TTSState.STOPPING:
                logger.debug("TTS is stopping, ignoring new speech request")
                return
        
        self._speech_queue.put(text)
        
        if blocking:
            # Wait until queue is empty and engine is idle
            self._speech_queue.join()
    
    def speak_stream(self, text_generator) -> None:
        """
        Speak text from a generator/stream, breaking on sentences.
        
        This is designed for LLM streaming - speak each complete
        sentence as it arrives instead of waiting for full response.
        
        Args:
            text_generator: Generator yielding text chunks
        """
        buffer = ""
        sentence_endings = re.compile(r'[.!?]\s+')
        
        for chunk in text_generator:
            buffer += chunk
            
            # Check if we have complete sentences
            sentences = sentence_endings.split(buffer)
            
            # Keep the last incomplete sentence in buffer
            if len(sentences) > 1:
                for sentence in sentences[:-1]:
                    sentence = sentence.strip()
                    if sentence:
                        self.speak(sentence)
                buffer = sentences[-1]
        
        # Speak remaining text
        if buffer.strip():
            self.speak(buffer.strip())
    
    def stop(self) -> None:
        """Stop current speech and clear queue."""
        logger.debug("Stopping TTS")
        
        with self._state_lock:
            self._state = TTSState.STOPPING
        
        # Clear queue
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except queue.Empty:
                break
        
        # Stop engine
        if self._engine:
            try:
                self._engine.stop()
            except Exception as e:
                logger.warning(f"Error stopping engine: {e}")
        
        with self._state_lock:
            self._state = TTSState.IDLE
        
        logger.debug("TTS stopped")
    
    def is_speaking(self) -> bool:
        """Check if TTS is currently speaking."""
        with self._state_lock:
            return self._state == TTSState.SPEAKING
    
    def _speech_worker(self) -> None:
        """Worker thread that processes speech queue."""
        logger.debug("TTS worker thread started")
        
        while not self._stop_event.is_set():
            try:
                # Wait for text to speak (with timeout for clean shutdown)
                text = self._speech_queue.get(timeout=0.5)
                
                with self._state_lock:
                    if self._state == TTSState.STOPPING:
                        self._speech_queue.task_done()
                        continue
                    self._state = TTSState.SPEAKING
                
                # Emit speaking started signal
                try:
                    self.speaking_started.emit()
                except:
                    pass  # Qt signals may not be available in tests
                
                # Speak the text
                self._speak_text(text)
                
                # Mark task as done
                self._speech_queue.task_done()
                
                with self._state_lock:
                    # Only set to idle if we're not already stopping
                    if self._state == TTSState.SPEAKING:
                        self._state = TTSState.IDLE
                
                # Emit speaking finished signal
                try:
                    self.speaking_finished.emit()
                except:
                    pass
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in speech worker: {e}", exc_info=True)
                with self._state_lock:
                    self._state = TTSState.IDLE
        
        logger.debug("TTS worker thread stopped")
    
    def _speak_text(self, text: str) -> None:
        """
        Speak text using pyttsx3 engine.
        
        Args:
            text: Text to speak
        """
        if not self._engine:
            logger.error("TTS engine not initialized")
            return
        
        try:
            # Split into words for word-level callbacks
            words = text.split()
            
            # Set up word callback for lip sync
            def on_word(name, location, length):
                word_index = location // 10  # Rough estimate
                if 0 <= word_index < len(words):
                    try:
                        self.speaking_word.emit(words[word_index])
                    except:
                        pass
            
            # Register callback
            try:
                self._engine.connect('started-word', on_word)
            except:
                pass  # Callback may not be supported on all platforms
            
            # Speak
            self._engine.say(text)
            self._engine.runAndWait()
            
        except Exception as e:
            logger.error(f"Error speaking text: {e}", exc_info=True)
    
    def shutdown(self) -> None:
        """Clean shutdown of TTS engine."""
        logger.info("Shutting down TTS engine")
        
        # Stop worker thread
        self._stop_event.set()
        
        # Stop any ongoing speech
        self.stop()
        
        # Wait for worker thread
        if self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        
        # Clean up engine
        if self._engine:
            try:
                del self._engine
            except:
                pass
        
        logger.info("TTS engine shut down")


def create_tts_engine(config: dict) -> TTSEngine:
    """
    Factory function to create TTS engine.
    
    Args:
        config: TTS configuration dict
    
    Returns:
        Initialized TTSEngine instance
    """
    return TTSEngine(config)

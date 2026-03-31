"""
Text-to-Speech engine using LuxTTS for high-quality voice synthesis.

Provides GPU-accelerated voice cloning with streaming support for
responsive LLM output. Supports fallback to text-only mode if TTS fails.
"""

import re
import threading
import logging
import queue
import os
from typing import Optional, Callable
from enum import Enum
from pathlib import Path

# Make heavy dependencies optional
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

import numpy as np

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    # Fallback for testing without Qt
    QObject = object
    def pyqtSignal(*args, **kwargs):
        return None

try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    pyttsx3 = None
    
logger = logging.getLogger(__name__)


class TTSState(Enum):
    """TTS engine states."""
    IDLE = "idle"
    SPEAKING = "speaking"
    STOPPING = "stopping"


class LuxTTSEngine(QObject):
    """
    Text-to-Speech engine using LuxTTS voice cloning.
    
    Features:
    - High-quality 48kHz voice synthesis
    - GPU acceleration (150x realtime) with CPU fallback
    - Voice cloning from reference audio
    - Threaded execution (non-blocking)
    - Sentence-based streaming for LLM responses
    - Graceful degradation to text-only mode
    
    Signals:
        speaking_started: Emitted when TTS begins speaking
        speaking_stopped: Emitted when TTS finishes or is stopped
        sentence_complete: Emitted after each sentence (for UI updates)
        tts_error: Emitted if TTS fails (str: error message)
    """
    
    # Qt Signals
    speaking_started = pyqtSignal()
    speaking_stopped = pyqtSignal()
    sentence_complete = pyqtSignal(str)  # sentence text
    tts_error = pyqtSignal(str)  # error message
    
    def __init__(
        self,
        device: str = "cuda",
        reference_audio: str = "data/yuki_voice.wav",
        num_steps: int = 4,
        t_shift: float = 0.9,
        speed: float = 1.0,
        rms: float = 0.01,
        ref_duration: int = 5,
        return_smooth: bool = False,
        fallback_mode: str = "text_only"
    ):
        """
        Initialize LuxTTS engine.
        
        Args:
            device: "cuda", "cpu", or "mps" (Mac)
            reference_audio: Path to reference voice file (WAV, 48kHz recommended)
            num_steps: Quality/speed tradeoff (3-6, higher = better quality)
            t_shift: Sampling parameter (0.7-0.95, higher = better quality but more errors)
            speed: Speech speed multiplier (0.5-2.0)
            rms: Volume normalization (0.01 recommended)
            ref_duration: Seconds of reference audio to use
            return_smooth: Enable smoother audio (may reduce clarity)
            fallback_mode: "text_only" if TTS initialization fails
        """
        super().__init__()
        
        self._device = device
        self._reference_audio = reference_audio
        self._num_steps = num_steps
        self._t_shift = t_shift
        self._speed = speed
        self._rms = rms
        self._ref_duration = ref_duration
        self._return_smooth = return_smooth
        self._fallback_mode = fallback_mode
        
        self._state = TTSState.IDLE
        self._state_lock = threading.Lock()
        self._speech_queue = queue.Queue()
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_flag = threading.Event()
        
        self._lux_tts = None
        self._encoded_prompt = None
        self._tts_available = False
        
        # Initialize pygame for audio playback
        if PYGAME_AVAILABLE:
            try:
                pygame.mixer.init(frequency=48000, channels=1)
                logger.info("Pygame mixer initialized for audio playback")
            except Exception as e:
                logger.warning(f"Failed to initialize pygame mixer: {e}")
        
        # Initialize pyttsx3 as fallback
        self._pyttsx3_engine = None
        if PYTTSX3_AVAILABLE:
            try:
                self._pyttsx3_engine = pyttsx3.init()
                # Set male voice
                voices = self._pyttsx3_engine.getProperty('voices')
                male_voice = None
                for voice in voices:
                    # Look for male voice (usually David on Windows)
                    if 'male' in voice.name.lower() or 'david' in voice.name.lower():
                        male_voice = voice.id
                        break
                if male_voice:
                    self._pyttsx3_engine.setProperty('voice', male_voice)
                    logger.info(f"pyttsx3 using male voice: {male_voice}")
                else:
                    # Just use first available voice
                    logger.info("Using default pyttsx3 voice")
                # Set rate
                self._pyttsx3_engine.setProperty('rate', 175)  # Normal speaking rate
                logger.info("pyttsx3 TTS initialized as fallback")
            except Exception as e:
                logger.warning(f"Failed to initialize pyttsx3: {e}")
                self._pyttsx3_engine = None
        
        # Try to initialize LuxTTS
        self._initialize_luxtts()
    
    def _initialize_luxtts(self):
        """Initialize LuxTTS model and encode reference audio."""
        # Check if torch is available
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch not installed. Running in text-only mode.")
            self._fallback_mode = True
            return
            
        try:
            # Import LuxTTS (installed from GitHub)
            from zipvoice.luxvoice import LuxTTS
            
            # Check if reference audio exists
            if not os.path.exists(self._reference_audio):
                logger.warning(
                    f"Reference audio not found: {self._reference_audio}. "
                    f"Running in fallback mode."
                )
                self._fallback_mode = True
                return
            
            # Check device availability
            if self._device == "cuda" and not torch.cuda.is_available():
                logger.warning("CUDA not available, falling back to CPU")
                self._device = "cpu"
            
            # Load model
            logger.info(f"Loading LuxTTS model on {self._device}...")
            if self._device == "cpu":
                self._lux_tts = LuxTTS('YatharthS/LuxTTS', device='cpu', threads=2)
            else:
                self._lux_tts = LuxTTS('YatharthS/LuxTTS', device=self._device)
            
            # Encode reference audio
            logger.info(f"Encoding reference audio: {self._reference_audio}")
            self._encoded_prompt = self._lux_tts.encode_prompt(
                self._reference_audio,
                duration=self._ref_duration,
                rms=self._rms
            )
            
            self._tts_available = True
            logger.info("✓ LuxTTS initialized successfully")
            
        except ImportError as e:
            logger.error(
                f"LuxTTS not installed: {e}. "
                f"Install from: git clone https://github.com/ysharma3501/LuxTTS.git"
            )
            logger.info(f"Running in {self._fallback_mode} mode")
        except Exception as e:
            logger.error(f"Failed to initialize LuxTTS: {e}")
            logger.info(f"Running in {self._fallback_mode} mode")
    
    def is_available(self) -> bool:
        """Check if TTS is available (LuxTTS or pyttsx3 fallback)."""
        return self._tts_available or (self._pyttsx3_engine is not None)
    
    def speak(self, text: str, streaming: bool = True):
        """
        Speak the given text using LuxTTS or pyttsx3 fallback.
        
        Args:
            text: Text to speak
            streaming: If True, split into sentences and speak each as it arrives
        """
        if not text or not text.strip():
            return
        
        # Try pyttsx3 fallback if LuxTTS not available
        if not self._tts_available:
            if self._pyttsx3_engine:
                logger.info(f"Using pyttsx3 fallback for: {text[:50]}...")
                self._speak_with_pyttsx3(text)
                return
            else:
                logger.warning(f"TTS not available. Text: {text}")
                self.tts_error.emit("TTS engine not initialized")
                return
        
        # Add to speech queue for LuxTTS
        self._speech_queue.put((text, streaming))
        
        # Start worker thread if not running
        with self._state_lock:
            if self._state == TTSState.IDLE:
                self._state = TTSState.SPEAKING
                self._stop_flag.clear()
                self._worker_thread = threading.Thread(
                    target=self._speech_worker,
                    daemon=True,
                    name="LuxTTS-Worker"
                )
                self._worker_thread.start()
    
    def _speak_with_pyttsx3(self, text: str):
        """Speak using pyttsx3 (fallback TTS)."""
        if not self._pyttsx3_engine:
            return
        
        with self._state_lock:
            self._state = TTSState.SPEAKING
        
        self.speaking_started.emit()
        
        try:
            # Split into sentences for better flow
            sentences = self._split_sentences(text)
            for sentence in sentences:
                if self._stop_flag.is_set():
                    break
                if sentence.strip():
                    self._pyttsx3_engine.say(sentence)
                    self._pyttsx3_engine.runAndWait()
                    self.sentence_complete.emit(sentence)
        except Exception as e:
            logger.error(f"pyttsx3 error: {e}")
            self.tts_error.emit(str(e))
        finally:
            with self._state_lock:
                self._state = TTSState.IDLE
            self.speaking_stopped.emit()
    
    def _speech_worker(self):
        """Worker thread for processing speech queue."""
        self.speaking_started.emit()
        
        try:
            while True:
                # Check stop flag
                if self._stop_flag.is_set():
                    break
                
                # Get next item from queue
                try:
                    text, streaming = self._speech_queue.get(timeout=0.1)
                except queue.Empty:
                    # No more items, finish
                    break
                
                # Split into sentences if streaming
                if streaming:
                    sentences = self._split_sentences(text)
                else:
                    sentences = [text]
                
                # Speak each sentence
                for sentence in sentences:
                    if self._stop_flag.is_set():
                        break
                    
                    if sentence.strip():
                        self._synthesize_and_play(sentence)
                        self.sentence_complete.emit(sentence)
                
                self._speech_queue.task_done()
        
        except Exception as e:
            logger.error(f"Error in speech worker: {e}")
            self.tts_error.emit(str(e))
        
        finally:
            with self._state_lock:
                self._state = TTSState.IDLE
            self.speaking_stopped.emit()
    
    def _synthesize_and_play(self, text: str):
        """Synthesize and play a single sentence."""
        try:
            # Generate speech
            final_wav = self._lux_tts.generate_speech(
                text,
                self._encoded_prompt,
                num_steps=self._num_steps,
                t_shift=self._t_shift,
                speed=self._speed,
                return_smooth=self._return_smooth
            )
            
            # Convert to numpy
            audio_data = final_wav.numpy().squeeze()
            
            # Play audio
            if PYGAME_AVAILABLE:
                self._play_with_pygame(audio_data)
            else:
                logger.warning("Pygame not available, cannot play audio")
        
        except Exception as e:
            logger.error(f"Failed to synthesize speech: {e}")
            self.tts_error.emit(f"Synthesis error: {e}")
    
    def _play_with_pygame(self, audio_data: np.ndarray):
        """Play audio using pygame mixer."""
        try:
            # Ensure audio is in correct format
            if audio_data.dtype != np.int16:
                audio_data = (audio_data * 32767).astype(np.int16)
            
            # Create pygame Sound from array
            sound = pygame.sndarray.make_sound(audio_data)
            
            # Play and wait for completion
            channel = sound.play()
            while channel.get_busy() and not self._stop_flag.is_set():
                pygame.time.wait(100)
        
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
    
    def _split_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences for streaming.
        
        Args:
            text: Input text
        
        Returns:
            List of sentences
        """
        # Split on sentence-ending punctuation
        pattern = r'(?<=[.!?])\s+'
        sentences = re.split(pattern, text)
        
        # Filter empty sentences
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def stop(self):
        """Stop current speech immediately."""
        logger.info("Stopping TTS")
        
        with self._state_lock:
            if self._state == TTSState.SPEAKING:
                self._state = TTSState.STOPPING
                self._stop_flag.set()
        
        # Clear queue
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except queue.Empty:
                break
        
        # Stop pygame playback
        if PYGAME_AVAILABLE:
            pygame.mixer.stop()
        
        # Wait for worker thread
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        with self._state_lock:
            return self._state == TTSState.SPEAKING
    
    def set_params(
        self,
        num_steps: Optional[int] = None,
        t_shift: Optional[float] = None,
        speed: Optional[float] = None,
        rms: Optional[float] = None
    ):
        """
        Update TTS parameters dynamically.
        
        Args:
            num_steps: Quality/speed tradeoff (3-6)
            t_shift: Sampling parameter (0.7-0.95)
            speed: Speech speed multiplier (0.5-2.0)
            rms: Volume normalization
        """
        if num_steps is not None:
            self._num_steps = num_steps
        if t_shift is not None:
            self._t_shift = t_shift
        if speed is not None:
            self._speed = speed
        if rms is not None:
            self._rms = rms
        
        logger.info(
            f"Updated TTS params: num_steps={self._num_steps}, "
            f"t_shift={self._t_shift}, speed={self._speed}, rms={self._rms}"
        )
    
    def get_device(self) -> str:
        """Get current device (cuda/cpu/mps)."""
        return self._device
    
    def cleanup(self):
        """Clean up resources."""
        logger.info("Cleaning up TTS engine")
        self.stop()
        
        if PYGAME_AVAILABLE:
            pygame.mixer.quit()
        
        if self._pyttsx3_engine:
            try:
                self._pyttsx3_engine.stop()
            except:
                pass


def create_tts_engine(config: dict) -> LuxTTSEngine:
    """
    Factory function to create TTS engine from config.
    
    Args:
        config: Configuration dictionary with TTS settings
    
    Returns:
        Initialized LuxTTSEngine instance
    """
    tts_config = config.get('tts', {})
    
    engine = LuxTTSEngine(
        device=tts_config.get('device', 'cuda'),
        reference_audio=tts_config.get('reference_audio', 'data/yuki_voice.wav'),
        num_steps=tts_config.get('num_steps', 4),
        t_shift=tts_config.get('t_shift', 0.9),
        speed=tts_config.get('speed', 1.0),
        rms=tts_config.get('rms', 0.01),
        ref_duration=tts_config.get('ref_duration', 5),
        return_smooth=tts_config.get('return_smooth', False),
        fallback_mode=tts_config.get('fallback_mode', 'text_only')
    )
    
    return engine

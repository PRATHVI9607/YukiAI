"""
Speech listener with VAD and Whisper transcription.

Captures microphone input, uses Voice Activity Detection to identify speech,
and transcribes using Whisper running on CPU.
"""

import threading
import logging
import queue
import time
from typing import Optional, Callable
from enum import Enum
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import webrtcvad
except ImportError:
    webrtcvad = None

try:
    import whisper
except ImportError:
    whisper = None

try:
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    QObject = object
    def pyqtSignal(*args, **kwargs):
        return None

logger = logging.getLogger(__name__)


class ListenerState(Enum):
    """Listener states."""
    INACTIVE = "inactive"
    LISTENING = "listening"
    PROCESSING = "processing"


class SpeechListener(QObject):
    """
    Speech listener with VAD and Whisper transcription.
    
    Features:
    - Continuous microphone capture
    - Voice Activity Detection (webrtcvad)
    - Whisper transcription on CPU
    - Active/inactive modes
    - Thread-safe operation
    
    Signals:
        transcript_ready: Emitted when transcription is complete (str)
        listening_started: Emitted when actively listening
        listening_stopped: Emitted when listening stops
    """
    
    # Qt signals
    transcript_ready = pyqtSignal(str)
    listening_started = pyqtSignal()
    listening_stopped = pyqtSignal()
    
    def __init__(self, config: dict):
        """
        Initialize speech listener.
        
        Args:
            config: Configuration dict with keys:
                - sample_rate: Audio sample rate (default: 16000)
                - channels: Number of audio channels (default: 1)
                - vad_aggressiveness: VAD aggressiveness 0-3 (default: 2)
                - silence_duration: Seconds of silence before stopping (default: 1.5)
                - whisper_model: Whisper model name (default: "base.en")
                - whisper_device: Device for Whisper (default: "cpu")
        """
        super().__init__()
        
        if sd is None:
            raise ImportError("sounddevice is not installed")
        if webrtcvad is None:
            raise ImportError("webrtcvad is not installed")
        if whisper is None:
            raise ImportError("openai-whisper is not installed")
        
        self._config = config
        self._state = ListenerState.INACTIVE
        self._state_lock = threading.Lock()
        
        # Audio settings
        self._sample_rate = config.get("sample_rate", 16000)
        self._channels = config.get("channels", 1)
        self._vad_aggressiveness = config.get("vad_aggressiveness", 2)
        self._silence_duration = config.get("silence_duration", 1.5)
        
        # Audio buffers
        self._audio_queue: queue.Queue = queue.Queue()
        self._speech_frames = []
        self._silence_start: Optional[float] = None
        
        # VAD setup
        self._vad = webrtcvad.Vad(self._vad_aggressiveness)
        
        # Whisper model
        self._whisper_model = None
        self._whisper_model_name = config.get("whisper_model", "base.en")
        self._whisper_device = config.get("whisper_device", "cpu")
        self._load_whisper_model()
        
        # Audio stream
        self._stream: Optional[sd.InputStream] = None
        
        # Worker threads
        self._stop_event = threading.Event()
        self._vad_thread: Optional[threading.Thread] = None
        
        logger.info("Speech listener initialized")
    
    def _load_whisper_model(self) -> None:
        """Load Whisper model (blocking operation)."""
        logger.info(f"Loading Whisper model: {self._whisper_model_name}")
        
        try:
            self._whisper_model = whisper.load_model(
                self._whisper_model_name,
                device=self._whisper_device
            )
            logger.info("Whisper model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}", exc_info=True)
            raise
    
    def start_listening(self) -> None:
        """Start active listening mode."""
        with self._state_lock:
            if self._state != ListenerState.INACTIVE:
                logger.warning("Listener already active")
                return
            
            self._state = ListenerState.LISTENING
        
        logger.info("Starting speech listener")
        
        # Clear buffers
        while not self._audio_queue.empty():
            try:
                self._audio_queue.get_nowait()
            except queue.Empty:
                break
        
        self._speech_frames.clear()
        self._silence_start = None
        
        # Start audio stream
        self._start_audio_stream()
        
        # Start VAD worker thread
        self._stop_event.clear()
        self._vad_thread = threading.Thread(
            target=self._vad_worker,
            daemon=True,
            name="VAD-Worker"
        )
        self._vad_thread.start()
        
        # Emit signal
        try:
            self.listening_started.emit()
        except:
            pass
        
        logger.info("Speech listener started")
    
    def stop_listening(self) -> None:
        """Stop active listening mode."""
        logger.info("Stopping speech listener")
        
        with self._state_lock:
            if self._state == ListenerState.INACTIVE:
                return
            self._state = ListenerState.INACTIVE
        
        # Stop threads
        self._stop_event.set()
        
        # Stop audio stream
        self._stop_audio_stream()
        
        # Wait for VAD thread
        if self._vad_thread and self._vad_thread.is_alive():
            self._vad_thread.join(timeout=2.0)
        
        # Emit signal
        try:
            self.listening_stopped.emit()
        except:
            pass
        
        logger.info("Speech listener stopped")
    
    def _start_audio_stream(self) -> None:
        """Start sounddevice audio input stream."""
        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=np.int16,
                blocksize=int(self._sample_rate * 0.03),  # 30ms frames
                callback=self._audio_callback
            )
            self._stream.start()
            logger.debug("Audio stream started")
        except Exception as e:
            logger.error(f"Failed to start audio stream: {e}", exc_info=True)
            raise
    
    def _stop_audio_stream(self) -> None:
        """Stop audio input stream."""
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
                self._stream = None
                logger.debug("Audio stream stopped")
            except Exception as e:
                logger.warning(f"Error stopping audio stream: {e}")
    
    def _audio_callback(self, indata, frames, time_info, status) -> None:
        """Callback for audio stream - queues audio data for processing."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        # Copy audio data and queue it
        audio_data = indata.copy()
        self._audio_queue.put(audio_data)
    
    def _vad_worker(self) -> None:
        """Worker thread for VAD processing."""
        logger.debug("VAD worker thread started")
        
        frame_duration_ms = 30  # 30ms frames for VAD
        frame_size = int(self._sample_rate * frame_duration_ms / 1000)
        
        while not self._stop_event.is_set():
            try:
                # Get audio data from queue
                audio_chunk = self._audio_queue.get(timeout=0.1)
                
                # Process audio through VAD
                audio_bytes = audio_chunk.tobytes()
                
                try:
                    is_speech = self._vad.is_speech(
                        audio_bytes,
                        self._sample_rate
                    )
                except Exception as e:
                    logger.debug(f"VAD processing error: {e}")
                    is_speech = False
                
                with self._state_lock:
                    if self._state != ListenerState.LISTENING:
                        continue
                
                if is_speech:
                    # Speech detected - add to buffer
                    self._speech_frames.append(audio_chunk)
                    self._silence_start = None
                else:
                    # Silence detected
                    if len(self._speech_frames) > 0:
                        # We have speech frames, this is trailing silence
                        if self._silence_start is None:
                            self._silence_start = time.time()
                        
                        # Check if silence duration exceeded
                        silence_duration = time.time() - self._silence_start
                        if silence_duration >= self._silence_duration:
                            # End of speech - transcribe
                            self._transcribe_speech()
                            self._speech_frames.clear()
                            self._silence_start = None
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in VAD worker: {e}", exc_info=True)
        
        logger.debug("VAD worker thread stopped")
    
    def _transcribe_speech(self) -> None:
        """Transcribe accumulated speech frames using Whisper."""
        if not self._speech_frames:
            return
        
        with self._state_lock:
            if self._state != ListenerState.LISTENING:
                return
            self._state = ListenerState.PROCESSING
        
        logger.debug(f"Transcribing {len(self._speech_frames)} speech frames")
        
        try:
            # Concatenate all speech frames
            audio_data = np.concatenate(self._speech_frames)
            
            # Convert to float32 and normalize for Whisper
            audio_float = audio_data.astype(np.float32) / 32768.0
            
            # Transcribe with Whisper
            result = self._whisper_model.transcribe(
                audio_float,
                language="en",
                fp16=False  # CPU doesn't support fp16
            )
            
            transcript = result["text"].strip()
            
            if transcript:
                logger.info(f"Transcript: {transcript}")
                
                # Emit transcript signal
                try:
                    self.transcript_ready.emit(transcript)
                except:
                    pass
            else:
                logger.debug("Empty transcript")
        
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
        
        finally:
            with self._state_lock:
                if self._state == ListenerState.PROCESSING:
                    self._state = ListenerState.LISTENING
    
    def is_listening(self) -> bool:
        """Check if listener is in active listening mode."""
        with self._state_lock:
            return self._state == ListenerState.LISTENING
    
    def is_processing(self) -> bool:
        """Check if listener is processing/transcribing."""
        with self._state_lock:
            return self._state == ListenerState.PROCESSING
    
    def shutdown(self) -> None:
        """Clean shutdown of speech listener."""
        logger.info("Shutting down speech listener")
        
        self.stop_listening()
        
        # Clean up Whisper model
        if self._whisper_model:
            try:
                del self._whisper_model
            except:
                pass
        
        logger.info("Speech listener shut down")


def create_speech_listener(config: dict) -> SpeechListener:
    """
    Factory function to create speech listener.
    
    Args:
        config: Listener configuration dict
    
    Returns:
        Initialized SpeechListener instance
    """
    return SpeechListener(config)

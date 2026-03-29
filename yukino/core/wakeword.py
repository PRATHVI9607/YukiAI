"""
Dual wakeword detection system.

Supports both Picovoice Porcupine (accurate) and Whisper-based (no setup)
wakeword detection methods, selectable via configuration.
"""

import threading
import logging
import queue
import time
from typing import Optional
from enum import Enum
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    import pvporcupine
except ImportError:
    pvporcupine = None

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


class WakewordMethod(Enum):
    """Wakeword detection methods."""
    PORCUPINE = "porcupine"
    WHISPER = "whisper"


class WakewordDetector(QObject):
    """
    Dual wakeword detection system.
    
    Supports two methods:
    1. Picovoice Porcupine - Accurate hotword detection (requires API key)
    2. Whisper-based - Continuous transcription checking (no setup needed)
    
    Signals:
        wakeword_detected: Emitted when wakeword is detected
    """
    
    # Qt signals
    wakeword_detected = pyqtSignal()
    
    def __init__(self, config: dict):
        """
        Initialize wakeword detector.
        
        Args:
            config: Configuration dict with keys:
                - method: "porcupine" or "whisper"
                - keyword: Wakeword to detect (e.g., "yukino")
                - access_key: Picovoice access key (for porcupine method)
                - sensitivity: Porcupine sensitivity 0.0-1.0 (default: 0.5)
                - chunk_duration: Whisper chunk duration in seconds (default: 2.0)
                - check_interval: Whisper check interval in seconds (default: 0.5)
        """
        super().__init__()
        
        if sd is None:
            raise ImportError("sounddevice is not installed")
        
        self._config = config
        self._method = WakewordMethod(config.get("method", "whisper"))
        self._keyword = config.get("keyword", "yukino").lower()
        
        # Threading
        self._running = False
        self._stop_event = threading.Event()
        self._worker_thread: Optional[threading.Thread] = None
        
        # Audio stream
        self._stream: Optional[sd.InputStream] = None
        self._audio_queue: queue.Queue = queue.Queue()
        
        # Method-specific initialization
        if self._method == WakewordMethod.PORCUPINE:
            self._init_porcupine()
        else:
            self._init_whisper()
        
        logger.info(f"Wakeword detector initialized (method: {self._method.value})")
    
    def _init_porcupine(self) -> None:
        """Initialize Porcupine wakeword detection."""
        if pvporcupine is None:
            raise ImportError(
                "pvporcupine is not installed. "
                "Install with: pip install pvporcupine"
            )
        
        access_key = self._config.get("access_key")
        if not access_key:
            raise ValueError(
                "Picovoice access key required for Porcupine method. "
                "Get from: https://console.picovoice.ai/"
            )
        
        sensitivity = self._config.get("sensitivity", 0.5)
        
        try:
            # Create Porcupine instance with built-in keywords
            # Porcupine doesn't have "yukino" built-in, so we use a similar keyword
            # In production, you'd create a custom keyword file
            self._porcupine = pvporcupine.create(
                access_key=access_key,
                keywords=["hey siri"],  # Placeholder - user should create custom keyword
                sensitivities=[sensitivity]
            )
            
            self._sample_rate = self._porcupine.sample_rate
            self._frame_length = self._porcupine.frame_length
            
            logger.info(f"Porcupine initialized (sample_rate: {self._sample_rate})")
            logger.warning(
                "Using 'hey siri' keyword as placeholder. "
                "Create custom 'yukino' keyword at: https://console.picovoice.ai/"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize Porcupine: {e}", exc_info=True)
            raise
    
    def _init_whisper(self) -> None:
        """Initialize Whisper-based wakeword detection."""
        if whisper is None:
            raise ImportError("openai-whisper is not installed")
        
        self._sample_rate = 16000
        self._chunk_duration = self._config.get("chunk_duration", 2.0)
        self._check_interval = self._config.get("check_interval", 0.5)
        
        logger.info("Loading Whisper model for wakeword detection...")
        try:
            # Use tiny model for fast, low-resource wakeword detection
            self._whisper_model = whisper.load_model("tiny.en", device="cpu")
            logger.info("Whisper model loaded")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {e}", exc_info=True)
            raise
    
    def start(self) -> None:
        """Start wakeword detection in background."""
        if self._running:
            logger.warning("Wakeword detector already running")
            return
        
        logger.info("Starting wakeword detection")
        
        self._running = True
        self._stop_event.clear()
        
        # Start audio stream
        self._start_audio_stream()
        
        # Start worker thread
        if self._method == WakewordMethod.PORCUPINE:
            target = self._porcupine_worker
        else:
            target = self._whisper_worker
        
        self._worker_thread = threading.Thread(
            target=target,
            daemon=True,
            name="Wakeword-Worker"
        )
        self._worker_thread.start()
        
        logger.info("Wakeword detection started")
    
    def stop(self) -> None:
        """Stop wakeword detection."""
        if not self._running:
            return
        
        logger.info("Stopping wakeword detection")
        
        self._running = False
        self._stop_event.set()
        
        # Stop audio stream
        self._stop_audio_stream()
        
        # Wait for worker thread
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)
        
        logger.info("Wakeword detection stopped")
    
    def _start_audio_stream(self) -> None:
        """Start audio input stream."""
        try:
            if self._method == WakewordMethod.PORCUPINE:
                # Porcupine requires specific frame length
                blocksize = self._frame_length
            else:
                # Whisper uses standard frame size
                blocksize = int(self._sample_rate * 0.1)  # 100ms frames
            
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=1,
                dtype=np.int16,
                blocksize=blocksize,
                callback=self._audio_callback
            )
            self._stream.start()
            logger.debug("Wakeword audio stream started")
            
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
                logger.debug("Wakeword audio stream stopped")
            except Exception as e:
                logger.warning(f"Error stopping audio stream: {e}")
    
    def _audio_callback(self, indata, frames, time_info, status) -> None:
        """Audio stream callback - queue audio data."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        audio_data = indata.copy()
        self._audio_queue.put(audio_data)
    
    def _porcupine_worker(self) -> None:
        """Worker thread for Porcupine wakeword detection."""
        logger.debug("Porcupine worker thread started")
        
        while not self._stop_event.is_set():
            try:
                # Get audio frame
                audio_frame = self._audio_queue.get(timeout=0.1)
                
                # Convert to required format
                pcm = audio_frame.flatten()
                
                # Process with Porcupine
                keyword_index = self._porcupine.process(pcm)
                
                if keyword_index >= 0:
                    logger.info("Wakeword detected by Porcupine!")
                    
                    # Emit signal
                    try:
                        self.wakeword_detected.emit()
                    except:
                        pass
                    
                    # Small delay to avoid duplicate detections
                    time.sleep(1.0)
            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in Porcupine worker: {e}", exc_info=True)
        
        # Clean up
        if hasattr(self, '_porcupine'):
            self._porcupine.delete()
        
        logger.debug("Porcupine worker thread stopped")
    
    def _whisper_worker(self) -> None:
        """Worker thread for Whisper-based wakeword detection."""
        logger.debug("Whisper worker thread started")
        
        chunk_frames = int(self._sample_rate * self._chunk_duration)
        audio_buffer = []
        
        while not self._stop_event.is_set():
            try:
                # Collect audio chunks
                audio_frame = self._audio_queue.get(timeout=0.1)
                audio_buffer.append(audio_frame)
                
                # Check if we have enough audio
                total_frames = sum(len(frame) for frame in audio_buffer)
                
                if total_frames >= chunk_frames:
                    # Process accumulated audio
                    audio_data = np.concatenate(audio_buffer)
                    audio_buffer.clear()
                    
                    # Trim to exact chunk size
                    audio_data = audio_data[:chunk_frames]
                    
                    # Convert to float32 for Whisper
                    audio_float = audio_data.astype(np.float32) / 32768.0
                    
                    # Transcribe
                    result = self._whisper_model.transcribe(
                        audio_float,
                        language="en",
                        fp16=False
                    )
                    
                    transcript = result["text"].strip().lower()
                    
                    # Check if keyword is in transcript
                    if self._keyword in transcript:
                        logger.info(f"Wakeword detected by Whisper: '{transcript}'")
                        
                        # Emit signal
                        try:
                            self.wakeword_detected.emit()
                        except:
                            pass
                        
                        # Delay to avoid duplicate detections
                        time.sleep(1.0)
                        audio_buffer.clear()
                    
                    # Small delay between checks
                    time.sleep(self._check_interval)
            
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in Whisper worker: {e}", exc_info=True)
        
        logger.debug("Whisper worker thread stopped")
    
    def is_running(self) -> bool:
        """Check if wakeword detection is running."""
        return self._running
    
    def shutdown(self) -> None:
        """Clean shutdown of wakeword detector."""
        logger.info("Shutting down wakeword detector")
        
        self.stop()
        
        # Clean up models
        if hasattr(self, '_whisper_model'):
            try:
                del self._whisper_model
            except:
                pass
        
        logger.info("Wakeword detector shut down")


def create_wakeword_detector(config: dict) -> WakewordDetector:
    """
    Factory function to create wakeword detector.
    
    Args:
        config: Wakeword configuration dict
    
    Returns:
        Initialized WakewordDetector instance
    """
    return WakewordDetector(config)

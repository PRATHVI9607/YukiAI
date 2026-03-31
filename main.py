#!/usr/bin/env python3
"""
Yuki AI Voice Assistant - Main Entry Point

Wires together all components for a voice-only AI assistant:
- Status window UI with system tray
- LuxTTS voice synthesis
- Whisper speech recognition
- OpenRouter LLM brain
- Wakeword detection
- Action execution with undo
"""

import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QThread, pyqtSignal, QObject, QTimer
import yaml
from dotenv import load_dotenv

# Add yuki package to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import core systems
from yuki.core.listener import SpeechListener
from yuki.core.wakeword import WakewordDetector
from yuki.core.brain import YukiBrain
from yuki.core.action_router import ActionRouter
from yuki.core.undo_stack import UndoStack
from yuki.core.tts import create_tts_engine

# Import UI
from yuki.ui.status_window import create_status_window

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / 'yuki' / 'yuki.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('main')


class ConversationManager(QObject):
    """Manages conversation flow and component coordination"""
    
    # Internal signals
    _show_window_signal = pyqtSignal()
    _hide_window_signal = pyqtSignal()
    _update_status_signal = pyqtSignal(str)
    
    def __init__(self, config: dict, status_window, tts_engine, brain, action_router, undo_stack):
        super().__init__()
        self.config = config
        self.status_window = status_window
        self.tts_engine = tts_engine
        self.brain = brain
        self.action_router = action_router
        self.undo_stack = undo_stack
        
        # Conversation state
        self.is_active = False
        self.conversation_timeout_seconds = config.get('ui', {}).get('conversation_timeout_seconds', 10)
        
        # Timeout timer
        self.timeout_timer = QTimer()
        self.timeout_timer.setSingleShot(True)
        self.timeout_timer.timeout.connect(self._on_conversation_timeout)
        
        # Connect internal signals to window (thread-safe)
        self._show_window_signal.connect(self.status_window.show_window)
        self._hide_window_signal.connect(self.status_window.hide_window)
        self._update_status_signal.connect(self.status_window.set_status)
        
        logger.info("Conversation manager initialized")
    
    def start_conversation(self):
        """Start a new conversation (triggered by wakeword)"""
        if self.is_active:
            logger.debug("Conversation already active, resetting timeout")
            self._reset_timeout()
            return
        
        self.is_active = True
        self._show_window_signal.emit()
        self._update_status_signal.emit("listening")
        
        # Play wakeword chime if configured
        audio_config = self.config.get('audio', {})
        if audio_config.get('wakeword_chime'):
            logger.info("Playing wakeword chime")
            # TODO: Implement audio cue system with pygame.mixer
        
        self._reset_timeout()
        logger.info("Conversation started")
    
    def process_user_speech(self, transcript: str):
        """Process user speech and get Yuki's response"""
        if not transcript or not transcript.strip():
            logger.warning("Empty transcript received")
            return
        
        # Add to UI
        self.status_window.add_user_message(transcript)
        
        # Think state
        self._update_status_signal.emit("thinking")
        
        # Get LLM response (generator yields chunks)
        try:
            full_response = ""
            for chunk in self.brain.ask(transcript):
                full_response += chunk
            
            if not full_response:
                logger.error("Empty response from brain")
                self._speak("...I have nothing to say to that.")
                return
            
            # Add to UI
            self.status_window.add_yuki_message(full_response)
            
            # Check if response contains JSON intent (action request)
            if full_response.strip().startswith('{'):
                try:
                    import json
                    intent = json.loads(full_response)
                    if 'intent' in intent and intent['intent'] != 'chat':
                        logger.info(f"Action detected: {intent['intent']}")
                        self._handle_action(intent)
                        return
                except json.JSONDecodeError:
                    pass  # Not JSON, treat as regular speech
            
            # Just speak the response
            self._speak(full_response)
        
        except Exception as e:
            logger.error(f"Error processing speech: {e}", exc_info=True)
            self._speak("Ara...something went wrong. Try again.")
        
        finally:
            self._reset_timeout()
    
    def _handle_action(self, intent: dict):
        """Execute an action based on intent"""
        try:
            # Route intent through action router
            result = self.action_router.route_intent(intent)
            
            if result.get('needs_confirmation'):
                # Speak confirmation message and wait for response
                self._speak(result['confirmation_message'])
                # TODO: Implement confirmation flow with voice input
                return
            
            if result.get('success'):
                self._speak(result.get('message', "Done."))
            else:
                self._speak(result.get('message', f"...failed. {result.get('error', '')}"))
        
        except Exception as e:
            logger.error(f"Action execution error: {e}", exc_info=True)
            self._speak("The action failed. As expected.")
    
    def _speak(self, text: str):
        """Speak text using TTS"""
        self._update_status_signal.emit("speaking")
        
        try:
            self.tts_engine.speak(text, streaming=True)
            # Note: TTS engine will emit speaking_stopped signal when done
        except Exception as e:
            logger.error(f"TTS error: {e}", exc_info=True)
            self._update_status_signal.emit("idle")
    
    def _reset_timeout(self):
        """Reset conversation timeout"""
        self.timeout_timer.stop()
        self.timeout_timer.start(self.conversation_timeout_seconds * 1000)
    
    def _on_conversation_timeout(self):
        """Handle conversation timeout (end conversation)"""
        if not self.is_active:
            return
        
        logger.info("Conversation timeout reached")
        
        # Say goodbye
        goodbye_messages = [
            "...fine. Call if you need me.",
            "I'll be here. Not that I'm waiting.",
            "Try not to break anything.",
            "...back to work, then."
        ]
        import random
        goodbye = random.choice(goodbye_messages)
        
        self._speak(goodbye)
        
        # Wait for TTS to finish, then hide
        # Note: This is a simple delay; in production, should wait for TTS signal
        QTimer.singleShot(3000, self._end_conversation)
    
    def _end_conversation(self):
        """End conversation and hide window"""
        self.is_active = False
        self._update_status_signal.emit("idle")
        self._hide_window_signal.emit()
        logger.info("Conversation ended")


class YukiApplication:
    """Main application coordinator"""
    
    def __init__(self, config_path: str = None):
        # Load configuration
        if config_path is None:
            config_path = project_root / 'yuki' / 'config.yaml'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        logger.info(f"Loaded config from {config_path}")
        
        # Load environment variables
        env_path = project_root / 'yuki' / '.env'
        if env_path.exists():
            load_dotenv(env_path)
            logger.info("Loaded environment variables")
        else:
            logger.warning(f".env file not found at {env_path}")
        
        # Initialize Qt application
        self.qt_app = QApplication(sys.argv)
        self.qt_app.setApplicationName("Yuki AI")
        self.qt_app.setQuitOnLastWindowClosed(False)  # Keep running in tray
        
        # Initialize components
        logger.info("Initializing components...")
        self._init_components()
        self._connect_signals()
        
        logger.info("Yuki AI initialized successfully!")
    
    def _init_components(self):
        """Initialize all system components"""
        # TTS Engine
        logger.info("Initializing TTS engine...")
        self.tts_engine = create_tts_engine(self.config)
        
        # UI
        logger.info("Creating status window...")
        self.status_window = create_status_window(self.config)
        
        # Brain (LLM)
        logger.info("Initializing brain...")
        memory_dir = project_root / 'yuki' / 'memory'
        memory_dir.mkdir(parents=True, exist_ok=True)
        self.brain = YukiBrain(self.config.get('llm', {}), memory_dir)
        
        # Undo stack
        logger.info("Initializing undo stack...")
        self.undo_stack = UndoStack()
        
        # Action router
        logger.info("Initializing action router...")
        self.action_router = ActionRouter(self.undo_stack)
        
        # Conversation manager
        logger.info("Initializing conversation manager...")
        self.conversation_manager = ConversationManager(
            self.config,
            self.status_window,
            self.tts_engine,
            self.brain,
            self.action_router,
            self.undo_stack
        )
        
        # Speech listener
        logger.info("Initializing speech listener...")
        self.voice_listener = SpeechListener(self.config)
        
        # Wakeword detector
        logger.info("Initializing wakeword detector...")
        self.wakeword_detector = WakewordDetector(self.config)
    
    def _connect_signals(self):
        """Connect Qt signals between components"""
        logger.info("Connecting signals...")
        
        # Wakeword detection → Start conversation
        self.wakeword_detector.wakeword_detected.connect(
            self.conversation_manager.start_conversation
        )
        
        # Wakeword detection → Start listening
        self.wakeword_detector.wakeword_detected.connect(
            self.voice_listener.start_listening
        )
        
        # Voice listener → Process speech
        self.voice_listener.transcript_ready.connect(
            self.conversation_manager.process_user_speech
        )
        
        # TTS signals → Update UI
        self.tts_engine.speaking_started.connect(
            lambda: self.status_window.set_status("speaking")
        )
        self.tts_engine.speaking_stopped.connect(
            lambda: self.status_window.set_status("idle")
        )
        
        # UI signals → Actions
        self.status_window.mute_toggled.connect(
            self._on_mute_toggled
        )
        self.status_window.undo_requested.connect(
            self._on_undo_requested
        )
        
        logger.info("All signals connected")
    
    def _on_mute_toggled(self, is_muted: bool):
        """Handle mute button toggle"""
        if is_muted:
            logger.info("Muting microphone")
            self.wakeword_detector.stop()
            self.voice_listener.stop_listening()
            self.status_window.set_status("muted")
        else:
            logger.info("Unmuting microphone")
            self.wakeword_detector.start()
            self.status_window.set_status("idle")
    
    def _on_undo_requested(self):
        """Handle undo button press"""
        logger.info("Undo requested by user")
        
        if self.undo_stack.is_empty():
            logger.info("Undo stack is empty")
            self.status_window.add_yuki_message("...there's nothing to undo.")
            return
        
        try:
            success = self.undo_stack.pop_and_undo()
            if success:
                self.status_window.add_yuki_message("...undone.")
                logger.info("Undo successful")
            else:
                self.status_window.add_yuki_message("Undo failed. Predictable.")
                logger.warning("Undo failed")
        except Exception as e:
            logger.error(f"Undo error: {e}", exc_info=True)
            self.status_window.add_yuki_message("The undo failed catastrophically.")
    
    def run(self):
        """Start the application"""
        logger.info("Starting Yuki AI...")
        
        # Start wakeword detection
        logger.info("Starting wakeword detector...")
        self.wakeword_detector.start()
        
        # Show status window (initially hidden by default)
        # User can show via system tray
        logger.info("Yuki is now listening for wakeword...")
        logger.info("Say 'Hey Yuki' to start a conversation")
        
        # Run Qt event loop
        exit_code = self.qt_app.exec()
        
        # Cleanup on exit
        logger.info("Shutting down...")
        self.wakeword_detector.stop()
        self.voice_listener.stop_listening()
        self.tts_engine.stop()
        
        logger.info("Yuki AI shut down gracefully")
        return exit_code


def main():
    """Entry point"""
    try:
        # Check for required environment variables
        if not os.getenv('OPENROUTER_API_KEY'):
            logger.error("OPENROUTER_API_KEY not found in environment!")
            logger.error("Please create yuki/.env with your OpenRouter API key")
            logger.error("Get a free key at: https://openrouter.ai/keys")
            sys.exit(1)
        
        # Create and run application
        app = YukiApplication()
        sys.exit(app.run())
    
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()

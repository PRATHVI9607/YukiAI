"""
Chat panel widget for conversation display.

Scrollable chat history with user and Yukino messages.
"""

import logging
from typing import List, Dict
from datetime import datetime

try:
    from PyQt6.QtWidgets import (
        QWidget, QVBoxLayout, QScrollArea, QLabel, QFrame
    )
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont
except ImportError:
    QWidget = object
    QVBoxLayout = None
    QScrollArea = None
    QLabel = None
    QFrame = None
    Qt = None
    pyqtSignal = None
    QTimer = None
    QFont = None

logger = logging.getLogger(__name__)


class MessageBubble(QFrame):
    """
    A single message bubble.
    
    Displays speaker name, message text, and timestamp.
    """
    
    def __init__(self, speaker: str, message: str, is_user: bool):
        """
        Initialize message bubble.
        
        Args:
            speaker: Speaker name ("User" or "Yukino")
            message: Message text
            is_user: True if user message, False if Yukino
        """
        super().__init__()
        
        self._speaker = speaker
        self._message = message
        self._is_user = is_user
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """Setup bubble UI."""
        # Frame properties
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)
        
        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        # Speaker label
        speaker_label = QLabel(self._speaker)
        speaker_font = QFont()
        speaker_font.setBold(True)
        speaker_font.setPointSize(10)
        speaker_label.setFont(speaker_font)
        
        if self._is_user:
            speaker_label.setStyleSheet("color: #88AAFF;")
        else:
            speaker_label.setStyleSheet("color: #FF88AA;")
        
        layout.addWidget(speaker_label)
        
        # Message label
        message_label = QLabel(self._message)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        message_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(message_label)
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        time_label = QLabel(timestamp)
        time_label.setStyleSheet("color: #888888; font-size: 8pt;")
        layout.addWidget(time_label, alignment=Qt.AlignmentFlag.AlignRight)
        
        # Style the bubble
        if self._is_user:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: rgba(50, 60, 80, 200);
                    border-radius: 10px;
                    border: 1px solid rgba(100, 120, 150, 100);
                }
            """)
        else:
            self.setStyleSheet("""
                MessageBubble {
                    background-color: rgba(60, 50, 70, 200);
                    border-radius: 10px;
                    border: 1px solid rgba(120, 100, 130, 100);
                }
            """)


class ChatPanel(QWidget):
    """
    Chat panel widget for conversation display.
    
    Features:
    - Scrollable message history
    - User and Yukino message bubbles
    - Auto-scroll to bottom on new messages
    - Message limit (keeps last N messages)
    - Clear history function
    
    Signals:
        message_added: Emitted when new message is added
    """
    
    message_added = pyqtSignal(str, str)  # speaker, message
    
    def __init__(self, config: dict):
        """
        Initialize chat panel.
        
        Args:
            config: Chat panel configuration
        """
        super().__init__()
        
        self._config = config
        
        # Settings
        self._max_messages = config.get("max_messages", 50)
        self._auto_scroll = config.get("auto_scroll", True)
        self._show_timestamps = config.get("show_timestamps", True)
        
        # Message history
        self._messages: List[Dict] = []
        
        # UI elements
        self._scroll_area: Optional[QScrollArea] = None
        self._message_container: Optional[QWidget] = None
        self._message_layout: Optional[QVBoxLayout] = None
        
        self._setup_ui()
        
        logger.info("ChatPanel initialized")
    
    def _setup_ui(self) -> None:
        """Setup chat panel UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroll area
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        
        # Message container
        self._message_container = QWidget()
        self._message_layout = QVBoxLayout(self._message_container)
        self._message_layout.setContentsMargins(5, 5, 5, 5)
        self._message_layout.setSpacing(8)
        self._message_layout.addStretch()
        
        # Set container to scroll area
        self._scroll_area.setWidget(self._message_container)
        
        # Add scroll area to main layout
        main_layout.addWidget(self._scroll_area)
        
        # Style
        self.setStyleSheet("""
            QScrollArea {
                background-color: rgba(20, 20, 30, 180);
                border: 1px solid rgba(80, 80, 100, 100);
                border-radius: 5px;
            }
            QScrollBar:vertical {
                background: rgba(30, 30, 40, 150);
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: rgba(100, 100, 120, 200);
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        logger.debug("Chat panel UI setup complete")
    
    def add_message(self, speaker: str, message: str) -> None:
        """
        Add a message to the chat.
        
        Args:
            speaker: Speaker name ("User" or "Yukino")
            message: Message text
        """
        if not message.strip():
            return
        
        # Determine if user message
        is_user = speaker.lower() == "user"
        
        # Create message bubble
        bubble = MessageBubble(speaker, message, is_user)
        
        # Insert before stretch
        count = self._message_layout.count()
        self._message_layout.insertWidget(count - 1, bubble)
        
        # Store message
        self._messages.append({
            "speaker": speaker,
            "message": message,
            "timestamp": datetime.now(),
            "is_user": is_user
        })
        
        # Enforce message limit
        if len(self._messages) > self._max_messages:
            self._remove_oldest_message()
        
        # Auto-scroll to bottom
        if self._auto_scroll:
            QTimer.singleShot(50, self._scroll_to_bottom)
        
        # Emit signal
        self.message_added.emit(speaker, message)
        
        logger.debug(f"Message added: {speaker}: {message[:50]}...")
    
    def _remove_oldest_message(self) -> None:
        """Remove the oldest message from display."""
        if self._message_layout.count() > 1:
            # Get first widget (oldest message)
            item = self._message_layout.itemAt(0)
            if item and item.widget():
                widget = item.widget()
                self._message_layout.removeWidget(widget)
                widget.deleteLater()
        
        # Remove from history
        if self._messages:
            self._messages.pop(0)
    
    def _scroll_to_bottom(self) -> None:
        """Scroll to the bottom of the chat."""
        scrollbar = self._scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def add_user_message(self, message: str) -> None:
        """
        Add a user message.
        
        Args:
            message: User message text
        """
        self.add_message("User", message)
    
    def add_yukino_message(self, message: str) -> None:
        """
        Add a Yukino message.
        
        Args:
            message: Yukino message text
        """
        self.add_message("Yukino", message)
    
    def add_system_message(self, message: str) -> None:
        """
        Add a system message.
        
        Args:
            message: System message text
        """
        self.add_message("System", message)
    
    def clear_history(self) -> None:
        """Clear all messages."""
        # Remove all widgets except stretch
        while self._message_layout.count() > 1:
            item = self._message_layout.itemAt(0)
            if item and item.widget():
                widget = item.widget()
                self._message_layout.removeWidget(widget)
                widget.deleteLater()
        
        # Clear history
        self._messages.clear()
        
        logger.info("Chat history cleared")
    
    def get_messages(self) -> List[Dict]:
        """Get all messages."""
        return self._messages.copy()
    
    def get_message_count(self) -> int:
        """Get number of messages."""
        return len(self._messages)
    
    def set_auto_scroll(self, enabled: bool) -> None:
        """Enable or disable auto-scroll."""
        self._auto_scroll = enabled
        logger.debug(f"Auto-scroll: {'enabled' if enabled else 'disabled'}")
    
    def export_history(self) -> str:
        """
        Export chat history as text.
        
        Returns:
            Formatted chat history
        """
        lines = []
        
        for msg in self._messages:
            timestamp = msg["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            speaker = msg["speaker"]
            message = msg["message"]
            lines.append(f"[{timestamp}] {speaker}: {message}")
        
        return "\n".join(lines)


def create_chat_panel(config: dict) -> ChatPanel:
    """
    Factory function to create chat panel.
    
    Args:
        config: Chat panel configuration
    
    Returns:
        Initialized ChatPanel instance
    """
    return ChatPanel(config)

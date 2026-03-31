"""
Status bar widget for Yuki.

Displays current state (idle/listening/thinking/speaking) and system info.
"""

import logging
from typing import Optional
from enum import Enum

try:
    from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel
    from PyQt6.QtCore import Qt, pyqtSignal, QTimer
    from PyQt6.QtGui import QFont
except ImportError:
    QWidget = object
    QHBoxLayout = None
    QLabel = None
    Qt = None
    pyqtSignal = None
    QTimer = None
    QFont = None

logger = logging.getLogger(__name__)


class YukiStatus(Enum):
    """Yuki status states."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"


class StatusBar(QWidget):
    """
    Status bar widget.
    
    Features:
    - Status indicator with color coding
    - Status text display
    - Optional info text (e.g., model name, action in progress)
    - Pulsing animation for active states
    
    Signals:
        status_changed: Emitted when status changes
    """
    
    status_changed = pyqtSignal(str)  # status name
    
    # Status colors (RGBA)
    STATUS_COLORS = {
        YukiStatus.IDLE: "#88AA88",       # Green
        YukiStatus.LISTENING: "#8888FF",  # Blue
        YukiStatus.THINKING: "#FFAA44",   # Orange
        YukiStatus.SPEAKING: "#FF88AA",   # Pink
        YukiStatus.ERROR: "#FF4444",      # Red
    }
    
    # Status display text
    STATUS_TEXT = {
        YukiStatus.IDLE: "Idle",
        YukiStatus.LISTENING: "Listening...",
        YukiStatus.THINKING: "Thinking...",
        YukiStatus.SPEAKING: "Speaking...",
        YukiStatus.ERROR: "Error",
    }
    
    def __init__(self, config: dict):
        """
        Initialize status bar.
        
        Args:
            config: Status bar configuration
        """
        super().__init__()
        
        self._config = config
        
        # Settings
        self._enable_animation = config.get("enable_animation", True)
        self._show_info = config.get("show_info", True)
        
        # Current state
        self._current_status = YukiStatus.IDLE
        self._info_text = ""
        
        # Animation
        self._animation_timer: Optional[QTimer] = None
        self._animation_phase = 0.0
        
        # UI elements
        self._indicator_label: Optional[QLabel] = None
        self._status_label: Optional[QLabel] = None
        self._info_label: Optional[QLabel] = None
        
        self._setup_ui()
        self._setup_animation()
        
        logger.info("StatusBar initialized")
    
    def _setup_ui(self) -> None:
        """Setup status bar UI."""
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Status indicator (colored dot)
        self._indicator_label = QLabel("●")
        indicator_font = QFont()
        indicator_font.setPointSize(14)
        self._indicator_label.setFont(indicator_font)
        self._update_indicator_color()
        layout.addWidget(self._indicator_label)
        
        # Status text
        self._status_label = QLabel(self.STATUS_TEXT[YukiStatus.IDLE])
        status_font = QFont()
        status_font.setBold(True)
        status_font.setPointSize(10)
        self._status_label.setFont(status_font)
        self._status_label.setStyleSheet("color: #CCCCCC;")
        layout.addWidget(self._status_label)
        
        # Spacer
        layout.addStretch()
        
        # Info label
        if self._show_info:
            self._info_label = QLabel("")
            info_font = QFont()
            info_font.setPointSize(9)
            self._info_label.setFont(info_font)
            self._info_label.setStyleSheet("color: #888888;")
            layout.addWidget(self._info_label)
        
        # Style
        self.setStyleSheet("""
            StatusBar {
                background-color: rgba(30, 30, 40, 200);
                border: 1px solid rgba(80, 80, 100, 100);
                border-radius: 5px;
            }
        """)
        
        # Fixed height
        self.setFixedHeight(40)
        
        logger.debug("Status bar UI setup complete")
    
    def _setup_animation(self) -> None:
        """Setup pulsing animation for active states."""
        if not self._enable_animation or QTimer is None:
            return
        
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_animation)
        self._animation_timer.start(50)  # 20fps
        
        logger.debug("Status animation started")
    
    def _update_animation(self) -> None:
        """Update pulsing animation."""
        # Only pulse for active states
        if self._current_status in [YukiStatus.LISTENING, YukiStatus.THINKING, YukiStatus.SPEAKING]:
            self._animation_phase += 0.1
            if self._animation_phase > 6.28:  # 2*pi
                self._animation_phase = 0.0
            
            # Calculate opacity (pulse between 0.5 and 1.0)
            import math
            opacity = 0.75 + 0.25 * math.sin(self._animation_phase)
            
            # Apply to indicator
            color = self.STATUS_COLORS[self._current_status]
            self._indicator_label.setStyleSheet(f"color: {color}; opacity: {opacity};")
        else:
            # Static for idle/error
            self._update_indicator_color()
    
    def _update_indicator_color(self) -> None:
        """Update indicator color based on current status."""
        color = self.STATUS_COLORS[self._current_status]
        self._indicator_label.setStyleSheet(f"color: {color};")
    
    def set_status(self, status: YukiStatus) -> None:
        """
        Set current status.
        
        Args:
            status: YukiStatus enum value
        """
        if status == self._current_status:
            return
        
        old_status = self._current_status
        self._current_status = status
        
        # Update text
        self._status_label.setText(self.STATUS_TEXT[status])
        
        # Update color
        self._update_indicator_color()
        
        # Emit signal
        self.status_changed.emit(status.value)
        
        logger.debug(f"Status: {old_status.value} -> {status.value}")
    
    def set_idle(self) -> None:
        """Set status to idle."""
        self.set_status(YukiStatus.IDLE)
    
    def set_listening(self) -> None:
        """Set status to listening."""
        self.set_status(YukiStatus.LISTENING)
    
    def set_thinking(self) -> None:
        """Set status to thinking."""
        self.set_status(YukiStatus.THINKING)
    
    def set_speaking(self) -> None:
        """Set status to speaking."""
        self.set_status(YukiStatus.SPEAKING)
    
    def set_error(self) -> None:
        """Set status to error."""
        self.set_status(YukiStatus.ERROR)
    
    def set_info(self, text: str) -> None:
        """
        Set info text.
        
        Args:
            text: Info text to display
        """
        if not self._show_info or not self._info_label:
            return
        
        self._info_text = text
        self._info_label.setText(text)
        
        logger.debug(f"Info text: {text}")
    
    def clear_info(self) -> None:
        """Clear info text."""
        self.set_info("")
    
    def get_status(self) -> YukiStatus:
        """Get current status."""
        return self._current_status
    
    def get_info(self) -> str:
        """Get current info text."""
        return self._info_text


def create_status_bar(config: dict) -> StatusBar:
    """
    Factory function to create status bar.
    
    Args:
        config: Status bar configuration
    
    Returns:
        Initialized StatusBar instance
    """
    return StatusBar(config)

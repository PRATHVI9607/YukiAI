"""
Minimal status window for Yuki AI voice assistant.

Simple text-based window showing conversation history and current status.
Replaces the complex overlay UI for voice-only architecture.
"""

import logging
from typing import Optional
from datetime import datetime

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QLabel, QSystemTrayIcon, QMenu
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QIcon, QTextCursor, QFont, QAction

logger = logging.getLogger(__name__)


class StatusWindow(QMainWindow):
    """
    Minimal status window for Yuki voice assistant.
    
    Features:
    - Simple text display of conversation history
    - Status indicator (Listening/Thinking/Speaking)
    - Mute and Undo buttons
    - System tray integration
    - Auto-hide on conversation timeout
    - Draggable window
    
    Signals:
        mute_toggled: Emitted when mute button is clicked (bool: is_muted)
        undo_requested: Emitted when undo button is clicked
        window_closing: Emitted when window is being closed (not just hidden)
    """
    
    # Qt Signals
    mute_toggled = pyqtSignal(bool)  # is_muted
    undo_requested = pyqtSignal()
    window_closing = pyqtSignal()
    
    def __init__(
        self,
        width: int = 400,
        height: int = 300,
        position: str = "bottom_right",
        start_hidden: bool = True,
        always_on_top: bool = False
    ):
        """
        Initialize status window.
        
        Args:
            width: Window width in pixels
            height: Window height in pixels
            position: Window position ("bottom_right", "bottom_left", "top_right", "top_left", "center")
            start_hidden: Start with window hidden
            always_on_top: Keep window always on top
        """
        super().__init__()
        
        self._width = width
        self._height = height
        self._position = position
        self._always_on_top = always_on_top
        self._is_muted = False
        self._dragging = False
        self._drag_position = QPoint()
        
        # Setup UI
        self._setup_window()
        self._setup_ui()
        self._setup_system_tray()
        
        # Position window
        self._position_window()
        
        # Hide if configured
        if start_hidden:
            self.hide()
        
        logger.info(f"Status window initialized ({width}x{height}, position: {position})")
    
    def _setup_window(self):
        """Configure main window properties."""
        self.setWindowTitle("Yuki")
        self.resize(self._width, self._height)
        
        # Window flags
        flags = Qt.WindowType.Window
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        # Enable mouse tracking for dragging
        self.setMouseTracking(True)
    
    def _setup_ui(self):
        """Create UI components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        central_widget.setLayout(layout)
        
        # Status indicator
        self._status_label = QLabel("● Idle")
        self._status_label.setObjectName("statusLabel")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(10)
        font.setBold(True)
        self._status_label.setFont(font)
        layout.addWidget(self._status_label)
        
        # Conversation history
        self._history_text = QTextEdit()
        self._history_text.setObjectName("historyText")
        self._history_text.setReadOnly(True)
        self._history_text.setPlaceholderText("Conversation history will appear here...")
        layout.addWidget(self._history_text, stretch=1)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Mute button
        self._mute_button = QPushButton("🔊 Mute")
        self._mute_button.setObjectName("muteButton")
        self._mute_button.clicked.connect(self._on_mute_clicked)
        button_layout.addWidget(self._mute_button)
        
        # Undo button
        self._undo_button = QPushButton("↶ Undo")
        self._undo_button.setObjectName("undoButton")
        self._undo_button.clicked.connect(self._on_undo_clicked)
        button_layout.addWidget(self._undo_button)
        
        layout.addLayout(button_layout)
        
        # Apply stylesheet
        self._apply_styles()
    
    def _setup_system_tray(self):
        """Setup system tray icon and menu."""
        self._tray_icon = QSystemTrayIcon(self)
        
        # Use a default icon (you can replace with custom icon)
        # For now, using the application icon
        icon = self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon)
        self._tray_icon.setIcon(icon)
        self._tray_icon.setToolTip("Yuki AI Assistant")
        
        # Create tray menu
        tray_menu = QMenu()
        
        show_action = QAction("Show Window", self)
        show_action.triggered.connect(self._show_window)
        tray_menu.addAction(show_action)
        
        hide_action = QAction("Hide Window", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)
        
        tray_menu.addSeparator()
        
        mute_action = QAction("Toggle Mute", self)
        mute_action.triggered.connect(self._on_mute_clicked)
        tray_menu.addAction(mute_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self._on_quit)
        tray_menu.addAction(quit_action)
        
        self._tray_icon.setContextMenu(tray_menu)
        self._tray_icon.activated.connect(self._on_tray_activated)
        self._tray_icon.show()
        
        logger.info("System tray icon created")
    
    def _position_window(self):
        """Position window based on configuration."""
        screen = self.screen().availableGeometry()
        
        if self._position == "bottom_right":
            x = screen.width() - self._width - 20
            y = screen.height() - self._height - 50
        elif self._position == "bottom_left":
            x = 20
            y = screen.height() - self._height - 50
        elif self._position == "top_right":
            x = screen.width() - self._width - 20
            y = 50
        elif self._position == "top_left":
            x = 20
            y = 50
        elif self._position == "center":
            x = (screen.width() - self._width) // 2
            y = (screen.height() - self._height) // 2
        else:
            x = screen.width() - self._width - 20
            y = screen.height() - self._height - 50
        
        self.move(x, y)
    
    def _apply_styles(self):
        """Apply basic inline styles (will be overridden by styles.qss)."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a0a14;
            }
            QLabel#statusLabel {
                color: #e8e8f0;
                background-color: #1a1a2e;
                border-radius: 12px;
                padding: 8px;
                min-height: 30px;
            }
            QTextEdit#historyText {
                background-color: #0d0d1a;
                color: #e8e8f0;
                border: 1px solid #3d3060;
                border-radius: 8px;
                padding: 8px;
                font-size: 11pt;
            }
            QPushButton {
                background-color: #1e1e30;
                color: #a78bfa;
                border: 1px solid #3d3060;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 10pt;
                min-height: 30px;
            }
            QPushButton:hover {
                background-color: #2d2050;
            }
            QPushButton#muteButton {
                color: #4ade80;
            }
        """)
    
    # Public API
    
    def set_status(self, status: str):
        """
        Update status indicator.
        
        Args:
            status: "idle", "listening", "thinking", or "speaking"
        """
        status_lower = status.lower()
        
        if status_lower == "idle":
            self._status_label.setText("● Idle")
            self._status_label.setStyleSheet("color: #9ca3af; background-color: #1a1a2e;")
        elif status_lower == "listening":
            self._status_label.setText("● Listening")
            self._status_label.setStyleSheet("color: #4ade80; background-color: #1a3a1a;")
        elif status_lower == "thinking":
            self._status_label.setText("● Thinking")
            self._status_label.setStyleSheet("color: #fbbf24; background-color: #3a2a1a;")
        elif status_lower == "speaking":
            self._status_label.setText("● Speaking")
            self._status_label.setStyleSheet("color: #60a5fa; background-color: #1a2a3a;")
        else:
            self._status_label.setText(f"● {status}")
            self._status_label.setStyleSheet("color: #e8e8f0; background-color: #1a1a2e;")
        
        logger.debug(f"Status updated: {status}")
    
    def add_user_message(self, message: str):
        """
        Add user message to conversation history.
        
        Args:
            message: User's message text
        """
        timestamp = datetime.now().strftime("%H:%M")
        html = f'<div style="text-align: right; margin: 8px 0;"><span style="background-color: #2d1f5e; color: #c9b8ff; padding: 8px 12px; border-radius: 12px 12px 2px 12px; display: inline-block; max-width: 80%;"><b>[{timestamp}] You:</b> {message}</span></div>'
        self._history_text.append(html)
        self._scroll_to_bottom()
    
    def add_yuki_message(self, message: str):
        """
        Add Yuki's message to conversation history.
        
        Args:
            message: Yuki's response text
        """
        timestamp = datetime.now().strftime("%H:%M")
        html = f'<div style="text-align: left; margin: 8px 0;"><span style="background-color: #1a1a2e; color: #e8e8f0; padding: 8px 12px; border-radius: 12px 12px 12px 2px; display: inline-block; max-width: 80%;"><b>[{timestamp}] Yuki:</b> {message}</span></div>'
        self._history_text.append(html)
        self._scroll_to_bottom()
    
    def add_system_message(self, message: str):
        """
        Add system message to conversation history.
        
        Args:
            message: System message text
        """
        timestamp = datetime.now().strftime("%H:%M")
        html = f'<div style="text-align: center; margin: 8px 0;"><span style="background-color: #1e1e30; color: #9ca3af; padding: 4px 8px; border-radius: 8px; display: inline-block; font-size: 9pt;"><i>[{timestamp}] {message}</i></span></div>'
        self._history_text.append(html)
        self._scroll_to_bottom()
    
    def clear_history(self):
        """Clear conversation history."""
        self._history_text.clear()
        logger.info("Conversation history cleared")
    
    def set_mute_state(self, is_muted: bool):
        """
        Set mute button state.
        
        Args:
            is_muted: True if microphone is muted
        """
        self._is_muted = is_muted
        if is_muted:
            self._mute_button.setText("🔇 Unmute")
            self._mute_button.setStyleSheet("""
                QPushButton#muteButton {
                    background-color: #3a1a1a;
                    color: #ef4444;
                }
                QPushButton#muteButton:hover {
                    background-color: #4a2020;
                }
            """)
        else:
            self._mute_button.setText("🔊 Mute")
            self._mute_button.setStyleSheet("""
                QPushButton#muteButton {
                    background-color: #1e1e30;
                    color: #4ade80;
                }
                QPushButton#muteButton:hover {
                    background-color: #2d2050;
                }
            """)
    
    def show_window(self):
        """Show window and bring to front."""
        self.show()
        self.raise_()
        self.activateWindow()
        logger.info("Window shown")
    
    # Event handlers
    
    def _on_mute_clicked(self):
        """Handle mute button click."""
        self._is_muted = not self._is_muted
        self.set_mute_state(self._is_muted)
        self.mute_toggled.emit(self._is_muted)
        logger.info(f"Mute toggled: {self._is_muted}")
    
    def _on_undo_clicked(self):
        """Handle undo button click."""
        self.undo_requested.emit()
        logger.info("Undo requested")
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show_window()
    
    def _show_window(self):
        """Show window from tray menu."""
        self.show_window()
    
    def _on_quit(self):
        """Handle quit action."""
        logger.info("Quit requested from tray menu")
        self.window_closing.emit()
        self._tray_icon.hide()
        self.close()
    
    def _scroll_to_bottom(self):
        """Scroll conversation history to bottom."""
        cursor = self._history_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._history_text.setTextCursor(cursor)
    
    # Window dragging
    
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging."""
        if self._dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            event.accept()
    
    # Override close event
    
    def closeEvent(self, event):
        """
        Override close event to hide instead of quit.
        
        Clicking X hides the window (app continues in tray).
        Use tray menu "Quit" to actually exit.
        """
        event.ignore()
        self.hide()
        logger.info("Window hidden (not closed)")


def create_status_window(config: dict) -> StatusWindow:
    """
    Factory function to create status window from config.
    
    Args:
        config: Configuration dictionary with UI settings
    
    Returns:
        Initialized StatusWindow instance
    """
    ui_config = config.get('ui', {})
    
    window = StatusWindow(
        width=ui_config.get('width', 400),
        height=ui_config.get('height', 300),
        position=ui_config.get('position', 'bottom_right'),
        start_hidden=ui_config.get('start_hidden', True),
        always_on_top=ui_config.get('always_on_top', False)
    )
    
    return window

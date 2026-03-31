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
        self.setWindowTitle("Yuki AI")
        self.resize(self._width, self._height)
        self.setMinimumSize(380, 280)
        
        # Window flags - frameless with rounded corners
        flags = Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint
        if self._always_on_top:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        
        # Transparent background for rounded corners
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Enable mouse tracking for dragging
        self.setMouseTracking(True)
    
    def _setup_ui(self):
        """Create UI components."""
        # Central widget with rounded corners
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        central_widget.setStyleSheet("""
            #centralWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #ffffff,
                    stop: 0.5 #f8f9fa,
                    stop: 1 #f0f2f5
                );
                border-radius: 20px;
                border: 1px solid #e5e7eb;
            }
        """)
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        central_widget.setLayout(layout)
        
        # Title bar with drag handle and close button
        title_bar = QHBoxLayout()
        title_bar.setSpacing(8)
        
        # App title
        title_label = QLabel("✨ Yuki AI")
        title_label.setStyleSheet("""
            color: #6366f1;
            font-size: 14pt;
            font-weight: 700;
            padding: 4px;
        """)
        title_bar.addWidget(title_label)
        
        title_bar.addStretch()
        
        # Minimize button
        minimize_btn = QPushButton("─")
        minimize_btn.setFixedSize(28, 28)
        minimize_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6;
                border: none;
                border-radius: 14px;
                color: #6b7280;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #e5e7eb;
            }
        """)
        minimize_btn.clicked.connect(self.showMinimized)
        title_bar.addWidget(minimize_btn)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #fee2e2;
                border: none;
                border-radius: 14px;
                color: #dc2626;
                font-size: 16pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #fecaca;
            }
        """)
        close_btn.clicked.connect(self.hide)
        title_bar.addWidget(close_btn)
        
        layout.addLayout(title_bar)
        
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
        """Apply professional white gradient theme."""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #ffffff,
                    stop: 0.5 #f8f9fa,
                    stop: 1 #f0f2f5
                );
                border-radius: 16px;
            }
            QWidget {
                background: transparent;
                font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
            }
            QLabel#statusLabel {
                color: #1a1a2e;
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 0,
                    stop: 0 #e8f4f8,
                    stop: 1 #f0f4ff
                );
                border: 1px solid #d1d5db;
                border-radius: 20px;
                padding: 12px 20px;
                min-height: 36px;
                font-size: 12pt;
                font-weight: 600;
            }
            QTextEdit#historyText {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff,
                    stop: 1 #fafbfc
                );
                color: #1f2937;
                border: 1px solid #e5e7eb;
                border-radius: 12px;
                padding: 12px;
                font-size: 11pt;
                line-height: 1.5;
                selection-background-color: #bfdbfe;
            }
            QTextEdit#historyText:focus {
                border: 1px solid #93c5fd;
            }
            QScrollBar:vertical {
                background: #f3f4f6;
                width: 8px;
                border-radius: 4px;
                margin: 4px 2px;
            }
            QScrollBar::handle:vertical {
                background: #d1d5db;
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #9ca3af;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QPushButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff,
                    stop: 1 #f3f4f6
                );
                color: #374151;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 10px 20px;
                font-size: 10pt;
                font-weight: 500;
                min-height: 36px;
            }
            QPushButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f9fafb,
                    stop: 1 #e5e7eb
                );
                border: 1px solid #9ca3af;
            }
            QPushButton:pressed {
                background: #e5e7eb;
            }
            QPushButton#muteButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ecfdf5,
                    stop: 1 #d1fae5
                );
                color: #065f46;
                border: 1px solid #a7f3d0;
            }
            QPushButton#muteButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #d1fae5,
                    stop: 1 #a7f3d0
                );
            }
            QPushButton#undoButton {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #eff6ff,
                    stop: 1 #dbeafe
                );
                color: #1e40af;
                border: 1px solid #93c5fd;
            }
            QPushButton#undoButton:hover {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #dbeafe,
                    stop: 1 #bfdbfe
                );
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
            self._status_label.setStyleSheet("""
                color: #6b7280;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f3f4f6, stop:1 #e5e7eb);
                border: 1px solid #d1d5db; border-radius: 20px; padding: 12px 20px;
                font-size: 12pt; font-weight: 600;
            """)
        elif status_lower == "listening":
            self._status_label.setText("● Listening...")
            self._status_label.setStyleSheet("""
                color: #059669;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d1fae5, stop:1 #a7f3d0);
                border: 1px solid #6ee7b7; border-radius: 20px; padding: 12px 20px;
                font-size: 12pt; font-weight: 600;
            """)
        elif status_lower == "thinking":
            self._status_label.setText("● Thinking...")
            self._status_label.setStyleSheet("""
                color: #d97706;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fef3c7, stop:1 #fde68a);
                border: 1px solid #fcd34d; border-radius: 20px; padding: 12px 20px;
                font-size: 12pt; font-weight: 600;
            """)
        elif status_lower == "speaking":
            self._status_label.setText("● Speaking...")
            self._status_label.setStyleSheet("""
                color: #2563eb;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #dbeafe, stop:1 #bfdbfe);
                border: 1px solid #93c5fd; border-radius: 20px; padding: 12px 20px;
                font-size: 12pt; font-weight: 600;
            """)
        elif status_lower == "muted":
            self._status_label.setText("● Muted")
            self._status_label.setStyleSheet("""
                color: #dc2626;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #fee2e2, stop:1 #fecaca);
                border: 1px solid #fca5a5; border-radius: 20px; padding: 12px 20px;
                font-size: 12pt; font-weight: 600;
            """)
        else:
            self._status_label.setText(f"● {status}")
            self._status_label.setStyleSheet("""
                color: #374151;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f9fafb, stop:1 #f3f4f6);
                border: 1px solid #d1d5db; border-radius: 20px; padding: 12px 20px;
                font-size: 12pt; font-weight: 600;
            """)
        
        logger.debug(f"Status updated: {status}")
    
    def add_user_message(self, message: str):
        """
        Add user message to conversation history.
        
        Args:
            message: User's message text
        """
        timestamp = datetime.now().strftime("%H:%M")
        html = f'''<div style="text-align: right; margin: 10px 0;">
            <span style="background: linear-gradient(135deg, #6366f1, #8b5cf6); 
                         color: white; 
                         padding: 10px 16px; 
                         border-radius: 18px 18px 4px 18px; 
                         display: inline-block; 
                         max-width: 85%;
                         font-size: 11pt;
                         box-shadow: 0 2px 8px rgba(99, 102, 241, 0.2);">
                <b style="font-size: 9pt; opacity: 0.9;">[{timestamp}] You</b><br>{message}
            </span>
        </div>'''
        self._history_text.append(html)
        self._scroll_to_bottom()
    
    def add_yuki_message(self, message: str):
        """
        Add Yuki's message to conversation history.
        
        Args:
            message: Yuki's response text
        """
        timestamp = datetime.now().strftime("%H:%M")
        html = f'''<div style="text-align: left; margin: 10px 0;">
            <span style="background: linear-gradient(135deg, #f8fafc, #f1f5f9); 
                         color: #1e293b; 
                         padding: 10px 16px; 
                         border-radius: 18px 18px 18px 4px; 
                         display: inline-block; 
                         max-width: 85%;
                         font-size: 11pt;
                         border: 1px solid #e2e8f0;
                         box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);">
                <b style="font-size: 9pt; color: #6366f1;">[{timestamp}] Yuki</b><br>{message}
            </span>
        </div>'''
        self._history_text.append(html)
        self._scroll_to_bottom()
    
    def add_system_message(self, message: str):
        """
        Add system message to conversation history.
        
        Args:
            message: System message text
        """
        timestamp = datetime.now().strftime("%H:%M")
        html = f'''<div style="text-align: center; margin: 12px 0;">
            <span style="background: #f1f5f9; 
                         color: #64748b; 
                         padding: 6px 14px; 
                         border-radius: 12px; 
                         display: inline-block; 
                         font-size: 9pt;
                         font-style: italic;">
                {timestamp} • {message}
            </span>
        </div>'''
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
    
    def hide_window(self):
        """Hide window."""
        self.hide()
        logger.info("Window hidden")
    
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

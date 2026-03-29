"""
Main window for Yukino desktop overlay.

Frameless, always-on-top, draggable window with system tray integration.
"""

import logging
from typing import Optional
from pathlib import Path

try:
    from PyQt6.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QSystemTrayIcon, QMenu
    )
    from PyQt6.QtCore import Qt, QPoint, pyqtSignal, QTimer
    from PyQt6.QtGui import QIcon, QAction, QCursor
except ImportError:
    QMainWindow = object
    QWidget = None
    QVBoxLayout = None
    QHBoxLayout = None
    QSystemTrayIcon = None
    QMenu = None
    Qt = None
    QPoint = None
    pyqtSignal = None
    QTimer = None
    QIcon = None
    QAction = None
    QCursor = None

logger = logging.getLogger(__name__)


class YukinoMainWindow(QMainWindow):
    """
    Main overlay window for Yukino.
    
    Features:
    - Frameless and transparent
    - Always on top
    - Draggable anywhere
    - System tray integration
    - Auto-hide on inactivity
    - Smooth fade in/out transitions
    
    Signals:
        window_shown: Emitted when window becomes visible
        window_hidden: Emitted when window is hidden
        quit_requested: Emitted when user requests quit
    """
    
    window_shown = pyqtSignal()
    window_hidden = pyqtSignal()
    quit_requested = pyqtSignal()
    
    def __init__(self, config: dict):
        """
        Initialize main window.
        
        Args:
            config: UI configuration dict
        """
        super().__init__()
        
        self._config = config
        
        # Window settings
        self._window_width = config.get("window_width", 400)
        self._window_height = config.get("window_height", 600)
        self._always_on_top = config.get("always_on_top", True)
        self._enable_transparency = config.get("enable_transparency", True)
        self._opacity = config.get("default_opacity", 0.95)
        
        # Auto-hide settings
        self._auto_hide_enabled = config.get("auto_hide_enabled", True)
        self._auto_hide_delay = config.get("auto_hide_delay", 30.0)  # seconds
        self._auto_hide_timer: Optional[QTimer] = None
        self._last_interaction_time = 0.0
        
        # System tray
        self._tray_icon: Optional[QSystemTrayIcon] = None
        self._enable_tray = config.get("enable_system_tray", True)
        
        # Window state
        self._is_dragging = False
        self._drag_position = QPoint()
        self._is_visible = False
        
        # Child widgets (to be set by parent)
        self._avatar_widget: Optional[QWidget] = None
        self._chat_panel: Optional[QWidget] = None
        self._status_bar: Optional[QWidget] = None
        
        # Setup window
        self._setup_window()
        self._setup_layout()
        self._setup_system_tray()
        self._setup_auto_hide()
        
        logger.info("YukinoMainWindow initialized")
    
    def _setup_window(self) -> None:
        """Configure window properties."""
        # Window flags
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        if self._enable_transparency:
            flags |= Qt.WindowType.WindowTransparentForInput
        
        self.setWindowFlags(flags)
        
        # Window attributes
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        # Size and position
        self.setFixedSize(self._window_width, self._window_height)
        
        # Center on screen
        self._center_on_screen()
        
        # Opacity
        self.setWindowOpacity(self._opacity)
        
        # Title (for taskbar)
        self.setWindowTitle("Yukino AI")
        
        logger.debug("Window setup complete")
    
    def _center_on_screen(self) -> None:
        """Center window on primary screen."""
        try:
            screen = self.screen()
            if screen:
                screen_geometry = screen.geometry()
                x = (screen_geometry.width() - self.width()) // 2
                y = (screen_geometry.height() - self.height()) // 2
                self.move(x, y)
        except Exception as e:
            logger.error(f"Error centering window: {e}")
    
    def _setup_layout(self) -> None:
        """Setup main window layout."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(5)
        
        # Store layout for adding widgets later
        self._main_layout = main_layout
        
        logger.debug("Layout setup complete")
    
    def _setup_system_tray(self) -> None:
        """Setup system tray icon and menu."""
        if not self._enable_tray or QSystemTrayIcon is None:
            return
        
        try:
            # Create tray icon
            self._tray_icon = QSystemTrayIcon(self)
            
            # Try to load icon
            icon_path = Path("yukino/ui/icon.png")
            if icon_path.exists():
                self._tray_icon.setIcon(QIcon(str(icon_path)))
            else:
                # Use default icon
                logger.warning("Tray icon not found, using default")
            
            # Create context menu
            tray_menu = QMenu()
            
            # Show action
            show_action = QAction("Show Yukino", self)
            show_action.triggered.connect(self.show_window)
            tray_menu.addAction(show_action)
            
            # Hide action
            hide_action = QAction("Hide Yukino", self)
            hide_action.triggered.connect(self.hide_window)
            tray_menu.addAction(hide_action)
            
            tray_menu.addSeparator()
            
            # Quit action
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(self._on_quit_requested)
            tray_menu.addAction(quit_action)
            
            # Set menu
            self._tray_icon.setContextMenu(tray_menu)
            
            # Double-click to show
            self._tray_icon.activated.connect(self._on_tray_activated)
            
            # Show tray icon
            self._tray_icon.show()
            self._tray_icon.setToolTip("Yukino AI Assistant")
            
            logger.info("System tray initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup system tray: {e}", exc_info=True)
    
    def _setup_auto_hide(self) -> None:
        """Setup auto-hide timer."""
        if not self._auto_hide_enabled or QTimer is None:
            return
        
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.timeout.connect(self._check_auto_hide)
        self._auto_hide_timer.start(1000)  # Check every second
        
        logger.debug("Auto-hide timer started")
    
    def _on_tray_activated(self, reason) -> None:
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self._is_visible:
                self.hide_window()
            else:
                self.show_window()
    
    def _on_quit_requested(self) -> None:
        """Handle quit request."""
        logger.info("Quit requested from tray")
        self.quit_requested.emit()
    
    def _check_auto_hide(self) -> None:
        """Check if window should auto-hide."""
        if not self._is_visible or not self._auto_hide_enabled:
            return
        
        import time
        elapsed = time.time() - self._last_interaction_time
        
        if elapsed >= self._auto_hide_delay:
            logger.info("Auto-hide triggered")
            self.hide_window()
    
    def set_avatar_widget(self, widget: QWidget) -> None:
        """
        Set avatar renderer widget.
        
        Args:
            widget: Avatar widget (VRMRenderer)
        """
        self._avatar_widget = widget
        self._main_layout.addWidget(widget, stretch=3)
        logger.debug("Avatar widget added")
    
    def set_chat_panel(self, widget: QWidget) -> None:
        """
        Set chat panel widget.
        
        Args:
            widget: Chat panel widget
        """
        self._chat_panel = widget
        self._main_layout.addWidget(widget, stretch=2)
        logger.debug("Chat panel added")
    
    def set_status_bar(self, widget: QWidget) -> None:
        """
        Set status bar widget.
        
        Args:
            widget: Status bar widget
        """
        self._status_bar = widget
        self._main_layout.addWidget(widget, stretch=0)
        logger.debug("Status bar added")
    
    def show_window(self) -> None:
        """Show the window with fade-in."""
        if self._is_visible:
            return
        
        import time
        self._last_interaction_time = time.time()
        
        self.show()
        self.raise_()
        self.activateWindow()
        
        self._is_visible = True
        self.window_shown.emit()
        
        logger.info("Window shown")
    
    def hide_window(self) -> None:
        """Hide the window with fade-out."""
        if not self._is_visible:
            return
        
        self.hide()
        
        self._is_visible = False
        self.window_hidden.emit()
        
        logger.info("Window hidden")
    
    def toggle_window(self) -> None:
        """Toggle window visibility."""
        if self._is_visible:
            self.hide_window()
        else:
            self.show_window()
    
    def record_interaction(self) -> None:
        """Record user interaction (resets auto-hide timer)."""
        import time
        self._last_interaction_time = time.time()
    
    # Mouse events for dragging
    def mousePressEvent(self, event) -> None:
        """Handle mouse press for dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            self.record_interaction()
    
    def mouseMoveEvent(self, event) -> None:
        """Handle mouse move for dragging."""
        if self._is_dragging and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event) -> None:
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False
            event.accept()
    
    def closeEvent(self, event) -> None:
        """Handle window close event."""
        # Don't actually close, just hide
        event.ignore()
        self.hide_window()
    
    def is_visible_window(self) -> bool:
        """Check if window is visible."""
        return self._is_visible
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._auto_hide_timer:
            self._auto_hide_timer.stop()
        
        if self._tray_icon:
            self._tray_icon.hide()
        
        logger.debug("Window cleaned up")


def create_main_window(config: dict) -> YukinoMainWindow:
    """
    Factory function to create main window.
    
    Args:
        config: UI configuration dict
    
    Returns:
        Initialized YukinoMainWindow instance
    """
    return YukinoMainWindow(config)

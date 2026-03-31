"""
VRM avatar renderer with PyQt6 OpenGL.

Renders VRM 3D models with blend shapes, animations, and fallback placeholder
when VRM file is not available.
"""

import logging
from typing import Dict, Any, Optional
from pathlib import Path
from enum import Enum

try:
    from PyQt6.QtWidgets import QOpenGLWidget
    from PyQt6.QtCore import QTimer, pyqtSignal
    from PyQt6.QtGui import QPainter, QColor, QPen
except ImportError:
    QOpenGLWidget = object
    QTimer = None
    pyqtSignal = None
    QPainter = None
    QColor = None
    QPen = None

try:
    from OpenGL.GL import *
    from OpenGL.GLU import *
    OPENGL_AVAILABLE = True
except ImportError:
    OPENGL_AVAILABLE = False

try:
    import pygltflib
    PYGLTFLIB_AVAILABLE = True
except ImportError:
    PYGLTFLIB_AVAILABLE = False

import random
import time
import math

logger = logging.getLogger(__name__)


class MoodState(Enum):
    """Avatar mood states."""
    IDLE = "idle"
    THINKING = "thinking"
    HAPPY = "happy"
    ANNOYED = "annoyed"
    SPEAKING = "speaking"


class VRMRenderer(QOpenGLWidget):
    """
    VRM avatar renderer with OpenGL.
    
    Features:
    - VRM model loading with pygltflib
    - Blend shape support for expressions and lip sync
    - Placeholder mode when VRM is missing
    - 30fps render loop
    - Transparent background
    - Mood states and animations
    
    Signals:
        render_error: Emitted when rendering error occurs
    """
    
    render_error = pyqtSignal(str)
    
    def __init__(self, config: dict, parent=None):
        """
        Initialize VRM renderer.
        
        Args:
            config: Avatar configuration dict
            parent: Parent widget
        """
        super().__init__(parent)
        
        self._config = config
        self._vrm_path = Path(config.get("vrm_path", "data/Yuki.vrm"))
        self._fps = config.get("fps", 30)
        self._enable_placeholder = config.get("enable_placeholder", True)
        
        # VRM model data
        self._vrm_loaded = False
        self._vrm_model: Optional[Any] = None
        self._blend_shapes: Dict[str, float] = {}
        
        # Animation state
        self._mood_state = MoodState.IDLE
        self._current_blend: Dict[str, float] = {}
        self._blink_timer = 0.0
        self._next_blink = random.uniform(3.0, 5.0)
        self._breathing_phase = 0.0
        
        # Render timer
        self._timer: Optional[QTimer] = None
        self._last_frame_time = time.time()
        
        # Placeholder mode
        self._use_placeholder = False
        
        # Try to load VRM
        self._load_vrm()
        
        logger.info(f"VRMRenderer initialized (placeholder: {self._use_placeholder})")
    
    def _load_vrm(self) -> None:
        """Load VRM model from file."""
        if not self._vrm_path.exists():
            logger.warning(f"VRM file not found: {self._vrm_path}")
            if self._enable_placeholder:
                logger.info("Using placeholder avatar")
                self._use_placeholder = True
            else:
                logger.error("Placeholder disabled, no avatar available")
            return
        
        if not PYGLTFLIB_AVAILABLE:
            logger.error("pygltflib not available, cannot load VRM")
            self._use_placeholder = True
            return
        
        try:
            # Load glTF/VRM file
            logger.info(f"Loading VRM from: {self._vrm_path}")
            self._vrm_model = pygltflib.GLTF2().load(str(self._vrm_path))
            
            # Parse blend shapes (VRM extensions)
            self._parse_blend_shapes()
            
            self._vrm_loaded = True
            logger.info("VRM model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load VRM: {e}", exc_info=True)
            if self._enable_placeholder:
                logger.info("Falling back to placeholder avatar")
                self._use_placeholder = True
            else:
                raise
    
    def _parse_blend_shapes(self) -> None:
        """Parse VRM blend shapes from model."""
        if not self._vrm_model:
            return
        
        # VRM blend shapes are in extensions
        # This is a simplified parser - full VRM parsing is complex
        try:
            # Initialize common blend shapes to 0
            self._blend_shapes = {
                "Blink": 0.0,
                "BlinkL": 0.0,
                "BlinkR": 0.0,
                "Joy": 0.0,
                "Angry": 0.0,
                "Sorrow": 0.0,
                "Fun": 0.0,
                "A": 0.0,
                "I": 0.0,
                "U": 0.0,
                "E": 0.0,
                "O": 0.0,
            }
            
            logger.debug(f"Initialized {len(self._blend_shapes)} blend shapes")
            
        except Exception as e:
            logger.error(f"Error parsing blend shapes: {e}")
    
    def initializeGL(self) -> None:
        """Initialize OpenGL context."""
        if not OPENGL_AVAILABLE:
            logger.warning("OpenGL not available")
            return
        
        try:
            # Set clear color (transparent)
            glClearColor(0.0, 0.0, 0.0, 0.0)
            
            # Enable depth testing
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(GL_LEQUAL)
            
            # Enable blending for transparency
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # Start render timer
            self._start_render_loop()
            
            logger.debug("OpenGL initialized")
            
        except Exception as e:
            logger.error(f"OpenGL initialization error: {e}", exc_info=True)
    
    def resizeGL(self, w: int, h: int) -> None:
        """Handle window resize."""
        if not OPENGL_AVAILABLE:
            return
        
        try:
            glViewport(0, 0, w, h)
            
            # Set projection matrix
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45.0, w / h if h > 0 else 1.0, 0.1, 100.0)
            
            glMatrixMode(GL_MODELVIEW)
            
        except Exception as e:
            logger.error(f"Resize error: {e}")
    
    def paintGL(self) -> None:
        """Render the avatar."""
        try:
            if self._use_placeholder:
                self._render_placeholder()
            elif self._vrm_loaded:
                self._render_vrm()
            else:
                # Nothing to render
                if OPENGL_AVAILABLE:
                    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        except Exception as e:
            logger.error(f"Render error: {e}", exc_info=True)
            try:
                self.render_error.emit(str(e))
            except:
                pass
    
    def _render_placeholder(self) -> None:
        """Render a simple placeholder avatar."""
        if not OPENGL_AVAILABLE:
            # Use QPainter fallback for 2D placeholder
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Draw simple silhouette
            w, h = self.width(), self.height()
            
            # Background gradient
            painter.fillRect(0, 0, w, h, QColor(20, 20, 30, 180))
            
            # Silhouette circle (head)
            head_size = min(w, h) // 3
            head_x = w // 2
            head_y = h // 3
            
            painter.setPen(QPen(QColor(100, 100, 120), 2))
            painter.setBrush(QColor(60, 60, 80, 200))
            painter.drawEllipse(head_x - head_size//2, head_y - head_size//2, head_size, head_size)
            
            # Body
            body_width = head_size
            body_height = h // 2
            painter.drawRoundedRect(
                head_x - body_width//2,
                head_y + head_size//2,
                body_width,
                body_height,
                20, 20
            )
            
            # Text
            painter.setPen(QColor(150, 150, 170))
            painter.drawText(10, h - 10, "Yuki (Placeholder)")
            
            painter.end()
            return
        
        # OpenGL placeholder
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Position camera
        glTranslatef(0.0, 0.0, -5.0)
        
        # Apply breathing animation
        breathing_scale = 1.0 + 0.003 * math.sin(self._breathing_phase)
        glScalef(1.0, breathing_scale, 1.0)
        
        # Draw simple sphere for head
        glColor4f(0.7, 0.7, 0.8, 0.9)
        
        # Note: glutSolidSphere not available without GLUT
        # Draw a simple placeholder cube instead
        self._draw_cube(0.5)
    
    def _draw_cube(self, size: float) -> None:
        """Draw a simple cube (placeholder geometry)."""
        glBegin(GL_QUADS)
        
        # Front face
        glVertex3f(-size, -size, size)
        glVertex3f(size, -size, size)
        glVertex3f(size, size, size)
        glVertex3f(-size, size, size)
        
        # Back face
        glVertex3f(-size, -size, -size)
        glVertex3f(-size, size, -size)
        glVertex3f(size, size, -size)
        glVertex3f(size, -size, -size)
        
        # Top face
        glVertex3f(-size, size, -size)
        glVertex3f(-size, size, size)
        glVertex3f(size, size, size)
        glVertex3f(size, size, -size)
        
        # Bottom face
        glVertex3f(-size, -size, -size)
        glVertex3f(size, -size, -size)
        glVertex3f(size, -size, size)
        glVertex3f(-size, -size, size)
        
        glEnd()
    
    def _render_vrm(self) -> None:
        """Render VRM model with current blend shapes."""
        if not OPENGL_AVAILABLE:
            return
        
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        
        # Position camera
        glTranslatef(0.0, -0.5, -2.0)
        
        # Apply blend shapes (simplified - full implementation would modify vertices)
        # For now, just log active blend shapes
        active_blends = {k: v for k, v in self._current_blend.items() if v > 0.01}
        if active_blends:
            logger.debug(f"Active blends: {active_blends}")
        
        # TODO: Render actual VRM mesh with blend shapes
        # This requires full glTF mesh rendering which is complex
        # For now, render placeholder
        self._render_placeholder()
    
    def _start_render_loop(self) -> None:
        """Start the render loop timer."""
        if QTimer is None:
            return
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_frame)
        interval = int(1000 / self._fps)  # milliseconds
        self._timer.start(interval)
        
        logger.debug(f"Render loop started at {self._fps} fps")
    
    def _update_frame(self) -> None:
        """Update animation and trigger repaint."""
        current_time = time.time()
        delta_time = current_time - self._last_frame_time
        self._last_frame_time = current_time
        
        # Update animations
        self._update_animations(delta_time)
        
        # Trigger repaint
        self.update()
    
    def _update_animations(self, delta_time: float) -> None:
        """Update animation states."""
        # Auto-blink
        self._blink_timer += delta_time
        if self._blink_timer >= self._next_blink:
            self._trigger_blink()
            self._blink_timer = 0.0
            self._next_blink = random.uniform(3.0, 5.0)
        
        # Breathing animation
        self._breathing_phase += delta_time * 0.3  # 0.3 Hz
        if self._breathing_phase > 2 * math.pi:
            self._breathing_phase -= 2 * math.pi
        
        # Decay blend shapes
        for name in self._current_blend:
            if self._current_blend[name] > 0:
                self._current_blend[name] = max(0, self._current_blend[name] - delta_time * 2.0)
    
    def _trigger_blink(self) -> None:
        """Trigger a blink animation."""
        self._current_blend["Blink"] = 1.0
        logger.debug("Blink triggered")
    
    def set_mood(self, mood: MoodState) -> None:
        """
        Set avatar mood state.
        
        Args:
            mood: MoodState enum value
        """
        self._mood_state = mood
        
        # Clear previous mood blends
        self._current_blend["Joy"] = 0.0
        self._current_blend["Angry"] = 0.0
        self._current_blend["Sorrow"] = 0.0
        
        # Set new mood blend
        if mood == MoodState.HAPPY:
            self._current_blend["Joy"] = 0.7
        elif mood == MoodState.ANNOYED:
            self._current_blend["Angry"] = 0.5
        elif mood == MoodState.THINKING:
            # Slight head tilt - would need bone manipulation
            pass
        
        logger.debug(f"Mood set to: {mood.value}")
    
    def set_blend_shape(self, name: str, value: float) -> None:
        """
        Set a specific blend shape value.
        
        Args:
            name: Blend shape name
            value: Blend shape value (0.0 - 1.0)
        """
        if name in self._blend_shapes:
            self._current_blend[name] = max(0.0, min(1.0, value))
    
    def get_blend_shape(self, name: str) -> float:
        """Get current blend shape value."""
        return self._current_blend.get(name, 0.0)
    
    def is_using_placeholder(self) -> bool:
        """Check if using placeholder mode."""
        return self._use_placeholder
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._timer:
            self._timer.stop()
        
        self._vrm_model = None
        logger.debug("VRM renderer cleaned up")


def create_vrm_renderer(config: dict, parent=None) -> VRMRenderer:
    """
    Factory function to create VRM renderer.
    
    Args:
        config: Avatar configuration dict
        parent: Parent widget
    
    Returns:
        Initialized VRMRenderer instance
    """
    return VRMRenderer(config, parent)

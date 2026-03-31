"""
Avatar animation system.

Manages idle animations, mood states, blinking, breathing, and gesture triggers
for the VRM avatar.
"""

import logging
from typing import Dict, Optional, Callable
import random
import time
import math
from enum import Enum

logger = logging.getLogger(__name__)


class AnimationState(Enum):
    """Avatar animation states."""
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    GESTURING = "gesturing"


class MoodPreset(Enum):
    """Predefined mood presets with blend shape values."""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    ANNOYED = "annoyed"
    THINKING = "thinking"
    SURPRISED = "surprised"
    SAD = "sad"


class AnimationController:
    """
    Controls avatar animations and mood states.
    
    Features:
    - Idle animations (breathing, subtle movements)
    - Automatic blinking with randomization
    - Mood presets with blend shape combinations
    - Smooth transitions between states
    - Gesture triggers
    """
    
    # Mood preset blend shapes
    MOOD_BLENDS = {
        MoodPreset.NEUTRAL: {},
        
        MoodPreset.HAPPY: {
            "Joy": 0.6,
        },
        
        MoodPreset.ANNOYED: {
            "Angry": 0.5,
        },
        
        MoodPreset.THINKING: {
            "Sorrow": 0.2,  # Slight concern
        },
        
        MoodPreset.SURPRISED: {
            "Fun": 0.7,
            "Blink": -0.5,  # Eyes wide
        },
        
        MoodPreset.SAD: {
            "Sorrow": 0.7,
        },
    }
    
    def __init__(self, renderer, config: dict):
        """
        Initialize animation controller.
        
        Args:
            renderer: VRMRenderer instance
            config: Animation configuration
        """
        self._renderer = renderer
        self._config = config
        
        # Animation settings
        self._enable_idle = config.get("enable_idle_animations", True)
        self._enable_auto_blink = config.get("enable_auto_blink", True)
        self._blink_min_interval = config.get("blink_min_interval", 2.0)
        self._blink_max_interval = config.get("blink_max_interval", 5.0)
        self._breathing_enabled = config.get("enable_breathing", True)
        self._breathing_speed = config.get("breathing_speed", 0.25)  # Hz
        self._breathing_intensity = config.get("breathing_intensity", 0.01)
        
        # Current state
        self._animation_state = AnimationState.IDLE
        self._current_mood = MoodPreset.NEUTRAL
        
        # Blinking
        self._blink_timer = 0.0
        self._next_blink_time = self._random_blink_interval()
        self._is_blinking = False
        self._blink_phase = 0.0
        self._blink_duration = 0.15  # 150ms blink
        
        # Breathing
        self._breathing_phase = 0.0
        
        # Idle sway
        self._sway_phase = 0.0
        self._sway_enabled = config.get("enable_idle_sway", True)
        self._sway_speed = 0.1  # Hz
        self._sway_intensity = 0.005
        
        # Transition
        self._transition_active = False
        self._transition_start = 0.0
        self._transition_duration = 0.5
        self._transition_from: Dict[str, float] = {}
        self._transition_to: Dict[str, float] = {}
        
        logger.info("AnimationController initialized")
    
    def update(self, delta_time: float) -> None:
        """
        Update all animations.
        
        Should be called every frame.
        
        Args:
            delta_time: Time since last update (seconds)
        """
        # Update blinking
        if self._enable_auto_blink:
            self._update_blink(delta_time)
        
        # Update breathing
        if self._breathing_enabled:
            self._update_breathing(delta_time)
        
        # Update idle sway
        if self._enable_idle and self._sway_enabled and self._animation_state == AnimationState.IDLE:
            self._update_sway(delta_time)
        
        # Update mood transitions
        if self._transition_active:
            self._update_transition(delta_time)
    
    def _update_blink(self, delta_time: float) -> None:
        """Update blink animation."""
        if self._is_blinking:
            # Progress blink animation
            self._blink_phase += delta_time
            
            # Blink is a quick close-open
            if self._blink_phase < self._blink_duration:
                # Closing phase (first half)
                if self._blink_phase < self._blink_duration / 2:
                    progress = self._blink_phase / (self._blink_duration / 2)
                    blink_value = progress
                # Opening phase (second half)
                else:
                    progress = (self._blink_phase - self._blink_duration / 2) / (self._blink_duration / 2)
                    blink_value = 1.0 - progress
                
                self._renderer.set_blend_shape("Blink", blink_value)
            else:
                # Blink complete
                self._is_blinking = False
                self._blink_phase = 0.0
                self._renderer.set_blend_shape("Blink", 0.0)
        else:
            # Check if time to blink
            self._blink_timer += delta_time
            if self._blink_timer >= self._next_blink_time:
                self._trigger_blink()
    
    def _trigger_blink(self) -> None:
        """Trigger a blink."""
        self._is_blinking = True
        self._blink_phase = 0.0
        self._blink_timer = 0.0
        self._next_blink_time = self._random_blink_interval()
        
        logger.debug("Blink triggered")
    
    def _random_blink_interval(self) -> float:
        """Get random blink interval."""
        return random.uniform(self._blink_min_interval, self._blink_max_interval)
    
    def _update_breathing(self, delta_time: float) -> None:
        """Update breathing animation."""
        self._breathing_phase += delta_time * self._breathing_speed * 2 * math.pi
        
        # Wrap phase
        if self._breathing_phase > 2 * math.pi:
            self._breathing_phase -= 2 * math.pi
        
        # Apply breathing (this would typically affect bone transforms)
        # For now, subtle mouth breathing
        breathing_value = (math.sin(self._breathing_phase) + 1) / 2  # 0 to 1
        subtle_breath = breathing_value * self._breathing_intensity
        
        # Could apply to chest bone transform if bones were implemented
        logger.debug(f"Breathing phase: {breathing_value:.2f}")
    
    def _update_sway(self, delta_time: float) -> None:
        """Update idle sway animation."""
        self._sway_phase += delta_time * self._sway_speed * 2 * math.pi
        
        # Wrap phase
        if self._sway_phase > 2 * math.pi:
            self._sway_phase -= 2 * math.pi
        
        # Apply sway (would affect root bone rotation)
        sway_x = math.sin(self._sway_phase) * self._sway_intensity
        sway_z = math.cos(self._sway_phase * 0.7) * self._sway_intensity * 0.5
        
        logger.debug(f"Sway: x={sway_x:.3f}, z={sway_z:.3f}")
    
    def _update_transition(self, delta_time: float) -> None:
        """Update mood transition."""
        elapsed = time.time() - self._transition_start
        progress = min(1.0, elapsed / self._transition_duration)
        
        # Smooth easing (ease-in-out)
        eased_progress = self._ease_in_out(progress)
        
        # Interpolate blend shapes
        for shape_name in self._transition_to:
            from_value = self._transition_from.get(shape_name, 0.0)
            to_value = self._transition_to[shape_name]
            
            current_value = from_value + (to_value - from_value) * eased_progress
            self._renderer.set_blend_shape(shape_name, current_value)
        
        # Check if transition complete
        if progress >= 1.0:
            self._transition_active = False
            logger.debug("Mood transition complete")
    
    def _ease_in_out(self, t: float) -> float:
        """Smooth easing function."""
        return t * t * (3.0 - 2.0 * t)
    
    def set_animation_state(self, state: AnimationState) -> None:
        """
        Set animation state.
        
        Args:
            state: AnimationState enum value
        """
        if state == self._animation_state:
            return
        
        old_state = self._animation_state
        self._animation_state = state
        
        logger.info(f"Animation state: {old_state.value} -> {state.value}")
        
        # State-specific behavior
        if state == AnimationState.THINKING:
            # Trigger thinking mood
            self.set_mood(MoodPreset.THINKING)
        elif state == AnimationState.IDLE:
            # Return to neutral
            self.set_mood(MoodPreset.NEUTRAL)
    
    def set_mood(self, mood: MoodPreset, transition_duration: Optional[float] = None) -> None:
        """
        Set avatar mood with transition.
        
        Args:
            mood: MoodPreset enum value
            transition_duration: Optional override for transition time
        """
        if mood == self._current_mood and not self._transition_active:
            return
        
        # Get current blend values
        current_blends = {}
        for shape in ["Joy", "Angry", "Sorrow", "Fun"]:
            current_blends[shape] = self._renderer.get_blend_shape(shape)
        
        # Get target blend values
        target_blends = self.MOOD_BLENDS.get(mood, {})
        
        # Start transition
        self._transition_from = current_blends
        self._transition_to = target_blends
        self._transition_start = time.time()
        self._transition_duration = transition_duration or 0.5
        self._transition_active = True
        
        self._current_mood = mood
        
        logger.info(f"Mood set to: {mood.value}")
    
    def trigger_gesture(self, gesture_name: str) -> None:
        """
        Trigger a one-shot gesture animation.
        
        Args:
            gesture_name: Name of gesture (e.g., "nod", "shake_head", "shrug")
        """
        logger.info(f"Gesture triggered: {gesture_name}")
        
        # Gesture implementation would depend on bone animations
        # For now, just log
        
        if gesture_name == "nod":
            # Would rotate head bone up and down
            pass
        elif gesture_name == "shake_head":
            # Would rotate head bone left and right
            pass
        elif gesture_name == "shrug":
            # Would raise shoulder bones
            pass
    
    def set_idle_enabled(self, enabled: bool) -> None:
        """Enable or disable idle animations."""
        self._enable_idle = enabled
        logger.debug(f"Idle animations: {'enabled' if enabled else 'disabled'}")
    
    def set_blink_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-blinking."""
        self._enable_auto_blink = enabled
        
        if not enabled:
            # Reset blink state
            self._is_blinking = False
            self._renderer.set_blend_shape("Blink", 0.0)
        
        logger.debug(f"Auto-blink: {'enabled' if enabled else 'disabled'}")
    
    def set_breathing_enabled(self, enabled: bool) -> None:
        """Enable or disable breathing animation."""
        self._breathing_enabled = enabled
        logger.debug(f"Breathing: {'enabled' if enabled else 'disabled'}")
    
    def get_animation_state(self) -> AnimationState:
        """Get current animation state."""
        return self._animation_state
    
    def get_mood(self) -> MoodPreset:
        """Get current mood preset."""
        return self._current_mood
    
    def force_blink(self) -> None:
        """Force an immediate blink."""
        if not self._is_blinking:
            self._trigger_blink()
    
    def reset(self) -> None:
        """Reset all animations to default state."""
        self._animation_state = AnimationState.IDLE
        self._current_mood = MoodPreset.NEUTRAL
        self._transition_active = False
        self._is_blinking = False
        self._blink_timer = 0.0
        self._breathing_phase = 0.0
        self._sway_phase = 0.0
        
        # Clear all expression blend shapes
        for shape in ["Joy", "Angry", "Sorrow", "Fun", "Blink"]:
            self._renderer.set_blend_shape(shape, 0.0)
        
        logger.debug("Animations reset")


def create_animation_controller(renderer, config: dict) -> AnimationController:
    """
    Factory function to create animation controller.
    
    Args:
        renderer: VRMRenderer instance
        config: Animation configuration
    
    Returns:
        Initialized AnimationController instance
    """
    return AnimationController(renderer, config)

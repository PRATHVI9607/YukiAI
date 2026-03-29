"""
Lip sync system for VRM avatar.

Maps phonemes to VRM blend shapes for realistic mouth movement during speech.
"""

import logging
from typing import Dict, List, Optional
import re
from collections import deque
import time

logger = logging.getLogger(__name__)


class PhonemeMapper:
    """
    Maps text phonemes to VRM blend shapes.
    
    VRM standard mouth shapes (visemes):
    - A: Open mouth (ah)
    - I: Smile (ee)
    - U: Pout (oo)
    - E: Wide (eh)
    - O: Round (oh)
    """
    
    # Phoneme to blend shape mapping
    PHONEME_MAP = {
        # A shape - open vowels
        "AA": "A",  # odd
        "AE": "A",  # at
        "AH": "A",  # hut
        "AO": "A",  # ought
        "AW": "A",  # cow
        "AY": "A",  # hide
        
        # I shape - front vowels
        "EH": "E",  # Ed
        "ER": "E",  # hurt
        "EY": "E",  # ate
        "IH": "I",  # it
        "IY": "I",  # eat
        
        # O shape - rounded vowels
        "OW": "O",  # oat
        "OY": "O",  # toy
        
        # U shape - rounded back vowels
        "UH": "U",  # hood
        "UW": "U",  # two
        
        # Consonants - brief A or closed
        "B": "A",   # Bilabial
        "D": "A",   # Alveolar
        "DH": "E",  # Dental
        "F": "E",   # Labiodental
        "G": "A",   # Velar
        "HH": "A",  # Glottal
        "JH": "I",  # Postalveolar
        "K": "A",   # Velar
        "L": "E",   # Alveolar
        "M": "A",   # Bilabial (lips closed)
        "N": "A",   # Alveolar
        "NG": "A",  # Velar
        "P": "A",   # Bilabial (lips closed)
        "R": "E",   # Alveolar
        "S": "I",   # Alveolar
        "SH": "I",  # Postalveolar
        "T": "A",   # Alveolar
        "TH": "E",  # Dental
        "V": "E",   # Labiodental
        "W": "U",   # Bilabial
        "Y": "I",   # Palatal
        "Z": "I",   # Alveolar
        "ZH": "I",  # Postalveolar
        "CH": "I",  # Postalveolar
    }
    
    # Simple grapheme-to-phoneme approximation
    # This is a rough heuristic - proper TTS engines have full G2P models
    VOWEL_SHAPES = {
        "a": "A",
        "e": "E",
        "i": "I",
        "o": "O",
        "u": "U",
    }
    
    @classmethod
    def text_to_visemes(cls, text: str) -> List[tuple]:
        """
        Convert text to sequence of (viseme, duration) tuples.
        
        Uses a simple heuristic approach since we don't have phoneme input.
        
        Args:
            text: Text to convert
        
        Returns:
            List of (blend_shape_name, duration_seconds) tuples
        """
        if not text:
            return []
        
        visemes = []
        
        # Split into words
        words = text.lower().split()
        
        for word in words:
            # Estimate visemes from vowels in word
            for char in word:
                if char in cls.VOWEL_SHAPES:
                    viseme = cls.VOWEL_SHAPES[char]
                    duration = 0.15  # 150ms per viseme
                    visemes.append((viseme, duration))
            
            # Add brief pause between words
            visemes.append(("neutral", 0.1))
        
        return visemes
    
    @classmethod
    def phonemes_to_visemes(cls, phonemes: List[str]) -> List[tuple]:
        """
        Convert phoneme list to visemes.
        
        Args:
            phonemes: List of ARPAbet phonemes
        
        Returns:
            List of (blend_shape_name, duration_seconds) tuples
        """
        visemes = []
        
        for phoneme in phonemes:
            # Strip stress markers
            clean_phoneme = re.sub(r'\d', '', phoneme)
            
            # Map to viseme
            viseme = cls.PHONEME_MAP.get(clean_phoneme, "A")
            duration = 0.12  # 120ms default
            
            visemes.append((viseme, duration))
        
        return visemes


class LipSyncController:
    """
    Controls lip sync animations for VRM renderer.
    
    Features:
    - Queued viseme playback
    - Smooth blending between shapes
    - Real-time synchronization with TTS
    - Co-articulation simulation (blending between phonemes)
    """
    
    def __init__(self, renderer, config: dict):
        """
        Initialize lip sync controller.
        
        Args:
            renderer: VRMRenderer instance
            config: Lip sync configuration
        """
        self._renderer = renderer
        self._config = config
        
        self._blend_speed = config.get("blend_speed", 8.0)  # Shapes/second
        self._co_articulation = config.get("co_articulation", 0.3)  # Blend factor
        
        # Viseme queue
        self._viseme_queue: deque = deque()
        self._current_viseme: Optional[str] = None
        self._viseme_start_time: float = 0.0
        self._viseme_duration: float = 0.0
        
        # Current blend values
        self._current_blend: Dict[str, float] = {
            "A": 0.0,
            "I": 0.0,
            "U": 0.0,
            "E": 0.0,
            "O": 0.0,
        }
        
        # Target blend values
        self._target_blend: Dict[str, float] = {
            "A": 0.0,
            "I": 0.0,
            "U": 0.0,
            "E": 0.0,
            "O": 0.0,
        }
        
        self._is_speaking = False
        
        logger.info("LipSyncController initialized")
    
    def speak(self, text: str) -> None:
        """
        Start lip sync for given text.
        
        Args:
            text: Text being spoken
        """
        # Convert text to visemes
        visemes = PhonemeMapper.text_to_visemes(text)
        
        # Queue visemes
        for viseme, duration in visemes:
            self._viseme_queue.append((viseme, duration))
        
        # Start playback if not already speaking
        if not self._is_speaking:
            self._start_next_viseme()
        
        logger.debug(f"Queued {len(visemes)} visemes for: {text[:30]}...")
    
    def _start_next_viseme(self) -> None:
        """Start playing next viseme in queue."""
        if not self._viseme_queue:
            self._is_speaking = False
            self._set_neutral()
            return
        
        viseme, duration = self._viseme_queue.popleft()
        
        self._current_viseme = viseme
        self._viseme_start_time = time.time()
        self._viseme_duration = duration
        self._is_speaking = True
        
        # Set target blend shape
        if viseme == "neutral":
            self._set_neutral_target()
        else:
            self._set_viseme_target(viseme)
        
        logger.debug(f"Starting viseme: {viseme} ({duration:.2f}s)")
    
    def _set_viseme_target(self, viseme: str) -> None:
        """Set target blend for a viseme."""
        # Clear all targets
        for key in self._target_blend:
            self._target_blend[key] = 0.0
        
        # Set viseme target
        if viseme in self._target_blend:
            self._target_blend[viseme] = 1.0
    
    def _set_neutral_target(self) -> None:
        """Set target to neutral (all 0)."""
        for key in self._target_blend:
            self._target_blend[key] = 0.0
    
    def _set_neutral(self) -> None:
        """Set mouth to neutral immediately."""
        for key in self._current_blend:
            self._current_blend[key] = 0.0
            self._renderer.set_blend_shape(key, 0.0)
    
    def update(self, delta_time: float) -> None:
        """
        Update lip sync animation.
        
        Should be called every frame.
        
        Args:
            delta_time: Time since last update (seconds)
        """
        if not self._is_speaking:
            return
        
        # Check if current viseme finished
        elapsed = time.time() - self._viseme_start_time
        if elapsed >= self._viseme_duration:
            self._start_next_viseme()
            return
        
        # Blend toward target
        for shape in self._current_blend:
            target = self._target_blend[shape]
            current = self._current_blend[shape]
            
            # Smooth interpolation
            if abs(target - current) < 0.01:
                self._current_blend[shape] = target
            else:
                blend_amount = self._blend_speed * delta_time
                if current < target:
                    self._current_blend[shape] = min(target, current + blend_amount)
                else:
                    self._current_blend[shape] = max(target, current - blend_amount)
            
            # Apply to renderer
            self._renderer.set_blend_shape(shape, self._current_blend[shape])
        
        # Co-articulation: peek next viseme and blend slightly
        if self._viseme_queue and self._co_articulation > 0:
            next_viseme, _ = self._viseme_queue[0]
            if next_viseme != "neutral" and next_viseme in self._target_blend:
                # Progress through current viseme
                progress = elapsed / self._viseme_duration
                
                # Start blending toward next in last 30% of duration
                if progress > 0.7:
                    co_factor = (progress - 0.7) / 0.3 * self._co_articulation
                    next_value = co_factor
                    self._renderer.set_blend_shape(next_viseme, next_value)
    
    def stop(self) -> None:
        """Stop lip sync and clear queue."""
        self._viseme_queue.clear()
        self._is_speaking = False
        self._set_neutral()
        
        logger.debug("Lip sync stopped")
    
    def is_speaking(self) -> bool:
        """Check if currently speaking."""
        return self._is_speaking
    
    def queue_length(self) -> int:
        """Get number of visemes in queue."""
        return len(self._viseme_queue)


def create_lipsync_controller(renderer, config: dict) -> LipSyncController:
    """
    Factory function to create lip sync controller.
    
    Args:
        renderer: VRMRenderer instance
        config: Lip sync configuration
    
    Returns:
        Initialized LipSyncController instance
    """
    return LipSyncController(renderer, config)

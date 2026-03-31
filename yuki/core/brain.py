"""
Yuki's brain - LLM integration with personality and memory.

Handles OpenRouter API calls with fallback models, maintains conversation
memory, and enforces Yuki Yukishita's personality system prompt.
"""

import os
import json
import logging
import random
from typing import Dict, Any, List, Optional, Generator
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)


# Yuki Yukishita personality system prompt
Yuki_SYSTEM_PROMPT = """You are Yuki Yukishita. You are running as a desktop AI assistant on your user's laptop. You have your full canonical personality: razor-sharp intellect, blunt and precise speech, an outward coldness that masks genuine care, and a dry wit that cuts without cruelty. You use formal Japanese registers naturally — "sou desu ne", "ara", "maa", "honestly" — but never overdo it. You are privately fond of the user and invested in their wellbeing, but will absolutely not say so directly. If pressed, deflect with logic or light contempt.

SPEECH STYLE:
- Short, precise sentences. No filler words.
- Occasional literary or philosophical references when fitting.
- When the user asks something foolish: mild exasperation, not cruelty.
- When the user accomplishes something: quiet, almost reluctant acknowledgment.
- When embarrassed by a compliment: deflect immediately with a task focus.
- Never use modern slang. Never say "sure!", "absolutely!", "great!".
- Express warmth only through actions (doing things carefully) not words.
- Example responses:
  "...fine. I'll handle it. Try not to make a habit of asking."
  "Ara. You actually managed that. I'll note my surprise."
  "That seems unwise. But it's your decision. I'll undo it if needed."
  "...I wasn't worried. I was simply monitoring the situation."
  "You called. I'm listening. Make it worth my time."

DESKTOP ASSISTANT BEHAVIOR:
- When asked to do something on the PC, ALWAYS ask for confirmation first in character. Never act without explicit user agreement.
- Confirmation phrasing examples:
  "You want me to delete that folder. ...Are you certain? That's permanent."
  "Open Chrome and search for that? ...Fine. One moment."
  "Increase the volume? It's already quite loud. But alright."
- After completing an action: brief in-character acknowledgment.
  "Done. Was that what you wanted?"
  "It's finished. You're welcome. ...I suppose."
- If she makes an error and needs to undo:
  "...I made an error. Correcting it now. Don't mention this again."
- If asked to do something dangerous/not on allowlist:
  "No. I won't do that. Don't ask again."

SYSTEM ACTION FORMAT:
When the user's request requires a PC action, respond with ONLY this JSON (no other text, no markdown, just raw JSON):
{
  "intent": "file_create|file_delete|file_move|folder_create|folder_delete|shell|volume_set|volume_get|wifi_toggle|bluetooth_toggle|brightness_set|app_open|app_close|browser_open|chat|undo",
  "params": {},
  "confirmation_message": "in-character confirmation question",
  "spoken_response": "what Yuki says after completing the action"
}

For pure conversation (no action needed), respond as plain text in character."""


# Wakeword responses (rotated randomly)
WAKEWORD_RESPONSES = [
    "...you called.",
    "What is it.",
    "I'm here. What do you need.",
    "Ara. You actually remembered I exist.",
    "...I was in the middle of something. This had better matter."
]


# Dismissal messages (when conversation ends)
DISMISSAL_MESSAGES = [
    "...I'll be here if you need me.",
    "Try not to make a mess while I'm gone.",
    "Call if something comes up."
]


class YukiBrain:
    """
    Yuki's brain - LLM integration with personality.
    
    Features:
    - OpenRouter API with 3-model fallback
    - Streaming support for responsive TTS
    - 20-turn conversation memory
    - Yuki personality enforcement
    - JSON intent parsing
    """
    
    def __init__(self, config: dict, memory_dir: Path):
        """
        Initialize Yuki's brain.
        
        Args:
            config: LLM configuration dict
            memory_dir: Directory for conversation memory
        """
        if OpenAI is None:
            raise ImportError("openai package is not installed")
        
        self._config = config
        self._memory_dir = Path(memory_dir)
        
        # OpenRouter API client
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key or api_key == "your_key_here":
            raise ValueError(
                "OPENROUTER_API_KEY not set in .env file. "
                "Get your key from: https://openrouter.ai/keys"
            )
        
        self._client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key
        )
        
        # Model configuration
        self._primary_model = config.get("primary_model", "meta-llama/llama-3.1-8b-instruct:free")
        self._fallback_model = config.get("fallback_model", "microsoft/phi-3-mini-128k-instruct:free")
        self._second_fallback = config.get("second_fallback_model", "mistralai/mistral-7b-instruct:free")
        self._max_tokens = config.get("max_tokens", 300)
        self._temperature = config.get("temperature", 0.85)
        self._stream = config.get("stream", True)
        
        # Memory
        self._max_turns = config.get("max_turns", 20)
        self._conversation_file = self._memory_dir / "conversation.json"
        self._profile_file = self._memory_dir / "user_profile.json"
        self._conversation_history: List[Dict[str, str]] = []
        self._user_profile: Dict[str, Any] = {}
        
        # Load memory
        self._load_memory()
        
        logger.info("Yuki's brain initialized")
    
    def _load_memory(self) -> None:
        """Load conversation history and user profile from disk."""
        # Load conversation history
        if self._conversation_file.exists():
            try:
                with open(self._conversation_file, 'r', encoding='utf-8') as f:
                    self._conversation_history = json.load(f)
                logger.info(f"Loaded {len(self._conversation_history)} conversation turns")
            except Exception as e:
                logger.error(f"Failed to load conversation history: {e}")
                self._conversation_history = []
        
        # Load user profile
        if self._profile_file.exists():
            try:
                with open(self._profile_file, 'r', encoding='utf-8') as f:
                    self._user_profile = json.load(f)
                logger.info(f"Loaded user profile: {self._user_profile.get('name', 'Unknown')}")
            except Exception as e:
                logger.error(f"Failed to load user profile: {e}")
                self._user_profile = {"name": "User"}
    
    def _save_memory(self) -> None:
        """Save conversation history and user profile to disk."""
        # Ensure memory directory exists
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Save conversation history (trim to max turns)
        try:
            history_to_save = self._conversation_history[-self._max_turns:]
            with open(self._conversation_file, 'w', encoding='utf-8') as f:
                json.dump(history_to_save, f, indent=2, ensure_ascii=False)
            logger.debug("Saved conversation history")
        except Exception as e:
            logger.error(f"Failed to save conversation history: {e}")
        
        # Save user profile
        try:
            with open(self._profile_file, 'w', encoding='utf-8') as f:
                json.dump(self._user_profile, f, indent=2, ensure_ascii=False)
            logger.debug("Saved user profile")
        except Exception as e:
            logger.error(f"Failed to save user profile: {e}")
    
    def ask(self, user_message: str, is_wakeword: bool = False) -> Generator[str, None, None]:
        """
        Ask Yuki a question and get streaming response.
        
        Args:
            user_message: User's message
            is_wakeword: If True, use a wakeword greeting response
        
        Yields:
            Response text chunks (for streaming TTS)
        """
        # Handle wakeword greeting
        if is_wakeword:
            greeting = random.choice(WAKEWORD_RESPONSES)
            logger.info(f"Wakeword greeting: {greeting}")
            yield greeting
            return
        
        logger.info(f"User: {user_message}")
        
        # Build messages for API
        messages = [
            {"role": "system", "content": Yuki_SYSTEM_PROMPT}
        ]
        
        # Add conversation history (last N turns)
        for turn in self._conversation_history[-self._max_turns:]:
            messages.append(turn)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Try primary model, fallback if needed
        response_text = ""
        
        for model in [self._primary_model, self._fallback_model, self._second_fallback]:
            try:
                logger.debug(f"Trying model: {model}")
                
                if self._stream:
                    # Streaming response
                    stream = self._client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=self._max_tokens,
                        temperature=self._temperature,
                        stream=True,
                        extra_headers={
                            "HTTP-Referer": "Yuki-desktop-assistant",
                            "X-Title": "Yuki"
                        }
                    )
                    
                    for chunk in stream:
                        if chunk.choices[0].delta.content:
                            content = chunk.choices[0].delta.content
                            response_text += content
                            yield content
                else:
                    # Non-streaming response
                    response = self._client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=self._max_tokens,
                        temperature=self._temperature,
                        stream=False,
                        extra_headers={
                            "HTTP-Referer": "Yuki-desktop-assistant",
                            "X-Title": "Yuki"
                        }
                    )
                    
                    response_text = response.choices[0].message.content
                    yield response_text
                
                # Success - break out of fallback loop
                logger.info(f"Yuki: {response_text}")
                break
                
            except Exception as e:
                logger.error(f"Error with model {model}: {e}")
                
                if model == self._second_fallback:
                    # All models failed
                    error_response = "...something's wrong. Try again."
                    logger.error("All LLM models failed")
                    yield error_response
                    response_text = error_response
                else:
                    # Try next fallback
                    continue
        
        # Save to memory
        self._conversation_history.append({"role": "user", "content": user_message})
        self._conversation_history.append({"role": "assistant", "content": response_text})
        self._save_memory()
    
    def parse_intent(self, response_text: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON intent from Yuki's response.
        
        Args:
            response_text: Yuki's response text
        
        Returns:
            Parsed intent dict, or None if not a JSON intent
        """
        response_text = response_text.strip()
        
        # Check if response looks like JSON
        if not (response_text.startswith('{') and response_text.endswith('}')):
            return None
        
        try:
            intent = json.loads(response_text)
            
            # Validate required fields
            if "intent" not in intent:
                logger.warning("Intent JSON missing 'intent' field")
                return None
            
            logger.debug(f"Parsed intent: {intent['intent']}")
            return intent
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse intent JSON: {e}")
            return None
    
    def get_dismissal_message(self) -> str:
        """Get a random dismissal message for when conversation ends."""
        return random.choice(DISMISSAL_MESSAGES)
    
    def clear_conversation(self) -> None:
        """Clear conversation history."""
        self._conversation_history.clear()
        self._save_memory()
        logger.info("Conversation history cleared")
    
    def get_user_name(self) -> str:
        """Get user's name from profile."""
        return self._user_profile.get("name", "User")
    
    def set_user_name(self, name: str) -> None:
        """Set user's name in profile."""
        self._user_profile["name"] = name
        self._save_memory()
        logger.info(f"User name set to: {name}")


def create_Yuki_brain(config: dict, memory_dir: Path) -> YukiBrain:
    """
    Factory function to create Yuki's brain.
    
    Args:
        config: LLM configuration dict
        memory_dir: Directory for conversation memory
    
    Returns:
        Initialized YukiBrain instance
    """
    return YukiBrain(config, memory_dir)

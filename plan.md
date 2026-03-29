# Yukino AI Waifu Assistant - Implementation Plan

## Project Overview

Building **Yukino** - a Python desktop AI waifu assistant based on Yukino Yukinoshita from OreGairu. She's a floating desktop overlay that wakes on voice command, talks in character, and controls the PC. All processing is local except LLM (OpenRouter free API).

**Target Hardware:**
- GPU: RTX 2050, 4GB VRAM (minimal usage - avatar only)
- RAM: 16GB
- OS: Windows 11

## Core Requirements

1. **Voice-activated wake system** - Hidden by default, shows on "Hey Yukino"
2. **3D VRM Avatar** - PyQt6 OpenGL renderer with lip sync and animations
3. **Personality-driven LLM** - OpenRouter API with Yukino Yukinoshita character
4. **PC Control** - File ops, shell commands, system controls (volume, brightness, etc.)
5. **Undo System** - Reversible actions with 20-action history
6. **Always-on-top overlay** - Frameless, transparent, draggable window
7. **System tray integration** - Hidden state management

## Implementation Strategy

**Phased approach:** Setup → Foundation → Core Features → Avatar → Polish → Testing

This allows testing each component before adding complexity.

## Architecture

```
yukino/
├── main.py                    # Entry point, signal routing
├── config.yaml                # All configuration
├── .env                       # API keys (gitignored)
├── requirements.txt           # Dependencies
├── setup.py                   # First-run setup script
├── core/
│   ├── listener.py            # Mic + VAD + Whisper STT
│   ├── wakeword.py            # Hotword detection (Porcupine + Whisper)
│   ├── brain.py               # OpenRouter LLM + memory + personality
│   ├── action_router.py       # Intent → action dispatch
│   ├── undo_stack.py          # Action rollback system
│   └── tts.py                 # pyttsx3 voice output
├── actions/
│   ├── file_ops.py            # File/folder operations
│   ├── shell_exec.py          # Allowlisted shell commands
│   ├── system_ctrl.py         # Volume, brightness, wifi, bluetooth
│   ├── app_ctrl.py            # Open/close applications
│   └── browser_ctrl.py        # URL/search operations
├── avatar/
│   ├── renderer.py            # VRM loader + OpenGL renderer
│   ├── lipsync.py             # Phoneme → blend shape mapping
│   └── animations.py          # Idle, mood states, blinking
├── ui/
│   ├── main_window.py         # Overlay window + system tray
│   ├── chat_panel.py          # Scrollable chat history
│   ├── status_bar.py          # Status indicator widget
│   └── styles.qss             # Dark anime Qt stylesheet
├── memory/
│   ├── conversation.json      # Rolling 20-turn history
│   └── user_profile.json      # User name + preferences
├── data/
│   ├── yukino.vrm             # VRM model (user-provided)
│   └── command_allowlist.txt  # Safe shell commands
└── tests/
    ├── test_brain.py
    ├── test_action_router.py
    ├── test_undo_stack.py
    ├── test_file_ops.py
    └── test_system_ctrl.py
```

## Dependencies

```
openai                          # OpenRouter client
python-dotenv                   # Environment variables
sounddevice                     # Audio capture
webrtcvad-wheels                # Voice activity detection
openai-whisper                  # Speech-to-text
pvporcupine                     # Hotword detection
pyttsx3                         # Text-to-speech
PyQt6                           # GUI framework
PyOpenGL                        # 3D rendering
pygltflib                       # VRM model loading
pyautogui                       # GUI automation support
pycaw                           # Windows audio control
screen-brightness-control       # Display brightness
pygame                          # Audio playback
numpy                           # Array operations
torch                           # Whisper backend
pytest                          # Testing framework
pytest-qt                       # Qt testing
pytest-mock                     # Mocking support
PyYAML                          # Config file parsing
```

## Key Technical Decisions

### Wakeword Detection
- **Primary:** Picovoice Porcupine (accurate, low latency)
- **Fallback:** Whisper continuous transcription (no setup required)
- **Toggle:** `config.yaml` → `wakeword.method: "porcupine" | "whisper"`

### VRM Avatar
- **With model:** Full 3D rendering with lip sync and animations
- **Without model:** Placeholder gray silhouette + log warning
- **Graceful degradation:** App works fully even if VRM missing

### LLM Integration
- **Primary Model:** `meta-llama/llama-3.1-8b-instruct:free`
- **Fallback 1:** `microsoft/phi-3-mini-128k-instruct:free`
- **Fallback 2:** `mistralai/mistral-7b-instruct:free`
- **Streaming:** Token-by-token with sentence-based TTS trigger
- **Memory:** Last 20 conversation turns

### Personality System
**Yukino Yukinoshita character:**
- Razor-sharp intellect, blunt and precise
- Outward coldness masking genuine care
- Formal Japanese registers ("sou desu ne", "ara", "maa")
- Never overenthusiastic, deflects compliments
- **Always asks confirmation before PC actions**

### Safety & Undo
- File operations limited to user home directory
- Shell commands filtered through allowlist
- All destructive actions push to undo stack
- 20-action undo depth with full rollback

## Testing Strategy

### Unit Tests (pytest)
- `test_brain.py` - LLM integration, memory, fallback handling
- `test_action_router.py` - Intent parsing and routing
- `test_undo_stack.py` - Snapshot creation and rollback
- `test_file_ops.py` - File operations with temp directories
- `test_system_ctrl.py` - Mock system control calls
- `test_tts.py` - TTS initialization and streaming
- `test_listener.py` - Audio processing pipeline

### Integration Tests
- Wakeword → window show → listener active
- User speech → transcription → LLM → TTS → response
- Action intent → confirmation → execution → undo
- Conversation timeout → dismissal → window hide
- System tray interactions

### Manual Testing Checklist
- [ ] Wakeword detection (both Porcupine and Whisper modes)
- [ ] Avatar rendering (with and without VRM file)
- [ ] Lip sync during TTS
- [ ] Window dragging and positioning
- [ ] System tray show/hide/quit
- [ ] All action modules (file, shell, system, app, browser)
- [ ] Undo stack rollback
- [ ] Memory persistence across sessions
- [ ] OpenRouter API with all three fallback models
- [ ] Yukino personality consistency
- [ ] Graceful error handling

## Notes

- **No stubs:** Every file fully implemented
- **Type hints:** All functions and methods
- **Logging:** Python logging module throughout (no print statements)
- **Thread safety:** All threads are daemon threads
- **Qt signals:** Properly typed with pyqtSignal
- **Error resilience:** Graceful degradation when components fail
- **User permission:** Always ask before executing actions (built into personality)
- **VRAM optimization:** Only avatar uses GPU, everything else CPU-based

## Critical Path

1. ✅ Project structure setup
2. ✅ Configuration system
3. ✅ Core audio pipeline (listener + wakeword)
4. ✅ LLM integration + personality
5. ✅ TTS streaming
6. ✅ Basic UI + system tray
7. ✅ Action modules
8. ✅ Undo system
9. ✅ Avatar renderer
10. ✅ Full integration + testing

## Success Criteria

The app is complete when:
1. Yukino wakes on voice command
2. Responds in character with accurate personality
3. All action modules work with undo support
4. Avatar renders and lip syncs (or shows placeholder gracefully)
5. Window management (show/hide/tray) works smoothly
6. Memory persists across sessions
7. All tests pass
8. No crashes on missing VRM or API errors

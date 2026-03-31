# Yukino AI Voice Assistant - Implementation Plan (REVISED)

**Status:** Architecture Change - Refactoring to Voice-Only  
**Progress:** Core systems complete, refactoring UI for voice-only mode  
**Last Updated:** 2026-03-31

## Project Overview

Building **Yukino** - a Python voice-based AI assistant based on Yukino Yukinoshita from OreGairu. She runs as a background voice agent that wakes on voice command, responds in character with realistic voice synthesis, and controls the PC. All processing is local except LLM (OpenRouter free API).

**Target Hardware:**
- GPU: RTX 2050, 4GB VRAM (minimal usage - LuxTTS only if needed)
- RAM: 16GB
- OS: Windows 11

## Core Requirements (REVISED)

1. **Voice-activated wake system** - Background service, responds to "Hey Yukino"
2. **High-quality TTS** - LuxTTS for realistic voice cloning and natural speech
3. **Personality-driven LLM** - OpenRouter API with Yukino Yukinoshita character
4. **PC Control** - File ops, shell commands, system controls (volume, brightness, etc.)
5. **Undo System** - Reversible actions with 20-action history
6. **Minimal status UI** - Small text window showing conversation + status
7. **System tray integration** - Always-running background service

## Implementation Strategy

**Phased approach:** Setup → Foundation → Core Features → Avatar → Polish → Testing

This allows testing each component before adding complexity.

## Architecture (REVISED - Voice-Only)

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
│   └── tts.py                 # LuxTTS voice synthesis (UPDATED)
├── actions/
│   ├── file_ops.py            # File/folder operations ✅
│   ├── shell_exec.py          # Allowlisted shell commands ✅
│   ├── system_ctrl.py         # Volume, brightness, wifi, bluetooth ✅
│   ├── app_ctrl.py            # Open/close applications ✅
│   └── browser_ctrl.py        # URL/search operations ✅
├── avatar/                    # 🗑️ REMOVED - No longer needed
├── ui/
│   ├── status_window.py       # Minimal status + chat text (NEW)
│   └── styles.qss             # Simple dark stylesheet (SIMPLIFIED)
├── memory/
│   ├── conversation.json      # Rolling 20-turn history
│   └── user_profile.json      # User name + preferences
├── data/
│   ├── yukino_voice.wav       # Reference audio for voice cloning (NEW)
│   └── command_allowlist.txt  # Safe shell commands ✅
└── tests/
    ├── test_brain.py
    ├── test_action_router.py
    ├── test_undo_stack.py
    ├── test_file_ops.py
    └── test_system_ctrl.py
```

**Key Changes:**
- ✅ Removed all avatar/ components (renderer, lipsync, animations)
- ✅ Replaced complex overlay UI with minimal status window
- ✅ Replaced pyttsx3 with LuxTTS for high-quality voice synthesis
- ✅ Added reference audio file for voice cloning
- ✅ Kept all action modules (already complete)
- ✅ Kept core systems (listener, wakeword, brain, router, undo)

## Dependencies (REVISED)

```
# Core
openai                          # OpenRouter client
python-dotenv                   # Environment variables
PyYAML                          # Config file parsing

# Audio - Input
sounddevice                     # Audio capture
webrtcvad-wheels                # Voice activity detection
openai-whisper                  # Speech-to-text
pvporcupine                     # Hotword detection

# Audio - Output (NEW)
soundfile                       # Audio file I/O for LuxTTS
# LuxTTS will be installed from GitHub

# UI (Minimal)
PyQt6                           # GUI framework (status window only)
pygame                          # Audio playback and chimes

# System Control
pyautogui                       # GUI automation support
pycaw                           # Windows audio control
screen-brightness-control       # Display brightness

# ML Backend
numpy                           # Array operations
torch                           # Whisper + LuxTTS backend

# Testing
pytest                          # Testing framework
pytest-qt                       # Qt testing
pytest-mock                     # Mocking support

# REMOVED:
# - PyOpenGL (no 3D rendering)
# - pygltflib (no VRM models)
# - pyttsx3 (replaced by LuxTTS)
```

## Key Technical Decisions

### Wakeword Detection
- **Primary:** Picovoice Porcupine (accurate, low latency)
- **Fallback:** Whisper continuous transcription (no setup required)
- **Toggle:** `config.yaml` → `wakeword.method: "porcupine" | "whisper"`

### LuxTTS Voice Synthesis (NEW)
- **Voice cloning:** Uses reference audio file (yukino_voice.wav) for consistent character voice
- **Quality:** 48kHz output, clear and natural speech
- **Speed:** 150x realtime on GPU, faster than realtime on CPU
- **Efficiency:** <1GB VRAM, can run on CPU if needed
- **Fallback:** If LuxTTS fails, log warning and continue without voice (text-only mode)

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

## Testing Strategy (REVISED)

### Unit Tests (pytest)
- `test_brain.py` - LLM integration, memory, fallback handling ✅
- `test_action_router.py` - Intent parsing and routing ✅
- `test_undo_stack.py` - Snapshot creation and rollback ✅
- `test_file_ops.py` - File operations with temp directories ✅
- `test_system_ctrl.py` - Mock system control calls ✅
- `test_tts_luxtts.py` - LuxTTS initialization and voice generation (NEW)
- `test_listener.py` - Audio processing pipeline ✅

### Integration Tests
- Wakeword → service activation → listener active
- User speech → transcription → LLM → LuxTTS → voice response
- Action intent → confirmation → execution → undo
- Conversation timeout → dismissal → service returns to idle
- System tray interactions

### Manual Testing Checklist
- [ ] Wakeword detection (both Porcupine and Whisper modes)
- [ ] LuxTTS voice quality and cloning (NEW)
- [ ] Status window display and updates (REVISED)
- [ ] System tray show/hide/quit
- [ ] All action modules (file, shell, system, app, browser) ✅
- [ ] Undo stack rollback ✅
- [ ] Memory persistence across sessions
- [ ] OpenRouter API with all three fallback models
- [ ] Yukino personality consistency
- [ ] Graceful error handling
- [ ] Audio cues for state changes (listening, thinking, speaking)

## Notes

- **No stubs:** Every file fully implemented
- **Type hints:** All functions and methods
- **Logging:** Python logging module throughout (no print statements)
- **Thread safety:** All threads are daemon threads
- **Qt signals:** Properly typed with pyqtSignal
- **Error resilience:** Graceful degradation when components fail
- **User permission:** Always ask before executing actions (built into personality)
- **VRAM optimization:** Only avatar uses GPU, everything else CPU-based

## Critical Path (REVISED)

1. ✅ Project structure setup
2. ✅ Configuration system
3. ✅ Core audio pipeline (listener + wakeword)
4. ✅ LLM integration + personality
5. 🔄 **UPDATING: LuxTTS integration** (replacing pyttsx3)
6. 🔄 **UPDATING: Minimal status window** (replacing complex overlay)
7. ✅ Action modules (all complete)
8. ✅ Undo system
9. ❌ ~~Avatar renderer~~ (REMOVED)
10. 🔜 Full integration + testing

## Success Criteria (REVISED)

The app is complete when:
1. ✅ Yukino wakes on voice command (wakeword system working)
2. ✅ Responds in character with accurate personality (LLM working)
3. ✅ All action modules work with undo support (complete)
4. 🔄 **High-quality voice synthesis with LuxTTS** (in progress)
5. 🔄 **Status window shows conversation and state** (in progress)
6. ✅ System tray management works smoothly
7. 🔜 Memory persists across sessions
8. 🔜 All tests pass
9. 🔜 Graceful degradation for missing voice files or API errors

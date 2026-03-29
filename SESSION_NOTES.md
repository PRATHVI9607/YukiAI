# Yukino AI - Session Resume Notes

**Session Date:** 2026-03-28  
**Status:** Phase 1 Complete, Ready for Phase 2

---

## Project Context

Building **Yukino AI Waifu Assistant** - A voice-activated desktop AI assistant based on Yukino Yukinoshita from OreGairu. Full specs in `Prompt.md`.

---

## Important User Preferences (MUST REMEMBER)

1. **🔐 Permission Protocol:** ALWAYS ask permission before:
   - Running any commands
   - Installing packages
   - Creating/modifying files
   - Making any changes

2. **📁 File Locations:** 
   - `plan.md` and `task.md` are in PROJECT ROOT (`C:\Workspace\YukinoAI\`)
   - NOT in .copilot folder

3. **Implementation Choices:**
   - ✅ Build BOTH VRM renderer AND placeholder (graceful degradation)
   - ✅ Build BOTH Porcupine AND Whisper wakeword (config toggle)
   - ✅ Full pytest test suite required
   - ✅ Phased iterative development (not all at once)

4. **User Quote:** "i love you so build this properly pls" - Take this seriously, build quality code

---

## Current Progress

### ✅ Phase 1 Complete (3/30 tasks)
- ✅ setup-project - Full directory structure created
- ✅ config-files - config.yaml, requirements.txt, setup.py
- ✅ env-template - .env.example with API key instructions

### ✅ Phase 2 Complete (6/30 tasks) 
**Core modules (~/core/) all implemented:**
- ✅ undo_stack.py - Thread-safe rollback system (305 lines)
- ✅ tts.py - Streaming TTS with Qt signals (346 lines)
- ✅ listener.py - VAD + Whisper STT (380 lines)
- ✅ wakeword.py - Dual detection methods (378 lines)
- ✅ brain.py - OpenRouter + Yukino personality (348 lines)
- ✅ action_router.py - Intent dispatcher (345 lines)

### 🎯 Current: Phase 3 - Action Modules (0/5 tasks)
Ready to implement:
1. **file-ops** - File/folder operations with security
2. **shell-exec** - Allowlisted shell commands
3. **system-ctrl** - Volume, brightness, WiFi, Bluetooth
4. **app-ctrl** - Open/close applications
5. **browser-ctrl** - URL opening and search

### 📋 Remaining Phases:
- **Phase 4:** Avatar & UI (7 tasks) - VRM renderer, main window, chat panel, etc.
- **Phase 5:** Integration (3 tasks) - main.py, memory setup, setup script
- **Phase 6:** Testing & Polish (7 tasks) - Tests, docs, final validation

**Progress: 9/30 tasks (30%)**

---

## Technical Decisions Made

### Architecture
- **Language:** Python 3.10+
- **GUI:** PyQt6 (frameless overlay, always-on-top)
- **Audio:** sounddevice, webrtcvad, Whisper (CPU), pyttsx3
- **LLM:** OpenRouter free tier (Llama 3.1 8B primary)
- **Avatar:** PyOpenGL + pygltflib for VRM rendering
- **Memory:** Rolling 20-turn JSON conversation history

### Key Implementation Rules
- ✅ NO stubs or TODOs - full implementations only
- ✅ Type hints everywhere
- ✅ Python logging module (not print statements)
- ✅ All threads are daemon threads
- ✅ Proper Qt signal typing with pyqtSignal
- ✅ Graceful degradation for all optional features
- ✅ Security: file ops limited to user home directory
- ✅ Shell commands filtered through allowlist

### Yukino Personality System
- Razor-sharp intellect, blunt and precise
- Outward coldness masking genuine care
- Formal Japanese registers ("ara", "sou desu ne", "maa")
- **ALWAYS asks confirmation before PC actions** (built into character)
- Never overenthusiastic, deflects compliments
- System prompt injected on EVERY LLM call

---

## Project Structure Created

```
C:\Workspace\YukinoAI\
├── plan.md              ← Full technical plan
├── task.md              ← Progress tracker (updated)
├── SESSION_NOTES.md     ← This file - resume context
├── Prompt.md            ← Original requirements
└── yukino/
    ├── __init__.py
    ├── config.yaml      ← Complete configuration ✅
    ├── requirements.txt ← All dependencies ✅
    ├── setup.py         ← First-run setup script ✅
    ├── .env.example     ← API key template ✅
    ├── core/            ← ALL COMPLETE ✅
    │   ├── __init__.py
    │   ├── undo_stack.py     ✅ 305 lines
    │   ├── tts.py            ✅ 346 lines
    │   ├── listener.py       ✅ 380 lines
    │   ├── wakeword.py       ✅ 378 lines
    │   ├── brain.py          ✅ 348 lines
    │   └── action_router.py  ✅ 345 lines
    ├── actions/         ← PHASE 3 (NEXT!)
    │   └── __init__.py  ← Need: 5 modules
    ├── avatar/          ← PHASE 4
    │   └── __init__.py  ← Need: 3 modules
    ├── ui/              ← PHASE 4
    │   └── __init__.py  ← Need: 4 modules + styles.qss
    ├── memory/          ← Empty, for runtime files
    ├── data/            ← Empty, for VRM + allowlist
    └── tests/           ← PHASE 6
        └── __init__.py  ← Need: 5 test files
```

---

## How to Resume This Session

### When starting a new session:

1. **Share Context:**
   ```
   "I'm resuming the Yukino AI project. 
   Please read: plan.md, task.md, and SESSION_NOTES.md"
   ```

2. **I will:**
   - Read all three files
   - Understand current progress (Phase 1 done, Phase 2 next)
   - Remember your preferences (permission protocol, etc.)
   - Continue implementation

3. **To continue implementation:**
   ```
   "Let's continue with Phase 2" or
   "Implement [specific task name]" or
   "What's next?"
   ```

---

## SQL Task Tracking (Session-Specific)

Note: SQL database doesn't persist across sessions, but `task.md` has all info.

**To recreate task tracking in new session:**
```sql
-- Recreate tables
CREATE TABLE todos (id TEXT PRIMARY KEY, title TEXT, description TEXT, 
                    status TEXT DEFAULT 'pending', 
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);

CREATE TABLE todo_deps (todo_id TEXT, depends_on TEXT, 
                        PRIMARY KEY (todo_id, depends_on));

-- Then re-insert all tasks from plan.md if needed
```

**Or just use task.md** - it has all the same information in human-readable format.

---

## Dependencies & Environment

### Not Yet Installed:
- Python packages (requirements.txt not run yet)
- Whisper model (not downloaded yet)
- OpenRouter API key (user needs to add)

### To Setup (when ready):
```bash
cd C:\Workspace\YukinoAI\yukino
python setup.py  # Installs everything, creates defaults
```

---

## Testing Strategy

- Unit tests for all core modules (pytest)
- Integration test for full wakeword→conversation→hide cycle
- Manual testing checklist in plan.md
- No stubs - test real implementations

---

## Known Constraints

- **Hardware:** RTX 2050 (4GB VRAM), 16GB RAM, Windows 11
- **VRAM:** Minimize usage - only avatar uses GPU
- **CPU:** Whisper, TTS, all audio processing on CPU
- **Network:** Only OpenRouter API calls (LLM)

---

## Quick Reference Commands

```bash
# Navigate to project
cd C:\Workspace\YukinoAI

# View progress
cat task.md

# View plan
cat plan.md

# Check structure
tree yukino /F

# When ready to install (with permission):
cd yukino
python setup.py
```

---

## Important Files to Reference

1. **Prompt.md** - Original detailed requirements (20KB)
2. **plan.md** - Full implementation plan with architecture
3. **task.md** - Current progress tracker
4. **SESSION_NOTES.md** (this file) - Context for resuming

---

## Next Session Checklist

- [ ] Read SESSION_NOTES.md (this file)
- [ ] Read task.md for current status
- [ ] Reference plan.md for technical details
- [ ] Ask user if ready to continue Phase 2
- [ ] **ALWAYS ask permission before executing anything**

---

**Remember:** User wants high-quality implementation, no rushing, always ask permission! 💙

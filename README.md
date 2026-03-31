# 🎤 Yuki AI - Voice-Powered Desktop Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1+-red.svg)](https://pytorch.org/)
[![OpenRouter](https://img.shields.io/badge/LLM-OpenRouter-green.svg)](https://openrouter.ai/)
[![LuxTTS](https://img.shields.io/badge/TTS-LuxTTS-purple.svg)](https://github.com/ysharma3501/LuxTTS)

> **Yuki** is an intelligent voice-powered desktop assistant based on Yuki Yukinoshita from *Oregairu*. She runs as a background service on your Windows PC, wakes up when you call her name, responds with realistic cloned voice, and can control your computer through natural conversation. Everything runs locally except the LLM which uses OpenRouter's free API.

---

## 🌟 Features

### 🎙️ Voice Interaction
- **Wake word detection**: Say "Hey Yuki" or "Yuki" to activate
- **Natural speech recognition**: Powered by OpenAI Whisper (runs locally on CPU)
- **High-quality voice synthesis**: LuxTTS with voice cloning (48kHz, GPU-accelerated)
- **Streaming responses**: Speaks each sentence as soon as it's generated

### 🧠 Intelligent Personality
- **Character-accurate responses**: Yuki's sharp intellect, dry wit, and hidden warmth
- **Context-aware memory**: Remembers last 20 conversation turns
- **LLM-powered**: Uses OpenRouter free API (google/gemma-3-27b-it)
- **Streaming generation**: Low-latency responses with sentence-by-sentence TTS

### 💻 PC Control
- **File operations**: Create, delete, move files and folders (with safety checks)
- **Shell commands**: Execute allowlisted commands with timeout protection
- **System control**: Adjust volume, brightness, WiFi, Bluetooth
- **Application management**: Open/close apps (Chrome, VS Code, Discord, etc.)
- **Web browsing**: Open URLs and perform searches
- **Undo system**: Rollback destructive actions (20-action history)

### 🖥️ User Interface
- **Minimal status window**: Clean 400x300px window showing conversation history
- **System tray integration**: Always-running background service
- **Auto-hide**: Window appears on wake word, hides after conversation timeout
- **Audio cues**: Chimes and beeps for state changes

---

## 🎯 Use Cases

- **Hands-free PC control**: Control your computer while cooking, exercising, or away from keyboard
- **Quick tasks**: "Yuki, open Chrome and search for Python tutorials"
- **System management**: "Set volume to 50%", "Increase brightness"
- **File operations**: "Create a folder called Projects", "Delete temp.txt"
- **Casual conversation**: Chat with an AI that has actual personality
- **Productivity**: Get things done without breaking your workflow

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Yuki AI Assistant                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌───────────────┐      ┌────────────┐    │
│  │   Wakeword   │────> │   Listener    │────> │   Brain    │    │
│  │  Detection   │      │   (Whisper)   │      │ (OpenRouter│    │
│  │  (Whisper)   │      │   + VAD       │      │    LLM)    │    │
│  └──────────────┘      └───────────────┘      └──────┬─────┘    │
│         │                                           │           │
│         │                                           ▼           │
│  ┌──────▼──────┐     ┌───────────────┐       ┌────────────┐     │
│  │   System    │     │     TTS       │ <──── │   Action   │     │
│  │    Tray     │     │  (LuxTTS)     │       │   Router   │     │
│  │   + Menu    │     │  Voice Clone  │       └──────┬─────┘     │
│  └──────┬──────┘     └───────────────┘              │           │
│         │                                           ▼           │
│         ▼                                  ┌─────────────────┐  │
│  ┌─────────────┐                           │     Actions     │  │
│  │   Status    │                           ├─────────────────┤  │
│  │   Window    │                           │ • File Ops      │  │
│  │ (Text UI)   │                           │ • Shell Exec    │  │
│  └─────────────┘                           │ • System Ctrl   │  │
│                                            │ • App Control   │  │
│                                            │ • Browser       │  │
│                                            └─────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

       Local Processing                      Cloud Processing
    ┌────────────────────────┐          ┌────────────────────┐
    │ • Whisper (CPU/GPU)    │          │  OpenRouter API    │
    │ • LuxTTS (GPU/CPU)     │─────────>│  Free LLM Models   │
    │ • WebRTC VAD           │  HTTPS   │  Streaming Tokens  │
    │ • All Actions Local    │          │  No Data Stored    │
    └────────────────────────┘          └────────────────────┘
```

### Core Components

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Wakeword** | Whisper (continuous transcription) | Detect "Yuki" in audio stream |
| **Speech Recognition** | OpenAI Whisper (base.en) | Convert speech to text (VAD-triggered) |
| **Voice Activity Detection** | WebRTC VAD | Detect when user is speaking |
| **LLM Brain** | OpenRouter API (Llama 3.1 8B) | Generate responses with personality |
| **Voice Synthesis** | LuxTTS (voice cloning) | High-quality 48kHz speech output |
| **Action Router** | Intent parser | Dispatch commands to action modules |
| **Undo Stack** | Snapshot-based rollback | Reverse destructive operations |
| **UI** | PyQt6 (minimal) | Status window and system tray |

---

## 🔧 How It Works (Technical Deep Dive)

### 1. Wakeword Detection Flow

```
[Microphone] ─────▶ [Audio Buffer (2s chunks)] ─────▶ [Whisper Transcription]
                           │                                    │
                           │                                    ▼
                           │                          [Text: "hey yuki"]
                           │                                    │
                           │                                    ▼
                           │                          [Keyword Match?]
                           │                                    │
                           │                                    ├─ NO ──▶ [Discard]
                           │                                    │
                           │                                    └─ YES ─▶ [Emit Signal]
                           │                                              │
                           └──────────────────────────────────────────────┘
                                                                          │
                                                                          ▼
                                                        [Show Window + Start Listening]
```

**How wakeword detection works:**
1. **Continuous audio capture**: Records from microphone in 2-second chunks
2. **Whisper transcription**: Each chunk is transcribed using Whisper base.en model
3. **Keyword matching**: Checks if "yuki" appears in transcription (case-insensitive)
4. **Signal emission**: On match, Qt signal triggers window to show and listener to activate
5. **Low CPU impact**: Runs on separate daemon thread, ~15-20% CPU usage

**Alternative (Porcupine)**: For better accuracy, can use Picovoice Porcupine wake word engine (requires API key).

---

### 2. Speech Recognition Pipeline

```
[User Speaks] ─────▶ [VAD Detection] ─────▶ [Audio Buffering] ─────▶ [Whisper]
                           │                        │                      │
                           │                        │                      ▼
                      [Is Speech?]            [Accumulate              [Text Output]
                           │                   Frames]                     │
                           ├─ NO ──> [Ignore]      │                       │
                           │                       │                       ▼
                           └─ YES ─> [Buffer] ─────┤                 [Send to Brain]
                                                   │
                                            [Silence > 1.5s?]
                                                   │
                                                   └─ YES ─▶ [Stop Recording]
```

**Speech recognition details:**
1. **VAD (Voice Activity Detection)**: WebRTC VAD detects when user is speaking
   - Aggressiveness level: 2 (balanced)
   - Sample rate: 16kHz mono
   - Filters out background noise

2. **Audio buffering**: Speech frames are accumulated in memory
   - Stops buffering after 1.5s of silence
   - Prevents cutting off long sentences

3. **Whisper transcription**: 
   - Model: `base.en` (74M parameters)
   - Device: CPU (to save VRAM for LuxTTS)
   - Processes entire buffered audio at once
   - Typical transcription time: 2-4 seconds

4. **Output**: Transcribed text sent to Brain module for processing

---

### 3. LLM Brain & Personality System

```
[User Text] ─────▶ [Load Memory] ─────▶ [Build Prompt] ─────▶ [OpenRouter API]
                         │                     │                      │
                         │                     │                      ▼
                   [Last 20 turns]     [System Prompt +         [Stream Tokens]
                         │              Conversation +                │
                         │              User Message]                 │
                         │                                            ▼
                         │                                   [Parse for Actions]
                         │                                            │
                         │                                            ├─ JSON? ─▶ [Action Router]
                         │                                            │
                         │                                            └─ Text? ─▶ [TTS]
                         │                                                         │
                         └─────────────────────────────────────────────────────────┤
                                                                                   ▼
                                                                        [Save to Memory]
```

**Brain processing steps:**

1. **Memory loading**:
   - Reads `memory/conversation.json`
   - Loads last 20 conversation turns (user + assistant pairs)
   - Provides context for coherent conversations

2. **Prompt construction**:
   ```python
   messages = [
       {"role": "system", "content": YUKINO_PERSONALITY_PROMPT},
       ...last_20_turns,
       {"role": "user", "content": user_message}
   ]
   ```

3. **OpenRouter streaming**:
   - Primary model: `google/gemma-3-27b-it:free`
   - Fallback models: `qwen/qwen3-coder:free`, `nvidia/nemotron-3-nano-30b-a3b:free`
   - Streaming enabled: Tokens arrive incrementally
   - Headers: `HTTP-Referer` and `X-Title` for tracking

4. **Response parsing**:
   - **JSON response**: `{"intent": "...", "params": {...}}` → Route to action modules
   - **Text response**: Plain text → Send directly to TTS
   - **Streaming**: Split on sentence boundaries (`.!?`) and speak each sentence immediately

5. **Memory persistence**:
   - Append user message and assistant response
   - Trim to last 20 turns
   - Save to JSON file

**Personality implementation**:
The system prompt defines Yukino's character traits:
- Short, precise sentences (enforced by `max_tokens: 300`)
- Formal Japanese phrases ("ara", "sou desu ne")
- Blunt confirmation questions before actions
- Temperature: 0.85 (balanced creativity/consistency)

---

### 4. Action Router & Execution

```
[JSON Intent] ─────▶ [Parse Intent Type] ─────▶ [Route to Module]
                              │                         │
                              │                         ▼
                        [Validation]           ┌─────────────────┐
                              │                │  Action Module  │
                              │                ├─────────────────┤
                              ▼                │ • file_ops      │
                     [Ask Confirmation]        │ • shell_exec    │
                              │                │ • system_ctrl   │
                              ▼                │ • app_ctrl      │
                     [User Confirms?]          │ • browser_ctrl  │
                              │                └────────┬────────┘
                              ├─ NO ──▶ [Cancel]       │
                              │                         ▼
                              └─ YES ─▶ [Push to       [Execute Action]
                                         Undo Stack]           │
                                                               ▼
                                                        [Return Result]
                                                               │
                                                               ▼
                                                        [Speak Response]
```

**Action execution process:**

1. **Intent parsing**: Brain returns JSON like:
   ```json
   {
     "intent": "file_create",
     "params": {"path": "test.txt", "content": "hello"},
     "confirmation_message": "Create file test.txt. Are you certain?",
     "spoken_response": "Done. Was that what you wanted?"
   }
   ```

2. **Confirmation**: Yuki speaks the confirmation message and waits for user's yes/no

3. **Undo snapshot**: Before execution, create rollback snapshot:
   - File operations: Save original content/state
   - System changes: Record previous settings (volume, brightness)
   - Shell commands: Log only (non-reversible)

4. **Module execution**:
   - **file_ops**: File/folder creation, deletion, moving (restricted to home directory)
   - **shell_exec**: Execute allowlisted commands with 30s timeout
   - **system_ctrl**: Volume, brightness, WiFi, Bluetooth control (Windows APIs)
   - **app_ctrl**: Launch/kill processes (psutil)
   - **browser_ctrl**: Open URLs with default browser

5. **Result handling**:
   - Success: Speak the `spoken_response`
   - Failure: Speak error message in character
   - Log all actions for debugging

---

### 5. LuxTTS Voice Synthesis

```
[Text Input] ─────▶ [Sentence Splitter] ─────▶ [Synthesis Queue]
                             │                         │
                             │                         ▼
                    [Split on .!?]            [Worker Thread]
                             │                         │
                             ▼                         ▼
                    ["sentence 1",          [Load Reference Audio]
                     "sentence 2",                    │
                     "sentence 3"]                    ▼
                             │                [Encode Prompt]
                             │                         │
                             └─────────────────────────┤
                                                       ▼
                                           [Generate Audio (GPU)]
                                                       │
                                                       ▼
                                           [48kHz WAV Output]
                                                       │
                                                       ▼
                                           [Pygame Playback]
                                                       │
                                                       ▼
                                           [Emit sentence_complete]
```

**LuxTTS synthesis details:**

1. **Reference audio encoding** (once at startup):
   - Loads `data/yuki_voice.wav` (male voice sample)
   - Encodes into latent representation using LuxTTS encoder
   - Takes ~10 seconds on first load (librosa initialization)
   - Cached for entire session

2. **Text preprocessing**:
   - Split text on sentence boundaries: `r'(?<=[.!?])\s+'`
   - Each sentence synthesized independently
   - Enables streaming playback (speak while generating next sentence)

3. **Synthesis parameters**:
   - `num_steps: 4` (quality/speed balance, 3-6 range)
   - `t_shift: 0.9` (sampling parameter, higher = better quality)
   - `speed: 1.0` (speech rate multiplier)
   - `rms: 0.01` (volume normalization)
   - Device: CUDA (150x realtime) or CPU (>1x realtime)

4. **GPU optimization**:
   - Model size: <1GB VRAM
   - Batch processing: Generates full sentence at once
   - Mixed precision: Uses float32 (float16 planned for v1.1)

5. **Audio playback**:
   - Pygame mixer at 48kHz mono
   - Convert torch tensor → numpy array → int16 format
   - Blocking playback (waits for sentence to finish)
   - Stop flag checked during playback for interruption

6. **Graceful fallback**:
   - If LuxTTS fails to load: Continues in text-only mode
   - If synthesis fails: Logs error, skips audio, continues conversation
   - If pygame unavailable: Logs warning, shows text in window

---

### 6. Undo System

```
[Action About to Execute] ─────▶ [Create Snapshot] ─────▶ [Push to Stack]
                                          │                      │
                                          │                      │
                                    [Snapshot Type]        [Max Depth: 20]
                                          │                      │
                                          ▼                      │
                                 ┌─────────────────┐             │
                                 │ • file_create   │             │
                                 │ • file_delete   │             ▼
                                 │ • file_move     │      [Circular Buffer]
                                 │ • folder_create │             │
                                 │ • folder_delete │             │
                                 │ • volume_change │             │
                                 │ • brightness    │             │
                                 │ • shell (log)   │             │
                                 └─────────────────┘             │
                                                                 │
[User Says "Undo"] ─────▶ [Pop from Stack] ─────▶ [Execute Rollback] ─────▶ [Restore State]
                                 │
                                 ▼
                        [Thread-Safe Lock]
```

**Undo mechanism:**

1. **Snapshot creation**: Before any destructive action, capture current state
   - File created: Store `{"path": "file.txt"}` → On undo: `os.remove(path)`
   - File deleted: Store `{"path": "file.txt", "content": bytes}` → On undo: Restore content
   - Folder created: Store `{"path": "folder/"}` → On undo: `shutil.rmtree()`
   - Folder deleted: Store entire directory tree → On undo: Recreate structure
   - Volume/brightness: Store previous value → On undo: Restore setting
   - Shell command: Store command string → On undo: Log only (non-reversible)

2. **Stack management**:
   - Thread-safe with `threading.Lock`
   - Max depth: 20 actions (configurable)
   - Circular buffer: Oldest action dropped when full

3. **Rollback execution**:
   - Pop most recent action
   - Execute reverse operation
   - Return spoken response: *"Reversing previous action. There."*
   - Log all undo operations for audit trail

---

## 🚀 Installation

### Prerequisites

- **OS**: Windows 11 (Windows 10 may work)
- **Python**: 3.10 or higher
- **GPU**: NVIDIA GPU with CUDA support (RTX 2050 or better recommended)
  - LuxTTS can run on CPU but will be slower
- **RAM**: 16GB recommended (8GB minimum)
- **Disk Space**: ~5GB (for models and dependencies)

### Step 1: Clone Repository

```bash
git clone https://github.com/PRATHVI9607/YukiAI.git
cd YukiAI
```

### Step 2: Install Dependencies

```bash
# Install Python dependencies
pip install -r yuki/requirements.txt

# Install LuxTTS from GitHub
git clone https://github.com/ysharma3501/LuxTTS.git temp_luxtts
pip install -r temp_luxtts/requirements.txt
rmdir /s /q temp_luxtts
```

### Step 3: Setup Configuration

```bash
# Run setup script (creates directories, downloads models, etc.)
python yuki/setup.py

# Configure API key
# Edit .env and add your OpenRouter API key:
# OPENROUTER_API_KEY=your_key_here
```

**Get OpenRouter API Key (FREE):**
1. Visit https://openrouter.ai/
2. Sign up for a free account
3. Go to Keys section
4. Create a new API key
5. Copy to `.env` file

### Step 4: Add Reference Audio (Optional)

For best voice quality, provide a reference audio file:

```bash
# Place a 3-10 second WAV file (48kHz) at:
yuki/data/yuki_voice.wav
```

If you don't have one, Yuki will run in text-only mode (no voice output).

**How to get reference audio:**
- Record your own voice or use a voice sample
- Use a free TTS service to generate a sample
- Find a voice clip online (ensure you have rights to use it)
- Convert to WAV 48kHz using a tool like Audacity

---

## 🎮 Usage

### Starting Yuki

```bash
# Navigate to project directory
cd YukiAI

# Run Yuki
python yuki/main.py
```

Yuki will start as a background service with a system tray icon. The status window is hidden by default.

### Waking Yuki

1. Say **"Hey Yuki"** or **"Yuki"** clearly into your microphone
2. Wait for the wake chime sound
3. The status window will appear showing "Listening"
4. Speak your request
5. Yuki will respond with synthesized voice

### Example Commands

**Conversation:**
```
You: "Hey Yuki"
Yuki: "...you called."
You: "What's the weather like today?"
Yuki: "I don't have internet access. But I can help with tasks on your PC."
```

**File Operations:**
```
You: "Create a folder called Projects"
Yuki: "Create a folder called Projects. Are you certain?"
You: "Yes"
Yuki: "Done. Was that what you wanted?"
```

**System Control:**
```
You: "Set volume to 50%"
Yuki: "Setting volume to 50%. One moment."
Yuki: "It's finished. You're welcome. ...I suppose."
```

**Application Control:**
```
You: "Open Chrome and search for Python tutorials"
Yuki: "Open Chrome and search for that? ...Fine. One moment."
```

**Undo:**
```
You: "Undo that"
Yuki: "Reversing previous action. There."
```

### System Tray Menu

Right-click the Yuki system tray icon:
- **Show/Hide Window** - Toggle status window visibility
- **Mute Microphone** - Disable wake word detection
- **Settings** - (Coming soon)
- **Quit** - Exit Yuki

### Conversation Timeout

After 10 seconds of silence following Yuki's last response, she will:
1. Say a dismissal line: *"...I'll be here if you need me."*
2. Hide the status window
3. Return to listening for wake word

---

## ⚙️ Configuration

Edit `yuki/config.yaml` to customize behavior:

### LLM Settings

```yaml
llm:
  primary_model: google/gemma-3-27b-it:free
  fallback_model: qwen/qwen3-coder:free
  max_tokens: 300
  temperature: 0.85  # 0.0-1.0, higher = more creative
  stream: true
```

### Voice Synthesis (LuxTTS)

```yaml
tts:
  device: cuda  # "cuda", "cpu", or "mps" (Mac)
  reference_audio: data/yuki_voice.wav
  num_steps: 4  # 3-6, higher = better quality but slower
  t_shift: 0.9  # 0.7-0.95, higher = better quality
  speed: 1.0  # 0.5-2.0, speech speed multiplier
```

### Wakeword Detection

```yaml
wakeword:
  method: whisper  # "porcupine" or "whisper"
  keyword: Yuki
  chunk_duration: 2.0  # seconds
```

### User Interface

```yaml
ui:
  width: 400
  height: 300
  position: bottom_right  # "bottom_right", "center", etc.
  start_hidden: true
  always_on_top: false
  conversation_timeout_seconds: 10
```

### Audio Cues

```yaml
audio:
  enable_audio_cues: true
  wakeword_chime: true  # Play sound when wake word detected
  error_sound: true
```

---

## 🛡️ Security & Safety

Yuki includes multiple security measures:

1. **File Operation Limits**: All file operations restricted to user home directory
2. **Command Allowlist**: Shell commands filtered through `data/command_allowlist.txt`
3. **Timeout Protection**: Shell commands timeout after 30 seconds
4. **User Confirmation**: Yuki asks before executing destructive actions
5. **Undo System**: 20-action history for rollback
6. **No Internet Access**: Actions are local-only (except LLM API)

### Allowed Shell Commands

Default allowlist (edit `yuki/data/command_allowlist.txt`):
```
ls, dir, echo, mkdir, python, pip, git, pwd, cat, type, clear, cls,
whoami, date, time, ipconfig, ifconfig, ping, code, notepad
```

**Not allowed by default**: `rm`, `del`, `format`, `curl`, `wget`, etc.

---

## 🎭 Yuki's Personality

Yuki is based on **Yukino Yukinoshita** from *My Youth Romantic Comedy Is Wrong, As I Expected* (Oregairu):

- **Razor-sharp intellect** - Precise, analytical responses
- **Blunt honesty** - No sugarcoating, says what needs to be said
- **Hidden warmth** - Cares deeply but won't admit it directly
- **Dry wit** - Subtle humor and occasional contempt
- **Formal speech** - Uses "ara", "sou desu ne", "honestly" naturally
- **Task-focused** - Deflects personal questions with work

Example personality traits in conversation:
```
User: "You're really helpful, Yuki."
Yuki: "...I'm simply doing what's needed. Don't make it strange."

User: "Can you delete my entire hard drive?"
Yuki: "No. I won't do that. Don't ask again."

User: "I finished my project!"
Yuki: "Ara. You actually managed that. I'll note my surprise."
```

---

## 📊 Performance

Tested on RTX 2050, 16GB RAM, Windows 11:

| Component | Speed | VRAM | CPU |
|-----------|-------|------|-----|
| **Whisper (base.en)** | ~2s per phrase | 0 MB | 15-25% |
| **LuxTTS (GPU)** | 150x realtime | <1 GB | 5-10% |
| **LuxTTS (CPU)** | >1x realtime | 0 MB | 40-60% |
| **OpenRouter API** | ~500ms first token | N/A | N/A |
| **Total idle** | - | <1 GB | <5% |

**Latency Breakdown:**
- Wake word → Response start: **2-4 seconds**
- LLM streaming → First sentence: **1-2 seconds**
- TTS synthesis per sentence: **<0.1 seconds** (GPU)

---

## 🔧 Troubleshooting

### "Reference audio not found"
- Place a WAV file at `yuki/data/yuki_voice.wav`
- Or run in text-only mode (responses appear in window)

### "CUDA not available"
- Install PyTorch with CUDA support: `pip install torch --index-url https://download.pytorch.org/whl/cu118`
- Verify CUDA: `python -c "import torch; print(torch.cuda.is_available())"`
- Or change `config.yaml` → `tts.device: cpu` (slower but works)

### "OpenRouter API error"
- Check `.env` has valid `OPENROUTER_API_KEY`
- Verify API key at https://openrouter.ai/
- Check internet connection

### Wake word not detected
- Check microphone permissions in Windows settings
- Increase microphone volume
- Speak clearly and directly into microphone
- Try changing `wakeword.chunk_duration` in config

### High CPU usage
- Reduce `whisper.model` to `tiny.en` or `base.en`
- Change `tts.device` from `cuda` to `cpu` if GPU issues
- Increase `wakeword.check_interval` to reduce checks

---

## 🗺️ Roadmap

### ✅ Version 1.0 (Current - Voice-Only Architecture)
- [x] Whisper-based wake word detection
- [x] LuxTTS voice synthesis with cloning
- [x] OpenRouter LLM integration (streaming)
- [x] 5 action modules (file, shell, system, app, browser)
- [x] Thread-safe undo system (20-action depth)
- [x] Minimal status window UI
- [x] System tray integration
- [x] Conversation memory (20 turns)
- [x] Graceful error handling and fallbacks

### 🔄 Version 1.1 (Next - Enhanced Capabilities)
- [ ] Web search integration (DuckDuckGo API)
- [ ] Screenshot capture and description
- [ ] Email reading and sending
- [ ] Calendar and reminder system
- [ ] Settings UI panel in status window
- [ ] Custom wake word training
- [ ] Float16 precision for faster synthesis

### 🚀 Future (v2.0+ - Advanced Features)
- [ ] Multi-language support (Japanese, Spanish, French)
- [ ] Plugin system for community extensions
- [ ] Voice tuning UI (adjust pitch, speed, tone)
- [ ] Mobile companion app (Android/iOS)
- [ ] Cross-platform support (Linux, macOS)
- [ ] Local LLM option (Ollama integration)
- [ ] Context awareness (screen content, clipboard)

---

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide (use `black` for formatting)
- Add type hints to all functions
- Write comprehensive docstrings (Google style)
- Include unit tests for new features
- Update documentation and README as needed
- Test on Windows 11 before submitting PR

### Project Structure for Contributors

```
yuki/
├── core/           # Core functionality (listener, wakeword, brain, tts, etc.)
├── actions/        # Action modules (file_ops, shell_exec, system_ctrl, etc.)
├── ui/             # User interface (status window, system tray)
├── data/           # Static data (command allowlist, voice reference)
├── memory/         # Persistent storage (conversation history, user profile)
└── tests/          # Unit and integration tests
```

Key files to understand:
- `main.py` - Entry point and signal routing
- `core/brain.py` - LLM integration and personality
- `core/tts.py` - LuxTTS voice synthesis
- `core/action_router.py` - Intent parsing and routing
- `config.yaml` - All configuration settings

---

## 📝 License

This project is open source. Feel free to use, modify, and distribute as needed.

---

## 🙏 Credits & Acknowledgments

### Technologies
- **OpenAI Whisper** - Speech-to-text recognition (https://github.com/openai/whisper)
- **LuxTTS** - High-quality voice synthesis (https://github.com/ysharma3501/LuxTTS)
- **OpenRouter** - Free LLM API access (https://openrouter.ai/)
- **PyQt6** - Cross-platform GUI framework
- **PyTorch** - Machine learning backend
- **WebRTC VAD** - Voice activity detection

### Inspiration
- **Yukino Yukinoshita** character from *Oregairu* by Wataru Watari
- Voice assistants: Jarvis (Iron Man), Cortana (Halo), HAL 9000 (2001: A Space Odyssey)

### Special Thanks
- LuxTTS team (YatharthS) for the amazing voice synthesis model
- OpenRouter for providing free LLM API access
- OpenAI for open-sourcing Whisper
- The open-source AI community

---

## 📧 Contact & Support

- **GitHub Issues**: https://github.com/PRATHVI9607/YukiAI/issues
- **Discussions**: https://github.com/PRATHVI9607/YukiAI/discussions

---

## ⚠️ Disclaimer

This is a fan project inspired by the *Oregairu* anime series. All character rights belong to their respective owners. This software is provided "as is" without warranty of any kind.

**Important considerations:**
- Your conversations are sent to OpenRouter API (privacy policy: https://openrouter.ai/privacy)
- LLM responses may occasionally be inaccurate or inappropriate
- Use responsibly and don't rely on Yuki for critical tasks
- Test all file/system operations carefully before using on important data
- The undo system has limitations (e.g., cannot undo shell commands)

---

<div align="center">

**Made with ❄️ by the YukiAI team**

[⭐ Star this repo](https://github.com/PRATHVI9607/YukiAI) • [🐛 Report Bug](https://github.com/PRATHVI9607/YukiAI/issues) • [💡 Request Feature](https://github.com/PRATHVI9607/YukiAI/issues)

</div>

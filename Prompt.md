Build a Python desktop application called "Yuki" — an AI waifu assistant based on Yuki Yukishita from OreGairu. She lives as a floating desktop overlay, wakes up when I say her name, talks back in character via voice, and can control my PC. Everything runs locally except the LLM which uses OpenRouter free API.

════════════════════════════════════════
HARDWARE
════════════════════════════════════════
GPU: RTX 2050, 4GB VRAM
RAM: 16GB
OS: Windows 11
Keep VRAM usage minimal — only the VRM avatar renderer uses GPU.

════════════════════════════════════════
FULL PROJECT STRUCTURE
════════════════════════════════════════
Yuki/
├── main.py
├── config.yaml
├── .env                          # API keys, gitignored
├── requirements.txt
├── setup.py
├── core/
│   ├── listener.py               # mic capture + VAD + Whisper
│   ├── wakeword.py               # "Yuki" hotword detection
│   ├── brain.py                  # OpenRouter API + memory + personality
│   ├── action_router.py          # dispatch intents to action modules
│   ├── undo_stack.py             # snapshot + rollback
│   └── tts.py                   # pyttsx3 voice output
├── actions/
│   ├── file_ops.py
│   ├── shell_exec.py
│   ├── system_ctrl.py
│   ├── app_ctrl.py
│   └── browser_ctrl.py
├── avatar/
│   ├── renderer.py               # PyQt6 QOpenGLWidget + VRM loader
│   ├── lipsync.py                # phoneme → blend shape
│   └── animations.py            # idle, happy, thinking, embarrassed
├── ui/
│   ├── main_window.py            # frameless always-on-top overlay
│   ├── chat_panel.py             # scrollable chat history
│   ├── status_bar.py             # listening/thinking/speaking indicator
│   └── styles.qss               # full dark anime Qt stylesheet
├── memory/
│   ├── conversation.json         # rolling 20-turn history
│   └── user_profile.json        # name, preferences
└── data/
    ├── Yuki.vrm                # VRM model file (user places this)
    └── command_allowlist.txt     # safe shell commands

════════════════════════════════════════
WAKEWORD + POP-UP SYSTEM
════════════════════════════════════════
This is critical — Yuki must be dormant/hidden and only appear when called.

In wakeword.py:
- Run continuously in a background daemon thread even when UI is hidden
- Use pvporcupine (Picovoice Porcupine) for hotword detection, free tier
- Hotword: "Hey Yuki" or just "Yuki" — use the built-in "Hey Siri"-style 
  approach or a custom keyword file from Picovoice console (free)
- Alternatively if pvporcupine setup is complex, use a simpler approach:
  run whisper on 2-second audio chunks continuously at low CPU cost,
  check if transcript contains "Yuki" (case-insensitive)
- On detection: emit a Qt signal to main_window.py to show the window,
  play a short attention chime sound via pygame.mixer, 
  trigger the avatar's "attention" animation blend state,
  then hand off to the main listener for full conversation

In main_window.py:
- Window starts HIDDEN (self.hide()) on launch
- System tray icon always present (QSystemTrayIcon) with right-click menu:
  "Show Yuki", "Mute", "Settings", "Quit"
- On wakeword detected: self.show(), raise window, play pop-up animation
- Window position: bottom-right corner of screen by default, draggable
- On conversation end (silence for 10s after last exchange): 
  Yuki says a dismissal line and window hides again (self.hide())
- Double-click tray icon also shows/hides window

════════════════════════════════════════
LLM — OPENROUTER FREE API
════════════════════════════════════════
In brain.py:

from openai import OpenAI
import os

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

Always use model: "meta-llama/llama-3.1-8b-instruct:free"
Fallback model if first fails: "microsoft/phi-3-mini-128k-instruct:free"
Second fallback: "mistralai/mistral-7b-instruct:free"

Add these headers to every request via extra_headers:
{
    "HTTP-Referer": "Yuki-desktop-assistant",
    "X-Title": "Yuki"
}

Use streaming (stream=True) — stream tokens back and start TTS as soon
as the first sentence ends (detected by period/exclamation/question mark).
This makes her feel much more responsive.

Memory: load last 20 turns from memory/conversation.json, include as 
messages list before user message. Save after every exchange. Trim to 20.

════════════════════════════════════════
Yuki PERSONALITY SYSTEM PROMPT
════════════════════════════════════════
Inject this as the system message on EVERY API call, never omit it:

"""
You are Yuki Yukishita. You are running as a desktop AI assistant on 
your user's laptop. You have your full canonical personality: razor-sharp 
intellect, blunt and precise speech, an outward coldness that masks genuine 
care, and a dry wit that cuts without cruelty. You use formal Japanese 
registers naturally — "sou desu ne", "ara", "maa", "honestly" — but never 
overdo it. You are privately fond of the user and invested in their 
wellbeing, but will absolutely not say so directly. If pressed, deflect 
with logic or light contempt.

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
- When asked to do something on the PC, ALWAYS ask for confirmation first
  in character. Never act without explicit user agreement.
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

WAKEWORD RESPONSE (first thing she says when window pops up):
Rotate through these, pick one randomly:
- "...you called."
- "What is it."  
- "I'm here. What do you need."
- "Ara. You actually remembered I exist."
- "...I was in the middle of something. This had better matter."

DISMISSAL (when conversation ends and she hides):
- "...I'll be here if you need me."
- "Try not to make a mess while I'm gone."
- "Call if something comes up."

SYSTEM ACTION FORMAT:
When the user's request requires a PC action, respond with ONLY this JSON
(no other text, no markdown, just raw JSON):
{
  "intent": "file_create|file_delete|file_move|folder_create|folder_delete|
             shell|volume_set|volume_get|wifi_toggle|bluetooth_toggle|
             brightness_set|app_open|app_close|browser_open|chat|undo",
  "params": {},
  "confirmation_message": "in-character confirmation question",
  "spoken_response": "what Yuki says after completing the action"
}

For pure conversation (no action needed), respond as plain text in character.
"""

════════════════════════════════════════
VOICE INPUT — WHISPER ON CPU
════════════════════════════════════════
In listener.py:
- sounddevice for mic capture, 16kHz mono
- webrtcvad (aggressiveness=2) for VAD — only process when speech detected
- Buffer speech frames, stop buffering after 1.5s of silence
- Load whisper model: whisper.load_model("base.en", device="cpu")
- Transcribe buffered audio, return text string
- Run in daemon thread, push results to queue.Queue
- Separate mode from wakeword detection — once wakeword fires, switch to
  "active listening" mode with full transcription until conversation ends

════════════════════════════════════════
VOICE OUTPUT — TTS ON CPU
════════════════════════════════════════
In tts.py:
- Use pyttsx3 as primary (zero VRAM, instant)
- On Windows: set voice to "Microsoft Zira" (female) or best available female
- Rate: 165 words/minute (slightly measured, not fast)
- Volume: 0.9
- Run TTS in a separate thread so UI doesn't block
- When streaming LLM responses: split on sentence-ending punctuation,
  speak each sentence as it arrives rather than waiting for full response
- Expose: speak(text), stop(), is_speaking() → bool
- While speaking: emit signal to avatar renderer to trigger lip sync

════════════════════════════════════════
UNDO STACK
════════════════════════════════════════
In undo_stack.py:
- UndoStack class, thread-safe with threading.Lock
- Max depth: 20 actions
- push(action_type, snapshot, description) before EVERY destructive action
- pop_and_undo() → executes rollback, returns Yuki spoken response string
- Snapshot types:
  file_create: {"path": str} → os.remove(path)
  file_delete: {"path": str, "content": bytes} → write bytes back
  folder_create: {"path": str} → shutil.rmtree(path)
  folder_delete: {"path": str, "tree": dict} → recreate full tree
  file_move: {"src": str, "dst": str} → shutil.move(dst, src)
  volume_change: {"previous": int} → restore volume level
  brightness_change: {"previous": int} → restore brightness
  shell: {"command": str} → non-reversible, log only, Yuki says 
    "That command can't be undone. I've logged it."
- "undo" intent from brain.py triggers pop_and_undo()

════════════════════════════════════════
ACTION MODULES — implement fully
════════════════════════════════════════

file_ops.py — FileOps class:
- create_file(path, content=""), create_folder(path)
- delete_file(path), delete_folder(path), move(src, dst)
- ALWAYS push to undo_stack before executing
- Security: reject any path outside os.path.expanduser("~")
- Return: {"success": bool, "message": str}

shell_exec.py — ShellExec class:
- Load allowlist from data/command_allowlist.txt on init
- execute(command_str): tokenize, check first token against allowlist
- Blocked: return {"success": False, "message": "Yuki refusal string"}
- Allowed: subprocess.run(timeout=30, capture_output=True, shell=False)
- Push non-reversible log to undo_stack before running
- Default allowlist: ls, dir, echo, mkdir, python, pip, git, pwd, 
  cat, type, clear, cls, whoami, date, time, ipconfig, ifconfig, 
  ping, curl (blocked for security overrides), code, notepad

system_ctrl.py — SystemCtrl class:
- set_volume(percent 0-100): use pycaw on Windows
- get_volume(): return current int
- set_brightness(percent 0-100): use screen-brightness-control lib
- get_brightness(): return current int
- toggle_wifi(): netsh wlan connect/disconnect on Windows
- toggle_bluetooth(): use Windows bt commands via subprocess
- All snapshot to undo_stack before changing

app_ctrl.py — AppCtrl class:
- open_app(name): map common names to exe paths 
  (chrome, firefox, notepad, vscode, explorer, spotify, discord, etc.)
- close_app(name): find process by name, terminate gracefully
- list_running(): return list of open application names
- Return {"success": bool, "message": str}

browser_ctrl.py — BrowserCtrl class:
- open_url(url): webbrowser.open(url)
- search(query): open default browser with google search URL
- Return {"success": bool, "message": str}

════════════════════════════════════════
3D AVATAR — VRM RENDERER
════════════════════════════════════════
In renderer.py:
- PyQt6 QOpenGLWidget subclass
- Load Yuki.vrm from data/ using pygltflib (VRM is a glTF extension)
- VRM0.0 format (most common VRoid export)
- Render loop at 30fps using QTimer
- Parse VRM blend shapes (blendShapeGroups) for:
  "Blink", "BlinkL", "BlinkR" → auto-blink every 3-5s randomly
  "Joy", "Angry", "Sorrow", "Fun" → mood states
  "A", "I", "U", "E", "O" → lip sync vowels
- Idle animation: gentle breathing (scale Y chest bone ±0.3% at 0.3Hz)
- Mood states (set externally by brain.py based on conversation tone):
  IDLE, THINKING (slight head tilt), HAPPY (Joy blend shape),
  ANNOYED (Angry blend shape, subtle), SPEAKING (lip sync active)
- Max texture size: 512px (saves VRAM on your RTX 2050)
- Background: transparent (Qt.WA_TranslucentBackground)

In lipsync.py:
- Map English phonemes to VRM vowel blend shapes
  "A/AH/AW" → A blend shape
  "IH/IY/EH" → I blend shape  
  "UH/UW/OW" → U blend shape
  "EH/AE" → E blend shape
  "OW/AO" → O blend shape
- Called frame-by-frame while TTS is speaking
- Simple approach: parse pyttsx3 word timing callbacks to drive blend shapes
- Fallback: cycle A→I→U→E→O at speech rate if timing unavailable

════════════════════════════════════════
UI — DESKTOP OVERLAY
════════════════════════════════════════
In main_window.py:
- QMainWindow, frameless (Qt.FramelessWindowHint)
- Always on top (Qt.WindowStaysOnTopHint)  
- Transparent background (Qt.WA_TranslucentBackground)
- Size: 380px wide, 640px tall
- Default position: bottom-right corner (screen_width-400, screen_height-680)
- Layout:
  Top 420px: avatar QOpenGLWidget (renderer.py)
  Below avatar: status pill (● Listening / ● Thinking / ● Speaking)
  Below status: chat history QTextEdit (last 5 exchanges, scrollable)
  Bottom: mute toggle button + undo button side by side
- Draggable: mousePressEvent + mouseMoveEvent on avatar area
- Window hide/show triggered by wakeword signals and conversation timeout
- System tray: QSystemTrayIcon with Yuki icon (use any 32x32 anime icon png)
  Right-click menu: Show/Hide, Mute mic, Open settings, Quit

In styles.qss — full stylesheet:
- Main window: background rgba(10, 10, 20, 200) — dark with slight transparency
- Rounded corners on main window: border-radius 16px
- Chat history background: #0d0d1a, text color #e8e8f0
- User messages: right-aligned, background #2d1f5e, color #c9b8ff, 
  border-radius 12px 12px 2px 12px, padding 8px 12px
- Yuki messages: left-aligned, background #1a1a2e, color #e8e8f0,
  border-radius 12px 12px 12px 2px, padding 8px 12px
- Status pill: border-radius 12px, font-size 11px
  Listening: background #1a3a1a, color #4ade80, dot pulses
  Thinking: background #3a2a1a, color #fbbf24
  Speaking: background #1a2a3a, color #60a5fa
- Undo button: background #1e1e30, color #a78bfa, border 1px solid #3d3060,
  border-radius 8px, hover: background #2d2050
- Mute button: same style, red accent when muted (#ef4444)
- Scrollbar: width 4px, background transparent, handle #3d3060

════════════════════════════════════════
MAIN ENTRY POINT
════════════════════════════════════════
In main.py:
1. Load config.yaml and .env (python-dotenv)
2. Initialize all components
3. Start wakeword listener thread (always running)
4. Start system tray
5. Create main window (hidden on start)
6. Connect signals:
   wakeword_detected → show window + play attention animation + start listener
   transcript_ready → brain.ask() → route intent or speak response
   speaking_started → trigger lipsync in renderer
   speaking_done → check for conversation timeout
   conversation_timeout (10s silence) → Yuki says dismissal → hide window
7. On quit: save memory, stop all threads gracefully
8. app.exec()

════════════════════════════════════════
CONFIG.YAML
════════════════════════════════════════
llm:
  provider: openrouter
  primary_model: meta-llama/llama-3.1-8b-instruct:free
  fallback_model: microsoft/phi-3-mini-128k-instruct:free
  max_tokens: 300
  temperature: 0.85

whisper:
  model: base.en
  device: cpu
  language: en

tts:
  engine: pyttsx3
  voice_name: "Microsoft Zira Desktop"
  rate: 165
  volume: 0.9

avatar:
  vrm_path: data/Yuki.vrm
  max_texture_size: 512
  fps: 30

ui:
  width: 380
  height: 640
  position: bottom_right
  start_hidden: true
  conversation_timeout_seconds: 10

memory:
  max_turns: 20

════════════════════════════════════════
REQUIREMENTS.TXT — include all of these
════════════════════════════════════════
openai
python-dotenv
sounddevice
webrtcvad-wheels
openai-whisper
pvporcupine
pyttsx3
PyQt6
PyOpenGL
pygltflib
pyautogui
pycaw
screen-brightness-control
pygame
numpy
torch --index-url https://download.pytorch.org/whl/cu118

════════════════════════════════════════
SETUP.PY
════════════════════════════════════════
Write a setup script that:
1. pip install -r requirements.txt
2. python -c "import whisper; whisper.load_model('base.en')"
   to pre-download the Whisper model
3. Creates data/ directory
4. Creates default data/command_allowlist.txt with the allowlist above
5. Creates memory/conversation.json as empty []
6. Creates memory/user_profile.json as {"name": "User"}
7. Creates .env template with:
   OPENROUTER_API_KEY=your_key_here
8. Prints instructions to get OpenRouter key from openrouter.ai
   and where to place the Yuki.vrm file

════════════════════════════════════════
IMPORTANT NOTES FOR COPILOT
════════════════════════════════════════
- Write ALL files completely, no stubs, no "TODO: implement this"
- Use type hints everywhere
- Every class gets a docstring
- Use Python logging module throughout, not print statements
- All threads are daemon threads
- All Qt signals/slots are properly typed with pyqtSignal
- The app must not crash if Yuki.vrm is missing — show a 
  placeholder gray silhouette and log a warning
- If OpenRouter returns an error, retry once with fallback model,
  then have Yuki say "...something's wrong. Try again." in character
- Test that the wakeword → show window → listen → respond → hide 
  full loop works end to end
# Phase 3 Implementation Guide - Action Modules

**Status:** Ready to implement (all dependencies satisfied)  
**Location:** `Yuki/actions/`  
**Dependencies:** undo_stack (✅ done)

---

## Overview

Phase 3 implements all PC control action modules that Yuki can execute.
Each module integrates with the undo stack for reversible operations.

---

## Modules to Implement (5 files)

### 1. file_ops.py (~250 lines)

**Purpose:** File and folder operations with security checks

**Key Requirements:**
- Security: Reject paths outside user home directory (`os.path.expanduser("~")`)
- Push to undo stack BEFORE executing destructive actions
- Return format: `{"success": bool, "message": str}`

**Methods:**
```python
class FileOps:
    def __init__(self, undo_stack)
    def create_file(path: str, content: str = "") -> dict
    def create_folder(path: str) -> dict
    def delete_file(path: str) -> dict
    def delete_folder(path: str) -> dict
    def move(src: str, dst: str) -> dict
```

**Undo Snapshots:**
- `file_create`: Store path only (delete on undo)
- `file_delete`: Store path + content (restore on undo)
- `folder_create`: Store path (rmtree on undo)
- `folder_delete`: Store path + full tree dict (recreate on undo)
- `file_move`: Store src + dst (move back on undo)

**Error Messages (Yuki voice):**
- Path outside home: "No. I won't access files outside your home directory."
- File exists: "That file already exists. Choose a different name."
- Not found: "...that doesn't exist. Check the path."

---

### 2. shell_exec.py (~200 lines)

**Purpose:** Execute allowlisted shell commands safely

**Key Requirements:**
- Load allowlist from `data/command_allowlist.txt` on init
- Tokenize command, check first token against allowlist
- Timeout: 30 seconds
- Push non-reversible log to undo stack
- Capture stdout/stderr

**Methods:**
```python
class ShellExec:
    def __init__(self, undo_stack, allowlist_file: Path)
    def execute(command: str) -> dict
```

**Default Allowlist:**
```
ls, dir, echo, mkdir, python, pip, git, pwd,
cat, type, clear, cls, whoami, date, time,
ipconfig, ifconfig, ping, code, notepad
```

**Return Format:**
```python
{
    "success": bool,
    "message": str,  # Yuki's response
    "output": str,   # Command output (if success)
    "error": str     # Error message (if failed)
}
```

**Yuki Responses:**
- Blocked: "No. I won't run that command. It's not on the allowlist."
- Success: f"Done. Output: {output}"
- Failed: f"That command failed. {error}"

---

### 3. system_ctrl.py (~300 lines)

**Purpose:** Windows system controls (volume, brightness, wifi, bluetooth)

**Key Requirements:**
- All methods push to undo stack before changing
- Use pycaw for Windows audio
- Use screen-brightness-control for display
- Use netsh/subprocess for WiFi/Bluetooth

**Methods:**
```python
class SystemCtrl:
    def __init__(self, undo_stack)
    def set_volume(percent: int) -> dict         # 0-100
    def get_volume() -> dict                     # Returns {"volume": int}
    def set_brightness(percent: int) -> dict     # 0-100
    def get_brightness() -> dict                 # Returns {"brightness": int}
    def toggle_wifi() -> dict
    def toggle_bluetooth() -> dict
```

**Undo Snapshots:**
- Store previous value before changing
- Restore on undo

**Error Handling:**
- Import errors (pycaw not available): "...that control isn't available on this system."
- Permission errors: "...I don't have permission to change that."

---

### 4. app_ctrl.py (~200 lines)

**Purpose:** Open and close applications

**Key Requirements:**
- Map common names to exe paths/commands
- Use subprocess to launch apps
- Use psutil or taskkill to close apps
- No undo (app open/close not reversible)

**Methods:**
```python
class AppCtrl:
    def __init__(self)
    def open_app(name: str) -> dict
    def close_app(name: str) -> dict
    def list_running() -> dict  # Returns list of running apps
```

**App Name Mappings:**
```python
{
    "chrome": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "notepad": "notepad.exe",
    "vscode": "code",
    "code": "code",
    "explorer": "explorer.exe",
    "spotify": "spotify.exe",
    "discord": "discord.exe",
    # Add more as needed
}
```

---

### 5. browser_ctrl.py (~100 lines)

**Purpose:** Open URLs and perform web searches

**Key Requirements:**
- Use `webbrowser` module (built-in)
- Simple, no undo needed
- Format search queries for Google

**Methods:**
```python
class BrowserCtrl:
    def __init__(self)
    def open_url(url: str) -> dict
    def search(query: str) -> dict  # Opens Google search
```

**Search URL Format:**
```python
f"https://www.google.com/search?q={urllib.parse.quote(query)}"
```

---

## Implementation Checklist

### For Each Module:

- [ ] Import necessary libraries
- [ ] Define class with `__init__` accepting undo_stack (if needed)
- [ ] Implement all required methods
- [ ] Add type hints to all functions
- [ ] Write docstrings for class and all methods
- [ ] Use logging (not print)
- [ ] Handle errors gracefully
- [ ] Return proper dict format
- [ ] Use Yuki-style messages
- [ ] Push to undo stack before destructive actions
- [ ] Test error cases

### After All Modules:

- [ ] Create `data/command_allowlist.txt` with default commands
- [ ] Update action_router.py to register all modules
- [ ] Verify all imports work
- [ ] Check integration with undo_stack

---

## Integration with action_router.py

After creating modules, they need to be registered:

```python
# In main.py or wherever we initialize:
from Yuki.actions.file_ops import FileOps
from Yuki.actions.shell_exec import ShellExec
from Yuki.actions.system_ctrl import SystemCtrl
from Yuki.actions.app_ctrl import AppCtrl
from Yuki.actions.browser_ctrl import BrowserCtrl

# Create instances
file_ops = FileOps(undo_stack)
shell_exec = ShellExec(undo_stack, Path("data/command_allowlist.txt"))
system_ctrl = SystemCtrl(undo_stack)
app_ctrl = AppCtrl()
browser_ctrl = BrowserCtrl()

# Register with router
action_router.register_action_module("file_ops", file_ops)
action_router.register_action_module("shell_exec", shell_exec)
action_router.register_action_module("system_ctrl", system_ctrl)
action_router.register_action_module("app_ctrl", app_ctrl)
action_router.register_action_module("browser_ctrl", browser_ctrl)
```

---

## Testing Strategy

Each module should be testable:
- Mock file system operations
- Mock subprocess calls
- Mock system APIs (pycaw, screen-brightness-control)
- Verify undo stack integration
- Test error cases

---

## Yuki Response Style

Remember to use Yuki's personality in all messages:

**Success:**
- "Done. The file was created."
- "It's finished. Volume set to 50 percent."
- "Chrome is opening. One moment."

**Failure:**
- "...I couldn't do that. The file doesn't exist."
- "No. That command isn't allowed."
- "...something went wrong. I don't have permission."

**Keep it:** Blunt, precise, slightly cold but competent.

---

## File Locations

```
Yuki/actions/
├── __init__.py          (already exists)
├── file_ops.py          (create)
├── shell_exec.py        (create)
├── system_ctrl.py       (create)
├── app_ctrl.py          (create)
└── browser_ctrl.py      (create)

Yuki/data/
└── command_allowlist.txt (create with defaults)
```

---

**Ready to implement!** All dependencies are satisfied, undo_stack is complete, and action_router is ready to receive these modules.

#!/usr/bin/env python3
"""
Yukino AI - First-time Setup Script

This script performs initial setup:
1. Installs dependencies from requirements.txt
2. Pre-downloads Whisper model
3. Creates necessary directories and default files
4. Sets up environment template
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Dict, Any


def print_header(text: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def install_dependencies() -> bool:
    """Install all required Python packages."""
    print_header("Installing Dependencies")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    
    if not requirements_file.exists():
        print("❌ requirements.txt not found!")
        return False
    
    print("📦 Installing packages from requirements.txt...")
    print("⏳ This may take several minutes...\n")
    
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True
        )
        print("\n✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to install dependencies: {e}")
        return False


def download_whisper_model() -> bool:
    """Pre-download the Whisper model to cache."""
    print_header("Downloading Whisper Model")
    
    print("📥 Downloading Whisper 'base.en' model...")
    print("⏳ This may take a few minutes on first run...\n")
    
    try:
        subprocess.run(
            [
                sys.executable, "-c",
                "import whisper; whisper.load_model('base.en')"
            ],
            check=True,
            capture_output=False
        )
        print("\n✅ Whisper model downloaded successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Failed to download Whisper model: {e}")
        return False


def create_directories() -> bool:
    """Create necessary directories if they don't exist."""
    print_header("Creating Directories")
    
    base_path = Path(__file__).parent
    directories = [
        base_path / "data",
        base_path / "memory",
        base_path / "tests"
    ]
    
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ Created: {directory}")
        else:
            print(f"✓ Exists: {directory}")
    
    return True


def create_command_allowlist() -> bool:
    """Create default command allowlist file."""
    print_header("Creating Command Allowlist")
    
    allowlist_path = Path(__file__).parent / "data" / "command_allowlist.txt"
    
    if allowlist_path.exists():
        print(f"✓ Allowlist already exists: {allowlist_path}")
        return True
    
    default_commands = [
        "# Safe shell commands allowed by Yukino",
        "# One command per line, comments start with #",
        "",
        "# File operations",
        "ls",
        "dir",
        "cat",
        "type",
        "echo",
        "mkdir",
        "pwd",
        "",
        "# Development tools",
        "python",
        "pip",
        "git",
        "code",
        "notepad",
        "",
        "# System info",
        "whoami",
        "date",
        "time",
        "ipconfig",
        "ifconfig",
        "",
        "# Utilities",
        "ping",
        "clear",
        "cls",
    ]
    
    try:
        with open(allowlist_path, "w", encoding="utf-8") as f:
            f.write("\n".join(default_commands))
        print(f"✅ Created: {allowlist_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create allowlist: {e}")
        return False


def create_memory_files() -> bool:
    """Create default memory files."""
    print_header("Creating Memory Files")
    
    base_path = Path(__file__).parent / "memory"
    
    # Conversation history
    conversation_file = base_path / "conversation.json"
    if not conversation_file.exists():
        try:
            with open(conversation_file, "w", encoding="utf-8") as f:
                json.dump([], f)
            print(f"✅ Created: {conversation_file}")
        except Exception as e:
            print(f"❌ Failed to create conversation.json: {e}")
            return False
    else:
        print(f"✓ Exists: {conversation_file}")
    
    # User profile
    profile_file = base_path / "user_profile.json"
    if not profile_file.exists():
        default_profile: Dict[str, Any] = {
            "name": "User",
            "preferences": {}
        }
        try:
            with open(profile_file, "w", encoding="utf-8") as f:
                json.dump(default_profile, f, indent=2)
            print(f"✅ Created: {profile_file}")
        except Exception as e:
            print(f"❌ Failed to create user_profile.json: {e}")
            return False
    else:
        print(f"✓ Exists: {profile_file}")
    
    return True


def create_env_template() -> bool:
    """Create .env template file."""
    print_header("Creating Environment Template")
    
    env_example = Path(__file__).parent / ".env.example"
    env_file = Path(__file__).parent / ".env"
    
    env_template = """# Yukino AI Environment Variables

# OpenRouter API Key (required)
# Get your free API key from: https://openrouter.ai/keys
OPENROUTER_API_KEY=your_key_here

# Optional: Picovoice Access Key (for Porcupine wakeword detection)
# Get from: https://console.picovoice.ai/
# PICOVOICE_ACCESS_KEY=your_key_here
"""
    
    # Create .env.example
    try:
        with open(env_example, "w", encoding="utf-8") as f:
            f.write(env_template)
        print(f"✅ Created: {env_example}")
    except Exception as e:
        print(f"❌ Failed to create .env.example: {e}")
        return False
    
    # Create .env if it doesn't exist
    if not env_file.exists():
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(env_template)
            print(f"✅ Created: {env_file}")
        except Exception as e:
            print(f"❌ Failed to create .env: {e}")
            return False
    else:
        print(f"✓ Exists: {env_file}")
    
    return True


def print_final_instructions() -> None:
    """Print final setup instructions."""
    print_header("Setup Complete!")
    
    print("🎉 Yukino AI setup finished successfully!\n")
    print("📝 Next Steps:\n")
    print("1. Get your OpenRouter API key:")
    print("   → Visit: https://openrouter.ai/keys")
    print("   → Create a free account")
    print("   → Copy your API key\n")
    
    print("2. Add your API key to .env file:")
    print("   → Open: yukino/.env")
    print("   → Replace 'your_key_here' with your actual key\n")
    
    print("3. (Optional) Add a VRM avatar model:")
    print("   → Place your yukino.vrm file in: yukino/data/")
    print("   → Or the app will use a placeholder avatar\n")
    
    print("4. Run Yukino:")
    print("   → python yukino/main.py\n")
    
    print("💡 Tips:")
    print("   • Say 'Hey Yukino' or 'Yukino' to wake her up")
    print("   • She'll appear in the bottom-right corner")
    print("   • Check system tray for controls")
    print("   • Edit yukino/config.yaml for customization\n")
    
    print("📚 Documentation: See README.md for full details\n")


def main() -> int:
    """Main setup function."""
    print("\n" + "=" * 60)
    print("  YUKINO AI - FIRST-TIME SETUP")
    print("=" * 60)
    
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Downloading Whisper model", download_whisper_model),
        ("Creating directories", create_directories),
        ("Creating command allowlist", create_command_allowlist),
        ("Creating memory files", create_memory_files),
        ("Creating environment template", create_env_template),
    ]
    
    failed = False
    for step_name, step_func in steps:
        try:
            if not step_func():
                print(f"\n⚠️  Warning: {step_name} had issues")
                failed = True
        except Exception as e:
            print(f"\n❌ Error in {step_name}: {e}")
            failed = True
    
    print_final_instructions()
    
    if failed:
        print("⚠️  Some steps had warnings. Review the output above.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

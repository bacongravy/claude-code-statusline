#!/usr/bin/env python3
import os
import sys
import json
import urllib.request
import urllib.error
import subprocess
import platform
from pathlib import Path

# ANSI colors
BLUE = "\033[34m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
RESET = "\033[0m"

USAGE_API_URL = "https://api.anthropic.com/api/oauth/usage"
USAGE_THRESHOLD_HIGH = 80
USAGE_THRESHOLD_MEDIUM = 50
CREDENTIALS_PATH = Path.home() / ".claude" / ".credentials.json"

BLOCKS = "▏▎▍▌▋▊▉█"

# OSC 8 hyperlink escape sequences (for iTerm2, etc.)
OSC8_PREFIX = "\x1b]8;;"
OSC8_SEP = "\x07"
OSC8_SUFFIX = "\x1b]8;;\x07"

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw)
    except Exception:
        print("statusline: no data")
        return

    # Extract fields
    cwd = data.get("cwd", "")
    current_directory = vscode_folder_link(cwd)
    project_directory = data.get("workspace", {}).get("project_dir", cwd)
    model = data.get("model", {}).get("display_name", "")
    context_window = data.get("context_window", {})

    # Fetch usage from API (if credentials available)
    access_token = get_access_token()
    usage_str = ""
    if access_token:
        usage_data = fetch_usage(access_token)
        usage_str = f" · {format_usage(usage_data)}"

    line = f"📂 {current_directory}{format_git_branch(project_directory)}\n🧠 {CYAN}{model}{RESET} · {format_context_usage(context_window)}{usage_str}"

    print(line)

def supports_osc8() -> bool:
    """Check if the terminal supports OSC 8 hyperlinks."""
    # Known OSC 8 supporting terminals
    term_program = os.environ.get("TERM_PROGRAM", "")
    if term_program in ("iTerm.app", "WezTerm", "Hyper", "Alacritty"):
        return True
    # Terminal-specific env vars
    if any(os.environ.get(var) for var in ("ITERM_SESSION_ID", "WEZTERM_PANE", "WT_SESSION", "KITTY_WINDOW_ID")):
        return True
    # Kitty
    if "kitty" in os.environ.get("TERM", ""):
        return True
    return False

def hyperlink(url: str, text: str) -> str:
    """Create an OSC 8 hyperlink (clickable in iTerm2, etc.)."""
    return f"{OSC8_PREFIX}{url}{OSC8_SEP}{text}{OSC8_SUFFIX}"

def vscode_folder_link(path: str) -> str:
    """Create a clickable folder name that opens in VSCode."""
    folder_name = Path(path).name
    if not supports_osc8():
        return folder_name
    vscode_url = f"vscode://file{path}"
    return hyperlink(vscode_url, folder_name)

def format_context_usage(context_window):
    percent_used = context_window.get("used_percentage", 0)
    return f"📝 {get_usage_color(percent_used)}{get_progress_bar(percent_used)} {percent_used}%{RESET}"

def format_git_branch(project_directory):
    """Get git info from single git status call. Works with regular repos and worktrees."""
    staged = unstaged = ahead = behind = 0
    branch = ""

    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "-b"],
            capture_output=True, text=True, timeout=2, cwd=project_directory
        )
        if result.returncode != 0:
            return ""

        for line in result.stdout.splitlines():
            if line.startswith('## '):
                # Parse: ## branch...upstream [ahead N, behind M]
                # or: ## HEAD (no branch) for detached HEAD
                branch_part = line[3:]
                if branch_part.startswith('HEAD (no branch)'):
                    branch = "detached HEAD"
                else:
                    branch = branch_part.split('...')[0].split()[0]
                    if '[ahead ' in line:
                        ahead = int(line.split('[ahead ')[1].split(',')[0].split(']')[0])
                    if '[behind ' in line:
                        behind = int(line.split('[behind ')[1].split(']')[0])
            elif len(line) >= 2:
                if line[0] not in ' ?':  # Index has changes (staged)
                    staged += 1
                if line[1] != ' ':  # Worktree has changes or untracked
                    unstaged += 1
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return ""

    if not branch:
        return ""

    # Build change info string
    parts = []
    if staged:
        parts.append(f"{staged} staged")
    if unstaged:
        parts.append(f"{unstaged} unstaged")
    if ahead:
        parts.append(f"{ahead} ahead")
    if behind:
        parts.append(f"{behind} behind")

    suffix = f" ({', '.join(parts)})" if parts else ""
    return f" · 🌿 {branch}{suffix}"

def get_access_token() -> str | None:
    """Retrieve the access token based on the platform."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return get_access_token_macos()
    elif system == "Linux":
        return get_access_token_linux()
    else:
        return None # Windows not supported

def get_access_token_macos() -> str | None:
    """Retrieve access token from macOS Keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True
        )
        credentials = result.stdout.strip()
        if credentials:
            creds = json.loads(credentials)
            return creds.get("claudeAiOauth", {}).get("accessToken")
        return None
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        return None

def get_access_token_linux() -> str | None:
    """Read access token from credentials file on Linux."""
    try:
        with open(CREDENTIALS_PATH) as f:
            creds = json.load(f)
        return creds.get("claudeAiOauth", {}).get("accessToken")
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return None

def fetch_usage(access_token: str) -> dict | None:
    """Fetch usage data from Anthropic API."""
    try:
        req = urllib.request.Request(
            USAGE_API_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
                "anthropic-beta": "oauth-2025-04-20",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None

def get_progress_bar(progress, total=100, width=10):
    percent = progress / total
    total_blocks = width * 8  # 8 sub-blocks per character
    filled_blocks = int(percent * total_blocks)

    full_chars = filled_blocks // 8
    remainder = filled_blocks % 8
    empty = width - full_chars

    bar = "█" * full_chars
    if remainder > 0:
        bar += BLOCKS[remainder - 1]
        empty -= 1
    bar += "░" * empty

    return bar

def format_usage(usage_data: dict) -> str:
    """Format usage data for statusline display."""
    if not usage_data:
        return f"{RED}Usage: N/A{RESET}"

    # Extract 5-hour and 7-day limits
    five_hour_usage = usage_data.get("five_hour", {})
    weekly_usage = usage_data.get("seven_day", {})

    five_hour_percentage = five_hour_usage.get("utilization", 0) or 0
    weekly_percentage = weekly_usage.get("utilization", 0) or 0

    five_hour_str = f"{get_usage_color(five_hour_percentage)}{get_progress_bar(five_hour_percentage)} {five_hour_percentage:.0f}%{RESET}"
    weekly_str = f"{get_usage_color(weekly_percentage)}{get_progress_bar(weekly_percentage)} {weekly_percentage:.0f}%{RESET}"

    return f"🕔 {five_hour_str} · 🗓️ {weekly_str}"

def get_usage_color(percentage: float) -> str:
    if percentage >= USAGE_THRESHOLD_HIGH:
        return RED
    elif percentage >= USAGE_THRESHOLD_MEDIUM:
        return YELLOW
    return GREEN

if __name__ == "__main__":
    main()

# Claude Code Status Line

A Python status line script for Claude Code that displays your current model, context usage, API usage limits, working directory, and git status.

## Features

- **Directory & Git Info**: Current directory with git branch and status
  - Staged, unstaged, and untracked file counts
  - Commits ahead/behind tracking branch
  - Supports git worktrees and detached HEAD
- **Model Display**: Shows the currently active Claude model
- **Context Usage**: Visual progress bar showing context window utilization
- **Usage Tracking**: Real-time 5-hour and 7-day API usage limits with visual progress bars
  - Color-coded alerts (green < 50%, yellow 50-80%, red > 80%)
  - Only shown for Pro/Max subscribers with OAuth credentials

## Prerequisites

- Python 3.10 or higher
- Claude Code CLI
- Supported platforms: macOS, Linux (Windows not supported)
- Optional: OAuth login for Pro/Max quota display

## Installation

1. **Download or copy `statusline.py` to `~/.claude/statusline.py`**
   ```bash
   curl -o ~/.claude/statusline.py https://raw.githubusercontent.com/bacongravy/claude-code-statusline/main/statusline.py
   chmod +x ~/.claude/statusline.py
   ```

2. **Configure Claude Code**

   Add or update the `statusLine` attribute in `~/.claude/settings.json`:
   ```json
   {
     "statusLine": {
       "type": "command",
       "command": "~/.claude/statusline.py",
       "padding": 0
     }
   }
   ```

3. **Restart Claude Code**

## How It Works

The script:
1. Receives session data from Claude Code via stdin (JSON format)
2. Retrieves your OAuth access token:
   - **macOS**: From Keychain using `security find-generic-password`
   - **Linux**: From `~/.claude/.credentials.json`
   - **Windows**: Not supported (returns empty)
3. Fetches current usage data from Anthropic's API
4. Outputs a formatted status line with ANSI colors

## Example Output

```
📂 ~/projects/myapp · 🌿 main (1 staged, 2 unstaged, 1 ahead)
🧠 Claude Opus 4.5 · 📝 ██░░░░░░░░ 23% · 🕔 ██░░░░░░░░ 15% · 🗓️ ████░░░░░░ 45%
```

## Troubleshooting

- **"Usage: N/A" message**: API request failed (check network connection)
- **Quota usage not showing**: Requires Pro/Max subscription with OAuth login
- **Script not updating**: Verify the path in `.claude/settings.json` is absolute and executable

## Documentation

For more information about status lines in Claude Code, see the [official documentation](https://code.claude.com/docs/en/statusline).
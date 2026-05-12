# Deep Coder

The most cost-effective code assistant tool based on DeepSeek V4.

## Architecture

Deep Coder uses a **two-tier agent architecture** for optimal cost-performance balance:

```
                User Input
                    │
                    ▼
        ┌───────────────────────┐
        │  Orchestrator (V4 Pro)│  Planning & task decomposition
        └───────────┬───────────┘
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
       ┌──────┐ ┌──────┐ ┌──────┐
       │Worker│ │Worker│ │Worker│  Parallel execution (V4 Flash)
       │Task 1│ │Task 2│ │Task 3│
       └──┬───┘ └──┬───┘ └──┬───┘
          │        │        │
          └────────┼────────┘
                   ▼
        ┌───────────────────────┐
        │  Orchestrator (V4 Pro)│  Result verification & summary
        └───────────────────────┘
```

- **DeepSeek V4 Pro** — Global planning, task decomposition, and result verification
- **DeepSeek V4 Flash** — Parallel subtask execution with tool access, fast and cost-efficient

Each request flows through three phases with animated progress indicators:

1. **PLANNING** (Pro) — Analyze request, decompose into parallel subtasks
2. **EXECUTING** (Flash) — Workers execute subtasks concurrently with live progress
3. **VERIFYING** (Pro) — Review all results, synthesize final answer

## Installation

```bash
pip install -e .
```

## Quick Start

1. Set your API key:

```bash
# Environment variable
export DEEPSEEK_API_KEY="your-api-key-here"

# Or project-local config (auto-gitignored)
mkdir -p .deep-coder
cat > .deep-coder/config.toml << 'EOF'
[model]
api_key = "your-api-key-here"
EOF
```

2. Run:

```bash
deep-coder
```

## Skills

Purpose-built developer workflow commands — type the slash command instead of verbose prompts.

| Command | Description |
|---|---|
| `/review [file\|staged]` | AI code review for staged changes or a specific file |
| `/commit [hint]` | Generate smart commit message and commit |
| `/test [command]` | Run tests (auto-detect framework) and analyze failures |
| `/fix <error>` | Analyze error message / traceback and fix root cause |
| `/think <question>` | Deep reasoning for architecture and design questions |
| `/pr [base]` | Generate PR title and description from branch diff |
| `/explain [file:lines]` | Explain code, file, or project overview |

## Session Commands

| Command | Description |
|---|---|
| `/clear` | Clear conversation history and file snapshots |
| `/compact` | Compress conversation history to free context space |
| `/cost` | Show token usage and estimated cost |
| `/save [name]` | Save current session for later |
| `/resume [name]` | Resume a saved session (no arg = list sessions) |

## Code Commands

| Command | Description |
|---|---|
| `/diff` | Show all file changes made in this session |
| `/undo` | Revert the last file modification |
| `/init` | Scan project and generate CODER.md |

## Settings

| Command | Description |
|---|---|
| `/config` | Show current configuration |
| `/model` | Show model information |

## Shell Integration

Run shell commands inline without leaving Deep Coder:

```
! git status
! ls -la
! pytest tests/
```

Interactive programs (vim, nano, less, ssh, etc.) are automatically detected and given full terminal control — edit files in vim and return seamlessly to the Deep Coder prompt.

## Interrupt Handling

- **Ctrl+C during a task** — Gracefully cancels the current operation
- **Ctrl+C at the prompt** — Shows "Press Ctrl+C again to exit"
- **Ctrl+C twice** — Exits cleanly, no tracebacks

## Inline Diff Display

When the agent edits files, changes are shown as Claude-style inline diffs with syntax highlighting:

```
⏺ Update(deep_coder/cli.py)
  ⎿  Added 3 lines, Removed 1 line
        5   import sys
        6 - from typing import Any
        6 + import json
        7 + from typing import Any, Optional
        8
```

## Available Tools

The agent workers have access to these tools:

| Tool | Description |
|---|---|
| `read_file` | Read file contents with line numbers |
| `write_file` | Create or overwrite files |
| `edit_file` | Search-and-replace edits |
| `list_files` | List directory contents with glob patterns |
| `grep_files` | Regex search across files |
| `glob_files` | Find files by pattern |
| `exec_shell` | Execute shell commands |
| `git_status` | Show git working tree status |
| `git_diff` | Show git diffs |
| `git_log` | Show git commit history |
| `git_commit` | Create git commits |

## VS code plugins  

```shell
  cd plugins/vscode
  npm install && npm run compile     
  npx @vscode/vsce package           
  npx @vscode/vsce publish        
```

## Configuration

Configuration is loaded in priority order (later overrides earlier):

1. **Global config**: `~/.deep-coder/config.toml`
2. **Project-local config**: `.deep-coder/config.toml` (gitignored)
3. **Environment variables**

Example `config.toml`:

```toml
[model]
pro_model = "deepseek-v4-pro"
flash_model = "deepseek-v4-flash"
base_url = "https://api.deepseek.com"
api_key = ""
max_tokens = 8192
temperature = 0.0

[agent]
max_workers = 5
worker_timeout = 120
```

| Environment Variable | Description |
|---|---|
| `DEEPSEEK_API_KEY` | Your DeepSeek API key |
| `DEEPSEEK_BASE_URL` | API base URL |
| `DEEPSEEK_PRO_MODEL` | Pro model ID |
| `DEEPSEEK_FLASH_MODEL` | Flash model ID |

## Project Structure

```
deep_coder/
├── cli.py                # REPL, command dispatch, shell integration
├── config.py             # Configuration management
├── client.py             # DeepSeek API client (OpenAI-compatible)
├── models.py             # Model definitions and registry
├── display.py            # Rich terminal output, diffs, spinners
├── agent/
│   ├── orchestrator.py   # Pro model: planning & verification
│   ├── worker.py         # Flash model: subtask execution
│   └── task.py           # Task data model
├── tools/
│   ├── base.py           # Tool base class, registry, snapshot tracker
│   ├── file_ops.py       # File operation tools
│   ├── shell.py          # Shell execution tool
│   ├── search.py         # Search tools (grep, glob)
│   └── git.py            # Git integration tools
├── skills/
│   ├── base.py           # Skill ABC and SkillContext
│   ├── review.py         # /review — AI code review
│   ├── commit.py         # /commit — smart commit messages
│   ├── test_skill.py     # /test — run & analyze tests
│   ├── fix.py            # /fix — error diagnosis & fix
│   ├── think.py          # /think — deep reasoning
│   ├── pr.py             # /pr — PR description generation
│   └── explain.py        # /explain — code explanation
└── prompts/
    ├── system.py         # Prompt template management
    ├── orchestrator.txt  # Orchestrator system prompt
    └── worker.txt        # Worker system prompt
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

## License

AGPL-3.0

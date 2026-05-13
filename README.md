# Deep Coder

[![CI](https://github.com/xsank/deep-coder/actions/workflows/ci.yml/badge.svg)](https://github.com/xsank/deep-coder/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/deep-coder)](https://pypi.org/project/deep-coder/)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](https://pypi.org/project/deep-coder/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
![Coverage](assets/coverage-badge.svg)

The most cost-effective code assistant tool based on DeepSeek V4.

## Architecture

Deep Coder uses a **two-tier agent architecture** with **DAG-based task scheduling** and a **verification loop** for optimal cost-performance balance:

```
                  User Input
                      │
                      ▼
          ┌───────────────────────┐
          │ Orchestrator (V4 Pro) │  Plan generation (JSON Task DAG)
          │  "Think"              │  ↓ Each task declares dependencies
          └───────────┬───────────┘
                      │ Plan (Task DAG)
                      ▼
          ┌───────────────────────┐
          │   Execution Engine    │  Pick ready tasks (all deps met)
          │   (asyncio gather)    │  Launch up to max_workers in parallel
          └──┬───────┬───────┬────┘
             │       │       │
     ┌───────┴┐ ┌────┴───┐ ┌─┴──────┐
     │Worker  │ │Worker  │ │Worker  │  Parallel execution (V4 Flash)
     │Task A  │ │Task B  │ │Task C  │  Each has tool access & retry
     └───────┬┘ └────┬───┘ └────────┘
             │       │
        ┌────┴───────┴────┐
        │   Task D        │  Depends on A + B → starts after both done
        └────────┬────────┘
                 │
                 ▼
     ┌─────────────────────────┐
     │ Orchestrator (V4 Pro)   │  VERIFICATION
     │  "Verify"               │  JSON verdict: "complete" or "continue"
     └───────────┬─────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
   "complete"          "continue"
       │                   │
       ▼                   ▼
   Final report    Generate new plan
   to user         (replan & re-execute)
                   loop continues
```

### Task DAG with Maximal Parallelism

The **Orchestrator** (Pro model) decomposes the user's request into a JSON plan where each task declares:

- `id` — Unique identifier
- `description` — Instructions for the Worker
- `depends_on` — List of task IDs that must complete first

The **Execution Engine** uses topological ordering: it continuously picks **ready tasks** (all dependencies satisfied) and launches them concurrently via `asyncio.gather`, up to `max_workers` (default: 5). Tasks with no dependencies run immediately in parallel; dependent tasks start as soon as their prerequisites finish. This maximizes parallelism while respecting ordering constraints.

### Verification Loop

After all tasks in the current plan complete, the **Orchestrator** re-engages to:

1. **Analyze** all task results and the original request
2. **Issue a JSON verdict** — either `"complete"` (goal achieved) or `"continue"` (needs changes)
3. **On "continue"** — Generate a new plan (with new Task DAG) addressing what's missing
4. **Loop** — The new plan feeds back into the Execution Engine, and the cycle repeats

This creates a **closed verification loop**: `Plan → Execute → Verify → Replan → Execute → ... → Complete`. The loop terminates only when the Orchestrator judges the goal fully satisfied, ensuring correctness without manual intervention.

### Cost-Performance Strategy

- **DeepSeek V4 Pro** — Used only for planning (brainstorming decomposition) and verification (quality gate). These are the "thinking" steps.
- **DeepSeek V4 Flash** — Used for all actual tool execution (reading files, editing code, running shell commands). These are the "doing" steps, run in parallel.
- **Automatic retry** — Failed tasks are retried once before reporting failure to the Orchestrator.

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

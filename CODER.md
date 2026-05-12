# Deep Coder — CODER.md

## 1. Project Overview

**Deep Coder** (v0.1.0) is a cost-optimized AI code assistant that runs in the terminal. It uses **DeepSeek V4 Pro** as its "Orchestrator" (for planning & verification) and **DeepSeek V4 Flash** as its "Workers" (for parallel subtask execution). It provides a REPL with slash commands (`/review`, `/commit`, `/test`, `/fix`, `/think`, `/pr`, `/explain`), shell integration, inline diff display, and session management. Built for developer productivity — think of it as an open-source, terminal-native alternative to Claude Code / GitHub Copilot powered by DeepSeek.

**Key differentiator**: Two-tier architecture optimizes cost by using an expensive reasoning model for high-level thinking and a cheap model for the heavy-lifting tool execution.

License: **AGPL-3.0**

---

## 2. Tech Stack & Dependencies

| Requirement | Value |
|---|---|
| **Python** | `>=3.10` (tested on 3.10–3.13) |
| **Build system** | setuptools + wheel |
| **Linting** | ruff (line-length 100, target py310, rules E/F/I/W) |
| **Testing** | pytest 8+, pytest-asyncio (asyncio_mode = "auto") |

### Core Dependencies

| Package | Version | Purpose |
|---|---|---|
| `openai` | >=1.30.0 | Async OpenAI-compatible API client for DeepSeek |
| `rich` | >=13.0.0 | Terminal output: syntax highlighting, spinners, live displays |
| `prompt-toolkit` | >=3.0.0 | REPL input: history, key bindings, tab completion |
| `pydantic` | >=2.0.0 | Config data models with validation |
| `httpx` | >=0.27.0 | Async HTTP (used by openai client under the hood) |
| `tomli` (or `tomllib` on 3.11+) | >=2.0.0 | TOML config parsing |
| `tomli-w` | >=1.0.0 | TOML config writing (save command) |

### Dev Dependencies

| Package | Purpose |
|---|---|
| `pytest>=8.0.0` | Test runner |
| `pytest-asyncio>=0.23.0` | Async test support |
| `ruff>=0.4.0` | Linter & formatter |

---

## 3. Directory Structure

```
deep-coder/
├── pyproject.toml              # Project metadata, dependencies, scripts, tool config
├── README.md                   # User-facing docs, installation, command reference
├── CLAUDE.md                   # Claude Code guidance (mirrors arch info for AI assistants)
├── LICENSE                     # AGPL-3.0 license
├── .gitignore
├── .deep-coder/
│   └── config.toml             # Project-local config (gitignored) — API key, model settings
├── .claude/
│   └── settings.local.json     # Claude Code local settings
├── deep_coder/                 # Main source package
│   ├── __init__.py             # Package init — exports __version__ = "0.1.0"
│   ├── __main__.py             # Entry point for `python -m deep_coder`
│   ├── cli.py                  # REPL loop, command dispatch, shell integration, slash completer
│   ├── config.py               # Config loading (global → local → env), pydantic models
│   ├── client.py               # Async DeepSeek API client, token tracking, streaming
│   ├── models.py               # ModelInfo, ModelRegistry, ModelRole enum (pro/flash)
│   ├── display.py              # Rich terminal: spinners, streaming, diffs, panels
│   ├── agent/                  # Two-tier agent system
│   │   ├── orchestrator.py     # Pro model: planning, task decomposition, verification
│   │   ├── worker.py           # Flash model: parallel subtask execution with tool access
│   │   └── task.py             # Task/Plan dataclasses, TaskStatus enum
│   ├── tools/                  # Tool system (agent tools accessible to workers)
│   │   ├── base.py             # Tool ABC, ToolRegistry, ToolResult, snapshot tracker (undo)
│   │   ├── file_ops.py         # read_file, write_file, edit_file, list_files
│   │   ├── shell.py            # exec_shell — shell command execution
│   │   ├── search.py           # grep_files, glob_files — search tools
│   │   └── git.py              # git_status, git_diff, git_log, git_commit
│   ├── skills/                 # Slash command skills
│   │   ├── base.py             # Skill ABC, SkillContext dataclass, SkillRegistry
│   │   ├── review.py           # /review — AI code review
│   │   ├── commit.py           # /commit — smart commit messages
│   │   ├── test_skill.py       # /test — run & analyze test failures
│   │   ├── fix.py              # /fix — error diagnosis
│   │   ├── think.py            # /think — deep reasoning
│   │   ├── pr.py               # /pr — PR title & description
│   │   └── explain.py          # /explain — code explanation
│   └── prompts/                # System prompt templates
│       ├── system.py           # Prompt loading & assembly (injects CODER.md context)
│       ├── orchestrator.txt    # Orchestrator system prompt (planning agent)
│       └── worker.txt          # Worker system prompt (execution agent)
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_tools.py           # Tool system tests
│   ├── test_client.py          # API client tests
│   └── test_orchestrator.py    # Orchestrator tests
└── plugins/                    # (empty) Plugin directory — not yet populated
```

---

## 4. Key Conventions

### Code Style
- **`from __future__ import annotations`** — placed at the top of every `.py` file
- **Full type annotations** on all function/method signatures
- **Async-first** — all I/O operations are async (`async def`)
- **Ruff linting** — line-length 100, target Python 3.10, rules `E/F/I/W` (pycodestyle, pyflakes, import sorting, pycodestyle warnings)

### Naming
- `snake_case` for functions, methods, variables
- `PascalCase` for classes
- `UPPER_CASE` for constants (e.g., `DEFAULT_BASE_URL`, `GLOBAL_CONFIG_DIR`)
- Slash command names use `snake_case` for files: `test_skill.py`, `fix.py`

### Architectural Patterns
- **ABC + Registry pattern**: Abstract base classes (`Tool`, `Skill`) with lazy-loaded registries (`ToolRegistry`, `SkillRegistry`) via factory functions to avoid circular imports
- **Pydantic `BaseModel`** for configuration objects (`ModelConfig`, `AgentConfig`, `Config`)
- **`@dataclass`** for data transfer objects (`Task`, `Plan`, `ToolResult`, `SkillContext`, `UsageStats`)
- **`Enum`** for fixed categories (`ModelRole`, `TaskStatus`)
- **Lazy imports** inside factory functions (`create_default_registry()`, `create_default_skills()`) to avoid circular dependency issues
- **Config priority**: global (`~/.deep-coder/config.toml`) → project-local (`.deep-coder/config.toml`) → environment variables (later overrides earlier)
- **Snapshot tracking** in tool system enables `/diff` and `/undo` commands via file snapshots taken before modification

### Project Structure Pattern
- Flat package `deep_coder/` with subpackages for major concerns: `agent/`, `tools/`, `skills/`, `prompts/`
- Each subpackage has its own `__init__.py` and `base.py` for the abstract foundation

---

## 5. Build / Test / Run Commands

### Installation
```bash
# Editable install (development)
pip install -e .

# With dev dependencies (pytest, ruff)
pip install -e ".[dev]"
```

### Run
```bash
# Via CLI script entry point
deep-coder

# Or via module
python -m deep_coder
```

### Testing
```bash
# Run all tests
pytest

# Run a specific test file with verbose output
pytest tests/test_tools.py -v

# Tests use pytest-asyncio with asyncio_mode = "auto"
# No @pytest.mark.asyncio decorator needed — just write async test functions
```

### Linting
```bash
# Check for lint errors
ruff check deep_coder/ tests/

# Auto-fix where possible
ruff check deep_coder/ tests/ --fix
```

### Environment Setup
```bash
# Required: Set your DeepSeek API key
export DEEPSEEK_API_KEY="sk-your-key-here"

# Optional: Custom base URL
export DEEPSEEK_BASE_URL="https://api.deepseek.com"
```

### Config File (Alternative to env vars)
```toml
# .deep-coder/config.toml
[model]
api_key = "sk-your-key-here"
pro_model = "deepseek-v4-pro"
flash_model = "deepseek-v4-flash"
base_url = "https://api.deepseek.com"
max_tokens = 8192
temperature = 0.0

[agent]
max_workers = 5
worker_timeout = 120
```

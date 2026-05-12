# Deep Coder — Project Overview

## Project Overview

**Deep Coder** is a cost-effective AI code assistant CLI tool powered by **DeepSeek V4**. It uses a **two-tier agent architecture**:

- **Orchestrator (V4 Pro)**: Handles planning, task decomposition, and result verification. It has *no direct tool access* — everything is delegated to workers.
- **Workers (V4 Flash)**: Execute individual subtasks in parallel using a suite of file/shell/search tools. Fast and cost-efficient.

The user interacts via a REPL with slash commands (`/review`, `/commit`, `/fix`, `/think`, `/explain`, `/pr`, `/test`) and can also run shell commands inline with `! <cmd>`.

---

## Tech Stack & Dependencies

| Category | Technology |
|---|---|
| **Language** | Python >= 3.10 |
| **AI Models** | DeepSeek V4 Pro (planning/verification), DeepSeek V4 Flash (execution) |
| **API Client** | `openai>=1.30.0` (OpenAI-compatible SDK for DeepSeek API) |
| **Terminal UI** | `rich>=13.0.0` (markdown, panels, spinners, live display) |
| **REPL** | `prompt-toolkit>=3.0.0` (autocomplete, history, vi mode) |
| **Config** | `pydantic>=2.0.0`, `tomli>=2.0.0`, `tomli-w>=1.0.0` |
| **HTTP** | `httpx>=0.27.0` |
| **Linting** | `ruff>=0.4.0` (dev) |
| **Testing** | `pytest>=8.0.0`, `pytest-asyncio>=0.23.0` (dev) |
| **License** | AGPL-3.0 |

---

## Directory Structure

```
deep-coder/
├── deep_coder/                      # Main source package
│   ├── __init__.py                  # Package metadata (__version__ = "0.1.0")
│   ├── __main__.py                  # `python -m deep_coder` entry point
│   ├── cli.py                       # REPL loop, slash command dispatch, autocomplete
│   ├── config.py                    # Config loading (TOML + env vars), Pydantic models
│   ├── client.py                    # Async DeepSeek API client (OpenAI-compatible SDK)
│   ├── models.py                    # Model definitions, role enums (Pro/Flash), registry
│   ├── display.py                   # Rich terminal: banner, spinners, phase indicators, cost panel
│   ├── agent/                       # Two-tier agent architecture
│   │   ├── __init__.py
│   │   ├── orchestrator.py          # Pro model: plans tasks, verifies results, compacts history
│   │   ├── worker.py                # Flash model: executes single task with tool loop (max 15 iterations)
│   │   └── task.py                  # Task & Plan data models (TaskStatus, dependency resolution)
│   ├── tools/                       # Tool system (OpenAI function-calling compatible)
│   │   ├── __init__.py
│   │   ├── base.py                  # Tool ABC, ToolResult, SnapshotTracker (undo), ToolRegistry
│   │   ├── file_ops.py              # read_file, write_file, edit_file, list_files
│   │   ├── search.py                # grep_files (regex), glob_files (pattern)
│   │   ├── shell.py                 # exec_shell (async subprocess with timeout)
│   │   └── git.py                   # git_status, git_diff, git_log, git_commit
│   ├── skills/                      # Developer slash-command skills
│   │   ├── __init__.py              # SkillRegistry, create_default_skills()
│   │   ├── base.py                  # Skill ABC, SkillContext, helper methods
│   │   ├── review.py                # /review — AI code review of file or staged diff
│   │   ├── commit.py                # /commit — Generate & commit with AI message
│   │   ├── test_skill.py            # /test — Auto-detect framework, run tests, analyze failures
│   │   ├── fix.py                   # /fix — Analyze error traceback and apply fix
│   │   ├── think.py                 # /think — Deep reasoning for architecture questions
│   │   ├── pr.py                    # /pr — Generate PR title/description from branch diff
│   │   └── explain.py              # /explain — Explain a file, function, or project
│   └── prompts/                     # System prompt templates (loaded as .txt files)
│       ├── __init__.py
│       ├── system.py                # get_orchestrator_prompt(), get_worker_prompt()
│       ├── orchestrator.txt         # Pro model: role, task plan JSON format, verification rules
│       └── worker.txt               # Flash model: role, available tools, response format
├── tests/                           # Test suite
│   ├── __init__.py
│   ├── test_client.py               # Client creation & model routing tests
│   ├── test_orchestrator.py         # Task & Plan lifecycle, dependency resolution tests
│   └── test_tools.py                # Tool registry, read/write/edit/grep/shell tests
├── plugins/
│   └── vscode/                      # Future VS Code extension placeholder
├── pyproject.toml                   # Build config, dependencies, scripts, ruff/pytest settings
├── README.md                        # User-facing documentation
├── LICENSE                          # AGPL-3.0 license
├── .gitignore                       # Standard Python + Deep Coder local config
└── CODER.md                         # This file — AI assistant project guide
```

---

## Key Conventions Observed

1. **`from __future__ import annotations`**: Used in almost every Python file for deferred evaluation of type hints.
2. **Type hints**: All functions/methods are fully annotated using `typing` module (`Any`, `Optional`, `TYPE_CHECKING` for import guards).
3. **Async-first**: All I/O operations are async (`asyncio`, `async/await`). Tools, client, and orchestrator all use async patterns.
4. **`__init__.py` files**: Used for lazy imports in factory functions (e.g., `create_default_registry()`, `create_default_skills()` import inside functions to avoid circular dependencies).
5. **Pydantic for config**: `Config`, `ModelConfig`, `AgentConfig` are Pydantic `BaseModel` subclasses with `Field()` defaults.
6. **Dataclasses for data models**: `Task`, `Plan`, `ToolResult`, `FileSnapshot`, `UsageStats`, `SkillContext` use `@dataclass`.
7. **Enum for states**: `ModelRole` (PRO/FLASH), `TaskStatus` (PENDING/RUNNING/COMPLETED/FAILED).
8. **ABC for extensibility**: `Tool` and `Skill` are abstract base classes that new tools/skills extend via registration.
9. **Config loading priority**: Global config → Project-local `.deep-coder/config.toml` → Environment variables (later overrides earlier).
10. **Prompt-as-templates**: System prompts stored as `.txt` files in `prompts/` and loaded by `system.py`.
11. **Linting**: `ruff` with line-length 100, target Python 3.10, selects E/F/I/W rules.
12. **Testing**: `pytest` with `asyncio_mode = "auto"`, no need for `@pytest.mark.asyncio` (though some tests still use it explicitly).

---

## Build / Test / Run Commands

```bash
# Install (editable)
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run the CLI
deep-coder

# Or via Python module
python -m deep_coder

# Run tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/test_tools.py -v

# Lint with ruff
ruff check deep_coder/ tests/

# Configuration
export DEEPSEEK_API_KEY="your-api-key"
# Or create .deep-coder/config.toml with your API key
```

### Slash Commands Reference
| Command | Description |
|---|---|
| `/review [file\|staged]` | AI code review |
| `/commit [hint]` | Generate commit message & commit |
| `/test [command]` | Run tests & analyze failures |
| `/fix <error>` | Analyze error & fix root cause |
| `/think <question>` | Deep reasoning for architecture |
| `/pr [base]` | Generate PR description |
| `/explain [file:lines]` | Explain code |
| `/help` | Show all commands |
| `/cost` | Show token usage & cost |
| `/diff` | Show file changes |
| `/undo` | Revert last change |
| `/compact` | Compress conversation history |
| `/init` | Generate CODER.md |
| `/save` / `/resume` | Session management |
| `! <command>` | Run shell command inline |

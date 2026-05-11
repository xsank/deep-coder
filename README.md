# Deep Coder

The most cost-effective code assistant tool based on DeepSeek V4.

## Architecture

Deep Coder uses a **two-tier agent architecture** for optimal cost-performance balance:

```
User Input
    |
    v
+----------------------------+
| Orchestrator (V4 Pro)      |  Planning, design, verification
| - Analyze request          |
| - Decompose into subtasks  |
+----------------------------+
    |
    +--------+--------+
    v        v        v
+--------+--------+--------+
| Worker | Worker | Worker |  Parallel execution (V4 Flash)
| Task 1 | Task 2 | Task 3 |
+--------+--------+--------+
    |        |        |
    +--------+--------+
    v
+----------------------------+
| Orchestrator (V4 Pro)      |  Result verification
| - Review all results       |
| - Synthesize final answer  |
+----------------------------+
```

- **DeepSeek V4 Pro**: Used for global planning, task decomposition, and final result verification
- **DeepSeek V4 Flash**: Used for parallel subtask execution — fast and cost-efficient

## Installation

```bash
pip install -e .
```

## Quick Start

1. Set your API key (choose one method):

```bash
# Method A: Environment variable
export DEEPSEEK_API_KEY="your-api-key-here"

# Method B: Project-local config (recommended, auto-gitignored)
mkdir -p .deep-coder
cat > .deep-coder/config.toml << 'EOF'
[model]
api_key = "your-api-key-here"
EOF
```

2. Run Deep Coder:

```bash
deep-coder
```

## Configuration

Configuration is loaded in priority order (later overrides earlier):

1. **Global config**: `~/.deep-coder/config.toml`
2. **Project-local config**: `.deep-coder/config.toml` (in project root, gitignored)
3. **Environment variables**: `DEEPSEEK_API_KEY`, etc.

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

Environment variables override config file settings:

| Variable | Description |
|---|---|
| `DEEPSEEK_API_KEY` | Your DeepSeek API key |
| `DEEPSEEK_BASE_URL` | API base URL |
| `DEEPSEEK_PRO_MODEL` | Pro model ID |
| `DEEPSEEK_FLASH_MODEL` | Flash model ID |

## CLI Commands

| Command | Description |
|---|---|
| `/help` | Show available commands |
| `/clear` | Clear conversation history |
| `/config` | Show current configuration |
| `/model` | Show model information |
| `/exit` | Exit Deep Coder |

## Available Tools

The agent has access to these tools for code operations:

- **read_file** — Read file contents with line numbers
- **write_file** — Create or overwrite files
- **edit_file** — Search-and-replace edits
- **list_files** — List directory contents with glob patterns
- **grep_files** — Regex search across files
- **glob_files** — Find files by pattern
- **exec_shell** — Execute shell commands (with approval)

## Development

```bash
pip install -e ".[dev]"
pytest
```

## Project Structure

```
deep_coder/
├── cli.py              # REPL and command dispatch
├── config.py           # Configuration management
├── client.py           # DeepSeek API client (OpenAI-compatible)
├── models.py           # Model definitions and registry
├── display.py          # Rich terminal output
├── agent/
│   ├── orchestrator.py # Pro model: planning & verification
│   ├── worker.py       # Flash model: subtask execution
│   └── task.py         # Task data model
├── tools/
│   ├── base.py         # Tool base class & registry
│   ├── file_ops.py     # File operation tools
│   ├── shell.py        # Shell execution tool
│   └── search.py       # Search tools (grep, glob)
└── prompts/
    ├── system.py       # Prompt template management
    ├── orchestrator.txt # Orchestrator system prompt
    └── worker.txt      # Worker system prompt
plugins/
└── vscode/             # Future VS Code extension
```

## License

AGPL-3.0

# Deep Coder VS Code Extension

AI coding assistant powered by DeepSeek V4 — two-tier agent with Pro planning and Flash execution.

## Features

- **Sidebar Chat Panel** — interact with Deep Coder directly in VS Code
- **Real-time Planning** — see the orchestrator's reasoning as it plans
- **Task Progress** — watch parallel Flash workers execute tasks
- **Inline Diffs** — file changes displayed with syntax-aware highlighting
- **Tool Approval** — approve or deny destructive operations with one click
- **Cost Tracking** — live token usage and cost in the status bar

## Requirements

- Python 3.10+
- `deep-coder` CLI installed (`pip install deep-coder`)
- `DEEPSEEK_API_KEY` environment variable set

## Setup

1. Install the extension (`.vsix` file or from marketplace)
2. The extension auto-starts the Deep Coder server on port 9120
3. Open the sidebar panel (Deep Coder icon in the activity bar)
4. Start chatting!

## Configuration

| Setting | Default | Description |
|---|---|---|
| `deep-coder.serverPort` | `9120` | WebSocket server port |
| `deep-coder.autoStartServer` | `true` | Auto-start server on activation |
| `deep-coder.pythonPath` | `deep-coder` | Path to the deep-coder CLI |

## Commands

- `Deep Coder: Start Server` — manually start the backend server
- `Deep Coder: Stop Server` — stop the backend server
- `Deep Coder: Review Code` — run AI code review (`/review`)
- `Deep Coder: Explain Selection` — explain selected code

## Development

```bash
cd plugins/vscode
npm install
npm run watch    # Development mode with auto-rebuild
```

## Build & Publish

```bash
npm run compile              # Production build
npx @vscode/vsce package     # Create .vsix file
npx @vscode/vsce publish     # Publish to marketplace
```

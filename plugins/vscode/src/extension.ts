import * as vscode from "vscode";
import * as cp from "child_process";
import { DeepCoderClient } from "./client";
import { ChatPanelProvider } from "./chatPanel";
import { StatusBar } from "./statusBar";

let client: DeepCoderClient;
let statusBar: StatusBar;
let chatProvider: ChatPanelProvider;
let serverProcess: cp.ChildProcess | null = null;

export function activate(context: vscode.ExtensionContext): void {
  const config = vscode.workspace.getConfiguration("deep-coder");
  const port = config.get<number>("serverPort", 9120);

  client = new DeepCoderClient("127.0.0.1", port);
  statusBar = new StatusBar(client);
  chatProvider = new ChatPanelProvider(context.extensionUri, client);

  context.subscriptions.push(statusBar);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      ChatPanelProvider.viewType,
      chatProvider
    )
  );

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("deep-coder.startServer", () => {
      startServer(config);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("deep-coder.stopServer", () => {
      stopServer();
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("deep-coder.review", () => {
      client.sendCommand("/review");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("deep-coder.explain", () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) {
        vscode.window.showWarningMessage("No active editor");
        return;
      }
      const selection = editor.document.getText(editor.selection);
      if (!selection) {
        vscode.window.showWarningMessage("No text selected");
        return;
      }
      const file = editor.document.fileName;
      client.sendChat(
        `Explain this code from ${file}:\n\`\`\`\n${selection}\n\`\`\``
      );
    })
  );

  // Auto-start server
  if (config.get<boolean>("autoStartServer", true)) {
    startServer(config);
  }

  // Connect WebSocket
  setTimeout(() => client.connect(), 1000);
}

function startServer(
  config: vscode.WorkspaceConfiguration
): void {
  if (serverProcess) {
    vscode.window.showInformationMessage("Deep Coder server is already running");
    return;
  }

  const pythonPath = config.get<string>("pythonPath", "deep-coder");
  const port = config.get<number>("serverPort", 9120);
  const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;

  try {
    serverProcess = cp.spawn(pythonPath, ["--serve", "--port", String(port)], {
      cwd: cwd,
      stdio: "pipe",
    });

    serverProcess.on("error", (err) => {
      vscode.window.showErrorMessage(
        `Failed to start Deep Coder server: ${err.message}. ` +
        `Make sure 'deep-coder' is installed (pip install deep-coder).`
      );
      serverProcess = null;
    });

    serverProcess.on("exit", (code) => {
      if (code !== 0 && code !== null) {
        vscode.window.showWarningMessage(
          `Deep Coder server exited with code ${code}`
        );
      }
      serverProcess = null;
    });

    serverProcess.stderr?.on("data", (data: Buffer) => {
      const text = data.toString().trim();
      if (text) {
        console.log(`[deep-coder server] ${text}`);
      }
    });

    // Reconnect WebSocket after server starts
    setTimeout(() => client.connect(), 2000);
    vscode.window.showInformationMessage(
      `Deep Coder server starting on port ${port}...`
    );
  } catch (err) {
    vscode.window.showErrorMessage(`Failed to start server: ${err}`);
  }
}

function stopServer(): void {
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
    vscode.window.showInformationMessage("Deep Coder server stopped");
  } else {
    vscode.window.showInformationMessage("No server running");
  }
}

export function deactivate(): void {
  client?.disconnect();
  statusBar?.dispose();
  chatProvider?.dispose();
  if (serverProcess) {
    serverProcess.kill();
    serverProcess = null;
  }
}

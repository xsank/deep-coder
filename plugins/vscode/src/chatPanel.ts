import * as vscode from "vscode";
import { DeepCoderClient, ServerMessage } from "./client";

export class ChatPanelProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = "deep-coder.chat";
  private view?: vscode.WebviewView;
  private disposable?: vscode.Disposable;

  constructor(
    private readonly extensionUri: vscode.Uri,
    private readonly client: DeepCoderClient
  ) {}

  resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ): void {
    this.view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [
        vscode.Uri.joinPath(this.extensionUri, "media"),
      ],
    };

    webviewView.webview.html = this.getHtml(webviewView.webview);

    // Forward webview messages to server
    webviewView.webview.onDidReceiveMessage((msg) => {
      switch (msg.type) {
        case "chat":
          this.client.sendChat(msg.message);
          break;
        case "cancel":
          this.client.sendCancel();
          break;
        case "approval_response":
          this.client.sendApproval(msg.id, msg.approved);
          break;
        case "command":
          this.client.sendCommand(msg.command);
          break;
      }
    });

    // Forward server messages to webview
    this.disposable = this.client.onMessage((msg: ServerMessage) => {
      this.view?.webview.postMessage(msg);
    });
  }

  private getHtml(webview: vscode.Webview): string {
    const cssUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "media", "chat.css")
    );
    const jsUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this.extensionUri, "media", "chat.js")
    );
    const nonce = getNonce();

    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Content-Security-Policy"
    content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <link href="${cssUri}" rel="stylesheet">
  <title>Deep Coder Chat</title>
</head>
<body>
  <div id="chat-container">
    <div id="messages"></div>
    <div id="status-bar">
      <span id="status-text">Disconnected</span>
      <span id="cost-text"></span>
    </div>
    <div id="input-area">
      <textarea id="input" placeholder="Ask Deep Coder..." rows="2"></textarea>
      <div id="input-actions">
        <button id="send-btn" title="Send (Enter)">Send</button>
        <button id="cancel-btn" title="Cancel" class="secondary" style="display:none">Cancel</button>
      </div>
    </div>
  </div>
  <script nonce="${nonce}" src="${jsUri}"></script>
</body>
</html>`;
  }

  dispose(): void {
    this.disposable?.dispose();
  }
}

function getNonce(): string {
  let text = "";
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return text;
}

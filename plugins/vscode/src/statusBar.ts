import * as vscode from "vscode";
import { DeepCoderClient, ServerMessage } from "./client";

export class StatusBar {
  private item: vscode.StatusBarItem;
  private disposable: vscode.Disposable;

  constructor(client: DeepCoderClient) {
    this.item = vscode.window.createStatusBarItem(
      vscode.StatusBarAlignment.Right,
      100
    );
    this.item.command = "deep-coder.startServer";
    this.updateDisconnected();
    this.item.show();

    this.disposable = client.onMessage((msg: ServerMessage) => {
      if (msg.type === "connection") {
        if (msg.status === "connected") {
          this.updateConnected();
        } else {
          this.updateDisconnected();
        }
      } else if (msg.type === "cost") {
        const cost = msg.cost as number;
        this.item.text = `$(code) Deep Coder $${cost.toFixed(4)}`;
      }
    });
  }

  private updateConnected(): void {
    this.item.text = "$(code) Deep Coder";
    this.item.tooltip = "Deep Coder: Connected";
    this.item.backgroundColor = undefined;
  }

  private updateDisconnected(): void {
    this.item.text = "$(code) Deep Coder (offline)";
    this.item.tooltip = "Deep Coder: Disconnected — click to start server";
    this.item.backgroundColor = new vscode.ThemeColor(
      "statusBarItem.warningBackground"
    );
  }

  dispose(): void {
    this.disposable.dispose();
    this.item.dispose();
  }
}

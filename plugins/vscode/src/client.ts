import * as vscode from "vscode";
import WebSocket from "ws";

export interface ServerMessage {
  type: string;
  [key: string]: unknown;
}

type MessageHandler = (msg: ServerMessage) => void;

export class DeepCoderClient {
  private ws: WebSocket | null = null;
  private handlers: MessageHandler[] = [];
  private reconnectTimer: NodeJS.Timeout | null = null;
  private _connected = false;

  constructor(
    private host: string = "127.0.0.1",
    private port: number = 9120
  ) {}

  get connected(): boolean {
    return this._connected;
  }

  connect(): void {
    if (this.ws) {
      this.ws.close();
    }

    const url = `ws://${this.host}:${this.port}/ws`;
    this.ws = new WebSocket(url);

    this.ws.on("open", () => {
      this._connected = true;
      this.emit({ type: "connection", status: "connected" });
    });

    this.ws.on("message", (data: WebSocket.Data) => {
      try {
        const msg = JSON.parse(data.toString()) as ServerMessage;
        this.emit(msg);
      } catch {
        // ignore malformed messages
      }
    });

    this.ws.on("close", () => {
      this._connected = false;
      this.emit({ type: "connection", status: "disconnected" });
      this.scheduleReconnect();
    });

    this.ws.on("error", () => {
      this._connected = false;
    });
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this._connected = false;
  }

  sendChat(message: string): void {
    this.send({ type: "chat", message });
  }

  sendCommand(command: string): void {
    this.send({ type: "command", command });
  }

  sendCancel(): void {
    this.send({ type: "cancel" });
  }

  sendApproval(id: string, approved: boolean): void {
    this.send({ type: "approval_response", id, approved });
  }

  onMessage(handler: MessageHandler): vscode.Disposable {
    this.handlers.push(handler);
    return new vscode.Disposable(() => {
      const idx = this.handlers.indexOf(handler);
      if (idx >= 0) {
        this.handlers.splice(idx, 1);
      }
    });
  }

  private send(data: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data));
    }
  }

  private emit(msg: ServerMessage): void {
    for (const handler of this.handlers) {
      handler(msg);
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, 3000);
  }
}

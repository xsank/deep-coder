// @ts-nocheck
(function () {
  const vscode = acquireVsCodeApi();
  const messagesEl = document.getElementById("messages");
  const inputEl = document.getElementById("input");
  const sendBtn = document.getElementById("send-btn");
  const cancelBtn = document.getElementById("cancel-btn");
  const statusText = document.getElementById("status-text");
  const costText = document.getElementById("cost-text");

  let streaming = false;
  let currentAssistantEl = null;
  let planningEl = null;
  let taskProgressEl = null;

  // --- Send message ---
  function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    if (text.startsWith("/")) {
      vscode.postMessage({ type: "command", command: text });
    } else {
      vscode.postMessage({ type: "chat", message: text });
    }

    appendUserMessage(text);
    inputEl.value = "";
    setStreaming(true);
  }

  sendBtn.addEventListener("click", sendMessage);
  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  cancelBtn.addEventListener("click", () => {
    vscode.postMessage({ type: "cancel" });
    setStreaming(false);
  });

  function setStreaming(v) {
    streaming = v;
    sendBtn.style.display = v ? "none" : "";
    cancelBtn.style.display = v ? "" : "none";
  }

  // --- Render messages ---
  function appendUserMessage(text) {
    const el = document.createElement("div");
    el.className = "message user";
    el.innerHTML = `<div class="role">You</div><div class="content">${escapeHtml(text)}</div>`;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function getOrCreateAssistant() {
    if (!currentAssistantEl) {
      currentAssistantEl = document.createElement("div");
      currentAssistantEl.className = "message assistant";
      currentAssistantEl.innerHTML = `<div class="role">Deep Coder</div><div class="content"></div>`;
      messagesEl.appendChild(currentAssistantEl);
    }
    return currentAssistantEl.querySelector(".content");
  }

  function finishAssistant() {
    if (currentAssistantEl) {
      const content = currentAssistantEl.querySelector(".content");
      if (content) {
        content.innerHTML = renderMarkdown(content.textContent || "");
      }
    }
    currentAssistantEl = null;
    planningEl = null;
    taskProgressEl = null;
  }

  // --- Handle server messages ---
  window.addEventListener("message", (event) => {
    const msg = event.data;
    switch (msg.type) {
      case "connection":
        if (msg.status === "connected") {
          statusText.textContent = "Connected";
          statusText.className = "connected";
        } else {
          statusText.textContent = "Disconnected";
          statusText.className = "";
        }
        break;

      case "planning":
        showPlanning(msg.reasoning);
        break;

      case "token":
        appendToken(msg.content);
        break;

      case "task_progress":
        updateTaskProgress(msg.task_id, msg.status, msg.detail);
        break;

      case "approval":
        showApproval(msg.id, msg.tool, msg.arguments);
        break;

      case "diff":
        showDiff(msg.file, msg.old, msg.new);
        break;

      case "cost":
        costText.textContent = `$${msg.cost.toFixed(4)}`;
        break;

      case "done":
        if (msg.content) {
          const content = getOrCreateAssistant();
          if (!content.textContent) {
            content.textContent = msg.content;
          }
        }
        finishAssistant();
        setStreaming(false);
        scrollToBottom();
        break;

      case "error":
        appendError(msg.message);
        setStreaming(false);
        break;
    }
  });

  function showPlanning(reasoning) {
    if (!planningEl) {
      planningEl = document.createElement("div");
      planningEl.className = "planning";
      planningEl.innerHTML = `<div class="label">PLANNING (Pro)</div><div class="reasoning"></div>`;
      messagesEl.appendChild(planningEl);
    }
    const r = planningEl.querySelector(".reasoning");
    const text = r.textContent + reasoning;
    r.textContent = text.length > 300 ? "..." + text.slice(-300) : text;
    scrollToBottom();
  }

  function appendToken(token) {
    // Remove planning indicator when tokens start
    if (planningEl) {
      planningEl.remove();
      planningEl = null;
    }
    const content = getOrCreateAssistant();
    content.textContent += token;
    scrollToBottom();
  }

  function updateTaskProgress(taskId, status, detail) {
    if (!taskProgressEl) {
      taskProgressEl = document.createElement("div");
      taskProgressEl.className = "task-progress";
      messagesEl.appendChild(taskProgressEl);
    }

    let taskEl = taskProgressEl.querySelector(`[data-task="${taskId}"]`);
    if (!taskEl) {
      taskEl = document.createElement("div");
      taskEl.className = "task-item pending";
      taskEl.setAttribute("data-task", taskId);
      taskEl.innerHTML = `<span class="icon">○</span><span class="task-id">${taskId}</span><span class="detail">waiting</span>`;
      taskProgressEl.appendChild(taskEl);
    }

    const icons = { running: "⟳", completed: "✓", failed: "✗", pending: "○" };
    taskEl.className = `task-item ${status}`;
    taskEl.querySelector(".icon").textContent = icons[status] || "○";
    taskEl.querySelector(".detail").textContent = detail || status;
    scrollToBottom();
  }

  function showApproval(id, tool, args) {
    let argsDisplay = "";
    try {
      const parsed = JSON.parse(args);
      if (tool === "exec_shell") {
        argsDisplay = parsed.command || args;
      } else if (parsed.file_path) {
        argsDisplay = parsed.file_path;
      } else {
        argsDisplay = args.substring(0, 100);
      }
    } catch {
      argsDisplay = args.substring(0, 100);
    }

    const el = document.createElement("div");
    el.className = "approval";
    el.innerHTML = `
      <div class="tool-name">Approval: ${escapeHtml(tool)}</div>
      <div class="args">${escapeHtml(argsDisplay)}</div>
      <div class="actions">
        <button class="approve-btn" onclick="handleApproval('${id}', true, this)">Approve</button>
        <button class="deny-btn" onclick="handleApproval('${id}', false, this)">Deny</button>
      </div>
    `;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  // Global handler for approval buttons
  window.handleApproval = function (id, approved, btn) {
    vscode.postMessage({ type: "approval_response", id, approved });
    const actions = btn.closest(".actions");
    actions.innerHTML = approved
      ? '<span style="color:var(--vscode-terminal-ansiGreen)">Approved</span>'
      : '<span style="color:var(--vscode-terminal-ansiRed)">Denied</span>';
  };

  function showDiff(file, oldContent, newContent) {
    // Simple line-level diff display
    const el = document.createElement("div");
    el.className = "diff-block";

    let html = `<div class="diff-header">⏺ ${escapeHtml(file)}</div>`;
    if (oldContent && newContent) {
      const oldLines = oldContent.split("\n");
      const newLines = newContent.split("\n");
      // Show only changed lines (simplified)
      const maxLines = Math.max(oldLines.length, newLines.length);
      for (let i = 0; i < maxLines && i < 50; i++) {
        if (i < oldLines.length && oldLines[i] !== (newLines[i] || "")) {
          html += `<div class="diff-line removed">- ${escapeHtml(oldLines[i])}</div>`;
        }
        if (i < newLines.length && newLines[i] !== (oldLines[i] || "")) {
          html += `<div class="diff-line added">+ ${escapeHtml(newLines[i])}</div>`;
        }
      }
    }
    el.innerHTML = html;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  function appendError(message) {
    const el = document.createElement("div");
    el.className = "message assistant";
    el.innerHTML = `<div class="role" style="color:var(--vscode-terminal-ansiRed)">Error</div><div class="content">${escapeHtml(message)}</div>`;
    messagesEl.appendChild(el);
    scrollToBottom();
  }

  // --- Helpers ---
  function scrollToBottom() {
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  function renderMarkdown(text) {
    // Simple markdown: code blocks, inline code, bold, lists
    return text
      .replace(/```(\w*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>')
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
      .replace(/^- (.+)$/gm, "<li>$1</li>")
      .replace(/\n/g, "<br>");
  }
})();

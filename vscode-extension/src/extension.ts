import * as vscode from 'vscode';
import axios from 'axios';

// Server URL configuration
let serverUrl = 'http://localhost:8000';
let panel: vscode.WebviewPanel | undefined;
let statusBarItem: vscode.StatusBarItem;

// Agent state
interface AgentState {
    connected: boolean;
    currentFile: string | undefined;
    cursorPosition: vscode.Position | undefined;
    selection: vscode.Selection | undefined;
}

const state: AgentState = {
    connected: false,
    currentFile: undefined,
    cursorPosition: undefined,
    selection: undefined
};

export function activate(context: vscode.ExtensionContext) {
    console.log('Mini KI Tools extension activated');

    // Get configuration
    const config = vscode.workspace.getConfiguration('mini-ki-tools');
    serverUrl = config.get('serverUrl', 'http://localhost:8000');

    // Create status bar
    statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(circle-outline) Mini KI';
    statusBarItem.command = 'mini-ki-tools.chat';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Register commands
    const startCmd = vscode.commands.registerCommand('mini-ki-tools.start', async () => {
        await startAgent();
    });
    context.subscriptions.push(startCmd);

    const chatCmd = vscode.commands.registerCommand('mini-ki-tools.chat', async () => {
        await openChatPanel();
    });
    context.subscriptions.push(chatCmd);

    const applyCmd = vscode.commands.registerCommand('mini-ki-tools.applyChanges', async () => {
        await applyChanges();
    });
    context.subscriptions.push(applyCmd);

    const analyzeCmd = vscode.commands.registerCommand('mini-ki-tools.analyze', async () => {
        await analyzeCode();
    });
    context.subscriptions.push(analyzeCmd);

    const refactorCmd = vscode.commands.registerCommand('mini-ki-tools.refactor', async () => {
        await refactorCode();
    });
    context.subscriptions.push(refactorCmd);

    // Track active editor changes
    vscode.window.onDidChangeActiveTextEditor((editor) => {
        if (editor) {
            state.currentFile = editor.document.fileName;
            state.cursorPosition = editor.selection.active;
            state.selection = editor.selection;
            updateStatusBar();
        }
    });

    // Track cursor position changes
    vscode.window.onDidChangeTextEditorSelection((event) => {
        if (event.selections && event.selections.length > 0) {
            state.cursorPosition = event.selections[0].active;
            state.selection = event.selections[0];
        }
    });

    // Auto-start if configured
    if (config.get('autoStart', false)) {
        startAgent();
    }
}

async function startAgent(): Promise<void> {
    try {
        // Check if server is reachable
        const response = await axios.get(`${serverUrl}/health`, { timeout: 5000 });
        state.connected = true;
        vscode.window.showInformationMessage('Mini KI Tools connected to server');
        updateStatusBar();
    } catch (error) {
        state.connected = false;
        vscode.window.showWarningMessage('Mini KI Tools server not reachable. Start server first.');
        updateStatusBar();
    }
}

function updateStatusBar(): void {
    if (state.connected) {
        statusBarItem.text = '$(check) Mini KI';
        statusBarItem.command = 'mini-ki-tools.chat';
    } else {
        statusBarItem.text = '$(circle-outline) Mini KI';
        statusBarItem.command = 'mini-ki-tools.start';
    }
}

async function openChatPanel(): Promise<void> {
    // Create or show webview panel
    if (panel) {
        panel.reveal();
    } else {
        panel = vscode.window.createWebviewPanel(
            'mini-ki-tools-panel',
            'Mini KI Tools',
            vscode.ViewColumn.Two,
            {
                enableScripts: true,
                retainContextWhenHidden: true
            }
        );

        panel.onDidDispose(() => {
            panel = undefined;
        });

        // Update webview with current state
        updateWebview();
    }

    // Get current file content
    const editor = vscode.window.activeTextEditor;
    if (editor) {
        const content = editor.document.getText();
        const selection = editor.selection;
        
        // Send current context to webview
        panel.webview.postMessage({
            type: 'context',
            file: editor.document.fileName,
            content: content.substring(0, 5000), // Limit content size
            selection: selection.isEmpty ? undefined : content.substring(
                selection.start.character,
                selection.end.character
            )
        });
    }
}

function updateWebview(): void {
    if (!panel) return;

    panel.webview.html = getWebviewHtml();
}

function getWebviewHtml(): string {
    return `
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mini KI Tools</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; padding: 20px; }
        .header { display: flex; align-items: center; margin-bottom: 20px; }
        .status { padding: 5px 10px; border-radius: 4px; font-size: 12px; }
        .status.connected { background: #4caf50; color: white; }
        .status.disconnected { background: #f44336; color: white; }
        .chat-container { border: 1px solid #ddd; border-radius: 8px; height: 400px; display: flex; flex-direction: column; }
        .messages { flex: 1; overflow-y: auto; padding: 10px; }
        .message { margin: 10px 0; padding: 10px; border-radius: 8px; }
        .message.user { background: #e3f2fd; text-align: right; }
        .message.assistant { background: #f5f5f5; }
        .input-container { display: flex; padding: 10px; border-top: 1px solid #ddd; }
        input { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
        button { padding: 10px 20px; background: #2196f3; color: white; border: none; border-radius: 4px; cursor: pointer; margin-left: 10px; }
        button:hover { background: #1976d2; }
        .file-info { font-size: 12px; color: #666; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🤖 Mini KI Tools</h1>
        <span class="status ${state.connected ? 'connected' : 'disconnected'}" style="margin-left: 10px;">
            ${state.connected ? 'Connected' : 'Disconnected'}
        </span>
    </div>
    <div class="file-info">
        Current File: ${state.currentFile || 'None'}
    </div>
    <div class="chat-container">
        <div class="messages" id="messages"></div>
        <div class="input-container">
            <input type="text" id="input" placeholder="Ask me anything..." />
            <button onclick="sendMessage()">Send</button>
        </div>
    </div>
    <script>
        const vscode = acquireVsCodeApi();
        let messages = [];

        // Listen for messages from extension
        window.addEventListener('message', (event) => {
            const data = event.data;
            if (data.type === 'context') {
                addMessage('system', 'File loaded: ' + data.file);
            }
        });

        function addMessage(role, content) {
            messages.push({ role, content });
            const container = document.getElementById('messages');
            container.innerHTML += '<div class="message ' + role + '">' + content + '</div>';
            container.scrollTop = container.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('input');
            const message = input.value;
            if (!message) return;

            addMessage('user', message);
            input.value = '';

            try {
                const response = await fetch('${serverUrl}/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        messages: [{ content: message, role: 'user' }]
                    })
                });
                const data = await response.json();
                addMessage('assistant', data.response);
            } catch (error) {
                addMessage('assistant', 'Error: Server not reachable');
            }
        }

        // Handle Enter key
        document.getElementById('input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });
    </script>
</body>
</html>`;
}

async function applyChanges(): Promise<void> {
    // Get current document
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    // Show input dialog for changes
    const newCode = await vscode.window.showInputBox({
        prompt: 'Enter the new code to replace the selection',
        value: editor.document.getText(editor.selection)
    });

    if (newCode !== undefined) {
        await editor.edit(editBuilder => {
            editBuilder.replace(editor.selection, newCode);
        });
        vscode.window.showInformationMessage('Code changes applied');
    }
}

async function analyzeCode(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const content = editor.document.getText();
    const fileName = editor.document.fileName;

    try {
        const response = await axios.post(`${serverUrl}/chat`, {
            messages: [{
                content: `Analyze this code file: ${fileName}\n\n${content.substring(0, 3000)}`,
                role: 'user'
            }]
        });

        vscode.window.showInformationMessage('Analysis complete');
        
        // Show in output channel
        const output = vscode.window.createOutputChannel('Mini KI Analysis');
        output.appendLine(response.data.response);
        output.show();
    } catch (error) {
        vscode.window.showErrorMessage('Failed to analyze code');
    }
}

async function refactorCode(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    const selectedCode = editor.document.getText(selection);

    if (!selectedCode) {
        vscode.window.showWarningMessage('No code selected');
        return;
    }

    try {
        const response = await axios.post(`${serverUrl}/chat`, {
            messages: [{
                content: `Refactor this code:\n\n${selectedCode}`,
                role: 'user'
            }]
        });

        // Show diff editor
        const refactoredCode = response.data.response;
        
        // Create a new document with the refactored code
        const newDoc = await vscode.workspace.openTextDocument({
            content: refactoredCode,
            language: editor.document.languageId
        });
        
        await vscode.window.showTextDocument(newDoc, vscode.ViewColumn.Two);
        vscode.window.showInformationMessage('Refactored code opened in new tab');
    } catch (error) {
        vscode.window.showErrorMessage('Failed to refactor code');
    }
}

// Get current file info for external use
export function getCurrentFileInfo(): { fileName: string; content: string; cursorPosition: vscode.Position; selection: vscode.Selection | undefined } {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        return { fileName: '', content: '', cursorPosition: new vscode.Position(0, 0), selection: undefined };
    }

    return {
        fileName: editor.document.fileName,
        content: editor.document.getText(),
        cursorPosition: editor.selection.active,
        selection: editor.selection.isEmpty ? undefined : editor.selection
    };
}

export function deactivate() {
    if (panel) {
        panel.dispose();
    }
    if (statusBarItem) {
        statusBarItem.dispose();
    }
}
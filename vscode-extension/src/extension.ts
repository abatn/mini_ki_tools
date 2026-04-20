import * as vscode from 'vscode';
import axios from 'axios';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';

// Python subprocess
let pythonProcess: ChildProcess | undefined;
let pythonReady = false;

// Server URL configuration
let serverUrl = 'http://localhost:8000';
let panel: vscode.WebviewPanel | undefined;
let statusBarItem: vscode.StatusBarItem;
let setupStatusBarItem: vscode.StatusBarItem;

// Environment variables from VS Code Settings
let envLLMUrl = 'http://localhost:11434';
let envLLMModel = 'llama3.2';
let envWorkspacePath = '';

enum SetupState {
    Idle,
    Checking,
    CreatingVenv,
    Installing,
    Starting,
    Ready,
    Error
}

let currentSetupState = SetupState.Idle;

function updateSetupStatus(state: SetupState, message?: string): void {
    currentSetupState = state;
    if (!setupStatusBarItem) return;
    
    switch (state) {
        case SetupState.Checking:
            setupStatusBarItem.text = `$(sync~spin) Mini KI: Checking...`;
            setupStatusBarItem.color = '#58a6ff';
            break;
        case SetupState.CreatingVenv:
            setupStatusBarItem.text = `$(sync~spin) Mini KI: Creating venv...`;
            setupStatusBarItem.color = '#ffa657';
            break;
        case SetupState.Installing:
            setupStatusBarItem.text = `$(sync~spin) Mini KI: Installing deps...`;
            setupStatusBarItem.color = '#ffa657';
            break;
        case SetupState.Starting:
            setupStatusBarItem.text = `$(sync~spin) Mini KI: Starting...`;
            setupStatusBarItem.color = '#3fb950';
            break;
        case SetupState.Ready:
            setupStatusBarItem.text = `$(check) Mini KI`;
            setupStatusBarItem.color = '#3fb950';
            break;
        case SetupState.Error:
            setupStatusBarItem.text = `$(error) Mini KI: Setup failed`;
            setupStatusBarItem.color = '#f85149';
            setupStatusBarItem.command = 'mini-ki-tools.retrySetup';
            break;
        default:
            setupStatusBarItem.text = `$(circle-outline) Mini KI`;
            setupStatusBarItem.color = undefined;
    }
}

// Agent state
interface AgentState {
    connected: boolean;
    currentFile: string | undefined;
    cursorPosition: vscode.Position | undefined;
    selection: vscode.Selection | undefined;
    workspacePath: string | undefined;
    llmProvider: string | undefined;
    llmModel: string | undefined;
}

const state: AgentState = {
    connected: false,
    currentFile: undefined,
    cursorPosition: undefined,
    selection: undefined,
    workspacePath: undefined,
    llmProvider: undefined,
    llmModel: undefined
};

async function runAutoSetup(context: vscode.ExtensionContext): Promise<boolean> {
    const extensionPath = context.extensionPath;
    const venvPath = path.join(extensionPath, 'python', 'venv');
    const venvPython = path.join(venvPath, 'bin', 'python');
    const requirementsPath = path.join(extensionPath, 'python', 'requirements.txt');
    
    updateSetupStatus(SetupState.Checking);
    
    const venvExists = fs.existsSync(venvPath) && fs.existsSync(venvPython);
    
    if (!venvExists) {
        updateSetupStatus(SetupState.CreatingVenv);
        
        try {
            const pythonDir = path.join(extensionPath, 'python');
            if (!fs.existsSync(pythonDir)) {
                fs.mkdirSync(pythonDir, { recursive: true });
            }
            
            const createResult = await new Promise<{success: boolean, error?: string}>((resolve) => {
                const createProcess = spawn('python3', ['-m', 'venv', venvPath], {
                    stdio: ['pipe', 'pipe', 'pipe']
                });
                
                let stdout = '';
                let stderr = '';
                
                createProcess.stdout?.on('data', (data) => { stdout += data.toString(); });
                createProcess.stderr?.on('data', (data) => { stderr += data.toString(); });
                
                createProcess.on('close', (code) => {
                    if (code === 0) {
                        resolve({ success: true });
                    } else {
                        resolve({ success: false, error: stderr || `Exit code: ${code}` });
                    }
                });
                
                createProcess.on('error', (err) => {
                    resolve({ success: false, error: err.message });
                });
            });
            
            if (!createResult.success) {
                throw new Error(`Failed to create venv: ${createResult.error}`);
            }
            
            vscode.window.showInformationMessage('Virtual environment created');
            
        } catch (error: any) {
            updateSetupStatus(SetupState.Error);
            vscode.window.showErrorMessage(`Failed to create virtual environment: ${error.message}`);
            return false;
        }
    }
    
    if (!fs.existsSync(requirementsPath)) {
        updateSetupStatus(SetupState.Error);
        vscode.window.showErrorMessage('requirements.txt not found in python/ folder');
        return false;
    }
    
    updateSetupStatus(SetupState.Installing);
    
    try {
        const installResult = await new Promise<{success: boolean, error?: string}>((resolve) => {
            const pipProcess = spawn(venvPython, ['-m', 'pip', 'install', '-r', requirementsPath], {
                stdio: ['pipe', 'pipe', 'pipe']
            });
            
            let stdout = '';
            let stderr = '';
            
            pipProcess.stdout?.on('data', (data) => { stdout += data.toString(); });
            pipProcess.stderr?.on('data', (data) => { stderr += data.toString(); });
            
            pipProcess.on('close', (code) => {
                if (code === 0) {
                    resolve({ success: true });
                } else {
                    resolve({ success: false, error: stderr || `Exit code: ${code}` });
                }
            });
            
            pipProcess.on('error', (err) => {
                resolve({ success: false, error: err.message });
            });
        });
        
        if (!installResult.success) {
            throw new Error(`Failed to install dependencies: ${installResult.error}`);
        }
        
        vscode.window.showInformationMessage('Python dependencies installed');
        
    } catch (error: any) {
        updateSetupStatus(SetupState.Error);
        vscode.window.showErrorMessage(`Failed to install dependencies: ${error.message}`);
        return false;
    }
    
    updateSetupStatus(SetupState.Starting);
    return true;
}

function startPythonSubprocess(context: vscode.ExtensionContext, pythonPath: string): void {
    const extensionPythonPath = path.join(context.extensionPath, 'python', 'extension_host.py');
    
    if (!fs.existsSync(extensionPythonPath)) {
        console.error(`extension_host.py not found at ${extensionPythonPath}`);
        state.connected = false;
        updateSetupStatus(SetupState.Error);
        vscode.window.showErrorMessage('extension_host.py not found. Please ensure the extension is properly installed.');
        return;
    }
    
    const env = { ...process.env };
    env.LLM_URL = envLLMUrl;
    env.LLM_MODEL = envLLMModel;
    if (envWorkspacePath) {
        env.WORKSPACE_PATH = envWorkspacePath;
    }
    
    try {
        pythonProcess = spawn(pythonPath, [extensionPythonPath, '--workspace', envWorkspacePath], {
            env,
            stdio: ['pipe', 'pipe', 'pipe']
        });
        
        let buffer = '';
        
        pythonProcess.stdout?.on('data', (data: Buffer) => {
            buffer += data.toString();
            pythonReady = true;
            state.connected = true;
            updateStatusBar();
        });
        
        pythonProcess.stderr?.on('data', (data: Buffer) => {
            console.log(`Python stderr: ${data.toString()}`);
        });
        
        pythonProcess.on('error', (err) => {
            console.error(`Python process error: ${err.message}`);
            state.connected = false;
            updateSetupStatus(SetupState.Error);
            vscode.window.showErrorMessage(`Failed to start Python process: ${err.message}`);
            updateStatusBar();
        });
        
        pythonProcess.on('exit', (code) => {
            console.log(`Python process exited with code ${code}`);
            state.connected = false;
            pythonReady = false;
            updateStatusBar();
        });
        
        console.log('Python subprocess started');
        state.connected = true;
        updateSetupStatus(SetupState.Ready);
        updateStatusBar();
        
    } catch (error: any) {
        console.error(`Failed to start Python subprocess: ${error}`);
        state.connected = false;
        updateSetupStatus(SetupState.Error);
        vscode.window.showErrorMessage(`Failed to start Python subprocess: ${error.message}`);
    }
}

function sendToPython(message: object): Promise<any> {
    return new Promise((resolve, reject) => {
        if (!pythonProcess || !pythonReady) {
            reject(new Error('Python process not ready'));
            return;
        }
        
        const data = JSON.stringify(message) + '\n';
        pythonProcess.stdin?.write(data);
        
        // For now, simulate response until we have proper communication
        setTimeout(() => {
            resolve({ success: true, response: 'Message sent to Python process' });
        }, 100);
    });
}

interface PendingPermission {
    tool: string;
    description: string;
    resolve: (allowed: boolean) => void;
    timestamp: number;
}

let pendingPermissions: PendingPermission[] = [];

async function askUserPermission(toolName: string, description: string): Promise<boolean> {
    return new Promise((resolve) => {
        const pending: PendingPermission = {
            tool: toolName,
            description: description,
            resolve: resolve,
            timestamp: Date.now()
        };
        
        pendingPermissions.push(pending);
        
        vscode.window.showInformationMessage(
            `Mini KI: Erlaube '${toolName}'? ${description}`,
            { modal: false },
            'Erlauben',
            'Ablehnen'
        ).then((selection) => {
            const allowed = selection === 'Erlauben';
            pending.resolve(allowed);
            pendingPermissions = pendingPermissions.filter(p => p !== pending);
        });
        
        setTimeout(() => {
            if (pendingPermissions.includes(pending)) {
                pending.resolve(false);
                pendingPermissions = pendingPermissions.filter(p => p !== pending);
                vscode.window.showWarningMessage(`Permission request for '${toolName}' timed out`);
            }
        }, 60000);
    });
}

function loadWorkspaceRules(workspacePath: string): void {
    const rulesPath = path.join(workspacePath, 'rules.json');
    try {
        if (fs.existsSync(rulesPath)) {
            const rulesContent = fs.readFileSync(rulesPath, 'utf-8');
            const rules = JSON.parse(rulesContent);
            console.log('Loaded workspace rules from:', rulesPath);
            
            sendToPython({
                command: 'set_permissions',
                params: { rules: rules }
            });
        }
    } catch (error) {
        console.error('Failed to load rules.json:', error);
    }
}

export async function activate(context: vscode.ExtensionContext) {
    console.log('Mini KI Tools extension activated');

    // Create setup status bar
    setupStatusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Left,
        100
    );
    setupStatusBarItem.text = '$(circle-outline) Mini KI';
    setupStatusBarItem.show();
    context.subscriptions.push(setupStatusBarItem);

    // Create main status bar
    statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(circle-outline) Mini KI';
    statusBarItem.command = 'mini-ki-tools.chat';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    // Get configuration from VS Code Settings
    const config = vscode.workspace.getConfiguration('mini-ki-tools');
    
    // Read LLM settings - use config values or fall back to environment variables
    const pythonPathConfig = config.get('pythonPath', '');
    const llmUrlConfig = config.get('llmUrl', '');
    const llmModelConfig = config.get('llmModel', '');
    const workspaceConfig = config.get('workspacePath', '');
    
    // Resolve environment variables
    envLLMUrl = llmUrlConfig || process.env.LLM_URL || 'http://localhost:11434';
    envLLMModel = llmModelConfig || process.env.LLM_MODEL || 'llama3.2';
    envWorkspacePath = workspaceConfig || vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';
    
    console.log(`LLM URL: ${envLLMUrl}, Model: ${envLLMModel}`);
    
    // Load workspace rules.json if exists
    if (envWorkspacePath) {
        loadWorkspaceRules(envWorkspacePath);
    }
    
    // Run automatic setup (create venv, install deps)
    const setupSuccess = await runAutoSetup(context);
    
    if (!setupSuccess) {
        return;
    }
    
    // Determine Python path (use venv)
    const extensionPath = context.extensionPath;
    const venvPython = path.join(extensionPath, 'python', 'venv', 'bin', 'python');
    
    let pythonPath = pythonPathConfig || venvPython;
    
    console.log(`Python path: ${pythonPath}`);
    
    // Start Python subprocess
    startPythonSubprocess(context, pythonPath);

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

    const retrySetupCmd = vscode.commands.registerCommand('mini-ki-tools.retrySetup', async () => {
        await runAutoSetup(context);
        const venvPython = path.join(context.extensionPath, 'python', 'venv', 'bin', 'python');
        startPythonSubprocess(context, venvPython);
    });
    context.subscriptions.push(retrySetupCmd);

    const allowPermissionCmd = vscode.commands.registerCommand('mini-ki-tools.allowPermission', async (toolName: string) => {
        const pending = pendingPermissions.find(p => p.tool === toolName);
        if (pending) {
            pending.resolve(true);
            pendingPermissions = pendingPermissions.filter(p => p.tool !== toolName);
            vscode.window.showInformationMessage(`Permission granted for '${toolName}'`);
        }
    });
    context.subscriptions.push(allowPermissionCmd);

    const denyPermissionCmd = vscode.commands.registerCommand('mini-ki-tools.denyPermission', async (toolName: string) => {
        const pending = pendingPermissions.find(p => p.tool === toolName);
        if (pending) {
            pending.resolve(false);
            pendingPermissions = pendingPermissions.filter(p => p.tool !== toolName);
            vscode.window.showInformationMessage(`Permission denied for '${toolName}'`);
        }
    });
    context.subscriptions.push(denyPermissionCmd);

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
        
        // Get workspace and LLM info
        if (response.data.workspace) {
            state.workspacePath = response.data.workspace.workspace_path;
        }
        if (response.data.llm) {
            state.llmProvider = response.data.llm.provider;
            state.llmModel = response.data.llm.model;
        }
        
        vscode.window.showInformationMessage(`Mini KI Tools connected to server (Workspace: ${state.workspacePath}, LLM: ${state.llmProvider}/${state.llmModel})`);
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

        // Handle messages from webview
        panel.webview.onDidReceiveMessage(async (message) => {
            if (message.type === 'chat' && panel) {
                try {
                    const result = await sendToPython({
                        command: 'chat',
                        params: {
                            message: message.content,
                            workspace: envWorkspacePath,
                            llm_url: envLLMUrl,
                            llm_model: envLLMModel
                        }
                    });
                    
                    panel.webview.postMessage({
                        type: 'response',
                        response: result.response || result.error || 'Done'
                    });
                } catch (error) {
                    panel.webview.postMessage({
                        type: 'response',
                        response: `Error: ${error}`
                    });
                }
            }
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
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>أدوات الذكاء الاصطناعي المصغرة</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;500;600;700&display=swap');
        
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --bg-hover: #30363d;
            --bg-active: #1f6feb;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-bright: #f0f6fc;
            --accent-blue: #58a6ff;
            --accent-purple: #a371f7;
            --accent-orange: #ffa657;
            --accent-green: #3fb950;
            --accent-cyan: #39d3c5;
            --accent-pink: #f778ba;
            --status-connected: #3fb950;
            --status-disconnected: #f85149;
            --border-color: #30363d;
            --shadow-lg: 0 10px 40px rgba(0, 0, 0, 0.4);
            --gradient-primary: linear-gradient(135deg, #1f6feb 0%, #a371f7 100%);
            --gradient-glow: radial-gradient(circle at 50% 0%, rgba(31, 111, 235, 0.15) 0%, transparent 50%);
        }
        
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { height: 100%; font-family: 'Cairo', 'Segoe UI', sans-serif; background: var(--bg-primary); color: var(--text-primary); }
        
        .app-container { 
            display: flex; 
            flex-direction: column; 
            height: 100%; 
            background: var(--bg-primary);
            position: relative;
            overflow: hidden;
        }
        
        .app-container::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 200px;
            background: var(--gradient-glow);
            pointer-events: none;
        }
        
        .header { 
            display: flex; 
            align-items: center; 
            justify-content: space-between; 
            padding: 16px 24px; 
            background: var(--bg-secondary); 
            border-bottom: 1px solid var(--border-color);
            position: relative;
            z-index: 10;
        }
        
        .header h1 { 
            font-size: 18px; 
            font-weight: 600; 
            color: var(--text-bright); 
            display: flex; 
            align-items: center; 
            gap: 12px; 
            letter-spacing: 0.5px;
        }
        
        .header-logo {
            width: 36px;
            height: 36px;
            background: var(--gradient-primary);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            box-shadow: 0 4px 12px rgba(31, 111, 235, 0.3);
        }
        
        .app-container {
            display: flex;
            flex-direction: row;
        }
        
        .sidebar {
            width: 72px;
            min-width: 72px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 12px 8px;
            gap: 8px;
            z-index: 20;
        }
        
        .sidebar-icon {
            width: 56px;
            height: 56px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            color: var(--text-secondary);
            font-size: 11px;
            gap: 4px;
        }
        
        .sidebar-icon:hover {
            background: var(--bg-hover);
            color: var(--text-primary);
        }
        
        .sidebar-icon.active {
            background: var(--bg-active);
            color: var(--text-bright);
        }
        
        .sidebar-icon .icon {
            font-size: 22px;
        }
        
        .sidebar-icon .label {
            font-family: 'Cairo', sans-serif;
            font-weight: 500;
            font-size: 10px;
        }
        
        .sidebar-divider {
            height: 1px;
            background: var(--border-color);
            margin: 8px 0;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            min-width: 0;
        }
        
        .nav-tabs { 
            display: none;
        }
        
        .view-panel { 
            display: none; 
            flex: 1; 
            flex-direction: column; 
            overflow: hidden; 
            position: relative;
            z-index: 5;
        }
        
        .view-panel.active { 
            display: flex; 
        }
        
        .config-info { 
            font-size: 12px; 
            color: var(--text-secondary); 
            padding: 12px 24px; 
            background: rgba(22, 27, 34, 0.8); 
            border-bottom: 1px solid var(--border-color); 
            display: flex; 
            gap: 24px; 
            flex-wrap: wrap;
            backdrop-filter: blur(10px);
        }
        
        .config-info span {
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .config-info strong {
            color: var(--accent-cyan);
            font-weight: 500;
        }
        
        .messages { 
            flex: 1; 
            overflow-y: auto; 
            padding: 24px; 
            display: flex; 
            flex-direction: column; 
            gap: 16px; 
        }
        
        .message { 
            display: flex; 
            flex-direction: column; 
            max-width: 75%; 
            animation: fadeIn 0.3s ease; 
        }
        
        @keyframes fadeIn { 
            from { opacity: 0; transform: translateY(10px); } 
            to { opacity: 1; transform: translateY(0); } 
        }
        
        .message.user { 
            align-self: flex-end; 
        }
        
        .message.assistant { 
            align-self: flex-start; 
        }
        
        .message-header { 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            margin-bottom: 8px; 
            font-size: 12px; 
        }
        
        .avatar { 
            width: 32px; 
            height: 32px; 
            border-radius: 50%; 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            font-size: 13px; 
            font-weight: 600;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }
        
        .message.user .avatar { 
            background: var(--gradient-primary); 
            color: white; 
        }
        
        .message.assistant .avatar { 
            background: linear-gradient(135deg, #a371f7 0%, #f778ba 100%); 
            color: white; 
        }
        
        .name { 
            color: var(--text-secondary); 
            font-weight: 500;
        }
        
        .message-content { 
            padding: 16px 20px; 
            border-radius: 16px; 
            font-size: 14px; 
            line-height: 1.7;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }
        
        .message.user .message-content { 
            background: var(--bg-tertiary); 
            border: 1px solid var(--border-color); 
            border-top-left-radius: 4px;
        }
        
        .message.assistant .message-content { 
            background: var(--bg-secondary); 
            border: 1px solid var(--border-color); 
            border-top-right-radius: 4px;
        }
        
        .code-block { 
            background: var(--bg-tertiary); 
            border-radius: 12px; 
            overflow: hidden; 
            margin: 12px 0; 
            border: 1px solid var(--border-color);
        }
        
        .code-block-header { 
            display: flex; 
            padding: 8px 16px; 
            background: var(--bg-hover); 
            font-size: 12px; 
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border-color);
        }
        
        .code-block pre { 
            padding: 16px; 
            font-family: 'Cairo', 'Fira Code', monospace; 
            font-size: 13px; 
            overflow-x: auto; 
            white-space: pre; 
        }
        
        .code-block code { 
            color: var(--accent-orange); 
        }
        
        .input-container { 
            display: flex; 
            padding: 16px 24px; 
            background: var(--bg-secondary); 
            border-top: 1px solid var(--border-color); 
            gap: 12px;
            position: relative;
            z-index: 10;
        }
        
        input, textarea { 
            flex: 1; 
            padding: 14px 18px; 
            background: var(--bg-tertiary); 
            border: 1px solid var(--border-color); 
            border-radius: 12px; 
            color: var(--text-primary); 
            font-size: 14px; 
            outline: none;
            font-family: 'Cairo', sans-serif;
            transition: all 0.3s ease;
        }
        
        input:focus, textarea:focus { 
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1);
        }
        
        input::placeholder, textarea::placeholder { 
            color: var(--text-secondary); 
        }
        
        textarea { 
            resize: none; 
            min-height: 60px; 
            font-family: 'Cairo', sans-serif;
        }
        
        button { 
            padding: 14px 24px; 
            background: var(--gradient-primary); 
            color: white; 
            border: none; 
            border-radius: 12px; 
            cursor: pointer; 
            font-size: 14px; 
            font-weight: 600;
            font-family: 'Cairo', sans-serif;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 15px rgba(31, 111, 235, 0.3);
        }
        
        button:hover { 
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(31, 111, 235, 0.4);
        }
        
        button.secondary { 
            background: var(--bg-hover); 
            color: var(--text-primary);
            box-shadow: none;
        }
        
        button.secondary:hover {
            background: var(--bg-tertiary);
        }
        
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .action-grid { 
            display: grid; 
            grid-template-columns: repeat(2, 1fr); 
            gap: 12px; 
            padding: 24px; 
        }
        
        .action-card { 
            padding: 20px; 
            background: var(--bg-secondary); 
            border: 1px solid var(--border-color); 
            border-radius: 16px; 
            cursor: pointer; 
            text-align: center; 
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .action-card:hover { 
            border-color: var(--accent-blue);
            transform: translateY(-4px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.2);
        }
        
        .action-card h3 { 
            font-size: 15px; 
            color: var(--accent-blue); 
            margin-bottom: 8px; 
            font-weight: 600;
        }
        
        .action-card p { 
            font-size: 12px; 
            color: var(--text-secondary); 
        }
        
        .analysis-view { 
            flex: 1; 
            overflow-y: auto; 
            padding: 24px; 
        }
        
        .analysis-section { 
            margin-bottom: 16px; 
            padding: 20px; 
            background: var(--bg-secondary); 
            border: 1px solid var(--border-color); 
            border-radius: 16px;
            transition: all 0.3s ease;
        }
        
        .analysis-section:hover {
            border-color: var(--accent-purple);
        }
        
        .analysis-section h3 { 
            font-size: 14px; 
            color: var(--accent-yellow); 
            margin-bottom: 12px; 
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .analysis-section p { 
            font-size: 13px; 
            line-height: 1.8; 
        }
        
        .refactor-view { 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            padding: 24px; 
            gap: 16px; 
        }
        
        .refactor-original, .refactor-result { 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            min-height: 150px; 
        }
        
        .refactor-original label, .refactor-result label { 
            font-size: 13px; 
            color: var(--text-secondary); 
            margin-bottom: 10px; 
            font-weight: 500;
        }
        
        .refactor-original textarea { 
            flex: 1; 
            font-family: 'Cairo', 'Fira Code', monospace; 
            font-size: 13px; 
        }
        
        .completion-view { 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            padding: 24px; 
            gap: 16px; 
        }
        
        .completion-context { 
            padding: 20px; 
            background: var(--bg-secondary); 
            border: 1px solid var(--border-color); 
            border-radius: 16px; 
        }
        
        .completion-context h3 { 
            font-size: 14px; 
            color: var(--accent-green); 
            margin-bottom: 12px;
            font-weight: 600;
        }
        
        .completion-suggestions { 
            display: flex; 
            flex-direction: column; 
            gap: 10px; 
        }
        
        .completion-item { 
            padding: 16px; 
            background: var(--bg-tertiary); 
            border: 1px solid var(--border-color); 
            border-radius: 12px; 
            cursor: pointer; 
            font-family: 'Cairo', monospace; 
            font-size: 13px;
            transition: all 0.3s ease;
        }
        
        .completion-item:hover { 
            border-color: var(--accent-blue);
            transform: translateX(-4px);
        }
        
        .agent-view { 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            padding: 24px; 
            gap: 20px; 
            overflow-y: auto; 
        }
        
        .agent-status-card { 
            padding: 32px; 
            background: var(--bg-secondary); 
            border: 1px solid var(--border-color); 
            border-radius: 20px; 
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .agent-status-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-primary);
        }
        
        .agent-status-card h3 { 
            font-size: 16px; 
            color: var(--text-primary); 
            margin-bottom: 20px; 
            font-weight: 600;
        }
        
        .agent-status-indicator { 
            display: flex; 
            align-items: center; 
            justify-content: center; 
            gap: 12px; 
            font-size: 18px; 
            font-weight: 600;
        }
        
        .agent-status-indicator .status-dot { 
            width: 14px; 
            height: 14px; 
            box-shadow: 0 0 15px currentColor;
        }
        
        .agent-actions { 
            display: flex; 
            gap: 16px; 
            justify-content: center; 
        }
        
        .agent-actions button { 
            flex: 1; 
            max-width: 220px;
        }
        
        .agent-info { 
            display: flex; 
            flex-direction: column; 
            gap: 12px; 
            padding: 20px; 
            background: var(--bg-secondary); 
            border: 1px solid var(--border-color); 
            border-radius: 16px; 
        }
        
        .agent-info-item { 
            display: flex; 
            justify-content: space-between; 
            font-size: 13px;
            padding: 8px 0;
            border-bottom: 1px solid var(--border-color);
        }
        
        .agent-info-item:last-child {
            border-bottom: none;
        }
        
        .agent-info-item label { 
            color: var(--text-secondary); 
            font-weight: 500;
        }
        
        .agent-info-item span { 
            color: var(--text-primary); 
            font-family: 'Cairo', monospace; 
        }
        
        .agent-logs { 
            flex: 1; 
            min-height: 180px; 
            background: var(--bg-tertiary); 
            border: 1px solid var(--border-color); 
            border-radius: 16px; 
            overflow-y: auto; 
            padding: 8px 0;
        }
        
        .settings-view { 
            flex: 1; 
            overflow-y: auto; 
            padding: 24px; 
            display: flex; 
            flex-direction: column; 
            gap: 20px; 
        }
        
        .settings-section { 
            background: var(--bg-secondary); 
            border: 1px solid var(--border-color); 
            border-radius: 16px; 
            padding: 20px; 
        }
        
        .settings-section h3 { 
            font-size: 15px; 
            color: var(--accent-blue); 
            margin-bottom: 16px; 
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .settings-group { 
            margin-bottom: 16px; 
        }
        
        .settings-group:last-child { 
            margin-bottom: 0; 
        }
        
        .settings-group label { 
            display: block; 
            font-size: 13px; 
            color: var(--text-secondary); 
            margin-bottom: 8px; 
            font-weight: 500;
        }
        
        .settings-group input[type="text"],
        .settings-group input[type="number"],
        .settings-group select { 
            width: 100%; 
            padding: 12px 16px; 
            background: var(--bg-tertiary); 
            border: 1px solid var(--border-color); 
            border-radius: 10px; 
            color: var(--text-primary); 
            font-size: 14px;
            font-family: 'Cairo', sans-serif;
            outline: none;
            transition: all 0.3s ease;
        }
        
        .settings-group input:focus,
        .settings-group select:focus { 
            border-color: var(--accent-blue);
            box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.1);
        }
        
        .settings-group input[type="range"] { 
            width: 100%;
            accent-color: var(--accent-blue);
        }
        
        .checkbox-label {
            display: flex !important;
            align-items: center;
            gap: 10px;
            cursor: pointer;
        }
        
        .checkbox-label input[type="checkbox"] {
            width: 18px;
            height: 18px;
            accent-color: var(--accent-blue);
        }
        
        .settings-mode-info {
            margin-top: 8px;
            font-size: 11px;
            color: var(--text-secondary);
            padding: 8px;
            background: var(--bg-tertiary);
            border-radius: 8px;
        }
        
        .settings-mode-info div {
            display: none;
        }
        
        .settings-mode-info div:first-child {
            display: block;
        }
        
        .provider-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            margin-bottom: 12px;
        }
        
        .provider-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            background: var(--bg-tertiary);
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }
        
        .provider-item .provider-name {
            flex: 1;
            font-weight: 500;
        }
        
        .provider-item .provider-status {
            font-size: 11px;
            padding: 4px 8px;
            border-radius: 12px;
            background: var(--bg-hover);
            color: var(--text-secondary);
        }
        
        .provider-item .provider-status.connected {
            background: rgba(63, 185, 80, 0.2);
            color: var(--accent-green);
        }
        
        .provider-item .provider-status.checking {
            background: rgba(88, 166, 255, 0.2);
            color: var(--accent-blue);
        }
        
        .provider-item input {
            width: 180px;
            padding: 6px 10px;
            background: var(--bg-primary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            color: var(--text-primary);
            font-size: 12px;
        }
        
        .btn-check-providers {
            width: 100%;
            padding: 10px;
            background: var(--bg-hover);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            color: var(--text-primary);
            cursor: pointer;
            margin-bottom: 12px;
            font-family: 'Cairo', sans-serif;
        }
        
        .btn-check-providers:hover {
            background: var(--bg-tertiary);
        }
        
        .provider-results {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }
        
        .provider-result {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 12px;
            background: var(--bg-tertiary);
            border-radius: 6px;
            font-size: 12px;
        }
        
        .provider-result.fastest {
            background: rgba(63, 185, 80, 0.15);
            border: 1px solid var(--accent-green);
        }
        
        .provider-result .latency {
            margin-left: auto;
            color: var(--accent-green);
        }
        
        .shortcuts-list {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        
        .shortcut-item {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            color: var(--text-secondary);
        }
        
        .shortcut-item kbd {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 4px 8px;
            font-family: 'Cairo', monospace;
            font-size: 12px;
            color: var(--accent-cyan);
        }
        
        .shortcut-item span {
            color: var(--text-primary);
        }
        
        .status-bar { 
            display: flex; 
            align-items: center; 
            gap: 24px; 
            padding: 10px 24px; 
            background: var(--bg-tertiary); 
            border-top: 1px solid var(--border-color); 
            font-size: 12px;
            position: relative;
            z-index: 10;
        }
        
        .status-bar-item { 
            display: flex; 
            align-items: center; 
            gap: 6px; 
        }
        
        .status-dot { 
            width: 8px; 
            height: 8px; 
            border-radius: 50%; 
            background: currentColor; 
        }
        
        .loading { 
            display: flex; 
            align-items: center; 
            gap: 10px; 
            color: var(--text-secondary); 
            font-size: 13px; 
        }
        
        .loading-spinner { 
            width: 18px; 
            height: 18px; 
            border: 2px solid var(--border-color); 
            border-top-color: var(--accent-blue); 
            border-radius: 50%; 
            animation: spin 0.8s linear infinite; 
        }
        
        @keyframes spin { to { transform: rotate(360deg); } }
        
        .refactor-templates {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        
        .refactor-template {
            padding: 8px 14px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            color: var(--text-secondary);
        }
        
        .refactor-template:hover {
            background: var(--bg-hover);
            border-color: var(--accent-blue);
            color: var(--text-primary);
        }
        
        .quick-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }
        
        .quick-action {
            padding: 8px 14px;
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s ease;
            color: var(--accent-cyan);
        }
        
        .quick-action:hover {
            background: var(--bg-hover);
            border-color: var(--accent-cyan);
        }
        
        ::-webkit-scrollbar { 
            width: 8px; 
            height: 8px; 
        }
        
        ::-webkit-scrollbar-thumb { 
            background: var(--bg-hover); 
            border-radius: 4px; 
        }
        
        ::-webkit-scrollbar-thumb:hover { 
            background: var(--text-secondary); 
        }
        
        .empty-state {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            color: var(--text-secondary);
            font-size: 15px;
            padding: 40px;
            text-align: center;
            gap: 12px;
        }
        
        .empty-state-icon {
            font-size: 48px;
            opacity: 0.5;
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar -->
        <nav class="sidebar">
            <div class="sidebar-icon active" data-view="chat" title="محادثة">
                <span class="icon">💬</span>
                <span class="label">Chat</span>
            </div>
            <div class="sidebar-icon" data-view="analyze" title="تحليل">
                <span class="icon">🔍</span>
                <span class="label">Analyze</span>
            </div>
            <div class="sidebar-icon" data-view="refactor" title="إعادة هيكلة">
                <span class="icon">🔧</span>
                <span class="label">Refactor</span>
            </div>
            <div class="sidebar-icon" data-view="completion" title="إكمال">
                <span class="icon">✨</span>
                <span class="label">Complete</span>
            </div>
            <div class="sidebar-divider"></div>
            <div class="sidebar-icon" data-view="agent" title="الوكيل">
                <span class="icon">⚡</span>
                <span class="label">Agent</span>
            </div>
            <div class="sidebar-icon" data-view="settings" title="الإعدادات">
                <span class="icon">⚙️</span>
                <span class="label">Settings</span>
            </div>
        </nav>
        
        <div class="main-content">
            <header class="header">
                <h1>
                    <div class="header-logo">🤖</div>
                    أدوات الذكاء الاصطناعي المصغرة
                </h1>
            </header>
            
            <div class="config-info">
                <span><strong>المساحة:</strong> ${state.workspacePath || 'غير مكون'}</span>
                <span><strong>LLM:</strong> ${state.llmModel || 'N/A'}</span>
                <span><strong>ملف:</strong> ${state.currentFile || 'لا يوجد'}</span>
            </div>
        
        <!-- Chat View -->
        <div class="view-panel active" id="view-chat">
            <div class="quick-actions">
                <div class="quick-action" onclick="addQuickAction('Explain this code')">📖 erklären</div>
                <div class="quick-action" onclick="addQuickAction('Find bugs in this code')">🐛 Bugs finden</div>
                <div class="quick-action" onclick="addQuickAction('Optimize this code')">⚡ تحسين</div>
                <div class="quick-action" onclick="addQuickAction('Add comments to this code')">💬 تعليق</div>
            </div>
            <div class="messages" id="messages"></div>
            <div class="input-container">
                <textarea id="input" placeholder="اكتب رسالتك... (Enter للإرسال, Shift+Enter لسطر جديد)"></textarea>
                <button onclick="sendMessage()">إرسال</button>
            </div>
        </div>
        
        <!-- Analyze View -->
        <div class="view-panel" id="view-analyze">
            <div class="analysis-view" id="analysis-results">
                <div style="padding: 16px; color: var(--text-secondary); text-align: center;">
                    انقر على "تشغيل التحليل" لتحليل الملف الحالي
                </div>
            </div>
            <div class="input-container">
                <button onclick="runAnalysis()">تشغيل التحليل</button>
            </div>
        </div>
        
        <!-- Refactor View -->
        <div class="view-panel" id="view-refactor">
            <div class="refactor-view">
                <div class="refactor-templates">
                    <div class="refactor-template" onclick="setRefactorTemplate('extract')">📤 استخراج دالة</div>
                    <div class="refactor-template" onclick="setRefactorTemplate('rename')">✏️ إعادة تسمية</div>
                    <div class="refactor-template" onclick="setRefactorTemplate('inline')">📥 دمج في place</div>
                    <div class="refactor-template" onclick="setRefactorTemplate('optimize')">⚡ تحسين الأداء</div>
                    <div class="refactor-template" onclick="setRefactorTemplate('clean')">🧹 تنظيف الكود</div>
                </div>
                <div class="refactor-original">
                    <label>الكود الأصلي (المحدد):</label>
                    <textarea id="refactor-input" placeholder="حدد الكود في المحرر لإعادة هيكلته..."></textarea>
                </div>
                <div class="refactor-result">
                    <label>التعليمات:</label>
                    <textarea id="refactor-instructions" placeholder="صف كيف تريد إعادة هيكلة الكود..."></textarea>
                </div>
                <button onclick="runRefactor()">إعادة هيكلة الكود</button>
            </div>
        </div>
        
        <!-- Completion View -->
        <div class="view-panel" id="view-completion">
            <div class="completion-view">
                <div class="completion-context">
                    <h3>السياق الحالي</h3>
                    <p id="completion-cursor">موقع المؤشر: ${state.cursorPosition?.line || 0}:${state.cursorPosition?.character || 0}</p>
                </div>
                <button onclick="getCompletions()">الحصول على الإكمالات</button>
                <div class="completion-suggestions" id="completion-results"></div>
            </div>
        </div>
        
        <!-- Agent View -->
        <div class="view-panel" id="view-agent">
            <div class="agent-view">
                <div class="agent-status-card">
                    <h3>حالة الوكيل</h3>
                    <div class="agent-status-indicator">
                        <span class="status-dot" id="agent-status-dot" style="background: ${state.connected ? 'var(--status-connected)' : 'var(--status-disconnected)'}"></span>
                        <span id="agent-status-text">${state.connected ? 'قيد التشغيل' : 'متوقف'}</span>
                    </div>
                </div>
                <div class="agent-actions">
                    <button onclick="startAgent()" id="agent-start-btn" ${state.connected ? 'disabled' : ''}>تشغيل الوكيل</button>
                    <button onclick="stopAgent()" id="agent-stop-btn" class="secondary" ${!state.connected ? 'disabled' : ''}>إيقاف الوكيل</button>
                </div>
                <div class="agent-info">
                    <div class="agent-info-item">
                        <label>مساحة العمل:</label>
                        <span>${state.workspacePath || 'غير مكون'}</span>
                    </div>
                    <div class="agent-info-item">
                        <label>نموذج الذكاء:</label>
                        <span>${state.llmProvider || 'N/A'}/${state.llmModel || 'N/A'}</span>
                    </div>
                    <div class="agent-info-item">
                        <label>الملف الحالي:</label>
                        <span>${state.currentFile || 'لا يوجد'}</span>
                    </div>
                </div>
                <div class="agent-logs" id="agent-logs">
                    <div style="color: var(--text-secondary); padding: 16px; text-align: center;">
                        ستظهر سجلات الوكيل هنا
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Settings View -->
        <div class="view-panel" id="view-settings">
            <div class="settings-view">
                <div class="settings-section">
                    <h3>🔑 API Provider</h3>
                    <div class="provider-list" id="provider-list">
                        <div class="provider-item" data-provider="ollama">
                            <div class="provider-name">Ollama</div>
                            <div class="provider-status connected">Verbunden</div>
                            <input type="text" class="provider-key" placeholder="URL (falls abweichend)" />
                        </div>
                        <div class="provider-item" data-provider="openai">
                            <div class="provider-name">OpenAI</div>
                            <div class="provider-status">Nicht konfiguriert</div>
                            <input type="password" class="provider-key" placeholder="sk-..." />
                        </div>
                        <div class="provider-item" data-provider="anthropic">
                            <div class="provider-name">Anthropic</div>
                            <div class="provider-status">Nicht konfiguriert</div>
                            <input type="password" class="provider-key" placeholder="sk-ant-..." />
                        </div>
                        <div class="provider-item" data-provider="groq">
                            <div class="provider-name">Groq</div>
                            <div class="provider-status">Nicht konfiguriert</div>
                            <input type="password" class="provider-key" placeholder="gsk_..." />
                        </div>
                        <div class="provider-item" data-provider="huggingface">
                            <div class="provider-name">Hugging Face</div>
                            <div class="provider-status">Nicht konfiguriert</div>
                            <input type="password" class="provider-key" placeholder="hf_..." />
                        </div>
                        <div class="provider-item" data-provider="mistral">
                            <div class="provider-name">Mistral AI</div>
                            <div class="provider-status">Nicht konfiguriert</div>
                            <input type="password" class="provider-key" placeholder="API Key" />
                        </div>
                        <div class="provider-item" data-provider="google">
                            <div class="provider-name">Google AI</div>
                            <div class="provider-status">Nicht konfiguriert</div>
                            <input type="password" class="provider-key" placeholder="API Key" />
                        </div>
                    </div>
                    <button class="btn-check-providers" onclick="checkProviders()">🔄 Provider prüfen</button>
                    <div class="provider-results" id="provider-results">
                        <div class="provider-result fastest">
                            <span class="icon">⚡</span>
                            <span class="name">Schnellster: Ollama</span>
                            <span class="latency">45ms</span>
                        </div>
                    </div>
                </div>
                <div class="settings-section">
                    <h3>إعدادات الذكاء الاصطناعي</h3>
                    <div class="settings-group">
                        <label>LLM Provider:</label>
                        <select id="settings-llm-provider">
                            <option value="auto">Auto (Schnellster)</option>
                            <option value="ollama">Ollama</option>
                            <option value="openai">OpenAI</option>
                            <option value="anthropic">Anthropic</option>
                            <option value="groq">Groq</option>
                        </select>
                    </div>
                    <div class="settings-group">
                        <label>النموذج:</label>
                        <select id="settings-llm-model">
                            <option value="llama3.2" ${envLLMModel === 'llama3.2' ? 'selected' : ''}>Llama 3.2</option>
                            <option value="gpt-4o">GPT-4o</option>
                            <option value="claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                        </select>
                    </div>
                </div>
                <div class="settings-section">
                    <h3>وضع التفكير</h3>
                    <div class="settings-group">
                        <label>Reasoning-Modus:</label>
                        <select id="settings-reasoning-mode">
                            <option value="tao">TAO - Thought-Action-Observation</option>
                            <option value="tot">ToT - Tree of Thoughts</option>
                            <option value="got">GoT - Graph of Thoughts</option>
                            <option value="reflexion">Reflexion - With Error Memory</option>
                            <option value="plan_solve">Plan-Solve - Plan then Execute</option>
                            <option value="pot">PoT - Code as Thought</option>
                            <option value="voyager">Voyager - Experience-based</option>
                        </select>
                    </div>
                    <div class="settings-mode-info">
                        <div data-mode="tao">Klassischer TAO-Loop mit Beobachten und Handeln</div>
                        <div data-mode="tot">Verzweigte Pfade, Backtracking, beste Lösung wählen</div>
                        <div data-mode="got">Vernetzte Gedanken, Zusammenführungen, Zyklen</div>
                        <div data-mode="reflexion">Lernt aus Fehlern, speichert Error-Memory</div>
                        <div data-mode="plan_solve">Erstellt erst Plan, dann ausführen</div>
                        <div data-mode="pot">Schreibt Code als Thought, führt ihn aus</div>
                        <div data-mode="voyager">Erfahrungsbasiert, ähnliche Fälle abrufen</div>
                    </div>
                </div>
                <div class="settings-section">
                    <h3>إعدادات الوكيل</h3>
                    <div class="settings-group">
                        <label>الحد الأقصى للتوكنات:</label>
                        <input type="number" id="settings-max-tokens" value="4096" min="512" max="8192" />
                    </div>
                    <div class="settings-group">
                        <label>درجة الحرارة:</label>
                        <input type="range" id="settings-temperature" min="0" max="1" step="0.1" value="0.7" />
                        <span id="temp-value">0.7</span>
                    </div>
                    <div class="settings-group">
                        <label class="checkbox-label">
                            <input type="checkbox" id="settings-auto-complete" /> الإكمال التلقائي للكود
                        </label>
                    </div>
                </div>
                <div class="settings-section">
                    <h3>مفاتيح الاختصار</h3>
                    <div class="shortcuts-list">
                        <div class="shortcut-item"><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>C</kbd> <span>فتح المحادثة</span></div>
                        <div class="shortcut-item"><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>A</kbd> <span>تحليل الكود</span></div>
                        <div class="shortcut-item"><kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>R</kbd> <span>إعادة الهيكلة</span></div>
                    </div>
                </div>
                <button onclick="saveSettings()">حفظ الإعدادات</button>
            </div>
        </div>
        
        <footer class="status-bar">
            <div class="status-bar-item">
                <span class="status-dot" style="background: ${state.connected ? 'var(--status-connected)' : 'var(--status-disconnected)'}"></span>
                ${state.connected ? 'Connected' : 'Disconnected'}
            </div>
            <div class="status-bar-item" style="margin-left: auto;">${state.workspacePath || 'No workspace'}</div>
        </footer>
    </div>
    <script>
        const vscode = acquireVsCodeApi();
        let messages = [];
        let currentView = 'chat';

        // Sidebar icon navigation
        document.querySelectorAll('.sidebar-icon').forEach(icon => {
            icon.addEventListener('click', () => {
                document.querySelectorAll('.sidebar-icon').forEach(i => i.classList.remove('active'));
                document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
                icon.classList.add('active');
                document.getElementById('view-' + icon.dataset.view).classList.add('active');
                currentView = icon.dataset.view;
            });
        });

        window.addEventListener('message', (event) => {
            const data = event.data;
            if (data.type === 'context') {
                addMessage('system', 'File loaded: ' + data.file);
                document.getElementById('refactor-input').value = data.selection || '';
            } else if (data.type === 'response') {
                const msgs = document.getElementById('messages');
                const last = msgs.lastElementChild;
                if (last && last.textContent.includes('Processing...')) {
                    last.remove();
                }
                if (currentView === 'chat') {
                    addMessage('assistant', data.response);
                }
            } else if (data.type === 'analysis') {
                displayAnalysis(data.result);
            } else if (data.type === 'refactor') {
                displayRefactorResult(data.result);
            } else if (data.type === 'completions') {
                displayCompletions(data.suggestions);
            } else if (data.type === 'agent-status') {
                updateAgentStatus(data.connected);
            } else if (data.type === 'agent-log') {
                addAgentLog(data.message);
            }
        });

        const refactorTemplates = {
            'extract': 'استخراج هذا الكود إلى دالة منفصلة مع اسم واضح',
            'rename': 'إعادة تسمية المتغيرات والدوال بأسماء وصفية',
            'inline': 'دمج المتغير المباشر في место использования',
            'optimize': 'تحسين الأداء وإزالة الكود المكر',
            'clean': 'تنظيف الكود وإزالة الأسطر غير المستخدمة'
        };

        function setRefactorTemplate(template) {
            const instructions = document.getElementById('refactor-instructions');
            instructions.value = refactorTemplates[template] || '';
            const code = document.getElementById('refactor-input');
            if (!code.value && state.currentFile) {
                addMessage('system', 'يرجى تحديد الكود المراد إعادة هيكلته');
            }
        }

        function addQuickAction(action) {
            const input = document.getElementById('input');
            input.value = action;
            sendMessage();
        }

        function addMessage(role, content) {
            messages.push({ role, content });
            const container = document.getElementById('messages');
            const isUser = role === 'user';
            const avatar = isUser ? 'أ' : 'ذ';
            const name = isUser ? 'أنت' : 'الذكاء الاصطناعي';
            const html = '<div class="message ' + role + '">' +
                '<div class="message-header">' +
                '<div class="avatar">' + avatar + '</div>' +
                '<span class="name">' + name + '</span>' +
                '</div>' +
                '<div class="message-content">' + content.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>' +
                '</div>';
            container.innerHTML += html;
            container.scrollTop = container.scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('input');
            const message = input.value;
            if (!message) return;
            addMessage('user', message);
            input.value = '';
            vscode.postMessage({ type: 'command', command: 'chat', content: message });
            addMessage('assistant', '<div class="loading"><div class="loading-spinner"></div>جاري التفكير...</div>');
        }
        
        async function saveProviderKey(providerId) {
            const selector = '[data-provider="' + providerId + '"] .provider-key';
            const input = document.querySelector(selector);
            if (!input || !input.value) return;
            
            try {
                const url = 'http://localhost:8000/providers/' + providerId;
                const response = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ api_key: input.value })
                });
                if (response.ok) {
                    const statusSelector = '[data-provider="' + providerId + '"] .provider-status';
                    const statusEl = document.querySelector(statusSelector);
                    if (statusEl) {
                        statusEl.textContent = '✓ Gespeichert';
                        statusEl.classList.add('connected');
                    }
                }
            } catch (e) {
                console.error('Failed to save key:', e);
            }
        }
        
        function saveSettings() {
            const llmUrl = document.getElementById('settings-llm-url')?.value;
            const llmModel = document.getElementById('settings-llm-model')?.value;
            const reasoningMode = document.getElementById('settings-reasoning-mode')?.value;
            
            // Save all provider keys
            const items = document.querySelectorAll('.provider-item');
            items.forEach(function(item) {
                const providerId = item.dataset.provider;
                const input = item.querySelector('.provider-key');
                if (input && input.value) {
                    saveProviderKey(providerId);
                }
            });
            
            // Save settings to VS Code
            vscode.postMessage({
                type: 'command',
                command: 'saveSettings',
                settings: { llmUrl, llmModel, reasoningMode }
            });
            
            vscode.window.showInformationMessage('Einstellungen gespeichert');
        }
        
        async function checkProviders() {
            const btn = document.querySelector('.btn-check-providers');
            if (btn) btn.textContent = '🔄 Prüfe...';
            
            try {
                await fetch('http://localhost:8000/providers/check', { method: 'POST' });
                const response = await fetch('http://localhost:8000/providers');
                const providers = await response.json();
                
                // Update UI - use for...of instead
                for (var id in providers) {
                    var data = providers[id];
                    var itemSelector = '[data-provider="' + id + '"]';
                    var item = document.querySelector(itemSelector);
                    if (item) {
                        var statusEl = item.querySelector('.provider-status');
                        if (statusEl) {
                            if (data.hasApiKey && data.status === 'available') {
                                statusEl.textContent = '✓ ' + data.latencyMs + 'ms';
                                statusEl.classList.add('connected');
                            } else if (data.hasApiKey) {
                                statusEl.textContent = '✗ Nicht verfügbar';
                            }
                        }
                    }
                }
            } catch (e) {
                console.error('Check failed:', e);
            }
            
            if (btn) btn.textContent = '🔄 Provider prüfen';
        }

        async function runAnalysis() {
            vscode.postMessage({ type: 'command', command: 'analyze' });
            document.getElementById('analysis-results').innerHTML = '<div class="loading"><div class="loading-spinner"></div>جاري التحليل...</div>';
        }

        function displayAnalysis(result) {
            document.getElementById('analysis-results').innerHTML = 
                '<div class="analysis-section"><h3>ملخص</h3><p>' + (result.summary || 'لا يوجد ملخص') + '</p></div>' +
                '<div class="analysis-section"><h3>المشاكل</h3><p>' + (result.issues || 'لم يتم العثور على مشاكل') + '</p></div>' +
                '<div class="analysis-section"><h3>الاقتراحات</h3><p>' + (result.suggestions || 'لا توجد اقتراحات') + '</p></div>';
        }

        async function runRefactor() {
            const code = document.getElementById('refactor-input').value;
            const instructions = document.getElementById('refactor-instructions').value;
            if (!code) { alert('حدد الكود المراد إعادة هيكلته أولاً'); return; }
            vscode.postMessage({ type: 'command', command: 'refactor', code: code, instructions: instructions });
        }

        function displayRefactorResult(result) {
            document.getElementById('analysis-results').innerHTML = 
                '<div class="analysis-section"><h3>الكود المعاد هيكلته</h3><pre><code>' + result.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</code></pre></div>';
        }

        async function getCompletions() {
            vscode.postMessage({ type: 'command', command: 'completion' });
        }

        function displayCompletions(suggestions) {
            const container = document.getElementById('completion-results');
            container.innerHTML = suggestions.map((s, i) => 
                '<div class="completion-item" onclick="applyCompletion(' + i + ')">' + s.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</div>'
            ).join('');
        }

        async function applyCompletion(index) {
            vscode.postMessage({ type: 'command', command: 'apply-completion', index: index });
        }

        function startAgent() {
            vscode.postMessage({ type: 'command', command: 'start-agent' });
            addAgentLog('Starting agent...');
        }

        function stopAgent() {
            vscode.postMessage({ type: 'command', command: 'stop-agent' });
            addAgentLog('Stopping agent...');
        }

        function addAgentLog(message) {
            const logs = document.getElementById('agent-logs');
            const time = new Date().toLocaleTimeString();
            logs.innerHTML += '<div style="padding: 4px 12px; border-bottom: 1px solid var(--border-color); font-size: 12px;"><span style="color: var(--text-secondary);">[' + time + ']</span> ' + message + '</div>';
            logs.scrollTop = logs.scrollHeight;
        }

        function updateAgentStatus(connected) {
            const dot = document.getElementById('agent-status-dot');
            const text = document.getElementById('agent-status-text');
            const startBtn = document.getElementById('agent-start-btn');
            const stopBtn = document.getElementById('agent-stop-btn');
            if (connected) {
                dot.style.background = 'var(--status-connected)';
                text.textContent = 'Running';
                startBtn.disabled = true;
                stopBtn.disabled = false;
            } else {
                dot.style.background = 'var(--status-disconnected)';
                text.textContent = 'Stopped';
                startBtn.disabled = false;
                stopBtn.disabled = true;
            }
        }

        document.getElementById('input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
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
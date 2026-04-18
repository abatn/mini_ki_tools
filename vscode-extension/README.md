# Mini KI Tools - VS Code Extension

AI-powered coding assistant for VS Code with autonomous planning, collaboration, and sandboxing.

## Features

- 🤖 **AI Chat** - Open WebView with AI assistant
- 📝 **Code Analysis** - Analyze current file with AI
- 🔄 **Refactoring** - Refactor selected code
- ✏️ **Apply Changes** - Apply AI-generated code changes via Diff Editor
- 📊 **Status Bar** - Shows connection status
- 🔗 **VS Code API Integration** - Reads current file, cursor position, selection

## Installation

1. Navigate to the extension directory:
   ```bash
   cd vscode-extension
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Compile TypeScript:
   ```bash
   npm run compile
   ```

4. Press `F5` in VS Code to launch the extension

## Commands

| Command | Description |
|---------|-------------|
| `Mini KI Tools: Start Agent` | Connect to the agent server |
| `Mini KI Tools: Chat` | Open chat with AI assistant |
| `Mini KI Tools: Apply Changes` | Apply code changes from AI |
| `Mini KI Tools: Analyze Code` | Analyze current file |
| `Mini KI Tools: Refactor` | Refactor selected code |

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `mini-ki-tools.serverUrl` | `http://localhost:8000` | Agent server URL |
| `mini-ki-tools.autoStart` | `false` | Auto-connect on startup |
| `mini-ki-tools.maxTokens` | `4096` | Max response tokens |

## WebView Features

- Chat interface with message history
- Shows current file info
- Connection status indicator
- Send messages via Enter or button

## Requirements

- VS Code 1.75.0+
- Mini KI Tools server running on configured URL

## Development

```bash
# Watch for changes
npm run watch

# Run tests
npm test
```

## License

MIT
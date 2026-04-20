# Mini KI Tools (أدوات الذكاء الاصطناعي المصغرة)

Lokaler KI-Agent mit Web-UI und VS Code Extension, der Dateien lesen/schreiben, Code ausführen, HTTP-Anfragen und Terminal-Befehle ausführen kann - unter Verwendung lokaler LLMs (Ollama).

## Komponenten

- **Web UI** - Browser-basierte Agent-Oberfläche (React)
- **VS Code Extension** - Direkte Integration in VS Code
- **Python Backend** - TAO-Loop (Thought → Action → Observation)

## Features

- Einheitliche Benutzeroberfläche mit Tabs
- Professionelles Arabisches Design (RTL)
- Lokale LLM-Unterstützung (Ollama)
- Dateioperationen (lesen/schreiben)
- Code-Ausführung (Python)
- HTTP-Anfragen
- Terminal-Befehle
- Agent-Loop mit Thought → Action → Observation
- Refactoring-Vorlagen
- Quick Actions für häufige Aufgaben
- Konfigurierbare Einstellungen

## UI-Struktur

### Tabs (6 Funktionen)
1. **💬 محادثة (Chat)** - Chatten mit dem KI-Agenten
2. **🔍 تحليل (Analyze)** - Code analysieren
3. **🔧 إعادة هيكلة (Refactor)** - Code refaktorieren mit Vorlagen
4. **✨ إكمال (Completion)** - Code-Vervollständigung
5. **⚡ الوكيل (Agent)** - Agent starten/stoppen
6. **⚙️ الإعدادات (Settings)** - Konfiguration

### Design
- Dark Theme: GitHub Dark / VS Code Dark+
- Sprache: Arabisch mit RTL
- Font: Cairo

## VS Code Extension

Die VS Code Extension ermöglicht direkte Kommunikation mit dem KI-Agenten innerhalb von VS Code.

### Installation

```bash
cd vscode-extension
npm install
npm run compile
```

### Konfiguration

In VS Code Settings (`settings.json`):

```json
{
  "mini-ki-tools.pythonPath": "${extensionPath}/python/venv/bin/python",
  "mini-ki-tools.llmUrl": "http://localhost:11434",
  "mini-ki-tools.llmModel": "llama3.2",
  "mini-ki-tools.workspacePath": "${workspaceFolder}"
}
```

### Entwicklung

```bash
# Extension entwickeln
cd vscode-extension

# Kompilieren
npm run compile

# Mit F5 debuggen (VS Code Extension Host)

# Python-Abhängigkeiten installieren
cd python
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Befehle

- `Mini KI Tools: Start Agent` - Agent starten
- `Mini KI Tools: Chat` - Chat-Panel öffnen
- `Mini KI Tools: Analyze Code` - Code analysieren
- `Mini KI Tools: Refactor` - Code refaktorieren
- `Mini KI Tools: Settings` - Einstellungen öffnen

### Arabische UI

Die Extension und Web-UI verwenden vollständig Arabische Oberfläche mit:
- RTL-Layout (rechts nach links)
- Moderne Cairo-Schrift
- VS Code Dark+ / GitHub Dark Theme
- 6 Tabs für alle Funktionen

### Architektur

Die Extension startet einen Python-Subprozess (`extension_host.py`) und kommuniziert via stdin/stdout:

```
VS Code ←→ extension.ts ←→ stdin/stdout ←→ extension_host.py ←→ TAO-Loop ←→ Ollama
```

## Web Server (Alternative)

### Setup

```bash
# Abhängigkeiten installieren
pip install -r requirements.txt

# Server starten
python agent_server.py
```

### Docker

```bash
docker build -t mini-ki-tools .
docker run -p 8000:8000 -e LLM_URL=http://host.docker.internal:11434 mini-ki-tools
```

## Umgebungsvariablen

- `LLM_URL` - Ollama URL (Standard: http://localhost:11434)
- `LLM_MODEL` - Modellname (Standard: llama3.2)
- `WORKSPACE_PATH` - Arbeitsverzeichnis

## Usage

1. **VS Code Extension**: Öffne das Chat-Panel mit `Strg+Shift+P` → "Mini KI Tools: Chat"
2. **Web UI**: Öffne http://localhost:8000
3. Gib Prompts ein wie ">> hilf mir, CSV zu laden"
4. Der Agent führt Aktionen automatisch aus

## Refactoring-Vorlagen

Im Refactor-Tab können Vorlagen verwendet werden:
- **📤 استخراج دالة** - Funktion extrahieren
- **✏️ إعادة تسمية** - Umbenennen
- **📥 دمج في place** - Inline zusammenführen
- **⚡ تحسين الأداء** - Leistung optimieren
- **🧹 تنظيف الكود** - Code aufräumen

## Quick Actions

Im Chat-Tab gibt es Schnellaktionen:
- **📖 erkären** - Code erklären
- **🐛 Bugs finden** - Fehler finden
- **⚡ تحسين** - Optimieren
- **💬 تعليق** - Kommentare hinzufügen

## Bestätigungen

- ✅ UI KONSOLIDIERT
- ✅ ARABISCHES DESIGN IMPLEMENTIERT
- ✅ ERWEITERTE FEATURES HINZUGEFÜGT
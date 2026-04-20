# Mini KI Tools - VS Code Extension

AI-powered coding assistant mit fortschrittlichem Reasoning und Provider-Management.

## Features

- 🔑 **Provider Manager** - 12 LLM-Provider mit API-Keys
- 🧠 **Reasoning Engine** - 7 verschiedene Reasoning-Modi
- ⚡ **Slash Commands** - /workflow, /test, /make, etc.
- 👥 **Agent Teams** - Multi-Agent Kollaboration
- 🤖 TAO-Loop Agent
- 💬 Chat mit AI
- 🔍 Code-Analyse
- 🔧 Refactoring
- ✨ Code-Vervollständigung
- 📊 Sidebar-Navigation
- 🌍 i18n (EN/AR/FR)
- 🔒 Permissions System

## Installation

1. Install the extension from VS Code Marketplace
2. **Fertig!** Die Extension startet automatisch.

## Zero-Configuration

- Python-Umgebung wird automatisch eingerichtet
- Alle Abhängigkeiten werden automatisch installiert

## API Provider (12 Provider)

| Provider | API Key |
|---------|-------|
| Ollama | lokal |
| OpenAI | OPENAI_API_KEY |
| Anthropic | ANTHROPIC_API_KEY |
| Groq | GROQ_API_KEY |
| Hugging Face | HF_TOKEN |
| Mistral AI | MISTRAL_API_KEY |
| Google AI | GOOGLE_API_KEY |
| OpenRouter | OPENROUTER_API_KEY |
| Together AI | TOGETHER_API_KEY |
| Replicate | REPLICATE_API_TOKEN |
| DeepInfra | DEEPINFRA_API_KEY |
| Cohere | COHERE_API_KEY |

**Features:**
- Sichere verschlüsselte Speicherung
- Automatische Verfügbarkeitsprüfung
- Latenz-Messung (ms)
- Auto-Modus: Schnellster Provider

## Reasoning-Modi

| Modus | Beschreibung |
|-------|-------------|
| TAO | Thought-Action-Observation |
| ToT | Tree of Thoughts |
| GoT | Graph of Thoughts |
| Reflexion | With Error Memory |
| Plan-Solve | Plan then Execute |
| PoT | Code as Thought |
| Voyager | Experience-based |

## Slash Commands

| Command | Beschreibung |
|---------|-------------|
| /workflow | Fire-and-forget Workflow |
| /test | TDD Test-Runner |
| /make | Code-Implementierung |
| /explain | Code-Erklärung |
| /bug | Bug-Finder/Fixer |
| /refactor | Refactoring |
| /review | Code-Review |

## Agent Teams

- Team erstellen mit Lead Agent
- Teammates spawnen (coder, reviewer, tester)
- Team-Nachrichten senden
- Status abrufen

## Sidebar

| Icon | Funktion |
|------|----------|
| 💬 | Chat |
| 🔍 | Analyze |
| 🔧 | Refactor |
| ✨ | Complete |
| ⚡ | Agent |
| ⚙️ | Settings |

## i18n

- 🇬🇧 Englisch
- 🇸🇦 Arabisch (RTL)
- 🇫🇷 Französisch

## Requirements

- VS Code 1.75+
- Python 3.11+

## License

MIT
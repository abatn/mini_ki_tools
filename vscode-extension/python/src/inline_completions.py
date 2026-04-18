# Inline Autocompletion Provider for VS Code
# Generiert Vorschläge via lokales LLM (Ollama) für Code-Vervollständigung

import os
import json
import requests
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class CompletionRequest:
    """Request for code completion"""
    file_path: str
    content: str
    cursor_line: int
    cursor_column: int
    language: str
    max_tokens: int = 100


@dataclass
class CompletionResult:
    """Result of code completion"""
    completions: List[str]
    is_incomplete: bool = False
    provider: str = "ollama"


class InlineCompletionProvider:
    """
    Provider für Inline-Autovervollständigung.
    Generiert Vorschläge via lokales LLM (Ollama) für Code-Vervollständigung
    basierend auf aktueller Cursor-Position und Kontext.
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "codellama",
        temperature: float = 0.2,
        max_context_lines: int = 50
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.temperature = temperature
        self.max_context_lines = max_context_lines
        self._session = requests.Session()
        self._session.timeout = 10
    
    def _check_ollama_available(self) -> bool:
        """Prüfe ob Ollama verfügbar ist"""
        try:
            response = self._session.get(f"{self.ollama_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False
    
    def _build_prompt(self, request: CompletionRequest) -> str:
        """Build completion prompt from context"""
        lines = request.content.split('\n')
        
        # Get context around cursor
        start_line = max(0, request.cursor_line - self.max_context_lines)
        end_line = min(len(lines), request.cursor_line + 5)
        
        context = '\n'.join(lines[start_line:end_line])
        
        # Build prompt based on language
        language_hints = {
            'python': 'Python',
            'javascript': 'JavaScript',
            'typescript': 'TypeScript',
            'java': 'Java',
            'cpp': 'C++',
            'go': 'Go',
            'rust': 'Rust'
        }
        
        lang = language_hints.get(request.language.lower(), request.language)
        
        prompt = f"""Complete the following {lang} code. Only output the completion, no explanations.

Context:
{context}

Current line: {request.cursor_line + 1}
Cursor position: column {request.cursor_column + 1}

Provide 3 possible completions, one per line:"""
        
        return prompt
    
    def _parse_completions(self, response_text: str) -> List[str]:
        """Parse completions from LLM response"""
        completions = []
        
        for line in response_text.split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                completions.append(line)
                if len(completions) >= 3:
                    break
        
        return completions
    
    def get_completions(self, request: CompletionRequest) -> CompletionResult:
        """
        Get code completions for the given request.
        
        Args:
            request: Completion request with file info and cursor position
            
        Returns:
            CompletionResult with list of completions
        """
        # Check if Ollama is available
        if not self._check_ollama_available():
            logger.warning("Ollama not available, returning empty completions")
            return CompletionResult(
                completions=[],
                is_incomplete=False,
                provider="ollama-offline"
            )
        
        try:
            prompt = self._build_prompt(request)
            
            # Call Ollama
            response = self._session.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "max_tokens": request.max_tokens,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                response_text = result.get('response', '')
                completions = self._parse_completions(response_text)
                
                return CompletionResult(
                    completions=completions,
                    is_incomplete=False,
                    provider="ollama"
                )
            else:
                logger.error(f"Ollama returned status {response.status_code}")
                return CompletionResult(completions=[], provider="ollama-error")
                
        except Exception as e:
            logger.error(f"Completion error: {e}")
            return CompletionResult(completions=[], provider="error")
    
    def get_inline_completion(
        self,
        document: str,
        position: Dict[str, int],
        language: str
    ) -> Optional[str]:
        """
        Get a single inline completion (for VS Code integration).
        
        Args:
            document: Full document content
            position: Cursor position {line, character}
            language: Programming language
            
        Returns:
            Completion string or None
        """
        request = CompletionRequest(
            file_path="",
            content=document,
            cursor_line=position.get('line', 0),
            cursor_column=position.get('character', 0),
            language=language,
            max_tokens=50
        )
        
        result = self.get_completions(request)
        
        if result.completions:
            return result.completions[0]
        return None


# VS Code Extension Integration
def register_completion_provider():
    """Register completion provider with VS Code (for extension.ts)"""
    return """
// Inline Completion Provider Integration
// Add to your VS Code extension:

const completionProvider = new InlineCompletionProvider();

vscode.languages.registerInlineCompletionItemProvider(
    { pattern: '**/*' },
    {
        provideInlineCompletionItems: async (document, position, context) => {
            const content = document.getText();
            const language = document.languageId;
            
            const result = completionProvider.get_inline_completion(
                content,
                { line: position.line, character: position.character },
                language
            );
            
            if (result) {
                return [{
                    insertText: result,
                    range: new vscode.Range(position, position)
                }];
            }
            return [];
        }
    }
);
"""


# Standalone test
if __name__ == "__main__":
    provider = InlineCompletionProvider()
    
    # Test completion
    test_code = '''def calculate_sum(a, b):
    """Calculate sum of two numbers"""
    return a + b

def main():
    result = calculate_sum(5, 3)
    print(f"Result: {result}")
'''
    
    request = CompletionRequest(
        file_path="test.py",
        content=test_code,
        cursor_line=7,
        cursor_column=10,
        language="python",
        max_tokens=50
    )
    
    result = provider.get_completions(request)
    print(f"Completions: {result.completions}")
    print(f"Provider: {result.provider}")
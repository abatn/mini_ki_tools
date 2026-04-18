# LLM Provider Abstraction Layer
# Zentrale Schnittstelle für verschiedene LLM-Anbieter

import os
import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import requests

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstrakte Basisklasse für LLM Provider"""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generiere eine Antwort vom LLM"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Prüfe ob der Provider verfügbar ist"""
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Gib den Namen des Providers zurück"""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """Gib das Standard-Modell zurück"""
        pass


class OllamaProvider(LLMProvider):
    """Ollama - Lokale LLM-Verbindung (flexibel via Umgebungsvariablen)"""

    def __init__(
        self,
        url: str = None,
        model: str = None,
        timeout: int = 30
    ):
        # Use environment variables with sensible defaults
        # LLM_URL: Override default Ollama URL (e.g., http://localhost:11434)
        # LLM_MODEL: Override default model (e.g., llama3.2)
        self.url = url or os.environ.get("LLM_URL", "http://localhost:11434")
        self.model = model or os.environ.get("LLM_MODEL", "llama3.2")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.timeout = timeout
        logger.info(f"OllamaProvider initialized: URL={self.url}, Model={self.model}")

    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generiere Antwort von Ollama"""
        try:
            payload = {
                "model": kwargs.get("model", self.model),
                "prompt": prompt,
                "stream": False
            }
            if system_prompt:
                payload["system"] = system_prompt

            response = self._session.post(
                f"{self.url}/api/generate",
                json=payload
            )

            if response.status_code == 200:
                return response.json().get("response", "").strip()
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return f"Error: {response.status_code}"

        except requests.exceptions.Timeout:
            return "Error: Request timed out"
        except Exception as e:
            logger.error(f"Ollama call failed: {e}")
            return f"Error: {str(e)}"

    def is_available(self) -> bool:
        """Prüfe ob Ollama verfügbar ist"""
        try:
            response = self._session.get(f"{self.url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False

    def get_available_models(self) -> List[str]:
        """Liste alle verfügbaren Ollama-Modelle auf"""
        try:
            response = self._session.get(f"{self.url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [m.get("name", "") for m in data.get("models", [])]
        except:
            pass
        return []

    def get_default_model(self) -> str:
        """Gib das Default-Modell zurück - holt erstes verfügbares wenn keines gesetzt"""
        if self.model:
            return self.model
        # Try to get first available model
        models = self.get_available_models()
        if models:
            return models[0]
        return "llama3.2"  # Ultimate fallback

    def get_name(self) -> str:
        return "ollama"


class OpenAIProvider(LLMProvider):
    """OpenAI - API-basierte LLM-Verbindung (flexibel via Umgebungsvariablen)"""

    def __init__(
        self,
        api_key: str = None,
        model: str = None,
        base_url: str = None,
        timeout: int = 60
    ):
        # Use environment variables with sensible defaults
        # LLM_API_KEY or OPENAI_API_KEY: API key for OpenAI
        # LLM_MODEL or OPENAI_MODEL: Model to use (default: gpt-4)
        # LLM_URL or OPENAI_BASE_URL: Custom API endpoint
        self.api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("LLM_MODEL") or os.environ.get("OPENAI_MODEL", "gpt-4")
        self.base_url = base_url or os.environ.get("LLM_URL") or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.timeout = timeout
        self._session = requests.Session()
        if self.api_key:
            self._session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self._session.timeout = timeout
        logger.info(f"OpenAIProvider initialized: Model={self.model}, BaseURL={self.base_url}")

    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generiere Antwort von OpenAI"""
        if not self.api_key:
            return "Error: OpenAI API key not configured"

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": kwargs.get("model", self.model),
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 2000)
            }

            response = self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"OpenAI error: {response.status_code}")
                return f"Error: {response.status_code}"

        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            return f"Error: {str(e)}"

    def is_available(self) -> bool:
        """Prüfe ob OpenAI verfügbar ist"""
        if not self.api_key:
            return False
        try:
            response = self._session.get(
                f"{self.base_url}/models",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False

    def get_name(self) -> str:
        return "openai"

    def get_default_model(self) -> str:
        return self.model


class AnthropicProvider(LLMProvider):
    """Anthropic - Claude API"""

    def __init__(
        self,
        api_key: str = None,
        model: str = "claude-3-sonnet-20240229",
        timeout: int = 60
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model
        self.timeout = timeout
        self.base_url = "https://api.anthropic.com/v1"
        self._session = requests.Session()
        self._session.headers.update({
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        })
        self._session.timeout = timeout

    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generiere Antwort von Anthropic"""
        if not self.api_key:
            return "Error: Anthropic API key not configured"

        try:
            messages = [{"role": "user", "content": prompt}]

            payload = {
                "model": kwargs.get("model", self.model),
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", 2000),
                "temperature": kwargs.get("temperature", 0.7)
            }

            if system_prompt:
                payload["system"] = system_prompt

            response = self._session.post(
                f"{self.base_url}/messages",
                json=payload
            )

            if response.status_code == 200:
                return response.json()["content"][0]["text"].strip()
            else:
                logger.error(f"Anthropic error: {response.status_code}")
                return f"Error: {response.status_code}"

        except Exception as e:
            logger.error(f"Anthropic call failed: {e}")
            return f"Error: {str(e)}"

    def is_available(self) -> bool:
        """Prüfe ob Anthropic verfügbar ist"""
        if not self.api_key:
            return False
        return True  # Simplified check

    def get_name(self) -> str:
        return "anthropic"

    def get_default_model(self) -> str:
        return self.model


class OpenRouterProvider(LLMProvider):
    """OpenRouter - Aggregator für mehrere LLM-Anbieter"""

    def __init__(
        self,
        api_key: str = None,
        model: str = "openai/gpt-3.5-turbo",
        timeout: int = 60
    ):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY", "")
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1"
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {self.api_key}"})
        self._session.timeout = timeout

    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generiere Antwort über OpenRouter"""
        if not self.api_key:
            return "Error: OpenRouter API key not configured"

        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": kwargs.get("model", self.model),
                "messages": messages,
                "temperature": kwargs.get("temperature", 0.7),
                "max_tokens": kwargs.get("max_tokens", 2000)
            }

            response = self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )

            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            else:
                logger.error(f"OpenRouter error: {response.status_code}")
                return f"Error: {response.status_code}"

        except Exception as e:
            logger.error(f"OpenRouter call failed: {e}")
            return f"Error: {str(e)}"

    def is_available(self) -> bool:
        """Prüfe ob OpenRouter verfügbar ist"""
        if not self.api_key:
            return False
        return True

    def get_name(self) -> str:
        return "openrouter"

    def get_default_model(self) -> str:
        return self.model


class LLMProviderFactory:
    """Factory zur Erstellung von LLM Providern"""

    PROVIDERS = {
        "ollama": OllamaProvider,
        "openai": OpenAIProvider,
        "anthropic": AnthropicProvider,
        "openrouter": OpenRouterProvider
    }

    @classmethod
    def create(cls, provider_name: str, config: Dict = None) -> Optional[LLMProvider]:
        """Erstelle einen Provider basierend auf Namen und Konfiguration"""
        if provider_name not in cls.PROVIDERS:
            logger.error(f"Unknown provider: {provider_name}")
            return None

        provider_class = cls.PROVIDERS[provider_name]
        return provider_class(**(config or {}))

    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Liste aller verfügbaren Provider"""
        return list(cls.PROVIDERS.keys())


class LLMProviderManager:
    """Zentrale Verwaltung der LLM Provider"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.environ.get(
            "LLM_CONFIG_PATH",
            "config/llm_config.yaml"
        )
        self._config = self._load_config()
        self._current_provider: Optional[LLMProvider] = None
        self._provider_name = self._config.get("default_provider", "ollama")
        self._initialize_provider()

    def _load_config(self) -> Dict:
        """Lade Konfiguration aus YAML/JSON und Umgebungsvariablen"""
        config = {}

        # Load from YAML config file
        try:
            import yaml
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
        except ImportError:
            logger.warning("PyYAML not installed, using JSON config")

        # Fallback: JSON config
        if not config:
            json_path = self.config_path.replace(".yaml", ".json")
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    config = json.load(f)

        # Override with environment variables for runtime flexibility
        # LLM_URL: The base URL for the LLM API (e.g., http://localhost:11434)
        # LLM_MODEL: The model name to use (e.g., llama3.2, gpt-4, etc.)
        # LLM_PROVIDER: The provider type (ollama, openai, anthropic, openrouter)
        # LLM_API_KEY: API key for cloud providers

        if "providers" not in config:
            config["providers"] = {}

        # Environment variable overrides for Ollama
        llm_url = os.environ.get("LLM_URL")
        llm_model = os.environ.get("LLM_MODEL")
        llm_provider = os.environ.get("LLM_PROVIDER", "ollama")
        llm_api_key = os.environ.get("LLM_API_KEY")

        if llm_url or llm_model:
            # Use environment variables to configure provider
            if "ollama" not in config["providers"]:
                config["providers"]["ollama"] = {}

            if llm_url:
                config["providers"]["ollama"]["url"] = llm_url
            if llm_model:
                config["providers"]["ollama"]["model"] = llm_model

            # Set as default if not already set
            if "default_provider" not in config:
                config["default_provider"] = llm_provider

        # Apply API key from environment
        if llm_api_key:
            for provider_name in ["openai", "anthropic", "openrouter"]:
                if provider_name not in config["providers"]:
                    config["providers"][provider_name] = {}
                config["providers"][provider_name]["api_key"] = llm_api_key

        # Set default provider from environment if specified
        if llm_provider and "default_provider" not in config:
            config["default_provider"] = llm_provider

        # Ensure default provider is set
        if "default_provider" not in config:
            config["default_provider"] = "ollama"

        return config

    def _initialize_provider(self):
        """Initialisiere den aktuellen Provider"""
        provider_config = self._config.get("providers", {}).get(self._provider_name, {})
        self._current_provider = LLMProviderFactory.create(self._provider_name, provider_config)

    def get_provider(self) -> Optional[LLMProvider]:
        """Gib den aktuellen Provider zurück"""
        return self._current_provider

    def get_current_provider_name(self) -> str:
        """Gib den Namen des aktuellen Providers zurück"""
        return self._provider_name

    def switch_provider(self, provider_name: str) -> bool:
        """Wechsle zu einem anderen Provider"""
        if provider_name not in LLMProviderFactory.PROVIDERS:
            logger.error(f"Unknown provider: {provider_name}")
            return False

        self._provider_name = provider_name
        self._initialize_provider()
        logger.info(f"Switched to provider: {provider_name}")
        return True

    def list_providers(self) -> List[Dict]:
        """Liste alle konfigurierten Provider mit Status"""
        providers = []
        for name in LLMProviderFactory.get_available_providers():
            provider = LLMProviderFactory.create(
                name,
                self._config.get("providers", {}).get(name, {})
            )
            providers.append({
                "name": name,
                "available": provider.is_available() if provider else False,
                "default_model": provider.get_default_model() if provider else None
            })
        return providers

    def generate(self, prompt: str, system_prompt: str = None, **kwargs) -> str:
        """Generiere Antwort mit aktuellem Provider"""
        if not self._current_provider:
            return "Error: No provider configured"
        return self._current_provider.generate(prompt, system_prompt, **kwargs)


# Globale Instanz für einfachen Zugriff
_provider_manager: Optional[LLMProviderManager] = None


def get_llm_manager(config_path: str = None) -> LLMProviderManager:
    """Gib die globale LLM Provider Manager Instanz zurück"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = LLMProviderManager(config_path)
    return _provider_manager


def get_llm_provider() -> Optional[LLMProvider]:
    """Gib den aktuellen LLM Provider zurück"""
    return get_llm_manager().get_provider()


def generate(prompt: str, system_prompt: str = None, **kwargs) -> str:
    """Generiere LLM Antwort (Convenience-Funktion)"""
    return get_llm_manager().generate(prompt, system_prompt, **kwargs)
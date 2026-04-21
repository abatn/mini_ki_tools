# Provider Manager - Vollautomatisches LLM-Provider-System
# Unterstützt: OpenAI, Anthropic, Ollama, HuggingFace, Groq, Together AI, OpenRouter, etc.

import os
import json
import time
import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import requests

logger = logging.getLogger(__name__)

# Verschlüsselung für API-Keys
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography not available, API keys will be stored in plaintext")


class ProviderStatus(Enum):
    """Provider Verfügbarkeits-Status"""
    UNCONFIGURED = "unconfigured"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    CHECKING = "checking"


@dataclass
class Provider:
    """Ein LLM Provider mit Konfiguration"""
    id: str
    name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    status: ProviderStatus = ProviderStatus.UNCONFIGURED
    latency_ms: float = 999999
    last_check: Optional[str] = None
    models: List[str] = field(default_factory=list)
    enabled: bool = True
    
    def has_api_key(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 0)


@dataclass
class ProviderConfig:
    """Konfiguration für einen Provider"""
    id: str
    name: str
    base_url: str
    api_key_env: str
    default_model: str
    models_endpoint: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)


# Alle unterstützten Provider
PROVIDER_CONFIGS: Dict[str, ProviderConfig] = {
    "ollama": ProviderConfig(
        id="ollama",
        name="Ollama",
        base_url="http://localhost:11434",
        api_key_env="",
        default_model="llama3.2",
        models_endpoint="/api/tags"
    ),
    "openai": ProviderConfig(
        id="openai",
        name="OpenAI",
        base_url="https://api.openai.com/v1",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
        models_endpoint="/models"
    ),
    "anthropic": ProviderConfig(
        id="anthropic",
        name="Anthropic",
        base_url="https://api.anthropic.com/v1",
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-3-5-sonnet-20241022",
        headers={"anthropic-version": "2023-06-01"}
    ),
    "groq": ProviderConfig(
        id="groq",
        name="Groq",
        base_url="https://api.groq.com/openai/v1",
        api_key_env="GROQ_API_KEY",
        default_model="llama-3.1-70b-versatile",
        models_endpoint="/models"
    ),
    "huggingface": ProviderConfig(
        id="huggingface",
        name="Hugging Face",
        base_url="https://api-inference.huggingface.co",
        api_key_env="HF_TOKEN",
        default_model="meta-llama/Llama-3.2-1B-Instruct",
        models_endpoint="/models"
    ),
    "togetherai": ProviderConfig(
        id="togetherai",
        name="Together AI",
        base_url="https://api.together.ai/v1",
        api_key_env="TOGETHER_API_KEY",
        default_model="meta-llama/Llama-3.2-70B-Instruct-Turbo",
        models_endpoint="/models"
    ),
    "openrouter": ProviderConfig(
        id="openrouter",
        name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        api_key_env="OPENROUTER_API_KEY",
        default_model="anthropic/claude-3.5-sonnet",
        models_endpoint="/models"
    ),
    "replicate": ProviderConfig(
        id="replicate",
        name="Replicate",
        base_url="https://api.replicate.com/v1",
        api_key_env="REPLICATE_API_TOKEN",
        default_model="meta/llama-3.2-90b-instruct"
    ),
    "deepinfra": ProviderConfig(
        id="deepinfra",
        name="DeepInfra",
        base_url="https://api.deepinfra.com/v1",
        api_key_env="DEEPINFRA_API_KEY",
        default_model="meta-llama/Llama-3.2-70B-Instruct",
        models_endpoint="/models"
    ),
    "cohere": ProviderConfig(
        id="cohere",
        name="Cohere",
        base_url="https://api.cohere.ai/v1",
        api_key_env="COHERE_API_KEY",
        default_model="command-r-plus-08-2024"
    ),
    "mistral": ProviderConfig(
        id="mistral",
        name="Mistral AI",
        base_url="https://api.mistral.ai/v1",
        api_key_env="MISTRAL_API_KEY",
        default_model="mistral-large-latest",
        models_endpoint="/models"
    ),
    "google": ProviderConfig(
        id="google",
        name="Google AI",
        base_url="https://generativelanguage.googleapis.com/v1",
        api_key_env="GOOGLE_API_KEY",
        default_model="gemini-1.5-pro"
    ),
}


class EncryptedStorage:
    """Sichere verschlüsselte Speicherung"""
    
    def __init__(self, storage_path: str = "~/.mini_ki_providers.enc"):
        self.storage_path = os.path.expanduser(storage_path)
        self._key = None
        self._fernet = None
        self._init_crypto()
    
    def _init_crypto(self):
        """Initialisiere Verschlüsselung"""
        if not CRYPTO_AVAILABLE:
            return
        
        key_file = self.storage_path + ".key"
        
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                self._key = f.read()
        else:
            self._key = Fernet.generate_key()
            with open(key_file, "wb") as f:
                f.write(self._key)
        
        self._fernet = Fernet(self._key)
    
    def save(self, data: Dict) -> bool:
        """Speichere verschlüsselte Daten"""
        try:
            json_data = json.dumps(data)
            
            if CRYPTO_AVAILABLE and self._fernet:
                encrypted = self._fernet.encrypt(json_data.encode())
                with open(self.storage_path, "wb") as f:
                    f.write(encrypted)
            else:
                with open(self.storage_path, "w") as f:
                    f.write(json_data)
            
            return True
        except Exception as e:
            logger.error(f"Failed to save encrypted data: {e}")
            return False
    
    def load(self) -> Dict:
        """Lade verschlüsselte Daten"""
        try:
            if not os.path.exists(self.storage_path):
                return {}
            
            if CRYPTO_AVAILABLE and self._fernet:
                with open(self.storage_path, "rb") as f:
                    encrypted = f.read()
                decrypted = self._fernet.decrypt(encrypted)
                return json.loads(decrypted)
            else:
                with open(self.storage_path, "r") as f:
                    return json.loads(f.read())
        except Exception as e:
            logger.error(f"Failed to load encrypted data: {e}")
            return {}


class ProviderManager:
    """
    Vollautomatischer Provider Manager
    - Verwaltet API-Keys sicher
    - Prüft Verfügbarkeit periodisch
    - Wählt automatisch schnellsten Provider
    """
    
    def __init__(self):
        self.storage = EncryptedStorage()
        self.providers: Dict[str, Provider] = {}
        self._last_full_check = 0
        self._check_interval = 24 * 3600  # 24 hours
        self._load_providers()
    
    def _load_providers(self):
        """Lade Provider aus Speicher"""
        data = self.storage.load()
        
        for config in PROVIDER_CONFIGS.values():
            stored_key = data.get(config.id, {}).get("api_key")
            env_key = os.environ.get(config.api_key_env)
            
            provider = Provider(
                id=config.id,
                name=config.name,
                api_key=stored_key or env_key or "",
                base_url=config.base_url,
                enabled=data.get(config.id, {}).get("enabled", True),
                models=data.get(config.id, {}).get("models", [])
            )
            
            if provider.has_api_key():
                provider.status = ProviderStatus.UNAVAILABLE
            
            self.providers[config.id] = provider
    
    def save_api_key(self, provider_id: str, api_key: str) -> bool:
        """Speichere API-Key für Provider"""
        if provider_id not in PROVIDER_CONFIGS:
            return False
        
        if provider_id in self.providers:
            self.providers[provider_id].api_key = api_key
            self.providers[provider_id].status = ProviderStatus.UNAVAILABLE
        
        # Save to storage
        data = self.storage.load()
        data[provider_id] = {
            "api_key": api_key,
            "enabled": self.providers[provider_id].enabled,
            "models": self.providers[provider_id].models
        }
        
        return self.storage.save(data)
    
    def remove_api_key(self, provider_id: str) -> bool:
        """Entferne API-Key für Provider"""
        if provider_id in self.providers:
            self.providers[provider_id].api_key = ""
            self.providers[provider_id].status = ProviderStatus.UNCONFIGURED
            self.providers[provider_id].models = []
        
        data = self.storage.load()
        if provider_id in data:
            del data[provider_id]
        
        return self.storage.save(data)
    
    def get_configured_providers(self) -> List[Provider]:
        """Liste Provider mit API-Key"""
        return [p for p in self.providers.values() if p.has_api_key()]
    
    def get_available_providers(self) -> List[Provider]:
        """Liste verfügbare Provider"""
        return [p for p in self.providers.values() 
                if p.has_api_key() and p.status == ProviderStatus.AVAILABLE]
    
    async def check_provider(self, provider_id: str) -> Provider:
        """Prüfe Verfügbarkeit eines Providers"""
        if provider_id not in self.providers:
            return self.providers.get(provider_id)
        
        provider = self.providers[provider_id]
        
        if not provider.has_api_key():
            provider.status = ProviderStatus.UNCONFIGURED
            return provider
        
        provider.status = ProviderStatus.CHECKING
        
        try:
            # Speed test
            start = time.time()
            
            if provider_id == "ollama":
                response = requests.get(
                    f"{provider.base_url}/api/tags",
                    timeout=5
                )
            elif provider_id == "openai":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=5
                )
            elif provider_id == "anthropic":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={
                        "x-api-key": provider.api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    timeout=5
                )
            elif provider_id == "google":
                response = requests.get(
                    f"{provider.base_url}/models?key={provider.api_key}",
                    timeout=5
                )
            elif provider_id == "replicate":
                response = requests.get(
                    "https://api.replicate.com/v1/models",
                    headers={"Authorization": f"Token {provider.api_key}"},
                    timeout=5
                )
            elif provider_id == "cohere":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=5
                )
            elif provider_id == "mistral":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=5
                )
            elif provider_id == "deepinfra":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=5
                )
            else:
                # Generic check
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=5
                )
            
            latency = (time.time() - start) * 1000
            
            if response.status_code < 400:
                provider.status = ProviderStatus.AVAILABLE
                provider.latency_ms = latency
                provider.last_check = time.strftime("%Y-%m-%d %H:%M")
                
                # Try to get models
                await self._fetch_models(provider_id)
            else:
                provider.status = ProviderStatus.UNAVAILABLE
                
        except Exception as e:
            logger.warning(f"Provider {provider_id} check failed: {e}")
            provider.status = ProviderStatus.UNAVAILABLE
        
        return provider
    
    async def _fetch_models(self, provider_id: str):
        """Hole verfügbare Models für Provider"""
        provider = self.providers.get(provider_id)
        if not provider or not provider.has_api_key():
            return
        
        try:
            if provider_id == "ollama":
                response = requests.get(
                    f"{provider.base_url}/api/tags",
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["name"] for m in response.json().get("models", [])]
                    provider.models = models
            
            elif provider_id in ["openai", "groq", "togetherai", "openrouter"]:
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["id"] for m in response.json().get("data", [])]
                    provider.models = models
            
            elif provider_id == "anthropic":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={
                        "x-api-key": provider.api_key,
                        "anthropic-version": "2023-06-01"
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["id"] for m in response.json().get("data", [])]
                    provider.models = models
            
            elif provider_id == "huggingface":
                response = requests.get(
                    "https://huggingface.co/api/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    params={"pipeline_tag": "text-generation", "limit": 50},
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["id"] for m in response.json()]
                    provider.models = models[:30]
            
            elif provider_id == "replicate":
                response = requests.get(
                    "https://api.replicate.com/v1/models",
                    headers={"Authorization": f"Token {provider.api_key}"},
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["id"] for m in response.json().get("results", [])]
                    provider.models = models[:20]
            
            elif provider_id == "deepinfra":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["id"] for m in response.json().get("data", [])]
                    provider.models = models
            
            elif provider_id == "cohere":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["id"] for m in response.json().get("models", [])]
                    provider.models = models
            
            elif provider_id == "mistral":
                response = requests.get(
                    f"{provider.base_url}/models",
                    headers={"Authorization": f"Bearer {provider.api_key}"},
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["id"] for m in response.json().get("data", [])]
                    provider.models = models
            
            elif provider_id == "google":
                response = requests.get(
                    f"{provider.base_url}/models?key={provider.api_key}",
                    timeout=10
                )
                if response.status_code == 200:
                    models = [m["name"] for m in response.json().get("models", [])]
                    provider.models = models
            
            # Save models to storage
            data = self.storage.load()
            data[provider_id] = {
                "api_key": provider.api_key,
                "enabled": provider.enabled,
                "models": provider.models
            }
            self.storage.save(data)
            
        except Exception as e:
            logger.warning(f"Failed to fetch models for {provider_id}: {e}")
    
    async def check_all_providers(self, force: bool = False) -> List[Provider]:
        """Prüfe alle konfigurierten Provider"""
        now = time.time()
        
        if not force and (now - self._last_full_check) < self._check_interval:
            return self.get_available_providers()
        
        self._last_full_check = now
        
        tasks = [
            self.check_provider(pid) 
            for pid in self.providers.keys()
            if self.providers[pid].has_api_key()
        ]
        
        await asyncio.gather(*tasks)
        
        return self.get_available_providers()
    
    def get_fastest_provider(self) -> Optional[Provider]:
        """Gib schnellsten verfügbaren Provider zurück"""
        available = self.get_available_providers()
        
        if not available:
            return None
        
        return min(available, key=lambda p: p.latency_ms)
    
    def get_best_provider(self, preferred_id: str = None) -> Optional[Provider]:
        """
        Bester verfügbarer Provider:
        1. Bevorzugter Provider falls verfügbar
        2. Sonst schnellster
        """
        if preferred_id and preferred_id in self.providers:
            p = self.providers[preferred_id]
            if p.status == ProviderStatus.AVAILABLE:
                return p
        
        return self.get_fastest_provider()
    
    def switch_provider(self, provider_id: str) -> bool:
        """Wechsle zu einem anderen Provider und setze Environment Variables"""
        if provider_id not in self.providers:
            return False
        
        provider = self.providers[provider_id]
        
        # Setze Environment Variables für llm_provider
        os.environ["LLM_PROVIDER"] = provider_id
        os.environ["LLM_URL"] = provider.base_url or ""
        
        if provider.models:
            os.environ["LLM_MODEL"] = provider.models[0]
        
        # Setze API Key
        if provider.api_key:
            env_key_var = PROVIDER_CONFIGS.get(provider_id, ProviderConfig("", "", "", "", "")).api_key_env
            if env_key_var:
                os.environ[env_key_var] = provider.api_key
        
        return True
    
    def to_dict(self) -> Dict:
        """Export für UI"""
        return {
            pid: {
                "name": p.name,
                "hasApiKey": p.has_api_key(),
                "status": p.status.value,
                "latencyMs": round(p.latency_ms, 0) if p.latency_ms < 999999 else None,
                "lastCheck": p.last_check,
                "models": p.models[:10] if p.models else [],
                "enabled": p.enabled
            }
            for pid, p in self.providers.items()
        }


# Global instance
_provider_manager: Optional[ProviderManager] = None


def get_provider_manager() -> ProviderManager:
    """Gib globale Provider Manager Instanz"""
    global _provider_manager
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    return _provider_manager


def get_available_providers() -> List[Provider]:
    """Kurzform für verfügbare Provider"""
    return get_provider_manager().get_available_providers()


def get_best_llm_config() -> Dict:
    """Gib beste LLM-Konfiguration für Agent"""
    manager = get_provider_manager()
    provider = manager.get_best_provider()
    
    if not provider:
        return {
            "provider": None,
            "model": None,
            "error": "No provider available"
        }
    
    return {
        "provider": provider.id,
        "name": provider.name,
        "model": provider.models[0] if provider.models else PROVIDER_CONFIGS[provider.id].default_model,
        "base_url": provider.base_url,
        "api_key": provider.api_key,
        "latency_ms": provider.latency_ms
    }
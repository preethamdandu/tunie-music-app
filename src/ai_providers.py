"""
Multi-Provider AI System for TuneGenie
Supports 5 FREE AI providers with automatic fallback
All providers are 100% free with no credit card required
"""

import os
import logging
from typing import Optional, Dict, Any, List
from enum import Enum
import requests
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIProvider(Enum):
    """Supported AI providers (all FREE)"""
    GROQ = "groq"
    GEMINI = "gemini"
    OPENROUTER = "openrouter"
    DEEPSEEK = "deepseek"
    HUGGINGFACE = "huggingface"


class ProviderConfig:
    """Configuration for each AI provider"""
    
    GROQ = {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "max_tokens": 8000,
        "temperature": 0.7,
        "free_tier": {
            "requests_per_minute": 30,
            "requests_per_day": 14400,
            "tokens_per_minute": 20000,
            "cost": 0.0
        },
        "speed": "ultra_fast",
        "quality": "high"
    }
    
    GEMINI = {
        "name": "Google Gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-2.0-flash-exp",
        "max_tokens": 8000,
        "temperature": 0.7,
        "free_tier": {
            "requests_per_minute": 15,
            "requests_per_day": 1500,
            "tokens_per_minute": 1000000,
            "cost": 0.0
        },
        "speed": "fast",
        "quality": "very_high"
    }
    
    OPENROUTER = {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "meta-llama/llama-3.3-70b-instruct:free",
        "max_tokens": 8000,
        "temperature": 0.7,
        "free_tier": {
            "requests_per_minute": 20,
            "requests_per_day": float('inf'),  # Unlimited
            "tokens_per_minute": 200000,
            "cost": 0.0
        },
        "speed": "fast",
        "quality": "high",
        "free_models": [
            "meta-llama/llama-3.3-70b-instruct:free",
            "google/gemini-2.0-flash-exp:free",
            "deepseek/deepseek-r1:free",
            "qwen/qwen-2.5-72b-instruct:free"
        ]
    }
    
    DEEPSEEK = {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "max_tokens": 8000,
        "temperature": 0.7,
        "free_tier": {
            "requests_per_minute": 60,
            "requests_per_day": 10000,
            "tokens_per_minute": 500000,
            "tokens_total": 5000000,  # 5M free tokens on signup
            "cost": 0.0
        },
        "speed": "fast",
        "quality": "very_high"
    }
    
    HUGGINGFACE = {
        "name": "HuggingFace",
        "base_url": "https://api-inference.huggingface.co/models",
        "model": "meta-llama/Llama-3.2-3B-Instruct",
        "max_tokens": 2000,
        "temperature": 0.7,
        "free_tier": {
            "requests_per_minute": 10,
            "requests_per_day": 1000,
            "cost": 0.0
        },
        "speed": "slow",
        "quality": "medium"
    }


class MultiProviderAI:
    """
    Multi-provider AI system with automatic fallback
    Tries providers in order of speed: Groq -> Gemini -> OpenRouter -> DeepSeek -> HuggingFace
    """
    
    def __init__(self):
        self.providers = self._initialize_providers()
        self.provider_priority = [
            AIProvider.GROQ,
            AIProvider.GEMINI,
            AIProvider.OPENROUTER,
            AIProvider.DEEPSEEK,
            AIProvider.HUGGINGFACE
        ]
        logger.info(f"Initialized {len(self.providers)} AI providers")
    
    def _initialize_providers(self) -> Dict[AIProvider, Any]:
        """Initialize all available providers"""
        providers = {}
        
        # Groq
        if os.getenv("GROQ_API_KEY"):
            try:
                providers[AIProvider.GROQ] = OpenAI(
                    api_key=os.getenv("GROQ_API_KEY"),
                    base_url=ProviderConfig.GROQ["base_url"]
                )
                logger.info("✓ Groq provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Groq: {e}")
        
        # Gemini
        if os.getenv("GOOGLE_API_KEY"):
            providers[AIProvider.GEMINI] = {
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "config": ProviderConfig.GEMINI
            }
            logger.info("✓ Gemini provider initialized")
        
        # OpenRouter
        if os.getenv("OPENROUTER_API_KEY"):
            try:
                providers[AIProvider.OPENROUTER] = OpenAI(
                    api_key=os.getenv("OPENROUTER_API_KEY"),
                    base_url=ProviderConfig.OPENROUTER["base_url"]
                )
                logger.info("✓ OpenRouter provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenRouter: {e}")
        
        # DeepSeek
        if os.getenv("DEEPSEEK_API_KEY"):
            try:
                providers[AIProvider.DEEPSEEK] = OpenAI(
                    api_key=os.getenv("DEEPSEEK_API_KEY"),
                    base_url=ProviderConfig.DEEPSEEK["base_url"]
                )
                logger.info("✓ DeepSeek provider initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize DeepSeek: {e}")
        
        # HuggingFace
        if os.getenv("HUGGINGFACE_API_KEY"):
            providers[AIProvider.HUGGINGFACE] = {
                "api_key": os.getenv("HUGGINGFACE_API_KEY"),
                "config": ProviderConfig.HUGGINGFACE
            }
            logger.info("✓ HuggingFace provider initialized")
        
        return providers
    
    def generate(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate text using the first available provider
        Automatically falls back to next provider if one fails
        """
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        
        for provider_type in self.provider_priority:
            if provider_type not in self.providers:
                continue
            
            try:
                logger.info(f"Trying provider: {provider_type.value}")
                response = self._call_provider(provider_type, messages, max_tokens, temperature)
                if response:
                    logger.info(f"✓ Success with {provider_type.value}")
                    return response
            except Exception as e:
                logger.warning(f"Provider {provider_type.value} failed: {e}")
                continue
        
        logger.error("All AI providers failed")
        return None
    
    def _call_provider(
        self,
        provider_type: AIProvider,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Optional[str]:
        """Call a specific provider"""
        
        if provider_type == AIProvider.GROQ:
            return self._call_openai_compatible(
                self.providers[provider_type],
                ProviderConfig.GROQ["model"],
                messages,
                max_tokens,
                temperature
            )
        
        elif provider_type == AIProvider.GEMINI:
            return self._call_gemini(messages, max_tokens, temperature)
        
        elif provider_type == AIProvider.OPENROUTER:
            return self._call_openai_compatible(
                self.providers[provider_type],
                ProviderConfig.OPENROUTER["model"],
                messages,
                max_tokens,
                temperature
            )
        
        elif provider_type == AIProvider.DEEPSEEK:
            return self._call_openai_compatible(
                self.providers[provider_type],
                ProviderConfig.DEEPSEEK["model"],
                messages,
                max_tokens,
                temperature
            )
        
        elif provider_type == AIProvider.HUGGINGFACE:
            return self._call_huggingface(messages, max_tokens, temperature)
        
        return None
    
    def _call_openai_compatible(
        self,
        client: OpenAI,
        model: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Optional[str]:
        """Call OpenAI-compatible API"""
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        return response.choices[0].message.content
    
    def _call_gemini(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Optional[str]:
        """Call Google Gemini API"""
        config = self.providers[AIProvider.GEMINI]
        api_key = config["api_key"]
        model = ProviderConfig.GEMINI["model"]
        
        # Convert messages to Gemini format
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        
        url = f"{ProviderConfig.GEMINI['base_url']}/models/{model}:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }
        
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    
    def _call_huggingface(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Optional[str]:
        """Call HuggingFace Inference API"""
        config = self.providers[AIProvider.HUGGINGFACE]
        api_key = config["api_key"]
        model = ProviderConfig.HUGGINGFACE["model"]
        
        # Convert messages to single prompt
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        
        url = f"{ProviderConfig.HUGGINGFACE['base_url']}/{model}"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False
            }
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        return data[0]["generated_text"]
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return [provider.value for provider in self.providers.keys()]
    
    def get_provider_info(self, provider_type: AIProvider) -> Dict[str, Any]:
        """Get information about a specific provider"""
        configs = {
            AIProvider.GROQ: ProviderConfig.GROQ,
            AIProvider.GEMINI: ProviderConfig.GEMINI,
            AIProvider.OPENROUTER: ProviderConfig.OPENROUTER,
            AIProvider.DEEPSEEK: ProviderConfig.DEEPSEEK,
            AIProvider.HUGGINGFACE: ProviderConfig.HUGGINGFACE
        }
        return configs.get(provider_type, {})


# Global instance
_multi_provider_ai = None


def get_multi_provider_ai() -> MultiProviderAI:
    """Get or create the global MultiProviderAI instance"""
    global _multi_provider_ai
    if _multi_provider_ai is None:
        _multi_provider_ai = MultiProviderAI()
    return _multi_provider_ai

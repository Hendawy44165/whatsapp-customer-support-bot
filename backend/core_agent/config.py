"""
Shared configuration — model factory and prompt loader.
Nodes import from here to avoid circular imports with graph.py.
"""

import os
from functools import lru_cache
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_HERE, "prompts")


@lru_cache(maxsize=10)
def _get_cached_model(api_key: str, base_url: str, model_name: str) -> ChatOpenAI:
    """Helper to return a cached ChatOpenAI instance for specific credentials/model."""
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model_name,
    )


def get_model() -> ChatOpenAI:
    """Get the shared LLM instance, supporting dynamic model changes via environment variables."""
    api_key = os.getenv("PROVIDER_API_KEY")
    base_url = os.getenv("PROVIDER_BASE_URL", "https://models.github.ai/inference")
    model_name = os.getenv("PROVIDER_MODEL_NAME", "openai/gpt-4.1-mini")
    
    if not api_key:
        raise ValueError("PROVIDER_API_KEY environment variable is not set.")
        
    return _get_cached_model(api_key, base_url, model_name)


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = os.path.join(_PROMPTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

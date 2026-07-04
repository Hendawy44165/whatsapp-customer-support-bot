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


@lru_cache(maxsize=1)
def get_model() -> ChatOpenAI:
    """Get the shared LLM instance (singleton). Single model for now."""
    return ChatOpenAI(
        api_key=os.getenv("PROVIDER_API_KEY"),
        base_url=os.getenv("PROVIDER_BASE_URL", "https://models.github.ai/inference"),
        model=os.getenv("PROVIDER_MODEL_NAME", "openai/gpt-4.1-mini"),
    )


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = os.path.join(_PROMPTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

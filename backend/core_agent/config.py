import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROMPTS_DIR = os.path.join(_HERE, "prompts")

THREAD_ID = "498wa1d6s5af4"


def get_model():
    """Get the shared LLM instance, supporting dynamic model changes via environment variables."""
    api_key = os.getenv("PROVIDER_API_KEY")
    base_url = os.getenv("PROVIDER_BASE_URL")
    model = os.getenv("PROVIDER_MODEL_NAME")
    model_provider = os.getenv("MODEL_PROVIDER")

    return init_chat_model(
        model=model,
        api_key=api_key,
        model_provider=model_provider,
        base_url=base_url,
    )


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ directory."""
    path = os.path.join(_PROMPTS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Prompt file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()

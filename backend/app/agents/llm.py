from langchain_openai import ChatOpenAI

from app.core.config import settings


def chat_client(*, temperature: float = 0.2) -> ChatOpenAI:
    """Build a ChatOpenAI client from app settings.
    Args:
        temperature: The temperature of the model.
    Returns:
        A ChatOpenAI client.
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=temperature,
    )

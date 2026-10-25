"""Azure OpenAI provider setup for pydantic-ai agents.

Two models, because the tutor runs two paths with opposite priorities:

* **hot** (`chat_model`) — the reply the student is waiting to hear. Cheap and
  fast wins; a smarter model that takes an extra second is a worse tutor.
* **cold** (`analysis_model`) — memory extraction, grammar feedback, titles.
  Runs detached after the reply is already streaming, so nobody is waiting and
  quality wins.

Both are built lazily. Constructing `AsyncAzureOpenAI` with an empty endpoint
raises, and the app must still boot without a key so `/api/health` can report
`tutor_configured: false` instead of crashing on import.
"""

from functools import cache

import httpx
from openai import AsyncAzureOpenAI
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.openai import OpenAIProvider

from src.core.config import settings
from src.core.exceptions import TutorUnavailable


@cache
def _client() -> AsyncAzureOpenAI:
    if not settings.azure_configured:
        raise TutorUnavailable()
    return AsyncAzureOpenAI(
        azure_endpoint=settings.AZURE_LLM_ENDPOINT,
        api_version=settings.AZURE_LLM_API_VERSION,
        api_key=settings.AZURE_LLM_API_KEY,
        http_client=httpx.AsyncClient(
            timeout=float(settings.AGENT_TIMEOUT_S),
            trust_env=settings.AZURE_LLM_TRUST_ENV,
        ),
    )


def reasoning_settings(effort: str) -> OpenAIChatModelSettings | None:
    """Model settings for one reasoning effort, or None to leave it unset."""
    if not effort:
        return None
    return OpenAIChatModelSettings(openai_reasoning_effort=effort)


@cache
def chat_model() -> OpenAIChatModel:
    """Hot path — conversational replies."""
    return OpenAIChatModel(
        settings.AZURE_LLM_MODEL,
        provider=OpenAIProvider(openai_client=_client()),
        settings=reasoning_settings(settings.AZURE_LLM_REASONING_EFFORT),
    )


@cache
def analysis_model() -> OpenAIChatModel:
    """Cold path — structured extraction. Falls back to the chat deployment so
    a single-deployment Azure resource still works out of the box."""
    return OpenAIChatModel(
        settings.AZURE_LLM_ANALYSIS_MODEL or settings.AZURE_LLM_MODEL,
        provider=OpenAIProvider(openai_client=_client()),
        settings=reasoning_settings(settings.AZURE_LLM_ANALYSIS_REASONING_EFFORT),
    )

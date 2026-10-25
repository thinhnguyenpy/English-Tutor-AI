"""Cold-path agents for conversation titles and rolling summaries.

Both run on the analysis deployment but at the light reasoning effort: a
title or a summary does not get better with more hidden reasoning, only
slower and dearer.
"""

from pydantic_ai import Agent

from src.agents.base import analysis_model, reasoning_settings
from src.agents.prompts.memory_prompts import SUMMARY_PROMPT, TITLE_PROMPT
from src.core.config import settings


def build_title_agent() -> Agent[None, str]:
    return Agent(
        analysis_model(),
        instructions=TITLE_PROMPT,
        output_type=str,
        model_settings=reasoning_settings(settings.AZURE_LLM_LIGHT_REASONING_EFFORT),
    )


def build_summary_agent() -> Agent[None, str]:
    return Agent(
        analysis_model(),
        instructions=SUMMARY_PROMPT,
        output_type=str,
        model_settings=reasoning_settings(settings.AZURE_LLM_LIGHT_REASONING_EFFORT),
    )

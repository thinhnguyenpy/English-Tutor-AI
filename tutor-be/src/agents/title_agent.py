"""Cold-path agents for conversation titles and rolling summaries."""

from pydantic_ai import Agent

from src.agents.base import analysis_model
from src.agents.prompts.memory_prompts import SUMMARY_PROMPT, TITLE_PROMPT


def build_title_agent() -> Agent[None, str]:
    return Agent(analysis_model(), instructions=TITLE_PROMPT, output_type=str)


def build_summary_agent() -> Agent[None, str]:
    return Agent(analysis_model(), instructions=SUMMARY_PROMPT, output_type=str)

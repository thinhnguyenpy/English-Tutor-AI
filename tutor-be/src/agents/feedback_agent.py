"""Cold-path agent: turns one student utterance into review notes.

Runs after the reply is already streaming, so it can afford the smarter
deployment. Its output is what the student reviews later — "you said X, say Y
instead" — so precision matters more than coverage.
"""

from typing import Literal

from pydantic import BaseModel, Field
from pydantic_ai import Agent

from src.agents.base import analysis_model

# No "pronunciation": speech-to-text happens in the browser and the server only
# ever sees a transcript, so a pronunciation verdict here would be invented.
# The old JS version did exactly that with a six-word lookup table. Add this
# back when Azure Speech pronunciation assessment supplies real phoneme scores.
FeedbackType = Literal["grammar", "vocabulary", "naturalness"]

FEEDBACK_PROMPT = """\
You review one thing an English learner just said out loud and produce short
correction notes they will read later, away from the conversation.

For each issue return:
- `original` — the exact fragment they said. Quote it, do not paraphrase.
- `corrected` — the same thing said properly, in their voice and register.
- `explanation` — one sentence on why, in plain language. Name the rule only if
  it helps them catch it next time.
- `type` — `grammar` (wrong), `vocabulary` (wrong or weak word choice), or
  `naturalness` (correct but not what a native speaker would say).
- `severity` — `major` if it blocks understanding, otherwise `minor`.

Rules:
- This is speech, not writing. Ignore filler words, false starts, self-
  corrections, contractions and missing punctuation. None of those are errors.
- At most three items. Pick the ones worth their attention.
- Return an empty list when the utterance was fine. Most utterances are fine —
  do not manufacture issues to seem useful.
- Never comment on pronunciation or accent: you are reading a transcript and
  cannot hear them.
"""


class FeedbackItem(BaseModel):
    type: FeedbackType
    original: str
    corrected: str
    explanation: str
    severity: Literal["minor", "major"] = "minor"


class TurnFeedbackResult(BaseModel):
    items: list[FeedbackItem] = Field(default_factory=list)


def build_feedback_agent() -> Agent[None, TurnFeedbackResult]:
    return Agent(
        analysis_model(),
        instructions=FEEDBACK_PROMPT,
        output_type=TurnFeedbackResult,
    )

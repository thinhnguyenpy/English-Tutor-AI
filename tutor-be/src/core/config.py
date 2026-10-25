from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root (tutor-be/), so relative paths in .env resolve the same no matter
# which directory uvicorn was launched from.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DEBUG: bool = False

    # --- Database ------------------------------------------------------------
    # SQLite, not Postgres: this app runs locally for a single user, so there is
    # no concurrent-writer problem for SQLite to lose. Alembic and SQLAlchemy
    # async work unchanged over aiosqlite.
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'tutor.db'}"

    # --- Azure OpenAI --------------------------------------------------------
    # Two deployments with different jobs. The hot path runs while the student
    # is waiting to hear a reply, so it wants cheap + fast. The cold path
    # (memory extraction, grammar feedback, titles) runs detached after the
    # reply is already streaming, so latency is irrelevant and quality wins.
    AZURE_LLM_ENDPOINT: str = ""
    AZURE_LLM_API_KEY: str = ""
    AZURE_LLM_MODEL: str = ""
    AZURE_LLM_ANALYSIS_MODEL: str = ""
    AZURE_LLM_API_VERSION: str = ""
    AZURE_LLM_TRUST_ENV: bool = False
    # Reasoning effort per path. Reasoning models (gpt-5 family) default to
    # "medium", which on gpt-5-mini cost 5-7s before the first token and spent
    # ~90% of output tokens on hidden reasoning. The hot path wants none of it;
    # feedback and memory extraction gain precision from a little; titles and
    # summaries do not. Empty means "do not send the parameter" — required for
    # non-reasoning deployments, which reject it.
    AZURE_LLM_REASONING_EFFORT: str = "minimal"
    AZURE_LLM_ANALYSIS_REASONING_EFFORT: str = "low"
    AZURE_LLM_LIGHT_REASONING_EFFORT: str = "minimal"
    AGENT_TIMEOUT_S: int = 60

    # --- Tutoring behaviour --------------------------------------------------
    # Sidebar shows this many active conversations. Creating one past the cap
    # archives the least-recently-active; nothing is ever deleted.
    MAX_ACTIVE_CONVERSATIONS: int = 15
    # Student turns per conversation. The last one gets a wrap-up instruction;
    # past it the tutor refuses and the student starts a fresh conversation.
    # Bounds the per-conversation transcripts the cold path re-reads.
    MAX_TURNS_PER_CONVERSATION: int = 30
    # Verbatim messages (not exchanges) replayed into the prompt, capped twice:
    # by count, and by characters so one long monologue cannot blow up every
    # later prompt. Anything older is represented by the rolling summary.
    RECENT_TURNS_IN_CONTEXT: int = 10
    HISTORY_CHAR_BUDGET: int = 6000  # ≈ 1500 tokens
    # One utterance. Speech rarely gets near this; a pasted essay would. Longer
    # turns are refused with an error, never truncated silently.
    MAX_TURN_CHARS: int = 1000
    # Cold-path cadence: re-summarize + re-extract memories every N user turns.
    COLD_PASS_EVERY_N_TURNS: int = 6

    # --- Application ---------------------------------------------------------
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    CORS_HEADERS: list[str] = ["*"]

    @property
    def azure_configured(self) -> bool:
        """False means every agent call is skipped and the UI is told it is in
        demo mode. The old Node server silently returned canned replies here,
        which made a missing key look like a bad model."""
        return bool(self.AZURE_LLM_ENDPOINT and self.AZURE_LLM_API_KEY and self.AZURE_LLM_MODEL)


settings = Settings()

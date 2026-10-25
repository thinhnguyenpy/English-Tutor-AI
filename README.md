# English Tutor AI 🎤

A local AI English tutor you talk to out loud. It replies out loud, and — the part that makes it useful — **it remembers you between conversations**: your job, the exam you have next month, the mistakes you keep making.

![Python](https://img.shields.io/badge/Python-3.13-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688)
![React](https://img.shields.io/badge/React-18-61dafb)
![License](https://img.shields.io/badge/License-MIT-yellow)

Runs entirely on your own machine. One user, one laptop, one SQLite file.

## What it does

- **Free conversation.** Press the mic and talk about anything, or pick from twelve preset topics when you don't know where to start.
- **It remembers.** After a few turns the tutor quietly extracts durable facts about you and carries them into every future conversation. Start a brand-new chat weeks later and it still knows where you work and how the exam went.
- **Review notes.** Corrections appear a few seconds after you speak — *you said X, say Y instead* — without interrupting the conversation.
- **Fifteen conversations** stay in the sidebar. Resume any of them at any time. Older ones are archived, never deleted, and what the tutor learned from them stays.
- **Five tutor personalities** — conversation partner, grammar tutor, pronunciation coach, vocabulary builder, fluency coach.

## Requirements

- **Python 3.13** and [`uv`](https://docs.astral.sh/uv/) — `uv python install 3.13` handles the interpreter
- **Node 18+**
- An **Azure OpenAI** resource with a chat deployment
- A **Chromium-based browser** (Chrome, Edge, Brave) — speech recognition uses the Web Speech API

## Setup

```bash
# Backend
cd tutor-be
cp .env.example .env          # fill in the AZURE_LLM_* block
make install
make upgrade                  # creates data/tutor.db
make run                      # :8000

# Frontend, in a second terminal
cd tutor-fe
npm install
npm run dev                   # :5173
```

Open **http://localhost:5173**.

Without an Azure key the app still runs, but the tutor refuses turns and shows a banner saying so — it will not fake replies at you.

### Configuration

Everything lives in `tutor-be/.env`. The ones that matter:

| Variable | What it does |
|---|---|
| `AZURE_LLM_ENDPOINT` / `AZURE_LLM_API_KEY` / `AZURE_LLM_API_VERSION` | Your Azure resource |
| `AZURE_LLM_MODEL` | Deployment for conversation replies — pick something cheap and fast |
| `AZURE_LLM_ANALYSIS_MODEL` | Deployment for memory extraction and corrections — pick something smarter; nobody is waiting on it |
| `MAX_ACTIVE_CONVERSATIONS` | Sidebar size, default 15 |
| `COLD_PASS_EVERY_N_TURNS` | How often memories and summaries refresh, default 6 |

## How it works

```
browser speech-to-text ──ws──> hot path:  reply, streamed back token by token
                                  │
                                  └─ detached ─> cold path: corrections, memory, title, summary
```

Speech-to-text and text-to-speech both run **in the browser**. The server never receives audio, only the transcript.

The split matters: the reply has to arrive in about a second, so it runs on a cheap fast model with everything it needs already in the prompt. Memory extraction and grammar analysis run afterwards on a smarter model, detached, where taking five seconds costs nothing and a failure can't touch the conversation.

## Project layout

```
tutor-be/    FastAPI + SQLAlchemy + Alembic + pydantic-ai      (see tutor-be/CLAUDE.md)
tutor-fe/    Vite + React + TypeScript + Tailwind              (see tutor-fe/CLAUDE.md)
```

## Development

```bash
cd tutor-be
make lint     # ruff
make test     # pytest
make migrate "describe your change"

cd tutor-fe
npm run lint  # tsc --noEmit
npm run build
```

## Not built yet

Talking to the tutor from your phone by scanning a QR code, offline review notes on the phone, server-side speech recognition with real pronunciation scoring, and Docker packaging.

The phone part has one real blocker worth knowing about: browsers only allow microphone access on `localhost` or HTTPS, so a plain `http://192.168.x.x` LAN address will not work no matter what. It needs a trusted certificate on the local network.

## License

MIT — see [LICENSE.md](LICENSE.md).

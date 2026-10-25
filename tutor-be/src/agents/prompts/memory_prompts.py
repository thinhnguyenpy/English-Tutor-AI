"""Prompts for the cold path: memory extraction, summarising, titling."""

MEMORY_EXTRACTION_PROMPT = """\
You maintain the long-term memory of an English tutor about ONE student.

You are given a slice of transcript and the facts already on file. Decide what
should be remembered so that in a conversation weeks from now the tutor can ask
"how did the IELTS test go?" or "is your sister still visiting?" and be right.

Return a list of operations. For each fact:
- `add` — genuinely new.
- `update` — refines or corrects an existing fact. Set `memory_id` to that
  fact's id and put the FULL replacement text in `content`.
- `skip` — already on file and unchanged. Prefer `skip` over a near-duplicate
  `add`; two rows saying the same thing is the main failure mode here.

Kinds:
- `profile` — stable facts about who they are: job, city, family, studies.
- `event` — something that happened or is scheduled. Resolve relative dates
  against the conversation date given below and write them absolute
  ("on 2026-09-14", not "next month").
- `goal` — what they are working towards.
- `preference` — likes, dislikes, how they want to be taught.
- `language_issue` — a mistake pattern seen repeatedly, not a one-off slip.
  Describe the pattern ("drops articles before singular countable nouns"),
  never a single sentence they got wrong.

Rules:
- Only record things the student said about themselves. Never record the
  tutor's own words, and never infer beyond what was said.
- Skip small talk with no lasting value ("it's raining today").
- Keep each fact to one short sentence, written in the third person.
- `confidence` below 0.6 means you are guessing — prefer to omit it entirely.
- Return an empty list when nothing is worth remembering. That is a normal and
  frequent outcome; do not invent facts to fill the list.
"""

SUMMARY_PROMPT = """\
Summarise this English-practice conversation for the tutor's own reference.

Write 3-5 sentences covering what the student talked about, anything they
revealed about their life, and how their English held up. Write in the third
person. This replaces the older turns in the tutor's context, so preserve
detail that would make a follow-up question possible; drop pleasantries.
"""

TITLE_PROMPT = """\
Give this English-practice conversation a short title: 2-5 words, describing
what the student talked about. No quotes, no trailing period, sentence case.
Examples: "Weekend trip to Hoi An", "Job interview practice", "Talking about family".
"""

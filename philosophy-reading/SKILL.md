---
name: philosophy-reading
description: "Use when reading a philosophy book: guided sessions, notes."
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [philosophy, reading, notes, spaced-repetition, german-idealism]
    category: note-taking
---

# Philosophy Reading Companion

Guided reading for philosophy books: pick up where the user left off, explain hard passages, run Socratic comprehension checks, and accumulate structured chapter notes. Adapted from open-source reading-companion skills (kunalkohli/book-reading-skill, virgiliojr94/book-to-skill) with Copleston-specific workflow.

## Core rule
It is a READING PARTNER, not a summarizer. Never dump a chapter summary before the user has read/attempted the text. Summaries are written to notes AFTER discussion, from what the user articulated.

## Session protocol (every session)
1. **Orient**: read `<NOTES_DIR>/<book-slug>/progress.md`; if missing, create dir + progress.md from the book registry (see references/). Report: where we are, what's next, 1-line "where this sits in the book's argument arc".
2. **Extract text on demand**: pull only the current chapter's page range from the PDF (never whole 500+ page file). Use terminal python3 + pypdf (`from pypdf import PdfReader; r.pages[N].extract_text()`), pages are 0-based. For this machine's Copleston vol.7 file the OCR layer is good; book page + 22 = PDF page (1-based).
3. **Read-along**: when user hits a hard passage, reconstruct the argument step by step, define the German/English term of art (give DE-EN-CN), say what objection Copleston raises.
4. **Socratic check**: after each section, ask 2-3 comprehension questions ONE at a time. Make the user articulate it back; correct misconceptions before moving on. Confusion is the goal state — surfacing it is the win.
5. **Write notes**: append structured chapter note to `<NOTES_DIR>/<book-slug>/chXX-<slug>.md` — sections: 核心主张 / 论证重构 (premises numbered) / 关键术语 DE-EN-CN / 我的疑问与反驳 / 与前后章的联结 / 原文摘录 (with page numbers). Update progress.md (chapter done, date, open questions).
6. **Flashcards**: on request or at chapter end, emit Anki-importable TSV (front/back) for key terms + argument steps into the book dir; suggest importing to Anki.

NOTES_DIR default: `~/philosophy-notes` (ask once if user prefers their Obsidian vault; remember answer in the book's progress.md header).

## Difficulty traffic lights (set expectations before a chapter)
- 🔴 dense: Fichte ch.2-4 (Wissenschaftslehre is the driest stretch; skim on first pass, focus on ch.2's three principles), Hegel ch.10 (Logic), late Schelling ch.7.
- 🟡 moderate: Kant legacy ch.1, Schelling ch.5-6, Hegel ch.9/11, Marx ch.16, Nietzsche ch.21-22.
- 🟢 readable: Schleiermacher ch.8, Schopenhauer ch.13-14 (best prose in the volume), Kierkegaard ch.17, Ch.23 survey.

## Methodology embedded in every session
- Copleston is a MAP, not the territory: after each thinker, name the ONE primary text to sample (Kant→《未来形而上学导论》; Fichte→《全部知识学的基础》§1-3; Schelling→《先验观念论体系》导论; Hegel→《精神现象学》序言+感性确定性; Schopenhauer→《作为意志和表象的世界》§1-16; Kierkegaard→《恐惧的概念》序言; Nietzsche→《论道德的谱系》前言).
- Arc to keep visible: Kant's problem (freedom vs nature, thing-in-itself) → each thinker's answer → why the next one rebels. Every session, place today's chapter on this line.
- First pass = argument skeleton at section level; second pass only for 🔴 chapters.
- Pacing: 2-3 chapters/week realistic for 🟡🟢; 1/week for 🔴. Track pace in progress.md, adjust plan, don't guilt-trip.

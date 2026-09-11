# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This file covers **how the code is written**. For *what* to build, see `MISSION.md`. For *how the factory operates*, see `FACTORY_RULES.md`. When these conflict: MISSION.md wins on scope, FACTORY_RULES.md wins on process, CLAUDE.md wins on code style. All three are protected files (FACTORY_RULES.md §5) — factory workflows must never modify them; only a human commit may.

---

## What This Repo Is

Two things live here:

1. **DynaChat** (`app/`) — a RAG chat app over a single YouTube channel's transcripts. FastAPI + Python backend, React + Vite + TypeScript frontend, SQLite (Postgres migration planned). Streaming answers with citations.
2. **The Dark Factory** (`.archon/`, `contracts/`, `feedback/`, `progress.json`) — Archon workflows that triage GitHub issues, implement fixes in isolated worktrees, validate PRs, and auto-merge. `.archon/commands/*.md` are the agent prompts; `.archon/workflows/*.yaml` wire them together. `contracts/` and `feedback/` are sprint-planning artifacts from the initial build, not runtime code.

Most tasks touch only `app/`. Read `MISSION.md` and `FACTORY_RULES.md` before any non-trivial change.

---

## Commands

### Backend (run from `app/backend/` unless noted)

```bash
cd app/backend
uv sync --all-extras                 # creates .venv, installs runtime + dev deps (ruff, mypy, pytest)

uv run ruff check .                  # lint
uv run ruff check --fix .            # lint autofix
uv run ruff format --check .         # format check (use `uv run ruff format .` to apply)
uv run mypy .                        # type check
uv run pytest tests -xvs             # all tests
uv run pytest tests/test_version.py -xvs                                   # one file
uv run pytest tests/test_version.py::test_version_endpoint_returns_200 -xvs  # one test
```

Run the dev server from `app/` (not `app/backend/`) — the `backend.main:app` import path requires it:

```bash
cd app
uv --project backend run uvicorn backend.main:app --reload --port 8000
```

Tooling (ruff/mypy/pytest) must run from `app/backend/` so `pyproject.toml` config is picked up. Running them from `app/` with `--project backend` silently loses the exclude lists and `asyncio_mode = "auto"`.

### Frontend (run from `app/frontend/`)

```bash
cd app/frontend
bun install                          # bun only — not npm/pnpm/yarn
bun run dev                          # Vite dev server on :5173, proxies /api → :8000
bun run build                        # tsc && vite build → dist/
bun run tsc --noEmit                 # type check (also: bun run type-check)
bun x biome check src                # lint + format check (bun run lint)
bun x biome check --apply src        # autofix
bun run test                         # vitest run (all)
bun x vitest run src/components/Foo.test.tsx   # one file
bun x vitest run -t "renders sources"          # one test by name
```

**Gotcha:** `bun run test` exits 1 with "No test files found" while there are zero frontend test files. Vitest, jsdom, and Testing Library are already installed and configured (`vitest.config.ts`, `src/__tests__/setup.ts`); the first PR that adds a `*.test.tsx` makes this pass.

### Everything at once

```bash
cd app && ./start.sh      # uv sync → seed DB → uvicorn :8000 + vite :5173 (start.bat on Windows)
```

`start.sh` copies a repo-root `.env` into `app/.env` if present. The README's "Manual start" section (python -m venv / pip / requirements.txt) is stale — use the uv commands above.

### What the validator runs before merge

```bash
cd app/backend && uv run ruff check . && uv run ruff format --check . && uv run mypy . && uv run pytest tests -xvs
cd app/frontend && bun run tsc --noEmit && bun x biome check src && bun run test
```

Plus the agent-browser end-to-end regression (FACTORY_RULES.md §4, skill at `.claude/skills/agent-browser/SKILL.md`). Run all of it before declaring a PR done.

---

## Architecture

### Request flow for a chat message

`POST /api/conversations/{id}/messages` in `routes/messages.py` orchestrates the whole RAG pipeline in one handler:

1. Persist the user message (`db/repository.py`)
2. Load full conversation history for the LLM
3. `rag/embeddings.embed_text()` embeds the query via OpenRouter
4. `rag/retriever.retrieve()` loads **every** chunk embedding from SQLite into NumPy and returns the top-5 by cosine similarity, joined with video titles
5. `llm/openrouter.stream_chat()` streams `anthropic/claude-sonnet-4.6` with the chunks injected into the system prompt
6. The route intercepts `data: [DONE]` to emit the `sources` event first, then persists the assistant text (reconstructed from the SSE chunks) and auto-titles the conversation on first reply

Retrieval failures are swallowed (logged, answer continues without context). LLM errors before the first token raise; after the first token they arrive as a `data: {"error": ...}` SSE payload.

### Ingest and seeding

`POST /api/ingest` and `data/seed.py` share the same pipeline: create video row → `rag/chunker.chunk_video()` → `rag/embeddings.embed_batch()` → one `chunks` row per chunk with the embedding stored as a JSON-encoded float array in a TEXT column. Seeding runs in the FastAPI lifespan on every startup: full seed if no videos, chunk-and-embed if videos exist without chunks, skip otherwise. Because seeding calls the embeddings API, starting without `OPENROUTER_API_KEY` yields 10 videos and 0 chunks; the next startup with a key backfills the chunks.

Chunking uses Docling `HybridChunker` with a tiktoken `cl100k_base` `OpenAITokenizer` (matching `text-embedding-3-small`), `max_tokens=512`, plus a post-pass that hard-splits any chunk over 2400 chars and guarantees ≥2 chunks for ≥3-paragraph transcripts.

### SSE wire format (frontend parser depends on this exactly)

- Token: `data: <JSON-encoded string>\n\n` — tokens are JSON strings (quoted, escaped) so newlines survive
- Sources: `event: sources\ndata: <JSON array>\n\n`, emitted **before** the terminator
- Terminator: `data: [DONE]\n\n`
- Mid-stream error: `data: {"error": "..."}\n\n`

`useStreamingResponse.ts` is the only SSE consumer and the one sanctioned inline `fetch()` outside `lib/api.ts`. Do not parse SSE anywhere else. Change both sides together or not at all.

**Current gap vs. MISSION.md:** the `sources` array is currently a list of video-title strings. MISSION.md's quality bar (and the §4 regression test) require citations with title, URL, timestamp deep-link, and transcript snippet, plus a modal with an embedded player at the timestamp. Likewise auth and the 25 msg/day rate limit are in MISSION.md but not implemented. Build toward these when an issue is filed; never regress a field once it exists.

### Frontend shape

`App.tsx` holds `BrowserRouter` with `/` and `/c/:conversationId` rendering the same `AppLayout` (Sidebar + ChatArea). State is plain hooks: `useConversations`, `useMessages`, `useStreamingResponse`, `useToast` (Context via `ToastProvider`). `lib/api.ts` holds every typed fetch wrapper and the shared interfaces (`Video`, `Conversation`, `Message`).

### Database

SQLite via `aiosqlite`, no ORM, no migrations. `db/schema.py` runs `CREATE TABLE IF NOT EXISTS` for `videos`, `chunks` (FK → videos, cascade), `conversations`, `messages` (FK → conversations, cascade, `role` CHECK) with `PRAGMA foreign_keys=ON` and `journal_mode=WAL`. Every query lives in `db/repository.py`; each function opens its own connection. IDs are text UUIDs; `repository._now()` writes ISO 8601 UTC strings.

### Other endpoints

`GET /api/health` (counts + db path), `GET /api/version` (package metadata; 503 if unavailable), `POST /api/stream-test` (streams a canned LLM reply to smoke-test SSE), `GET /api/videos`, `GET/POST/DELETE /api/conversations[/{id}]`.

---

## Placement Rules

- New API route → new file in `app/backend/routes/`, one per resource, mounted in `main.py` under `/api`. Pydantic request/response models live in the route file unless shared.
- New SQL → `app/backend/db/repository.py` only. Never in routes, services, or seed code.
- Schema change → `app/backend/db/schema.py`, `CREATE TABLE IF NOT EXISTS`, portable SQL (see Database rules).
- New RAG step → `app/backend/rag/`; keep chunker, embeddings, retriever separate.
- New env var → read once in `app/backend/config.py` as a module constant with a default; import the constant elsewhere.
- New React component → `app/frontend/src/components/`, one per file, named export matching filename.
- New hook → `app/frontend/src/hooks/`, `use` prefix, returns a typed object.
- New API call → `app/frontend/src/lib/api.ts`. Never `fetch()` in a component or new hook.
- Backend tests → `app/backend/tests/` (pattern in `test_version.py`: `httpx.AsyncClient(transport=ASGITransport(app=app))`, plain `async def`, no marker needed). Never touch `data/chat.db`; use `tmp_path` for a temp DB.
- Frontend tests → co-located `*.test.tsx` or `src/__tests__/`. Mock fetch with `vi.stubGlobal('fetch', ...)`.

---

## Code Conventions

### Python

- Async everywhere in routes and DB. Sync blocking calls in a handler are a bug — wrap in `asyncio.to_thread`. (Existing violation: `embed_text`/`embed_batch` use the sync `OpenAI` client and are called directly from `routes/messages.py` and `routes/ingest.py`. Fix only under an issue that covers it.)
- Type hints on every signature; builtin generics (`list[str]`, `dict | None`), not `typing.List`.
- `logging.getLogger(__name__)`, never `print()` in runtime code (`data/seed.py` and `config.py` startup warnings are the tolerated exceptions).
- Specific exceptions, never bare `except:`. `except Exception` only at the outermost handler boundary.
- Parameterized SQL with `?`; never f-string/`%` into SQL.
- Ruff: line-length 100, py311 target, rules E/F/W/I/B/UP/SIM/RUF, double quotes. Mypy: `strict = false`, `warn_return_any`, `warn_unused_ignores` (a stale `# type: ignore` fails the check).
- Python 3.11 is the floor (`requires-python = ">=3.11"`); don't use 3.12+ features.

### TypeScript

- Function components, named exports, one per file. Hooks only for state; no Redux/Zustand/Jotai.
- No `any` without a comment explaining the untyped bridge (biome warns on it).
- Biome: single quotes, semicolons, trailing commas, 2-space indent, line width 100, `organizeImports` on. `useExhaustiveDependencies` is disabled.
- Styling rule for new code: Tailwind utilities; inline `style={{}}` only for values Tailwind can't express. Be aware the existing components lean heavily on inline styles and custom classes from `styles/globals.css` (CSS variables, `.app-layout`, `.skeleton`, etc.). Match the local file's style when editing; don't refactor styling outside your issue's scope.
- Relative imports only (no path aliases configured).

---

## Database Rules (Postgres-portable from day one)

The Postgres migration is an allowed evolution once an issue is filed. Until then every new query must be a drop-in for both engines:

1. ANSI SQL only — no `json_extract()`, `strftime()`, or SQLite pragmas in queries.
2. Explicit `NOT NULL` / `CHECK` / types on every new column.
3. Timestamps as ISO 8601 TEXT written from Python (`_now()`), not DB-side defaults. The existing `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` columns predate this rule; don't copy the pattern.
4. Text UUID primary keys; no auto-increment integers.
5. No Alembic until the migration PR itself introduces it.

---

## RAG and Streaming Invariants (do not change without an authorizing issue)

1. Chunking: Docling `HybridChunker`, `HYBRID_CHUNKER_MAX_TOKENS = 512`. No LangChain/recursive splitters.
2. Embeddings: `openai/text-embedding-3-small` via OpenRouter (1536-dim). Never on the frontend.
3. Retrieval: in-process NumPy cosine, `RETRIEVAL_TOP_K = 5`. No vector DB (FAISS/Chroma/pgvector) without an explicit issue.
4. Chat: `anthropic/claude-sonnet-4.6` via the `openai` SDK at `https://openrouter.ai/api/v1`. Provider and model are out of scope per MISSION.md.
5. SSE format as described above.
6. Citation fields (title, URL, timestamp deep-link, snippet, modal player) are a MISSION.md quality bar — regressing any is an auto-reject.

---

## Configuration

`config.py` walks up parent directories from `app/backend/` and loads the first `.env` it finds. The only required variable is `OPENROUTER_API_KEY`; everything else (`OPENROUTER_BASE_URL`, `EMBEDDING_MODEL`, `CHAT_MODEL`, `DB_PATH`, `RETRIEVAL_TOP_K`, `HYBRID_CHUNKER_MAX_TOKENS`, `BACKEND_PORT=8000`, `FRONTEND_PORT=5173`) is a hardcoded constant there. No `.env.example` exists yet — create one only under an issue that asks for it.

**Security-invariant paths** (FACTORY_RULES.md §5 asks CLAUDE.md to name them): CORS is configured in `app/backend/main.py` (`CORSMiddleware`, origins `localhost:5173` / `127.0.0.1:5173`). Auth middleware and the 25 msg/day rate-limit constant do not exist yet; when added, list their paths here via a human commit and treat them as protected.

---

## Known Footguns

1. **Sync OpenAI client in async routes** (see Python conventions). Under load this blocks the event loop.
2. **Retriever loads the whole `chunks` table per query.** Fine for the 10-video seed; will not scale. Only address under an issue.
3. **`bun run test` fails with no test files** (exit 1). Not a broken toolchain.
4. **`bun.lock` is gitignored** (`.gitignore` lists it), so frontend installs are not fully reproducible. `uv.lock` *is* committed and authoritative for the backend; runtime deps are intentionally unpinned in `pyproject.toml` — don't add upper bounds.
5. **No `.env.example`** — see Configuration.
6. **README "Manual start" is stale** (pip/requirements.txt). The uv flow above is correct.
7. **Two `[DONE]` handling paths.** `routes/messages.py` injects `sources` by string-matching `"data: [DONE]\n\n"` from `stream_chat`; if you change the terminator in one place the sources event silently disappears.

---

## Commits and PRs

- Conventional commits (`feat:`, `fix:`, `chore:`, `refactor:`, `docs:`, `test:`), subject < 72 chars, body explains *why*.
- PR title uses the same prefix. PR body must follow `.github/pull_request_template.md` and contain `Fixes #N` on its own line — the validator extracts the linked issue from it and fails without one.
- One issue per PR, ≤ 500 changed lines, no protected files (`MISSION.md`, `FACTORY_RULES.md`, `CLAUDE.md`, `.github/**`, Dockerfiles/deploy configs, `.env*`, `.archon/config.yaml`).
- New dependencies need the template's "Dependencies" section filled in (FACTORY_RULES.md §2).
- Every bug fix ships a regression test; every feature ships tests. The validator reads only the PR body, diff, and test results (holdout principle, FACTORY_RULES.md §9) — if it isn't explained in the PR body, it isn't considered.
- Don't "improve" code outside the issue's scope; file a new issue instead. Scope discipline is enforced.

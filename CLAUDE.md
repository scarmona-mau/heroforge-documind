# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DocuMind is an AI-powered knowledge management system — a Q&A chatbot that answers questions from company documents using Claude, RAG, and agentic engineering. It is the course project for the HeroForge Agentic AI Engineering course (Sessions 3–10), built incrementally across sessions.

## Development Commands

```bash
# Initial setup
cp .env.example .env    # configure API keys
npm install             # install Node.js dependencies
pip install -r requirements.txt   # install Python dependencies

# Tests
npm test                # run Jest tests (JS)
npm run test:watch      # watch mode
pytest tests/           # run all Python tests
pytest tests/unit/pipeline/test_extractor.py   # run a single Python test file

# Lint
npm run lint            # ESLint on src/

# Launch Claude Code
dsp
```

## Architecture

This is a hybrid Python + Node.js project. Python is the primary application language; Node.js/Jest handle tooling and JS unit tests.

### Document Processing Pipeline (`src/agents/pipeline/`)

The core pipeline is composed of three agents coordinated by an orchestrator:

- **`OrchestratorAgent`** (`orchestrate.py`) — coordinates the pipeline sequentially (Session 3); upgraded to parallel `asyncio` in Session 5+. Entry point: run as `python -m src.agents.pipeline.orchestrate <file>`.
- **`ExtractorAgent`** (`extractor.py`) — extracts raw text from documents (TXT/MD in S3; PDF/DOCX added in S7).
- **`ChunkerAgent`** (`chunker.py`) — splits extracted text into overlapping word-based chunks (configurable `CHUNK_SIZE` / `CHUNK_OVERLAP`).
- **`WriterAgent`** (`writer.py`) — serializes chunks to JSON in the output directory.

### Application Layer (`src/documind/`)

- **`upload_handler.py`** — validates and ingests uploaded files with security hardening (path traversal prevention, symlink detection, extension allowlist, size limits). The `UPLOAD_BASE_DIR` env var sets the allowed base path.
- **`config.py`** — centralised application configuration loaded from `.env`.

### Session Progression

Each session adds a layer on top of the previous:

| Session | Capability added |
|---------|-----------------|
| S3 | Pipeline foundation (this branch) |
| S4 | Supabase/PostgreSQL persistence via MCP |
| S5 | Parallel multi-agent processing |
| S6 | RAG Q&A interface |
| S7 | PDF/DOCX parsing |
| S8 | pgvector semantic search |
| S9 | Conversation memory |
| S10 | RAGAS evaluation metrics |

## Claude Code Configuration (`.claude/`)

Hooks in `.claude/settings.json` run automatically:

| Event | Hook | What it does |
|-------|------|--------------|
| `SessionStart` | `SessionStart.sh`, `ValidateEnvironment.sh` | Prints welcome banner; checks `.env`, dirs, git status |
| `PostToolUse` (Write/Edit) | `FormatOnSave.sh` | Auto-formats saved files |
| `UserPromptSubmit` | `UserPromptSubmit.sh` | Pre-prompt processing |
| `Stop` | `Stop.sh` | Session teardown |

Custom agents live in `.claude/agents/` (doc-writer, security-reviewer). Custom skills live in `.claude/skills/`.

## Environment Variables

Required keys (set in `.env`):

| Key | When required |
|-----|--------------|
| `ANTHROPIC_API_KEY` | Session 3+ |
| `OPENAI_API_KEY` | Session 5+ (embeddings) |
| `SUPABASE_URL` / `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_KEY` / `SUPABASE_ACCESS_TOKEN` | Session 4+ |
| `OPENROUTER_API_KEY` | Session 6+ (optional) |

Application tunables: `DEBUG`, `LOG_LEVEL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `OUTPUT_DIR`, `UPLOAD_BASE_DIR`.

## Testing Layout

```
tests/
├── unit/pipeline/       # per-agent unit tests
├── integration/         # end-to-end pipeline tests (test_pipeline_e2e.py)
└── e2e/                 # full system tests (added in later sessions)
```

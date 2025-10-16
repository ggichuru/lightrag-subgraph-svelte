# LightRAG Backend

This FastAPI backend powers the Conversational Knowledge Graph application. It exposes REST and WebSocket APIs that sit on top of [LightRAG](https://github.com/LinkSoul-AI/LightRAG) to provide hybrid retrieval, conversational context tracking, and dynamic graph summaries.

## Features

- Async LightRAG integration with proper storage initialisation and cleanup
- REST endpoints for querying, graph retrieval, statistics, and document ingestion
- WebSocket endpoint for real-time conversational experiences
- Contextual subgraph generation with temporal decay and multi-factor node scoring
- Batch ingestion pipeline with status tracking and automatic graph reloads

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- OpenAI (or compatible) API credentials configured through environment variables

## Quick Start

```bash
cd backend
uv sync
cp .env.example .env  # update secrets
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`. A health check exists at `/api/health`.

## Environment Variables

All configuration is driven by environment variables (see `.env.example`). Important fields:

- `OPENAI_API_KEY` – Secret key used by LightRAG for LLM and embedding calls
- `LIGHTRAG_WORKING_DIR` – Directory where LightRAG stores graph artefacts
- `CORPUS_DIR` – Document corpus directory for ingestion
- `CORS_ORIGINS` – Frontend origins allowed to access the API

## Document Ingestion Workflow

1. Upload files via `POST /api/documents/upload` (supports `.txt`, `.md`, `.json`, `.pdf`, `.docx`)
2. Trigger ingestion with `POST /api/documents/ingest`
3. Poll progress at `GET /api/documents/ingest/status`

Ingestion runs asynchronously. When finished the backend refreshes entity caches and reloads the NetworkX graph from LightRAG storage.

## Running Tests

Integration with LightRAG requires valid model credentials. Start with a small corpus to verify ingestion and query flows. Example curl commands:

```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the project about?", "mode": "hybrid"}'
```

## Project Structure

```
src/
  api/            # FastAPI routes + websocket handler
  core/           # Configuration, LightRAG wrapper, graph manager
  models/         # Pydantic schemas
  utils/          # File parsing helpers
```


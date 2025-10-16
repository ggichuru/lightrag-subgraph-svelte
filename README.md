# Conversational Knowledge Graph with LightRAG + Svelte

This project delivers a production-ready conversational retrieval system that combines the reasoning power of [LightRAG](https://github.com/LinkSoul-AI/LightRAG) with a dynamic, conversation-aware knowledge graph visualised in Svelte.

Users can upload documents, ingest them into LightRAG, ask natural language questions, and watch a force-directed graph highlight the entities and relationships used to form each answer.

## Repository Layout

```
backend/   # FastAPI + LightRAG backend
frontend/  # SvelteKit frontend with D3 visualisation
scripts/   # Helper scripts (e.g. setup.sh)
docs/      # Project documentation portal
```

## Quick Start

```bash
./scripts/setup.sh
```

The setup script installs Python dependencies via `uv`, prepares LightRAG directories, creates a `.env` scaffold, and installs frontend packages.

### 1. Configure Environment

- Open `backend/.env` and set `OPENAI_API_KEY` (or another LightRAG-compatible provider).
- Adjust optional settings (`API_PORT`, `CORS_ORIGINS`, etc.) as needed. The default backend port is **8002** to avoid macOS conflicts; keep the frontend configuration in sync.
- (Optional) Drop initial documents into `backend/data/corpus` before ingestion.

### 2. Run the Backend

```bash
cd backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8002
```

REST base: `http://localhost:8002/api`

### 3. Run the Frontend

```bash
cd frontend
npm run dev -- --open
```

The SvelteKit dev server picks an available port starting at 5173. `frontend/.env.development` already points `VITE_API_URL` to `http://localhost:8002`, so the UI connects to the backend automatically.

### 4. Ingest Documents & Chat

1. Upload files through the UI or copy them into `backend/data/corpus`.
2. Trigger ingestion (UI button or `POST /api/documents/ingest`).
3. Monitor `GET /api/documents/ingest/status` until `status` becomes `completed`.
4. Start chatting—responses include a contextual subgraph rendered in real time.

## Documentation

The `docs/` directory contains detailed guides:

- [docs/README.md](docs/README.md) – Documentation hub + architecture overview
- [docs/concept.md](docs/concept.md) – The idea, what the UI reveals, and how the moving parts tell the story
- [docs/backend.md](docs/backend.md) – Backend internals, configuration, ingestion flow
- [docs/frontend.md](docs/frontend.md) – SvelteKit structure, state flow, D3 graph
- [docs/operations.md](docs/operations.md) – Operations, troubleshooting, deployment notes

## Key Features

- **Hybrid Retrieval:** LightRAG wrapper ensures storages initialise correctly, conversation history is maintained, and ingestion pipelines run asynchronously.
- **Contextual Graphs:** NetworkX-based graph manager builds contextual subgraphs using frequency, recency, centrality, and focal-entity weighting.
- **Real-Time UX:** WebSocket-powered chat, D3 force-directed visualisation, conversation stats, and ingestion progress updates.
- **Document Pipeline:** Drag-and-drop uploads, batch ingestion, status polling, and automatic graph reloads.

## Testing the Stack

Backend smoke tests:

```bash
curl http://localhost:8002/api/health
curl -X POST http://localhost:8002/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What does this system do?", "mode": "hybrid"}'
```

Frontend checks:

- Chat sends queries and receives responses.
- Graph animates and highlights focal entities.
- Stats panel updates after each question.
- Upload + ingest pipeline reports progress and refreshes the graph.

## Extending the Project

- Enhance entity extraction with NER or embeddings for fuzzy matching.
- Add graph filters (by type, weight, recency) or path-highlighting between entities.
- Introduce authentication to separate user corpora.
- Persist conversation history and export graph snapshots.

## License

Choose the license that fits your deployment needs (e.g. MIT, Apache 2.0). Update this section accordingly.

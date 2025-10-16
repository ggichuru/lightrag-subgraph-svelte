# Documentation Hub

Welcome to the Conversational Knowledge Graph documentation set. This guide helps you understand **what** the system does, **how** it is organised, and **how** to operate or extend it.

## Contents

- [Project Overview](#project-overview)
- [System Architecture](#system-architecture)
- [How to Run Everything](#how-to-run-everything)
- [Where to Go Next](#where-to-go-next)

## Project Overview

The project combines a FastAPI backend powered by LightRAG with a SvelteKit frontend to let users:

1. Upload and ingest documents into LightRAG.
2. Chat with the corpus using hybrid retrieval + graph reasoning.
3. Visualise the entities and relations that were relevant for each answer.

## System Architecture

```
┌─────────────┐      REST / WebSocket       ┌─────────────┐
│  SvelteKit  │◀──────────────────────────▶│   FastAPI   │
│  Frontend   │                            │   Backend   │
└──────┬──────┘                            └──────┬──────┘
       │   Graph + Chat Stores                    │
       │                                           │
       │                                   ┌───────▼────────┐
       │                                   │  LightRAG      │
       │                                   │  Knowledge     │
       │                                   │  Graph + RAG   │
       │                                   └───────┬────────┘
       │                                           │
       │                GraphML / Vector Stores    │
       └───────────────────────────────────────────┘
```

Key responsibilities:

- **Frontend** renders chat, graph visualisation (D3), ingestion flows, and statistics. It consumes REST and WebSocket APIs exposed by the backend.
- **Backend** orchestrates LightRAG queries, manages contextual graph filtering, and serves both REST endpoints and the chat WebSocket.
- **LightRAG** performs hybrid retrieval, embedding, knowledge graph management, and writes its graph to GraphML inside `backend/lightrag_storage`.

## How to Run Everything

Most tasks start from the repository root.

### 1. Install and Configure

```bash
./scripts/setup.sh
```

What the script does:

- Installs backend dependencies with `uv`.
- Installs frontend dependencies with `npm`.
- Creates `backend/.env` (fill in OpenAI-compatible credentials afterwards).
- Ensures `backend/data/corpus` and `backend/lightrag_storage` exist.

After the script:

1. Open `backend/.env` and set `OPENAI_API_KEY` plus any custom model/config overrides.
2. (Optional) drop documents into `backend/data/corpus` for ingestion.

### 2. Start the Backend

```bash
cd backend
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8002
```

- REST base: `http://localhost:8002/api`
- WebSocket: `ws://localhost:8002/ws`
- Health check: `GET /api/health`

> **Why port 8002?** Port 8000 is often busy on macOS (AirPlay/etc.). Using 8002 avoids conflicts. You can change `API_PORT` in `.env`; remember to update the frontend `VITE_API_URL` if you do.

### 3. Start the Frontend

```bash
cd frontend
npm run dev -- --open
```

- The dev server will try ports 5173, 5174, 5175, ... automatically.
- `frontend/.env.development` already points `VITE_API_URL` to `http://localhost:8002` so the UI talks to the backend without extra work.

### 4. Ingest Documents

1. Upload files via the **Document Upload** panel in the UI *or* copy them into `backend/data/corpus` manually.
2. Click **Start Ingestion** in the UI (or call `POST /api/documents/ingest`).
3. Watch progress in the panel or poll `GET /api/documents/ingest/status`.
4. Once completed, the backend reloads the GraphML and refreshes cached entities automatically.

> Encrypted PDFs are skipped with a clear error message. Decrypt them or provide a readable version before re-ingesting.

### 5. Chat and Explore

- Send a prompt in the chat panel. The backend maintains conversation history and builds a contextual subgraph around the relevant entities.
- The graph view animates to highlight nodes with high importance scores.
- The stats panel tracks query counts, most discussed entities, and response times.

## Where to Go Next

- Start with [docs/concept.md](concept.md) to understand the idea, what the UI reveals, and how the moving parts interact.
- Dive into [docs/backend.md](backend.md) for backend internals (config, ingestion, LightRAG wrapper, endpoints).
- Read [docs/frontend.md](frontend.md) to understand the Svelte stores, components, and D3 graph implementation.
- Check [docs/operations.md](operations.md) for troubleshooting, environment tweaks, and deployment notes.

If you prefer a printed guide, the documentation hierarchy is intentionally modular—pick the file that matches your current task.

# Frontend Guide

This document explains the SvelteKit frontend, how state flows through the app, and how to extend the visualisation or UI.

## Project Structure

```
frontend/
├── src/
│   ├── app.html               # HTML template (required for SvelteKit 2)
│   ├── app.css                # Tailwind entrypoint
│   ├── lib/
│   │   ├── components/        # Svelte components
│   │   ├── graph/             # D3 integration
│   │   ├── stores/            # Svelte stores (global state)
│   │   └── utils/             # API utilities
│   └── routes/
│       ├── +layout.svelte     # Global styles + document head
│       └── +page.svelte       # Main application shell
├── .env.development           # Dev-only env vars (VITE_API_URL)
├── package.json               # Dependencies and scripts
└── vite.config.js             # Vite settings + backend proxy
```

## Key Concepts

### State Management (`lib/stores/app.js`)

- `messages`: chat transcript.
- `graphData`: latest graph `{nodes, links}` payload for D3.
- `stats`: conversation analytics from `/api/stats`.
- `viewMode`: `'chat' | 'split' | 'graph'` toggled by `ViewToggle`.
- `isLoading`, `isIngesting`, `ingestStatus`: UI flags for pending operations.
- Derived stores provide handy helpers (`currentEntities`, `hasConversation`).

### API Layer (`lib/utils/api.js`)

All HTTP/WebSocket calls go through this module. `VITE_API_URL` defaults to `http://localhost:8002` (set in `.env.development`). Functions include:

- `sendQuery`, `loadFullGraph`, `loadStats`, `uploadDocument`, `startIngestion`, `getIngestionStatus`, `checkHealth`.
- `createWebSocket()` builds a `ws://` URL from `VITE_API_URL` or browser location fallback.
- Generic `request()` helper handles JSON responses and errors consistently.

### Components

| Component | Purpose |
| --------- | ------- |
| `ChatPanel.svelte` | Chat UI, WebSocket connection, fallback to REST when socket is unavailable, mode selector, entity badges. |
| `GraphPanel.svelte` | Hosts the D3 SVG canvas and renders the focus list. |
| `GraphStats.svelte` | Collapsible card with conversation metrics. |
| `DocumentUpload.svelte` | Drag-and-drop + file picker, ingestion status polling. |
| `ViewToggle.svelte` | Switch between chat, split, and graph-only layouts. |

### D3 Graph (`lib/graph/d3-graph.js`)

- Uses D3 force simulation with link distance, charge, and collision forces.
- `createGraph(svg, data)` initialises simulation and returns `{simulation, update, destroy}`.
- `updateGraph(instance, data)` applies new nodes/links via the enter/update/exit pattern.
- Zooming and node dragging are enabled by default.

### Routes

- `+layout.svelte` imports global CSS and sets the `<head>` title.
- `+page.svelte` composes the view: header (`ViewToggle`), chat and graph columns, optional error/loading states. It loads the initial graph + stats during `onMount`.

## Running and Building

```bash
npm run dev -- --open     # Dev server (hot reload)
npm run check             # svelte-kit sync + svelte-check
dnpm run build            # Production bundle in .svelte-kit/output
npm run preview           # Serve the built output
```

> Vite automatically finds an available port starting at 5173. The backend CORS configuration allows 5173–5175 by default.

## Environment Variables

- `VITE_API_URL`: base URL for backend requests. Set per environment (development, staging, production). In dev, SvelteKit also proxies `/api` and `/ws` through `vite.config.js`.

To set env vars for other environments, create `.env` files following Vite’s [naming conventions](https://vitejs.dev/guide/env-and-mode.html).

## Extending the UI

- **Add new tabs or panels**: Update `+page.svelte` and add additional stores or components under `lib/components`.
- **Graph customisation**: Modify `d3-graph.js` to change node colours, add tooltips, or switch to Canvas rendering for very large graphs.
- **Styling**: Tailwind is available (see `tailwind.config.cjs`). `app.css` imports Tailwind layers.
- **Deployment**: Use `npm run build` + `npm run preview` for quick smoke tests. For adapters (Netlify, Vercel, etc.), install the appropriate `@sveltejs/adapter-*` and update `svelte.config.js`.

## Troubleshooting

- **WebSocket not connecting**: Ensure the backend is running and reachable at `VITE_API_URL`. The status badge in `ChatPanel` shows connection state.
- **CORS errors**: Update `backend/.env` → `CORS_ORIGINS` to include the exact origin displayed in your browser (protocol + host + port).
- **Graph not updating**: Check browser console for fetch/WebSocket errors. If ingestion completes but the graph remains empty, confirm the backend logs show a GraphML filename and no ingestion errors.

For deeper debugging, open dev tools and watch the network requests (`/api/query`, `/api/stats`, `/api/documents/ingest/status`) to confirm payloads match expectations.

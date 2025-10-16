from __future__ import annotations

import json
from fastapi import WebSocket, WebSocketDisconnect

from ..core.graph_manager import GraphManager
from ..core.lightrag_wrapper import LightRAGWrapper
from ..models.schemas import Message


async def websocket_handler(websocket: WebSocket) -> None:
    await websocket.accept()
    app_state = websocket.app.state
    lightrag: LightRAGWrapper = getattr(app_state, "lightrag")
    graph_manager: GraphManager = getattr(app_state, "graph_manager")
    settings = getattr(app_state, "settings")

    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "error": "Invalid JSON payload"})
                continue

            if payload.get("type") != "query":
                await websocket.send_json({"type": "error", "error": "Unsupported message type"})
                continue

            query: str = payload.get("query", "")
            mode: str = payload.get("mode", "hybrid")
            history_payload = payload.get("conversation_history", [])
            history = [Message.model_validate(message) for message in history_payload][-10:]

            try:
                response_text, elapsed = await lightrag.query(
                    query,
                    mode=mode,
                    conversation_history=history,
                    history_turns=min(len(history), 5),
                )
            except Exception as exc:  # pragma: no cover - runtime safety
                await websocket.send_json({"type": "error", "error": str(exc)})
                continue

            query_entities = graph_manager.extract_entities(query)
            response_entities = graph_manager.extract_entities(response_text)
            combined_entities = query_entities.union(response_entities)

            graph_manager.update_conversation_context(
                query,
                response_text,
                combined_entities,
                elapsed,
            )

            subgraph = graph_manager.build_contextual_subgraph(
                combined_entities,
                max_hops=settings.MAX_HOPS,
                max_nodes=settings.MAX_GRAPH_NODES,
            )
            graph_payload = graph_manager.graph_to_vis_format(subgraph, combined_entities)

            await websocket.send_json(
                {
                    "type": "response",
                    "response": response_text,
                    "graph": graph_payload,
                    "entities": [
                        graph_manager.node_metadata.get(node, {}).get("label", node)
                        for node in combined_entities
                    ],
                    "processing_time": elapsed,
                }
            )
    except WebSocketDisconnect:
        return


from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile

from ..core.config import Settings
from ..core.graph_manager import GraphManager
from ..core.lightrag_wrapper import LightRAGWrapper
from ..models.schemas import (
    GraphStats,
    IngestStatus,
    Message,
    QueryRequest,
    QueryResponse,
)

router = APIRouter(prefix="/api")


def get_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    if not settings:
        raise RuntimeError("Settings not attached to application state")
    return settings


def get_lightrag(request: Request) -> LightRAGWrapper:
    wrapper = getattr(request.app.state, "lightrag", None)
    if not wrapper:
        raise RuntimeError("LightRAG wrapper not available")
    return wrapper


def get_graph_manager(request: Request) -> GraphManager:
    manager = getattr(request.app.state, "graph_manager", None)
    if not manager:
        raise RuntimeError("Graph manager not available")
    return manager


SettingsDep = Annotated[Settings, Depends(get_settings)]
LightRAGDep = Annotated[LightRAGWrapper, Depends(get_lightrag)]
GraphManagerDep = Annotated[GraphManager, Depends(get_graph_manager)]


@router.post("/query", response_model=QueryResponse)
async def query_endpoint(
    payload: QueryRequest,
    settings: SettingsDep,
    lightrag: LightRAGDep,
    graph_manager: GraphManagerDep,
) -> QueryResponse:
    if not lightrag.initialized:
        raise HTTPException(status_code=503, detail="LightRAG is not ready yet")

    history_messages: list[Message] = payload.conversation_history[-10:]

    try:
        response_text, elapsed = await lightrag.query(
            payload.query,
            mode=payload.mode,
            conversation_history=history_messages,
            user_prompt=payload.user_prompt,
            history_turns=min(len(history_messages), 5),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    query_entities = graph_manager.extract_entities(payload.query)
    response_entities = graph_manager.extract_entities(response_text)
    combined_entities = query_entities.union(response_entities)

    graph_manager.update_conversation_context(
        payload.query,
        response_text,
        combined_entities,
        elapsed,
    )

    graph_data = None
    if payload.include_graph:
        subgraph = graph_manager.build_contextual_subgraph(
            combined_entities,
            max_hops=settings.MAX_HOPS,
            max_nodes=settings.MAX_GRAPH_NODES,
        )
        graph_data = graph_manager.graph_to_vis_format(subgraph, combined_entities)

    entity_labels = [
        graph_manager.node_metadata.get(node, {}).get("label", node)
        for node in combined_entities
    ]

    return QueryResponse(
        response=response_text,
        graph=graph_data,
        entities=sorted(entity_labels),
        processing_time=elapsed,
        mode_used=payload.mode,
    )


@router.get("/graph/full")
async def full_graph(graph_manager: GraphManagerDep) -> dict:
    return graph_manager.graph_to_vis_format(graph_manager.graph, graph_manager.last_entities)


@router.get("/graph/subgraph")
async def subgraph_endpoint(
    graph_manager: GraphManagerDep,
    settings: SettingsDep,
    entities: str | None = None,
) -> dict:
    if not entities:
        raise HTTPException(status_code=400, detail="entities query parameter is required")
    requested = [entity.strip() for entity in entities.split(",") if entity.strip()]
    node_ids = graph_manager.resolve_labels_to_nodes(requested)
    if not node_ids:
        raise HTTPException(status_code=404, detail="No matching entities found")

    subgraph = graph_manager.build_contextual_subgraph(
        node_ids,
        max_hops=settings.MAX_HOPS,
        max_nodes=settings.MAX_GRAPH_NODES,
    )
    return graph_manager.graph_to_vis_format(subgraph, node_ids)


@router.get("/stats", response_model=GraphStats)
async def stats_endpoint(graph_manager: GraphManagerDep) -> GraphStats:
    return graph_manager.get_graph_stats()


@router.post("/documents/upload")
async def upload_document(
    settings: SettingsDep,
    file: UploadFile = File(...),
) -> dict:
    corpus_dir = settings.corpus_path
    corpus_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or "document.txt"
    destination = corpus_dir / filename
    counter = 1
    while destination.exists():
        destination = corpus_dir / f"{Path(filename).stem}_{counter}{Path(filename).suffix}"
        counter += 1

    content = await file.read()
    destination.write_bytes(content)

    return {"status": "uploaded", "filename": destination.name}


@router.post("/documents/ingest", response_model=IngestStatus)
async def ingest_documents(
    lightrag: LightRAGDep,
    settings: SettingsDep,
    graph_manager: GraphManagerDep,
) -> IngestStatus:
    status = await lightrag.start_ingestion(settings.corpus_path)

    async def finalize() -> None:
        await lightrag.wait_for_ingestion()
        graph_manager.graph_path = lightrag.get_graph_path()
        graph_manager.reload_graph()
        await lightrag.refresh_entity_cache()

    asyncio.create_task(finalize())
    return status


@router.get("/documents/ingest/status", response_model=IngestStatus)
async def ingest_status(lightrag: LightRAGDep) -> IngestStatus:
    return lightrag.get_ingest_status()


@router.get("/health")
async def health_endpoint(lightrag: LightRAGDep) -> dict:
    return {"status": "ok", "lightrag_initialized": lightrag.initialized}


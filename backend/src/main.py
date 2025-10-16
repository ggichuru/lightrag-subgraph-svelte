from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .api.websocket import websocket_handler
from .core.config import Settings, get_settings
from .core.graph_manager import GraphManager
from .core.lightrag_wrapper import LightRAGWrapper

LOGGER = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(level=logging.INFO)
    LOGGER.info("Starting application")

    lightrag = LightRAGWrapper(settings)
    await lightrag.initialize()

    graph_manager = GraphManager(lightrag.get_graph_path(), settings)

    app.state.settings = settings
    app.state.lightrag = lightrag
    app.state.graph_manager = graph_manager

    try:
        yield
    finally:
        LOGGER.info("Shutting down application")
        await lightrag.cleanup()


app = FastAPI(title="Conversational Knowledge Graph API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.add_api_websocket_route("/ws", websocket_handler)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Conversational Knowledge Graph API"}


if __name__ == "__main__":
    import uvicorn

    settings: Settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )


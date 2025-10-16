from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    entities: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class QueryRequest(BaseModel):
    query: str
    conversation_history: list[Message] = Field(default_factory=list)
    mode: Literal["naive", "local", "global", "hybrid", "mix"] = "hybrid"
    include_graph: bool = True
    user_prompt: Optional[str] = None


class QueryResponse(BaseModel):
    response: str
    graph: Optional[dict] = None
    entities: list[str] = Field(default_factory=list)
    processing_time: float
    mode_used: str


class DocumentUpload(BaseModel):
    filename: str
    content: str
    doc_id: Optional[str] = None


class GraphStats(BaseModel):
    total_queries: int
    unique_entities: int
    most_discussed: list[tuple[str, int]]
    avg_response_time: float
    graph_node_count: int
    graph_edge_count: int


class IngestStatus(BaseModel):
    status: Literal["idle", "processing", "completed", "failed"] = "idle"
    documents_processed: int = 0
    total_documents: int = 0
    current_file: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


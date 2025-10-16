from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from lightrag import LightRAG, QueryParam
from lightrag.exceptions import PipelineNotInitializedError
from lightrag.kg.shared_storage import initialize_pipeline_status
from lightrag.llm.openai import openai_complete_if_cache, openai_embed
from lightrag.utils import wrap_embedding_func_with_attrs

from ..models.schemas import IngestStatus, Message
from ..utils.helpers import iter_corpus_files, load_document_text, slugify
from .config import Settings

LOGGER = logging.getLogger(__name__)


class LightRAGWrapper:
    """High-level async wrapper around LightRAG."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._rag: LightRAG | None = None
        self._initialized = False
        self._entity_cache: set[str] = set()
        self._ingest_lock = asyncio.Lock()
        self._ingest_task: asyncio.Task[None] | None = None
        self._ingest_status = IngestStatus()
        self._embedding_func = self._build_embedding_func()
        self._llm_func = self._build_llm_func()

    def _build_embedding_func(self):
        model = self._settings.OPENAI_EMBEDDING_MODEL
        embedding_dim = self._settings.OPENAI_EMBEDDING_DIM

        @wrap_embedding_func_with_attrs(embedding_dim=embedding_dim)
        async def _embedding(texts: list[str]):
            return await openai_embed(texts, model=model)

        return _embedding

    def _build_llm_func(self):
        model = self._settings.LIGHTRAG_MODEL

        async def _llm(prompt, system_prompt=None, history_messages=None, enable_cot: bool = False, **kwargs):
            return await openai_complete_if_cache(
                model,
                prompt,
                system_prompt=system_prompt,
                history_messages=history_messages or [],
                enable_cot=enable_cot,
                **kwargs,
            )

        return _llm

    @property
    def rag(self) -> LightRAG:
        if not self._rag:
            raise RuntimeError("LightRAG has not been initialized yet")
        return self._rag

    @property
    def initialized(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        """Initialise the LightRAG instance and storages."""

        if self._initialized:
            return

        workdir = self._settings.lightrag_working_path
        workdir.mkdir(parents=True, exist_ok=True)
        self._settings.corpus_path.mkdir(parents=True, exist_ok=True)

        LOGGER.info("Initialising LightRAG at %s", workdir)
        self._rag = LightRAG(
            working_dir=str(workdir),
            llm_model_name=self._settings.LIGHTRAG_MODEL,
            llm_model_max_async=self._settings.LIGHTRAG_MAX_ASYNC,
            max_total_tokens=self._settings.LIGHTRAG_MAX_TOKENS,
            max_parallel_insert=self._settings.MAX_PARALLEL_INSERT,
            embedding_func=self._embedding_func,
            llm_model_func=self._llm_func,
        )

        await self._rag.initialize_storages()
        await initialize_pipeline_status()
        await self._refresh_entity_cache()
        self._initialized = True
        LOGGER.info("LightRAG initialised successfully")

    async def cleanup(self) -> None:
        """Clean up LightRAG resources."""

        if self._rag:
            LOGGER.info("Finalising LightRAG storages")
            await self._rag.finalize_storages()
            self._rag = None
        self._initialized = False

    async def query(
        self,
        question: str,
        *,
        mode: str = "hybrid",
        conversation_history: Sequence[Message] | None = None,
        user_prompt: str | None = None,
        history_turns: int = 3,
    ) -> tuple[str, float]:
        """Execute a LightRAG query and return the response and elapsed time."""

        if not self._initialized:
            raise RuntimeError("LightRAG must be initialised before querying")

        conversation = [
            {"role": msg.role, "content": msg.content}
            for msg in (conversation_history or [])
        ]
        if history_turns:
            conversation = conversation[-history_turns:]

        params = QueryParam(
            mode=mode,
            conversation_history=conversation,
            history_turns=len(conversation),
            user_prompt=user_prompt,
        )

        start = time.perf_counter()
        try:
            result = await self.rag.aquery(question, param=params)
        except PipelineNotInitializedError:
            LOGGER.warning("Pipeline not initialised, attempting recovery")
            await initialize_pipeline_status()
            result = await self.rag.aquery(question, param=params)
        except Exception as exc:
            LOGGER.exception("LightRAG query failed: %s", exc)
            raise RuntimeError("LightRAG query failed") from exc

        elapsed = time.perf_counter() - start
        response_text: str
        if isinstance(result, str):
            response_text = result
        elif hasattr(result, '__aiter__'):
            chunks = [chunk async for chunk in result]
            response_text = "".join(chunks)
        elif result is None:
            response_text = ""
        else:
            response_text = str(result)

        return response_text, elapsed

    async def insert_documents(self, texts: Sequence[str], ids: Sequence[str]) -> None:
        if not self._initialized:
            raise RuntimeError("LightRAG must be initialised before inserting documents")
        if len(texts) != len(ids):
            raise ValueError("texts and ids must have the same length")

        await self.rag.ainsert(list(texts), ids=list(ids))

    async def ingest_corpus(self, corpus_dir: Path) -> None:
        """Ingest all supported documents from the corpus directory."""

        if not self._initialized:
            raise RuntimeError("LightRAG must be initialised before ingestion")

        async with self._ingest_lock:
            files = list(iter_corpus_files(corpus_dir))
            if not files:
                LOGGER.info("No documents found for ingestion in %s", corpus_dir)
                self._ingest_status = IngestStatus(
                    status="completed",
                    documents_processed=0,
                    total_documents=0,
                    started_at=datetime.utcnow(),
                    finished_at=datetime.utcnow(),
                )
                return

            start_time = datetime.utcnow()
            self._ingest_status = IngestStatus(
                status="processing",
                documents_processed=0,
                total_documents=len(files),
                started_at=start_time,
            )

            errors: list[str] = []
            processed = 0

            for doc_path in files:
                self._ingest_status.current_file = doc_path.name
                try:
                    text = load_document_text(doc_path)
                    if not text.strip():
                        LOGGER.warning("Skipping empty document %s", doc_path)
                        continue
                    doc_id = slugify(doc_path.stem)
                    await self.insert_documents([text], [doc_id])
                    processed += 1
                    self._ingest_status.documents_processed = processed
                except Exception as exc:
                    LOGGER.exception("Failed to ingest %s", doc_path)
                    errors.append(f"{doc_path.name}: {exc}")
                    continue

            status_value = "completed" if not errors else "failed"
            self._ingest_status = IngestStatus(
                status=status_value,
                documents_processed=processed,
                total_documents=len(files),
                current_file=None,
                error="; ".join(errors) if errors else None,
                started_at=start_time,
                finished_at=datetime.utcnow(),
            )

            await self._refresh_entity_cache()

    async def start_ingestion(self, corpus_dir: Path) -> IngestStatus:
        """Launch ingestion in the background if not already running."""

        if self._ingest_task and not self._ingest_task.done():
            LOGGER.info("Ingestion already in progress")
            return self._ingest_status

        self._ingest_status = IngestStatus(status="processing", started_at=datetime.utcnow())

        async def runner() -> None:
            try:
                await self.ingest_corpus(corpus_dir)
            finally:
                self._ingest_task = None

        loop = asyncio.get_running_loop()
        self._ingest_task = loop.create_task(runner())
        return self._ingest_status

    def get_ingest_status(self) -> IngestStatus:
        return self._ingest_status

    def get_graph_path(self) -> Path:
        """Return the path to the GraphML file managed by LightRAG."""

        storage = getattr(self.rag, 'chunk_entity_relation_graph', None)
        if storage is not None:
            raw_path = getattr(storage, '_graphml_xml_file', None)
            if raw_path:
                return Path(raw_path)

        candidates = sorted(self._settings.lightrag_working_path.glob('*.graphml'))
        if candidates:
            return candidates[0]
        return self._settings.lightrag_working_path / 'graph.graphml'

    async def refresh_entity_cache(self) -> None:
        await self._refresh_entity_cache()

    async def wait_for_ingestion(self) -> None:
        if self._ingest_task:
            try:
                await self._ingest_task
            except Exception:
                LOGGER.exception("Ingestion task raised an exception")

    def extract_entities_from_text(self, text: str, *, additional_entities: Iterable[str] | None = None) -> list[str]:
        """Extract known entity labels from the given text."""

        candidates = set(self._entity_cache)
        if additional_entities:
            candidates.update(additional_entities)

        lowered = text.lower()
        matches = {
            entity for entity in candidates if entity.lower() in lowered
        }
        return sorted(matches)

    async def _refresh_entity_cache(self) -> None:
        if not self._rag:
            return
        try:
            labels = await self._rag.get_graph_labels()
        except Exception:  # pragma: no cover - best-effort cache refresh
            LOGGER.debug("Failed to refresh graph labels", exc_info=True)
            labels = []

        if isinstance(labels, Counter):
            entities = set(labels.keys())
        elif isinstance(labels, (list, tuple, set)):
            entities = {str(label) for label in labels}
        elif isinstance(labels, str):
            entities = {piece.strip() for piece in labels.split("\n") if piece.strip()}
        else:
            entities = set()

        if entities:
            self._entity_cache = entities


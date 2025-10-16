from __future__ import annotations

import math
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import networkx as nx

from ..models.schemas import GraphStats
from .config import Settings

LOGGER = logging.getLogger(__name__)

ENTITY_COLORS = {
    "PERSON": "#1f77b4",
    "ORG": "#ff7f0e",
    "EVENT": "#2ca02c",
    "PLACE": "#9467bd",
    "WORK": "#8c564b",
    "DATE": "#17becf",
}


class GraphManager:
    """Manage the LightRAG knowledge graph and conversation context."""

    def __init__(self, graph_path: Path, settings: Settings) -> None:
        self.settings = settings
        self.graph_path = graph_path
        self.graph = nx.Graph()
        self.label_index: dict[str, set[str]] = defaultdict(set)
        self.node_metadata: dict[str, dict] = {}
        self.entity_frequency: dict[str, float] = defaultdict(float)
        self.entity_last_seen: dict[str, datetime] = {}
        self.total_queries = 0
        self.response_times: list[float] = []
        self.last_entities: set[str] = set()
        self.last_query: str | None = None
        self.last_response: str | None = None
        self._centrality: dict[str, float] = {}

        self.reload_graph()

    def reload_graph(self) -> None:
        """Load the graph from disk and rebuild indices."""

        if self.graph_path.exists():
            try:
                self.graph = nx.read_graphml(self.graph_path)
                LOGGER.info(
                    "Loaded knowledge graph %s (%d nodes, %d edges)",
                    self.graph_path,
                    self.graph.number_of_nodes(),
                    self.graph.number_of_edges(),
                )
            except Exception:  # pragma: no cover - defensive logging
                LOGGER.exception("Failed to read graphml %s", self.graph_path)
                self.graph = nx.Graph()
        else:
            LOGGER.warning("Graph path %s does not exist yet", self.graph_path)
            self.graph = nx.Graph()

        self._build_indices()
        self._compute_centrality()

    def _build_indices(self) -> None:
        self.label_index.clear()
        self.node_metadata.clear()

        for node_id, data in self.graph.nodes(data=True):
            label = self._resolve_label(node_id, data)
            lowered = label.lower()
            self.label_index[lowered].add(node_id)
            self.node_metadata[node_id] = {
                "id": node_id,
                "label": label,
                "type": data.get("entity_type") or data.get("type") or "ENTITY",
                "description": data.get("description") or data.get("summary") or "",
            }

    def _compute_centrality(self) -> None:
        if self.graph.number_of_nodes() == 0:
            self._centrality = {}
            return

        try:
            self._centrality = nx.pagerank(self.graph, max_iter=100)
        except Exception:  # pragma: no cover - fallback
            LOGGER.debug("Falling back to degree centrality", exc_info=True)
            self._centrality = nx.degree_centrality(self.graph)

    @staticmethod
    def _resolve_label(node_id: str, data: dict) -> str:
        return str(data.get("name") or data.get("label") or data.get("title") or node_id)

    def extract_entities(self, text: str) -> set[str]:
        """Return node ids whose label occurs in the provided text."""

        lowered = text.lower()
        matches: set[str] = set()
        for label_lower, node_ids in self.label_index.items():
            if label_lower in lowered:
                matches.update(node_ids)
        return matches

    def resolve_labels_to_nodes(self, labels: Iterable[str]) -> set[str]:
        nodes: set[str] = set()
        for label in labels:
            if not label:
                continue
            nodes.update(self.label_index.get(label.lower(), set()))
        return nodes


    def apply_temporal_decay(self) -> None:
        if not self.entity_frequency:
            return
        for node_id in list(self.entity_frequency.keys()):
            self.entity_frequency[node_id] *= self.settings.TEMPORAL_DECAY_RATE
            if self.entity_frequency[node_id] < 1e-4:
                del self.entity_frequency[node_id]

    def update_conversation_context(
        self,
        query: str,
        response: str,
        entities: Iterable[str],
        response_time: float,
    ) -> None:
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        entities = set(entities)
        self.apply_temporal_decay()

        for entity in entities:
            self.entity_frequency[entity] += 1.0
            self.entity_last_seen[entity] = now

        self.last_entities = entities
        self.last_query = query
        self.last_response = response
        self.total_queries += 1
        self.response_times.append(response_time)

    def calculate_node_importance(self, node_id: str, focal_entities: set[str]) -> float:
        freq = self.entity_frequency.get(node_id, 0.0)
        max_freq = max(self.entity_frequency.values()) if self.entity_frequency else 1.0
        freq_score = freq / max_freq if max_freq else 0.0

        recency_score = self._recency_score(node_id)
        centrality_score = self._centrality.get(node_id, 0.0)
        focal_score = 1.0 if node_id in focal_entities else 0.0

        return (
            self.settings.ENTITY_FREQUENCY_WEIGHT * freq_score
            + self.settings.RECENCY_WEIGHT * recency_score
            + self.settings.CENTRALITY_WEIGHT * centrality_score
            + self.settings.FOCAL_WEIGHT * focal_score
        )

    def _recency_score(self, node_id: str) -> float:
        timestamp = self.entity_last_seen.get(node_id)
        if not timestamp:
            return 0.0
        now = datetime.utcnow().replace(tzinfo=timezone.utc)
        delta_hours = max((now - timestamp).total_seconds() / 3600.0, 0.0)
        decay_rate = -math.log(max(self.settings.TEMPORAL_DECAY_RATE, 1e-6))
        return math.exp(-decay_rate * delta_hours)

    def build_contextual_subgraph(
        self,
        focal_entities: set[str],
        *,
        max_hops: Optional[int] = None,
        max_nodes: Optional[int] = None,
    ) -> nx.Graph:
        if self.graph.number_of_nodes() == 0:
            return nx.Graph()

        max_hops = max_hops or self.settings.MAX_HOPS
        max_nodes = max_nodes or self.settings.MAX_GRAPH_NODES

        candidate_nodes: set[str] = set()
        for entity in focal_entities:
            if entity not in self.graph:
                continue
            ego = nx.ego_graph(self.graph, entity, radius=max_hops)
            candidate_nodes.update(ego.nodes)

        if not candidate_nodes:
            # fallback to most central nodes
            sorted_nodes = sorted(
                self.graph.nodes(),
                key=lambda node: self._centrality.get(node, 0.0),
                reverse=True,
            )
            candidate_nodes = set(sorted_nodes[:max_nodes])

        scored = []
        for node in candidate_nodes:
            score = self.calculate_node_importance(node, focal_entities)
            scored.append((node, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        selected_nodes = {node for node, _ in scored[:max_nodes]}

        if focal_entities:
            selected_nodes.update(focal_entities)

        subgraph = self.graph.subgraph(selected_nodes).copy()
        self._ensure_connectivity(subgraph, selected_nodes, focal_entities, max_nodes)
        return self.graph.subgraph(selected_nodes).copy()

    def _ensure_connectivity(
        self,
        subgraph: nx.Graph,
        selected_nodes: set[str],
        focal_entities: set[str],
        max_nodes: int,
    ) -> None:
        if not focal_entities:
            return

        try:
            components = list(nx.connected_components(subgraph))
        except nx.NetworkXError:
            return

        if len(components) <= 1:
            return

        focal = [node for node in focal_entities if node in self.graph]
        if not focal:
            return

        base_component = max(
            components,
            key=lambda comp: len(comp.intersection(focal_entities)),
        )

        for component in components:
            if component == base_component:
                continue
            source = next(iter(component))
            target = min(
                focal,
                key=lambda node: self._shortest_path_length_safe(source, node),
            )
            if target is None:
                continue
            path = self._shortest_path_safe(source, target)
            for node in path:
                selected_nodes.add(node)
                if len(selected_nodes) >= max_nodes:
                    return

    def _shortest_path_safe(self, src: str, dst: str) -> list[str]:
        try:
            return nx.shortest_path(self.graph, src, dst)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return [src]

    def _shortest_path_length_safe(self, src: str, dst: str) -> float:
        try:
            return nx.shortest_path_length(self.graph, src, dst)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return math.inf

    def graph_to_vis_format(self, subgraph: nx.Graph, focal_entities: set[str]) -> dict:
        nodes_payload = []
        links_payload = []

        max_importance = 0.0
        importance_cache: dict[str, float] = {}
        for node in subgraph.nodes():
            importance = self.calculate_node_importance(node, focal_entities)
            importance_cache[node] = importance
            max_importance = max(max_importance, importance)

        scaling = max_importance or 1.0

        for node_id, data in subgraph.nodes(data=True):
            meta = self.node_metadata.get(node_id, {})
            importance = importance_cache.get(node_id, 0.0)
            size = 8 + (importance / scaling) * 20
            node_type = meta.get("type", "ENTITY")
            color = ENTITY_COLORS.get(node_type.upper(), "#4a5568")

            nodes_payload.append(
                {
                    "id": node_id,
                    "label": meta.get("label") or self._resolve_label(node_id, data),
                    "type": node_type,
                    "description": meta.get("description", ""),
                    "frequency": self.entity_frequency.get(node_id, 0.0),
                    "is_focal": node_id in focal_entities,
                    "size": size,
                    "color": color,
                    "centrality": self._centrality.get(node_id, 0.0),
                }
            )

        for source, target, data in subgraph.edges(data=True):
            links_payload.append(
                {
                    "source": source,
                    "target": target,
                    "relationship": data.get("relation")
                    or data.get("label")
                    or data.get("type")
                    or "related",
                    "weight": float(data.get("weight", 1.0)),
                    "keywords": data.get("keywords", ""),
                }
            )

        return {"nodes": nodes_payload, "links": links_payload}

    def get_graph_stats(self) -> GraphStats:
        avg_response = sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        most_discussed = sorted(
            ((self.node_metadata.get(node, {}).get("label", node), int(freq)) for node, freq in self.entity_frequency.items()),
            key=lambda item: item[1],
            reverse=True,
        )[:5]

        return GraphStats(
            total_queries=self.total_queries,
            unique_entities=len(self.entity_frequency),
            most_discussed=most_discussed,
            avg_response_time=avg_response,
            graph_node_count=self.graph.number_of_nodes(),
            graph_edge_count=self.graph.number_of_edges(),
        )


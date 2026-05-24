from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
import math
import os
import re
import uuid


TOKEN_RE = re.compile(r"[a-zA-Z0-9_]{3,}")


@dataclass
class IngestedDocument:
    doc_id: str
    chunks_count: int


@dataclass
class KnowledgeChunk:
    chunk_id: str
    source_doc_id: str
    source_type: str
    source_ref: str
    title: str
    content: str
    created_at: str
    embedding: list[float] | None = None
    file_id: str = ""
    metadata: dict[str, str] | None = None


class KnowledgeBase:
    def __init__(self, path: str) -> None:
        self.path = path
        self._chunks: list[KnowledgeChunk] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._chunks = []
            return
        with open(self.path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        chunks: list[KnowledgeChunk] = []
        for item in payload:
            # Compatibilidade retroativa com formato antigo (um item por documento).
            is_old_doc = "chunk_id" not in item and "doc_id" in item and "content" in item
            if is_old_doc:
                old_doc_id = str(item.get("doc_id") or str(uuid.uuid4()))
                chunks.append(
                    KnowledgeChunk(
                        chunk_id=str(uuid.uuid4()),
                        source_doc_id=old_doc_id,
                        source_type=str(item.get("source_type", "")),
                        source_ref=str(item.get("source_ref", "")),
                        title=str(item.get("title", "")),
                        content=str(item.get("content", "")),
                        created_at=str(item.get("created_at", "")),
                        embedding=self._coerce_embedding(item.get("embedding")),
                        file_id="",
                        metadata={},
                    )
                )
                continue

            chunks.append(
                KnowledgeChunk(
                    chunk_id=str(item.get("chunk_id", "")),
                    source_doc_id=str(item.get("source_doc_id", "")),
                    source_type=str(item.get("source_type", "")),
                    source_ref=str(item.get("source_ref", "")),
                    title=str(item.get("title", "")),
                    content=str(item.get("content", "")),
                    created_at=str(item.get("created_at", "")),
                    embedding=self._coerce_embedding(item.get("embedding")),
                    file_id=str(item.get("file_id", "")),
                    metadata=item.get("metadata") if isinstance(item.get("metadata"), dict) else {},
                )
            )
        self._chunks = chunks

    @staticmethod
    def _coerce_embedding(raw: object) -> list[float] | None:
        if not isinstance(raw, list):
            return None
        try:
            return [float(v) for v in raw]
        except (TypeError, ValueError):
            return None

    def _save(self) -> None:
        parent_dir = os.path.dirname(self.path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(chunk) for chunk in self._chunks], f, ensure_ascii=False, indent=2)

    @staticmethod
    def _chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
        clean = text.strip()
        if not clean:
            return [""]
        chunks: list[str] = []
        start = 0
        step = max(1, chunk_size - chunk_overlap)
        while start < len(clean):
            chunk = clean[start : start + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
            start += step
        return chunks or [clean]

    def add_document(
        self,
        source_type: str,
        source_ref: str,
        title: str,
        content: str,
        *,
        file_id: str = "",
        metadata: dict[str, str] | None = None,
        chunk_size: int = 1200,
        chunk_overlap: int = 180,
        embedder: object | None = None,
    ) -> IngestedDocument:
        source_doc_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        title_clean = title.strip() or source_ref
        metadata_clean = metadata or {}

        pieces = self._chunk_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        inserted = 0
        for piece in pieces:
            embedding = None
            if embedder is not None and piece.strip():
                try:
                    embedding = embedder.embed_text(piece, input_type="SEARCH_DOCUMENT")
                except Exception:
                    embedding = None

            self._chunks.append(
                KnowledgeChunk(
                    chunk_id=str(uuid.uuid4()),
                    source_doc_id=source_doc_id,
                    source_type=source_type,
                    source_ref=source_ref,
                    title=title_clean,
                    content=piece,
                    created_at=created_at,
                    embedding=embedding,
                    file_id=file_id,
                    metadata=metadata_clean,
                )
            )
            inserted += 1

        self._save()
        return IngestedDocument(doc_id=source_doc_id, chunks_count=inserted)

    def list_sources(self) -> list[dict[str, str | int]]:
        grouped: dict[str, dict[str, str | int]] = {}
        for chunk in self._chunks:
            key = chunk.source_doc_id
            if key not in grouped:
                grouped[key] = {
                    "doc_id": chunk.source_doc_id,
                    "source_type": chunk.source_type,
                    "source_ref": chunk.source_ref,
                    "title": chunk.title,
                    "created_at": chunk.created_at,
                    "file_id": chunk.file_id,
                    "chunks_count": 0,
                }
            grouped[key]["chunks_count"] = int(grouped[key]["chunks_count"]) + 1
        items = list(grouped.values())
        items.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
        return items

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {match.group(0).lower() for match in TOKEN_RE.finditer(text)}

    @staticmethod
    def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def _lexical_score(query_tokens: set[str], chunk_tokens: set[str]) -> float:
        if not query_tokens or not chunk_tokens:
            return 0.0
        intersection = len(query_tokens.intersection(chunk_tokens))
        if intersection == 0:
            return 0.0
        return (2.0 * intersection) / (len(query_tokens) + len(chunk_tokens))

    @staticmethod
    def _matches_filters(chunk: KnowledgeChunk, filters: dict[str, str] | None) -> bool:
        if not filters:
            return True
        source_type = filters.get("source_type", "").strip()
        if source_type and chunk.source_type != source_type:
            return False
        source_ref = filters.get("source_ref", "").strip()
        if source_ref and chunk.source_ref != source_ref:
            return False
        file_id = filters.get("file_id", "").strip()
        if file_id and chunk.file_id != file_id:
            return False
        title_contains = filters.get("title_contains", "").strip().lower()
        if title_contains and title_contains not in chunk.title.lower():
            return False
        created_after = filters.get("created_after", "").strip()
        if created_after and chunk.created_at < created_after:
            return False
        created_before = filters.get("created_before", "").strip()
        if created_before and chunk.created_at > created_before:
            return False
        return True

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        *,
        embedder: object | None = None,
        rerank_alpha: float = 0.65,
        filters: dict[str, str] | None = None,
    ) -> str:
        query_tokens = self._tokens(query)
        if not self._chunks:
            return ""

        query_embedding: list[float] | None = None
        if embedder is not None and query.strip():
            try:
                query_embedding = embedder.embed_text(query, input_type="SEARCH_QUERY")
            except Exception:
                query_embedding = None

        scored: list[tuple[float, float, float, KnowledgeChunk]] = []
        for chunk in self._chunks:
            if not self._matches_filters(chunk, filters):
                continue
            chunk_tokens = self._tokens(f"{chunk.title}\n{chunk.content}")
            lexical = self._lexical_score(query_tokens, chunk_tokens)

            semantic = 0.0
            if query_embedding is not None and chunk.embedding:
                cosine = self._cosine_similarity(query_embedding, chunk.embedding)
                semantic = max(0.0, (cosine + 1.0) / 2.0)

            final_score = lexical if query_embedding is None else (1.0 - rerank_alpha) * lexical + rerank_alpha * semantic
            if final_score > 0:
                scored.append((final_score, lexical, semantic, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_chunks = scored[:top_k]
        if not top_chunks:
            return ""

        parts: list[str] = []
        for idx, (final_score, lexical, semantic, chunk) in enumerate(top_chunks, start=1):
            snippet = chunk.content[:1800].strip()
            parts.append(
                f"[Fonte {idx}] {chunk.title} ({chunk.source_type})\n"
                f"Ref: {chunk.source_ref}\n"
                f"Chunk: {chunk.chunk_id}\n"
                f"Score: final={final_score:.4f} lexical={lexical:.4f} semantic={semantic:.4f}\n"
                f"Trecho: {snippet}"
            )
        return "\n\n".join(parts)

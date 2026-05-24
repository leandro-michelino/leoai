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
class KnowledgeDoc:
    doc_id: str
    source_type: str
    source_ref: str
    title: str
    content: str
    created_at: str
    embedding: list[float] | None = None


class KnowledgeBase:
    def __init__(self, path: str) -> None:
        self.path = path
        self._docs: list[KnowledgeDoc] = []
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._docs = []
            return
        with open(self.path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        docs: list[KnowledgeDoc] = []
        for item in payload:
            embedding_raw = item.get("embedding")
            embedding: list[float] | None
            if isinstance(embedding_raw, list):
                try:
                    embedding = [float(v) for v in embedding_raw]
                except (TypeError, ValueError):
                    embedding = None
            else:
                embedding = None

            docs.append(
                KnowledgeDoc(
                    doc_id=str(item.get("doc_id", "")),
                    source_type=str(item.get("source_type", "")),
                    source_ref=str(item.get("source_ref", "")),
                    title=str(item.get("title", "")),
                    content=str(item.get("content", "")),
                    created_at=str(item.get("created_at", "")),
                    embedding=embedding,
                )
            )
        self._docs = docs

    def _save(self) -> None:
        parent_dir = os.path.dirname(self.path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(doc) for doc in self._docs], f, ensure_ascii=False, indent=2)

    def add_document(
        self,
        source_type: str,
        source_ref: str,
        title: str,
        content: str,
        embedding: list[float] | None = None,
    ) -> KnowledgeDoc:
        doc = KnowledgeDoc(
            doc_id=str(uuid.uuid4()),
            source_type=source_type,
            source_ref=source_ref,
            title=title.strip() or source_ref,
            content=content.strip(),
            created_at=datetime.now(timezone.utc).isoformat(),
            embedding=embedding,
        )
        self._docs.append(doc)
        self._save()
        return doc

    def list_sources(self) -> list[dict[str, str]]:
        return [
            {
                "doc_id": doc.doc_id,
                "source_type": doc.source_type,
                "source_ref": doc.source_ref,
                "title": doc.title,
                "created_at": doc.created_at,
            }
            for doc in self._docs
        ]

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
    def _lexical_score(query_tokens: set[str], doc_tokens: set[str]) -> float:
        if not query_tokens or not doc_tokens:
            return 0.0
        intersection = len(query_tokens.intersection(doc_tokens))
        if intersection == 0:
            return 0.0
        # Similaridade de Dice para manter score em [0,1]
        return (2.0 * intersection) / (len(query_tokens) + len(doc_tokens))

    def retrieve_context(self, query: str, top_k: int = 3, embedder: object | None = None, rerank_alpha: float = 0.65) -> str:
        query_tokens = self._tokens(query)
        if not self._docs:
            return ""

        query_embedding: list[float] | None = None
        if embedder is not None and query.strip():
            try:
                query_embedding = embedder.embed_text(query, input_type="SEARCH_QUERY")
            except Exception:
                query_embedding = None

        scored: list[tuple[float, float, float, KnowledgeDoc]] = []
        for doc in self._docs:
            doc_tokens = self._tokens(f"{doc.title}\n{doc.content}")
            lexical = self._lexical_score(query_tokens, doc_tokens)

            semantic = 0.0
            if query_embedding is not None and doc.embedding:
                cosine = self._cosine_similarity(query_embedding, doc.embedding)
                semantic = max(0.0, (cosine + 1.0) / 2.0)

            if query_embedding is None:
                final_score = lexical
            else:
                final_score = (1.0 - rerank_alpha) * lexical + rerank_alpha * semantic

            if final_score > 0:
                scored.append((final_score, lexical, semantic, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_docs = scored[:top_k]
        if not top_docs:
            return ""

        parts: list[str] = []
        for idx, (final_score, lexical, semantic, doc) in enumerate(top_docs, start=1):
            snippet = doc.content[:1800].strip()
            parts.append(
                f"[Fonte {idx}] {doc.title} ({doc.source_type})\n"
                f"Ref: {doc.source_ref}\n"
                f"Score: final={final_score:.4f} lexical={lexical:.4f} semantic={semantic:.4f}\n"
                f"Trecho: {snippet}"
            )
        return "\n\n".join(parts)

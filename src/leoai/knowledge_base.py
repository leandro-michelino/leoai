from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import json
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
        self._docs = [KnowledgeDoc(**item) for item in payload]

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(doc) for doc in self._docs], f, ensure_ascii=False, indent=2)

    def add_document(self, source_type: str, source_ref: str, title: str, content: str) -> KnowledgeDoc:
        doc = KnowledgeDoc(
            doc_id=str(uuid.uuid4()),
            source_type=source_type,
            source_ref=source_ref,
            title=title.strip() or source_ref,
            content=content.strip(),
            created_at=datetime.now(timezone.utc).isoformat(),
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

    def retrieve_context(self, query: str, top_k: int = 3) -> str:
        query_tokens = self._tokens(query)
        if not query_tokens or not self._docs:
            return ""

        scored: list[tuple[int, KnowledgeDoc]] = []
        for doc in self._docs:
            doc_tokens = self._tokens(doc.content)
            score = len(query_tokens.intersection(doc_tokens))
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda item: item[0], reverse=True)
        top_docs = scored[:top_k]
        if not top_docs:
            return ""

        parts: list[str] = []
        for idx, (_, doc) in enumerate(top_docs, start=1):
            snippet = doc.content[:1800].strip()
            parts.append(
                f"[Fonte {idx}] {doc.title} ({doc.source_type})\n"
                f"Ref: {doc.source_ref}\n"
                f"Trecho: {snippet}"
            )
        return "\n\n".join(parts)


from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

from .config import Settings
from .file_extractors import extract_content_for_rag


SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


@dataclass
class StoredFile:
    file_id: str
    kind: str
    original_name: str
    stored_name: str
    content_type: str
    size_bytes: int
    sha256: str
    created_at: str
    path: str


class FileStore:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.upload_dir = Path(settings.files_store_dir)
        self.generated_dir = Path(settings.generated_store_dir)
        self.index_path = Path(settings.files_index_path)
        self._items: list[StoredFile] = []
        self._ensure_layout()
        self._load()

    def _ensure_layout(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> None:
        if not self.index_path.exists():
            self._items = []
            return
        with self.index_path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        items: list[StoredFile] = []
        for raw in payload:
            try:
                items.append(
                    StoredFile(
                        file_id=str(raw["file_id"]),
                        kind=str(raw["kind"]),
                        original_name=str(raw["original_name"]),
                        stored_name=str(raw["stored_name"]),
                        content_type=str(raw["content_type"]),
                        size_bytes=int(raw["size_bytes"]),
                        sha256=str(raw["sha256"]),
                        created_at=str(raw["created_at"]),
                        path=str(raw["path"]),
                    )
                )
            except Exception:
                continue
        self._items = items

    def _save(self) -> None:
        with self.index_path.open("w", encoding="utf-8") as f:
            json.dump([asdict(item) for item in self._items], f, ensure_ascii=False, indent=2)

    @staticmethod
    def _safe_name(name: str) -> str:
        stripped = (name or "file.bin").strip()
        safe = SAFE_NAME_RE.sub("_", stripped)
        return safe[:240] or "file.bin"

    def _destination(self, kind: str, original_name: str) -> tuple[str, Path]:
        file_id = str(uuid.uuid4())
        safe_name = self._safe_name(original_name)
        stored_name = f"{file_id}_{safe_name}"
        base_dir = self.upload_dir if kind == "uploaded" else self.generated_dir
        return file_id, base_dir / stored_name

    def _record(self, kind: str, original_name: str, content_type: str, data: bytes) -> StoredFile:
        file_id, dest = self._destination(kind=kind, original_name=original_name)
        with dest.open("wb") as f:
            f.write(data)

        sha256 = hashlib.sha256(data).hexdigest()
        item = StoredFile(
            file_id=file_id,
            kind=kind,
            original_name=original_name,
            stored_name=dest.name,
            content_type=(content_type or "application/octet-stream").strip(),
            size_bytes=len(data),
            sha256=sha256,
            created_at=datetime.now(timezone.utc).isoformat(),
            path=str(dest),
        )
        self._items.append(item)
        self._save()
        return item

    def save_uploaded(self, original_name: str, content_type: str, data: bytes) -> StoredFile:
        return self._record("uploaded", original_name, content_type, data)

    def save_generated(self, original_name: str, content_type: str, data: bytes) -> StoredFile:
        return self._record("generated", original_name, content_type, data)

    def list_files(self, kind: str | None = None, limit: int = 200) -> list[StoredFile]:
        items = self._items
        if kind:
            items = [i for i in items if i.kind == kind]
        return list(reversed(items))[:limit]

    def get(self, file_id: str) -> StoredFile | None:
        for item in self._items:
            if item.file_id == file_id:
                return item
        return None

    def open_path(self, item: StoredFile) -> Path:
        path = Path(item.path)
        if not path.exists():
            raise FileNotFoundError("Arquivo não encontrado no storage.")
        return path

    @staticmethod
    def infer_text_for_rag(filename: str, content_type: str, data: bytes) -> tuple[str, dict[str, str]]:
        return extract_content_for_rag(filename=filename, content_type=content_type, data=data)

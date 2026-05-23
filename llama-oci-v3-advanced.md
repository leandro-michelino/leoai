# Llama on OCI Always Free - Advanced Features (v3 supplement)

> **Audience:** AI coding agent (Codex). This document **extends** `llama-oci-free-bootstrap.md` (v2). Apply v2 first, then this.
> **Goal:** Add Tier 1 + Tier 2 + vision capabilities without exceeding Always Free limits.
> **Estimated time:** 60-90 min after v2 is up (mostly model downloads on first run).

---

## 0. What this supplement adds

| # | Feature | New surface |
|---|---------|-------------|
| 1 | Function calling / tools (ReAct agent) | `POST /agent/run` |
| 2 | SSE streaming | `stream: true` flag on `/v1/*` and `/agent/run` |
| 3 | PDF/DOCX/MD ingestion into RAG | `POST /rag/ingest` (multipart) |
| 4 | Persistent conversation memory (SQLite + summarizer) | `POST /chat`, `GET/POST/DELETE /chat/sessions[/:id]` |
| 5 | Secondary small model (Qwen 2.5 0.5B) + auto-routing | `POST /v1/small/*`, used internally by router |
| 6 | Whisper.cpp audio transcription | `POST /whisper/transcribe` |
| 7 | Better embeddings (bge-m3, multilingual PT/EN) | replaces `all-MiniLM-L6-v2` |
| 8 | Cross-encoder reranker (bge-reranker-base) | applied on `/rag/query` |
| 15 | Multi-modal vision (MoonDream2) | `POST /v1/vision/chat/completions` |

All run on the **same** A1 Flex VM. No new infrastructure provisioned beyond a bigger boot volume.

---

## 1. Updated architecture

```
                              Internet
                                  |
                       NGINX :80 (api-key on /v1, /rag, /agent, /whisper)
                                  |
   +------------------------------+------------------------------+
   |                  rag-api (FastAPI :8082)                    |
   |  +-------------+  +----------+  +----------+  +----------+  |
   |  | /agent/run  |  | /rag/*   |  | /chat/*  |  | /whisper |  |
   |  | ReAct loop  |  | retrieve |  | sessions |  | proxy    |  |
   |  | + tools     |  | + rerank |  | + memory |  |          |  |
   |  +------+------+  +-----+----+  +-----+----+  +-----+----+  |
   |         |               |             |             |       |
   +---------|---------------|-------------|-------------|-------+
             |               |             |             |
   +---------v---+    +------v-----+   +---v---+    +----v-----+
   | llama 3B    |    | chroma +   |   |sqlite |    |whisper.cpp|
   | :8081       |<---| bge-m3 +   |   |conv.db|    | :8084     |
   | (primary)   |    | reranker   |   |       |    |           |
   +-------------+    +------------+   +-------+    +-----------+
   +-------------+    +------------+
   | qwen 0.5B   |    | moondream2 |
   | :8083       |    | :8085      |
   | (routing,   |    | (vision)   |
   |  summary)   |    |            |
   +-------------+    +------------+
```

Open WebUI sits in front and now sees three models (`llama-3b`, `qwen-small`, `moondream-vision`) through the OpenAI `/v1/models` endpoint.

---

## 2. Prerequisites (delta from v2)

Add to `.env`:

```bash
# Optional override - if blank, uses defaults
export VISION_MODEL_FILE="moondream2-text-model-f16.gguf"
export VISION_MMPROJ_FILE="moondream2-mmproj-f16.gguf"
export SMALL_MODEL_FILE="qwen2.5-0.5b-instruct-q4_k_m.gguf"
export WHISPER_MODEL="base"   # tiny | base | small (small ~500MB)
```

Bump in `terraform/variables.tf`:

```hcl
variable "boot_volume_gb" {
  type    = number
  default = 80   # was 50
}
```

Then re-run `make tf-apply` - OCI resizes the boot volume in place; expand the FS:

```bash
make ssh -- "sudo /usr/libexec/oci-growfs -y"
```

---

## 3. New files

### 3.1 Update `terraform/variables.tf` - additional model variables

Append:

```hcl
variable "small_model_file" {
  type    = string
  default = "qwen2.5-0.5b-instruct-q4_k_m.gguf"
}

variable "small_model_source_url" {
  type    = string
  default = "https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
}

variable "vision_model_file" {
  type    = string
  default = "moondream2-text-model-f16.gguf"
}

variable "vision_mmproj_file" {
  type    = string
  default = "moondream2-mmproj-f16.gguf"
}

variable "vision_model_source_url" {
  type    = string
  default = "https://huggingface.co/vikhyatk/moondream2/resolve/main/moondream2-text-model-f16.gguf"
}

variable "vision_mmproj_source_url" {
  type    = string
  default = "https://huggingface.co/vikhyatk/moondream2/resolve/main/moondream2-mmproj-f16.gguf"
}
```

### 3.2 Update `terraform/templates/inventory.tpl` - pass new vars

Append inside `vars:`:

```yaml
    small_model_file: ${small_model_file}
    small_model_source_url: ${small_model_source_url}
    vision_model_file: ${vision_model_file}
    vision_mmproj_file: ${vision_mmproj_file}
    vision_model_source_url: ${vision_model_source_url}
    vision_mmproj_source_url: ${vision_mmproj_source_url}
```

And update `terraform/outputs.tf` `local_file.ansible_inventory` content to pass them through templatefile.

### 3.3 Update `ansible/group_vars/all.yml`

```yaml
hf_token: "{{ lookup('env', 'HF_TOKEN') }}"
api_key: "{{ lookup('env', 'API_KEY') }}"
webui_secret_key: "{{ lookup('env', 'WEBUI_SECRET_KEY') }}"

llama_port: 8081
llama_small_port: 8083
whisper_port: 8084
vision_port: 8085
webui_port: 3000
rag_port: 8082

llama_image: "docker.io/amperecomputingai/llama.cpp:latest"
webui_image: "ghcr.io/open-webui/open-webui:main"

# Primary
ctx_size: 4096
threads: 4

# Secondary small model
small_ctx_size: 2048
small_threads: 2

# Vision
vision_ctx_size: 2048
vision_threads: 2

# Whisper
whisper_model: "{{ lookup('env', 'WHISPER_MODEL') | default('base', true) }}"
```

### 3.4 Update `ansible/site.yml` - add new roles

```yaml
  roles:
    - base
    - model
    - llama
    - llama_small        # NEW
    - llama_vision       # NEW
    - whisper            # NEW
    - rag                # MODIFIED
    - webui
    - nginx              # MODIFIED
```

---

## 4. New role: `llama_small`

`ansible/roles/llama_small/tasks/main.yml`

```yaml
---
- name: Check if small model exists
  ansible.builtin.stat:
    path: "/opt/llama/models/{{ small_model_file }}"
  register: small_model_local

- name: Download small model from Hugging Face
  ansible.builtin.get_url:
    url: "{{ small_model_source_url }}"
    dest: "/opt/llama/models/{{ small_model_file }}"
    mode: "0644"
    owner: opc
    group: opc
    headers:
      Authorization: "Bearer {{ hf_token }}"
    timeout: 300
  when: not small_model_local.stat.exists

- name: Deploy llama-small systemd unit
  ansible.builtin.template:
    src: llama_small.service.j2
    dest: /etc/systemd/system/llama-small.service
    mode: "0644"

- name: Enable and start llama-small
  ansible.builtin.systemd:
    name: llama-small
    enabled: true
    state: started
    daemon_reload: true

- name: Wait for llama-small HTTP
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ llama_small_port }}/health"
    status_code: 200
  register: small_health
  retries: 30
  delay: 5
  until: small_health.status == 200
```

`ansible/roles/llama_small/templates/llama_small.service.j2`

```ini
[Unit]
Description=llama.cpp small (Qwen 2.5 0.5B) for routing and summarization
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=on-failure
RestartSec=10
ExecStartPre=-/usr/bin/podman rm -f llama-small
ExecStart=/usr/bin/podman run --rm --name llama-small \
  -p 127.0.0.1:{{ llama_small_port }}:{{ llama_small_port }} \
  -v /opt/llama/models:/models:Z \
  {{ llama_image }} \
  -m /models/{{ small_model_file }} \
  --host 0.0.0.0 --port {{ llama_small_port }} \
  --ctx-size {{ small_ctx_size }} \
  --threads {{ small_threads }} \
  --api-key dummy-internal-key
ExecStop=/usr/bin/podman stop -t 10 llama-small

[Install]
WantedBy=multi-user.target
```

---

## 5. New role: `llama_vision` (MoonDream2)

`ansible/roles/llama_vision/tasks/main.yml`

```yaml
---
- name: Check if vision model exists
  ansible.builtin.stat:
    path: "/opt/llama/models/{{ vision_model_file }}"
  register: vision_model_local

- name: Download vision model
  ansible.builtin.get_url:
    url: "{{ vision_model_source_url }}"
    dest: "/opt/llama/models/{{ vision_model_file }}"
    mode: "0644"
    owner: opc
    group: opc
    timeout: 600
  when: not vision_model_local.stat.exists

- name: Check if mmproj exists
  ansible.builtin.stat:
    path: "/opt/llama/models/{{ vision_mmproj_file }}"
  register: vision_mmproj_local

- name: Download mmproj (multimodal projector)
  ansible.builtin.get_url:
    url: "{{ vision_mmproj_source_url }}"
    dest: "/opt/llama/models/{{ vision_mmproj_file }}"
    mode: "0644"
    owner: opc
    group: opc
    timeout: 300
  when: not vision_mmproj_local.stat.exists

- name: Deploy llama-vision systemd unit
  ansible.builtin.template:
    src: llama_vision.service.j2
    dest: /etc/systemd/system/llama-vision.service
    mode: "0644"

- name: Enable and start llama-vision
  ansible.builtin.systemd:
    name: llama-vision
    enabled: true
    state: started
    daemon_reload: true

- name: Wait for llama-vision HTTP
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ vision_port }}/health"
    status_code: 200
  register: vision_health
  retries: 30
  delay: 5
  until: vision_health.status == 200
```

`ansible/roles/llama_vision/templates/llama_vision.service.j2`

```ini
[Unit]
Description=llama.cpp vision server (MoonDream2)
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Restart=on-failure
RestartSec=10
ExecStartPre=-/usr/bin/podman rm -f llama-vision
ExecStart=/usr/bin/podman run --rm --name llama-vision \
  -p 127.0.0.1:{{ vision_port }}:{{ vision_port }} \
  -v /opt/llama/models:/models:Z \
  {{ llama_image }} \
  -m /models/{{ vision_model_file }} \
  --mmproj /models/{{ vision_mmproj_file }} \
  --host 0.0.0.0 --port {{ vision_port }} \
  --ctx-size {{ vision_ctx_size }} \
  --threads {{ vision_threads }} \
  --api-key dummy-internal-key
ExecStop=/usr/bin/podman stop -t 10 llama-vision

[Install]
WantedBy=multi-user.target
```

---

## 6. New role: `whisper`

Builds whisper.cpp from source (it's ARM-native and fast). Runs the example HTTP server as a systemd unit.

`ansible/roles/whisper/tasks/main.yml`

```yaml
---
- name: Install build dependencies for whisper.cpp
  ansible.builtin.dnf:
    name:
      - git
      - cmake
      - gcc-c++
      - make
      - ffmpeg-free
    state: present

- name: Clone whisper.cpp
  ansible.builtin.git:
    repo: https://github.com/ggerganov/whisper.cpp.git
    dest: /opt/whisper.cpp
    version: master
    depth: 1
    update: false
  become_user: opc

- name: Build whisper.cpp with server support
  ansible.builtin.shell: |
    cd /opt/whisper.cpp
    cmake -B build -DWHISPER_BUILD_SERVER=ON -DGGML_NATIVE=ON
    cmake --build build --config Release -j 4 --target whisper-server
  args:
    creates: /opt/whisper.cpp/build/bin/whisper-server
  become_user: opc

- name: Download whisper model
  ansible.builtin.shell: |
    cd /opt/whisper.cpp
    bash ./models/download-ggml-model.sh {{ whisper_model }}
  args:
    creates: "/opt/whisper.cpp/models/ggml-{{ whisper_model }}.bin"
  become_user: opc

- name: Deploy whisper systemd unit
  ansible.builtin.template:
    src: whisper.service.j2
    dest: /etc/systemd/system/whisper.service
    mode: "0644"

- name: Enable and start whisper
  ansible.builtin.systemd:
    name: whisper
    enabled: true
    state: started
    daemon_reload: true

- name: Wait for whisper HTTP
  ansible.builtin.wait_for:
    host: 127.0.0.1
    port: "{{ whisper_port }}"
    timeout: 60
```

`ansible/roles/whisper/templates/whisper.service.j2`

```ini
[Unit]
Description=whisper.cpp HTTP transcription server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=opc
Group=opc
WorkingDirectory=/opt/whisper.cpp
ExecStart=/opt/whisper.cpp/build/bin/whisper-server \
  --host 127.0.0.1 \
  --port {{ whisper_port }} \
  --model /opt/whisper.cpp/models/ggml-{{ whisper_model }}.bin \
  --threads 2
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 7. Rewrite `rag` role - the meat of v3

Module layout under `ansible/roles/rag/files/`:

```
rag/
├── rag_api.py        # FastAPI routes
├── llm_client.py     # httpx wrapper, streaming
├── retrieval.py      # chroma + bge-m3 + reranker
├── ingestion.py      # PDF/docx/md parsing + chunking
├── memory.py         # sqlite conversation store
├── agent.py          # ReAct loop + tool registry
├── router.py         # picks model based on query
├── requirements.txt
└── seed.txt
```

### 7.1 `requirements.txt`

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
chromadb==0.5.5
sentence-transformers==3.0.1
httpx==0.27.2
pydantic==2.8.2
python-multipart==0.0.9
pypdf==4.3.1
python-docx==1.1.2
markdown==3.7
simpleeval==1.0.3
ddgs==9.0.0
beautifulsoup4==4.12.3
aiosqlite==0.20.0
sse-starlette==2.1.3
FlagEmbedding==1.3.2
```

### 7.2 `llm_client.py`

```python
"""Async HTTP client for llama.cpp servers with streaming support."""
import json
import os
from typing import AsyncIterator, Optional

import httpx

LLAMA_KEY = os.environ.get("LLAMA_INTERNAL_KEY", "dummy-internal-key")

PRIMARY = os.environ.get("LLAMA_URL", "http://127.0.0.1:8081")
SMALL   = os.environ.get("LLAMA_SMALL_URL", "http://127.0.0.1:8083")
VISION  = os.environ.get("LLAMA_VISION_URL", "http://127.0.0.1:8085")


def _headers():
    return {"Authorization": f"Bearer {LLAMA_KEY}", "Content-Type": "application/json"}


async def complete(messages, model: str = "primary", **kwargs) -> dict:
    base = {"primary": PRIMARY, "small": SMALL, "vision": VISION}[model]
    payload = {"messages": messages, **kwargs, "stream": False}
    async with httpx.AsyncClient(timeout=600) as h:
        r = await h.post(f"{base}/v1/chat/completions", json=payload, headers=_headers())
        r.raise_for_status()
        return r.json()


async def stream(messages, model: str = "primary", **kwargs) -> AsyncIterator[str]:
    """Yields raw SSE 'data: {...}' lines from the upstream llama.cpp server."""
    base = {"primary": PRIMARY, "small": SMALL, "vision": VISION}[model]
    payload = {"messages": messages, **kwargs, "stream": True}
    async with httpx.AsyncClient(timeout=600) as h:
        async with h.stream("POST", f"{base}/v1/chat/completions",
                            json=payload, headers=_headers()) as r:
            r.raise_for_status()
            async for line in r.aiter_lines():
                if line:
                    yield line
```

### 7.3 `retrieval.py`

```python
"""Chroma + bge-m3 embeddings + bge-reranker cross-encoder."""
import os
from typing import List

import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import CrossEncoder

CHROMA_DIR = os.environ.get("CHROMA_DIR", "/opt/llama/chroma")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.environ.get("RERANK_MODEL", "BAAI/bge-reranker-base")
COLLECTION = "docs"

_embedder = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
_client = chromadb.PersistentClient(path=CHROMA_DIR)
collection = _client.get_or_create_collection(name=COLLECTION, embedding_function=_embedder)

_reranker = None
def _get_reranker():
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(RERANK_MODEL, max_length=512)
    return _reranker


def add(documents: List[str], ids: List[str], metadatas: List[dict]):
    collection.add(documents=documents, ids=ids, metadatas=metadatas)


def query(text: str, top_k: int = 5, rerank_top_n: int = 3, use_reranker: bool = True):
    pool = max(top_k * 3, 15) if use_reranker else top_k
    raw = collection.query(query_texts=[text], n_results=pool)
    docs = raw["documents"][0]
    metas = raw["metadatas"][0]
    ids = raw["ids"][0]

    if not use_reranker or not docs:
        return list(zip(docs[:top_k], metas[:top_k], ids[:top_k]))

    rr = _get_reranker()
    scores = rr.predict([(text, d) for d in docs])
    ranked = sorted(zip(scores, docs, metas, ids), key=lambda x: -x[0])[:rerank_top_n]
    return [(d, m, i) for _, d, m, i in ranked]


def reset_collection():
    global collection
    try:
        _client.delete_collection(name=COLLECTION)
    except Exception:
        pass
    collection = _client.get_or_create_collection(name=COLLECTION, embedding_function=_embedder)


def count() -> int:
    return collection.count()
```

### 7.4 `ingestion.py`

```python
"""Parse PDF/DOCX/MD/TXT and chunk into Chroma-ready pieces."""
import re
from pathlib import Path
from typing import List, Tuple

import pypdf
from docx import Document as DocxDocument


def _chunk(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    text = re.sub(r"\s+\n", "\n", text).strip()
    if not text:
        return []
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buf = [], ""
    for p in paragraphs:
        if len(buf) + len(p) + 2 <= chunk_size:
            buf = (buf + "\n\n" + p).strip()
        else:
            if buf:
                chunks.append(buf)
            if len(p) > chunk_size:
                # Hard split long paragraph by sentences
                for i in range(0, len(p), chunk_size - overlap):
                    chunks.append(p[i:i + chunk_size])
                buf = ""
            else:
                buf = p
    if buf:
        chunks.append(buf)
    return chunks


def parse_pdf(path: Path) -> str:
    reader = pypdf.PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def parse_docx(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


def parse_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def ingest_file(path: Path) -> Tuple[List[str], List[str], List[dict]]:
    """Returns (chunks, ids, metadatas) ready for retrieval.add()."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = parse_pdf(path)
    elif suffix == ".docx":
        text = parse_docx(path)
    elif suffix in (".md", ".txt"):
        text = parse_text(path)
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    chunks = _chunk(text)
    stem = path.stem
    ids = [f"{stem}-{i}" for i in range(len(chunks))]
    metas = [{"source": path.name, "chunk": i} for i in range(len(chunks))]
    return chunks, ids, metas
```

### 7.5 `memory.py`

```python
"""SQLite conversation store with on-demand summarization."""
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from typing import List, Optional

DB_PATH = os.environ.get("MEMORY_DB", "/opt/llama/conversations.db")
MAX_MESSAGES_BEFORE_SUMMARY = int(os.environ.get("MAX_MESSAGES_BEFORE_SUMMARY", "20"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL DEFAULT 'default',
  title TEXT,
  summary TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  conv_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conv_id, created_at);
"""


@contextmanager
def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init():
    with _conn() as c:
        c.executescript(SCHEMA)


def create_session(user_id: str = "default", title: Optional[str] = None) -> str:
    cid = str(uuid.uuid4())
    now = time.time()
    with _conn() as c:
        c.execute(
            "INSERT INTO conversations(id, user_id, title, created_at, updated_at) VALUES (?,?,?,?,?)",
            (cid, user_id, title or "New chat", now, now),
        )
    return cid


def list_sessions(user_id: str = "default") -> List[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, title, summary, created_at, updated_at FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def delete_session(cid: str):
    with _conn() as c:
        c.execute("DELETE FROM conversations WHERE id = ?", (cid,))


def add_message(cid: str, role: str, content: str):
    mid = str(uuid.uuid4())
    now = time.time()
    with _conn() as c:
        c.execute(
            "INSERT INTO messages(id, conv_id, role, content, created_at) VALUES (?,?,?,?,?)",
            (mid, cid, role, content, now),
        )
        c.execute("UPDATE conversations SET updated_at = ? WHERE id = ?", (now, cid))


def get_messages(cid: str, limit: Optional[int] = None) -> List[dict]:
    q = "SELECT role, content, created_at FROM messages WHERE conv_id = ? ORDER BY created_at"
    params = [cid]
    if limit:
        q += " LIMIT ?"
        params.append(limit)
    with _conn() as c:
        rows = c.execute(q, params).fetchall()
    return [dict(r) for r in rows]


def get_summary(cid: str) -> Optional[str]:
    with _conn() as c:
        r = c.execute("SELECT summary FROM conversations WHERE id = ?", (cid,)).fetchone()
    return r["summary"] if r else None


def set_summary(cid: str, summary: str):
    with _conn() as c:
        c.execute("UPDATE conversations SET summary = ? WHERE id = ?", (summary, cid))


def count_messages(cid: str) -> int:
    with _conn() as c:
        return c.execute("SELECT COUNT(*) FROM messages WHERE conv_id = ?", (cid,)).fetchone()[0]


def build_context(cid: str, system_prompt: str) -> List[dict]:
    """Build messages list ready for /v1/chat/completions, including summary if any."""
    summary = get_summary(cid)
    msgs: List[dict] = [{"role": "system", "content": system_prompt}]
    if summary:
        msgs.append({"role": "system", "content": f"Conversation summary so far:\n{summary}"})
    recent = get_messages(cid, limit=MAX_MESSAGES_BEFORE_SUMMARY)
    for m in recent:
        msgs.append({"role": m["role"], "content": m["content"]})
    return msgs
```

### 7.6 `agent.py`

```python
"""ReAct-style agent with a small tool registry. Uses primary model."""
import json
import re
from typing import Any, Callable, Dict

import httpx
from ddgs import DDGS
from simpleeval import simple_eval

from . import llm_client, retrieval

# --- Tools -------------------------------------------------------------------

def tool_web_search(query: str) -> str:
    with DDGS() as ddg:
        results = list(ddg.text(query, max_results=5))
    if not results:
        return "(no results)"
    return "\n".join(f"- {r['title']}: {r['body'][:200]} ({r['href']})" for r in results[:5])


def tool_calculator(expression: str) -> str:
    try:
        return str(simple_eval(expression))
    except Exception as e:
        return f"error: {e}"


def tool_rag_search(query: str) -> str:
    if retrieval.count() == 0:
        return "(rag collection empty)"
    hits = retrieval.query(query, top_k=5, rerank_top_n=3)
    return "\n---\n".join(f"[{m.get('source','?')}] {d[:400]}" for d, m, _ in hits)


def tool_http_get(url: str) -> str:
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as h:
            r = h.get(url)
            r.raise_for_status()
            return r.text[:4000]
    except Exception as e:
        return f"error: {e}"


TOOLS: Dict[str, Callable[..., str]] = {
    "web_search": tool_web_search,
    "calculator": tool_calculator,
    "rag_search": tool_rag_search,
    "http_get": tool_http_get,
}

TOOL_SPEC = """You are an assistant that can use tools.

Tools available:
- web_search(query): general web search, returns 5 results
- calculator(expression): evaluate math, e.g. "2*(3+4)"
- rag_search(query): search the local knowledge base
- http_get(url): fetch the text content of a URL

On every turn you respond with EXACTLY one JSON object, no prose:
  {"action": "tool", "tool": "<name>", "args": {"<key>": "<value>"}}
or
  {"action": "respond", "content": "<final answer to the user>"}

Use tools when you need fresh, factual, or local information. Otherwise respond directly.
"""

_JSON_BLOCK = re.compile(r"\{[\s\S]*\}")


def _parse(text: str) -> Dict[str, Any]:
    m = _JSON_BLOCK.search(text)
    if not m:
        return {"action": "respond", "content": text.strip()}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"action": "respond", "content": text.strip()}


async def run(user_query: str, max_steps: int = 5) -> Dict[str, Any]:
    history = [
        {"role": "system", "content": TOOL_SPEC},
        {"role": "user", "content": user_query},
    ]
    trace = []
    for step in range(max_steps):
        resp = await llm_client.complete(history, model="primary", temperature=0.1, max_tokens=400)
        text = resp["choices"][0]["message"]["content"]
        parsed = _parse(text)
        trace.append({"step": step, "model_raw": text, "parsed": parsed})

        if parsed.get("action") == "respond":
            return {"answer": parsed.get("content", ""), "trace": trace}

        if parsed.get("action") == "tool":
            name = parsed.get("tool")
            args = parsed.get("args", {}) or {}
            if name not in TOOLS:
                obs = f"unknown tool '{name}'"
            else:
                try:
                    obs = TOOLS[name](**args)
                except TypeError as e:
                    obs = f"bad arguments: {e}"
                except Exception as e:
                    obs = f"tool error: {e}"
            history.append({"role": "assistant", "content": json.dumps(parsed)})
            history.append({"role": "user", "content": f"Observation: {obs}"})
            trace[-1]["observation"] = obs[:500]
            continue

        return {"answer": text, "trace": trace}

    return {"answer": "Max steps reached.", "trace": trace}
```

### 7.7 `router.py`

```python
"""Pick which backend model to use for a given task."""
import re

SHORT_THRESHOLD = 40         # words
COMPLEX_KEYWORDS = re.compile(
    r"\b(explain|why|how|compare|analyze|reason|step\s*by\s*step|architecture|design)\b",
    re.IGNORECASE,
)


def pick(prompt: str) -> str:
    """Return 'small' or 'primary' based on heuristics."""
    n_words = len(prompt.split())
    if n_words < SHORT_THRESHOLD and not COMPLEX_KEYWORDS.search(prompt):
        return "small"
    return "primary"
```

### 7.8 `rag_api.py` (rewritten)

```python
"""FastAPI app exposing /agent, /rag, /chat, /whisper-proxy, with streaming."""
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from . import agent, ingestion, llm_client, memory, retrieval, router

API_KEY = os.environ["API_KEY"]
WHISPER_URL = os.environ.get("WHISPER_URL", "http://127.0.0.1:8084")

app = FastAPI(title="llama-rag v3")
memory.init()


def _auth(x_api_key: Optional[str]):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


# ---------- Health ----------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "rag_count": retrieval.count()}


# ---------- RAG -------------------------------------------------------------

class QueryBody(BaseModel):
    query: str
    top_k: int = 5
    rerank_top_n: int = 3
    use_reranker: bool = True
    temperature: float = 0.2
    max_tokens: int = 400


@app.post("/rag/query")
async def rag_query(body: QueryBody, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    if retrieval.count() == 0:
        raise HTTPException(409, "collection is empty - ingest something first")
    hits = retrieval.query(body.query, top_k=body.top_k,
                           rerank_top_n=body.rerank_top_n,
                           use_reranker=body.use_reranker)
    contexts = [d for d, _, _ in hits]
    sources = [m for _, m, _ in hits]
    block = "\n\n".join(f"[{i+1}] {c}" for i, c in enumerate(contexts))
    messages = [
        {"role": "system", "content": "Answer strictly from the context. If absent, say you don't know."},
        {"role": "user", "content": f"Context:\n{block}\n\nQuestion: {body.query}"},
    ]
    resp = await llm_client.complete(messages, model="primary",
                                     temperature=body.temperature, max_tokens=body.max_tokens)
    return {
        "answer": resp["choices"][0]["message"]["content"],
        "contexts": contexts,
        "sources": sources,
        "usage": resp.get("usage"),
    }


@app.post("/rag/ingest")
async def rag_ingest(file: UploadFile = File(...), x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".docx", ".md", ".txt"):
        raise HTTPException(400, f"unsupported type {suffix}")
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    try:
        chunks, ids, metas = ingestion.ingest_file(tmp_path)
        if not chunks:
            return {"added": 0, "total": retrieval.count(), "message": "no extractable text"}
        # ensure unique ids
        ids = [f"{file.filename}-{i}" for i in range(len(chunks))]
        retrieval.add(chunks, ids, metas)
        return {"added": len(chunks), "total": retrieval.count(), "source": file.filename}
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/rag/reset")
def rag_reset(x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    retrieval.reset_collection()
    return {"reset": True}


# ---------- Conversation memory --------------------------------------------

class ChatBody(BaseModel):
    session_id: Optional[str] = None
    message: str
    use_rag: bool = False
    stream: bool = False
    system_prompt: str = "You are a helpful assistant."


@app.get("/chat/sessions")
def list_sessions(x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    return memory.list_sessions()


@app.post("/chat/sessions")
def create_session(x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    return {"id": memory.create_session()}


@app.delete("/chat/sessions/{cid}")
def delete_session(cid: str, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    memory.delete_session(cid)
    return {"deleted": cid}


@app.get("/chat/sessions/{cid}/messages")
def get_session_messages(cid: str, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    return memory.get_messages(cid)


async def _summarize_if_needed(cid: str):
    n = memory.count_messages(cid)
    if n < memory.MAX_MESSAGES_BEFORE_SUMMARY:
        return
    msgs = memory.get_messages(cid)
    half = msgs[: n // 2]
    summary_prompt = "Summarize this conversation concisely (max 200 words):\n\n" + \
        "\n".join(f"{m['role']}: {m['content']}" for m in half)
    resp = await llm_client.complete(
        [{"role": "user", "content": summary_prompt}],
        model="small", temperature=0.1, max_tokens=300,
    )
    memory.set_summary(cid, resp["choices"][0]["message"]["content"])


@app.post("/chat")
async def chat(body: ChatBody, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    cid = body.session_id or memory.create_session()

    # Optionally augment with RAG
    user_content = body.message
    if body.use_rag and retrieval.count() > 0:
        hits = retrieval.query(body.message, top_k=5, rerank_top_n=3)
        ctx = "\n\n".join(f"[{i+1}] {d}" for i, (d, _, _) in enumerate(hits))
        user_content = f"Context:\n{ctx}\n\nQuestion: {body.message}"

    memory.add_message(cid, "user", body.message)
    history = memory.build_context(cid, body.system_prompt)
    history[-1] = {"role": "user", "content": user_content}  # swap last user msg with augmented

    model = router.pick(body.message)

    if body.stream:
        async def gen():
            buf = ""
            async for line in llm_client.stream(history, model=model, temperature=0.7, max_tokens=600):
                yield {"event": "message", "data": line}
                if line.startswith("data: "):
                    try:
                        payload = json.loads(line[6:])
                        delta = payload["choices"][0]["delta"].get("content") or ""
                        buf += delta
                    except Exception:
                        pass
            memory.add_message(cid, "assistant", buf)
            await _summarize_if_needed(cid)
            yield {"event": "end", "data": json.dumps({"session_id": cid})}

        return EventSourceResponse(gen())

    resp = await llm_client.complete(history, model=model, temperature=0.7, max_tokens=600)
    answer = resp["choices"][0]["message"]["content"]
    memory.add_message(cid, "assistant", answer)
    await _summarize_if_needed(cid)
    return {"session_id": cid, "answer": answer, "model_used": model, "usage": resp.get("usage")}


# ---------- Agent (function calling) ---------------------------------------

class AgentBody(BaseModel):
    query: str
    max_steps: int = 5


@app.post("/agent/run")
async def agent_run(body: AgentBody, x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    return await agent.run(body.query, max_steps=body.max_steps)


# ---------- Whisper proxy --------------------------------------------------

@app.post("/whisper/transcribe")
async def whisper_transcribe(file: UploadFile = File(...),
                             language: str = Form("auto"),
                             x_api_key: Optional[str] = Header(None)):
    _auth(x_api_key)
    content = await file.read()
    async with httpx.AsyncClient(timeout=600) as h:
        files = {"file": (file.filename, content, file.content_type or "audio/wav")}
        data = {"language": language, "response_format": "json"}
        r = await h.post(f"{WHISPER_URL}/inference", files=files, data=data)
        r.raise_for_status()
        return r.json()


# ---------- Vision proxy ---------------------------------------------------

@app.post("/v1/vision/chat/completions")
async def vision_chat(body: dict, x_api_key: Optional[str] = Header(None)):
    """Pass-through to the vision llama.cpp instance. Accepts OpenAI vision format."""
    _auth(x_api_key)
    resp = await llm_client.complete(
        body.get("messages", []),
        model="vision",
        temperature=body.get("temperature", 0.2),
        max_tokens=body.get("max_tokens", 400),
    )
    return resp
```

### 7.9 Updated `ansible/roles/rag/tasks/main.yml`

```yaml
---
- name: Copy RAG package
  ansible.builtin.copy:
    src: "{{ item }}"
    dest: "/opt/llama/rag/{{ item }}"
    owner: opc
    group: opc
    mode: "0644"
  loop:
    - rag_api.py
    - llm_client.py
    - retrieval.py
    - ingestion.py
    - memory.py
    - agent.py
    - router.py
    - requirements.txt
    - seed.txt

- name: Create __init__.py so the package imports work
  ansible.builtin.copy:
    dest: /opt/llama/rag/__init__.py
    content: ""
    owner: opc
    group: opc
    mode: "0644"

- name: Create Python venv
  ansible.builtin.command: python3 -m venv /opt/llama/rag/venv
  args:
    creates: /opt/llama/rag/venv/bin/python

- name: Upgrade pip
  ansible.builtin.pip:
    name: ["pip", "wheel", "setuptools"]
    state: latest
    virtualenv: /opt/llama/rag/venv

- name: Install RAG dependencies (this triggers model downloads, may take 10+ min)
  ansible.builtin.pip:
    requirements: /opt/llama/rag/requirements.txt
    virtualenv: /opt/llama/rag/venv

- name: Pre-fetch embedding + reranker models (~2.3 GB total)
  ansible.builtin.shell: |
    /opt/llama/rag/venv/bin/python -c "
    from sentence_transformers import SentenceTransformer, CrossEncoder
    SentenceTransformer('BAAI/bge-m3')
    CrossEncoder('BAAI/bge-reranker-base')
    "
  args:
    creates: /home/opc/.cache/huggingface/hub/models--BAAI--bge-m3
  become_user: opc

- name: Fix ownership
  ansible.builtin.file:
    path: /opt/llama/rag
    state: directory
    recurse: true
    owner: opc
    group: opc

- name: Deploy RAG systemd unit
  ansible.builtin.template:
    src: rag.service.j2
    dest: /etc/systemd/system/rag.service
    mode: "0644"

- name: Enable and start RAG
  ansible.builtin.systemd:
    name: rag
    enabled: true
    state: started
    daemon_reload: true

- name: Wait for RAG health
  ansible.builtin.uri:
    url: "http://127.0.0.1:{{ rag_port }}/health"
    status_code: 200
  register: rag_health
  retries: 60
  delay: 10
  until: rag_health.status == 200
```

### 7.10 Updated `ansible/roles/rag/templates/rag.service.j2`

```ini
[Unit]
Description=RAG API v3
After=network-online.target llama.service llama-small.service llama-vision.service whisper.service
Wants=network-online.target

[Service]
Type=simple
User=opc
Group=opc
WorkingDirectory=/opt/llama
EnvironmentFile=/etc/llama.env
Environment=CHROMA_DIR=/opt/llama/chroma
Environment=MEMORY_DB=/opt/llama/conversations.db
Environment=LLAMA_URL=http://127.0.0.1:{{ llama_port }}
Environment=LLAMA_SMALL_URL=http://127.0.0.1:{{ llama_small_port }}
Environment=LLAMA_VISION_URL=http://127.0.0.1:{{ vision_port }}
Environment=WHISPER_URL=http://127.0.0.1:{{ whisper_port }}
Environment=LLAMA_INTERNAL_KEY=dummy-internal-key
ExecStart=/opt/llama/rag/venv/bin/uvicorn rag.rag_api:app --host 127.0.0.1 --port {{ rag_port }}
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

> Note: `WorkingDirectory=/opt/llama` so `from rag import ...` resolves correctly with the package layout.

---

## 8. Updated `nginx` config

`ansible/roles/nginx/templates/llama.conf.j2`

```nginx
map $http_x_api_key $api_key_valid {
    default 0;
    "{{ api_key }}" 1;
}

server {
    listen 80 default_server;
    server_name _;
    client_max_body_size 100m;  # bumped for audio + PDFs

    location = /health { access_log off; default_type text/plain; return 200 "ok\n"; }

    # Primary OpenAI API
    location /v1/chat/completions {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ llama_port }}/v1/chat/completions;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_read_timeout 600s;
        proxy_buffering off;       # critical for SSE streaming
        proxy_cache off;
    }

    # Small model
    location /v1/small/ {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ llama_small_port }}/v1/;
        proxy_http_version 1.1;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    # Vision (goes through RAG service for auth + routing)
    location /v1/vision/ {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ rag_port }}/v1/vision/;
        proxy_http_version 1.1;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    # Models listing (combined - simple alias to primary)
    location = /v1/models {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ llama_port }}/v1/models;
    }

    # RAG, agent, chat, whisper
    location /rag/ {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ rag_port }}/rag/;
        client_max_body_size 100m;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    location /agent/ {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ rag_port }}/agent/;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    location /chat {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ rag_port }}/chat;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    location /chat/ {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ rag_port }}/chat/;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    location /whisper/ {
        if ($api_key_valid = 0) { return 401; }
        proxy_pass http://127.0.0.1:{{ rag_port }}/whisper/;
        client_max_body_size 100m;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }

    # Open WebUI fallback
    location / {
        proxy_pass http://127.0.0.1:{{ webui_port }}/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 600s;
        proxy_buffering off;
    }
}
```

---

## 9. Updated Makefile targets

Append to the existing Makefile:

```makefile
.PHONY: test-v3 ingest-pdf transcribe agent-test stream-test vision-test

test-v3: ## End-to-end smoke test of v3 features
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip); \
	  echo "--- Agent ---"; \
	  curl -fsS http://$$IP/agent/run -H "X-API-Key: $$API_KEY" -H "Content-Type: application/json" \
	    -d '{"query":"What is 17 * 23?"}' | jq .answer; \
	  echo "--- Chat with session memory ---"; \
	  SID=$$(curl -fsS -X POST http://$$IP/chat/sessions -H "X-API-Key: $$API_KEY" | jq -r .id); \
	  echo "Session: $$SID"; \
	  curl -fsS http://$$IP/chat -H "X-API-Key: $$API_KEY" -H "Content-Type: application/json" \
	    -d "{\"session_id\":\"$$SID\",\"message\":\"My name is Leandro.\"}" | jq .answer; \
	  curl -fsS http://$$IP/chat -H "X-API-Key: $$API_KEY" -H "Content-Type: application/json" \
	    -d "{\"session_id\":\"$$SID\",\"message\":\"What did I just tell you my name was?\"}" | jq .answer

ingest-pdf: ## Upload a PDF: make ingest-pdf FILE=path/to/doc.pdf
	@[ -n "$(FILE)" ] || { echo "Usage: make ingest-pdf FILE=path"; exit 1; }
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip); \
	  curl -fsS -X POST http://$$IP/rag/ingest -H "X-API-Key: $$API_KEY" \
	    -F "file=@$(FILE)" | jq .

transcribe: ## Transcribe audio: make transcribe FILE=audio.wav
	@[ -n "$(FILE)" ] || { echo "Usage: make transcribe FILE=path.wav"; exit 1; }
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip); \
	  curl -fsS -X POST http://$$IP/whisper/transcribe -H "X-API-Key: $$API_KEY" \
	    -F "file=@$(FILE)" | jq .

stream-test: ## Test SSE streaming on /chat
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip); \
	  curl -N http://$$IP/chat -H "X-API-Key: $$API_KEY" -H "Content-Type: application/json" \
	    -d '{"message":"Count from 1 to 10 slowly.","stream":true}'

vision-test: ## Test image understanding: make vision-test IMG=cat.jpg
	@[ -n "$(IMG)" ] || { echo "Usage: make vision-test IMG=path.jpg"; exit 1; }
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip); \
	  B64=$$(base64 -w0 < $(IMG)); \
	  curl -fsS http://$$IP/v1/vision/chat/completions -H "X-API-Key: $$API_KEY" \
	    -H "Content-Type: application/json" \
	    -d "{\"messages\":[{\"role\":\"user\",\"content\":[{\"type\":\"text\",\"text\":\"Describe this image.\"},{\"type\":\"image_url\",\"image_url\":{\"url\":\"data:image/jpeg;base64,$$B64\"}}]}],\"max_tokens\":200}" | jq .choices[0].message.content
```

Update the existing `logs` target to include the new units:

```makefile
logs: ## Tail logs
	@cd $(TF_DIR) && IP=$$(terraform output -raw public_ip) && \
	  ssh -i $$TF_VAR_ssh_private_key_path opc@$$IP \
	    "sudo journalctl -u llama -u llama-small -u llama-vision -u whisper -u rag -u webui -f"
```

---

## 10. Execution

After v2 is deployed and working:

```bash
# 1. Add new env vars and resize boot volume
source .env

# 2. Bump boot volume in terraform/variables.tf (50 -> 80)
make tf-apply
make ssh -- "sudo /usr/libexec/oci-growfs -y"

# 3. Re-render Ansible inventory with new variables
cd terraform && terraform apply -auto-approve && cd ..

# 4. Run the playbook - new roles install everything
make ansible-deploy

# 5. Smoke test
make test-v3
make stream-test
```

First run downloads:
- Qwen 2.5 0.5B GGUF: ~400 MB
- MoonDream2 + mmproj: ~3 GB
- Whisper base model: ~150 MB
- bge-m3 + bge-reranker-base: ~2.3 GB
- New Python deps: ~1.5 GB

Plan ~15-20 min of downloads on first deploy.

---

## 11. Validation per feature

| Feature | Quick check |
|---------|-------------|
| Function calling | `curl /agent/run -d '{"query":"What is 17 * 23?"}'` → answer "391" with trace showing calculator |
| Streaming | `make stream-test` shows tokens arriving incrementally |
| PDF ingestion | `make ingest-pdf FILE=test.pdf` returns `added > 0` |
| Memory | `make test-v3` - second message recalls the name |
| Small model routing | `curl /chat -d '{"message":"hi"}'` returns `"model_used":"small"` |
| Whisper | `make transcribe FILE=sample.wav` returns transcribed text |
| bge-m3 + reranker | `curl /rag/query` - sources are clearly relevant; check `make ssh -- "ls ~/.cache/huggingface/hub"` shows bge-m3 |
| Vision | `make vision-test IMG=cat.jpg` returns image description |

---

## 12. Troubleshooting (delta)

| Symptom | Action |
|---------|--------|
| RAG service OOM on startup | bge-m3 needs ~2 GB to load; check `free -h`; stop unused container with `sudo systemctl stop llama-vision` and restart |
| `sentence-transformers` model download fails | `make ssh -- "rm -rf ~/.cache/huggingface && sudo systemctl restart rag"` |
| Vision returns gibberish | mmproj file mismatch with text model; verify both moondream2 files downloaded from the same HF revision |
| Agent loops forever | Lower `max_steps` to 3; small model can struggle with strict JSON output - check `trace` for parse failures |
| Streaming hangs | NGINX must have `proxy_buffering off`; verify with `make ssh -- "sudo nginx -T \| grep -A2 buffering"` |
| PDF ingestion returns 0 chunks | Scanned PDF (no text layer); use OCR upstream (Tesseract) before ingest |
| Whisper "unknown format" | Re-encode input: `ffmpeg -i input.m4a -ar 16000 -ac 1 output.wav` |
| Out of disk | Boot volume not resized; run `df -h /` and `sudo /usr/libexec/oci-growfs -y` |
| Memory DB locked | Concurrent writes - SQLite is fine for single-user; if multi-user, switch to WAL mode (`PRAGMA journal_mode=WAL`) |

---

## 13. References

- llama.cpp server (streaming, tool calling, vision): https://github.com/ggerganov/llama.cpp/tree/master/examples/server
- MoonDream2 model card: https://huggingface.co/vikhyatk/moondream2
- Qwen 2.5 0.5B Instruct GGUF: https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF
- whisper.cpp server: https://github.com/ggerganov/whisper.cpp/tree/master/examples/server
- BAAI bge-m3 multilingual embeddings: https://huggingface.co/BAAI/bge-m3
- BAAI bge-reranker-base: https://huggingface.co/BAAI/bge-reranker-base
- ChromaDB: https://docs.trychroma.com/
- pypdf: https://pypdf.readthedocs.io/
- python-docx: https://python-docx.readthedocs.io/
- ddgs (DuckDuckGo search): https://github.com/deedy5/ddgs
- simpleeval (sandboxed math): https://github.com/danthedeckie/simpleeval
- sse-starlette: https://github.com/sysid/sse-starlette
- FastAPI: https://fastapi.tiangolo.com/

---

**End of v3 supplement.** Codex should apply this on top of v2, then run section 10. Report section 11 results.

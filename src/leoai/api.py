from __future__ import annotations

import csv
import hmac
import io
import json
from typing import Literal, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from .assistant import LeoAIAssistant
from .config import get_settings
from .connectors.object_storage_loader import load_object_text
from .connectors.web_loader import load_web_document
from .embeddings import build_embedder
from .file_store import FileStore
from .knowledge_base import KnowledgeBase


app = FastAPI(title="LeoAI API", version="0.4.0")

GUI_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LeoAI Workspace</title>
  <style>
    :root {
      --bg: #f7f9fc;
      --paper: #ffffff;
      --line: #d7dfeb;
      --text: #1b2a41;
      --muted: #556b8a;
      --brand: #1677ff;
      --brand-2: #0ea5e9;
      --ok: #16a34a;
      --warn: #ca8a04;
      --danger: #dc2626;
      --shadow: 0 18px 40px rgba(14, 30, 68, 0.08);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        linear-gradient(120deg, rgba(22,119,255,0.12), transparent 35%),
        linear-gradient(210deg, rgba(14,165,233,0.10), transparent 30%),
        var(--bg);
      min-height: 100vh;
    }
    .shell { max-width: 1200px; margin: 0 auto; padding: 28px 20px 30px; }
    .hero { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; margin-bottom:16px; }
    .title { margin:0; font-size:clamp(1.8rem,1.2rem + 1.8vw,3rem); font-weight:800; letter-spacing:-0.02em; }
    .subtitle { margin:8px 0 0; color:var(--muted); font-size:1rem; }
    .status {
      display:inline-flex; align-items:center; gap:8px; padding:10px 12px; border-radius:999px;
      border:1px solid var(--line); background:#fff; color:var(--muted); font-size:.88rem; white-space:nowrap;
    }
    .dot { width:9px; height:9px; border-radius:50%; background:var(--warn); }
    .auth {
      display:grid; grid-template-columns:1fr auto auto; gap:10px;
      background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:12px; box-shadow:var(--shadow);
      margin-bottom:16px;
    }
    .workspace { display:grid; grid-template-columns:1.4fr 1fr; gap:16px; }
    .card {
      background:var(--paper); border:1px solid var(--line); border-radius:18px; box-shadow:var(--shadow);
      overflow:hidden;
    }
    .card-head {
      padding:14px 16px; border-bottom:1px solid var(--line); display:flex; justify-content:space-between; align-items:center; gap:10px;
    }
    .card-head h2 { margin:0; font-size:1.1rem; }
    .card-body { padding:14px 16px; }
    .log { height:min(44vh,460px); overflow:auto; background:#f8fbff; border:1px solid var(--line); border-radius:12px; padding:12px; }
    .msg { max-width:88%; margin:0 0 10px; padding:10px 12px; border-radius:12px; line-height:1.45; white-space:pre-wrap; word-break:break-word; }
    .user { margin-left:auto; background:linear-gradient(135deg, #1d4ed8, #0ea5e9); color:#fff; border-bottom-right-radius:4px; }
    .bot { margin-right:auto; background:#fff; border:1px solid var(--line); color:var(--text); border-bottom-left-radius:4px; }
    .sys { margin:0 auto 10px; text-align:center; font-size:.85rem; color:var(--muted); background:#f3f7fd; border:1px dashed #c4d2e8; }
    .composer { display:grid; grid-template-columns:1fr auto; gap:10px; margin-top:12px; }
    .opts { display:flex; flex-wrap:wrap; gap:12px; margin-top:8px; color:var(--muted); font-size:.9rem; }
    .exports { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
    .files-actions { display:grid; grid-template-columns:1fr auto auto; gap:8px; margin-bottom:10px; }
    .file-list {
      border:1px solid var(--line); border-radius:12px; overflow:auto; max-height:300px;
    }
    table { width:100%; border-collapse:collapse; font-size:.9rem; }
    th, td { padding:10px; border-bottom:1px solid #edf2fa; text-align:left; }
    th { background:#f6f9ff; color:#4a607f; position:sticky; top:0; z-index:1; }
    tr:last-child td { border-bottom:0; }
    input, textarea, select {
      width:100%; border:1px solid #c7d4e8; background:#fff; color:var(--text);
      border-radius:11px; padding:10px 12px; font:inherit; outline:none;
    }
    textarea { resize:vertical; min-height:70px; max-height:180px; }
    input:focus, textarea:focus, select:focus {
      border-color:var(--brand); box-shadow:0 0 0 3px rgba(22,119,255,.14);
    }
    button {
      height:42px; padding:0 14px; border:0; border-radius:11px; cursor:pointer; font-weight:700;
      background:linear-gradient(135deg, var(--brand), var(--brand-2)); color:#fff;
    }
    .btn-soft { background:#edf4ff; color:#18406f; border:1px solid #c9daf5; }
    .btn-danger { background:#fee2e2; color:#9f1239; border:1px solid #fecaca; }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    .muted { color: var(--muted); }
    .row { display:flex; gap:8px; align-items:center; }
    .foot { margin-top:12px; color:var(--muted); font-size:.85rem; display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; }
    @media (max-width: 980px) {
      .workspace { grid-template-columns:1fr; }
      .auth { grid-template-columns:1fr; }
      .files-actions { grid-template-columns:1fr; }
      .composer { grid-template-columns:1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <h1 class="title">LeoAI Workspace</h1>
        <p class="subtitle">Auth, chat, RAG v2 e gerenciamento de arquivos em um único fluxo.</p>
      </div>
      <div class="status"><span class="dot" id="dot"></span><span id="status">Aguardando auth...</span></div>
    </header>

    <div class="auth" id="authBar">
      <input id="apiKey" type="password" placeholder="LEOAI API key (X-API-Key)" />
      <button id="saveKeyBtn" type="button">Salvar key</button>
      <button id="verifyBtn" type="button">Verificar</button>
    </div>

    <section class="workspace">
      <article class="card">
        <div class="card-head">
          <h2>Chat</h2>
          <span class="muted">POST /chat</span>
        </div>
        <div class="card-body">
          <div class="log" id="log"></div>
          <form class="composer" id="chatForm">
            <div>
              <textarea id="message" placeholder="Digite sua mensagem..." required></textarea>
              <div class="opts">
                <label><input id="withWeb" type="checkbox" /> pesquisar web</label>
                <label><input id="withRag" type="checkbox" checked /> usar RAG v2</label>
              </div>
            </div>
            <button id="sendBtn" type="submit">Enviar</button>
          </form>
          <div class="exports">
            <input id="exportFilename" type="text" placeholder="ex.: resposta.md" />
            <select id="exportFormat">
              <option value="txt">TXT</option>
              <option value="md">Markdown</option>
              <option value="json">JSON</option>
              <option value="csv">CSV</option>
            </select>
            <button id="exportBtn" type="button" class="btn-soft">Exportar resposta</button>
          </div>
        </div>
      </article>

      <article class="card">
        <div class="card-head">
          <h2>Files Hub</h2>
          <span class="muted">Upload até 10 arquivos</span>
        </div>
        <div class="card-body">
          <div class="files-actions">
            <input id="filesInput" type="file" multiple />
            <label class="row"><input id="addToRag" type="checkbox" /> indexar no RAG</label>
            <button id="uploadBtn" type="button">Upload</button>
          </div>
          <div class="row" style="margin-bottom:10px;">
            <select id="fileKindFilter">
              <option value="">Todos</option>
              <option value="uploaded">Uploaded</option>
              <option value="generated">Generated</option>
            </select>
            <button id="refreshFilesBtn" type="button" class="btn-soft">Atualizar</button>
          </div>
          <div class="file-list">
            <table>
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>Tipo</th>
                  <th>Tamanho</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody id="filesTableBody"></tbody>
            </table>
          </div>
          <p class="muted" style="margin:10px 0 0;">Use upload, listagem e download direto da interface.</p>
        </div>
      </article>
    </section>

    <div class="foot">
      <span>Auth header: <span class="mono">X-API-Key</span></span>
      <span>Endpoints: <span class="mono">/chat /files/* /chat/export</span></span>
    </div>
  </main>

  <script>
    const logEl = document.getElementById("log");
    const formEl = document.getElementById("chatForm");
    const msgEl = document.getElementById("message");
    const sendBtn = document.getElementById("sendBtn");
    const withWebEl = document.getElementById("withWeb");
    const withRagEl = document.getElementById("withRag");
    const statusEl = document.getElementById("status");
    const dotEl = document.getElementById("dot");
    const apiKeyEl = document.getElementById("apiKey");
    const authBarEl = document.getElementById("authBar");
    const saveKeyBtn = document.getElementById("saveKeyBtn");
    const verifyBtn = document.getElementById("verifyBtn");
    const exportBtn = document.getElementById("exportBtn");
    const exportFilenameEl = document.getElementById("exportFilename");
    const exportFormatEl = document.getElementById("exportFormat");
    const filesInputEl = document.getElementById("filesInput");
    const addToRagEl = document.getElementById("addToRag");
    const uploadBtn = document.getElementById("uploadBtn");
    const refreshFilesBtn = document.getElementById("refreshFilesBtn");
    const fileKindFilterEl = document.getElementById("fileKindFilter");
    const filesTableBodyEl = document.getElementById("filesTableBody");
    let lastPrompt = "";
    let lastAnswer = "";

    function addMessage(kind, text) {
      const div = document.createElement("div");
      div.className = `msg ${kind}`;
      div.textContent = text;
      logEl.appendChild(div);
      logEl.scrollTop = logEl.scrollHeight;
    }

    function setStatus(kind, text) {
      statusEl.textContent = text;
      if (kind === "ok") dotEl.style.background = "#42d392";
      if (kind === "warn") dotEl.style.background = "#ffd166";
      if (kind === "err") dotEl.style.background = "#ef476f";
    }

    function getApiKey() {
      return localStorage.getItem("leoai_api_key") || "";
    }

    function authHeaders() {
      const key = getApiKey();
      return key ? { "X-API-Key": key } : {};
    }

    async function autoDetectAuthMode() {
      try {
        const response = await fetch("/auth/verify", { headers: authHeaders() });
        if (response.ok) {
          setStatus("ok", "Auth automática ativa");
          authBarEl.style.display = "none";
          addMessage("sys", "Sessão pronta sem entrada manual de key.");
          return;
        }
      } catch (_) {}
      setStatus("warn", "Aguardando auth...");
    }

    async function downloadById(fileId, filename) {
      const response = await fetch(`/files/${encodeURIComponent(fileId)}/download`, { headers: authHeaders() });
      if (!response.ok) {
        const maybe = await response.text();
        throw new Error(maybe || `Falha no download (${response.status})`);
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename || `file-${fileId}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    }

    function renderFiles(items) {
      filesTableBodyEl.innerHTML = "";
      if (!items.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = '<td colspan="4" class="muted">Nenhum arquivo encontrado.</td>';
        filesTableBodyEl.appendChild(tr);
        return;
      }
      for (const item of items) {
        const tr = document.createElement("tr");
        const sizeKb = `${Math.max(1, Math.round((item.size_bytes || 0) / 1024))} KB`;
        tr.innerHTML = `
          <td>${item.original_name || "(sem nome)"}</td>
          <td>${item.kind || "-"}</td>
          <td>${sizeKb}</td>
          <td><button type="button" class="btn-soft" data-file-id="${item.file_id}" data-name="${item.original_name || ""}">Download</button></td>
        `;
        filesTableBodyEl.appendChild(tr);
      }
      for (const btn of filesTableBodyEl.querySelectorAll("button[data-file-id]")) {
        btn.addEventListener("click", async () => {
          try {
            await downloadById(btn.dataset.fileId, btn.dataset.name);
          } catch (err) {
            addMessage("bot", `Erro no download: ${err.message}`);
          }
        });
      }
    }

    async function refreshFiles() {
      const kind = fileKindFilterEl.value;
      const qs = kind ? `?kind=${encodeURIComponent(kind)}` : "";
      const response = await fetch(`/files${qs}`, { headers: authHeaders() });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || `Erro HTTP ${response.status}`);
      renderFiles(payload.files || []);
    }

    saveKeyBtn.addEventListener("click", () => {
      localStorage.setItem("leoai_api_key", apiKeyEl.value.trim());
      addMessage("sys", "API key salva no navegador.");
    });

    verifyBtn.addEventListener("click", async () => {
      setStatus("warn", "Verificando auth...");
      try {
        const response = await fetch("/auth/verify", { headers: authHeaders() });
        if (!response.ok) throw new Error("API key inválida");
        setStatus("ok", "Auth OK");
        addMessage("sys", "Autenticação validada.");
      } catch (err) {
        setStatus("err", "Auth falhou");
        addMessage("sys", `Falha de auth: ${err.message}`);
      }
    });

    formEl.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = msgEl.value.trim();
      if (!text) return;
      addMessage("user", text);
      msgEl.value = "";
      sendBtn.disabled = true;
      setStatus("warn", "Processando...");
      try {
        const response = await fetch("/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({
            message: text,
            with_web: Boolean(withWebEl.checked),
            with_rag: Boolean(withRagEl.checked),
          }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || `Erro HTTP ${response.status}`);
        addMessage("bot", payload.response || "(sem conteúdo)");
        lastPrompt = text;
        lastAnswer = payload.response || "";
        setStatus("ok", "Online");
      } catch (err) {
        addMessage("bot", `Erro: ${err.message}`);
        setStatus("err", "Falha");
      } finally {
        sendBtn.disabled = false;
        msgEl.focus();
      }
    });

    exportBtn.addEventListener("click", async () => {
      if (!lastPrompt || !lastAnswer) {
        addMessage("sys", "Envie uma pergunta antes de exportar.");
        return;
      }
      const filename = exportFilenameEl.value.trim() || `leoai-export.${exportFormatEl.value}`;
      try {
        const response = await fetch("/chat/export", {
          method: "POST",
          headers: { "Content-Type": "application/json", ...authHeaders() },
          body: JSON.stringify({
            message: lastPrompt,
            with_web: Boolean(withWebEl.checked),
            with_rag: Boolean(withRagEl.checked),
            filename,
            file_format: exportFormatEl.value,
          }),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || `Erro HTTP ${response.status}`);
        await downloadById(payload.generated_file.file_id, payload.generated_file.original_name);
        addMessage("sys", `Arquivo exportado: ${payload.generated_file.original_name}`);
      } catch (err) {
        addMessage("bot", `Erro na exportação: ${err.message}`);
      }
    });

    uploadBtn.addEventListener("click", async () => {
      const files = Array.from(filesInputEl.files || []);
      if (!files.length) {
        addMessage("sys", "Selecione arquivos para upload.");
        return;
      }
      if (files.length > 10) {
        addMessage("sys", "Máximo de 10 arquivos por upload.");
        return;
      }
      const formData = new FormData();
      for (const file of files) formData.append("files", file);
      formData.append("add_to_rag", addToRagEl.checked ? "true" : "false");
      uploadBtn.disabled = true;
      try {
        const response = await fetch("/files/upload", {
          method: "POST",
          headers: { ...authHeaders() },
          body: formData,
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || `Erro HTTP ${response.status}`);
        addMessage("sys", `Upload concluído: ${payload.uploaded.length} arquivo(s).`);
        await refreshFiles();
      } catch (err) {
        addMessage("bot", `Erro no upload: ${err.message}`);
      } finally {
        uploadBtn.disabled = false;
      }
    });

    refreshFilesBtn.addEventListener("click", async () => {
      try {
        await refreshFiles();
      } catch (err) {
        addMessage("bot", `Erro ao listar arquivos: ${err.message}`);
      }
    });

    fileKindFilterEl.addEventListener("change", async () => {
      try {
        await refreshFiles();
      } catch (err) {
        addMessage("bot", `Erro ao listar arquivos: ${err.message}`);
      }
    });

    msgEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        formEl.requestSubmit();
      }
    });

    apiKeyEl.value = getApiKey();
    addMessage("sys", "Use chat/files no painel. Auth automática é detectada ao carregar.");
    autoDetectAuthMode().catch(() => {});
    refreshFiles().catch(() => {});
  </script>
</body>
</html>
"""


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    with_web: bool = False
    with_rag: bool = True


class ObjectStorageIngestRequest(BaseModel):
    namespace_name: str = Field(min_length=1)
    bucket_name: str = Field(min_length=1)
    object_name: str = Field(min_length=1)
    title: str = ""


class WebIngestRequest(BaseModel):
    source_type: Literal["confluence", "sharepoint"]
    url: str = Field(min_length=1)
    title: str = ""
    auth_header: str = Field(default="", description="Ex.: Bearer <token>")


class ChatExportRequest(BaseModel):
    message: str = Field(min_length=1)
    with_web: bool = False
    with_rag: bool = True
    filename: str = Field(min_length=1)
    file_format: Literal["txt", "md", "json", "csv"] = "txt"


class GenerateFileRequest(BaseModel):
    filename: str = Field(min_length=1)
    content: str
    content_type: str = "text/plain; charset=utf-8"


def _embedding_input(text: str, max_chars: int = 4000) -> str:
    return text.strip()[:max_chars]


def _build_chat_answer(prompt: str, with_web: bool, with_rag: bool) -> str:
    settings = get_settings()
    kb = KnowledgeBase(settings.rag_store_path)
    embedder = build_embedder(settings)
    rag_context = ""
    if settings.rag_enabled and with_rag:
        rag_context = kb.retrieve_context(
            prompt,
            top_k=3,
            embedder=embedder,
            rerank_alpha=settings.rag_rerank_alpha,
        )

    assistant = LeoAIAssistant(settings)
    return assistant.ask_with_options(
        user_message=prompt,
        use_web_search=with_web,
        extra_context=rag_context,
    )


def _serialize_file_meta(item: object) -> dict[str, str | int]:
    return {
        "file_id": str(getattr(item, "file_id")),
        "kind": str(getattr(item, "kind")),
        "original_name": str(getattr(item, "original_name")),
        "content_type": str(getattr(item, "content_type")),
        "size_bytes": int(getattr(item, "size_bytes")),
        "created_at": str(getattr(item, "created_at")),
        "sha256": str(getattr(item, "sha256")),
    }


def _build_export_bytes(prompt: str, answer: str, file_format: str) -> tuple[bytes, str]:
    if file_format == "md":
        content = f"# Prompt\n\n{prompt}\n\n# Resposta\n\n{answer}\n"
        return content.encode("utf-8"), "text/markdown; charset=utf-8"
    if file_format == "json":
        payload = {"prompt": prompt, "response": answer}
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"), "application/json"
    if file_format == "csv":
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(["prompt", "response"])
        writer.writerow([prompt, answer])
        return out.getvalue().encode("utf-8"), "text/csv; charset=utf-8"
    return answer.encode("utf-8"), "text/plain; charset=utf-8"


def require_api_key(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")) -> None:
    settings = get_settings()
    if not settings.api_auth_enabled:
        return
    if not x_api_key or not hmac.compare_digest(x_api_key, settings.api_auth_key):
        raise HTTPException(status_code=401, detail="API key inválida.")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return GUI_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/auth/verify", dependencies=[Depends(require_api_key)])
def auth_verify() -> dict[str, str]:
    return {"status": "authenticated"}


@app.post("/chat", dependencies=[Depends(require_api_key)])
def chat(body: ChatRequest) -> dict[str, str]:
    prompt = body.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message não pode ser vazio")

    try:
        answer = _build_chat_answer(prompt=prompt, with_web=body.with_web, with_rag=body.with_rag)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha na chamada OCI GenAI: {exc}") from exc

    return {"response": answer}


@app.post("/rag/ingest/object-storage", dependencies=[Depends(require_api_key)])
def ingest_object_storage(body: ObjectStorageIngestRequest) -> dict[str, str]:
    try:
        settings = get_settings()
        embedder = build_embedder(settings)
        content = load_object_text(
            settings=settings,
            namespace_name=body.namespace_name.strip(),
            bucket_name=body.bucket_name.strip(),
            object_name=body.object_name.strip(),
        )
        kb = KnowledgeBase(settings.rag_store_path)
        title = body.title.strip() or body.object_name.strip()
        source_ref = f"oci://{body.namespace_name}/{body.bucket_name}/{body.object_name}"
        embedding = None
        if embedder is not None:
            try:
                embedding = embedder.embed_text(_embedding_input(content), input_type="SEARCH_DOCUMENT")
            except Exception:
                embedding = None
        doc = kb.add_document(
            source_type="object_storage",
            source_ref=source_ref,
            title=title,
            content=content,
            embedding=embedding,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha ao ingerir Object Storage: {exc}") from exc

    return {"doc_id": doc.doc_id, "source_ref": source_ref}


@app.post("/rag/ingest/web", dependencies=[Depends(require_api_key)])
def ingest_web(body: WebIngestRequest) -> dict[str, str]:
    try:
        settings = get_settings()
        embedder = build_embedder(settings)
        content = load_web_document(url=body.url.strip(), auth_header=body.auth_header.strip())
        kb = KnowledgeBase(settings.rag_store_path)
        title = body.title.strip() or body.url.strip()
        embedding = None
        if embedder is not None:
            try:
                embedding = embedder.embed_text(_embedding_input(content), input_type="SEARCH_DOCUMENT")
            except Exception:
                embedding = None
        doc = kb.add_document(
            source_type=body.source_type,
            source_ref=body.url.strip(),
            title=title,
            content=content,
            embedding=embedding,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha ao ingerir documento web: {exc}") from exc

    return {"doc_id": doc.doc_id, "source_ref": body.url.strip()}


@app.get("/rag/sources", dependencies=[Depends(require_api_key)])
def rag_sources() -> dict[str, list[dict[str, str]]]:
    settings = get_settings()
    kb = KnowledgeBase(settings.rag_store_path)
    return {"sources": kb.list_sources()}


@app.post("/files/upload", dependencies=[Depends(require_api_key)])
async def upload_files(
    files: list[UploadFile] = File(...),
    add_to_rag: bool = Form(default=False),
) -> dict[str, list[dict[str, str | int]]]:
    if not files:
        raise HTTPException(status_code=400, detail="Envie ao menos 1 arquivo.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Máximo de 10 arquivos por upload.")

    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    store = FileStore(settings)
    kb = KnowledgeBase(settings.rag_store_path)
    embedder = build_embedder(settings)

    uploaded_items: list[dict[str, str | int]] = []
    rag_items: list[dict[str, str | int]] = []

    for file in files:
        name = (file.filename or "file.bin").strip() or "file.bin"
        data = await file.read()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Arquivo {name} excede limite de {settings.max_upload_size_mb}MB.",
            )

        item = store.save_uploaded(
            original_name=name,
            content_type=file.content_type or "application/octet-stream",
            data=data,
        )
        uploaded_items.append(_serialize_file_meta(item))

        if add_to_rag and settings.rag_enabled:
            rag_text = FileStore.infer_text_for_rag(name, file.content_type or "", data)
            embedding = None
            if embedder is not None:
                try:
                    embedding = embedder.embed_text(_embedding_input(rag_text), input_type="SEARCH_DOCUMENT")
                except Exception:
                    embedding = None
            doc = kb.add_document(
                source_type="uploaded_file",
                source_ref=f"uploaded://{item.file_id}/{name}",
                title=name,
                content=rag_text,
                embedding=embedding,
            )
            rag_items.append({"doc_id": doc.doc_id, "file_id": item.file_id, "title": name})

    return {"uploaded": uploaded_items, "rag_indexed": rag_items}


@app.get("/files", dependencies=[Depends(require_api_key)])
def list_files(kind: Optional[Literal["uploaded", "generated"]] = None, limit: int = 100) -> dict[str, list[dict[str, str | int]]]:
    settings = get_settings()
    store = FileStore(settings)
    safe_limit = max(1, min(limit, 500))
    items = store.list_files(kind=kind, limit=safe_limit)
    return {"files": [_serialize_file_meta(item) for item in items]}


@app.get("/files/{file_id}/download", dependencies=[Depends(require_api_key)])
def download_file(file_id: str) -> FileResponse:
    settings = get_settings()
    store = FileStore(settings)
    item = store.get(file_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    path = store.open_path(item)
    return FileResponse(
        path=str(path),
        media_type=item.content_type,
        filename=item.original_name,
    )


@app.post("/files/generate", dependencies=[Depends(require_api_key)])
def generate_file(body: GenerateFileRequest) -> dict[str, object]:
    settings = get_settings()
    store = FileStore(settings)
    item = store.save_generated(
        original_name=body.filename.strip(),
        content_type=body.content_type.strip() or "text/plain; charset=utf-8",
        data=body.content.encode("utf-8"),
    )
    meta = _serialize_file_meta(item)
    return {"generated_file": meta, "download_url": f"/files/{item.file_id}/download"}


@app.post("/chat/export", dependencies=[Depends(require_api_key)])
def chat_export(body: ChatExportRequest) -> dict[str, object]:
    prompt = body.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message não pode ser vazio")

    try:
        answer = _build_chat_answer(prompt=prompt, with_web=body.with_web, with_rag=body.with_rag)
        content, content_type = _build_export_bytes(prompt=prompt, answer=answer, file_format=body.file_format)
        settings = get_settings()
        store = FileStore(settings)
        item = store.save_generated(
            original_name=body.filename.strip(),
            content_type=content_type,
            data=content,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha ao exportar chat: {exc}") from exc

    return {
        "response": answer,
        "generated_file": _serialize_file_meta(item),
        "download_url": f"/files/{item.file_id}/download",
    }

from __future__ import annotations

import csv
import hmac
import io
import json
from pathlib import Path
import time
from typing import Literal, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field

from .assistant import LeoAIAssistant
from .config import get_settings
from .connectors.object_storage_loader import load_object_text
from .connectors.web_loader import load_web_document
from .embeddings import build_embedder
from .file_store import FileStore
from .job_queue import JobQueue
from .knowledge_base import KnowledgeBase


app = FastAPI(title="LeoAI API", version="0.4.0")
JOB_QUEUE = JobQueue()

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
    .files-actions { display:grid; grid-template-columns:1fr auto auto auto; gap:8px; margin-bottom:10px; }
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
                <label><input id="withStream" type="checkbox" checked /> streaming</label>
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
            <label class="row"><input id="asyncRag" type="checkbox" checked /> indexação async</label>
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
          <p id="jobsStatus" class="muted" style="margin:8px 0 0;"></p>
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
    const withStreamEl = document.getElementById("withStream");
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
    const asyncRagEl = document.getElementById("asyncRag");
    const uploadBtn = document.getElementById("uploadBtn");
    const refreshFilesBtn = document.getElementById("refreshFilesBtn");
    const fileKindFilterEl = document.getElementById("fileKindFilter");
    const filesTableBodyEl = document.getElementById("filesTableBody");
    const jobsStatusEl = document.getElementById("jobsStatus");
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

    async function runChatStreaming(text) {
      const botDiv = document.createElement("div");
      botDiv.className = "msg bot";
      botDiv.textContent = "";
      logEl.appendChild(botDiv);
      logEl.scrollTop = logEl.scrollHeight;

      const response = await fetch("/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify({
          message: text,
          with_web: Boolean(withWebEl.checked),
          with_rag: Boolean(withRagEl.checked),
        }),
      });
      if (!response.ok || !response.body) {
        throw new Error(`Falha no stream (${response.status})`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\\n\\n");
        buffer = events.pop() || "";
        for (const evt of events) {
          const line = evt.trim();
          if (!line.startsWith("data:")) continue;
          try {
            const payload = JSON.parse(line.slice(5).trim());
            if (payload.type === "chunk" && payload.content) {
              botDiv.textContent += payload.content;
              logEl.scrollTop = logEl.scrollHeight;
            }
            if (payload.type === "error") {
              throw new Error(payload.detail || "Erro no stream");
            }
          } catch (err) {
            throw err;
          }
        }
      }
      return botDiv.textContent || "(sem conteúdo)";
    }

    async function pollJob(jobId) {
      jobsStatusEl.textContent = `Job ${jobId} em execução...`;
      for (let i = 0; i < 120; i++) {
        const response = await fetch(`/jobs/${encodeURIComponent(jobId)}`, { headers: authHeaders() });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || `Erro HTTP ${response.status}`);
        if (payload.status === "done") {
          const indexed = (payload.result && payload.result.indexed) ? payload.result.indexed.length : 0;
          jobsStatusEl.textContent = `Job ${jobId} concluído: ${indexed} arquivo(s) indexado(s).`;
          return;
        }
        if (payload.status === "failed") {
          jobsStatusEl.textContent = `Job ${jobId} falhou: ${payload.error || "erro desconhecido"}`;
          return;
        }
        await new Promise((r) => setTimeout(r, 1500));
      }
      jobsStatusEl.textContent = `Job ${jobId} ainda em execução.`;
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
        let answer = "";
        if (withStreamEl.checked) {
          answer = await runChatStreaming(text);
        } else {
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
          answer = payload.response || "(sem conteúdo)";
          addMessage("bot", answer);
        }
        lastPrompt = text;
        lastAnswer = answer;
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
      formData.append("async_mode", asyncRagEl.checked ? "true" : "false");
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
        if (payload.job && payload.job.job_id) {
          pollJob(payload.job.job_id).catch((err) => {
            jobsStatusEl.textContent = `Erro ao acompanhar job: ${err.message}`;
          });
        }
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
    rag_filters: Optional[dict[str, str]] = None


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
    rag_filters: Optional[dict[str, str]] = None
    filename: str = Field(min_length=1)
    file_format: Literal["txt", "md", "json", "csv"] = "txt"


class GenerateFileRequest(BaseModel):
    filename: str = Field(min_length=1)
    content: str
    content_type: str = "text/plain; charset=utf-8"


class RagSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = 5
    filters: Optional[dict[str, str]] = None


class RagIndexJobRequest(BaseModel):
    file_ids: list[str] = Field(min_length=1)
    source_type: str = "uploaded_file"


def _build_chat_answer(prompt: str, with_web: bool, with_rag: bool, rag_filters: Optional[dict[str, str]] = None) -> str:
    settings = get_settings()
    kb = KnowledgeBase(settings.rag_store_path)
    embedder = build_embedder(settings)
    rag_context = ""
    if settings.rag_enabled and with_rag:
        rag_context = kb.retrieve_context(
            prompt,
            top_k=settings.rag_default_top_k,
            embedder=embedder,
            rerank_alpha=settings.rag_rerank_alpha,
            filters=rag_filters,
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


def _sse_line(payload: dict[str, object]) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _index_uploaded_files_for_rag(
    *,
    settings: object,
    file_ids: list[str],
    source_type: str = "uploaded_file",
) -> dict[str, object]:
    cfg = settings if settings is not None else get_settings()
    store = FileStore(cfg)
    kb = KnowledgeBase(cfg.rag_store_path)
    embedder = build_embedder(cfg)

    indexed: list[dict[str, str | int]] = []
    skipped: list[str] = []
    for file_id in file_ids:
        item = store.get(file_id)
        if item is None:
            skipped.append(file_id)
            continue
        path = store.open_path(item)
        data = path.read_bytes()
        rag_text, extraction_meta = FileStore.infer_text_for_rag(
            filename=item.original_name,
            content_type=item.content_type,
            data=data,
        )

        doc = kb.add_document(
            source_type=source_type,
            source_ref=f"uploaded://{item.file_id}/{item.original_name}",
            title=item.original_name,
            content=rag_text,
            file_id=item.file_id,
            metadata={
                "content_type": item.content_type,
                "extraction_strategy": extraction_meta.get("strategy", ""),
            },
            chunk_size=cfg.rag_chunk_size,
            chunk_overlap=cfg.rag_chunk_overlap,
            embedder=embedder,
        )
        indexed.append(
            {
                "file_id": item.file_id,
                "doc_id": doc.doc_id,
                "chunks_count": doc.chunks_count,
                "strategy": extraction_meta.get("strategy", ""),
            }
        )
    return {"indexed": indexed, "skipped_file_ids": skipped}


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
        answer = _build_chat_answer(
            prompt=prompt,
            with_web=body.with_web,
            with_rag=body.with_rag,
            rag_filters=body.rag_filters,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha na chamada OCI GenAI: {exc}") from exc

    return {"response": answer}


@app.post("/chat/stream", dependencies=[Depends(require_api_key)])
def chat_stream(body: ChatRequest) -> StreamingResponse:
    prompt = body.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message não pode ser vazio")

    def event_generator():
        started_at = time.time()
        yield _sse_line({"type": "meta", "status": "started"})
        try:
            answer = _build_chat_answer(
                prompt=prompt,
                with_web=body.with_web,
                with_rag=body.with_rag,
                rag_filters=body.rag_filters,
            )
            step = 140
            for idx in range(0, len(answer), step):
                chunk = answer[idx : idx + step]
                yield _sse_line({"type": "chunk", "content": chunk})
            duration_ms = int((time.time() - started_at) * 1000)
            yield _sse_line({"type": "done", "duration_ms": duration_ms})
        except Exception as exc:  # noqa: BLE001
            yield _sse_line({"type": "error", "detail": str(exc)})
            yield _sse_line({"type": "done", "duration_ms": int((time.time() - started_at) * 1000)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
        doc = kb.add_document(
            source_type="object_storage",
            source_ref=source_ref,
            title=title,
            content=content,
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            embedder=embedder,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha ao ingerir Object Storage: {exc}") from exc

    return {"doc_id": doc.doc_id, "source_ref": source_ref, "chunks_count": str(doc.chunks_count)}


@app.post("/rag/ingest/web", dependencies=[Depends(require_api_key)])
def ingest_web(body: WebIngestRequest) -> dict[str, str]:
    try:
        settings = get_settings()
        embedder = build_embedder(settings)
        content = load_web_document(url=body.url.strip(), auth_header=body.auth_header.strip())
        kb = KnowledgeBase(settings.rag_store_path)
        title = body.title.strip() or body.url.strip()
        doc = kb.add_document(
            source_type=body.source_type,
            source_ref=body.url.strip(),
            title=title,
            content=content,
            chunk_size=settings.rag_chunk_size,
            chunk_overlap=settings.rag_chunk_overlap,
            embedder=embedder,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha ao ingerir documento web: {exc}") from exc

    return {"doc_id": doc.doc_id, "source_ref": body.url.strip(), "chunks_count": str(doc.chunks_count)}


@app.get("/rag/sources", dependencies=[Depends(require_api_key)])
def rag_sources() -> dict[str, list[dict[str, str | int]]]:
    settings = get_settings()
    kb = KnowledgeBase(settings.rag_store_path)
    return {"sources": kb.list_sources()}


@app.post("/rag/search", dependencies=[Depends(require_api_key)])
def rag_search(body: RagSearchRequest) -> dict[str, object]:
    settings = get_settings()
    kb = KnowledgeBase(settings.rag_store_path)
    embedder = build_embedder(settings)
    top_k = max(1, min(body.top_k, 20))
    context = kb.retrieve_context(
        body.query.strip(),
        top_k=top_k,
        embedder=embedder,
        rerank_alpha=settings.rag_rerank_alpha,
        filters=body.filters,
    )
    return {"query": body.query, "top_k": top_k, "filters": body.filters or {}, "context": context}


@app.post("/files/upload", dependencies=[Depends(require_api_key)])
async def upload_files(
    files: list[UploadFile] = File(...),
    add_to_rag: bool = Form(default=False),
    async_mode: bool = Form(default=True),
    background_tasks: BackgroundTasks = None,
) -> dict[str, object]:
    if not files:
        raise HTTPException(status_code=400, detail="Envie ao menos 1 arquivo.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Máximo de 10 arquivos por upload.")

    settings = get_settings()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    store = FileStore(settings)

    uploaded_items: list[dict[str, str | int]] = []
    uploaded_ids: list[str] = []

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
        uploaded_ids.append(item.file_id)

    if not add_to_rag or not settings.rag_enabled:
        return {"uploaded": uploaded_items, "rag_indexed": [], "job": None}

    if async_mode:
        job = JOB_QUEUE.create(
            kind="rag_index_uploaded_files",
            payload={"file_ids": uploaded_ids, "source_type": "uploaded_file"},
        )

        def _runner():
            return _index_uploaded_files_for_rag(
                settings=settings,
                file_ids=uploaded_ids,
                source_type="uploaded_file",
            )

        if background_tasks is not None:
            background_tasks.add_task(JOB_QUEUE.run_guarded, job.job_id, _runner)
        else:
            JOB_QUEUE.run_guarded(job.job_id, _runner)
        return {
            "uploaded": uploaded_items,
            "rag_indexed": [],
            "job": {"job_id": job.job_id, "status": job.status, "kind": job.kind},
        }

    result = _index_uploaded_files_for_rag(
        settings=settings,
        file_ids=uploaded_ids,
        source_type="uploaded_file",
    )
    return {"uploaded": uploaded_items, "rag_indexed": result.get("indexed", []), "job": None}


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


@app.post("/jobs/rag-index-files", dependencies=[Depends(require_api_key)])
def enqueue_rag_index_files(body: RagIndexJobRequest, background_tasks: BackgroundTasks) -> dict[str, str]:
    settings = get_settings()
    file_ids = [f.strip() for f in body.file_ids if f.strip()]
    if not file_ids:
        raise HTTPException(status_code=400, detail="file_ids não pode ser vazio.")

    job = JOB_QUEUE.create(
        kind="rag_index_uploaded_files",
        payload={"file_ids": file_ids, "source_type": body.source_type},
    )

    def _runner():
        return _index_uploaded_files_for_rag(settings=settings, file_ids=file_ids, source_type=body.source_type)

    background_tasks.add_task(JOB_QUEUE.run_guarded, job.job_id, _runner)
    return {"job_id": job.job_id, "status": job.status, "kind": job.kind}


@app.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_job(job_id: str) -> dict[str, object]:
    job = JOB_QUEUE.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    return {
        "job_id": job.job_id,
        "kind": job.kind,
        "status": job.status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "payload": job.payload,
        "result": job.result,
        "error": job.error,
    }


@app.get("/jobs", dependencies=[Depends(require_api_key)])
def list_jobs(limit: int = 50) -> dict[str, list[dict[str, object]]]:
    safe_limit = max(1, min(limit, 200))
    jobs = JOB_QUEUE.list(limit=safe_limit)
    return {
        "jobs": [
            {
                "job_id": job.job_id,
                "kind": job.kind,
                "status": job.status,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            }
            for job in jobs
        ]
    }


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
        answer = _build_chat_answer(
            prompt=prompt,
            with_web=body.with_web,
            with_rag=body.with_rag,
            rag_filters=body.rag_filters,
        )
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

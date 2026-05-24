from __future__ import annotations

import hmac
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from .assistant import LeoAIAssistant
from .config import get_settings
from .connectors.object_storage_loader import load_object_text
from .connectors.web_loader import load_web_document
from .knowledge_base import KnowledgeBase


app = FastAPI(title="LeoAI API", version="0.3.0")

GUI_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LeoAI Console</title>
  <style>
    :root { --bg:#0b1220; --panel:#111a2b; --panel2:#18243d; --text:#e8edf8; --muted:#9db0d0; --accent:#31c4f3; --ok:#42d392; --warn:#ffd166; --danger:#ef476f; }
    * { box-sizing: border-box; }
    body { margin:0; font-family:"Avenir Next",Avenir,"Segoe UI",sans-serif; color:var(--text);
      background:radial-gradient(900px 500px at 5% -10%, #1f3058 0%, transparent 70%), radial-gradient(1000px 600px at 100% 0%, #203a54 0%, transparent 60%), linear-gradient(160deg, #0b1220 0%, #0f1a2d 60%, #0d1525 100%);
      min-height:100vh; }
    .shell { max-width:980px; margin:24px auto; padding:0 16px 24px; }
    .hero { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; }
    .title { margin:0; font-size:clamp(1.4rem,1rem + 1.4vw,2.2rem); font-weight:700; }
    .subtitle { margin:6px 0 0; color:var(--muted); font-size:.96rem; }
    .status { display:inline-flex; align-items:center; gap:8px; padding:8px 10px; border-radius:999px; border:1px solid #30456f; background:#101a2f; color:var(--muted); font-size:.85rem; white-space:nowrap; }
    .dot { width:8px; height:8px; border-radius:50%; background:var(--warn); }
    .auth { display:grid; grid-template-columns:1fr auto auto; gap:8px; margin:0 0 12px; }
    .panel { border:1px solid #243557; border-radius:18px; overflow:hidden; background:linear-gradient(180deg, var(--panel) 0%, #0f1a2d 100%); box-shadow:0 20px 55px rgba(3,10,24,.45); }
    .log { padding:18px; height:min(58vh,620px); overflow-y:auto; }
    .msg { max-width:85%; margin:0 0 12px; padding:11px 13px; border-radius:14px; line-height:1.45; white-space:pre-wrap; word-break:break-word; }
    .user { margin-left:auto; background:linear-gradient(135deg, #1d6ca1, #29a8d6); color:#f6fbff; border-bottom-right-radius:4px; }
    .bot { margin-right:auto; background:var(--panel2); border:1px solid #2b3f67; color:#e8edf8; border-bottom-left-radius:4px; }
    .sys { margin:0 auto 12px; text-align:center; font-size:.86rem; color:var(--muted); background:transparent; border:1px dashed #2e446f; }
    .composer { display:grid; grid-template-columns:1fr auto; gap:10px; padding:14px; border-top:1px solid #223356; background:#0d1628; }
    input, textarea { width:100%; border:1px solid #324d7a; background:#0f1b31; color:var(--text); border-radius:12px; padding:10px 12px; font:inherit; outline:none; }
    textarea { resize:vertical; min-height:56px; max-height:180px; }
    input:focus, textarea:focus { border-color:var(--accent); box-shadow:0 0 0 3px rgba(49,196,243,.16); }
    button { height:42px; padding:0 14px; border:0; border-radius:10px; background:linear-gradient(135deg, #31c4f3, #1e8fc1); color:#031522; font-weight:700; cursor:pointer; }
    button:disabled { opacity:.6; cursor:not-allowed; }
    .opts { display:flex; flex-direction:column; gap:6px; margin:0 0 8px; color:var(--muted); font-size:.85rem; }
    .foot { margin-top:10px; color:var(--muted); font-size:.82rem; display:flex; justify-content:space-between; gap:10px; flex-wrap:wrap; }
    .mono { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; }
  </style>
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <h1 class="title">LeoAI Console</h1>
        <p class="subtitle">GUI com auth + web search + RAG enterprise connectors.</p>
      </div>
      <div class="status"><span class="dot" id="dot"></span><span id="status">Aguardando auth...</span></div>
    </header>

    <div class="auth">
      <input id="apiKey" type="password" placeholder="LEOAI API key" />
      <button id="saveKeyBtn" type="button">Salvar key</button>
      <button id="verifyBtn" type="button">Verificar</button>
    </div>

    <section class="panel">
      <div class="log" id="log"></div>
      <form class="composer" id="chatForm">
        <textarea id="message" placeholder="Digite sua mensagem..." required></textarea>
        <div>
          <div class="opts">
            <label><input id="withWeb" type="checkbox" /> pesquisar web</label>
            <label><input id="withRag" type="checkbox" checked /> usar RAG</label>
          </div>
          <button id="sendBtn" type="submit">Enviar</button>
        </div>
      </form>
    </section>
    <div class="foot">
      <span>Auth header: <span class="mono">X-API-Key</span></span>
      <span>RAG endpoints: <span class="mono">/rag/ingest/*</span></span>
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
    const saveKeyBtn = document.getElementById("saveKeyBtn");
    const verifyBtn = document.getElementById("verifyBtn");

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
        setStatus("ok", "Online");
      } catch (err) {
        addMessage("bot", `Erro: ${err.message}`);
        setStatus("err", "Falha");
      } finally {
        sendBtn.disabled = false;
        msgEl.focus();
      }
    });

    msgEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        formEl.requestSubmit();
      }
    });

    apiKeyEl.value = getApiKey();
    addMessage("sys", "Defina e valide a API key para usar o chat.");
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
        settings = get_settings()
        kb = KnowledgeBase(settings.rag_store_path)
        rag_context = ""
        if settings.rag_enabled and body.with_rag:
            rag_context = kb.retrieve_context(prompt, top_k=3)

        assistant = LeoAIAssistant(settings)
        answer = assistant.ask_with_options(
            user_message=prompt,
            use_web_search=body.with_web,
            extra_context=rag_context,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha na chamada OCI GenAI: {exc}") from exc

    return {"response": answer}


@app.post("/rag/ingest/object-storage", dependencies=[Depends(require_api_key)])
def ingest_object_storage(body: ObjectStorageIngestRequest) -> dict[str, str]:
    try:
        settings = get_settings()
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
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha ao ingerir Object Storage: {exc}") from exc

    return {"doc_id": doc.doc_id, "source_ref": source_ref}


@app.post("/rag/ingest/web", dependencies=[Depends(require_api_key)])
def ingest_web(body: WebIngestRequest) -> dict[str, str]:
    try:
        settings = get_settings()
        content = load_web_document(url=body.url.strip(), auth_header=body.auth_header.strip())
        kb = KnowledgeBase(settings.rag_store_path)
        title = body.title.strip() or body.url.strip()
        doc = kb.add_document(
            source_type=body.source_type,
            source_ref=body.url.strip(),
            title=title,
            content=content,
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

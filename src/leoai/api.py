from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .assistant import LeoAIAssistant
from .config import get_settings


app = FastAPI(title="LeoAI API", version="0.2.0")

GUI_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>LeoAI Console</title>
  <style>
    :root {
      --bg: #0b1220;
      --panel: #111a2b;
      --panel-2: #18243d;
      --text: #e8edf8;
      --muted: #9db0d0;
      --accent: #31c4f3;
      --ok: #42d392;
      --warn: #ffd166;
      --danger: #ef476f;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Avenir Next", Avenir, "Segoe UI", sans-serif;
      color: var(--text);
      background:
        radial-gradient(900px 500px at 5% -10%, #1f3058 0%, transparent 70%),
        radial-gradient(1000px 600px at 100% 0%, #203a54 0%, transparent 60%),
        linear-gradient(160deg, #0b1220 0%, #0f1a2d 60%, #0d1525 100%);
      min-height: 100vh;
    }
    .shell {
      max-width: 980px;
      margin: 32px auto;
      padding: 0 16px 24px;
    }
    .hero {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 14px;
    }
    .title {
      margin: 0;
      font-size: clamp(1.4rem, 1rem + 1.4vw, 2.2rem);
      letter-spacing: 0.01em;
      font-weight: 700;
    }
    .subtitle {
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 0.96rem;
    }
    .status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      border-radius: 999px;
      border: 1px solid #30456f;
      background: #101a2f;
      color: var(--muted);
      font-size: 0.85rem;
      white-space: nowrap;
    }
    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--warn);
      box-shadow: 0 0 0 0 rgba(255, 209, 102, 0.7);
      animation: pulse 1.8s infinite;
    }
    @keyframes pulse {
      0% { box-shadow: 0 0 0 0 rgba(255, 209, 102, 0.7); }
      70% { box-shadow: 0 0 0 10px rgba(255, 209, 102, 0); }
      100% { box-shadow: 0 0 0 0 rgba(255, 209, 102, 0); }
    }
    .panel {
      border: 1px solid #243557;
      border-radius: 18px;
      overflow: hidden;
      background: linear-gradient(180deg, var(--panel) 0%, #0f1a2d 100%);
      box-shadow: 0 20px 55px rgba(3, 10, 24, 0.45);
    }
    .log {
      padding: 18px;
      height: min(62vh, 640px);
      overflow-y: auto;
      scroll-behavior: smooth;
    }
    .msg {
      max-width: 85%;
      margin: 0 0 12px;
      padding: 11px 13px;
      border-radius: 14px;
      line-height: 1.45;
      white-space: pre-wrap;
      word-break: break-word;
      animation: slide .2s ease-out;
    }
    @keyframes slide {
      from { opacity: 0; transform: translateY(5px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .msg.user {
      margin-left: auto;
      background: linear-gradient(135deg, #1d6ca1, #29a8d6);
      color: #f6fbff;
      border-bottom-right-radius: 4px;
    }
    .msg.bot {
      margin-right: auto;
      background: var(--panel-2);
      border: 1px solid #2b3f67;
      color: #e8edf8;
      border-bottom-left-radius: 4px;
    }
    .msg.system {
      margin: 0 auto 12px;
      text-align: center;
      font-size: 0.86rem;
      color: var(--muted);
      background: transparent;
      border: 1px dashed #2e446f;
    }
    .composer {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 10px;
      padding: 14px;
      border-top: 1px solid #223356;
      background: #0d1628;
    }
    textarea {
      width: 100%;
      resize: vertical;
      min-height: 56px;
      max-height: 180px;
      border: 1px solid #324d7a;
      background: #0f1b31;
      color: var(--text);
      border-radius: 12px;
      padding: 12px;
      font: inherit;
      outline: none;
    }
    textarea:focus { border-color: var(--accent); box-shadow: 0 0 0 3px rgba(49, 196, 243, 0.16); }
    button {
      align-self: end;
      height: 56px;
      padding: 0 16px;
      border: 0;
      border-radius: 12px;
      background: linear-gradient(135deg, #31c4f3, #1e8fc1);
      color: #031522;
      font-weight: 700;
      letter-spacing: 0.02em;
      cursor: pointer;
    }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .foot {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.82rem;
      display: flex;
      justify-content: space-between;
      gap: 10px;
      flex-wrap: wrap;
    }
    .mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
  </style>
</head>
<body>
  <main class="shell">
    <header class="hero">
      <div>
        <h1 class="title">LeoAI Console</h1>
        <p class="subtitle">GUI web para conversar com seu modelo OCI GenAI.</p>
      </div>
      <div class="status" id="statusPill">
        <span class="status-dot" id="statusDot"></span>
        <span id="statusText">Conectando...</span>
      </div>
    </header>

    <section class="panel">
      <div class="log" id="log"></div>
      <form class="composer" id="chatForm">
        <textarea id="message" placeholder="Digite sua mensagem..." required></textarea>
        <div>
          <label style="display:flex;align-items:center;gap:8px;color:var(--muted);font-size:.85rem;margin:0 0 8px;">
            <input id="withWeb" type="checkbox" />
            Pesquisar na web antes de responder
          </label>
          <button id="sendBtn" type="submit">Enviar</button>
        </div>
      </form>
    </section>
    <div class="foot">
      <span>Endpoint: <span class="mono">POST /chat</span></span>
      <span>Atalho: <span class="mono">Enter</span> envia | <span class="mono">Shift+Enter</span> quebra linha</span>
    </div>
  </main>

  <script>
    const logEl = document.getElementById("log");
    const formEl = document.getElementById("chatForm");
    const msgEl = document.getElementById("message");
    const sendBtn = document.getElementById("sendBtn");
    const withWebEl = document.getElementById("withWeb");
    const statusText = document.getElementById("statusText");
    const statusDot = document.getElementById("statusDot");

    function setStatus(kind, text) {
      statusText.textContent = text;
      if (kind === "ok") statusDot.style.background = "#42d392";
      if (kind === "warn") statusDot.style.background = "#ffd166";
      if (kind === "err") statusDot.style.background = "#ef476f";
    }

    function addMessage(kind, text) {
      const div = document.createElement("div");
      div.className = `msg ${kind}`;
      div.textContent = text;
      logEl.appendChild(div);
      logEl.scrollTop = logEl.scrollHeight;
    }

    async function checkHealth() {
      try {
        const r = await fetch("/health");
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        setStatus("ok", "Online");
        addMessage("system", "Conectado. Pode enviar sua mensagem.");
      } catch {
        setStatus("warn", "Sem resposta da API");
        addMessage("system", "API ainda indisponível. Tente novamente em instantes.");
      }
    }

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
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, with_web: Boolean(withWebEl.checked) }),
        });

        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || `Erro HTTP ${response.status}`);
        }

        addMessage("bot", payload.response || "(sem conteúdo)");
        setStatus("ok", "Online");
      } catch (err) {
        addMessage("bot", `Erro: ${err.message}`);
        setStatus("err", "Falha na chamada");
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

    addMessage("system", "Inicializando console...");
    checkHealth();
  </script>
</body>
</html>
"""


class ChatRequest(BaseModel):
    message: str
    with_web: bool = False


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return GUI_HTML


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat")
def chat(body: ChatRequest) -> dict[str, str]:
    prompt = body.message.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="message não pode ser vazio")

    try:
        settings = get_settings()
        assistant = LeoAIAssistant(settings)
        answer = assistant.ask_with_options(user_message=prompt, use_web_search=body.with_web)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha na chamada OCI GenAI: {exc}") from exc

    return {"response": answer}

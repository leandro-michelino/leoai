from pydantic import BaseModel
from fastapi import FastAPI, HTTPException

from .assistant import LeoAIAssistant
from .config import get_settings


app = FastAPI(title="LeoAI API", version="0.2.0")


class ChatRequest(BaseModel):
    message: str


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
        answer = assistant.ask(prompt)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Falha na chamada OCI GenAI: {exc}") from exc

    return {"response": answer}

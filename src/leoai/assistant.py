from openai import OpenAI

from .config import Settings


SYSTEM_PROMPT = (
    "Você é o LeoAI, um assistente direto, útil e colaborativo. "
    "Responda em português de forma clara."
)


class LeoAIAssistant:
    def __init__(self, settings: Settings) -> None:
        self.client = OpenAI(api_key=settings.api_key)
        self.model = settings.model

    def ask(self, user_message: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
        )
        return response.output_text.strip()

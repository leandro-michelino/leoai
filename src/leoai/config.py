from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str = "gpt-4.1-mini"



def get_settings() -> Settings:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"

    if not api_key:
        raise ValueError("OPENAI_API_KEY não encontrada. Configure no arquivo .env.")

    return Settings(api_key=api_key, model=model)

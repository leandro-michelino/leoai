from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    compartment_id: str
    model_id: str
    region: str
    inference_endpoint: str
    auth_mode: str = "instance_principal"
    oci_profile: str = "DEFAULT"
    api_format: str = "GENERIC"
    cohere_safety_mode: str = "OFF"
    web_search_enabled: bool = False
    web_search_max_results: int = 5
    temperature: float = 0.2
    top_p: float = 0.75
    max_tokens: int = 600


def _env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"{name} não encontrada. Configure no arquivo .env.")
    return value


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError as exc:  # noqa: B904
        raise ValueError(f"{name} inválida. Use um número.") from exc


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:  # noqa: B904
        raise ValueError(f"{name} inválida. Use um inteiro.") from exc


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "y", "on"}:
        return True
    if raw in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{name} inválida. Use true/false.")


def _default_inference_endpoint(region: str) -> str:
    return f"https://inference.generativeai.{region}.oci.oraclecloud.com"


def get_settings() -> Settings:
    compartment_id = _env_required("OCI_COMPARTMENT_ID")
    model_id = _env_required("OCI_GENAI_MODEL_ID")
    region = _env_required("OCI_REGION")

    auth_mode = os.getenv("OCI_AUTH_MODE", "instance_principal").strip().lower() or "instance_principal"
    if auth_mode not in {"instance_principal", "api_key"}:
        raise ValueError("OCI_AUTH_MODE deve ser 'instance_principal' ou 'api_key'.")

    oci_profile = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT").strip() or "DEFAULT"
    api_format = os.getenv("OCI_API_FORMAT", "GENERIC").strip().upper() or "GENERIC"
    if api_format not in {"GENERIC", "COHERE"}:
        raise ValueError("OCI_API_FORMAT deve ser 'GENERIC' ou 'COHERE'.")

    cohere_safety_mode = os.getenv("OCI_COHERE_SAFETY_MODE", "OFF").strip().upper() or "OFF"
    if cohere_safety_mode not in {"OFF", "CONTEXTUAL", "STRICT"}:
        raise ValueError("OCI_COHERE_SAFETY_MODE deve ser 'OFF', 'CONTEXTUAL' ou 'STRICT'.")

    web_search_enabled = _env_bool("WEB_SEARCH_ENABLED", False)
    web_search_max_results = _env_int("WEB_SEARCH_MAX_RESULTS", 5)
    if web_search_max_results < 1 or web_search_max_results > 10:
        raise ValueError("WEB_SEARCH_MAX_RESULTS deve estar entre 1 e 10.")

    inference_endpoint = (
        os.getenv("OCI_GENAI_INFERENCE_ENDPOINT", "").strip()
        or _default_inference_endpoint(region)
    )

    temperature = _env_float("OCI_TEMPERATURE", 0.2)
    top_p = _env_float("OCI_TOP_P", 0.75)
    max_tokens = _env_int("OCI_MAX_TOKENS", 600)

    return Settings(
        compartment_id=compartment_id,
        model_id=model_id,
        region=region,
        inference_endpoint=inference_endpoint,
        auth_mode=auth_mode,
        oci_profile=oci_profile,
        api_format=api_format,
        cohere_safety_mode=cohere_safety_mode,
        web_search_enabled=web_search_enabled,
        web_search_max_results=web_search_max_results,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )

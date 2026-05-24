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
    api_auth_enabled: bool = True
    api_auth_key: str = ""
    web_search_enabled: bool = False
    web_search_max_results: int = 5
    rag_enabled: bool = True
    rag_store_path: str = "/opt/leoai/data/knowledge_base.json"
    rag_embeddings_enabled: bool = True
    rag_embedding_model_id: str = "cohere.embed-multilingual-v3.0"
    rag_rerank_alpha: float = 0.65
    rag_chunk_size: int = 1200
    rag_chunk_overlap: int = 180
    rag_default_top_k: int = 5
    files_store_dir: str = "/opt/leoai/data/files/uploads"
    generated_store_dir: str = "/opt/leoai/data/files/generated"
    files_index_path: str = "/opt/leoai/data/files/index.json"
    max_upload_size_mb: int = 100
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
    if cohere_safety_mode != "OFF":
        raise ValueError(
            "Politica deste projeto: OCI_COHERE_SAFETY_MODE deve permanecer 'OFF' "
            "e ApplyGuardrails nao deve ser habilitado."
        )

    web_search_enabled = _env_bool("WEB_SEARCH_ENABLED", False)
    web_search_max_results = _env_int("WEB_SEARCH_MAX_RESULTS", 5)
    if web_search_max_results < 1 or web_search_max_results > 10:
        raise ValueError("WEB_SEARCH_MAX_RESULTS deve estar entre 1 e 10.")

    api_auth_enabled = _env_bool("LEOAI_API_AUTH_ENABLED", True)
    api_auth_key = os.getenv("LEOAI_API_AUTH_KEY", "").strip()
    if api_auth_enabled and len(api_auth_key) < 12:
        raise ValueError("LEOAI_API_AUTH_KEY deve ter ao menos 12 caracteres quando auth estiver habilitado.")

    rag_enabled = _env_bool("RAG_ENABLED", True)
    rag_store_path = os.getenv("RAG_STORE_PATH", "/opt/leoai/data/knowledge_base.json").strip() or "/opt/leoai/data/knowledge_base.json"
    rag_embeddings_enabled = _env_bool("RAG_EMBEDDINGS_ENABLED", True)
    rag_embedding_model_id = (
        os.getenv("RAG_EMBEDDING_MODEL_ID", "cohere.embed-multilingual-v3.0").strip()
        or "cohere.embed-multilingual-v3.0"
    )
    rag_rerank_alpha = _env_float("RAG_RERANK_ALPHA", 0.65)
    if rag_rerank_alpha < 0 or rag_rerank_alpha > 1:
        raise ValueError("RAG_RERANK_ALPHA deve estar entre 0 e 1.")
    rag_chunk_size = _env_int("RAG_CHUNK_SIZE", 1200)
    if rag_chunk_size < 200 or rag_chunk_size > 4000:
        raise ValueError("RAG_CHUNK_SIZE deve estar entre 200 e 4000.")
    rag_chunk_overlap = _env_int("RAG_CHUNK_OVERLAP", 180)
    if rag_chunk_overlap < 0 or rag_chunk_overlap >= rag_chunk_size:
        raise ValueError("RAG_CHUNK_OVERLAP deve ser >= 0 e menor que RAG_CHUNK_SIZE.")
    rag_default_top_k = _env_int("RAG_DEFAULT_TOP_K", 5)
    if rag_default_top_k < 1 or rag_default_top_k > 20:
        raise ValueError("RAG_DEFAULT_TOP_K deve estar entre 1 e 20.")

    files_store_dir = os.getenv("FILES_STORE_DIR", "/opt/leoai/data/files/uploads").strip() or "/opt/leoai/data/files/uploads"
    generated_store_dir = os.getenv("GENERATED_STORE_DIR", "/opt/leoai/data/files/generated").strip() or "/opt/leoai/data/files/generated"
    files_index_path = os.getenv("FILES_INDEX_PATH", "/opt/leoai/data/files/index.json").strip() or "/opt/leoai/data/files/index.json"
    max_upload_size_mb = _env_int("MAX_UPLOAD_SIZE_MB", 100)
    if max_upload_size_mb < 1 or max_upload_size_mb > 1024:
        raise ValueError("MAX_UPLOAD_SIZE_MB deve estar entre 1 e 1024.")

    inference_endpoint = (
        os.getenv("OCI_GENAI_INFERENCE_ENDPOINT", "").strip()
        or _default_inference_endpoint(region)
    )

    temperature = _env_float("OCI_TEMPERATURE", 0.2)
    if temperature < 0 or temperature > 2:
        raise ValueError("OCI_TEMPERATURE deve estar entre 0 e 2.")

    top_p = _env_float("OCI_TOP_P", 0.75)
    if top_p <= 0 or top_p > 1:
        raise ValueError("OCI_TOP_P deve estar entre 0 (exclusivo) e 1.")

    max_tokens = _env_int("OCI_MAX_TOKENS", 600)
    if max_tokens < 1 or max_tokens > 4096:
        raise ValueError("OCI_MAX_TOKENS deve estar entre 1 e 4096.")

    return Settings(
        compartment_id=compartment_id,
        model_id=model_id,
        region=region,
        inference_endpoint=inference_endpoint,
        auth_mode=auth_mode,
        oci_profile=oci_profile,
        api_format=api_format,
        cohere_safety_mode=cohere_safety_mode,
        api_auth_enabled=api_auth_enabled,
        api_auth_key=api_auth_key,
        web_search_enabled=web_search_enabled,
        web_search_max_results=web_search_max_results,
        rag_enabled=rag_enabled,
        rag_store_path=rag_store_path,
        rag_embeddings_enabled=rag_embeddings_enabled,
        rag_embedding_model_id=rag_embedding_model_id,
        rag_rerank_alpha=rag_rerank_alpha,
        rag_chunk_size=rag_chunk_size,
        rag_chunk_overlap=rag_chunk_overlap,
        rag_default_top_k=rag_default_top_k,
        files_store_dir=files_store_dir,
        generated_store_dir=generated_store_dir,
        files_index_path=files_index_path,
        max_upload_size_mb=max_upload_size_mb,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
    )

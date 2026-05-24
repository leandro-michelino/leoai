from leoai.config import get_settings


def test_get_settings_uses_oci_env(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("OCI_AUTH_MODE", "instance_principal")
    monkeypatch.setenv("OCI_API_FORMAT", "COHERE")
    monkeypatch.setenv("OCI_COHERE_SAFETY_MODE", "OFF")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("LEOAI_API_AUTH_KEY", "test-auth-key-123")

    settings = get_settings()

    assert settings.compartment_id == "ocid1.compartment.oc1..test"
    assert settings.model_id == "meta.llama-3.1-70b-instruct"
    assert settings.region == "eu-madrid-1"
    assert settings.inference_endpoint == "https://inference.generativeai.eu-madrid-1.oci.oraclecloud.com"
    assert settings.auth_mode == "instance_principal"
    assert settings.api_format == "COHERE"
    assert settings.cohere_safety_mode == "OFF"
    assert settings.rag_embeddings_enabled is True
    assert settings.rag_embedding_model_id == "cohere.embed-multilingual-v3.0"


def test_get_settings_raises_without_compartment(monkeypatch):
    monkeypatch.delenv("OCI_COMPARTMENT_ID", raising=False)
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "false")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "OCI_COMPARTMENT_ID" in str(exc)


def test_get_settings_rejects_invalid_auth_mode(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("OCI_AUTH_MODE", "foo")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "false")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "OCI_AUTH_MODE" in str(exc)


def test_get_settings_rejects_invalid_api_format(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("OCI_API_FORMAT", "FOO")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "false")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "OCI_API_FORMAT" in str(exc)


def test_get_settings_rejects_weak_api_key(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "true")
    monkeypatch.setenv("LEOAI_API_AUTH_KEY", "short")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "LEOAI_API_AUTH_KEY" in str(exc)


def test_get_settings_rejects_invalid_sampling_values(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "false")
    monkeypatch.setenv("OCI_TEMPERATURE", "4")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "OCI_TEMPERATURE" in str(exc)


def test_get_settings_rejects_invalid_rerank_alpha(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "false")
    monkeypatch.setenv("RAG_RERANK_ALPHA", "1.5")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "RAG_RERANK_ALPHA" in str(exc)


def test_get_settings_rejects_invalid_chunk_settings(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "false")
    monkeypatch.setenv("RAG_CHUNK_SIZE", "100")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "RAG_CHUNK_SIZE" in str(exc)


def test_get_settings_rejects_invalid_rag_default_top_k(monkeypatch):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "meta.llama-3.1-70b-instruct")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "false")
    monkeypatch.setenv("RAG_DEFAULT_TOP_K", "50")

    try:
        get_settings()
        assert False, "Era esperado ValueError"
    except ValueError as exc:
        assert "RAG_DEFAULT_TOP_K" in str(exc)

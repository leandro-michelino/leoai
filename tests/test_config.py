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

from fastapi.testclient import TestClient

from leoai.api import app


def _set_base_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OCI_COMPARTMENT_ID", "ocid1.compartment.oc1..test")
    monkeypatch.setenv("OCI_GENAI_MODEL_ID", "cohere.command-a")
    monkeypatch.setenv("OCI_REGION", "eu-madrid-1")
    monkeypatch.setenv("LEOAI_API_AUTH_ENABLED", "false")
    monkeypatch.setenv("RAG_ENABLED", "false")
    monkeypatch.setenv("FILES_STORE_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("GENERATED_STORE_DIR", str(tmp_path / "generated"))
    monkeypatch.setenv("FILES_INDEX_PATH", str(tmp_path / "index.json"))
    monkeypatch.setenv("MAX_UPLOAD_SIZE_MB", "2")


def test_upload_multiple_files_up_to_10(monkeypatch, tmp_path):
    _set_base_env(monkeypatch, tmp_path)
    client = TestClient(app)

    files = [
        ("files", ("a.txt", b"alpha", "text/plain")),
        ("files", ("b.csv", b"col\n1\n", "text/csv")),
    ]
    response = client.post("/files/upload", files=files)
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["uploaded"]) == 2
    assert payload["rag_indexed"] == []


def test_upload_rejects_more_than_10_files(monkeypatch, tmp_path):
    _set_base_env(monkeypatch, tmp_path)
    client = TestClient(app)

    files = [("files", (f"f{i}.txt", b"x", "text/plain")) for i in range(11)]
    response = client.post("/files/upload", files=files)
    assert response.status_code == 400
    assert "Máximo de 10 arquivos" in response.json()["detail"]


def test_generate_and_download_file(monkeypatch, tmp_path):
    _set_base_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post(
        "/files/generate",
        json={
            "filename": "saida.txt",
            "content": "conteudo gerado",
            "content_type": "text/plain; charset=utf-8",
        },
    )
    assert response.status_code == 200
    file_id = response.json()["generated_file"]["file_id"]

    download = client.get(f"/files/{file_id}/download")
    assert download.status_code == 200
    assert download.content == b"conteudo gerado"

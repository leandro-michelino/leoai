from leoai.file_extractors import extract_content_for_rag


def test_extract_plain_text_strategy():
    text, meta = extract_content_for_rag(
        filename="notes.txt",
        content_type="text/plain",
        data=b"linha 1\nlinha 2",
    )
    assert "linha 1" in text
    assert meta["strategy"] == "plain_text"


def test_extract_binary_fallback_strategy():
    text, meta = extract_content_for_rag(
        filename="blob.bin",
        content_type="application/octet-stream",
        data=b"\x00\x01\x02\x03",
    )
    assert "Arquivo binario enviado" in text
    assert meta["strategy"] in {"binary_metadata", "fallback_after_error"}

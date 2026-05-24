import os

import pytest

from leoai.connectors.web_loader import load_web_document
from leoai.knowledge_base import KnowledgeBase


def test_knowledge_base_supports_relative_filename(tmp_path):
    cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        kb = KnowledgeBase("kb.json")
        kb.add_document(
            source_type="test",
            source_ref="unit://sample",
            title="Sample",
            content="conteudo de teste",
        )
        assert (tmp_path / "kb.json").exists()
    finally:
        os.chdir(cwd)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "http://127.0.0.1:8000/private",
        "http://10.0.0.10/internal",
        "http://localhost:8000",
    ],
)
def test_web_loader_rejects_unsafe_urls(url):
    with pytest.raises(ValueError):
        load_web_document(url)

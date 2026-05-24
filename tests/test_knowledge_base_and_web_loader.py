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


class _FakeEmbedder:
    def embed_text(self, text: str, input_type: str = "SEARCH_DOCUMENT") -> list[float]:
        lower = text.lower()
        if "oracle" in lower:
            return [1.0, 0.0]
        if "faturamento" in lower:
            return [0.0, 1.0]
        return [0.5, 0.5]


def test_knowledge_base_hybrid_reranking_prefers_semantic_match(tmp_path):
    kb = KnowledgeBase(str(tmp_path / "kb.json"))
    kb.add_document(
        source_type="test",
        source_ref="doc://oracle",
        title="Oracle Doc",
        content="oracle cloud e servicos",
        embedder=_FakeEmbedder(),
    )
    kb.add_document(
        source_type="test",
        source_ref="doc://finance",
        title="Financeiro",
        content="faturamento consolidado",
        embedder=_FakeEmbedder(),
    )

    context = kb.retrieve_context(
        "oracle cloud",
        top_k=1,
        embedder=_FakeEmbedder(),
        rerank_alpha=0.8,
    )
    assert "doc://oracle" in context


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

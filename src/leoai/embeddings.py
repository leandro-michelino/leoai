from __future__ import annotations

from typing import Optional

import oci

from .config import Settings


def _build_client(settings: Settings) -> oci.generative_ai_inference.GenerativeAiInferenceClient:
    if settings.auth_mode == "instance_principal":
        signer = oci.auth.signers.InstancePrincipalsSecurityTokenSigner()
        return oci.generative_ai_inference.GenerativeAiInferenceClient(
            config={"region": settings.region},
            signer=signer,
            service_endpoint=settings.inference_endpoint,
            timeout=(10, 120),
        )

    config = oci.config.from_file(profile_name=settings.oci_profile)
    return oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=settings.inference_endpoint,
        timeout=(10, 120),
    )


class OciEmbedder:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = _build_client(settings)

    def embed_text(self, text: str, input_type: str = "SEARCH_DOCUMENT") -> list[float]:
        content = text.strip()
        if not content:
            raise ValueError("Texto vazio para embedding.")

        models = oci.generative_ai_inference.models
        details = models.EmbedTextDetails(
            compartment_id=self.settings.compartment_id,
            serving_mode=models.OnDemandServingMode(model_id=self.settings.rag_embedding_model_id),
            inputs=[content],
            input_type=input_type,
            embedding_types=["float"],
            truncate="END",
        )

        response = self.client.embed_text(embed_text_details=details)
        result = response.data

        # SDKs recentes trazem embeddings em `embeddings` ou `embed_contents`.
        embeddings = getattr(result, "embeddings", None)
        if embeddings and isinstance(embeddings, list):
            first = embeddings[0]
            if isinstance(first, list):
                return [float(v) for v in first]

        embed_contents = getattr(result, "embed_contents", None)
        if embed_contents and isinstance(embed_contents, list):
            first_content = embed_contents[0]
            first_embedding = getattr(first_content, "embedding", None)
            if first_embedding and isinstance(first_embedding, list):
                return [float(v) for v in first_embedding]

        raise RuntimeError("Resposta de embedding OCI invalida: vetor nao encontrado.")


def build_embedder(settings: Settings) -> Optional[OciEmbedder]:
    if not settings.rag_embeddings_enabled:
        return None
    try:
        return OciEmbedder(settings)
    except Exception:
        # Embeddings falharam na inicializacao: manter API operacional com fallback lexical.
        return None

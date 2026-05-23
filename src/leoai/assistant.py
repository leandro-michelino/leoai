from __future__ import annotations

import oci

from .config import Settings
from .web_search import search_web_context


SYSTEM_PROMPT = (
    "Você é o LeoAI, um assistente direto, útil e colaborativo. "
    "Responda em português de forma clara."
)


class LeoAIAssistant:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = self._build_client(settings)

    def _build_client(self, settings: Settings) -> oci.generative_ai_inference.GenerativeAiInferenceClient:
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

    def ask(self, user_message: str) -> str:
        return self.ask_with_options(user_message=user_message, use_web_search=False)

    def ask_with_options(self, user_message: str, use_web_search: bool) -> str:
        models = oci.generative_ai_inference.models
        final_message = user_message

        if use_web_search and self.settings.web_search_enabled:
            try:
                web_context = search_web_context(
                    query=user_message,
                    max_results=self.settings.web_search_max_results,
                )
                final_message = (
                    "Contexto web coletado automaticamente:\n"
                    f"{web_context}\n\n"
                    "Pergunta original do usuário:\n"
                    f"{user_message}"
                )
            except Exception:
                # Falha de pesquisa web nao deve bloquear a resposta do modelo.
                final_message = user_message

        if self.settings.api_format == "COHERE":
            chat_request = models.CohereChatRequest(
                message=final_message,
                temperature=self.settings.temperature,
                top_p=self.settings.top_p,
                max_tokens=self.settings.max_tokens,
                safety_mode=self.settings.cohere_safety_mode,
                is_stream=False,
            )
        else:
            chat_request = models.GenericChatRequest(
                api_format="GENERIC",
                messages=[
                    models.SystemMessage(
                        role="SYSTEM",
                        content=[models.TextContent(text=SYSTEM_PROMPT)],
                    ),
                    models.UserMessage(
                        role="USER",
                        content=[models.TextContent(text=final_message)],
                    ),
                ],
                temperature=self.settings.temperature,
                top_p=self.settings.top_p,
                max_tokens=self.settings.max_tokens,
                is_stream=False,
            )

        chat_details = models.ChatDetails(
            compartment_id=self.settings.compartment_id,
            serving_mode=models.OnDemandServingMode(model_id=self.settings.model_id),
            chat_request=chat_request,
        )

        response = self.client.chat(chat_details=chat_details)
        return self._extract_text(response.data)

    @staticmethod
    def _extract_text(chat_result: object) -> str:
        chat_response = getattr(chat_result, "chat_response", None)
        if chat_response is None:
            raise RuntimeError("Resposta OCI inválida: chat_response ausente")

        cohere_text = getattr(chat_response, "text", None)
        if isinstance(cohere_text, str) and cohere_text.strip():
            return cohere_text.strip()

        choices = getattr(chat_response, "choices", None) or []
        if not choices:
            raise RuntimeError("Resposta OCI inválida: choices vazio")

        message = getattr(choices[0], "message", None)
        if message is None:
            raise RuntimeError("Resposta OCI inválida: message ausente")

        content = getattr(message, "content", None) or []
        text_parts: list[str] = []
        for part in content:
            text = getattr(part, "text", None)
            if text:
                text_parts.append(str(text))

        if not text_parts:
            raise RuntimeError("Resposta OCI inválida: conteúdo textual vazio")

        return "\n".join(text_parts).strip()

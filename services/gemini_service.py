import google.generativeai as genai
from services.http_audit_service import HttpAuditService


class GeminiService:
    def __init__(self, api_key: str, model_name: str, audit_service: HttpAuditService):
        self.api_key = api_key
        # Приводим название к стандартному виду
        self.model_name = model_name if model_name.startswith("models/") else f"models/{model_name}"
        self.audit_service = audit_service
        
        # Настраиваем старый стабильный SDK
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    async def generate_response(
        self, full_prompt: str, system_instruction: str
    ) -> tuple[str, int, int]:
        # Если задана системная инструкция, пересоздаем модель с ней
        if system_instruction:
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=system_instruction
            )
        else:
            model = self.model

        # Вызываем асинхронную генерацию
        response = await model.generate_content_async(full_prompt)

        input_tokens = 0
        output_tokens = 0
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
            output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

        class DummyRequest:
            def __init__(self, model_name: str):
                self.url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent"
                self.method = "POST"
                self.headers = {"Content-Type": "application/json"}

        class DummyResponse:
            def __init__(self, text_resp: str, in_t: int, out_t: int):
                self.status_code = 200
                self.text = f"{{\"prompt_tokens\": {in_t}, \"candidate_tokens\": {out_t}, \"preview\": \"{text_resp[:80]}...\"}}"

        self.audit_service.log_transport_event(
            request=DummyRequest(self.model_name),
            response=DummyResponse(response.text or "", input_tokens, output_tokens),
        )

        return response.text or "", input_tokens, output_tokens

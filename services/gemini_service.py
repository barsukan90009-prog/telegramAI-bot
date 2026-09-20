import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError
from services.http_audit_service import HttpAuditService

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, api_keys: list[str], model_name: str, audit_service: HttpAuditService):
        if not api_keys:
            raise ValueError("Список API-ключей Gemini пуст! Проверь конфигурацию .env")
        
        self.api_keys = api_keys
        self.current_key_index = 0
        self.model_name = model_name if model_name.startswith("models/") else f"models/{model_name}"
        self.audit_service = audit_service

        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    def _get_current_key(self) -> str:
        return self.api_keys[self.current_key_index]

    def _rotate_key(self):
        """Переключает на следующий API-ключ по кругу."""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            logger.info(f"🔄 Превышена квота. Переключение на API-ключ индекс: {self.current_key_index}")

    async def generate_response(
        self, full_prompt: str, system_instruction: str
    ) -> tuple[str, int, int]:
        
        class DummyRequest:
            def __init__(self, model_name: str, prompt: str, sys_instruction: str):
                self.url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent"
                self.method = "POST"
                self.headers = {"Content-Type": "application/json"}
                self.body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "system_instruction": system_instruction
                }

        req = DummyRequest(self.model_name, full_prompt, system_instruction)
        user_friendly_error = "Дело пахнет писюнами. Попробуйте позже ептэ."

        attempts = len(self.api_keys)

        for attempt in range(attempts):
            current_key = self._get_current_key()
            logger.info(f"🔑 Попытка {attempt + 1}/{attempts} с использованием ключа индекс #{self.current_key_index}")
            
            genai.configure(api_key=current_key)

            try:
                model = genai.GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=system_instruction
                )

                response = await model.generate_content_async(
                    full_prompt, 
                    safety_settings=self.safety_settings
                )

                input_tokens = 0
                output_tokens = 0
                if hasattr(response, "usage_metadata") and response.usage_metadata:
                    input_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
                    output_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0

                if response.candidates:
                    candidate = response.candidates[0]
                    if candidate.finish_reason and candidate.finish_reason not in (0, 1):
                        error_reason = f"Blocked by safety filter (finish_reason: {candidate.finish_reason})"
                        self._log_audit(req, status=400, response_text=error_reason, error=error_reason)
                        return user_friendly_error, input_tokens, output_tokens
                    
                    if candidate.content and candidate.content.parts:
                        text_response = candidate.content.parts[0].text
                        self._log_audit(req, status=200, response_text=text_response)
                        return text_response, input_tokens, output_tokens

                block_reason = getattr(response.prompt_feedback, "block_reason", "PROHIBITED_CONTENT")
                error_reason = f"Blocked prompt: {block_reason}"
                self._log_audit(req, status=400, response_text=error_reason, error=error_reason)
                return user_friendly_error, input_tokens, output_tokens

            except ResourceExhausted as e:
                error_msg = f"Quota Exceeded (Key index {self.current_key_index}): {e}"
                logger.warning(f"⚠️ Ключ #{self.current_key_index} поймал 429. Ротируем ключ...")
                self._log_audit(req, status=429, response_text=error_msg, error=error_msg)
                self._rotate_key()
                continue

            except GoogleAPIError as e:
                status_code = getattr(e, "code", 500) or 500
                error_msg = getattr(e, "message", str(e))
                logger.error(f"Gemini API Error [{status_code}]: {error_msg}")
                self._log_audit(req, status=status_code, response_text=error_msg, error=error_msg)
                return user_friendly_error, 0, 0

            except Exception as e:
                logger.error(f"Unexpected Exception: {e}", exc_info=True)
                self._log_audit(req, status=500, response_text=str(e), error=str(e))
                return user_friendly_error, 0, 0

        logger.error("❌ Все доступные API-ключи исчерпали квоту.")
        return user_friendly_error, 0, 0

    def get_audit_logs(self) -> list[str]:
        """Заглушка или метод для получения логов из аудита, если требуется"""
        if hasattr(self.audit_service, "get_logs"):
            return self.audit_service.get_logs()
        return []

    def _log_audit(self, request, status: int, response_text: str, error: str = None):
        class DummyResponse:
            def __init__(self, st: int, t_resp: str):
                self.status_code = st
                self.text = t_resp[:300]

        self.audit_service.log_transport_event(
            request=request,
            response=DummyResponse(status, response_text),
            error=error
        )
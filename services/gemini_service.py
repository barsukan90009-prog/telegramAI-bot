import logging
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from google.api_core.exceptions import ResourceExhausted, GoogleAPIError
from services.http_audit_service import HttpAuditService

logger = logging.getLogger(__name__)


class GeminiService:
    def __init__(self, api_key: str, model_name: str, audit_service: HttpAuditService):
        self.api_key = api_key
        self.model_name = model_name if model_name.startswith("models/") else f"models/{model_name}"
        self.audit_service = audit_service
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }

    async def generate_response(
        self, full_prompt: str, system_instruction: str
    ) -> tuple[str, int, int]:
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_instruction
        ) if system_instruction else self.model

        # Формируем объект запроса с прокинутым body
        class DummyRequest:
            def __init__(self, model_name: str, prompt: str, sys_instruction: str):
                self.url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent"
                self.method = "POST"
                self.headers = {"Content-Type": "application/json"}
                self.body = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "system_instruction": sys_instruction
                }

        req = DummyRequest(self.model_name, full_prompt, system_instruction)
        user_friendly_error = "Что-то пошло не так. Попробуйте позже или обратитесь к администратору."

        try:
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
            # Превышение лимитов (429 Too Many Requests / Quota Exceeded)
            error_msg = str(e)
            logger.warning(f"Gemini API Quota Exceeded [429]: {error_msg}")
            self._log_audit(req, status=429, response_text=error_msg, error=error_msg)
            return user_friendly_error, 0, 0

        except GoogleAPIError as e:
            # Остальные ошибки Google API (400, 401, 403, 503)
            status_code = getattr(e, "code", 500) or 500
            error_msg = getattr(e, "message", str(e))
            logger.error(f"Gemini API Error [{status_code}]: {error_msg}")
            self._log_audit(req, status=status_code, response_text=error_msg, error=error_msg)
            return user_friendly_error, 0, 0

        except Exception as e:
            # Сетевые или локальные сбои
            logger.error(f"Unexpected Exception: {e}", exc_info=True)
            self._log_audit(req, status=500, response_text=str(e), error=str(e))
            return user_friendly_error, 0, 0

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
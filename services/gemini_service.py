import asyncio
from google import genai
from google.genai import types as genai_types

class GeminiService:
    """Сервис взаимодействия с Google GenAI API."""

    def __init__(self, api_key: str, model_name: str, max_retries: int = 5):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model_name
        self._max_retries = max_retries
        self._safety_settings = [
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
            ),
            genai_types.SafetySetting(
                category=genai_types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=genai_types.HarmBlockThreshold.BLOCK_NONE,
            ),
        ]

    async def generate_response(self, full_prompt: str, system_instruction: str) -> tuple[str, int, int]:
        for attempt in range(self._max_retries):
            try:
                response = await self._client.aio.models.generate_content(
                    model=self._model_name,
                    contents=full_prompt,
                    config=genai_types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        safety_settings=self._safety_settings,
                        temperature=1.0,
                    ),
                )
                
                text = response.text if response and response.text else "Слышь, Gemini че-то затупил, давай заново."
                
                # Достаем количество токенов
                input_tokens = 0
                output_tokens = 0
                if response and response.usage_metadata:
                    input_tokens = response.usage_metadata.prompt_token_count or 0
                    output_tokens = response.usage_metadata.candidates_token_count or 0

                return text, input_tokens, output_tokens

            except Exception as err:
                await self._handle_retry(err, attempt)

        raise RuntimeError("Не удалось получить ответ от API после серии попыток.")

    async def _handle_retry(self, err: Exception, attempt: int) -> None:
        err_str = str(err)
        is_rate_limit = any(code in err_str for code in ("429", "503", "RESOURCE_EXHAUSTED"))

        if is_rate_limit and attempt < self._max_retries - 1:
            sleep_time = (attempt + 1) * 2  # Паузы: 2с, 4с, 6с, 8с (вместо 3, 6, 9, 12)
            print(f"[LOG] Лимит API (429/503). Ожидание {sleep_time}с... Попытка {attempt + 1}/{self._max_retries}")
            await asyncio.sleep(sleep_time)
        else:
            raise err
import time
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AuditLogEntry:
    timestamp: str
    url: str
    method: str
    request_headers: Dict[str, str]
    request_body: str
    status_code: int
    response_body: str


class HttpAuditService:
    """Сервис для логирования сетевых событий и HTTP-запросов."""

    def __init__(self) -> None:
        self.logs: List[AuditLogEntry] = []

    def log_transport_event(
        self,
        request: Any,
        response: Optional[Any] = None,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """Перехватывает и сохраняет детали HTTP-запросов и ответов."""
        try:
            url = str(getattr(request, "url", "Unknown URL"))
            method = str(getattr(request, "method", "POST"))
            headers_raw = getattr(request, "headers", {})
            request_headers = dict(headers_raw) if headers_raw else {}

            # Извлекаем request_body (словарь, строка или объект)
            req_body_raw = getattr(request, "body", getattr(request, "json", ""))
            if isinstance(req_body_raw, (dict, list)):
                request_body = json.dumps(req_body_raw, ensure_ascii=False)
            else:
                request_body = str(req_body_raw) if req_body_raw else "{}"

            status_code = 0
            response_body = ""

            if response is None and "response" in kwargs:
                response = kwargs["response"]

            if response is not None:
                status_code = getattr(response, "status_code", getattr(response, "status", 200))
                if hasattr(response, "text"):
                    response_body = str(response.text)
                elif hasattr(response, "content"):
                    response_body = response.content.decode("utf-8", errors="ignore")
                else:
                    response_body = str(response)
            else:
                status_code = 200
                response_body = "Запрос зарегистрирован без тела ответа"

            entry = AuditLogEntry(
                timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                url=url,
                method=method,
                request_headers=request_headers,
                request_body=request_body,
                status_code=status_code,
                response_body=response_body,
            )
            self.logs.append(entry)
            print(f"📡 [HTTP AUDIT] {method} {url} -> [{status_code}]")

        except Exception as log_err:
            print(f"⚠️ Ошибка логирования HTTP: {log_err}")

    def format_logs_for_tg(self, limit: int = 5) -> str:
        """Форматирует последние логи для вывода в Telegram по команде /audit."""
        if not self.logs:
            return "📭 Логи аудита пусты."

        recent_logs = self.logs[-limit:]
        text_parts = [f"🌐 **HTTP Audit Log** (Всего перехвачено: {len(self.logs)}):\n"]

        for idx, log in enumerate(reversed(recent_logs), 1):
            req_headers_str = json.dumps(log.request_headers, ensure_ascii=False)
            
            # Обрезаем длинные ответы для читаемости в ТГ
            resp_body_preview = log.response_body[:300] + "..." if len(log.response_body) > 300 else log.response_body
            req_body_preview = log.request_body[:200] + "..." if len(log.request_body) > 200 else log.request_body

            entry_text = (
                f"**#{idx}**\n"
                f"🔹 **URL:** `{log.url}`\n"
                f"🔹 **Метод:** {log.method}\n"
                f"🔹 **Код ответа:** `{log.status_code}`\n"
                f"⏱ **Время:** {log.timestamp}\n\n"
                f"📥 **Request Headers:**\n`{req_headers_str}`\n"
                f"📥 **Request Body:**\n`{req_body_preview}`\n"
                f"📤 **Response Body:**\n`{resp_body_preview}`\n"
                f"-----------------------------------"
            )
            text_parts.append(entry_text)

        return "\n\n".join(text_parts)
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AuditLogEntry:
    timestamp: str
    url: str
    method: str
    request_headers: Dict[str, str]
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
                status_code=status_code,
                response_body=response_body,
            )
            self.logs.append(entry)
            print(f"📡 [HTTP AUDIT] {method} {url} -> [{status_code}]")

        except Exception as log_err:
            print(f"⚠️ Ошибка логирования HTTP: {log_err}")
# models/chat_repository.py
from collections import deque

class ChatHistoryRepository:
    """Модель для хранения и управления контекстом сообщений."""

    def __init__(self, maxlen: int = 100):
        self._buffers: dict[int, deque] = {}
        self._maxlen = maxlen

    def add_message(self, chat_id: int, formatted_text: str) -> None:
        if chat_id not in self._buffers:
            self._buffers[chat_id] = deque(maxlen=self._maxlen)
        self._buffers[chat_id].append(formatted_text)

    def get_history(self, chat_id: int) -> list[str]:
        return list(self._buffers.get(chat_id, []))

    def clear_history(self, chat_id: int) -> None:
        if chat_id in self._buffers:
            self._buffers[chat_id].clear()
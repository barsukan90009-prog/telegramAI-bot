from collections import defaultdict, deque
from typing import List


class ChatHistoryRepository:
    """Репозиторий для хранения истории сообщений пользователей."""

    def __init__(self, max_history: int = 10) -> None:
        self.max_history = max_history
        self._histories: dict[int, deque] = {}

    def add_message(self, chat_id: int, message: str) -> None:
        """Добавляет сообщение в историю чата с учетом ограничения max_history."""
        if chat_id not in self._histories:
            self._histories[chat_id] = deque(maxlen=self.max_history)
        self._histories[chat_id].append(message)

    def get_history(self, chat_id: int) -> List[str]:
        """Возвращает историю сообщений для указанного чата."""
        if chat_id not in self._histories:
            return []
        return list(self._histories[chat_id])

    def clear_history(self, chat_id: int) -> None:
        """Очищает историю сообщений чата."""
        if chat_id in self._histories:
            self._histories[chat_id].clear()

    def trim_history(self, chat_id: int, keep_last: int = 2) -> None:
        """Принудительно сжимает историю чата при ошибках токенов."""
        if chat_id in self._histories:
            items = list(self._histories[chat_id])[-keep_last:]
            self._histories[chat_id] = deque(items, maxlen=self.max_history)
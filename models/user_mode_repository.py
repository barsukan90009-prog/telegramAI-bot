class UserModeRepository:
    """Репозиторий для хранения выбранного режима/стиля общения каждого чата."""

    def __init__(self, default_mode: str = "bydlo") -> None:
        self.default_mode = default_mode
        self._modes: dict[int, str] = {}

    def get_mode(self, chat_id: int) -> str:
        """Возвращает текущий режим пользователя или дефолтный."""
        return self._modes.get(chat_id, self.default_mode)

    def set_mode(self, chat_id: int, mode: str) -> None:
        """Устанавливает новый режим общения для чата."""
        self._modes[chat_id] = mode
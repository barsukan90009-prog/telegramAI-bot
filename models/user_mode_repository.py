class UserModeRepository:
    """Модель для хранения выбранного режима работы бота для каждого чата."""

    DEFAULT_MODE = "bydlo"

    def __init__(self):
        # Храним {chat_id: "mode_key"}
        self._modes: dict[int, str] = {}

    def set_mode(self, chat_id: int, mode: str) -> None:
        self._modes[chat_id] = mode

    def get_mode(self, chat_id: int) -> str:
        return self._modes.get(chat_id, self.DEFAULT_MODE)
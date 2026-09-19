class StatsRepository:
    """Модель для сбора и агрегации статистики использования бота."""

    def __init__(self):
        self.total_requests: int = 0
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.mode_usage: dict[str, int] = {}

    def log_request(self, mode: str, input_tokens: int, output_tokens: int) -> None:
        """Записывает данные о выполненном запросе."""
        self.total_requests += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.mode_usage[mode] = self.mode_usage.get(mode, 0) + 1

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def get_summary_text(self) -> str:
        """Формирует красивый текстовый отчет."""
        if self.total_requests == 0:
            return "📊 **Статистика пока пуста.** Сделайте первый запрос!"

        modes_stat = "\n".join(
            f"  • {mode}: {count} раз" for mode, count in self.mode_usage.items()
        )

        return (
            "📊 **Статистика использования бота:**\n\n"
            f"🔹 **Всего запросов:** `{self.total_requests}`\n"
            f"📥 **Входные токены (Prompt):** `{self.total_input_tokens:,}`\n"
            f"📤 **Выходные токены (Response):** `{self.total_output_tokens:,}`\n"
            f"🧮 **Суммарно токенов:** `{self.total_tokens:,}`\n\n"
            f"🎭 **Использование режимов:**\n{modes_stat}"
        )
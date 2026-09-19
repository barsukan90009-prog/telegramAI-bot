from collections import defaultdict


class StatsRepository:
    """Репозиторий статистики расхода токенов по режимам."""

    def __init__(self) -> None:
        self.requests_count: dict[str, int] = defaultdict(int)
        self.input_tokens: dict[str, int] = defaultdict(int)
        self.output_tokens: dict[str, int] = defaultdict(int)

    def log_request(self, mode: str, input_t: int, output_t: int) -> None:
        """Регистрирует статистику вызова LLM."""
        self.requests_count[mode] += 1
        self.input_tokens[mode] += input_t
        self.output_tokens[mode] += output_t

    def get_summary_text(self) -> str:
        """Формирует текстовый отчёт со статистикой."""
        if not self.requests_count:
            return "📊 **Статистика вызовов пуста.**"

        total_req = sum(self.requests_count.values())
        total_in = sum(self.input_tokens.values())
        total_out = sum(self.output_tokens.values())

        text = f"📊 **Статистика использования Gemini:**\n\n"
        text += f"🔹 Всего запросов: `{total_req}`\n"
        text += f"📥 Входные токены: `{total_in}`\n"
        text += f"📤 Выходные токены: `{total_out}`\n\n"
        text += "**По режимам:**\n"

        for mode, count in self.requests_count.items():
            in_t = self.input_tokens[mode]
            out_t = self.output_tokens[mode]
            text += f"• `{mode}`: {count} зап., in: {in_t}, out: {out_t}\n"

        return text
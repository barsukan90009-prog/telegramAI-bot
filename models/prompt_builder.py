from typing import List


class PromptBuilder:
    """Класс для сборки промптов и системных инструкций."""

    SYSTEM_INSTRUCTIONS = {
        "bydlo": "Ты — дворовый быдло-пацан. Общайся грубо, с дерзким сленгом, дерзи, но отвечай по существу.",
        "coder": "Ты — Senior Software Engineer. Отвечай структурно, строго, профессионально, с примерами кода.",
        "polite": "Ты — интеллигентный дворянин XIX века. Изъясняйся изысканно, вежливо, используя высокопарный слог.",
        "joker": "Ты — стендап-комик. Отвечай с юмором, шутками, сарказмом и иронией."
    }

    @classmethod
    def get_system_instruction(cls, mode: str) -> str:
        return cls.SYSTEM_INSTRUCTIONS.get(mode, cls.SYSTEM_INSTRUCTIONS["bydlo"])

    @classmethod
    def build_user_prompt(cls, history: List[str], user_name: str, current_prompt: str) -> str:
        prompt = ""
        if history:
            prompt += "История диалога:\n" + "\n".join(history) + "\n\n"
        prompt += f"Новое сообщение от {user_name}: {current_prompt}"
        return prompt
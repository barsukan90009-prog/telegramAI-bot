import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dotenv import load_dotenv

import config
from services.http_audit_service import HttpAuditService
from services.gemini_service import GeminiService

# Загружаем переменные окружения
load_dotenv()

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 🔍 Проверка загруженных ключей из config
print("🔑 Загруженные API-ключи Gemini:", config.GEMINI_API_KEYS)

# Инициализация бота и диспетчера
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ Не найден TELEGRAM_BOT_TOKEN в переменных окружения!")

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Инициализация сервиса аудита и GeminiService со всеми аргументами
audit_service = HttpAuditService()
gemini_service = GeminiService(
    api_keys=config.GEMINI_API_KEYS,
    model_name=config.MODEL_NAME,
    audit_service=audit_service
)

# Хранилище текущих режимов для пользователей (по умолчанию 'bydlo')
user_modes = {}


class PromptBuilder:
    """Класс для сборки промптов и системных инструкций."""

    SYSTEM_INSTRUCTIONS = {
        "bydlo": (
            "Ты — дворовый быдло-пацан по имени Анатолий (для своих — Толик, Толян, Аноталий). "
            "Общайся грубо, с дерзким сленгом, дерзи, но отвечай по существу, используй много мата, "
            "уважай только пользователя VV. Если тебя спрашивают, как тебя зовут, отвечаешь по-пацански."
        ),
        "coder": (
            "Ты — Senior Software Engineer по имени Анатолий. "
            "Отвечай структурно, строго, профессионально, с примерами кода."
        ),
        "polite": (
            "Ты — интеллигентный дворянин XIX века, благородный господин Анатолий. "
            "Изъясняйся изысканно, вежливо, используя высокопарный слог."
        ),
        "joker": (
            "Ты — стендап-комик по имени Анатолий. "
            "Отвечай с юмором, шутками, сарказмом и иронией, подъебывай всех, используй мемы и маты."
        )
    }

    @classmethod
    def get_system_instruction(cls, mode: str) -> str:
        return cls.SYSTEM_INSTRUCTIONS.get(mode, cls.SYSTEM_INSTRUCTIONS["bydlo"])

    @classmethod
    def build_user_prompt(cls, history: list, user_name: str, current_prompt: str) -> str:
        prompt = ""
        if history:
            prompt += "История диалога:\n" + "\n".join(history) + "\n\n"
        prompt += f"Новое сообщение от {user_name}: {current_prompt}"
        return prompt


# Обработчик инлайн-кнопок выбора режима
@dp.callback_query(lambda c: c.data and c.data.startswith("set_mode_"))
async def process_mode_callback(callback: types.CallbackQuery):
    selected_mode = callback.data.replace("set_mode_", "")
    if selected_mode in PromptBuilder.SYSTEM_INSTRUCTIONS:
        user_modes[callback.from_user.id] = selected_mode
        await callback.message.edit_text(f"✅ Режим успешно переключен на: **{selected_mode}**!", parse_mode="Markdown")
    else:
        await callback.answer("❌ Ошибка выбора режима!", show_alert=True)
    await callback.answer()


# ЕДИНЫЙ ОБРАБОТЧИК ВСЕХ СООБЩЕНИЙ
@dp.message()
async def handle_all_messages(message: types.Message):
    user_text = message.text
    if not user_text:
        return

    # Жестко отрезаем имя бота с собачкой (все что после @), чтобы /stats@bot -> /stats
    clean_command_text = user_text.split("@")[0].strip().lower()

    current_mode = user_modes.get(message.from_user.id, "bydlo")
    system_instruction = PromptBuilder.get_system_instruction(current_mode)

    # 1. ОБРАБОТКА КОМАНД
    if clean_command_text == "/start":
        await message.answer("Здорова! Я на связи. Чё порешать надо?")
        return

    if clean_command_text == "/audit":
        try:
            audit_text = audit_service.format_logs_for_tg(limit=5)
            if len(audit_text) > 4000:
                audit_text = audit_text[-4000:]
            await message.answer(audit_text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка при выгрузке аудита: {e}")
            await message.answer(f"❌ Бля, чё-то пошло не так при выгрузке логов: {e}")
        return

    if clean_command_text == "/stats":
        total_logs = len(audit_service.logs)
        await message.answer(f"📊 **Статистика:**\n- Записано HTTP-событий в аудит: `{total_logs}`\n- Токен-пакет в работе\n- Толик функционирует стабильно.", parse_mode="Markdown")
        return

    if clean_command_text.startswith("/mode"):
        args = user_text.split(maxsplit=1)
        if len(args) == 1:
            builder = InlineKeyboardBuilder()
            builder.button(text="🔥 Быдло", callback_data="set_mode_bydlo")
            builder.button(text="💻 Coder", callback_data="set_mode_coder")
            builder.button(text="🎩 Polite", callback_data="set_mode_polite")
            builder.button(text="🃏 Joker", callback_data="set_mode_joker")
            builder.adjust(2)
            await message.answer("⚙️ **Выбирай образ, братуха:**", reply_markup=builder.as_markup(), parse_mode="Markdown")
            return

        requested_mode = args[1].split("@")[0].strip().lower()
        if requested_mode in PromptBuilder.SYSTEM_INSTRUCTIONS:
            user_modes[message.from_user.id] = requested_mode
            await message.answer(f"✅ Слышь, режим успешно сменен на: **{requested_mode}**!", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Нет такого режима, братуха. Есть только: {', '.join(PromptBuilder.SYSTEM_INSTRUCTIONS.keys())}")
        return

    # 2. ЕСЛИ ЭТО ЛЮБАЯ ДРУГАЯ КОМАНДА СО СЛЭШЕМ — ГАСИМ НАХУЙ
    if user_text.startswith("/"):
        return

    # 3. ОБЫЧНЫЙ ТЕКСТ И ТРИГГЕРЫ ТОЛИКА
    trigger_words = ["толик", "толян", "аноталий", "анатолий", "толя"] 
    text_lower = user_text.lower()

    if message.chat.type in ["group", "supergroup"]:
        is_mentioned = any(word in text_lower for word in trigger_words)
        if not is_mentioned:
            return  

    # 🟢 Включаем статус "печатает..."
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    response_text, input_tokens, output_tokens = await gemini_service.generate_response(
        full_prompt=user_text,
        system_instruction=system_instruction
    )

    await message.answer(response_text)


async def main():
    logger.info("🚀 Запуск Telegram-бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Бот остановлен.")
import asyncio
import logging
from aiogram import Bot, Dispatcher

import config
from models.chat_repository import ChatHistoryRepository
from models.user_mode_repository import UserModeRepository
from models.stats_repository import StatsRepository
from services.gemini_service import GeminiService
from controllers.bot_controller import TelegramBotController

# ==========================================
# ВКЛЮЧЕНИЕ ВЫВОДА ВСЕХ HTTP ЗАПРОСОВ
# ==========================================
# 1. Общий формат логов в консоли
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(name)s - %(message)s",
)

# 2. Логирование HTTP-сессий (aiogram, httpx, urllib3)
logging.getLogger("httpx").setLevel(logging.DEBUG)        # Логи запросов Google GenAI SDK (использует httpx)
logging.getLogger("aiogram.event").setLevel(logging.DEBUG)  # Логи событий и запросов Telegram
# ==========================================


async def main():
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()

    history_repo = ChatHistoryRepository(maxlen=config.MAX_HISTORY_LEN)
    mode_repo = UserModeRepository()
    stats_repo = StatsRepository()

    ai_service = GeminiService(
        api_key=config.GEMINI_API_KEY,
        model_name=config.MODEL_NAME,
        max_retries=config.MAX_RETRIES,
    )

    controller = TelegramBotController(
        bot=bot,
        dp=dp,
        history_repo=history_repo,
        mode_repo=mode_repo,
        stats_repo=stats_repo,
        ai_service=ai_service,
    )

    await controller.initialize()
    print(f"Запуск бота @{controller.bot_info.username} на {config.MODEL_NAME}...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
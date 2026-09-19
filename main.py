import asyncio
import os
import sys
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher

from models.chat_repository import ChatHistoryRepository
from models.user_mode_repository import UserModeRepository
from models.stats_repository import StatsRepository
from services.gemini_service import GeminiService
from services.http_audit_service import HttpAuditService
from controllers.bot_controller import TelegramBotController

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash")

if not BOT_TOKEN or not GEMINI_API_KEY:
    print("❌ Ошибка: Убедитесь, что BOT_TOKEN и GEMINI_API_KEY указаны в файле .env")
    sys.exit(1)


async def main() -> None:
    audit_service = HttpAuditService()

    history_repo = ChatHistoryRepository(max_history=10)
    mode_repo = UserModeRepository(default_mode="bydlo")
    stats_repo = StatsRepository()

    ai_service = GeminiService(
        api_key=GEMINI_API_KEY,
        model_name=MODEL_NAME,
        audit_service=audit_service
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    controller = TelegramBotController(
        bot=bot,
        dp=dp,
        history_repo=history_repo,
        mode_repo=mode_repo,
        stats_repo=stats_repo,
        ai_service=ai_service,
        audit_service=audit_service
    )

    await controller.initialize()

    bot_user = controller.bot_info
    print(f"Запуск бота @{bot_user.username} на {MODEL_NAME}...")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
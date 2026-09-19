import asyncio
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from models.chat_repository import ChatHistoryRepository
from models.user_mode_repository import UserModeRepository
from models.stats_repository import StatsRepository
from models.prompt_builder import PromptBuilder
from services.gemini_service import GeminiService
from services.http_audit_service import HttpAuditService


class TelegramBotController:
    """Контроллер: управляет логикой бота и связывает обработку со службами."""

    def __init__(
        self,
        bot: Bot,
        dp: Dispatcher,
        history_repo: ChatHistoryRepository,
        mode_repo: UserModeRepository,
        stats_repo: StatsRepository,
        ai_service: GeminiService,
        audit_service: HttpAuditService,
    ):
        self.bot = bot
        self.dp = dp
        self.history_repo = history_repo
        self.mode_repo = mode_repo
        self.stats_repo = stats_repo
        self.ai_service = ai_service
        self.audit_service = audit_service
        self.is_processing: dict[int, bool] = {}
        self.bot_info: types.User | None = None

        self._register_handlers()

    def _register_handlers(self) -> None:
        self.dp.message(CommandStart())(self.cmd_start)
        self.dp.message(Command("clear"))(self.cmd_clear)
        self.dp.message(Command("mode"))(self.cmd_mode)
        self.dp.message(Command("stats"))(self.cmd_stats)
        self.dp.message(Command("audit"))(self.cmd_audit)
        self.dp.callback_query(F.data.startswith("set_mode_"))(self.handle_mode_callback)
        self.dp.message()(self.handle_message)

    async def initialize(self) -> None:
        self.bot_info = await self.bot.get_me()

    def _get_mode_keyboard(self) -> InlineKeyboardMarkup:
        buttons = [
            [
                InlineKeyboardButton(text="🤬 Быдло-пацан", callback_data="set_mode_bydlo"),
                InlineKeyboardButton(text="💻 Сеньор-Программист", callback_data="set_mode_coder"),
            ],
            [
                InlineKeyboardButton(text="🎩 Вежливый Дворянин", callback_data="set_mode_polite"),
                InlineKeyboardButton(text="🤡 Шутник / Комик", callback_data="set_mode_joker"),
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    async def cmd_start(self, message: types.Message) -> None:
        await message.answer(
            "Привет! Я бот на базе Gemini.\n\n"
            "Выбери стиль общения с помощью команды /mode или ниже:",
            reply_markup=self._get_mode_keyboard()
        )

    async def cmd_mode(self, message: types.Message) -> None:
        current_mode = self.mode_repo.get_mode(message.chat.id)
        await message.answer(
            f"Текущий режим: **{current_mode}**\nВыбери новый стиль общения:",
            reply_markup=self._get_mode_keyboard(),
            parse_mode="Markdown"
        )

    async def cmd_stats(self, message: types.Message) -> None:
        summary = self.stats_repo.get_summary_text()
        await message.answer(summary, parse_mode="Markdown")

    async def cmd_audit(self, message: types.Message) -> None:
        if not self.audit_service.logs:
            await message.answer("🌐 **История HTTP-запросов пуста.**", parse_mode="Markdown")
            return

        last_log = self.audit_service.logs[-1]
        req_headers_str = json.dumps(last_log.request_headers, ensure_ascii=False, indent=2)[:300]
        resp_body_str = last_log.response_body[:400]

        report = (
            f"🌐 **HTTP Audit Log (Всего перехвачено: {len(self.audit_service.logs)}):**\n\n"
            f"🔹 **URL:** `{last_log.url}`\n"
            f"🔹 **Метод:** `{last_log.method}`\n"
            f"🔹 **Код ответа:** `{last_log.status_code}`\n"
            f"⏱ **Время:** `{last_log.timestamp}`\n\n"
            f"📥 **Request Headers:**\n```json\n{req_headers_str}\n```\n"
            f"📤 **Response Body:**\n```json\n{resp_body_str}\n```"
        )
        await message.answer(report, parse_mode="Markdown")

    async def handle_mode_callback(self, callback: types.CallbackQuery) -> None:
        mode_key = callback.data.replace("set_mode_", "")
        self.mode_repo.set_mode(callback.message.chat.id, mode_key)
        
        mode_names = {
            "bydlo": "Быдло-пацан 🤬",
            "coder": "Сеньор-Программист 💻",
            "polite": "Вежливый Дворянин 🎩",
            "joker": "Шутник / Комик 🤡"
        }
        
        selected_name = mode_names.get(mode_key, mode_key)
        await callback.answer(f"Режим изменен на: {selected_name}")
        await callback.message.edit_text(
            f"✅ Стиль бота изменен на: **{selected_name}**\nЗадавай вопросы!",
            parse_mode="Markdown"
        )

    async def cmd_clear(self, message: types.Message) -> None:
        self.history_repo.clear_history(message.chat.id)
        await message.answer("История переписки очищена!")

    async def handle_message(self, message: types.Message) -> None:
        if not message.text:
            return

        chat_id = message.chat.id
        self._record_incoming_message(chat_id, message)

        if not self._should_process(message) or self._is_chat_busy(chat_id):
            return

        self.is_processing[chat_id] = True
        try:
            await self._process_ai_reply(message)
        except Exception as e:
            await self._handle_error(message, e)
        finally:
            self.is_processing[chat_id] = False

    def _record_incoming_message(self, chat_id: int, message: types.Message) -> None:
        user_name = message.from_user.first_name or message.from_user.username or "Пользователь"
        text = f"{user_name}: {message.text}"
        self.history_repo.add_message(chat_id, text)

    def _should_process(self, message: types.Message) -> bool:
        if not self.bot_info:
            return False
        is_private = message.chat.type == "private"
        is_reply = (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == self.bot_info.id
        )
        is_mentioned = f"@{self.bot_info.username}" in message.text
        return is_private or is_reply or is_mentioned

    def _is_chat_busy(self, chat_id: int) -> bool:
        return self.is_processing.get(chat_id, False)

    async def _process_ai_reply(self, message: types.Message) -> None:
        chat_id = message.chat.id
        user_name = message.from_user.first_name or message.from_user.username or "Пользователь"

        clean_text = message.text.replace(f"@{self.bot_info.username}", "").strip()
        prompt_text = clean_text or "Поясни за контекст сообщений выше."

        await self.bot.send_chat_action(chat_id=chat_id, action="typing")
        await asyncio.sleep(0.5)

        history = self.history_repo.get_history(chat_id)
        current_mode = self.mode_repo.get_mode(chat_id)

        system_instruction = PromptBuilder.get_system_instruction(current_mode)
        full_prompt = PromptBuilder.build_user_prompt(history, user_name, prompt_text)

        response_text, in_tokens, out_tokens = await self.ai_service.generate_response(
            full_prompt=full_prompt,
            system_instruction=system_instruction
        )
        
        self.stats_repo.log_request(current_mode, in_tokens, out_tokens)
        self.history_repo.add_message(chat_id, f"Бот: {response_text}")
        await message.reply(response_text)

    async def _handle_error(self, message: types.Message, e: Exception) -> None:
        err_msg = str(e)
        chat_id = message.chat.id

        if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
            self.history_repo.trim_history(chat_id, keep_last=2)
            await message.reply(
                "⚠️ **Превышен лимит запросов Google API (429).**\n"
                "История диалога автоматически сокращена. Попробуй еще раз через пару секунд!"
            )
        else:
            await message.reply(f"Произошла ошибка: {e}")
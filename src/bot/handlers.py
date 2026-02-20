import logging
from aiogram import Bot, Router, F, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from shop_bot.data_manager.database import (
    get_user, register_user, get_user_role, get_user_keys,
    get_setting, get_all_hosts, get_plans_for_host, get_plan_by_id
)
from shop_bot.bot import keyboards
from shop_bot.bot.stars_handler import get_stars_router
from shop_bot.bot.roles_handlers import get_roles_router
from shop_bot.bot.roles_keyboards import create_role_menu_keyboard

logger = logging.getLogger(__name__)

user_router = Router()

class PaymentProcess(StatesGroup):
    waiting_for_email = State()
    waiting_for_payment_method = State()

async def process_successful_payment(bot: Bot, payload: dict):
    """Обработка успешного платежа"""
    user_id = int(payload.get("user_id"))
    months = int(payload.get("months"))
    price = float(payload.get("price"))
    
    # Обновляем статистику пользователя
    # Здесь должна быть логика создания ключа
    
    logger.info(f"Payment processed for user {user_id}: {months} months, {price} RUB")

@user_router.message(CommandStart())
async def start_handler(message: types.Message):
    """Обработчик /start"""
    telegram_id = message.from_user.id
    username = message.from_user.username or message.from_user.full_name
    
    register_user(telegram_id, username)
    
    await message.answer(
        f"👋 Привет, {username}!\n\n"
        "Я бот для покупки VPN ключей.\n"
        "Нажмите /menu для главного меню."
    )

@user_router.message(Command("menu"))
async def menu_handler(message: types.Message):
    """Обработчик /menu"""
    await show_main_menu(message)

async def show_main_menu(message: types.Message, edit_message: bool = False):
    """Показ главного меню"""
    user_id = message.chat.id
    user_db_data = get_user(user_id)
    user_keys = get_user_keys(user_id)
    user_role = get_user_role(user_id)
    
    text = "🏠 <b>Главное меню</b>\n"
    if user_role == "dealer":
        text += "👔 <b>Дилер</b>\n\n"
    elif user_role == "admin":
        text += "🛡 <b>Администратор</b>\n\n"
    text += "Выберите действие:"
    
    if user_role in ["dealer", "admin"]:
        keyboard = create_role_menu_keyboard(user_id)
    else:
        keyboard = keyboards.create_main_menu_keyboard(user_keys, True, user_role == "admin")
    
    if edit_message:
        try:
            await message.edit_text(text, reply_markup=keyboard)
        except:
            await message.answer(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)

@user_router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_handler(callback: types.CallbackQuery):
    """Возврат в главное меню"""
    await show_main_menu(callback.message, edit_message=True)

def get_user_router() -> Router:
    """Получение роутера пользователя"""
    stars_router = get_stars_router()
    roles_router = get_roles_router()
    
    user_router.include_router(stars_router)
    user_router.include_router(roles_router)
    
    return user_router
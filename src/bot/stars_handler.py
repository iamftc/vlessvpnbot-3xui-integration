import logging
import json
from aiogram import Bot, Router, F, types
from aiogram.fsm.context import FSMContext
from decimal import Decimal, ROUND_HALF_UP
from shop_bot.data_manager.database import get_user, get_plan_by_id, get_setting, log_transaction
from shop_bot.bot.handlers import PaymentProcess, process_successful_payment

logger = logging.getLogger(__name__)

def get_stars_router() -> Router:
    stars_router = Router()
    
    @stars_router.callback_query(PaymentProcess.waiting_for_payment_method, F.data == "pay_stars")
    async def create_stars_invoice_handler(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer("Создаю счет для оплаты звёздами...")
        try:
            data = await state.get_data()
            user_id = callback.from_user.id
            plan_id = data.get("plan_id")
            plan = get_plan_by_id(plan_id)
            user_data = get_user(user_id)
            
            if not plan:
                await callback.message.edit_text("❌ Ошибка: Тариф не найден.")
                await state.clear()
                return
            
            base_price = Decimal(str(plan["price"]))
            price_rub = base_price
            
            # Реферальная скидка
            if user_data.get("referred_by") and user_data.get("total_spent", 0) == 0:
                discount_str = get_setting("referral_discount") or "0"
                discount = Decimal(discount_str)
                if discount > 0:
                    price_rub = base_price - (base_price * discount / 100)
            
            # Конвертация в звёзды
            stars_rate = Decimal(get_setting("stars_price_rub") or "1.0")
            price_stars = int((price_rub / stars_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            
            if price_stars <= 0:
                await callback.message.edit_text("❌ Ошибка при расчёте стоимости.")
                await state.clear()
                return
            
            metadata = {
                "user_id": str(user_id),
                "months": str(plan["months"]),
                "price": str(float(price_rub)),
                "action": data.get("action", "buy"),
                "key_id": str(data.get("key_id", 0)),
                "host_name": data.get("host_name", ""),
                "plan_id": str(plan_id),
                "customer_email": data.get("customer_email", ""),
                "payment_method": "Telegram Stars"
            }
            
            await callback.bot.send_invoice(
                chat_id=user_id,
                title=f"VPN Подписка - {plan['plan_name']}",
                description=f"Оплата подписки на {plan['months']} месяц(ов)",
                payload=json.dumps(metadata),
                provider_token="",
                currency="XTR",
                prices=[types.LabeledPrice(label=f"Подписка на {plan['months']} мес.", amount=price_stars)],
                start_parameter=f"stars_invoice_{plan_id}"
            )
            
            await state.clear()
            await callback.message.edit_text("⏳ Счет отправлен. Нажмите на него, чтобы оплатить звёздами.")
            
        except Exception as e:
            logger.error(f"Failed to create Stars invoice: {e}", exc_info=True)
            await callback.message.edit_text(f"❌ Ошибка: {str(e)}")
            await state.clear()
    
    @stars_router.pre_checkout_query()
    async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery, bot: Bot):
        try:
            await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        except Exception as e:
            logger.error(f"Error in pre-checkout: {e}")
            await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False, error_message="Ошибка платежа")
    
    @stars_router.message(F.successful_payment)
    async def successful_payment_handler(message: types.Message, bot: Bot):
        try:
            if message.successful_payment.currency != "XTR":
                return
            
            payload = json.loads(message.successful_payment.invoice_payload)
            await process_successful_payment(bot, payload)
            await message.answer("✅ Спасибо за оплату! Ваш ключ готов.")
            
        except Exception as e:
            logger.error(f"Error processing Stars payment: {e}", exc_info=True)
            await message.answer("❌ Ошибка при обработке платежа.")
    
    return stars_router
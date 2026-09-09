import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date
from dotenv import load_dotenv
import db

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
raw_user_id = os.getenv("MY_USER_ID")
MY_USER_ID = int(raw_user_id) if raw_user_id and raw_user_id.isdigit() else 0

PAYMENT_DATES = [10, 25]  # Дни выплаты зарплаты и аванса

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db.init_db()

# Полный список категорий расходов
EXPENSE_CATEGORIES = {
    "cat_food": "🥗 Продукты питания",
    "cat_house": "🛒 Бытовые нужды",
    "cat_auto": "🚗 Автомобиль",
    "cat_habits": "🚬 Вредные привычки",
    "cat_health": "💊 Гигиена и здоровье",
    "cat_kids": "🧸 Дети",
    "cat_clothes": "👕 Одежда и косметика",
    "cat_communal": "🏠 КУ и ЖКХ",
    "cat_transport": "🚌 Общественный транспорт",
    "cat_cafe": "☕ Кафе и рестораны",
    "cat_other": "📦 Разное / Прочее"
}

class ExpenseState(StatesGroup): waiting_for_amount = State()
class IncomeState(StatesGroup): waiting_for_amount = State()
class ReserveState(StatesGroup): waiting_for_amount = State()

def is_owner(user_id: int) -> bool:
    return user_id == MY_USER_ID

def days_until_next_payment() -> int:
    today = date.today()
    next_payment_day = next((day for day in sorted(PAYMENT_DATES) if today.day < day), None)
    
    if next_payment_day:
        target_date = date(today.year, today.month, next_payment_day)
    else:
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        target_date = date(next_year, next_month, min(PAYMENT_DATES))

    delta = (target_date - today).days
    return delta if delta > 0 else 1

# --- МЕНЮ ---
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Сводка и Лимит", callback_data="summary")
    builder.button(text="💳 Записать расход", callback_data="show_expenses")
    builder.button(text="💰 Внести доход", callback_data="add_income")
    builder.button(text="🧊 Отложить на платежи", callback_data="manage_reserves")
    builder.button(text="📜 История и Отмена", callback_data="history_menu")
    builder.button(text="📈 Месячный отчет", callback_data="monthly_report")
    builder.adjust(1, 1, 2, 2)
    return builder.as_markup()

def get_expenses_menu():
    builder = InlineKeyboardBuilder()
    for code, name in EXPENSE_CATEGORIES.items():
        builder.button(text=name, callback_data=code)
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(2, 2, 2, 2, 2, 1)
    return builder.as_markup()

def get_reserves_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏦 Ипотека", callback_data="reserve_ипотека")
    builder.button(text="💳 Кредитки", callback_data="reserve_кредитки")
    builder.button(text="🎒 Школа", callback_data="reserve_школа")
    builder.button(text="🌐 Интернет", callback_data="reserve_интернет")
    builder.button(text="📱 Связь", callback_data="reserve_связь")
    builder.button(text="✅ Оплатить из отложенного", callback_data="pay_menu")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(2, 2, 1, 1, 1)
    return builder.as_markup()

def get_pay_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏦 Ипотеку", callback_data="pay_ипотека")
    builder.button(text="💳 Кредитки", callback_data="pay_кредитки")
    builder.button(text="🎒 Школу", callback_data="pay_школа")
    builder.button(text="🌐 Интернет", callback_data="pay_интернет")
    builder.button(text="📱 Связь", callback_data="pay_связь")
    builder.button(text="⬅️ Назад", callback_data="manage_reserves")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def get_history_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить последнюю операцию", callback_data="cancel_last")
    builder.button(text="⬅️ Назад", callback_data="back_to_main")
    builder.adjust(1, 1)
    return builder.as_markup()

# --- ОБРАБОТЧИКИ НАВИГАЦИИ ---
@dp.message(CommandStart())
async def cmd_start(message: Message):
    if not is_owner(message.from_user.id):
        return
    await message.answer("Фин-центр активен. Что сделаем?", reply_markup=get_main_menu())

@dp.callback_query(F.data == "back_to_main")
async def go_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню:", reply_markup=get_main_menu())

@dp.callback_query(F.data == "show_expenses")
async def show_expenses(callback: CallbackQuery):
    await callback.message.edit_text("Выберите категорию расхода:", reply_markup=get_expenses_menu())

@dp.callback_query(F.data == "manage_reserves")
async def show_reserves(callback: CallbackQuery):
    await callback.message.edit_text("🧊 Управление обязательными платежами:", reply_markup=get_reserves_menu())

@dp.callback_query(F.data == "pay_menu")
async def show_pay_menu(callback: CallbackQuery):
    await callback.message.edit_text("Что именно сейчас оплачиваем из резерва?", reply_markup=get_pay_menu())

# --- ВНЕСЕНИЕ РАСХОДА (Вручную) ---
@dp.callback_query(F.data.startswith("cat_"))
async def process_cat_btn(callback: CallbackQuery, state: FSMContext):
    category_name = EXPENSE_CATEGORIES[callback.data]
    await state.update_data(category=category_name)
    await state.set_state(ExpenseState.waiting_for_amount)
    await callback.message.edit_text(f"Введите сумму расхода для <b>{category_name}</b>:", parse_mode="HTML")

@dp.message(ExpenseState.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        data = await state.get_data()
        db.add_transaction("expense", data['category'], amount)
        await message.answer(f"✅ Учтено: <b>{amount:,.0f} ₽</b> в '{data['category']}'", reply_markup=get_main_menu(), parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число (например: 350 или 1200.50).")

# --- ВНЕСЕНИЕ ДОХОДА (Вручную) ---
@dp.callback_query(F.data == "add_income")
async def process_income_btn(callback: CallbackQuery, state: FSMContext):
    await state.set_state(IncomeState.waiting_for_amount)
    await callback.message.edit_text("Введите сумму полученного дохода:")

@dp.message(IncomeState.waiting_for_amount)
async def process_income_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        db.add_income(amount)
        await message.answer(f"✅ Доход <b>{amount:,.0f} ₽</b> записан!", reply_markup=get_main_menu(), parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число.")

# --- РЕЗЕРВЫ (Вручную) ---
@dp.callback_query(F.data.startswith("reserve_"))
async def process_reserve_btn(callback: CallbackQuery, state: FSMContext):
    target = callback.data.split("_")[1]
    await state.update_data(reserve_target=target)
    await state.set_state(ReserveState.waiting_for_amount)
    await callback.message.edit_text(f"Введите сумму для заморозки на <b>{target.title()}</b>:", parse_mode="HTML")

@dp.message(ReserveState.waiting_for_amount)
async def process_reserve_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        data = await state.get_data()
        db.add_reserve(amount, data['reserve_target'])
        await message.answer(f"🧊 <b>{amount:,.0f} ₽</b> заморожено на '{data['reserve_target'].title()}'.", reply_markup=get_main_menu(), parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("Пожалуйста, введите число.")

@dp.callback_query(F.data.startswith("pay_"))
async def process_pay_reserve(callback: CallbackQuery):
    target = callback.data.split("_")[1]
    db.execute_reserve(target)
    await callback.message.edit_text(f"✅ Платеж '{target.title()}' успешно проведен из замороженных средств!", reply_markup=get_main_menu())

# --- ИСТОРИЯ И ОТМЕНА ---
@dp.callback_query(F.data == "history_menu")
async def show_history(callback: CallbackQuery):
    transactions = db.get_recent_transactions(5)
    text = "📜 <b>Последние операции:</b>\n\n"
    if not transactions:
        text += "<i>Пока нет ни одной записи.</i>"
    else:
        for t_type, cat, amt, date_time in transactions:
            sign = "➕" if t_type == "income" else "📉"
            text += f"{sign} <b>{amt:,.0f} ₽</b> | {cat} <dim>({date_time[5:16]})\n</dim>"
            
    await callback.message.edit_text(text, reply_markup=get_history_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "cancel_last")
async def cancel_last_transaction(callback: CallbackQuery):
    last = db.delete_last_transaction()
    if last:
        t_type, cat, amt = last[1], last[2], last[3]
        text = f"❌ <b>Операция отменена и удалена:</b>\n{cat} — {amt:,.0f} ₽"
    else:
        text = "⚠️ История пуста, нечего отменять."
    await callback.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="HTML")

# --- МЕСЯЧНЫЙ ОТЧЕТ (АНАЛИТИКА) ---
@dp.callback_query(F.data == "monthly_report")
async def show_monthly_report(callback: CallbackQuery):
    expenses = db.get_expenses_by_category()
    total_expense = db.get_total_expenses()
    
    text = "📈 <b>Аналитика расходов по категориям:</b>\n\n"
    if not expenses or total_expense == 0:
        text += "<i>Расходов пока не зафиксировано.</i>"
    else:
        for cat, amt in expenses:
            percent = (amt / total_expense) * 100
            text += f"• <b>{cat}</b>: {amt:,.0f} ₽ <i>({percent:.1f}%)</i>\n"
        text += f"\n📉 <b>Всего потрачено:</b> {total_expense:,.0f} ₽"
        
    await callback.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="HTML")

# --- СВОДКА И ЛИМИТ ---
@dp.callback_query(F.data == "summary")
async def process_summary(callback: CallbackQuery):
    total_income = db.get_total_income()
    total_expense = db.get_total_expenses()
    total_reserve = db.get_total_reserve()
    
    actual_balance = total_income - total_expense
    free_balance = actual_balance - total_reserve
    
    days_left = days_until_next_payment()
    daily_limit = free_balance / days_left if free_balance > 0 else 0

    summary_text = (
        "📊 <b>Финансовая сводка:</b>\n\n"
        f"💳 Всего на счетах: <b>{actual_balance:,.0f} ₽</b>\n"
        f"🧊 Заморожено: <b>{total_reserve:,.0f} ₽</b>\n"
        f"✅ Свободно для трат: <b>{free_balance:,.0f} ₽</b>\n\n"
        f"📉 Потрачено на жизнь: <b>{total_expense:,.0f} ₽</b>\n"
        f"⏳ Дней до пополнения: <b>{days_left}</b>\n"
        f"🎯 <b>Дневной лимит: {daily_limit:,.0f} ₽ / день</b>"
    )
    
    await callback.message.edit_text(summary_text, reply_markup=get_main_menu(), parse_mode="HTML")

async def main():
    print("Бот успешно запущен и работает...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

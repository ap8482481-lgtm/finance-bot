import asyncio
import os
import io
import matplotlib.pyplot as plt
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
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

PAYMENT_DATES = [10, 25]

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db.init_db()

EXPENSE_CATEGORIES = {
    "cat_food": "🥗 Продукты питания",
    "cat_house": "🛒 Бытовые нужды",
    "cat_auto": "🚗 Автомобиль",
    "cat_gas": "⛽ Бензин",
    "cat_health": "💊 Гигиена и здоровье",
    "cat_kids": "🧸 Дети",
    "cat_clothes": "👕 Одежда и косметика",
    "cat_communal": "🏠 КУ и ЖКХ",
    "cat_transport": "🚌 Общественный транспорт",
    "cat_comms": "📱 Связь",
    "cat_cafe": "☕ Кафе и рестораны",
    "cat_fun": "🎉 Развлечения и подарки",
    "cat_habits": "🚬 Вредные привычки",
    "cat_invest": "📈 Инвестиции",
    "cat_deposit": "🐖 Вклад"
}

INCOME_CATEGORIES = {
    "inc_salary": "💼 Зарплата",
    "inc_advance": "💵 Аванс",
    "inc_cashback": "💳 Кэшбэк",
    "inc_gift": "🎁 Подарки",
    "inc_percent": "📈 Проценты",
    "inc_other": "💰 Прочие доходы"
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

def generate_progress_bar(percent):
    percent = max(0, min(100, percent))
    filled = int(percent / 10)
    return "🟩" * filled + "⬜️" * (10 - filled)

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="📊 Сводка", callback_data="summary")
    builder.button(text="💳 Расход", callback_data="show_expenses")
    builder.button(text="💰 Доход", callback_data="add_income")
    builder.button(text="🧊 Резервы", callback_data="manage_reserves")
    builder.button(text="📜 История", callback_data="history_menu")
    builder.button(text="📈 Отчет", callback_data="monthly_report")
    builder.adjust(2, 2, 2)
    return builder.as_markup()

def get_expenses_menu():
    builder = InlineKeyboardBuilder()
    for code, name in EXPENSE_CATEGORIES.items():
        builder.button(text=name, callback_data=code)
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(2, 2, 2, 2, 2, 2, 2, 1, 1)
    return builder.as_markup()

def get_incomes_menu():
    builder = InlineKeyboardBuilder()
    for code, name in INCOME_CATEGORIES.items():
        builder.button(text=name, callback_data=code)
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

def get_reserves_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏦 Ипотека", callback_data="reserve_ипотека")
    builder.button(text="💳 Кредитки", callback_data="reserve_кредитки")
    builder.button(text="🎒 Школа", callback_data="reserve_школа")
    builder.button(text="🌐 Интернет", callback_data="reserve_интернет")
    builder.button(text="📱 Связь", callback_data="reserve_связь")
    builder.button(text="📋 Активные", callback_data="view_reserves")
    builder.button(text="✅ Оплатить", callback_data="pay_menu")
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(2, 2, 1, 2, 1)
    return builder.as_markup()

def get_pay_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏦 Ипотеку", callback_data="pay_ипотека")
    builder.button(text="💳 Кредитки", callback_data="pay_кредитки")
    builder.button(text="🎒 Школу", callback_data="pay_школа")
    builder.button(text="🌐 Интернет", callback_data="pay_интернет")
    builder.button(text="📱 Связь", callback_data="pay_связь")
    builder.button(text="◀️ Назад", callback_data="manage_reserves")
    builder.adjust(2, 2, 1, 1)
    return builder.as_markup()

def get_history_menu():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отменить", callback_data="cancel_last")
    builder.button(text="◀️ Назад", callback_data="back_to_main")
    builder.adjust(1, 1)
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    if not is_owner(message.from_user.id):
        return
    text = (
        "<blockquote>💎 <b>Персональный Фин-Центр</b>\n\n"
        "Система учета и контроля бюджета активирована. "
        "Выберите нужное действие в меню ниже.</blockquote>"
    )
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "back_to_main")
async def go_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    if callback.message.photo:
        await callback.message.delete()
        await callback.message.answer("<blockquote>✨ <b>Главное меню</b></blockquote>", reply_markup=get_main_menu(), parse_mode="HTML")
    else:
        await callback.message.edit_text("<blockquote>✨ <b>Главное меню</b></blockquote>", reply_markup=get_main_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "show_expenses")
async def show_expenses(callback: CallbackQuery):
    await callback.message.edit_text("<blockquote>💳 <b>Категория расхода:</b></blockquote>", reply_markup=get_expenses_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "manage_reserves")
async def show_reserves(callback: CallbackQuery):
    await callback.message.edit_text("<blockquote>🧊 <b>Управление резервами:</b></blockquote>", reply_markup=get_reserves_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "pay_menu")
async def show_pay_menu(callback: CallbackQuery):
    await callback.message.edit_text("<blockquote>✅ <b>Оплата из резерва:</b></blockquote>", reply_markup=get_pay_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "view_reserves")
async def view_active_reserves(callback: CallbackQuery):
    reserves = db.get_all_reserves_with_id()
    total = db.get_total_reserve()
    
    text = "<blockquote>📋 <b>Активные резервы:</b>\n\n"
    builder = InlineKeyboardBuilder()
    
    if not reserves:
        text += "<i>Пусто.</i>"
    else:
        for r_id, target, amount in reserves:
            text += f"• <b>{target.title()}</b>: <code>{amount:,.0f} ₽</code>\n"
            builder.button(text=f"🗑 {target.title()} ({amount:,.0f}₽)", callback_data=f"del_res_{r_id}")
        text += f"\n🧊 <b>Всего заморожено:</b> <code>{total:,.0f} ₽</code>"
        
    text += "</blockquote>"
    builder.button(text="◀️ Назад", callback_data="manage_reserves")
    builder.adjust(1)
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("del_res_"))
async def delete_reserve_callback(callback: CallbackQuery):
    r_id = int(callback.data.split("_")[2])
    db.delete_reserve_by_id(r_id)
    await callback.answer("🗑 Резерв удален!", show_alert=False)
    await view_active_reserves(callback)

@dp.callback_query(F.data.startswith("cat_"))
async def process_cat_btn(callback: CallbackQuery, state: FSMContext):
    category_name = EXPENSE_CATEGORIES[callback.data]
    await state.update_data(category=category_name)
    await state.set_state(ExpenseState.waiting_for_amount)
    await callback.message.edit_text(f"<blockquote>✍️ <b>{category_name}</b>\n\nВведите сумму (можно добавить комментарий):</blockquote>", parse_mode="HTML")

@dp.message(ExpenseState.waiting_for_amount)
async def process_expense_amount(message: Message, state: FSMContext):
    try:
        parts = message.text.split(maxsplit=1)
        amount = float(parts[0].replace(",", "."))
        note = parts[1] if len(parts) > 1 else ""
        data = await state.get_data()
        db.add_transaction("expense", data['category'], amount, note)
        
        note_display = f"\n📝 <i>{note}</i>" if note else ""
        success_text = (
            f"<blockquote>✅ <b>Расход учтен</b>\n\n"
            f"📂 {data['category']}\n"
            f"📉 <b>{amount:,.0f} ₽</b>{note_display}</blockquote>"
        )
        await message.answer(success_text, reply_markup=get_main_menu(), parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Начните сообщение с числа.")

@dp.callback_query(F.data == "add_income")
async def show_incomes(callback: CallbackQuery):
    await callback.message.edit_text("<blockquote>💰 <b>Категория дохода:</b></blockquote>", reply_markup=get_incomes_menu(), parse_mode="HTML")

@dp.callback_query(F.data.startswith("inc_"))
async def process_inc_btn(callback: CallbackQuery, state: FSMContext):
    category_name = INCOME_CATEGORIES[callback.data]
    await state.update_data(category=category_name)
    await state.set_state(IncomeState.waiting_for_amount)
    await callback.message.edit_text(f"<blockquote>✍️ <b>{category_name}</b>\n\nВведите сумму:</blockquote>", parse_mode="HTML")

@dp.message(IncomeState.waiting_for_amount)
async def process_income_amount(message: Message, state: FSMContext):
    try:
        parts = message.text.split(maxsplit=1)
        amount = float(parts[0].replace(",", "."))
        note = parts[1] if len(parts) > 1 else ""
        data = await state.get_data()
        db.add_transaction("income", data['category'], amount, note)
        
        note_display = f"\n📝 <i>{note}</i>" if note else ""
        success_text = (
            f"<blockquote>🎉 <b>Доход зачислен</b>\n\n"
            f"📂 {data['category']}\n"
            f"➕ <b>{amount:,.0f} ₽</b>{note_display}</blockquote>"
        )
        await message.answer(success_text, reply_markup=get_main_menu(), parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Начните сообщение с числа.")

@dp.callback_query(F.data.startswith("reserve_"))
async def process_reserve_btn(callback: CallbackQuery, state: FSMContext):
    target = callback.data.split("_")[1]
    await state.update_data(reserve_target=target)
    await state.set_state(ReserveState.waiting_for_amount)
    await callback.message.edit_text(f"<blockquote>🧊 <b>Резерв: {target.title()}</b>\n\nВведите сумму:</blockquote>", parse_mode="HTML")

@dp.message(ReserveState.waiting_for_amount)
async def process_reserve_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        data = await state.get_data()
        db.add_reserve(amount, data['reserve_target'])
        
        success_text = (
            f"<blockquote>🧊 <b>Заморожено</b>\n\n"
            f"📌 {data['reserve_target'].title()}\n"
            f"💎 <b>{amount:,.0f} ₽</b></blockquote>"
        )
        await message.answer(success_text, reply_markup=get_main_menu(), parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Пожалуйста, введите число.")

@dp.callback_query(F.data.startswith("pay_"))
async def process_pay_reserve(callback: CallbackQuery):
    target = callback.data.split("_")[1]
    amount = db.execute_reserve(target)
    
    if amount:
        success_text = (
            f"<blockquote>✅ <b>Платеж проведен</b>\n\n"
            f"🎯 {target.title()}\n"
            f"💸 Списано: <b>{amount:,.0f} ₽</b></blockquote>"
        )
    else:
        success_text = f"<blockquote>⚠️ Резерв <b>{target.title()}</b> пуст.</blockquote>"
        
    await callback.message.edit_text(success_text, reply_markup=get_main_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "history_menu")
async def show_history(callback: CallbackQuery):
    transactions = db.get_recent_transactions(5)
    text = "<blockquote>📜 <b>Последние операции:</b>\n\n"
    if not transactions:
        text += "<i>Пусто.</i>"
    else:
        for t_type, cat, amt, date_time, note in transactions:
            sign = "➕" if t_type == "income" else "📉"
            note_str = f" <i>({note})</i>" if note else ""
            text += f"{sign} <b>{amt:,.0f} ₽</b> | {cat}{note_str} \n<code style='color: gray;'>{date_time[5:16]}</code>\n\n"
    text += "</blockquote>"
    await callback.message.edit_text(text, reply_markup=get_history_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "cancel_last")
async def cancel_last_transaction(callback: CallbackQuery):
    last = db.delete_last_transaction()
    if last:
        _, cat, amt = last[1], last[2], last[3]
        text = f"<blockquote>❌ <b>Отменено:</b>\n{cat} — <b>{amt:,.0f} ₽</b></blockquote>"
    else:
        text = "<blockquote>⚠️ История пуста.</blockquote>"
    await callback.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "monthly_report")
async def show_monthly_report(callback: CallbackQuery):
    expenses = db.get_expenses_by_category()
    total_expense = db.get_total_expenses()
    
    if not expenses or total_expense == 0:
        await callback.message.edit_text("<blockquote>📈 <i>Расходов пока нет.</i></blockquote>", reply_markup=get_main_menu(), parse_mode="HTML")
        return

    # Генерация круговой диаграммы
    labels = [cat for cat, _ in expenses]
    sizes = [amt for _, amt in expenses]
    
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(6, 6))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)
    
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%', 
        startangle=140, textprops={'color': "w", 'fontsize': 10},
        colors=plt.cm.Set3.colors
    )
    plt.title("Структура расходов", color="w", fontsize=14, weight='bold')
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    buf.seek(0)
    plt.close(fig)
    
    photo = BufferedInputFile(buf.read(), filename="chart.png")
    
    text = "<blockquote>📈 <b>Детализация расходов:</b>\n\n"
    for cat, amt in expenses:
        percent = (amt / total_expense) * 100
        text += f"• <b>{cat}</b>: <code>{amt:,.0f} ₽</code>\n"
    text += f"\n📉 <b>Всего:</b> <code>{total_expense:,.0f} ₽</code></blockquote>"

    await callback.message.delete()
    await callback.message.answer_photo(photo=photo, caption=text, reply_markup=get_main_menu(), parse_mode="HTML")

@dp.callback_query(F.data == "summary")
async def process_summary(callback: CallbackQuery):
    total_income = db.get_total_income()
    total_expense = db.get_total_expenses()
    total_reserve = db.get_total_reserve()
    
    actual_balance = total_income - total_expense
    free_balance = actual_balance - total_reserve
    days_left = days_until_next_payment()
    daily_limit = free_balance / days_left if free_balance > 0 else 0
    
    budget_percent = (free_balance / total_income * 100) if total_income > 0 else 0
    progress_bar = generate_progress_bar(budget_percent)

    summary_text = (
        "<blockquote>📊 <b>Финансовая сводка</b>\n\n"
        f"💳 Всего на счетах: <b>{actual_balance:,.0f} ₽</b>\n"
        f"🧊 Заморожено: <b>{total_reserve:,.0f} ₽</b>\n"
        f"✅ Свободно: <b>{free_balance:,.0f} ₽</b>\n\n"
        f"📉 Потрачено: <b>{total_expense:,.0f} ₽</b>\n"
        f"⏳ До пополнения: <b>{days_left} дн.</b>\n\n"
        f"🎯 <b>Лимит: {daily_limit:,.0f} ₽ / день</b>\n\n"
        f"Остаток бюджета:\n<code>{progress_bar}</code> {budget_percent:.0f}%</blockquote>"
    )
    
    await callback.message.edit_text(summary_text, reply_markup=get_main_menu(), parse_mode="HTML")

async def main():
    print("Бот успешно запущен и работает...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

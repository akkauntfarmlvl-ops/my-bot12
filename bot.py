import os
import sqlite3
import secrets
import logging
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ============ НАСТРОЙКИ ============
BOT_TOKEN = "8423435789:AAE3ZPgJMeq7cFUvMr3uhYHEjf-rUqsxzVo"
CHANNEL_CHAT_ID = "-1003586788303"
CHANNEL_LINK = "https://t.me/+SjVzcCRHyLExZDMy"
ADMIN_IDS = [6734219400]
PASSWORD = "NMJKL"
# ====================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

FILES_DIR = "bot_files"
os.makedirs(FILES_DIR, exist_ok=True)


def init_db():
    conn = sqlite3.connect("bot_data.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS files
           (code TEXT PRIMARY KEY, file_path TEXT, file_name TEXT, description TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS users
           (user_id INTEGER PRIMARY KEY, is_subscribed INTEGER DEFAULT 0)""")
    c.execute("""CREATE TABLE IF NOT EXISTS user_files
           (user_id INTEGER, file_code TEXT, file_name TEXT, received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, file_code))""")
    # Таблица покупок
    c.execute("""CREATE TABLE IF NOT EXISTS purchases
           (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, product TEXT, 
            amount INTEGER, status TEXT, screenshot_file_id TEXT, admin_msg_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()
    conn.close()


def get_db():
    return sqlite3.connect("bot_data.db")


async def is_subscribed(user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_CHAT_ID, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return False


def subscribe_keyboard(file_code: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url=CHANNEL_LINK)],
        [InlineKeyboardButton(text="✅ Я подписался, дать файл", callback_data=f"check:{file_code}")]
    ])


def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛒 Купить КФГ", callback_data="buy_cfg"),
            InlineKeyboardButton(text="📂 Мои файлы", callback_data="my_files")
        ]
    ])


def cfg_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📡 Wi-Fi / 5G", callback_data="cfg_wifi"),
            InlineKeyboardButton(text="📶 Мобильный (4G/3G)", callback_data="cfg_mobile")
        ],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")]
    ])


class AdminState(StatesGroup):
    enter_password = State()
    admin_menu = State()
    waiting_file = State()
    waiting_description = State()
    waiting_screenshot = State()
    sending_purchase_file = State()


@dp.message(CommandStart())
async def cmd_start(message: Message):
    args = message.text.split() if message.text else []
    if len(args) > 1 and args[1].startswith("file_"):
        await handle_file_request(message, args[1])
        return
    
    await message.answer(
        "👋 Привет! Тут вы можете получить файл и купить КФГ!\n\n"
        "📎 Для получения файла используйте ссылку от администратора\n"
        "🛒 Или выберите действие ниже:\n\n"
        "📋 *Главное меню:*",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        "👋 Привет! Тут вы можете получить файл и купить КФГ!\n\n"
        "📎 Для получения файла используйте ссылку от администратора\n"
        "🛒 Или выберите действие ниже:\n\n"
        "📋 *Главное меню:*",
        reply_markup=main_menu_keyboard(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "buy_cfg")
async def buy_cfg(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛒 *Покупка КФГ*\n\n"
        "📋 Выберите конфигурацию:\n\n"
        "📡 *Wi-Fi / 5G* — Пока что нету информации\n"
        "📶 *Мобильный (4G/3G)* — Пока что нету информации\n\n"
        "👇 Нажмите на нужную кнопку:",
        reply_markup=cfg_menu_keyboard(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "cfg_wifi")
async def cfg_wifi(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ Стоп + флеш 5 сек", callback_data="wifi_stopflash")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_cfg")]
    ])
    await callback.message.edit_text(
        "📡 *КФГ на Wi-Fi / 5G*\n\n"
        "*Примерный прайс*\n\n"
        "💰 80 грн\n"
        "⭐ 80 звёзд\n\n"
        "👇 Выберите кфг:",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "wifi_stopflash")
async def wifi_stopflash(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💳 Купить 80 грн", callback_data="pay_uah_80"),
            InlineKeyboardButton(text="⭐ Купить 80 звёзд", callback_data="pay_stars_80")
        ],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_wifi")]
    ])
    await callback.message.edit_text(
        "⏹ *Стоп + Флеш 5 сек*\n\n"
        "💰 *Стоимость:* 80 грн / 80 звёзд\n\n"
        "⚙️ *Функция:* Стопер + флеш\n"
        "⏱ *Время:* 5 сек\n"
        "🎯 *Рег:* 99% (при отдалении 95%)\n"
        "⚠️ *Риск бана:* 70% (зависит от вашей игры)\n"
        "📡 *Сети:* Wi-Fi\n\n"
        "💳 Выберите способ оплаты:",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "pay_uah_80")
async def pay_uah_80(callback: CallbackQuery, state: FSMContext):
    """Запрос скриншота оплаты"""
    user_id = callback.from_user.id
    
    # Создаём покупку в БД
    conn = get_db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO purchases (user_id, product, amount, status) VALUES (?, ?, ?, ?)",
        (user_id, "stop_flash_5sec", 80, "waiting_screenshot")
    )
    purchase_id = c.lastrowid
    conn.commit()
    conn.close()
    
    await state.update_data(purchase_id=purchase_id)
    await state.set_state(AdminState.waiting_screenshot)
    
    # Редактируем текущее сообщение вместо удаления
    await callback.message.edit_text(
        "💳 *Оплата 80 грн*\n\n"
        "Переведите 80 грн на карту:\n"
        "`0000 0000 0000 0000`\n\n"
        "❗️ В комментарии укажите: `КФГ`\n\n"
        "📸 После оплаты отправьте скриншот платежа сюда:",
        parse_mode="Markdown",
        reply_markup=None
    )


@dp.message(AdminState.waiting_screenshot, F.photo)
async def receive_screenshot(message: Message, state: FSMContext):
    """Получение скриншота от пользователя"""
    data = await state.get_data()
    purchase_id = data.get("purchase_id")
    user_id = message.from_user.id
    
    photo = message.photo[-1]
    screenshot_file_id = photo.file_id
    
    conn = get_db()
    conn.execute(
        "UPDATE purchases SET screenshot_file_id = ?, status = ? WHERE id = ?",
        (screenshot_file_id, "pending", purchase_id)
    )
    conn.commit()
    conn.close()
    
    # Удаляем сообщение со скриншотом и отправляем новое
    await message.delete()
    await message.answer(
        "✅ Скриншот получен!\n\n"
        "⏳ Ожидайте проверки администратором...\n"
        "Обычно это занимает до 30 минут.",
        reply_markup=main_menu_keyboard()
    )
    await state.clear()


@dp.callback_query(F.data.startswith("approve:"))
async def approve_purchase(callback: CallbackQuery, state: FSMContext):
    """Админ принял покупку — просим отправить файл"""
    purchase_id = int(callback.data.split(":")[1])
    
    conn = get_db()
    purchase = conn.execute(
        "SELECT user_id, product FROM purchases WHERE id = ?", (purchase_id,)
    ).fetchone()
    conn.close()
    
    if not purchase:
        await callback.answer("❌ Покупка не найдена!", show_alert=True)
        return
    
    user_id, product = purchase
    
    conn = get_db()
    conn.execute("UPDATE purchases SET status = ? WHERE id = ?", ("approved", purchase_id))
    conn.commit()
    conn.close()
    
    # Уведомляем пользователя
    await bot.send_message(
        chat_id=user_id,
        text=(
            "✅ *Ваша покупка принята!*\n\n"
            "⏹ Стоп + Флеш 5 сек\n\n"
            "⏳ Ожидайте файл в течение *2 часов*.\n"
            "Мы отправим его сюда как только будет готов."
        ),
        parse_mode="Markdown"
    )
    
    # Редактируем сообщение со скриншотом — просим файл
    await callback.message.edit_caption(
        caption=(
            f"✅ Покупка #{purchase_id} принята!\n\n"
            f"👤 Пользователь: `{user_id}`\n"
            f"📦 Товар: {product}\n\n"
            f"📤 *Отправьте файл для этого пользователя:*"
        ),
        reply_markup=None,
        parse_mode="Markdown"
    )
    
    await state.set_state(AdminState.sending_purchase_file)
    await state.update_data(purchase_id=purchase_id, user_id=user_id)
    
    await callback.answer("✅ Покупка принята! Теперь отправьте файл.")


@dp.callback_query(F.data.startswith("reject:"))
async def reject_purchase(callback: CallbackQuery):
    """Админ отклонил покупку"""
    purchase_id = int(callback.data.split(":")[1])
    
    conn = get_db()
    purchase = conn.execute(
        "SELECT user_id FROM purchases WHERE id = ?", (purchase_id,)
    ).fetchone()
    
    if purchase:
        user_id = purchase[0]
        conn.execute("UPDATE purchases SET status = ? WHERE id = ?", ("rejected", purchase_id))
        conn.commit()
        
        await bot.send_message(
            chat_id=user_id,
            text=(
                "❌ *Покупка отклонена*\n\n"
                "Возможные причины:\n"
                "• Скриншот не читается\n"
                "• Оплата не найдена\n"
                "• Неверная сумма\n\n"
                "Попробуйте ещё раз или свяжитесь с администратором."
            ),
            parse_mode="Markdown"
        )
    conn.close()
    
    await callback.message.edit_caption(
        caption="❌ Покупка отклонена.",
        reply_markup=None
    )
    await callback.answer("❌ Отклонено")


@dp.message(AdminState.sending_purchase_file, F.document)
async def send_purchase_file(message: Message, state: FSMContext):
    """Админ отправляет файл покупателю"""
    data = await state.get_data()
    user_id = data.get("user_id")
    purchase_id = data.get("purchase_id")
    
    file_id = message.document.file_id
    file_name = message.document.file_name or "КФГ.cfg"
    
    # Отправляем покупателю
    await bot.send_document(
        chat_id=user_id,
        document=file_id,
        caption=(
            f"📦 *Ваш товар готов!*\n\n"
            f"⏹ Стоп + Флеш 5 сек\n"
            f"📄 {file_name}\n\n"
            f"Спасибо за покупку! 🎉"
        ),
        parse_mode="Markdown"
    )
    
    conn = get_db()
    conn.execute("UPDATE purchases SET status = ? WHERE id = ?", ("completed", purchase_id))
    conn.commit()
    conn.close()
    
    # Удаляем сообщение с файлом админа и отправляем подтверждение
    await message.delete()
    await message.answer(
        f"✅ Файл отправлен покупателю `{user_id}`!\n\n"
        f"Покупка #{purchase_id} завершена.",
        parse_mode="Markdown"
    )
    await state.clear()


@dp.callback_query(F.data == "pay_stars_80")
async def pay_stars_80(callback: CallbackQuery):
    await callback.answer("⭐ Оплата звёздами временно недоступна", show_alert=True)


@dp.callback_query(F.data == "back_to_wifi")
async def back_to_wifi(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ Стоп + флеш 5 сек", callback_data="wifi_stopflash")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_cfg")]
    ])
    await callback.message.edit_text(
        "📡 *КФГ на Wi-Fi / 5G*\n\n"
        "*Примерный прайс*\n\n"
        "💰 80 грн\n"
        "⭐ 80 звёзд\n\n"
        "👇 Выберите кфг:",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "back_to_cfg")
async def back_to_cfg(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛒 *Покупка КФГ*\n\n"
        "📋 Выберите конфигурацию:\n\n"
        "📡 *Wi-Fi / 5G* — Пока что нету информации\n"
        "📶 *Мобильный (4G/3G)* — Пока что нету информации\n\n"
        "👇 Нажмите на нужную кнопку:",
        reply_markup=cfg_menu_keyboard(),
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "cfg_mobile")
async def cfg_mobile(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔔 Уведомить когда появится", callback_data="notify_mobile")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_cfg")]
    ])
    await callback.message.edit_text(
        "📶 *КФГ на мобильный интернет (4G/3G)*\n\n"
        "❌ *Пока что нету информации*\n\n"
        "🔔 Нажмите кнопку ниже, чтобы получить уведомление:",
        reply_markup=kb,
        parse_mode="Markdown"
    )


@dp.callback_query(F.data == "notify_mobile")
async def notify_mobile(callback: CallbackQuery):
    await callback.answer("✅ Вы подписаны на уведомления!", show_alert=True)


@dp.callback_query(F.data == "my_files")
async def my_files(callback: CallbackQuery):
    user_id = callback.from_user.id
    conn = get_db()
    files = conn.execute(
        "SELECT file_code, file_name, received_at FROM user_files WHERE user_id=? ORDER BY received_at DESC",
        (user_id,)
    ).fetchall()
    conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_main")]
    ])
    
    if not files:
        await callback.message.edit_text(
            "📂 У вас пока нет полученных файлов.\n\n"
            "Получите файл по ссылке от администратора!",
            reply_markup=kb
        )
        return
    
    text = "📂 *Ваши файлы:*\n\n"
    for i, (code, name, date) in enumerate(files, 1):
        text += f"{i}. 📄 *{name}*\n   Получен: {date}\n\n"
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)


async def handle_file_request(message: Message, deep_args: str):
    user_id = message.from_user.id
    if not deep_args.startswith("file_"):
        await message.answer("❌ Неверная ссылка.")
        return
    file_code = deep_args.replace("file_", "", 1)
    conn = get_db()
    file_data = conn.execute(
        "SELECT code, file_path, file_name, description FROM files WHERE code=?",
        (file_code,)
    ).fetchone()
    conn.close()
    if not file_data:
        await message.answer("❌ Файл не найден или удалён.")
        return
    subscribed = await is_subscribed(user_id)
    if subscribed:
        conn = get_db()
        conn.execute(
            "INSERT OR IGNORE INTO user_files (user_id, file_code, file_name) VALUES (?, ?, ?)",
            (user_id, file_code, file_data[2])
        )
        conn.execute(
            "INSERT OR REPLACE INTO users (user_id, is_subscribed) VALUES (?, 1)",
            (user_id,)
        )
        conn.commit()
        conn.close()
        desc_text = f"\n\n📝 *Описание:* {file_data[3]}" if file_data[3] else ""
        await message.answer(
            f"✅ Вы подписаны! Вот ваш файл:\n\n"
            f"📄 *{file_data[2]}*{desc_text}",
            parse_mode="Markdown"
        )
        await bot.send_document(user_id, file_data[1], caption=f"📄 {file_data[2]}")
        await message.answer(
            "📋 *Главное меню:*",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        kb = subscribe_keyboard(file_code)
        desc_text = f"\n\n📝 {file_data[3]}" if file_data[3] else ""
        await message.answer(
            f"📢 *Для получения файла подпишитесь на канал!*{desc_text}\n\n"
            f"📄 *Файл:* {file_data[2]}\n\n"
            "1️⃣ Подпишитесь на канал по кнопке ниже\n"
            "2️⃣ Вернитесь и нажмите «Я подписался»",
            reply_markup=kb,
            parse_mode="Markdown"
        )


@dp.callback_query(F.data.startswith("check:"))
async def check_sub(callback: CallbackQuery):
    user_id = callback.from_user.id
    file_code = callback.data.split(":", 1)[1]
    if await is_subscribed(user_id):
        conn = get_db()
        file_data = conn.execute(
            "SELECT file_path, file_name, description FROM files WHERE code=?",
            (file_code,)
        ).fetchone()
        if file_data:
            conn.execute(
                "INSERT OR IGNORE INTO user_files (user_id, file_code, file_name) VALUES (?, ?, ?)",
                (user_id, file_code, file_data[1])
            )
            conn.execute(
                "INSERT OR REPLACE INTO users (user_id, is_subscribed) VALUES (?, 1)",
                (user_id,)
            )
            conn.commit()
            desc_text = f"\n\n📝 *Описание:* {file_data[2]}" if file_data[2] else ""
            await callback.message.edit_text(
                f"✅ Отлично! Вот ваш файл: 📄 {file_data[1]}{desc_text}"
            )
            await bot.send_document(user_id, file_data[0], caption=f"📄 {file_data[1]}")
            await callback.answer("✅ Файл отправлен!")
            await callback.message.answer(
                "📋 *Главное меню:*",
                reply_markup=main_menu_keyboard(),
                parse_mode="Markdown"
            )
        else:
            await callback.answer("❌ Файл не найден!", show_alert=True)
        conn.close()
    else:
        await callback.message.edit_text(
            "❌ *Вы ещё не подписались!*\n\n"
            "Подпишитесь и нажмите кнопку снова.",
            reply_markup=subscribe_keyboard(file_code),
            parse_mode="Markdown"
        )
        await callback.answer("❌ Подпишитесь на канал!", show_alert=True)


# ═══════════════════════════════════════════════
#  АДМИН-ПАНЕЛЬ
# ═══════════════════════════════════════════════
@dp.message(Command("123"))
async def cmd_secret(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_admin")]
    ])
    await message.answer("🔐 Введите пароль администратора:", reply_markup=kb)
    await state.set_state(AdminState.enter_password)


@dp.message(AdminState.enter_password)
async def process_password(message: Message, state: FSMContext):
    if message.text.strip() == PASSWORD:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📎 Добавить файл", callback_data="admin_add")],
            [InlineKeyboardButton(text="📋 Мои файлы", callback_data="admin_list")],
            [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
            [InlineKeyboardButton(text="🗑 Удалить файл", callback_data="admin_delete")],
            [InlineKeyboardButton(text="🛒 Проверить покупки", callback_data="admin_purchases")],
        ])
        await message.answer(
            "✅ Добро пожаловать в панель администратора!\n\n"
            "📎 *Добавить файл* — загрузите файл и получите ссылку\n"
            "📋 *Мои файлы* — список всех загруженных файлов\n"
            "👥 *Пользователи* — статистика подписчиков\n"
            "🗑 *Удалить файл* — удалить файл и ссылку\n"
            "🛒 *Проверить покупки* — ожидающие скриншоты",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        await state.set_state(AdminState.admin_menu)
    else:
        await message.answer("❌ Неверный пароль!")


@dp.callback_query(F.data == "admin_add", AdminState.admin_menu)
async def admin_add(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        "📎 *Добавление файла*\n\n"
        "Отправьте мне файл (документ, фото, видео).\n"
        "Затем я попрошу вас добавить описание.",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await state.set_state(AdminState.waiting_file)


@dp.callback_query(F.data == "admin_list", AdminState.admin_menu)
async def admin_list(callback: CallbackQuery):
    conn = get_db()
    files = conn.execute("SELECT code, file_name, description FROM files").fetchall()
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    ])
    if not files:
        await callback.message.edit_text("📋 Список файлов пуст.", reply_markup=kb)
        return
    text = "📋 *Ваши файлы:*\n\n"
    bot_info = await bot.get_me()
    bot_un = bot_info.username
    for code, name, desc in files:
        link = f"https://t.me/{bot_un}?start=file_{code}"
        desc_text = f"\n📝 {desc}" if desc else ""
        text += f"📄 *{name}*{desc_text}\n🔗 `{link}`\n\n"
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)


@dp.callback_query(F.data == "admin_users", AdminState.admin_menu)
async def admin_users(callback: CallbackQuery):
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    subs = conn.execute("SELECT COUNT(*) FROM users WHERE is_subscribed=1").fetchone()[0]
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    ])
    await callback.message.edit_text(
        f"👥 *Статистика:*\n\nВсего пользователей: {total}\nПодписанных: {subs}",
        parse_mode="Markdown",
        reply_markup=kb
    )


@dp.callback_query(F.data == "admin_delete", AdminState.admin_menu)
async def admin_delete(callback: CallbackQuery):
    conn = get_db()
    files = conn.execute("SELECT code, file_name FROM files").fetchall()
    conn.close()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    ])
    if not files:
        await callback.message.edit_text("📋 Список файлов пуст.", reply_markup=kb)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🗑 {name}", callback_data=f"del:{code}")]
        for code, name in files
    ])
    kb.inline_keyboard.append(
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    )
    await callback.message.edit_text("🗑 Выберите файл для удаления:", reply_markup=kb)


# ═══════════════════════════════════════════════
#  ПРОВЕРКА ПОКУПОК — СКРИНШОТЫ ТОЛЬКО ЗДЕСЬ!
# ═══════════════════════════════════════════════
@dp.callback_query(F.data == "admin_purchases", AdminState.admin_menu)
async def admin_purchases(callback: CallbackQuery):
    """Показать все ожидающие покупки — скриншоты видны ТОЛЬКО здесь!"""
    conn = get_db()
    purchases = conn.execute(
        "SELECT id, user_id, product, amount, status, screenshot_file_id FROM purchases WHERE status IN (?, ?)",
        ("pending", "waiting_screenshot")
    ).fetchall()
    conn.close()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    ])
    
    if not purchases:
        await callback.message.edit_text(
            "🛒 *Ожидающие покупки:*\n\n"
            "Нет покупок на проверку.",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return
    
    # Редактируем текущее сообщение
    await callback.message.edit_text(
        f"🛒 *Ожидающие покупки:* {len(purchases)}\n\n"
        f"📸 Скриншоты отправлены ниже. Проверьте и примите решение:",
        parse_mode="Markdown",
        reply_markup=kb
    )
    
    # Отправляем скриншоты отдельными сообщениями с кнопками
    for pur in purchases:
        if pur[5]:  # screenshot_file_id
            kb_pur = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{pur[0]}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{pur[0]}")
                ]
            ])
            await callback.message.answer_photo(
                photo=pur[5],
                caption=(
                    f"🛒 *Покупка #{pur[0]}*\n"
                    f"👤 Пользователь: `{pur[1]}`\n"
                    f"📦 Товар: {pur[2]}\n"
                    f"💰 Сумма: {pur[3]} грн"
                ),
                reply_markup=kb_pur,
                parse_mode="Markdown"
            )


@dp.callback_query(F.data.startswith("del:"))
async def delete_file(callback: CallbackQuery):
    code = callback.data.split(":", 1)[1]
    conn = get_db()
    file_data = conn.execute("SELECT file_name FROM files WHERE code=?", (code,)).fetchone()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")]
    ])
    if file_data:
        conn.execute("DELETE FROM files WHERE code=?", (code,))
        conn.commit()
        local_path = os.path.join(FILES_DIR, f"{code}_{file_data[0]}")
        if os.path.exists(local_path):
            os.remove(local_path)
        conn.close()
        await callback.answer(f"✅ Файл {file_data[0]} удалён!")
        await callback.message.edit_text(
            f"✅ Файл *{file_data[0]}* удалён!",
            parse_mode="Markdown",
            reply_markup=kb
        )
    else:
        conn.close()
        await callback.answer("❌ Файл не найден!")
        await callback.message.edit_text("❌ Файл не найден!", reply_markup=kb)


@dp.callback_query(F.data == "cancel_admin")
async def cancel_admin(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Отменено.")


@dp.callback_query(F.data == "cancel_upload")
async def cancel_upload(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminState.admin_menu)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Добавить файл", callback_data="admin_add")],
        [InlineKeyboardButton(text="📋 Мои файлы", callback_data="admin_list")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🗑 Удалить файл", callback_data="admin_delete")],
        [InlineKeyboardButton(text="🛒 Проверить покупки", callback_data="admin_purchases")],
    ])
    await callback.message.edit_text("❌ Добавление файла отменено.", reply_markup=kb)


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📎 Добавить файл", callback_data="admin_add")],
        [InlineKeyboardButton(text="📋 Мои файлы", callback_data="admin_list")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🗑 Удалить файл", callback_data="admin_delete")],
        [InlineKeyboardButton(text="🛒 Проверить покупки", callback_data="admin_purchases")],
    ])
    await state.set_state(AdminState.admin_menu)
    await callback.message.edit_text("✅ Панель администратора!", reply_markup=kb)


@dp.message(AdminState.waiting_file, F.content_type.in_([
    "document", "photo", "video", "audio", "voice"
]))
async def handle_file_upload(message: Message, state: FSMContext):
    if message.document:
        file_info = message.document
    elif message.photo:
        file_info = message.photo[-1]
    elif message.video:
        file_info = message.video
    elif message.audio:
        file_info = message.audio
    else:
        file_info = message.voice
    
    file_id = file_info.file_id
    file_name = getattr(file_info, "file_name", f"file_{secrets.token_hex(4)}")
    unique_code = secrets.token_urlsafe(8)
    
    await state.update_data(
        file_id=file_id,
        file_name=file_name,
        file_code=unique_code
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏩ Пропустить описание", callback_data="skip_desc")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_upload")]
    ])
    await message.answer(
        "✅ Файл получен!\n\n"
        "📝 Теперь введите описание для файла (или нажмите «Пропустить»):",
        reply_markup=kb
    )
    await state.set_state(AdminState.waiting_description)


@dp.callback_query(F.data == "skip_desc", AdminState.waiting_description)
async def skip_description(callback: CallbackQuery, state: FSMContext):
    await save_file(callback.message, state, description=None)


@dp.message(AdminState.waiting_description)
async def process_description(message: Message, state: FSMContext):
    await save_file(message, state, description=message.text.strip())


async def save_file(msg, state, description):
    data = await state.get_data()
    file_id = data.get("file_id")
    file_name = data.get("file_name")
    unique_code = data.get("file_code")
    
    conn = get_db()
    conn.execute(
        "INSERT INTO files (code, file_path, file_name, description) VALUES (?, ?, ?, ?)",
        (unique_code, file_id, file_name, description)
    )
    conn.commit()
    conn.close()
    
    try:
        local_path = os.path.join(FILES_DIR, f"{unique_code}_{file_name}")
        await bot.download(file_id, destination=local_path)
    except Exception as e:
        logger.warning(f"Не удалось скачать файл: {e}")
    
    bot_info = await bot.get_me()
    bot_un = bot_info.username
    link = f"https://t.me/{bot_un}?start=file_{unique_code}"
    
    desc_text = f"\n📝 *Описание:* {description}" if description else ""
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Мои файлы", callback_data="admin_list")],
        [InlineKeyboardButton(text="📎 Ещё файл", callback_data="admin_add")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="back_to_menu")],
    ])
    
    text = (
        f"✅ Файл добавлен!\n\n"
        f"📄 *{file_name}*{desc_text}\n\n"
        f"🔗 Ссылка для поста:\n`{link}`\n\n"
        "Скопируйте ссылку и вставьте в пост на канале!"
    )
    
    if hasattr(msg, 'answer'):
        await msg.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await msg.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    
    await state.set_state(AdminState.admin_menu)


async def main():
    init_db()
    logger.info("🤖 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

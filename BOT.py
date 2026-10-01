import asyncio
import os
import sqlite3
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ================= SOZLAMALAR =================
# 1. @BotFather bergan tokenni qo'ying:
BOT_TOKEN = "8642381123:AAGT8HWcURijPXZaYfxYjH5IqBIdct7p6tE"

# 2. Netlify havolangizni qo'ying:
WEB_APP_URL = "https://chipper-banoffee-145251.netlify.app/"

# 3. Sizning shaxsiy Telegram ID raqamingiz:
ADMIN_ID = 1333770643

# 4. Sizning Telegram username'ingiz (bog'lanish uchun):
ADMIN_TELEGRAM_LINK = "https://t.me/abb0sbeek"
# ===============================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- MA'LUMOTLAR BAZASI (SQLite) ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            joined_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_user(user_id, first_name, username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    is_new = cursor.fetchone() is None
    if is_new:
        joined_date = datetime.now().strftime("%d.%m.%Y %H:%M")
        cursor.execute(
            "INSERT INTO users (user_id, first_name, username, joined_date) VALUES (?, ?, ?, ?)",
            (user_id, first_name, username, joined_date)
        )
        conn.commit()
    conn.close()
    return is_new

def get_total_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_recent_users(limit=10):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, username, user_id, joined_date FROM users ORDER BY rowid DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_user_date(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT joined_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else datetime.now().strftime("%d.%m.%Y")

# Bazani yaratamiz
init_db()


# --- TUGMALAR ---
def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🚀 Darsni boshlash",
                    web_app=WebAppInfo(url=WEB_APP_URL)
                )
            ],
            [
                InlineKeyboardButton(text="📊 Mening profilim", callback_data="my_profile"),
                InlineKeyboardButton(text="📖 Qo'llanma", callback_data="guide")
            ],
            [
                InlineKeyboardButton(text="👨‍💻 Bog'lanish (Admin)", url=ADMIN_TELEGRAM_LINK)
            ]
        ]
    )


# --- BUYRUQLAR VA HODISALAR ---

# /start bosilganda
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user = message.from_user
    ism = user.first_name or "Do'stim"
    username = f"@{user.username}" if user.username else "yo'q"
    
    # Bazaga saqlaymiz va yangi odamligini tekshiramiz
    is_new = save_user(user.id, ism, username)
    total_users = get_total_users()
    
    # AGAR YANGI FOYDALANUVCHI BO'LSA — ADMINGA (SIZGA) XABAR YUBORAMIZ
    if is_new and user.id != ADMIN_ID:
        try:
            admin_xabari = (
                "🔔 <b>Yangi o'quvchi qo'shildi!</b>\n\n"
                f"• <b>Ism:</b> {ism}\n"
                f"• <b>Username:</b> {username}\n"
                f"• <b>ID:</b> <code>{user.id}</code>\n"
                f"• <b>Sana:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"👥 <b>Jami foydalanuvchilar:</b> {total_users} ta"
            )
            await bot.send_message(chat_id=ADMIN_ID, text=admin_xabari, parse_mode="HTML")
        except Exception:
            pass

    # Foydalanuvchiga salomlashish xabari
    xabar = (
        f"Assalomu alaykum, <b>{ism}</b>!\n\n"
        "🇰🇷 <b>HANU</b> koreys tili platformasiga xush kelibsiz.\n\n"
        "Platformada darslarni boshlash uchun <b>«🚀 Darsni boshlash»</b> tugmasini bosing 👇"
    )
    await message.answer(xabar, reply_markup=get_main_keyboard(), parse_mode="HTML")


# FAQAT SIZ UCHUN STATISTIKA BUYRUG'I (/stat yoki /admin)
@dp.message(Command("stat"))
@dp.message(Command("admin"))
async def admin_stat_cmd(message: types.Message):
    # Faqat sizning ID raqamingiz bo'lsa ishlaydi:
    if message.from_user.id != ADMIN_ID:
        return
    
    total = get_total_users()
    recent = get_recent_users(10)
    
    matn = f"📊 <b>HANU BOT STATISTIKASI</b>\n\n"
    matn += f"👥 <b>Jami foydalanuvchilar:</b> {total} ta\n\n"
    matn += "🕒 <b>Oxirgi qo'shilganlar:</b>\n"
    
    for i, u in enumerate(recent, 1):
        ism, uname, uid, sana = u
        matn += f"{i}. <b>{ism}</b> ({uname}) — <i>{sana}</i>\n"
        
    await message.answer(matn, parse_mode="HTML")


# "Mening profilim" tugmasi bosilganda
@dp.callback_query(F.data == "my_profile")
async def profile_handler(callback: types.CallbackQuery):
    user = callback.from_user
    ism = user.first_name or "Do'stim"
    username = f"@{user.username}" if user.username else "Mavjud emas"
    joined_date = get_user_date(user.id)
    
    profil_matni = (
        f"👤 <b>FOYDALANUVCHI PROFILI</b>\n\n"
        f"• <b>Ism:</b> {ism}\n"
        f"• <b>Username:</b> {username}\n"
        f"• <b>ID raqam:</b> <code>{user.id}</code>\n"
        f"• <b>Ro'yxatdan o'tgan:</b> {joined_date}\n"
        f"• <b>Status:</b> O'quvchi 🎓\n\n"
        "📈 <i>Sizning joriy kuningiz, to'plagan XP laringiz va o'rganilgan so'zlaringiz ilova ichida real vaqtda saqlanadi.</i>\n\n"
        "O'quv ko'rsatkichlaringizni ko'rish uchun ilovani oching 👇"
    )
    
    profil_tugmalari = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Darsni ochish va statistika", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_menu")]
        ]
    )
    await callback.message.edit_text(profil_matni, reply_markup=profil_tugmalari, parse_mode="HTML")
    await callback.answer()


# "Qo'llanma" tugmasi bosilganda
@dp.callback_query(F.data == "guide")
async def guide_handler(callback: types.CallbackQuery):
    matn = (
        "📚 <b>HANU o'rganish tizimi qanday ishlaydi?</b>\n\n"
        "Har bir kunlik dars 5 ta bosqichdan iborat:\n"
        "1️⃣ <b>Flashcard:</b> Yangi so'zlar bilan tanishish va yodlash.\n"
        "2️⃣ <b>Test:</b> To'g'ri variantni tanlash mashqi.\n"
        "3️⃣ <b>Yozish:</b> Koreyschadan o'zbekchaga yozish.\n"
        "4️⃣ <b>Tarjima:</b> O'zbekchadan koreyschaga yozish.\n"
        "5️⃣ <b>Tinglash:</b> Audio talaffuzni eshitib topish.\n\n"
        "⚡ <b>Qoida:</b> Har bir bosqichda kamida <b>80%</b> to'plaganingizda keyingi bosqich ochiladi.\n"
        "🔥 Har kuni dars qilib, o'z <b>Streak</b> (ketma-ket kunlar)ingizni saqlang!"
    )
    orqaga_tugma = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Darsni boshlash", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_menu")]
        ]
    )
    await callback.message.edit_text(matn, reply_markup=orqaga_tugma, parse_mode="HTML")
    await callback.answer()


# "Asosiy menyu" tugmasi bosilganda
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery):
    ism = callback.from_user.first_name or "Do'stim"
    xabar = (
        f"Assalomu alaykum, <b>{ism}</b>!\n\n"
        "🇰🇷 <b>HANU</b> koreys tili platformasiga xush kelibsiz.\n\n"
        "Platformada darslarni boshlash uchun <b>«🚀 Darsni boshlash»</b> tugmasini bosing 👇"
    )
    await message.edit_text(xabar, reply_markup=get_main_keyboard(), parse_mode="HTML")
    await callback.answer()


# Render serveri uchun 24/7 uyg'oq tutuvchi qism:
async def start_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="HANU Bot 24/7 ishlamoqda! 🇰🇷"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    print("Bot muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

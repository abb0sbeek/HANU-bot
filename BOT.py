import asyncio
import os
import json
import sqlite3
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ==================== ASOSIY SOZLAMALAR ====================
# 1. @BotFather bergan tokenni qo'ying:
BOT_TOKEN = "8642381123:AAGT8HWcURijPXZaYfxYjH5IqBIdct7p6tE"

# 2. O'zingizning Netlify havolangizni qo'ying:
WEB_APP_URL = "https://chipper-banoffee-145251.netlify.app/"

# 3. Sizning shaxsiy Telegram ID raqamingiz (kiritildi):
ADMIN_ID = 1333770643

# 4. Sizning shaxsiy Telegram havolangiz (o'quvchilar bog'lanishi uchun):
ADMIN_TELEGRAM_LINK = "https://t.me/abb0sbeek"
# ==========================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ================= MA'LUMOTLAR BAZASI (SQLite) =============
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            joined_date TEXT,
            current_day INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            last_active TEXT
        )
    """)
    # Eski versiyadan yangisiga o'tganda ustunlarni tekshirish
    for col, ctype in [("current_day", "INTEGER DEFAULT 1"), ("xp", "INTEGER DEFAULT 0"), 
                       ("level", "INTEGER DEFAULT 1"), ("last_active", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

def save_new_user(user_id, first_name, username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    is_new = cursor.fetchone() is None
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    if is_new:
        cursor.execute(
            "INSERT INTO users (user_id, first_name, username, joined_date, last_active) VALUES (?, ?, ?, ?, ?)",
            (user_id, first_name, username, now_str, now_str)
        )
        conn.commit()
    conn.close()
    return is_new

def update_user_progress(user_id, first_name, username, day, xp):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    cursor.execute("SELECT user_id, current_day, xp FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        old_day = row[1] or 1
        old_xp = row[2] or 0
        new_day = max(old_day, day)
        new_xp = max(old_xp, xp)
        cursor.execute("""
            UPDATE users 
            SET current_day = ?, xp = ?, last_active = ?, first_name = ?, username = ?
            WHERE user_id = ?
        """, (new_day, new_xp, now_str, first_name, username, user_id))
    else:
        cursor.execute("""
            INSERT INTO users (user_id, first_name, username, joined_date, current_day, xp, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, first_name, username, now_str, day, xp, now_str))
        
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    
    today_str = datetime.now().strftime("%d.%m.%Y")
    cursor.execute("SELECT COUNT(*) FROM users WHERE last_active LIKE ?", (f"{today_str}%",))
    active_today = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT first_name, username, current_day, xp, last_active 
        FROM users 
        ORDER BY xp DESC, current_day DESC 
        LIMIT 10
    """)
    top_users = cursor.fetchall()
    conn.close()
    return total, active_today, top_users

def get_user_info(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT current_day, xp, joined_date FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row

init_db()


# ================= TUGMALAR MENYUSI =======================
def get_main_keyboard(user_id=None):
    tugmalar = [
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
    
    # FAQAT SIZGA (ADMIN GA) KO'RINADIGAN MAXSUS TUGMA:
    if user_id == ADMIN_ID:
        tugmalar.append([
            InlineKeyboardButton(text="👑 Admin Panel (Statistika)", callback_data="admin_stat_btn")
        ])
        
    return InlineKeyboardMarkup(inline_keyboard=tugmalar)


# ================= TELEGRAM HANDLERLAR ====================

# /start bosilganda
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user = message.from_user
    ism = user.first_name or "Do'stim"
    username = f"@{user.username}" if user.username else "yo'q"
    
    is_new = save_new_user(user.id, ism, username)
    
    # Yangi odam kirsa — faqat sizga bildirishnoma boradi
    if is_new and user.id != ADMIN_ID:
        try:
            total, _, _ = get_stats()
            admin_xabari = (
                "🔔 <b>Yangi o'quvchi qo'shildi!</b>\n\n"
                f"• <b>Ism:</b> {ism}\n"
                f"• <b>Username:</b> {username}\n"
                f"• <b>ID:</b> <code>{user.id}</code>\n"
                f"• <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"👥 <b>Jami o'quvchilar:</b> {total} ta"
            )
            await bot.send_message(chat_id=ADMIN_ID, text=admin_xabari, parse_mode="HTML")
        except Exception:
            pass

    xabar = (
        f"Assalomu alaykum, <b>{ism}</b>!\n\n"
        "🇰🇷 <b>HANU</b> koreys tili platformasiga xush kelibsiz.\n\n"
        "Darslarni boshlash uchun <b>«🚀 Darsni boshlash»</b> tugmasini bosing 👇"
    )
    await message.answer(xabar, reply_markup=get_main_keyboard(user.id), parse_mode="HTML")


# FAQAT SIZ UCHUN ADMIN PANEL TUGMASI (va /stat buyrug'i)
@dp.callback_query(F.data.in_(["admin_stat_btn", "refresh_stat"]))
@dp.message(Command("stat"))
@dp.message(Command("admin"))
async def admin_stat_handler(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    if user_id != ADMIN_ID:
        if isinstance(event, types.CallbackQuery):
            await event.answer("Bu bo'lim faqat bot egasi uchun!", show_alert=True)
        return
    
    total, active_today, top_users = get_stats()
    
    matn = "👑 <b>ADMIN PANEL — STATISTIKA</b>\n\n"
    matn += f"👥 <b>Jami o'quvchilar:</b> {total} ta\n"
    matn += f"🔥 <b>Bugun dars qilganlar:</b> {active_today} ta\n\n"
    matn += "🏆 <b>TOP O'QUVCHILAR (Faollik bo'yicha):</b>\n"
    
    if not top_users:
        matn += "<i>Hozircha dars yakunlaganlar yo'q.</i>\n"
    else:
        for i, u in enumerate(top_users, 1):
            ism, uname, day, xp, last_active = u
            matn += (
                f"{i}. <b>{ism}</b> ({uname})\n"
                f"   └ 📍 <b>Kun {day}</b> • ⚡ <b>{xp} XP</b>\n"
                f"   └ 🕒 <i>Oxirgi faollik: {last_active}</i>\n"
            )
    
    admin_klaviatura = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_stat")],
            [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_menu")]
        ]
    )
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(matn, reply_markup=admin_klaviatura, parse_mode="HTML")
        await event.answer("Statistika yangilandi!")
    else:
        await event.answer(matn, reply_markup=admin_klaviatura, parse_mode="HTML")


# "Mening profilim" tugmasi
@dp.callback_query(F.data == "my_profile")
async def profile_handler(callback: types.CallbackQuery):
    user = callback.from_user
    ism = user.first_name or "Do'stim"
    username = f"@{user.username}" if user.username else "Mavjud emas"
    
    row = get_user_info(user.id)
    day = row[0] if row else 1
    xp = row[1] if row else 0
    joined = row[2] if row else datetime.now().strftime("%d.%m.%Y")
    
    profil_matni = (
        f"👤 <b>FOYDALANUVCHI PROFILI</b>\n\n"
        f"• <b>Ism:</b> {ism}\n"
        f"• <b>Username:</b> {username}\n"
        f"• <b>ID raqam:</b> <code>{user.id}</code>\n"
        f"• <b>Ro'yxatdan o'tgan:</b> {joined}\n\n"
        f"📍 <b>Joriy kun:</b> Kun {day}\n"
        f"⚡ <b>To'plagan XP:</b> {xp} ball\n"
        f"🎓 <b>Status:</b> O'quvchi\n\n"
        "Darsni davom ettirish uchun ilovani oching 👇"
    )
    
    tugmalar = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Darsni davom ettirish", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_menu")]
        ]
    )
    await callback.message.edit_text(profil_matni, reply_markup=tugmalar, parse_mode="HTML")
    await callback.answer()


# "Qo'llanma" tugmasi
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
    orqaga = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Darsni boshlash", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_menu")]
        ]
    )
    await callback.message.edit_text(matn, reply_markup=orqaga, parse_mode="HTML")
    await callback.answer()


# "Asosiy menyu" tugmasi
@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery):
    ism = callback.from_user.first_name or "Do'stim"
    xabar = (
        f"Assalomu alaykum, <b>{ism}</b>!\n\n"
        "🇰🇷 <b>HANU</b> koreys tili platformasiga xush kelibsiz.\n\n"
        "Darslarni boshlash uchun <b>«🚀 Darsni boshlash»</b> tugmasini bosing 👇"
    )
    await callback.message.edit_text(xabar, reply_markup=get_main_keyboard(callback.from_user.id), parse_mode="HTML")
    await callback.answer()


# ================= WEB APP API VA 24/7 SERVER =============
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

async def handle_options(request):
    return web.Response(headers=CORS_HEADERS)

# Web App dars tugaganda shu yerga natijalarni jo'natadi
async def handle_progress(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        first_name = data.get("first_name", "")
        username = data.get("username", "")
        day = int(data.get("day", 1))
        xp = int(data.get("xp", 0))
        
        if user_id:
            update_user_progress(user_id, first_name, username, day, xp)
            return web.json_response({"status": "ok"}, headers=CORS_HEADERS)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400, headers=CORS_HEADERS)
    return web.json_response({"status": "ignored"}, headers=CORS_HEADERS)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="HANU Bot 24/7 API faol! 🇰🇷", headers=CORS_HEADERS))
    app.router.add_options("/api/save-progress", handle_options)
    app.router.add_post("/api/save-progress", handle_progress)
    
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

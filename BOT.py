import asyncio
import os
import json
import sqlite3
import aiohttp
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ==================== SOZLAMALAR ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8642381123:AAGT8HwCURijPXZaYfxYjH5IqBIdct7p6tE")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://chipper-banoffee-145251.netlify.app/")
ADMIN_ID = 1333770643
LOG_CHANNEL_ID = -1003919167998
ADMIN_TELEGRAM_LINK = "https://t.me/abb0sbeek"

# Google Gemini API Kaliti (Render Environment Variables dan olinadi)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
# ====================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ZAXIRA JAVOBLAR (Serverda uzilish bo'lsa ham bot to'xtamasligi uchun) ---
FALLBACK_RESPONSES = {
    "salom": (
        "Assalomu alaykum! Men HANU platformasining AI repetitoriman. "
        "Koreys tili bo'yicha savollaringiz bo'lsa, bemalol so'rang! Darslarni boshlash uchun esa pastdagi «🚀 Darsni boshlash» tugmasini bosing."
    ),
    "salomlashish": (
        "🇰🇷 <b>Koreys tilida salomlashish turlari:</b>\n\n"
        "1. <b>안녕하세요 (Annyong-haseyo)</b> — Eng keng tarqalgan, xushmuomala salomlashish (kattalar, hamkasblar, tanishlar uchun).\n"
        "2. <b>안녕하십니까 (Annyong-hashimnikka)</b> — Juda rasmiy va hurmatli salomlashish (yangiliklar, armiya, rasmiy uchrashuvlarda).\n"
        "3. <b>안녕 (Annyong)</b> — Norasmiy, faqat tengdosh va yaqin do'stlar orasida ishlatiladi ('Salom/Xayr').\n"
        "4. <b>처음 뵙겠습니다 (Cho-um boepgesseumnida)</b> — 'Birinchi marta ko'rishib turibmiz' (tanishganda)."
    ),
    "안녕하세요": (
        "안녕하세요! 반갑습니다! (Assalomu alaykum! Tanishganimdan xursandman!)\n"
        "Koreys tilini o'rganishda sizga qanday yordam bera olaman?"
    ),
    "rahmat": (
        "🇰🇷 <b>Koreys tilida minnatdorchilik bildirish:</b>\n\n"
        "1. <b>감사합니다 (Kamsahamnida)</b> — Eng rasmiy va keng tarqalgan 'Rahmat'.\n"
        "2. <b>고마워요 (Komawoyo)</b> — Muloyim, kundalik hayotdagi 'Rahmat'.\n"
        "3. <b>고마워 (Komawo)</b> — Do'stlar orasida 'Rahmat'."
    ),
    "o'rgat": (
        "Koreys tilini 0 dan boshlab mukammal o'rganish uchun bizning <b>5 bosqichli interaktiv dasturimiz</b> tayyorlangan!\n\n"
        "Har kuni yangi so'zlar, grammatika, yozish va audio tinglash orqali o'rganasiz. "
        "Darsni boshlash uchun pastdagi <b>«🚀 Darsni boshlash»</b> tugmasini bosing!"
    )
}

def get_fallback_answer(text: str) -> str:
    t = text.lower().strip()
    for key, val in FALLBACK_RESPONSES.items():
        if key in t:
            return val
    return ""

# --- GEMINI SUN'IY INTELLEKT MIYASI ---
async def ask_gemini(prompt: str, system_instruction: str = "") -> str:
    if not GEMINI_API_KEY:
        fb = get_fallback_answer(prompt)
        if fb:
            return fb
        return (
            "⚠️ <b>AI Repetitor:</b> Gemini API kaliti topilmadi.\n"
            "Iltimos, Render sozlamalariga <code>GEMINI_API_KEY</code> ni kiriting."
        )

    parts = []
    if system_instruction:
        parts.append({"text": f"Yo'riqnoma: {system_instruction}\n\nFoydalanuvchi savoli: {prompt}"})
    else:
        parts.append({"text": prompt})

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 600
        }
    }

    # Yangi va tezkor Gemini 2.0 va 2.5 modellari
    models = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash-latest", "gemini-pro"]

    async with aiohttp.ClientSession() as session:
        for model in models:
            for ver in ["v1beta", "v1"]:
                url = f"https://generativelanguage.googleapis.com/{ver}/models/{model}:generateContent?key={GEMINI_API_KEY}"
                try:
                    async with session.post(url, json=payload, timeout=12) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            c_list = data.get("candidates", [])
                            if c_list:
                                content = c_list[0].get("content", {})
                                p_resp = content.get("parts", [])
                                if p_resp:
                                    return p_resp[0].get("text", "").strip()
                except Exception as e:
                    pass

    fb = get_fallback_answer(prompt)
    if fb:
        return fb
    return "Kechirasiz, sun'iy intellekt serverida vaqtincha uzilish bo'ldi. Birozdan so'ng qayta urinib ko'ring."

async def check_answer_with_ai(korean: str, target: str, user_answer: str, mode: str):
    prompt = f"""Koreys tili va o'zbek tili mutaxassisi sifatida baholang.
Koreyscha so'z: "{korean}"
Lug'atdagi standart o'zbekcha tarjimasi: "{target}"
O'quvchi kiritgan javob: "{user_answer}"
Rejim: {mode} (writing = koreyschadan o'zbekchaga tarjima, translation = o'zbekchadan koreyschaga).

Savol: O'quvchi kiritgan javob ushbu so'zning to'g'ri ma'nosi, sinonimi, muqobil ma'nosi yoki joiz tarjimasi hisoblanadimi?
(Masalan, '이' so'ziga 'ikki' yoki 'bu' yoki 'tish' deb yozsa ham to'g'ri; '사과' so'ziga 'olma' yoki 'kechirim' deb yozsa ham to'g'ri).
Kichik imlo xatosi bo'lsa ham ma'no to'g'ri bo'lsa to'g'ri deb qabul qiling.

Faqat toza JSON formatda javob bering, hech qanday markdown belgilarsiz:
{{"is_correct": true, "feedback": "O'zbek tilida 1 jumlada qisqa tushuntirish"}}"""

    resp = await ask_gemini(prompt)
    try:
        clean = resp.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        return data.get("is_correct", False), data.get("feedback", "")
    except Exception:
        is_ok = "true" in resp.lower()
        return is_ok, resp[:100]

# --- MAHALLIY BAZA (Statistika hisoblash uchun) ---
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            joined_date TEXT,
            current_day INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            last_active TEXT
        )
    """)
    for col, ctype in [("current_day", "INTEGER DEFAULT 1"), ("xp", "INTEGER DEFAULT 0"), ("last_active", "TEXT")]:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    conn.close()

def save_user(user_id, first_name, username):
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

def update_progress_in_db(user_id, first_name, username, day, xp):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    cursor.execute("SELECT current_day, xp FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        new_day = max(row[0] or 1, day)
        new_xp = max(row[1] or 0, xp)
        cursor.execute("""
            UPDATE users SET current_day = ?, xp = ?, last_active = ?, first_name = ?, username = ?
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
        FROM users ORDER BY xp DESC, current_day DESC LIMIT 10
    """)
    top_users = cursor.fetchall()
    conn.close()
    return total, active_today, top_users

init_db()

# --- TUGMALAR ---
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
    
    if user_id == ADMIN_ID:
        tugmalar.append([
            InlineKeyboardButton(text="👑 Admin Panel (Statistika)", callback_data="admin_stat_btn")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=tugmalar)

# --- BOT HANDLERLARI ---
@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user = message.from_user
    ism = user.first_name or "Do'stim"
    username = f"@{user.username}" if user.username else "yo'q"
    
    is_new = save_user(user.id, ism, username)
    
    if is_new:
        try:
            total, _, _ = get_stats()
            kanal_xabari = (
                "👤 <b>YANGI O'QUVCHI QO'SHILDI!</b>\n\n"
                f"• <b>Ism:</b> {ism}\n"
                f"• <b>Username:</b> {username}\n"
                f"• <b>ID:</b> <code>{user.id}</code>\n"
                f"• <b>Sana:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
                f"👥 <b>Jami o'quvchilar:</b> {total} ta"
            )
            await bot.send_message(chat_id=LOG_CHANNEL_ID, text=kanal_xabari, parse_mode="HTML")
        except Exception as e:
            print("Kanalga yuborishda xato:", e)

    xabar = (
        f"Assalomu alaykum, <b>{ism}</b>!\n\n"
        "🇰🇷 <b>HANU</b> koreys tili platformasiga xush kelibsiz.\n\n"
        "Darslarni boshlash uchun <b>«🚀 Darsni boshlash»</b> tugmasini bosing.\n\n"
        "💡 <i>Menga istalgan koreyscha so'z, gap yoki grammatika haqida savol yozsangiz, AI Repetitor sifatida darhol javob beraman!</i>"
    )
    await message.answer(xabar, reply_markup=get_main_keyboard(user.id), parse_mode="HTML")

# AI BILAN ERKIN CHAT (Foydalanuvchi botga savol yozganda)
@dp.message(F.text & ~F.text.startswith("/"))
async def ai_chat_handler(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    user_prompt = message.text
    system_prompt = (
        "Siz 'HANU' koreys tili ta'lim platformasining shaxsiy sun'iy intellekt ustozisiz (AI Repetitor). "
        "Foydalanuvchining savollariga o'zbek tilida juda muloyim, sodda, tushunarli va koreyscha misollar bilan javob bering. "
        "Koreyscha so'zlarning talaffuzi va o'zbekcha ma'nolarini aniq tushuntiring."
    )
    answer = await ask_gemini(user_prompt, system_prompt)
    if answer:
        await message.reply(f"🤖 <b>AI Ustoz:</b>\n\n{answer}", parse_mode="HTML")
    else:
        await message.reply("Kechirasiz, savolingizni tushuna olmadim. Qaytadan so'rab ko'ring.")

# ADMIN PANEL TUGMASI
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

@dp.callback_query(F.data == "my_profile")
async def profile_handler(callback: types.CallbackQuery):
    user = callback.from_user
    ism = user.first_name or "Do'stim"
    username = f"@{user.username}" if user.username else "Mavjud emas"
    
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT current_day, xp, joined_date FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    conn.close()
    
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
        "🔥 Har kuni dars qilib, o'z <b>Streak</b>ingizni saqlang!\n"
        "🤖 <i>Har qanday savolingiz bo'lsa, botga to'g'ridan-to'g'ri yozsangiz AI Ustoz javob beradi.</i>"
    )
    orqaga = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Darsni boshlash", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_menu")]
        ]
    )
    await callback.message.edit_text(matn, reply_markup=orqaga, parse_mode="HTML")
    await callback.answer()

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

# --- WEB APP UCHUN API VA 24/7 SERVER ---
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}

async def handle_options(request):
    return web.Response(headers=CORS_HEADERS)

# Dars natijasini saqlash va kanalga yuborish
async def handle_progress(request):
    try:
        data = await request.json()
        user_id = data.get("user_id")
        first_name = data.get("first_name", "O'quvchi")
        username = data.get("username", "")
        day = int(data.get("day", 1))
        xp = int(data.get("xp", 0))
        stage_name = data.get("stage_name", "Dars")
        
        if user_id:
            update_progress_in_db(user_id, first_name, username, day, xp)
            try:
                log_msg = (
                    "📈 <b>DARS NATIJASI / FAOLLIK</b>\n\n"
                    f"• <b>O'quvchi:</b> {first_name} (@{username})\n"
                    f"• <b>ID:</b> <code>{user_id}</code>\n"
                    f"• <b>Bosqich:</b> {stage_name} (Kun {day})\n"
                    f"• <b>Jami XP:</b> ⚡ <b>{xp} ball</b>\n"
                    f"• <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                )
                await bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_msg, parse_mode="HTML")
            except Exception as e:
                print("Kanalga log yozishda xato:", e)
                
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400, headers=CORS_HEADERS)

# AI BILAN JAVOBNI AQLLI TEKSHIRISH (Web App dan keladigan so'rovlar uchun)
async def handle_ai_check(request):
    try:
        data = await request.json()
        korean = data.get("korean", "")
        target = data.get("target", "")
        user_answer = data.get("user_answer", "")
        mode = data.get("mode", "writing")
        
        if not user_answer:
            return web.json_response({"is_correct": False, "feedback": "Javob kiritilmadi."}, headers=CORS_HEADERS)
            
        is_ok, feedback = await check_answer_with_ai(korean, target, user_answer, mode)
        return web.json_response({"is_correct": is_ok, "feedback": feedback}, headers=CORS_HEADERS)
    except Exception as e:
        return web.json_response({"is_correct": False, "feedback": f"Xatolik: {str(e)}"}, status=500, headers=CORS_HEADERS)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="HANU AI Server 24/7 faol! 🇰🇷🧠", headers=CORS_HEADERS))
    app.router.add_options("/api/save-progress", handle_options)
    app.router.add_post("/api/save-progress", handle_progress)
    app.router.add_options("/api/ai-check-answer", handle_options)
    app.router.add_post("/api/ai-check-answer", handle_ai_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    print("Bot va AI server muvaffaqiyatli ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

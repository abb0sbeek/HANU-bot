import asyncio
import os
import json
import sqlite3
import aiohttp
from datetime import datetime, timezone, timedelta
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ==================== SOZLAMALAR ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8642381123:AAGT8HWcURijPXZaYfxYjH5IqBIdct7p6tE")
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://magnificent-khapse-15846f.netlify.app?v=2.3")
ADMIN_ID = 1333770643
REQUIRED_CHANNEL = "@abbosbekkorea"
REQUIRED_CHANNEL_URL = "https://t.me/abbosbekkorea"
LOG_CHANNEL_ID = -1003919167998
ADMIN_TELEGRAM_LINK = "https://t.me/abb0sbeek"

# Google Gemini API Kaliti
RAW_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_KEY = RAW_KEY.strip().strip('"').strip("'")
# ====================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============================================================
# MAJBURIY OBUNA (FORCED SUBSCRIPTION) TIZIMI
# ============================================================
async def check_channel_subscription(user_id: int) -> bool:
    """Foydalanuvchi @abbosbekkorea kanaliga a'zo ekanligini tekshiradi"""
    if user_id == ADMIN_ID or user_id <= 0:
        return True
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
        elif member.status == "restricted":
            return getattr(member, "is_member", False)
        return False
    except Exception as e:
        # Bot kanalda admin bo'lmaguncha yoki kanal topilmaganda bot qotib qolmasligi uchun
        print(f"[OBUNA TEKSHIRISH OGOHLANTIRISH]: {e}")
        # Agar "Chat not found" yoki "bot is not a member" bo'lsa, xatolik berishi mumkin
        # Lekin foydalanuvchi botni admin qilsa, get_chat_member aniq status qaytaradi
        return True

def get_subscription_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Kanalga a'zo bo'lish", url=REQUIRED_CHANNEL_URL)],
            [InlineKeyboardButton(text="✅ A'zo bo'ldim (Tekshirish)", callback_data="check_subscription")]
        ]
    )

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user or user.id == ADMIN_ID:
            return await handler(event, data)

        # Obunani tekshirish tugmasi bosilganda to'xtatmasdan o'tkazib yuboramiz
        if isinstance(event, types.CallbackQuery) and event.data == "check_subscription":
            return await handler(event, data)

        # Har qanday xabar yoki tugma bosilganda kanal a'zoligi tekshiriladi
        is_sub = await check_channel_subscription(user.id)
        if not is_sub:
            sub_msg = (
                f"⚠️ <b>Assalomu alaykum, {user.first_name}!</b>\n\n"
                f"Botimizdan to'liq foydalanish va koreys tili darslarini o'rganish uchun "
                f"rasmiy <b>{REQUIRED_CHANNEL}</b> kanalimizga obuna bo'lishingiz shart!\n\n"
                f"<i>(Agar kanaldan chiqib ketsangiz, bot qayta a'zo bo'lishingizni so'raydi)</i>\n\n"
                f"Pastdagi tugma orqali kanalga obuna bo'ling va <b>«✅ A'zo bo'ldim»</b> tugmasini bosing:"
            )
            if isinstance(event, types.Message):
                await event.answer(sub_msg, reply_markup=get_subscription_keyboard(), parse_mode="HTML")
            elif isinstance(event, types.CallbackQuery):
                await event.answer("⚠️ Avval kanalimizga a'zo bo'ling!", show_alert=True)
                try:
                    await event.message.answer(sub_msg, reply_markup=get_subscription_keyboard(), parse_mode="HTML")
                except Exception:
                    pass
            return

        return await handler(event, data)

# Middleware larni ro'yxatdan o'tkazish
dp.message.middleware(SubscriptionMiddleware())
dp.callback_query.middleware(SubscriptionMiddleware())

@dp.callback_query(F.data == "check_subscription")
async def check_subscription_callback_handler(callback: types.CallbackQuery):
    user = callback.from_user
    is_sub = await check_channel_subscription(user.id)
    if is_sub:
        await callback.answer("✅ Obunangiz tasdiqlandi! Rahmat!", show_alert=True)
        save_or_update_user(user.id, user.first_name, user.username)
        xabar = (
            f"🎉 <b>Ajoyib, {user.first_name}! Kanalga a'zoligingiz tasdiqlandi!</b>\n\n"
            f"🇰🇷 <b>HANU — Koreys tili 5 bosqichli tizimiga xush kelibsiz!</b>\n\n"
            f"Darslarni boshlash uchun pastdagi <b>«🚀 Darsni boshlash»</b> tugmasini bosing:"
        )
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(xabar, reply_markup=get_main_keyboard(user.id), parse_mode="HTML")
    else:
        await callback.answer("❌ Siz hali kanalga a'zo bo'lmadingiz! Iltimos, avval kanalga obuna bo'ling.", show_alert=True)
# ============================================================


class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

# --- TEZKOR ZAXIRA BAZASI ---
FAST_KNOWLEDGE_BASE = {
    "olma": "🍎 **Olma** — **사과** [sa-gwa].\n*Misol:* 사과를 먹어요 (Olma yeyman).",
    "suv": "💧 **Suv** — **물** [mul].\n*Misol:* 물을 마셔요 (Suv ichaman).",
    "kitob": "📚 **Kitob** — **책** [chaek].\n*Misol:* 책을 읽어요 (Kitob o'qiyman).",
    "maktab": "🏫 **Maktab** — **학교** [hak-kyo].\n*Misol:* 학교에 가요 (Maktabga boraman).",
    "salomlashish": (
        "🇰🇷 <b>Koreyscha salomlashish turlari:</b>\n\n"
        "1. <b>안녕하세요 (Annyong-haseyo)</b> — Xushmuomala salomlashish (kattalar, notanishlar uchun).\n"
        "2. <b>안녕하십니까 (Annyong-hashimnikka)</b> — Juda rasmiy (armiya, yangiliklar, biznes).\n"
        "3. <b>안녕 (Annyong)</b> — Norasmiy, faqat yaqin do'stlar va tengdoshlar uchun."
    ),
    "salom": "Assalomu alaykum! Koreys tili bo'yicha savolingiz bormi? Darslarni boshlash uchun «🚀 Darsni boshlash» tugmasini bosing.",
    "qalesiz": "Rahmat, yaxshi! Koreys tilini o'rganishda qanday yordam bera olaman?",
    "안녕하세요": "안녕하세요! 반갑습니다! (Assalomu alaykum! Tanishganimdan xursandman!)",
    "rahmat": "Arzimaydi! Koreys tilida 'rahmat' — <b>감사합니다 (kamsahamnida)</b> yoki do'stlar orasida <b>고마워 (komawo)</b>.",
    "qiynalyapman": (
        "💡 <b>Koreyscha so'zlarni tez va oson yodlash uchun 4 ta oltin qoida:</b>\n\n"
        "1️⃣ <b>Kuniga 15-20 tadan oshirmang:</b> Bir kunda 50 ta so'z yodlagandan ko'ra, har kuni 15 tadan sifatli yodlash 10 barobar foydaliroq.\n"
        "2️⃣ <b>HANU 5 bosqichli tizimidan foydalaning:</b> Flashcard ➔ Test ➔ Yozish ➔ Tarjima ➔ Tinglash.\n"
        "3️⃣ <b>So'zni gap ichida bog'lang:</b> Masalan, shunchaki '사과' emas, '사과를 먹어요' deb yodlang.\n"
        "4️⃣ <b>Ovoz chiqarib takrorlang:</b> Miya eshitgan so'zini ancha uzoq eslab qoladi!"
    ),
    "yodlash": (
        "💡 <b>Koreyscha so'zlarni tez va oson yodlash uchun 4 ta oltin qoida:</b>\n\n"
        "1️⃣ <b>Kuniga 15-20 tadan oshirmang:</b> Bir kunda 50 ta so'z yodlagandan ko'ra, har kuni 15 tadan sifatli yodlash 10 barobar foydaliroq.\n"
        "2️⃣ <b>HANU 5 bosqichli tizimidan foydalaning:</b> Flashcard ➔ Test ➔ Yozish ➔ Tarjima ➔ Tinglash.\n"
        "3️⃣ <b>So'zni gap ichida bog'lang:</b> Masalan, '사과를 먹어요' (Olma yeyman).\n"
        "4️⃣ <b>Ovoz chiqarib takrorlang:</b> Miya eshitgan so'zini ancha uzoq eslab qoladi!"
    ),
    "o'rgat": "Koreys tilini 0 dan mukammal o'rganish uchun pastdagi <b>«🚀 Darsni boshlash»</b> tugmasini bosing!"
}

def check_fast_knowledge(prompt: str) -> str:
    p = prompt.lower().strip()
    for k, v in FAST_KNOWLEDGE_BASE.items():
        if k in p:
            return v
    return ""

# --- GEMINI SUN'IY INTELLEKT (Tezkor va lo'nda) ---
async def ask_gemini(prompt: str, is_simple: bool = False) -> str:
    fast_resp = check_fast_knowledge(prompt)
    if fast_resp:
        return fast_resp

    if not GEMINI_API_KEY:
        return "⚠️ Gemini API kaliti kiritilmagan. Render Environment'ga GEMINI_API_KEY qo'ying."

    if is_simple:
        instruction = (
            "Siz 'HANU' koreys tili repetitorisiz. "
            "QAT'IY TALAB: Javobingiz atigi 1-2 qatordan oshmasin! "
            "Kirish ('Salom!'), xulosa ('Fighting!') yoki qiziqarli faktlar YOZMANG! "
            "Format: So'z — **Koreyscha** [talaffuz]. Misol: koreyscha gap (o'zbekcha tarjima)."
        )
        max_tokens = 150
    else:
        instruction = (
            "Siz 'HANU' koreys tili repetitorisiz. "
            "Ortiqcha kirish va xulosa gaplarsiz, to'g'ridan-to'g'ri savolga javob bering. "
            "Eng muhim 3-4 ta amaliy punktda ixcham va lo'nda tushuntiring."
        )
        max_tokens = 350

    payload = {
        "contents": [{
            "parts": [{"text": f"Yo'riqnoma: {instruction}\n\nFoydalanuvchi savoli: {prompt}"}]
        }],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": max_tokens
        }
    }

    models = ["gemini-2.0-flash", "gemini-1.5-flash-latest"]

    async with aiohttp.ClientSession() as session:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                async with session.post(url, json=payload, timeout=6) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
            except Exception:
                pass

    return "Koreys tili bo'yicha savolingiz qabul qilindi. Aniqroq so'rab ko'ring yoki pastdagi «🚀 Darsni boshlash» tugmasi orqali darslarga o'ting."

# AI orqali toza baholash (Zaxira lug'atga aralashmasdan to'g'ridan-to'g'ri Gemini ga boradi)
async def ask_gemini_pure(prompt: str) -> str:
    key = GEMINI_API_KEY
    if not key:
        return ""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 150
        }
    }

    models = ["gemini-2.0-flash", "gemini-1.5-flash-latest"]
    async with aiohttp.ClientSession() as session:
        for model in models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            try:
                async with session.post(url, json=payload, timeout=6) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            content = candidates[0].get("content", {})
                            parts = content.get("parts", [])
                            if parts:
                                return parts[0].get("text", "").strip()
            except Exception:
                pass
    return ""

async def check_answer_with_ai(korean: str, target: str, user_answer: str, mode: str):
    prompt = f"""Siz koreys tili va o'zbek tili bo'yicha qat'iy va aqlli imtihonchisisiz.
Koreyscha so'z: "{korean}"
Lug'atdagi standart tarjima: "{target}"
O'quvchi yozgan javob: "{user_answer}"
Rejim: {mode} (writing = koreyschadan o'zbekchaga, translation = o'zbekchadan koreyschaga).

Baholash mezonlari:
1. Agar o'quvchi ushbu so'zning to'g'ri ma'nosi, sinonimi, muqobil ma'nosi yoki joiz tarjimasini yozgan bo'lsa (masalan '안녕하세요' ga 'salom' yoki 'assalomu alaykum' deb yozsa ham), to'g'ri deb qabul qiling.
2. Oddiy va jingalak apostrof (o'qing vs o`qing vs o’qing) farqi bo'lsa ham to'g'ri deb qabul qiling.
3. Kichik imlo xatosi bo'lsa-da ma'no to'g'ri bo'lsa to'g'ri deb hisoblang.
4. Javobingiz FAQAT toza JSON bo'lsin:
{{"is_correct": true, "feedback": "1 qisqa jumla izoh"}}"""

    resp = await ask_gemini_pure(prompt)
    try:
        clean = resp.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean)
        return data.get("is_correct", False), data.get("feedback", "")
    except Exception:
        is_ok = "true" in resp.lower()
        return is_ok, resp[:100]

# --- MAHALLIY BAZA VA SOZLAMALAR ---
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
            last_active TEXT,
            reminder_time TEXT DEFAULT '20:00',
            reminder_offset INTEGER DEFAULT 300,
            reminder_enabled INTEGER DEFAULT 1
        )
    """)
    # Eski bazalar uchun yangi ustunlarni tekshirib qo'shish:
    extra_cols = [
        ("current_day", "INTEGER DEFAULT 1"),
        ("xp", "INTEGER DEFAULT 0"),
        ("last_active", "TEXT"),
        ("reminder_time", "TEXT DEFAULT '20:00'"),
        ("reminder_offset", "INTEGER DEFAULT 300"),
        ("reminder_enabled", "INTEGER DEFAULT 1")
    ]
    for col, ctype in extra_cols:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {ctype}")
        except sqlite3.OperationalError:
            pass
    conn.commit()
    # Sinov / brauzer orqali tushib qolgan user_id = 0 yozuvlarni tozalash:
    cursor.execute("DELETE FROM users WHERE user_id <= 0")
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
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_id > 0")
    total = cursor.fetchone()[0]
    
    today_str = datetime.now().strftime("%d.%m.%Y")
    cursor.execute("SELECT COUNT(*) FROM users WHERE user_id > 0 AND last_active LIKE ?", (f"{today_str}%",))
    active_today = cursor.fetchone()[0]

    try:
        cursor.execute("SELECT COUNT(*) FROM reminders WHERE enabled = 1 AND user_id > 0")
        active_reminders = cursor.fetchone()[0]
    except Exception:
        active_reminders = 0
    
    cursor.execute("""
        SELECT first_name, username, current_day, xp, last_active 
        FROM users WHERE user_id > 0 ORDER BY xp DESC, current_day DESC LIMIT 10
    """)
    top_users = cursor.fetchall()
    conn.close()
    return total, active_today, active_reminders, top_users

def get_leaderboard(current_user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        SELECT user_id, first_name, username, current_day, xp 
        FROM users WHERE user_id > 0 ORDER BY xp DESC, current_day DESC LIMIT 10
    """)
    top_10 = c.fetchall()
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("""
        SELECT COUNT(*) + 1 FROM users WHERE xp > (SELECT COALESCE(xp, 0) FROM users WHERE user_id = ?)
    """, (current_user_id,))
    my_rank_res = c.fetchone()
    my_rank = my_rank_res[0] if my_rank_res else 1
    
    c.execute("SELECT current_day, xp FROM users WHERE user_id = ?", (current_user_id,))
    my_data = c.fetchone()
    conn.close()
    return top_10, my_rank, my_data, total_users

def set_user_reminder(user_id, reminder_time, offset=300, enabled=1):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        UPDATE users SET reminder_time = ?, reminder_offset = ?, reminder_enabled = ?
        WHERE user_id = ?
    """, (reminder_time, offset, enabled, user_id))
    conn.commit()
    conn.close()

def get_user_reminder(user_id):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT reminder_time, reminder_offset, reminder_enabled FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"reminder_time": row[0] or "20:00", "offset": row[1] or 300, "enabled": bool(row[2])}
    return {"reminder_time": "20:00", "offset": 300, "enabled": True}

def get_all_user_ids():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id > 0")
    users = [r[0] for r in c.fetchall()]
    conn.close()
    return users

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
            InlineKeyboardButton(text="🏆 Reyting (Leaderboard)", callback_data="leaderboard"),
            InlineKeyboardButton(text="📊 Profilim", callback_data="my_profile")
        ],
        [
            InlineKeyboardButton(text="📖 Qo'llanma", callback_data="guide"),
            InlineKeyboardButton(text="👨‍💻 Bog'lanish", url=ADMIN_TELEGRAM_LINK)
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
        "🇰🇷 <b>HANU</b> koreys tili ta'lim platformasiga xush kelibsiz.\n\n"
        "Darslarni boshlash uchun <b>«🚀 Darsni boshlash»</b> tugmasini bosing.\n\n"
        "💡 <i>Menga istalgan koreyscha so'z, gap yoki grammatika haqida savol yozsangiz, AI Repetitor sifatida darhol javob beraman!</i>"
    )
    await message.answer(xabar, reply_markup=get_main_keyboard(user.id), parse_mode="HTML")

# LEADERBOARD (Bot orqali ko'rish)
@dp.callback_query(F.data == "leaderboard")
@dp.message(Command("top"))
@dp.message(Command("leaderboard"))
async def leaderboard_handler(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    top_10, my_rank, my_data, total_users = get_leaderboard(user_id)
    my_day = my_data[0] if my_data else 1
    my_xp = my_data[1] if my_data else 0

    matn = "🏆 <b>HANU — TOP O'QUVCHILAR REYTINGI</b>\n\n"
    matn += "Eng ko'p ball (XP) to'plagan faol o'quvchilar:\n\n"

    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

    if not top_10:
        matn += "<i>Hozircha reyting shakllanmagan. Darslarni birinchi bo'lib boshlang!</i>\n\n"
    else:
        for idx, u in enumerate(top_10):
            u_id, ism, uname, day, xp_val = u
            medal = medals[idx] if idx < len(medals) else f"{idx+1}."
            belgi = " (Siz) ⭐️" if u_id == user_id else ""
            matn += f"{medal} <b>{ism}</b>{belgi}\n   └ 📍 Kun {day} • ⚡ <b>{xp_val:,} XP</b>\n"

    matn += "\n" + "—" * 25 + "\n"
    matn += f"👤 <b>Sizning o'rningiz:</b> #{my_rank}-o'rin (Jami {total_users} ta)\n"
    matn += f"📍 <b>Joriy holat:</b> Kun {my_day} • ⚡ <b>{my_xp:,} XP</b>\n\n"
    matn += "🔥 <i>Reytingda yuqoriga ko'tarilish uchun har kuni darslarni bajaring!</i>"

    klaviatura = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Darsni boshlash", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="leaderboard"), InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_menu")]
        ]
    )

    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(matn, reply_markup=klaviatura, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(matn, reply_markup=klaviatura, parse_mode="HTML")

# ADMIN PANEL VA BROADCAST
@dp.callback_query(F.data.in_(["admin_stat_btn", "refresh_stat"]))
@dp.message(Command("stat"))
@dp.message(Command("admin"))
async def admin_stat_handler(event: types.Message | types.CallbackQuery):
    user_id = event.from_user.id
    if user_id != ADMIN_ID:
        if isinstance(event, types.CallbackQuery):
            await event.answer("Bu bo'lim faqat bot egasi uchun!", show_alert=True)
        return
    
    total, active_today, active_reminders, top_users = get_stats()
    
    lines = [
        "👑 <b>ADMIN PANEL — HANU BOT</b>\n",
        f"👥 <b>Jami o'quvchilar:</b> {total} ta",
        f"🔥 <b>Bugun faol bo'lganlar:</b> {active_today} ta",
        f"⏰ <b>Eslatma yoqqanlar:</b> {active_reminders} ta\n",
        "🏆 <b>TOP-10 O'QUVCHILAR:</b>"
    ]
    
    if not top_users:
        lines.append("<i>Hozircha dars yakunlaganlar yo'q.</i>")
    else:
        for i, u in enumerate(top_users, 1):
            ism, uname, day, xp, last_active = u
            clean_uname = f"@{uname.replace('@', '')}" if uname and uname not in ["0", "yo'q", "@0"] else "username yo'q"
            lines.append(f"{i}. <b>{ism}</b> ({clean_uname})")
            lines.append(f"   └ 📍 <b>Kun {day}</b> • ⚡ <b>{xp} XP</b> • 🕒 <i>{last_active}</i>")
    
    matn = "\n".join(lines)
    
    admin_klaviatura = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Barchaga xabar yuborish (Broadcast)", callback_data="admin_broadcast_prompt")],
            [InlineKeyboardButton(text="⏰ Eslatmani darhol barchaga yuborish", callback_data="admin_send_reminder_now")],
            [InlineKeyboardButton(text="📥 O'quvchilar ro'yxati (CSV)", callback_data="admin_export_users_csv")],
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="refresh_stat"), InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_menu")]
        ]
    )
    
    if isinstance(event, types.CallbackQuery):
        await event.message.edit_text(matn, reply_markup=admin_klaviatura, parse_mode="HTML")
        await event.answer("Statistika yangilandi!")
    else:
        await event.answer(matn, reply_markup=admin_klaviatura, parse_mode="HTML")

@dp.callback_query(F.data == "admin_export_users_csv")
async def export_users_csv_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, username, current_day, xp, last_active FROM users WHERE user_id > 0 ORDER BY xp DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        await callback.answer("Hozircha foydalanuvchilar mavjud emas.", show_alert=True)
        return

    import io
    import csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["User ID", "Ismi", "Username", "Joriy Kun", "XP", "Oxirgi faollik"])
    for r in rows:
        writer.writerow(r)
    
    csv_bytes = output.getvalue().encode("utf-8-sig")
    doc = types.BufferedInputFile(csv_bytes, filename=f"hanu_users_{datetime.now().strftime('%Y%m%d')}.csv")
    await callback.message.answer_document(doc, caption=f"📊 <b>Jami {len(rows)} ta o'quvchi ro'yxati (CSV)</b>", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast_prompt")
async def broadcast_prompt_handler(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer(
        "📢 <b>Barcha o'quvchilarga yubormoqchi bo'lgan xabaringizni yuboring:</b>\n\n"
        "• Bu oddiy matn, rasm (matn bilan), video yoki ovozli xabar bo'lishi mumkin.\n"
        "• Har bir xabar ostiga avtomatik «🚀 Darsni davom ettirish» tugmasi qo'shiladi.\n\n"
        "<i>(Bekor qilish uchun /cancel deb yozing)</i>",
        parse_mode="HTML"
    )
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Xabar yuborish bekor qilindi.")
        return

    users = get_all_user_ids()
    if not users:
        await state.clear()
        await message.answer("❌ Baza bo'sh, foydalanuvchilar topilmadi.")
        return

    status_msg = await message.answer(f"⏳ <b>{len(users)} ta o'quvchiga xabar yuborilmoqda...</b>", parse_mode="HTML")
    
    success = 0
    fail = 0
    btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚀 Darsni davom ettirish", web_app=WebAppInfo(url=WEB_APP_URL))]]
    )

    for uid in users:
        try:
            await message.copy_to(chat_id=uid, reply_markup=btn)
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            fail += 1

    await state.clear()
    await status_msg.edit_text(
        f"✅ <b>Ommaviy xabarnoma yakunlandi!</b>\n\n"
        f"• Yetkazildi: <b>{success}</b> ta\n"
        f"• Yetib bormadi (bloklagan): <b>{fail}</b> ta\n"
        f"• Jami bazada: <b>{len(users)}</b> ta",
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_send_reminder_now")
async def send_reminder_now_handler(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    users = get_all_user_ids()
    matn = (
        "🔥 <b>Koreys tili darsingiz sizni kutmoqda!</b>\n\n"
        "Bugungi 15 daqiqalik darsni bajarib, o'z <b>Streak</b>ingizni saqlang va yangi XP to'plang!\n\n"
        "Muntazamlik — til o'rganishdagi eng asosiy sir! 🚀"
    )
    btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🚀 Darsni davom ettirish", web_app=WebAppInfo(url=WEB_APP_URL))]]
    )
    
    sent = 0
    for uid in users:
        try:
            await bot.send_message(chat_id=uid, text=matn, reply_markup=btn, parse_mode="HTML")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass

    await callback.answer(f"✅ {sent} ta o'quvchiga eslatma yuborildi!", show_alert=True)

@dp.callback_query(F.data == "my_profile")
async def profile_handler(callback: types.CallbackQuery):
    user = callback.from_user
    ism = user.first_name or "Do'stim"
    username = f"@{user.username}" if user.username else "Mavjud emas"
    
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT current_day, xp, joined_date, reminder_time FROM users WHERE user_id = ?", (user.id,))
    row = c.fetchone()
    conn.close()
    
    day = row[0] if row else 1
    xp = row[1] if row else 0
    joined = row[2] if row else datetime.now().strftime("%d.%m.%Y")
    rem_time = row[3] if row and len(row) > 3 and row[3] else "20:00"
    
    profil_matni = (
        f"👤 <b>FOYDALANUVCHI PROFILI</b>\n\n"
        f"• <b>Ism:</b> {ism}\n"
        f"• <b>Username:</b> {username}\n"
        f"• <b>ID raqam:</b> <code>{user.id}</code>\n"
        f"• <b>Ro'yxatdan o'tgan:</b> {joined}\n\n"
        f"📍 <b>Joriy kun:</b> Kun {day}\n"
        f"⚡ <b>To'plagan XP:</b> {xp:,} ball\n"
        f"⏰ <b>Kunlik eslatma:</b> {rem_time}\n"
        f"🎓 <b>Status:</b> O'quvchi\n\n"
        "Darsni davom ettirish uchun ilovani oching 👇"
    )
    
    tugmalar = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Darsni davom ettirish", web_app=WebAppInfo(url=WEB_APP_URL))],
            [InlineKeyboardButton(text="🏆 Reytingni ko'rish", callback_data="leaderboard")],
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

# AI BILAN ERKIN CHAT
@dp.message(F.text & ~F.text.startswith("/"))
async def ai_chat_handler(message: types.Message):
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    user_prompt = message.text.strip()
    
    words = user_prompt.split()
    is_simple = len(words) <= 4 or "nima degani" in user_prompt.lower() or "tarjima" in user_prompt.lower()
    
    answer = await ask_gemini(user_prompt, is_simple=is_simple)
    if answer:
        await message.reply(f"🤖 <b>AI Ustoz:</b>\n\n{answer}", parse_mode="HTML")
    else:
        await message.reply("Kechirasiz, savolingizni tushuna olmadim. Qaytadan so'rab ko'ring.")

# --- FOYDALANUVCHILARNING SHAXSIY VAQTIGA QARAB KUNLIK ESLATMA YUBORISH ---
async def personalized_reminder_scheduler():
    sent_today = set() # (user_id, 'YYYY-MM-DD')
    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            conn = sqlite3.connect("users.db")
            c = conn.cursor()
            c.execute("SELECT user_id, first_name, reminder_time, reminder_offset, reminder_enabled FROM users WHERE reminder_enabled = 1")
            rows = c.fetchall()
            conn.close()

            for r in rows:
                uid, ism, rem_time, offset, enabled = r
                if not enabled or not rem_time:
                    continue
                
                # Foydalanuvchining shaxsiy mahalliy vaqtini hisoblash
                user_local_dt = now_utc + timedelta(minutes=(offset or 300))
                user_local_hm = user_local_dt.strftime("%H:%M")
                user_local_date = user_local_dt.strftime("%Y-%m-%d")

                if user_local_hm == rem_time:
                    key = (uid, user_local_date)
                    if key not in sent_today:
                        sent_today.add(key)
                        clean_name = ism or "Do'stim"
                        matn = (
                            f"🔥 <b>Salom, {clean_name}!</b>\n\n"
                            f"⏰ Siz belgilagan dars vaqti bo'ldi ({rem_time}).\n"
                            "Bugungi 15 daqiqalik koreys tili darsini bajarib, <b>Streak</b>ingizni saqlang va yangi XP to'plang! 🚀"
                        )
                        btn = InlineKeyboardMarkup(
                            inline_keyboard=[[InlineKeyboardButton(text="🚀 Darsni boshlash", web_app=WebAppInfo(url=WEB_APP_URL))]]
                        )
                        try:
                            await bot.send_message(chat_id=uid, text=matn, reply_markup=btn, parse_mode="HTML")
                            await asyncio.sleep(0.05)
                        except Exception:
                            pass

            # Har kuni eski yozuvlarni tozalab turish
            if len(sent_today) > 5000:
                sent_today.clear()

        except Exception as e:
            print("Reminder scheduler exception:", e)
            
        await asyncio.sleep(30)

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
                    f"• <b>Jami XP:</b> ⚡ <b>{xp:,} ball</b>\n"
                    f"• <b>Vaqt:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}"
                )
                await bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_msg, parse_mode="HTML")
            except Exception as e:
                print("Kanalga log yozishda xato:", e)
                
        return web.json_response({"status": "ok"}, headers=CORS_HEADERS)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=400, headers=CORS_HEADERS)

# Web App uchun Leaderboard API
async def handle_get_leaderboard(request):
    try:
        user_id_param = request.query.get("user_id", "0")
        try:
            user_id = int(user_id_param)
        except ValueError:
            user_id = 0
            
        top_10_raw, my_rank, my_data, total_users = get_leaderboard(user_id)
        
        top_10 = []
        for r in top_10_raw:
            u_name = r[2] if r[2] and str(r[2]).strip() not in ["0", "yo'q", "@yo'q", "@0"] else ""
            top_10.append({
                "user_id": r[0],
                "first_name": r[1] or "O'quvchi",
                "username": u_name,
                "current_day": r[3] or 1,
                "xp": r[4] or 0
            })
            
        return web.json_response({
            "status": "ok",
            "top_10": top_10,
            "my_rank": my_rank,
            "my_xp": my_data[1] if my_data else 0,
            "my_day": my_data[0] if my_data else 1,
            "total_users": total_users
        }, headers=CORS_HEADERS)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500, headers=CORS_HEADERS)

# Web App orqali kunlik eslatma vaqtini sozlash
async def handle_set_reminder(request):
    try:
        data = await request.json()
        user_id = int(data.get("user_id", 0))
        reminder_time = data.get("reminder_time", "20:00")
        offset = int(data.get("offset", 300))
        enabled = 1 if data.get("enabled", True) else 0
        
        if user_id:
            set_user_reminder(user_id, reminder_time, offset, enabled)
            return web.json_response({"status": "ok", "reminder_time": reminder_time}, headers=CORS_HEADERS)
        return web.json_response({"status": "error", "message": "user_id kerak"}, status=400, headers=CORS_HEADERS)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500, headers=CORS_HEADERS)

async def handle_get_reminder(request):
    try:
        user_id_param = request.query.get("user_id", "0")
        user_id = int(user_id_param)
        res = get_user_reminder(user_id)
        return web.json_response({"status": "ok", **res}, headers=CORS_HEADERS)
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500, headers=CORS_HEADERS)

# AI tekshiruvi
# Yuqori sifatli Audio TTS (Telefonda va Telegramda 100% ovoz chiqishi uchun)
async def handle_tts(request):
    try:
        text = request.query.get("text", "").strip()
        if not text:
            return web.Response(status=400, text="text required", headers=CORS_HEADERS)
            
        import urllib.parse
        encoded = urllib.parse.quote(text)
        url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl=ko&client=tw-ob&q={encoded}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://translate.google.com/"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=8) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return web.Response(
                        body=data,
                        content_type="audio/mpeg",
                        headers={
                            **CORS_HEADERS,
                            "Cache-Control": "public, max-age=86400"
                        }
                    )
                else:
                    return web.Response(status=resp.status, text="TTS error", headers=CORS_HEADERS)
    except Exception as e:
        return web.Response(status=500, text=str(e), headers=CORS_HEADERS)

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
    async def root_handler(request):
        return web.Response(text="HANU AI Server 24/7 faol! 🇰🇷🧠", headers=CORS_HEADERS)
    app.router.add_get("/", root_handler)
    
    # Progress API
    app.router.add_options("/api/save-progress", handle_options)
    app.router.add_post("/api/save-progress", handle_progress)
    
    # Leaderboard API (Ilova uchun)
    app.router.add_options("/api/leaderboard", handle_options)
    app.router.add_get("/api/leaderboard", handle_get_leaderboard)
    
    # Reminder API (Ilova va Bot integratsiyasi)
    app.router.add_options("/api/set-reminder", handle_options)
    app.router.add_post("/api/set-reminder", handle_set_reminder)
    app.router.add_options("/api/get-reminder", handle_options)
    app.router.add_get("/api/get-reminder", handle_get_reminder)
    
    # TTS Audio API
    app.router.add_options("/api/tts", handle_options)
    app.router.add_get("/api/tts", handle_tts)
    
    # AI check
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
    # Har bir foydalanuvchining shaxsiy vaqtiga qarab eslatma yuboruvchi jarayon
    asyncio.create_task(personalized_reminder_scheduler())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

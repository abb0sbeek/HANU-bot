import asyncio
import os
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# 1. @BotFather bergan tokenni qo'ying:
BOT_TOKEN = "8642381123:AAGT8HWcURijPXZaYfxYjH5IqBIdct7p6tE"

# 2. Netlify havolangizni qo'ying:
WEB_APP_URL = "https://chipper-banoffee-145251.netlify.app/"

# 3. O'zingizning Telegram username'ingizni qo'ying:
ADMIN_TELEGRAM_LINK = "https://t.me/abb0sbeek"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
user_joined_dates = {}

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

@dp.message(CommandStart())
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_joined_dates:
        user_joined_dates[user_id] = datetime.now().strftime("%d.%m.%Y")
        
    ism = message.from_user.first_name or "Do'stim"
    xabar = (
        f"Assalomu alaykum, <b>{ism}</b>!\n\n"
        "🇰🇷 <b>HANU</b> koreys tili platformasiga xush kelibsiz.\n\n"
        "Platformada darslarni boshlash uchun <b>«🚀 Darsni boshlash»</b> tugmasini bosing 👇"
    )
    await message.answer(xabar, reply_markup=get_main_keyboard(), parse_mode="HTML")

@dp.callback_query(F.data == "my_profile")
async def profile_handler(callback: types.CallbackQuery):
    user = callback.from_user
    ism = user.first_name or "Do'stim"
    username = f"@{user.username}" if user.username else "Mavjud emas"
    joined_date = user_joined_dates.get(user.id, datetime.now().strftime("%d.%m.%Y"))
    
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

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_handler(callback: types.CallbackQuery):
    ism = callback.from_user.first_name or "Do'stim"
    xabar = (
        f"Assalomu alaykum, <b>{ism}</b>!\n\n"
        "🇰🇷 <b>HANU</b> koreys tili platformasiga xush kelibsiz.\n\n"
        "Platformada darslarni boshlash uchun <b>«🚀 Darsni boshlash»</b> tugmasini bosing 👇"
    )
    await callback.message.edit_text(xabar, reply_markup=get_main_keyboard(), parse_mode="HTML")
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

import asyncio
import re
import shutil
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

# ================= SOZLAMALAR =================
TOKEN = "8604995011:AAGvSRXRysm5T4TIq8YZrwWnrnc9XxtFEmo"
ADMIN_ID = 8201674543  # O'zingizning Telegram ID raqamingiz
DONATION_INTERVAL = 3

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Ma'lumotlar bazasi (Vaqtinchalik xotirada, keyinchalik SQLite/PostgreSQL'ga ulashingiz mumkin)
users_db = set()
user_checks = {}

# --- YORDAMCHI FUNKSIYALAR ---

async def normalize_domain(domain: str) -> str:
    """Domenni tozalash va .uz variantiga aylantirish."""
    raw = domain.strip().lower()
    raw = re.sub(r'^https?://', '', raw)
    raw = re.sub(r'^www\.', '', raw)
    raw = raw.split('/')[0].strip('. ')

    if not raw:
        return ""

    if raw.endswith('.uz'):
        return raw

    if re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", raw):
        return raw + '.uz'

    return raw


async def check_whois(domain: str) -> dict:
    """Domen ma'lumotlarini .uz whois-serveri orqali tekshirish."""
    domain = (await normalize_domain(domain)).strip().lower()
    if not domain:
        return {"status": "error", "message": "empty_domain"}

    if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)*\.uz", domain):
        return {"status": "error", "message": "invalid_domain"}

    try:
        if shutil.which("whois"):
            process = await asyncio.create_subprocess_exec(
                'whois', domain,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            result = stdout.decode('utf-8', 'replace')
        else:
            reader, writer = await asyncio.open_connection('whois.cctld.uz', 43)
            writer.write((domain + '\r\n').encode('utf-8'))
            await writer.drain()

            chunks = []
            while True:
                data = await reader.read(4096)
                if not data:
                    break
                chunks.append(data)

            writer.close()
            await writer.wait_closed()
            result = b''.join(chunks).decode('utf-8', 'replace')

        lower_result = result.lower()
        if (
            'not found in database' in lower_result
            or 'no entries found' in lower_result
            or 'no match' in lower_result
            or 'domain not found' in lower_result
            or 'not found' in lower_result and 'domain' in lower_result
        ):
            return {"status": "free", "domain": domain}

        org_name = re.search(r'Organization:\s+(.+)', result, re.IGNORECASE)
        org_name = org_name or re.search(r'Registrant\s*:\s*(.+)', result, re.IGNORECASE)
        creation_date = re.search(r'Creation Date:\s+(.+)', result, re.IGNORECASE)
        expiration_date = re.search(r'Expiration Date:\s+(.+)', result, re.IGNORECASE)

        return {
            "status": "taken",
            "domain": domain,
            "org": org_name.group(1).strip() if org_name else "Маълумот яширилган",
            "created": creation_date.group(1).split()[0] if creation_date else "-",
            "expires": expiration_date.group(1).split()[0] if expiration_date else "-",
        }
    except Exception:
        return {"status": "error", "message": "whois_failed"}

def get_donation_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="☕️ Kofe olib berish (Payme/Click)", url="https://myurls.co/sizning_karta_havolangiz")]
    ])

def get_register_keyboard():
    # Ro'yxatdan o'tish uchun provayderlar tugmalari
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="aHOST ↗️", url="https://ahost.uz"),
            InlineKeyboardButton(text="Webname ↗️", url="https://webname.uz"),
            InlineKeyboardButton(text="Airnet ↗️", url="https://airnet.uz")
        ]
    ])

# --- BOT HANDLERLARI ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    users_db.add(message.from_user.id)
    text = (
        f"✋ Assalomu alaykum <b>{message.from_user.first_name}</b>\n"
        "✍️ Menga biror domen nomini yuboring! Sizga tekshirib beraman. Namuna:\n\n"
        "<i>shift.uz, 😃.uz, domen.uz</i>\n\n"
        "🌐 Tizim hozircha faqat <b>.uz</b> domenlarini qo'llab-quvvatlaydi."
    )
    await message.answer(text)

@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return

    total_users = len(users_db)
    total_checks = sum(user_checks.values())

    text = (
        "👑 <b>Admin Panel</b>\n\n"
        f"👥 Umumiy foydalanuvchilar: <b>{total_users}</b> ta\n"
        f"🔍 Jami domen tekshiruvlari: <b>{total_checks}</b> marta\n\n"
        "<i>Foydalanuvchilarga xabar yuborish uchun funksiyani shu yerga qo'shishingiz mumkin.</i>"
    )
    await message.answer(text)

@dp.message(F.text)
async def process_domain(message: types.Message):
    user_id = message.from_user.id
    users_db.add(user_id)

    domain_query = message.text.strip()
    normalized_domain = await normalize_domain(domain_query)

    if not normalized_domain:
        await message.answer("⚠️ Iltimos, domen nomini kiriting. Masalan: <b>shah.com</b> yoki <b>shift.uz</b>")
        return

    if not re.fullmatch(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", normalized_domain.replace('.uz', '')):
        await message.answer("⚠️ Noto'g'ri domen formati. Masalan: <b>shah.com</b> yoki <b>shift.uz</b>")
        return

    user_checks[user_id] = user_checks.get(user_id, 0) + 1

    checking_msg = await message.answer("⏳ <i>Tekshirilmoqda...</i>")
    domain_info = await check_whois(normalized_domain)
    await checking_msg.delete()

    if domain_info["status"] == "free":
        text = (
            f"🌐 <b>{domain_info['domain']}</b> — Domen bo'sh\n\n"
            "🔖 Ro'yxatdan o'tkazish mumkin!\n"
            "ℹ️ Auksionga chiqmagan"
        )
        await message.answer(text, reply_markup=get_register_keyboard())

    elif domain_info["status"] == "taken":
        text = (
            f"🌐 <b>{domain_info['domain']}</b> — Domen band\n\n"
            "🔖 Aktiv\n"
            f"📅 {domain_info['created']} - 🕞 {domain_info['expires']}\n"
            f"💼 Yuridik/Jismoniy shaxs: {domain_info['org']}\n"
            "🚫 Kontakt ma'lumotlari yo'q\n"
            "📍 O'zbekiston"
        )
        monitor_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔔 Bo'shashini kuzatish", callback_data="monitor_domain")]
        ])
        await message.answer(text, reply_markup=monitor_kb)

    else:
        await message.answer("⛔️ Xatolik yuz berdi. Domenni qayta tekshirib ko'ring.")

    # Donat so'rovini yuborish mantiqi
    if user_checks[user_id] % DONATION_INTERVAL == 0:
        donation_text = (
            "💡 **Botimiz ishingizni yengillashtiryaptimi?**\n\n"
            "Ushbu loyiha sizga foyda keltirayotgan bo'lsa, uni yanada rivojlantirishimiz va xarajatlarini qoplashimiz uchun "
            "bizga **bir piyola qahva** sovg'a qilib qo'llab-quvvatlashingiz mumkin! ☕️🚀\n\n"
            "*Kichik e'tiboringiz ham biz uchun juda qadrli.*"
        )
        # Asosiy xabarni o'qib olishi uchun kichik pauza
        await asyncio.sleep(1.5) 
        await message.answer(donation_text, reply_markup=get_donation_keyboard())

# --- ISHGA TUSHIRISH ---
async def main():
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
"""
Telegram Bot - المنظومة المتكاملة (v3.0)
دعم كامل للأكواد الديناميكية من Supabase
"""

import os
import asyncio
import logging
import httpx
import traceback
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.types import User
from supabase import create_client, Client

# ─────────────────────────────────────────────
#  إعداد اللوغ والمتغيرات
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

API_ID       = int(os.environ["API_ID"])
API_HASH     = os.environ["API_HASH"]
BOT_TOKEN    = os.environ["BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
OPENAI_KEY   = os.environ["OPENAI_KEY"]

bot: TelegramClient = TelegramClient("bot_session", API_ID, API_HASH)
supabase: Client    = create_client(SUPABASE_URL, SUPABASE_KEY)

user_states: dict[int, str | None] = {}
editing_button: dict[int, str | None] = {}

STATES = {
    "accounts":    "🏭 مصنع الجيوش",
    "tactical":    "🚀 الهجوم التكتيكي",
    "ai_analysis": "🧠 مختبر AI",
    "protection":  "🛡️ درع الحماية",
    "live_stats":  "📊 الإحصائيات الحية",
    "settings":    "⚙️ الإعدادات",
}

MAIN_BUTTONS = [
    [Button.inline("🏭 مصنع الجيوش", b"accounts"), Button.inline("🚀 الهجوم التكتيكي", b"tactical")],
    [Button.inline("🧠 مختبر AI", b"ai_analysis"), Button.inline("🛡️ درع الحماية", b"protection")],
    [Button.inline("📊 الإحصائيات الحية", b"live_stats"), Button.inline("⚙️ الإعدادات", b"settings")],
]

BACK_BUTTON = [[Button.inline("🔙 رجوع للقائمة الرئيسية", b"main_menu")]]

# ─────────────────────────────────────────────
#  محرك الأكواد الديناميكي (إضافة التعديلة)
# ─────────────────────────────────────────────
async def run_dynamic_code(event, button_name):
    try:
        res = supabase.table("dynamic_commands").select("python_code").eq("button_name", button_name).execute()
        if res.data and res.data[0]['python_code']:
            code = res.data[0]['python_code']
            # تنفيذ الكود برمجياً في بيئة البوت
            exec_globals = {'event': event, 'bot': bot, 'Button': Button, 'supabase': supabase, 'asyncio': asyncio}
            exec_code = f"async def _ex(event, bot, Button, supabase):\n" + "".join([f"    {line}\n" for line in code.split('\n')])
            exec(exec_code, exec_globals)
            await exec_globals['_ex'](event, bot, Button, supabase)
            return True # تم التنفيذ بنجاح
        return False # لا يوجد كود
    except Exception as e:
        await event.respond(f"❌ خطأ في تنفيذ الكود الديناميكي:\n`{e}`")
        return True

# ─────────────────────────────────────────────
#  مساعدات Supabase و OpenAI
# ─────────────────────────────────────────────
def db_upsert_user(user_id: int, username: str | None, full_name: str) -> None:
    try:
        supabase.table("users").upsert({"user_id": user_id, "username": username or "", "full_name": full_name, "last_seen": datetime.utcnow().isoformat()}, on_conflict="user_id").execute()
    except Exception as exc: log.error("Supabase upsert error: %s", exc)

def db_log_message(user_id: int, section: str, message: str, response: str) -> None:
    try:
        supabase.table("ai_logs").insert({"user_id": user_id, "section": section, "message": message, "response": response, "timestamp": datetime.utcnow().isoformat()}).execute()
    except Exception as exc: log.error("Supabase log error: %s", exc)

def db_get_user_stats(user_id: int) -> dict:
    try:
        result = supabase.table("ai_logs").select("id", count="exact").eq("user_id", user_id).execute()
        return {"total_queries": result.count or 0}
    except Exception: return {"total_queries": 0}

async def ask_ai(user_id: int, question: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}, json={"model": "gpt-4o-mini", "messages": [{"role": "system", "content": "أنت مساعد ذكي محترف بلهجة عراقية."}, {"role": "user", "content": question}]})
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception: return "🔴 مشكلة بالذكاء الاصطناعي."

def get_display_name(sender: User) -> str:
    return " ".join([p for p in [sender.first_name or "", sender.last_name or ""] if p]).strip() or "قائد"

# ─────────────────────────────────────────────
#  معالجة الأحداث (Handlers)
# ─────────────────────────────────────────────
@bot.on(events.NewMessage(pattern="/start"))
async def cmd_start(event):
    sender = await event.get_sender()
    name = get_display_name(sender)
    db_upsert_user(sender.id, sender.username, name)
    user_states[sender.id] = None
    await event.respond(f"⚡ **أهلاً بك يا قائد {name} في المنظومة** ⚡\n\nاختر القطاع:", buttons=MAIN_BUTTONS)

@bot.on(events.CallbackQuery())
async def callback_handler(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "main_menu":
        user_states[uid] = None
        await event.edit("اختر القطاع المطلوب 👇", buttons=MAIN_BUTTONS)
        return

    # تشغيل المحرك الديناميكي أولاً
    if await run_dynamic_code(event, data):
        return

    # الكود الافتراضي للأزرار إذا لم يوجد كود ديناميكي
        if data == "accounts":
        user_states[uid] = "accounts"
        # هذه القائمة هي اللي راح تظهر لك الـ 150 زر بالتدريج
        btns = [
            [Button.inline("🤖 نظام التوليد الآلي", b"auto_gen"), 
             Button.inline("📂 إدارة الجيوش", b"army_view")],
            [Button.inline("⏳ غرفة التخمير", b"incubation"), 
             Button.inline("🎭 محرك الهوية", b"identity_engine")],
            [Button.inline("⚙️ إضافة/تعديل كود", b"edit_mode")],
            [Button.inline("🔙 رجوع للقائمة الرئيسية", b"main_menu")]
        ]
        await event.edit(
            "🏭 **قطاع مصنع الجيوش والحسابات**\n\n"
            "مرحباً بك في وحدة التحكم.\n"
            "الأنظمة: 7 | الجداول: 8\n\n"
            "اختر النظام المطلوب أو اضغط 'تعديل كود' لبرمجة زر معين:", 
            buttons=btns 
        (
    elif data == "edit_mode":
        editing_button[uid] = "awaiting_id"
        await event.respond("🛡️ **محرر الأكواد**\nأرسل ID الزر (مثلاً `auto_gen`):")

    elif data in ["tactical", "ai_analysis", "protection", "live_stats", "settings"]:
        user_states[uid] = data
        await event.edit(f"القسم: **{STATES[data]}**", buttons=BACK_BUTTON)

@bot.on(events.NewMessage)
async def message_handler(event):
    uid = event.sender_id
    text = event.raw_text
    
    # محرر الأكواد المباشر
    if editing_button.get(uid) == "awaiting_id":
        editing_button[uid] = f"setcode_{text}"
        await event.respond(f"✅ تم اختيار `{text}`. أرسل الآن كود البايثون:")
        return

    if editing_button.get(uid) and editing_button[uid].startswith("setcode_"):
        btn_id = editing_button[uid].replace("setcode_", "")
        supabase.table("dynamic_commands").upsert({"button_name": btn_id, "python_code": text}).execute()
        await event.respond(f"🚀 تم تحديث الزر `{btn_id}` بنجاح!")
        editing_button[uid] = None
        return

    # معالجة AI Analysis الأصلية
    if user_states.get(uid) == "ai_analysis" and not text.startswith('/'):
        thinking = await event.respond("⏳ جاري التحليل...")
        answer = await ask_ai(uid, text)
        await thinking.delete()
        await event.respond(f"🤖 **النتيجة:**\n\n{answer}", buttons=BACK_BUTTON)

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

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
#  إعدادات النظام والبيئة
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

# ─────────────────────────────────────────────
#  تعريف القطاعات والأزرار (المخطط الشامل)
# ─────────────────────────────────────────────
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
#  محرك الأكواد الديناميكي (التنفيذ اللحظي)
# ─────────────────────────────────────────────
async def run_dynamic_code(event, button_name):
    try:
        res = supabase.table("dynamic_commands").select("python_code").eq("button_name", button_name).execute()
        if res.data and res.data[0]['python_code']:
            code = res.data[0]['python_code']
            exec_globals = {
                'event': event, 'bot': bot, 'Button': Button, 
                'supabase': supabase, 'asyncio': asyncio, 'datetime': datetime
            }
            # تحويل النص إلى دالة قابلة للتنفيذ بأسلوب نظيف
            indented_code = "\n".join([f"    {line}" for line in code.split('\n')])
            exec_code = f"async def _ex(event, bot, Button, supabase):\n{indented_code}"
            exec(exec_code, exec_globals)
            await exec_globals['_ex'](event, bot, Button, supabase)
            return True
        return False
    except Exception as e:
        await event.respond(f"❌ **خطأ في الكود الديناميكي:**\n`{str(e)}`")
        return True

# ─────────────────────────────────────────────
#  مساعدات البيانات والذكاء الاصطناعي
# ─────────────────────────────────────────────
def db_upsert_user(user_id, username, full_name):
    try:
        supabase.table("users").upsert({
            "user_id": user_id, "username": username or "", 
            "full_name": full_name, "last_seen": datetime.utcnow().isoformat()
        }, on_conflict="user_id").execute()
    except: pass

async def ask_ai(question):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "system", "content": "أنت مساعد ذكي عراقي محترف."}, {"role": "user", "content": question}]
                }
            )
            return resp.json()["choices"][0]["message"]["content"].strip()
    except: return "🔴 عذراً قائد، العقل المركزي مشغول."

# ─────────────────────────────────────────────
#  مستقبل الأوامر والضغطات (Handlers)
# ─────────────────────────────────────────────
@bot.on(events.NewMessage(pattern="/start"))
async def cmd_start(event):
    sender = await event.get_sender()
    name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "قائد"
    db_upsert_user(sender.id, sender.username, name)
    user_states[sender.id] = None
    await event.respond(f"⚡ **المنظومة تحت أمرك يا قائد {name}** ⚡\n\nاختر القطاع المطلوب للتنفيذ:", buttons=MAIN_BUTTONS)

@bot.on(events.CallbackQuery())
async def callback_handler(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "main_menu":
        user_states[uid] = None
        return await event.edit("اختر القطاع المطلوب 👇", buttons=MAIN_BUTTONS)

    # 1. فحص المحرك الديناميكي أولاً (إذا برمجت الزر من داخل البوت يشتغل فوراً)
    if await run_dynamic_code(event, data):
        return

    # 2. القوائم الافتراضية للقطاعات الستة
    if data == "accounts":
        user_states[uid] = "accounts"
        btns = [
            [Button.inline("🤖 نظام التوليد", b"auto_gen"), Button.inline("📂 إدارة الجيوش", b"army_view")],
            [Button.inline("⏳ غرفة التخمير", b"incubation"), Button.inline("🎭 محرك الهوية", b"identity_engine")],
            [Button.inline("⚙️ إضافة/تعديل كود", b"edit_mode"), Button.inline("🔙 رجوع", b"main_menu")]
        ]
        await event.edit("🏭 **قطاع مصنع الجيوش والحسابات**\nاختر الوظيفة أو برمج زر جديد:", buttons=btns)

    elif data == "tactical":
        user_states[uid] = "tactical"
        btns = [
            [Button.inline("🎯 هجوم استراتيجي", b"strat_atk"), Button.inline("📡 قصف إعلامي", b"media_atk")],
            [Button.inline("⚙️ إضافة/تعديل كود", b"edit_mode"), Button.inline("🔙 رجوع", b"main_menu")]
        ]
        await event.edit("🚀 **قطاع الهجوم التكتيكي**\nجاهز للعمليات الكبرى:", buttons=btns)

    elif data == "ai_analysis":
        user_states[uid] = "ai_analysis"
        await event.edit("🧠 **مختبر الذكاء الاصطناعي**\nأرسل فكرتك الآن وسأحللها لك برمجياً..", buttons=BACK_BUTTON)

    elif data == "protection":
        user_states[uid] = "protection"
        btns = [[Button.inline("🛡️ فحص الاختراق", b"scan"), Button.inline("⚙️ تعديل", b"edit_mode")], [Button.inline("🔙 رجوع", b"main_menu")]]
        await event.edit("🛡️ **قطاع درع الحماية**\nالأمن السيبراني للمنظومة مستقر.", buttons=btns)

    elif data == "edit_mode":
        editing_button[uid] = "awaiting_id"
        await event.respond("🛡️ **محرر المنظومة الذكي**\nأرسل ID الزر الذي تريد برمجته (مثال: `auto_gen` أو `strat_atk`):")

@bot.on(events.NewMessage)
async def message_handler(event):
    uid = event.sender_id
    text = event.raw_text
    if not text or text.startswith('/'): return

    # نظام البرمجة من داخل البوت
    if editing_button.get(uid) == "awaiting_id":
        editing_button[uid] = f"set_{text}"
        await event.respond(f"✅ تم اختيار `{text}`\nأرسل الآن كود بايثون التنفيذي لهذا الزر:")
        return

    if editing_button.get(uid) and editing_button[uid].startswith("set_"):
        btn_id = editing_button[uid].replace("set_", "")
        supabase.table("dynamic_commands").upsert({"button_name": btn_id, "python_code": text}).execute()
        await event.respond(f"🚀 **تم حقن الكود بنجاح!**\nالزر `{btn_id}` جاهز للعمل الآن.")
        editing_button[uid] = None
        return

    # الردود الذكية في مختبر AI
    if user_states.get(uid) == "ai_analysis":
        msg = await event.respond("⏳ جاري المعالجة...")
        ans = await ask_ai(text)
        await msg.delete()
        await event.respond(f"🤖 **تحليل العقل المركزي:**\n\n{ans}", buttons=BACK_BUTTON)

async def main():
    await bot.start(bot_token=BOT_TOKEN)
    log.info("✅ المنظومة تعمل بكامل طاقتها!")
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

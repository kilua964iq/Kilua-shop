"""
Telegram Bot - Telethon + Supabase + OpenAI (GPT-4o-Mini)
مستضاف على Railway | ردود بلهجة عراقية احترافية
المنظومة المتكاملة - الإصدار المحدث
"""

import os
import asyncio
import logging
import httpx
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.types import User
from supabase import create_client, Client

# ─────────────────────────────────────────────
#  إعداد اللوغ
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────
#  المتغيرات البيئية
# ─────────────────────────────────────────────
API_ID       = int(os.environ["API_ID"])
API_HASH     = os.environ["API_HASH"]
BOT_TOKEN    = os.environ["BOT_TOKEN"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
OPENAI_KEY   = os.environ["OPENAI_KEY"]

# ─────────────────────────────────────────────
#  تهيئة العملاء
# ─────────────────────────────────────────────
bot: TelegramClient = TelegramClient("bot_session", API_ID, API_HASH)
supabase: Client    = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─────────────────────────────────────────────
#  نظام الحالات (States)
# ─────────────────────────────────────────────
user_states: dict[int, str | None] = {}

STATES = {
    "accounts":    "🏭 مصنع الجيوش",
    "tactical":    "🚀 الهجوم التكتيكي",
    "ai_analysis": "🧠 مختبر AI",
    "protection":  "🛡️ درع الحماية",
    "live_stats":  "📊 الإحصائيات الحية",
    "settings":    "⚙️ الإعدادات",
}

# ─────────────────────────────────────────────
#  الأزرار الرئيسية (الواجهة السداسية الكاملة)
# ─────────────────────────────────────────────
MAIN_BUTTONS = [
    [Button.inline("🏭 مصنع الجيوش",    b"accounts"),
     Button.inline("🚀 الهجوم التكتيكي", b"tactical")],
    [Button.inline("🧠 مختبر AI",     b"ai_analysis"),
     Button.inline("🛡️ درع الحماية",      b"protection")],
    [Button.inline("📊 الإحصائيات الحية", b"live_stats"),
     Button.inline("⚙️ الإعدادات",      b"settings")],
]

BACK_BUTTON = [[Button.inline("🔙 رجوع للقائمة الرئيسية", b"main_menu")]]

# ─────────────────────────────────────────────
#  مساعدات Supabase
# ─────────────────────────────────────────────
def db_upsert_user(user_id: int, username: str | None, full_name: str) -> None:
    try:
        supabase.table("users").upsert(
            {
                "user_id":    user_id,
                "username":   username or "",
                "full_name":  full_name,
                "last_seen":  datetime.utcnow().isoformat(),
            },
            on_conflict="user_id",
        ).execute()
    except Exception as exc:
        log.error("Supabase upsert error: %s", exc)

def db_log_message(user_id: int, section: str, message: str, response: str) -> None:
    try:
        supabase.table("ai_logs").insert(
            {
                "user_id":   user_id,
                "section":   section,
                "message":   message,
                "response":  response,
                "timestamp": datetime.utcnow().isoformat(),
            }
        ).execute()
    except Exception as exc:
        log.error("Supabase log error: %s", exc)

def db_get_user_stats(user_id: int) -> dict:
    try:
        result = (
            supabase.table("ai_logs")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .execute()
        )
        return {"total_queries": result.count or 0}
    except Exception:
        return {"total_queries": 0}

# ─────────────────────────────────────────────
#  دالة ask_ai – محرك OpenAI المستقر
# ─────────────────────────────────────────────
async def ask_ai(user_id: int, question: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENAI_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "أنت مساعد ذكي محترف في المنظومة. تجاوب دائماً بلهجة عراقية احترافية وودية. كن دقيقاً ومفيداً."},
                        {"role": "user", "content": question}
                    ],
                }
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        log.error("OpenAI error for user %s: %s", user_id, exc)
        return "🔴 ما قدرت أوصل للعقل المركزي حالياً، حاول بعد شوية يا قائد."

# ─────────────────────────────────────────────
#  مساعد: بناء اسم المستخدم
# ─────────────────────────────────────────────
def get_display_name(sender: User) -> str:
    parts = [sender.first_name or "", sender.last_name or ""]
    return " ".join(p for p in parts if p).strip() or "قائد"

# ─────────────────────────────────────────────
#  أوامر البوت
# ─────────────────────────────────────────────
@bot.on(events.NewMessage(pattern="/start"))
async def cmd_start(event: events.NewMessage.Event) -> None:
    sender: User = await event.get_sender()
    uid  = sender.id
    name = get_display_name(sender)
    db_upsert_user(uid, sender.username, name)
    user_states[uid] = None
    welcome = (
        f"⚡ **أهلاً بك يا قائد {name} في المنظومة** ⚡\n\n"
        "الحالة: مستقرة ✅\n"
        "الاتصال: سوبابيز + ذكاء اصطناعي ✅\n\n"
        "اختر القطاع المطلوب من الأزرار أدناه:"
    )
    await event.respond(welcome, buttons=MAIN_BUTTONS)
    raise events.StopPropagation

@bot.on(events.NewMessage(pattern="/status"))
async def cmd_status(event: events.NewMessage.Event) -> None:
    uid   = event.sender_id
    state = user_states.get(uid)
    stats = db_get_user_stats(uid)
    state_label = STATES.get(state, "بدون قسم محدد") if state else "بدون قسم محدد"
    text = (
        "📊 **إحصائيات المنظومة:**\n\n"
        f"• القسم الحالي: `{state_label}`\n"
        f"• مجموع العمليات: `{stats['total_queries']}`\n"
    )
    await event.respond(text, buttons=BACK_BUTTON)
    raise events.StopPropagation

@bot.on(events.CallbackQuery())
async def callback_handler(event: events.CallbackQuery.Event) -> None:
    uid  = event.sender_id
    data = event.data.decode()

    if data == "main_menu":
        user_states[uid] = None
        await event.edit("اختر القطاع المطلوب 👇", buttons=MAIN_BUTTONS)
        return

        if data == "accounts":
        user_states[uid] = "accounts"
        # هذه الأزرار هي حجر الأساس للأنظمة الـ 7 في هذا القطاع
        buttons = [
            [Button.inline("🤖 نظام التوليد الآلي", b"factory_gen"), 
             Button.inline("📂 إدارة الجيوش", b"army_control")],
            [Button.inline("⏳ غرفة التخمير (48h)", b"incubation"), 
             Button.inline("🎭 محرك الهوية", b"identity_engine")],
            [Button.inline("🧹 تنظيف وتصفية", b"army_clean"),
             Button.inline("🔙 رجوع للقائمة الرئيسية", b"main_menu")]
        ]
        await event.edit(
            "🏭 **قطاع المصنع والحسابات**\n\n"
            "مرحباً بك في وحدة الإنشاء والأتمتة.\n"
            "الأنظمة المتاحة: 7 | الجداول الفعالة: 8\n\n"
            "اختر النظام المطلوب للبدء بالتنفيذ:", 
            buttons=buttons
        )
        return


    if data == "tactical":
        user_states[uid] = "tactical"
        await event.edit("🚀 **الهجوم التكتيكي**\n\nقيد التجهيز للعمليات الكبرى... ⚙️", buttons=BACK_BUTTON)
        return

    if data == "ai_analysis":
        user_states[uid] = "ai_analysis"
        await event.edit("🧠 **مختبر AI**\n\nأرسل فكرتك الآن وسيجيبك العقل المركزي فوراً..", buttons=BACK_BUTTON)
        return

    if data == "protection":
        user_states[uid] = "protection"
        await event.edit("🛡️ **درع الحماية**\n\nنظام حماية البيانات مفعّل وأمن المنظومة مستقر... 🛡️", buttons=BACK_BUTTON)
        return

    if data == "live_stats":
        user_states[uid] = "live_stats"
        stats = db_get_user_stats(uid)
        await event.edit(f"📊 **الإحصائيات الحية**\n\nإجمالي عملياتك: `{stats['total_queries']}`\nسيتم إضافة المزيد من البيانات قريباً.", buttons=BACK_BUTTON)
        return

    if data == "settings":
        user_states[uid] = "settings"
        await event.edit("⚙️ **الإعدادات**\n\nتخصيص المنظومة وتعديل المفاتيح متاح للمشرفين فقط.", buttons=BACK_BUTTON)
        return

@bot.on(events.NewMessage(func=lambda e: e.is_private and not e.via_bot_id))
async def message_handler(event: events.NewMessage.Event) -> None:
    uid  = event.sender_id
    text = (event.raw_text or "").strip()
    if not text or text.startswith("/"): return

    state = user_states.get(uid)
    if state == "ai_analysis":
        thinking_msg = await event.respond("⏳ جاري جلب الرد من العقل المركزي...")
        answer = await ask_ai(uid, text)
        db_log_message(uid, "ai_analysis", text, answer)
        await thinking_msg.delete()
        await event.respond(f"🤖 **النتيجة من مختبر AI:**\n\n{answer}", buttons=BACK_BUTTON)
        return

    if state is None:
        await event.respond("اختر قطاعاً من المنظومة للبدء 👇", buttons=MAIN_BUTTONS)
    else:
        await event.respond(f"أنت داخل قطاع **{STATES.get(state)}**.\nللذكاء الاصطناعي، انتقل لـ 🧠 مختبر AI.", buttons=BACK_BUTTON)

async def main() -> None:
    log.info("🚀 المنظومة تعمل بـ GPT-4o...")
    await bot.start(bot_token=BOT_TOKEN)
    await bot.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())

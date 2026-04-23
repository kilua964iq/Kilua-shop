"""
Telegram Bot - Telethon + Supabase + Google Gemini
مستضاف على Railway | ردود بلهجة عراقية احترافية
"""

import os
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, events, Button
from telethon.tl.types import User
from supabase import create_client, Client
import google.generativeai as genai

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
GEMINI_KEY   = os.environ["GEMINI_API_KEY"]

# ─────────────────────────────────────────────
#  تهيئة العملاء
# ─────────────────────────────────────────────
bot: TelegramClient = TelegramClient("bot_session", API_ID, API_HASH)
supabase: Client    = create_client(SUPABASE_URL, SUPABASE_KEY)

genai.configure(api_key=GEMINI_KEY)
gemini_model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=genai.GenerationConfig(
        temperature=0.7,
        max_output_tokens=1024,
    ),
    system_instruction=(
        "أنت مساعد ذكي محترف. تجاوب دائماً بلهجة عراقية احترافية وودية. "
        "كن دقيقاً، مختصراً، ومفيداً. لا تستخدم لغة رسمية جافة."
    ),
)

# ─────────────────────────────────────────────
#  نظام الحالات (States)
# ─────────────────────────────────────────────
# القيم الممكنة: None | "accounts" | "tactical" | "ai_analysis" | "protection"
user_states: dict[int, str | None] = {}

STATES = {
    "accounts":    "📦 إدارة الحسابات",
    "tactical":    "📊 العمليات التكتيكية",
    "ai_analysis": "💡 التحليل الذكي",
    "protection":  "🔐 نظام الحماية",
}

# ─────────────────────────────────────────────
#  الأزرار الرئيسية
# ─────────────────────────────────────────────
MAIN_BUTTONS = [
    [Button.inline("📦 إدارة الحسابات",    b"accounts"),
     Button.inline("📊 العمليات التكتيكية", b"tactical")],
    [Button.inline("💡 التحليل الذكي",     b"ai_analysis"),
     Button.inline("🔐 نظام الحماية",      b"protection")],
]

BACK_BUTTON = [[Button.inline("🔙 رجوع للقائمة الرئيسية", b"main_menu")]]

# ─────────────────────────────────────────────
#  مساعدات Supabase
# ─────────────────────────────────────────────
def db_upsert_user(user_id: int, username: str | None, full_name: str) -> None:
    """يحفظ أو يحدّث بيانات المستخدم في Supabase."""
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
    """يسجّل رسائل التحليل الذكي في Supabase."""
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
    """يجلب إحصائيات المستخدم."""
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
#  دالة ask_ai – القلب النابض للبوت
# ─────────────────────────────────────────────
async def ask_ai(user_id: int, question: str) -> str:
    """
    ترسل السؤال لـ Gemini وتعيد الرد.
    تعمل 24/7 مع معالجة شاملة للأخطاء.
    """
    try:
        loop   = asyncio.get_event_loop()
        # نشغّل الـ API في thread منفصل حتى لا يحجب event loop
        result = await loop.run_in_executor(
            None,
            lambda: gemini_model.generate_content(question),
        )
        answer = result.text.strip() if result.text else "ما قدرت أجيب رد واضح، حاول مرة ثانية."
        return answer

    except genai.types.BlockedPromptException:
        return "⚠️ السؤال محجوب من نظام الأمان. حاول تصيغه بطريقة ثانية."
    except Exception as exc:
        log.error("Gemini error for user %s: %s", user_id, exc)
        return "🔴 صار خطأ بالاتصال مع الذكاء الاصطناعي. اصبر شوية وحاول ثانية."

# ─────────────────────────────────────────────
#  مساعد: بناء اسم المستخدم
# ─────────────────────────────────────────────
def get_display_name(sender: User) -> str:
    parts = [sender.first_name or "", sender.last_name or ""]
    return " ".join(p for p in parts if p).strip() or "صديقي"

# ─────────────────────────────────────────────
#  أوامر البوت
# ─────────────────────────────────────────────
@bot.on(events.NewMessage(pattern="/start"))
async def cmd_start(event: events.NewMessage.Event) -> None:
    sender: User = await event.get_sender()
    uid  = sender.id
    name = get_display_name(sender)

    # تسجيل المستخدم في Supabase
    db_upsert_user(uid, sender.username, name)

    # تصفير الحالة
    user_states[uid] = None

    welcome = (
        f"أهلاً وسهلاً بيك يا **{name}** 👋\n\n"
        "أنا بوتك الذكي جاهز يخدمك على طول 🚀\n"
        "اختار القسم اللي تريده من الأزرار أدناه:"
    )
    await event.respond(welcome, buttons=MAIN_BUTTONS)
    raise events.StopPropagation


@bot.on(events.NewMessage(pattern="/help"))
async def cmd_help(event: events.NewMessage.Event) -> None:
    text = (
        "📖 **دليل الاستخدام**\n\n"
        "• `/start` – تشغيل البوت والقائمة الرئيسية\n"
        "• `/status` – حالتك الحالية والإحصائيات\n"
        "• `/reset` – رجوع للقائمة الرئيسية\n\n"
        "للتحليل الذكي: ادخل قسم 💡 وابدأ بالكلام!"
    )
    await event.respond(text, buttons=BACK_BUTTON)
    raise events.StopPropagation


@bot.on(events.NewMessage(pattern="/status"))
async def cmd_status(event: events.NewMessage.Event) -> None:
    uid   = event.sender_id
    state = user_states.get(uid)
    stats = db_get_user_stats(uid)

    state_label = STATES.get(state, "بدون قسم محدد") if state else "بدون قسم محدد"
    text = (
        "📊 **حالتك الحالية:**\n\n"
        f"• القسم: `{state_label}`\n"
        f"• مجموع استفساراتك للـ AI: `{stats['total_queries']}`\n"
    )
    await event.respond(text, buttons=BACK_BUTTON)
    raise events.StopPropagation


@bot.on(events.NewMessage(pattern="/reset"))
async def cmd_reset(event: events.NewMessage.Event) -> None:
    uid = event.sender_id
    user_states[uid] = None
    await event.respond("🔄 رجعنا للقائمة الرئيسية:", buttons=MAIN_BUTTONS)
    raise events.StopPropagation

# ─────────────────────────────────────────────
#  معالج الأزرار (Callbacks)
# ─────────────────────────────────────────────
@bot.on(events.CallbackQuery())
async def callback_handler(event: events.CallbackQuery.Event) -> None:
    uid  = event.sender_id
    data = event.data.decode()

    # ── رجوع للقائمة الرئيسية ──────────────────
    if data == "main_menu":
        user_states[uid] = None
        await event.edit(
            "اختار القسم اللي تريده 👇",
            buttons=MAIN_BUTTONS,
        )
        return

    # ── إدارة الحسابات ─────────────────────────
    if data == "accounts":
        user_states[uid] = "accounts"
        text = (
            "📦 **إدارة الحسابات**\n\n"
            "من هنا تقدر تدير حساباتك وتتابع كل التفاصيل.\n"
            "الميزات قريباً... 🔧"
        )
        await event.edit(text, buttons=BACK_BUTTON)
        return

    # ── العمليات التكتيكية ──────────────────────
    if data == "tactical":
        user_states[uid] = "tactical"
        text = (
            "📊 **العمليات التكتيكية**\n\n"
            "هنا تلاقي كل العمليات والإحصائيات التكتيكية.\n"
            "الميزات قريباً... ⚙️"
        )
        await event.edit(text, buttons=BACK_BUTTON)
        return

    # ── التحليل الذكي ───────────────────────────
    if data == "ai_analysis":
        user_states[uid] = "ai_analysis"
        text = (
            "💡 **التحليل الذكي**\n\n"
            "هلا! وصلت للقسم الذكي 🤖\n"
            "اكتب سؤالك أو استفسارك وأنا أجاوبك على طول.\n\n"
            "_(الرسائل هنا تنحل عن طريق Gemini AI)_"
        )
        await event.edit(text, buttons=BACK_BUTTON)
        return

    # ── نظام الحماية ────────────────────────────
    if data == "protection":
        user_states[uid] = "protection"
        text = (
            "🔐 **نظام الحماية**\n\n"
            "هنا تتحكم بإعدادات الأمان وحماية حسابك.\n"
            "الميزات قريباً... 🛡️"
        )
        await event.edit(text, buttons=BACK_BUTTON)
        return

    await event.answer("⚠️ أمر غير معروف.", alert=True)

# ─────────────────────────────────────────────
#  معالج الرسائل النصية
# ─────────────────────────────────────────────
@bot.on(events.NewMessage(func=lambda e: e.is_private and not e.via_bot_id))
async def message_handler(event: events.NewMessage.Event) -> None:
    uid  = event.sender_id
    text = (event.raw_text or "").strip()

    # تجاهل الأوامر (معالجتها فوق)
    if not text or text.startswith("/"):
        return

    state = user_states.get(uid)

    # ─── داخل التحليل الذكي: أرسل لـ Gemini ────
    if state == "ai_analysis":
        thinking_msg = await event.respond("⏳ أفكر بسؤالك...")

        answer = await ask_ai(uid, text)

        # تسجيل في Supabase
        db_log_message(uid, "ai_analysis", text, answer)

        # حذف رسالة "أفكر" وإرسال الجواب
        await thinking_msg.delete()
        await event.respond(
            f"🤖 **الجواب:**\n\n{answer}",
            buttons=BACK_BUTTON,
        )
        return

    # ─── خارج التحليل الذكي ─────────────────────
    if state is None:
        await event.respond(
            "اختار قسم من القائمة أول 👇",
            buttons=MAIN_BUTTONS,
        )
    else:
        section_name = STATES.get(state, state)
        await event.respond(
            f"أنت داخل قسم **{section_name}**.\n"
            "إذا تريد تستخدم الذكاء الاصطناعي، انتقل لقسم 💡 التحليل الذكي.",
            buttons=BACK_BUTTON,
        )

# ─────────────────────────────────────────────
#  نقطة الانطلاق
# ─────────────────────────────────────────────
async def main() -> None:
    log.info("🚀 البوت يشتغل...")
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    log.info("✅ اتصلنا كـ @%s", me.username)
    await bot.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())

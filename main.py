import os
import asyncio
import requests
from telethon import TelegramClient, events, Button
from supabase import create_client, Client

# --- تحميل الإعدادات من Variables (البيئة) ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

# --- تهيئة الاتصالات ---
# ربط المخ (Supabase)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ربط الجسم (Telegram Bot)
client = TelegramClient('Mustafa_Session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- محرك الذكاء الاصطناعي (العقل) ---
def ask_ai(prompt):
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"أنت خبير تقني وتسويقي عراقي ذكي جداً. أجب بذكاء ولهجة مفهومة عن: {prompt}",
        "parameters": {"max_new_tokens": 500, "return_full_text": False}
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        output = response.json()
        return output[0]['generated_text']
    except:
        return "⚠️ فشل الاتصال بالعقل المركزي، تأكد من توكن Hugging Face."

# --- الواجهة الرئيسية ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.inline("🏭 مصنع الجيوش", b"army_factory"), Button.inline("🚀 الهجوم التكتيكي", b"tactical_ops")],
        [Button.inline("🧠 مختبر AI", b"ai_lab"), Button.inline("🛡️ درع الحماية", b"security_shield")],
        [Button.inline("📊 الإحصائيات الحية", b"live_stats"), Button.inline("⚙️ الإعدادات", b"settings")]
    ]
    await event.reply(
        "⚡ **أهلاً بك يا قائد مصطفى في غرفة عمليات أربيل** ⚡\n\n"
        "المنظومة متصلة بالذكاء الاصطناعي و Supabase ✅\n"
        "جاهز لتنفيذ الأوامر:",
        buttons=buttons
    )

# --- معالجة الأزرار والذكاء الاصطناعي ---
@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    
    if data == "ai_lab":
        async with client.conversation(event.chat_id) as conv:
            await event.edit("🧠 **مختبر AI مفعّل..**\nأرسل الآن اسم منتجك أو مشروعك ليقوم الذكاء الاصطناعي بتحليله:")
            user_msg = await conv.get_response()
            waiting = await user_msg.reply("🔄 جاري التفكير في السيرفرات... انتظر لحظة")
            
            # استشارة الذكاء الاصطناعي
            answer = ask_ai(user_msg.text)
            await waiting.edit(f"💡 **رؤية الذكاء الاصطناعي لـ {user_msg.text}:**\n\n{answer}", 
                             buttons=[Button.inline("⬅️ رجوع", b"back_to_main")])

    elif data == "back_to_main":
        await start(event)

    elif data == "army_factory":
        await event.edit("🛠️ **قطاع مصنع الجيوش:**\n(قيد التطوير لربط الحسابات التلقائية)", 
                         buttons=[Button.inline("⬅️ رجوع", b"back_to_main")])

print("🚀 الوحش استيقظ على سيرفرات Railway.. انطلق!")
client.run_until_disconnected()

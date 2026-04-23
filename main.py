import os
import time
import google.generativeai as genai
from telethon import TelegramClient, events, Button
from supabase import create_client, Client

# --- الإعدادات ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY") # المفتاح الجديد

# تهيئة Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# تهيئة السيرفرات الأخرى
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = TelegramClient('Mustafa_Session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

user_states = {}

# --- العقل الجديد (Gemini) - شغال 24 ساعة ---
def ask_ai(prompt):
    try:
        # نظام تعليمات صارم ليفهم الشخصية
        full_prompt = f"أنت خبير تقني وتسويقي عراقي. أجب بلهجة عراقية بيضاء مفهومة واحترافية عن: {prompt}"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return "⚠️ عذراً قائد، واجهت مشكلة في الاتصال بالعقل. تأكد من صلاحية مفتاح Gemini."

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_states[event.chat_id] = None
    buttons = [
        [Button.inline("🏭 مصنع الجيوش", b"army_factory"), Button.inline("🚀 الهجوم التكتيكي", b"tactical_ops")],
        [Button.inline("🧠 مختبر AI", b"ai_lab"), Button.inline("🛡️ درع الحماية", b"security_shield")]
    ]
    await event.reply("⚡ **منظومة أربيل متصلة بعقل Google Gemini**\nالآن الاستجابة فورية 24/7.", buttons=buttons)

@client.on(events.CallbackQuery(data=b"ai_lab"))
async def ai_lab(event):
    user_states[event.chat_id] = "waiting_ai"
    await event.edit("🧠 **مختبر AI فائق السرعة:**\nأرسل فكرتك الآن وسأجيبك بلمح البصر..")

@client.on(events.NewMessage)
async def handle_messages(event):
    if user_states.get(event.chat_id) == "waiting_ai" and not event.text.startswith('/'):
        status = await event.reply("📡 جاري التحليل...")
        answer = ask_ai(event.text)
        user_states[event.chat_id] = None
        await status.edit(f"💡 **النتيجة:**\n\n{answer}", buttons=[Button.inline("⬅️ رجوع", b"back_to_main")])

@client.on(events.CallbackQuery(data=b"back_to_main"))
async def back(event):
    await start(event)

print("🚀 الـ Gemini شغال والوضع مستقر تماماً!")
client.run_until_disconnected()

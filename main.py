import os
import requests
from telethon import TelegramClient, events, Button
from supabase import create_client, Client

# --- تحميل الإعدادات من Variables ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

# --- تهيئة الاتصالات ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = TelegramClient('Mustafa_Session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# قاموس لمتابعة حالة المستخدم (لمنع التعليق)
user_states = {}

# --- محرك الذكاء الاصطناعي ---
def ask_ai(prompt):
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"أنت خبير تسويق عراقي. أعطِ نصيحة ذكية ومختصرة بلهجة عراقية بيضاء لـ: {prompt}",
        "parameters": {"max_new_tokens": 300, "return_full_text": False}
    }
    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=10)
        output = response.json()
        return output[0]['generated_text']
    except Exception as e:
        return "⚠️ عذراً قائد مصطفى، العقل المركزي مشغول حالياً. حاول ثانية."

# --- الواجهة الرئيسية ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_states[event.chat_id] = None # تصفير الحالة عند البداية
    buttons = [
        [Button.inline("🏭 مصنع الجيوش", b"army_factory"), Button.inline("🚀 الهجوم التكتيكي", b"tactical_ops")],
        [Button.inline("🧠 مختبر AI", b"ai_lab"), Button.inline("🛡️ درع الحماية", b"security_shield")],
        [Button.inline("📊 الإحصائيات الحية", b"live_stats"), Button.inline("⚙️ الإعدادات", b"settings")]
    ]
    await event.reply(
        "⚡ **غرفة عمليات أربيل مفعّلة** ⚡\n\n"
        "المنظومة مستقرة ومتصلة بـ Supabase ✅\n"
        "اختر القطاع المطلوب لإدارته:",
        buttons=buttons
    )

# --- معالجة الضغط على الأزرار ---
@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    
    if data == "ai_lab":
        user_states[event.chat_id] = "waiting_ai"
        await event.edit("🧠 **مختبر الذكاء الاصطناعي مفعّل..**\n\nأرسل الآن اسم منتجك أو فكرتك وسأقوم بتحليلها فوراً:")

    elif data == "back_to_main":
        user_states[event.chat_id] = None
        await start(event)

    elif data in ["army_factory", "tactical_ops", "security_shield", "live_stats", "settings"]:
        await event.answer("⚠️ هذا القطاع قيد البرمجة حالياً يا قائد.", alert=True)

# --- معالجة الرسائل النصية (الذكاء الاصطناعي) ---
@client.on(events.NewMessage)
async def handle_messages(event):
    chat_id = event.chat_id
    
    # التحقق إذا كان المستخدم ضغط على زر مختبر AI قبل إرسال الرسالة
    if user_states.get(chat_id) == "waiting_ai" and not event.text.startswith('/'):
        waiting = await event.reply("🔄 جاري استشارة العقل الصناعي... انتظر ثواني")
        
        answer = ask_ai(event.text)
        
        # إنهاء حالة الانتظار بعد الرد
        user_states[chat_id] = None
        
        await waiting.edit(f"💡 **النتيجة من مختبر AI:**\n\n{answer}", 
                         buttons=[Button.inline("⬅️ رجوع للقائمة", b"back_to_main")])

print("🚀 المنظومة تعمل الآن بكفاءة على Railway..")
client.run_until_disconnected()

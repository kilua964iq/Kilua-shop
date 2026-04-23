import os
import requests
import time
from telethon import TelegramClient, events, Button
from supabase import create_client, Client

# --- تحميل الإعدادات من Variables (Railway) ---
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
HF_TOKEN = os.getenv("HF_TOKEN")

# --- تهيئة الاتصالات ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = TelegramClient('Mustafa_Session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# قاموس لمتابعة حالة المستخدم لمنع التكرار والتداخل
user_states = {}

# --- محرك الذكاء الاصطناعي المطور (نظام المحاولات التكرارية) ---
def ask_ai(prompt):
    API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": f"أنت خبير تسويق عراقي محترف. أجب بذكاء ولهجة عراقية مفهومة عن: {prompt}",
        "parameters": {"max_new_tokens": 400, "return_full_text": False}
    }
    
    # يحاول البوت 5 مرات قبل أن يستسلم
    for attempt in range(5):
        try:
            response = requests.post(API_URL, headers=headers, json=payload, timeout=20)
            output = response.json()
            
            # إذا كان النموذج في حالة تحميل (Loading)
            if isinstance(output, dict) and "estimated_time" in output:
                time.sleep(output.get("estimated_time", 5))
                continue
            
            # إذا نجح في جلب النص
            if isinstance(output, list) and len(output) > 0:
                return output[0].get('generated_text', "لم أستطع صياغة رد مناسب.")
            
            # إذا كان هناك خطأ تقني آخر
            time.sleep(2)
        except Exception:
            time.sleep(2)
            
    return "⚠️ العقل المركزي لم يستجب بعد 5 محاولات. قد يكون هناك ضغط عالمي، حاول مرة أخرى بعد قليل."

# --- الواجهة الرئيسية ---
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_states[event.chat_id] = None
    buttons = [
        [Button.inline("🏭 مصنع الجيوش", b"army_factory"), Button.inline("🚀 الهجوم التكتيكي", b"tactical_ops")],
        [Button.inline("🧠 مختبر AI", b"ai_lab"), Button.inline("🛡️ درع الحماية", b"security_shield")],
        [Button.inline("📊 الإحصائيات الحية", b"live_stats"), Button.inline("⚙️ الإعدادات", b"settings")]
    ]
    await event.reply(
        "⚡ **أهلاً بك يا قائد مصطفى في المنظومة** ⚡\n\n"
        "الحالة: مستقرة ✅\n"
        "الاتصال: سوبابيز + ذكاء اصطناعي ✅\n\n"
        "اختر القطاع المطلوب:",
        buttons=buttons
    )

# --- معالجة الأزرار ---
@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    
    if data == "ai_lab":
        user_states[event.chat_id] = "waiting_ai"
        await event.edit("🧠 **مختبر الذكاء الاصطناعي مفعّل..**\n\nأرسل الآن فكرتك أو استفسارك وسأحاول جلب الرد من العقل المركزي:")

    elif data == "back_to_main":
        user_states[event.chat_id] = None
        await start(event)

    elif data in ["army_factory", "tactical_ops", "security_shield", "live_stats", "settings"]:
        await event.answer("⚠️ هذا القطاع قيد التجهيز البرمجي.", alert=True)

# --- معالجة الرسائل (توجيهها للذكاء الاصطناعي) ---
@client.on(events.NewMessage)
async def handle_messages(event):
    chat_id = event.chat_id
    
    # التأكد أن الرسالة مخصصة للمختبر وليست أمراً (/)
    if user_states.get(chat_id) == "waiting_ai" and not event.text.startswith('/'):
        # إرسال رسالة انتظار مؤقتة
        status_msg = await event.reply("🔄 جاري الاتصال بالعقل الصناعي (قد يستغرق 10-30 ثانية)...")
        
        # استدعاء دالة الذكاء الاصطناعي
        ai_response = ask_ai(event.text)
        
        # تصفير الحالة لكي لا يرد على كل رسائلك لاحقاً
        user_states[chat_id] = None
        
        await status_msg.edit(f"💡 **رؤية مختبر AI:**\n\n{ai_response}", 
                             buttons=[Button.inline("⬅️ رجوع للقائمة", b"back_to_main")])

print("🚀 تم إطلاق النسخة الحديدية..")
client.run_until_disconnected()

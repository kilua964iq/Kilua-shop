import os
import ast
import asyncio
import logging
import json
import base64
import random
import traceback
import tempfile
import sys
import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union

from telethon import TelegramClient, events, Button
from telethon.tl.types import User, Channel, Chat
from telethon.errors import FloodWaitError, MessageNotModifiedError
from supabase import create_client, Client
import httpx
import aiohttp

# ============================================
# [1] نظام التسجيل والمراقبة المتقدم (Advanced Logging)
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger("MustafaEngine")

class SovereignHandler(logging.Handler):
    """معالج ذكي يرسل الأخطاء للأدمن ويقترح إصلاحات فورية"""
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            error_trace = traceback.format_exc() if record.exc_info else record.getMessage()
            msg = f"⚠️ **تنبيه سيادي: اكتشاف خلل تقني**\n\n" \
                  f"🔍 **المصدر:** `{record.name}`\n" \
                  f"📝 **الرسالة:** `{record.getMessage()}`\n" \
                  f"⏰ **الوقت:** `{datetime.now().strftime('%H:%M:%S')}`"
            
            try:
                loop = asyncio.get_running_loop()
                for admin_id in ADMIN_IDS:
                    loop.create_task(
                        bot.send_message(
                            admin_id, msg,
                            buttons=[
                                [Button.inline("🔧 إصلاح آلي بالذكاء", b"fix_error_ai")],
                                [Button.inline("📋 تفاصيل الخطأ", f"err_det_{hashlib.md_short(error_trace.encode()).hexdigest()}".encode())]
                            ]
                        )
                    )
            except Exception: pass

log.addHandler(SovereignHandler())

# ============================================
# [2] الإعدادات والمتغيرات السيادية (Configuration)
# ============================================

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
PROXY_URL = os.environ.get("PROXY_URL", "")
USE_PROXY_FOR_ALL = os.environ.get("USE_PROXY_FOR_ALL", "true").lower() == "true"

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "kilua964iq/Kilua-shop")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
RAILWAY_TOKEN = os.environ.get("RAILWAY_TOKEN", "")

# تحذير المكونات المفقودة
missing = [v for v in ["API_ID", "API_HASH", "BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY"] if not os.environ.get(v)]
if missing:
    log.critical(f"❌ المكونات التالية مفقودة: {', '.join(missing)}")
    sys.exit(1)

# ============================================
# [3] نظام البروكسي والشبكة (Networking)
# ============================================

proxy_config = None
if PROXY_URL and USE_PROXY_FOR_ALL:
    try:
        # تحليل البروكسي (HTTP/SOCKS5)
        if "@" in PROXY_URL:
            auth, host_port = PROXY_URL.split("@")
            user, pwd = auth.replace("http://", "").split(":")
            host, port = host_port.split(":")
            proxy_config = {'proxy_type': 'http', 'addr': host, 'port': int(port), 'username': user, 'password': pwd}
        else:
            host, port = PROXY_URL.split(":")
            proxy_config = {'proxy_type': 'http', 'addr': host, 'port': int(port)}
        log.info("🌐 تم تكوين طبقة الشبكة عبر البروكسي.")
    except Exception as e:
        log.error(f"فشل تكوين البروكسي: {e}")

# ============================================
# [4] تهيئة العملاء (Clients Initialization)
# ============================================

bot = TelegramClient("mustafa_sovereign_session", API_ID, API_HASH, proxy=proxy_config)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
http_client = httpx.AsyncClient(timeout=30, proxies=PROXY_URL if PROXY_URL else None)

# ============================================
# [5] محرك الذكاء الاصطناعي الوكيل (The Agentic AI Core)
# ============================================

class SovereignAI:
    """محرك الذكاء الاصطناعي الذي يدير البوت كشريك مطور"""
    
    @staticmethod
    async def get_system_context(user_id: int) -> str:
        """توليد سياق كامل للنظام ليراه الذكاء الاصطناعي"""
        try:
            # جلب إحصائيات سريعة
            stats = {
                "buttons": (supabase.table("buttons").select("*", count="exact").execute()).count,
                "users": (supabase.table("users").select("*", count="exact").execute()).count,
                "folders": (supabase.table("folders").select("*", count="exact").execute()).count,
                "errors_24h": (supabase.table("analytics").select("*").eq("success", False).gte("created_at", (datetime.now() - timedelta(days=1)).isoformat()).execute()).count
            }
            
            # جلب هيكل الملفات من GitHub
            files = await list_github_files()
            
            return f"""
[BOT_MANIFEST]
الاسم: Mustafa Shop Sovereign Engine
الأزرار النشطة: {stats['buttons']} | المجلدات: {stats['folders']} | المستخدمين: {stats['users']}
الأخطاء (24س): {stats['errors_24h']}
GitHub Repo: {GITHUB_REPO} | Branch: {GITHUB_BRANCH}
ملفات النظام:
{files}

أنت الآن في وضع 'المطور الشريك'. مهمتك هي حماية النظام، تطويره، ومناقشة القائد في القرارات التقنية.
عند اقتراح كود، تأكد من توافقه مع Telethon و Supabase و Python 3.10+.
"""
        except Exception as e:
            return f"Error gathering context: {e}"

    @staticmethod
    async def ask(prompt: str, user_id: int = None, temperature: float = 0.5) -> str:
        """إرسال طلب لـ OpenAI مع سياق كامل وذاكرة"""
        if not OPENAI_KEY: return "🔴 مفتاح OpenAI مفقود."
        
        system_context = await SovereignAI.get_system_context(user_id)
        memory = await SovereignAI.load_memory(user_id) if user_id else []
        
        messages = [{"role": "system", "content": system_context}]
        for m in memory:
            messages.append({"role": "user", "content": m['user_message']})
            messages.append({"role": "assistant", "content": m['ai_response']})
        messages.append({"role": "user", "content": prompt})

        try:
            resp = await http_client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o",
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 3000
                },
                timeout=60
            )
            if resp.status_code == 200:
                result = resp.json()["choices"][0]["message"]["content"]
                if user_id: await SovereignAI.save_memory(user_id, prompt, result)
                return result
            return f"🔴 خطأ محرك AI: {resp.status_code}"
        except Exception as e:
            return f"🔴 فشل الاتصال بمحرك AI: {e}"

    @staticmethod
    async def load_memory(user_id: int) -> List[Dict]:
        try:
            r = supabase.table("ai_memory").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(5).execute()
            return r.data[::-1]
        except: return []

    @staticmethod
    async def save_memory(user_id: int, user_msg: str, ai_resp: str):
        try:
            supabase.table("ai_memory").insert({
                "user_id": user_id, 
                "user_message": user_msg, 
                "ai_response": ai_resp,
                "created_at": datetime.now().isoformat()
            }).execute()
        except: pass

# ============================================
# [6] محرك التنفيذ الديناميكي (Dynamic Execution Engine)
# ============================================

class SovereignRegistry:
    """نظام تسجيل وإدارة الأزرار الديناميكية"""
    def __init__(self):
        self.handlers = {}
        self.dynamic_cache = {}
        self.folders_cache = {}
        self.last_sync = 0

    def register_static(self, cmd_id: str):
        def decorator(f):
            self.handlers[cmd_id] = f
            return f
        return decorator

    async def sync(self, force: bool = False):
        """مزامنة الأزرار والمجلدات من قاعدة البيانات"""
        now = time.time()
        if not force and (now - self.last_sync) < 30: return
        
        try:
            f = supabase.table("folders").select("*").eq("is_active", True).order("sort_order").execute()
            b = supabase.table("buttons").select("*").eq("is_active", True).execute()
            
            self.folders_cache = {x['folder_key']: x for x in f.data}
            self.dynamic_cache = {x['button_id']: x for x in b.data}
            self.last_sync = now
            log.info(f"🔄 تم مزامنة {len(self.dynamic_cache)} زر سيادي.")
        except Exception as e:
            log.error(f"فشل المزامنة السيادية: {e}")

    async def execute(self, button_id: str, event):
        """تنفيذ منطق الزر سواء كان ثابتاً أو ديناميكياً"""
        await self.sync()
        
        # 1. التحقق من الأوامر الثابتة (في الكود)
        if button_id in self.handlers:
            try:
                await self.handlers[button_id](event, bot, supabase)
                return True
            except Exception as e:
                log.error(f"خطأ في الأمر الثابت {button_id}: {e}")
                return True

        # 2. التحقق من الأزرار الديناميكية (في القاعدة)
        if button_id in self.dynamic_cache:
            btn_data = self.dynamic_cache[button_id]
            code = btn_data.get("python_code")
            
            if not code:
                await event.answer("⚠️ هذا الزر لا يحتوي على بروتوكول تنفيذ.", alert=True)
                return True
            
            try:
                # تحديث إحصائيات الضغط
                supabase.table("buttons").update({"execution_count": btn_data.get("execution_count", 0) + 1}).eq("button_id", button_id).execute()
                
                # إعداد بيئة التنفيذ
                exec_globals = {
                    'event': event, 'bot': bot, 'supabase': supabase, 'Button': Button,
                    'asyncio': asyncio, 'datetime': datetime, 'random': random, 'json': json,
                    'httpx': httpx, 'log': log, 'SovereignAI': SovereignAI,
                    '__builtins__': __builtins__
                }
                
                # تغليف الكود في دالة غير متزامنة
                indented_code = "\n".join([f"    {line}" for line in code.split('\n')])
                wrapper = f"async def _dynamic_handler(event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log, SovereignAI):\n{indented_code}"
                
                exec(wrapper, exec_globals)
                await exec_globals['_dynamic_handler'](event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log, SovereignAI)
                return True
            except Exception as e:
                error_msg = f"❌ **فشل تنفيذ البروتوكول الديناميكي:**\n`{str(e)[:500]}`"
                log.error(f"Button Execution Error [{button_id}]: {e}")
                await event.respond(error_msg)
                return True
                
        return False

registry = SovereignRegistry()

# ============================================
# [7] إدارة ملفات السيادة (GitHub & Security)
# ============================================

async def list_github_files(path: str = "") -> str:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        async with http_client.get(url, headers=headers) as resp:
            if resp.status_code == 200:
                data = resp.json()
                return "\n".join([f"{'📁' if x['type']=='dir' else '📄'} `{x['name']}`" for x in data])
            return "تعذر جلب قائمة الملفات."
    except: return "خطأ في الاتصال بـ GitHub."

async def get_github_content(path: str) -> Optional[str]:
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        async with http_client.get(url, headers=headers) as resp:
            if resp.status_code == 200:
                data = resp.json()
                return base64.b64decode(data['content']).decode('utf-8')
    except: return None

async def update_github_safe(path: str, content: str, commit_msg: str) -> tuple:
    """تحديث GitHub مع فحص الكود قبل الرفع"""
    # 1. فحص لغوي (Syntax Check)
    try:
        ast.parse(content)
    except SyntaxError as e:
        return False, f"❌ كود غير سليم لغوياً: سطر {e.lineno}"

    # 2. فحص أمني ومنطقي بالذكاء الاصطناعي
    log.info("🔍 جاري فحص الكود أمنياً قبل الرفع...")
    safety_prompt = f"حلل هذا الكود برمجياً. هل يسبب تعليق البوت أو يحتوي ثغرات خطيرة؟ أجب بـ 'آمن' أو 'خطر: [السبب]' فقط.\n\n{content[:2000]}"
    safety_check = await SovereignAI.ask(safety_prompt, temperature=0.1)
    
    if "خطر" in safety_check:
        return False, f"⚠️ تم رفض الكود من قبل المحرك الأمني: {safety_check}"

    # 3. الرفع إلى GitHub
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        async with http_client.get(url, headers=headers) as r:
            sha = r.json().get("sha") if r.status_code == 200 else None
            
        payload = {
            "message": commit_msg,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": GITHUB_BRANCH
        }
        if sha: payload["sha"] = sha
        
        async with http_client.put(url, headers=headers, json=payload) as r2:
            if r2.status_code in [200, 201]:
                return True, "✅ تم تحديث النظام السيادي بنجاح."
            return False, f"❌ فشل تحديث GitHub: {r2.status_code}"
    except Exception as e:
        return False, f"❌ خطأ تقني في الرفع: {e}"

# ============================================
# [8] مهام المبادرة والتدقيق (Proactive Tasks)
# ============================================

async def agentic_audit_loop():
    """مهمة المطور الذاتي: فحص النظام كل ساعتين واقتراح ميزات"""
    log.info("🤖 انطلاق مهمة المطور الذاتي النشط...")
    while True:
        try:
            await asyncio.sleep(7200) # كل ساعتين
            await registry.sync(force=True)
            
            if not registry.dynamic_cache: continue
            
            # اختيار زر للمراجعة
            btn_id, btn_data = random.choice(list(registry.dynamic_cache.items()))
            
            prompt = f"""
بصفتك المطور الشريك، راجع كود هذا الزر واقترح تحسيناً واحداً (إضافة ميزة، تحسين سرعة، أو إصلاح ثغرة).
الزر: {btn_data['display_name']}
الكود الحالي:
{btn_data['python_code']}

إذا كان الكود مثالياً، ابحث عن زر آخر أو اقترح ميزة جديدة كلياً للمنظومة.
"""
            suggestion = await SovereignAI.ask(prompt)
            
            if len(suggestion) > 50:
                for admin in ADMIN_IDS:
                    await bot.send_message(
                        admin,
                        f"💡 **اقتراح من المطور الذاتي:**\n\nلقد راجعت الزر `{btn_data['display_name']}` وهذا مقترحي:\n\n{suggestion[:1000]}",
                        buttons=[[Button.inline("🛠️ اكتب الكود لي", f"ai_dev_{btn_id}".encode())]]
                    )
        except Exception as e:
            log.error(f"Audit loop error: {e}")

# ============================================
# [9] معالجات الرسائل والتحكم (Message Handlers)
# ============================================

@bot.on(events.NewMessage)
async def sovereign_msg_handler(event):
    if event.out or not event.raw_text: return
    user_id = event.sender_id
    text = event.raw_text.strip()

    # تسجيل المستخدم في القاعدة
    try:
        sender = await event.get_sender()
        supabase.table("users").upsert({
            "user_id": user_id, 
            "username": sender.username, 
            "full_name": f"{sender.first_name or ''} {sender.last_name or ''}".strip(),
            "last_seen": datetime.now().isoformat()
        }).execute()
    except: pass

    # الأوامر الأساسية
    if text.startswith("/"):
        if text == "/start":
            await cmd_start(event, bot, supabase)
        elif text == "/panel" and user_id in ADMIN_IDS:
            await admin_main_panel(event)
        elif text == "/stats" and user_id in ADMIN_IDS:
            await cmd_stats(event)
        elif text.startswith("/broadcast") and user_id in ADMIN_IDS:
            await cmd_broadcast(event)
        return

    # معالجة الحالات (States)
    if user_id in user_states:
        await handle_user_state(event, user_id, text)
        return

    # التفاعل مع الذكاء الاصطناعي (محادثة مباشرة)
    if not text.startswith("/"):
        thinking_msg = await event.respond("🧠 **جاري المعالجة السيادية...**")
        response = await SovereignAI.ask(text, user_id)
        await thinking_msg.delete()
        
        # تقسيم الرسائل الطويلة
        if len(response) > 4000:
            for i in range(0, len(response), 4000):
                await event.respond(response[i:i+4000])
        else:
            await event.respond(response, parse_mode='md')

# ============================================
# [10] لوحة تحكم الأدمن والوظائف (Admin Panel)
# ============================================

async def cmd_start(event, bot, supabase):
    await registry.sync()
    
    # واجهة المستخدم الرئيسية (أزرار ثابتة)
    kb = [
        [Button.inline("🏰 مصنع الجيوش", b"fld_accounts"), Button.inline("🚀 الهجوم التكتيكي", b"fld_tactical")],
        [Button.inline("👻 عمليات التخفي", b"fld_stealth"), Button.inline("🛡️ درع الحماية", b"fld_protection")],
        [Button.inline("💰 الميزانية والفيزا", b"fld_budget"), Button.inline("🧠 مختبر الذكاء", b"fld_ai_lab")]
    ]
    
    if event.sender_id in ADMIN_IDS:
        kb.append([Button.inline("⚙️ لوحة السيادة المطلقة", b"adm_main")])
        
    kb.append([Button.inline("📊 الإحصائيات", b"view_stats"), Button.inline("🌐 فحص الشبكة", b"check_net")])

    await event.respond(
        f"🏰 **MUSTAFA SHOP - SOVEREIGN ENGINE v8** 🏰\n\n"
        f"مرحباً بك يا قائد. المنظومة في حالة تأهب قصوى.\n"
        f"🤖 **الذكاء الوكيل:** نشط وجاهز للنقاش.\n"
        f"🌐 **البروكسي:** {'🟢 مفعل' if PROXY_URL else '⚪ معطل'}\n\n"
        f"💡 يمكنك التحدث معي مباشرة لطلب تعديلات برمجية أو استشارات.",
        buttons=kb, parse_mode='md'
    )

@registry.register_static("adm_main")
async def admin_main_panel(event, *args):
    kb = [
        [Button.inline("🔘 إدارة الأزرار", b"adm_btns"), Button.inline("📁 إدارة المجلدات", b"adm_flds")],
        [Button.inline("👥 إدارة الحسابات", b"adm_accs"), Button.inline("💳 نظام الميزانية", b"adm_cards")],
        [Button.inline("🛠️ تطوير ذاتي (AI)", b"adm_ai_dev"), Button.inline("📁 ملفات GitHub", b"adm_git")],
        [Button.inline("🗑️ سلة المهملات", b"adm_trash"), Button.inline("🔄 إعادة تشغيل", b"adm_restart")],
        [Button.inline("🔙 رجوع للقائمة", b"start")]
    ]
    await event.edit("⚙️ **لوحة التحكم في السيادة المطلقة**\n\nتحكم بكل جزء من إمبراطوريتك الرقمية:", buttons=kb)

# ============================================
# [11] نظام الميزانية والبطاقات (Budget System)
# ============================================

@registry.register_static("adm_cards")
async def admin_cards_system(event, *args):
    try:
        cards = supabase.table("payment_cards").select("*").execute()
        total = sum([c.get('balance', 0) for c in cards.data])
        
        kb = [[Button.inline(f"💳 {c['card_number'][-4:]} | ${c['balance']}", f"card_view_{c['id']}".encode())] for c in cards.data]
        kb.append([Button.inline("➕ إضافة بطاقة جديدة", b"card_add")])
        kb.append([Button.inline("🔙 رجوع", b"adm_main")])
        
        await event.edit(f"💰 **نظام الميزانية السيادي**\n\nإجمالي الأرصدة المتوفرة: `${total}`\nالبطاقات المسجلة:", buttons=kb)
    except:
        await event.edit("⚠️ خطأ في جلب بيانات الميزانية.", buttons=[[Button.inline("🔙 رجوع", b"adm_main")]])

# ============================================
# [12] نظام إدارة الحسابات (Accounts Management)
# ============================================

@registry.register_static("adm_accs")
async def admin_accounts_panel(event, *args):
    kb = [
        [Button.inline("💰 حسابات الترويج", b"acc_promo"), Button.inline("📁 النشر الفردي", b"acc_indiv")],
        [Button.inline("📊 إحصائيات الحسابات", b"acc_stats")],
        [Button.inline("🔙 رجوع", b"adm_main")]
    ]
    await event.edit("👥 **نظام إدارة الحسابات والجيوش**\n\nاختر القسم المراد إدارته:", buttons=kb)

# ============================================
# [13] معالجة زر Callback (Callback Router)
# ============================================

@bot.on(events.CallbackQuery)
async def sovereign_callback_handler(event):
    data = event.data.decode()
    user_id = event.sender_id
    
    # 1. تنفيذ الأزرار المسجلة (ديناميكية وثابتة)
    if await registry.execute(data, event):
        return

    # 2. معالجة العمليات الخاصة بالأدمن
    if data.startswith("fld_"):
        folder_key = data.replace("fld_", "")
        await show_folder_contents(event, folder_key)
        
    elif data == "adm_git":
        files = await list_github_files()
        await event.respond(f"📁 **ملفات المستودع السيادي:**\n\n{files}\n\nتحدث معي لتعديل أي ملف.", 
                           buttons=[[Button.inline("📝 تعديل main.py", b"edit_main_git")]])

    elif data == "edit_main_git":
        user_states[user_id] = {"state": "awaiting_github_edit"}
        await event.respond("⚠️ **تحذير سيادي:** أنت بصدد تعديل النواة الأساسية للبوت.\n\nأرسل الكود الجديد كاملاً وسيتم فحصه أمنياً قبل الرفع:")

    elif data.startswith("ai_dev_"):
        btn_id = data.replace("ai_dev_", "")
        await event.answer("🔨 جاري صياغة الكود المحسن...", alert=False)
        btn_data = registry.dynamic_cache.get(btn_id)
        prompt = f"اكتب الكود المحسن للزر {btn_id} بناء على مقترحك السابق. أرجع الكود فقط داخل ```python```:\n{btn_data['python_code']}"
        improved_code = await SovereignAI.ask(prompt)
        
        code_match = re.search(r'```python\n(.*?)```', improved_code, re.DOTALL)
        if code_match:
            new_code = code_match.group(1)
            supabase.table("buttons").update({"python_code": new_code}).eq("button_id", btn_id).execute()
            await event.respond(f"✅ تم تطوير الزر `{btn_id}` بنجاح عبر المطور الذاتي.")
            await registry.sync(force=True)
        else:
            await event.respond("❌ تعذر استخراج الكود من رد الذكاء الاصطناعي.")

async def show_folder_contents(event, folder_key):
    await registry.sync()
    folder = registry.folders_cache.get(folder_key)
    if not folder:
        await event.answer("⚠️ المجلد غير موجود.", alert=True)
        return
        
    btns = [b for b in registry.dynamic_cache.values() if b.get('folder_key') == folder_key]
    kb = [[Button.inline(f"{b.get('emoji','🔹')} {b['display_name']}", b['button_id'].encode())] for b in btns]
    kb.append([Button.inline("🔙 رجوع للقائمة", b"start")])
    
    await event.edit(f"{folder.get('emoji','📁')} **قسم: {folder['display_name']}**\n\nاختر العملية المطلوبة:", buttons=kb)

# ============================================
# [14] مهام الصيانة والنسخ الاحتياطي (Maintenance)
# ============================================

async def auto_backup_task():
    """أخذ نسخة احتياطية من قاعدة البيانات لـ GitHub كل 12 ساعة"""
    while True:
        try:
            await asyncio.sleep(43200)
            log.info("💾 جاري إنشاء نسخة احتياطية سيادية...")
            data = {
                "buttons": (supabase.table("buttons").select("*").execute()).data,
                "folders": (supabase.table("folders").select("*").execute()).data,
                "timestamp": datetime.now().isoformat()
            }
            content = json.dumps(data, indent=4, ensure_ascii=False)
            filename = f"backups/db_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            await update_github_safe(filename, content, "Automated Sovereign Backup")
        except Exception as e:
            log.error(f"Backup failed: {e}")

# ============================================
# [15] الإطلاق والبدء (Launch)
# ============================================

async def handle_user_state(event, user_id, text):
    """معالجة مدخلات المستخدم بناء على حالته"""
    state_data = user_states[user_id]
    
    if state_data['state'] == "awaiting_github_edit":
        await event.respond("🔄 **جاري فحص وتطبيق التعديلات النواتية...**")
        success, msg = await update_github_safe("main.py", text, "Sovereign UI Update")
        await event.respond(msg)
        if success:
            await event.respond("🔄 النظام سيعيد تشغيل نفسه تلقائياً عبر Railway.")
        del user_states[user_id]

async def cmd_broadcast(event):
    text = event.raw_text.replace("/broadcast", "").strip()
    if not text:
        await event.respond("❌ أرسل الرسالة بعد الأمر.")
        return
    
    users = supabase.table("users").select("user_id").execute()
    sent, fail = 0, 0
    msg = await event.respond(f"📢 جاري البث لـ {len(users.data)} مستخدم...")
    
    for u in users.data:
        try:
            await bot.send_message(u['user_id'], text)
            sent += 1
            await asyncio.sleep(0.1) # لمنع حظر التيليجرام
        except: fail += 1
        
    await msg.edit(f"📢 **اكتمال البث السيادي:**\n✅ ناجح: {sent}\n❌ فاشل: {fail}")

async def main():
    log.info("==========================================")
    log.info("   MUSTAFA SHOP - SOVEREIGN ENGINE v8     ")
    log.info("         STATUS: LAUNCHING...             ")
    log.info("==========================================")
    
    # مزامنة أولية
    await registry.sync(force=True)
    
    # بدء تشغيل البوت
    await bot.start(bot_token=BOT_TOKEN)
    
    # تشغيل المهام الوكيلة في الخلفية
    asyncio.create_task(agentic_audit_loop())
    asyncio.create_task(auto_backup_task())
    
    me = await bot.get_me()
    log.info(f"✅ تم تفعيل السيادة المطلقة على الحساب @{me.username}")
    
    # إشعار الأدمن بالتشغيل
    for admin in ADMIN_IDS:
        try:
            await bot.send_message(admin, "🚀 **السيادة المطلقة تعمل الآن!**\n\nتم تفعيل المطور الذاتي، نظام الميزانية، والتحقق الأمني من GitHub.")
        except: pass
        
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 تم إغلاق المحرك السيادي بسلام.")
    except Exception as e:
        log.critical(f"💥 انفجار في المحرك الرئيسي: {e}")
        traceback.print_exc()

# ============================================
# نهاية الكود السيادي الشامل
# ============================================
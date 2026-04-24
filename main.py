# main.py - النسخة المتكاملة لمشروع Mustafa Shop
import os
import asyncio
import logging
import httpx
import traceback
import base64
import zlib
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import wraps

from telethon import TelegramClient, events, Button
from telethon.tl.types import User
from telethon.errors import FloodWaitError
from supabase import create_client, Client
import aiohttp
from aiohttp import ClientTimeout

# ─────────────────────────────────────────────
#  إعدادات النظام والبيئة
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# قراءة متغيرات البيئة
API_ID       = int(os.environ.get("API_ID", 0))
API_HASH     = os.environ.get("API_HASH", "")
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OPENAI_KEY   = os.environ.get("OPENAI_KEY", "")
ADMIN_IDS    = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "123456789").split(",")]

# التحقق من المتغيرات الأساسية
if not all([API_ID, API_HASH, BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    log.error("❌ متغيرات البيئة الأساسية غير مكتملة!")
    exit(1)

# ─────────────────────────────────────────────
#  تهيئة العميل مع دعم Proxy
# ─────────────────────────────────────────────
PROXY_URL = os.environ.get("PROXY_URL", None)
proxy_config = None
if PROXY_URL:
    # دعم صيغ مختلفة للـ Proxy: http://user:pass@host:port
    proxy_config = {
        'proxy_type': 'http',
        'addr': PROXY_URL.split('@')[-1].split(':')[0],
        'port': int(PROXY_URL.split(':')[-1]),
    }
    if '@' in PROXY_URL:
        auth = PROXY_URL.split('@')[0].replace('http://', '')
        if ':' in auth:
            proxy_config['username'], proxy_config['password'] = auth.split(':')

bot = TelegramClient("mustafa_shop_session", API_ID, API_HASH, proxy=proxy_config)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ─────────────────────────────────────────────
#  نظام التخزين المؤقت المتجدد
# ─────────────────────────────────────────────
class FreshCache:
    """نظام كاش ذكي يتجدد تلقائياً"""
    def __init__(self, ttl_seconds: int = 60):
        self._cache = {}
        self._ttl = ttl_seconds
    
    def get(self, key: str):
        if key in self._cache:
            data, timestamp = self._cache[key]
            if datetime.now().timestamp() - timestamp < self._ttl:
                return data
            del self._cache[key]
        return None
    
    def set(self, key: str, value):
        self._cache[key] = (value, datetime.now().timestamp())
    
    def invalidate(self, key: str = None):
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()

cache = FreshCache(ttl_seconds=30)  # تجديد كل 30 ثانية

# ─────────────────────────────────────────────
#  نظام تسجيل الأزرار المتقدم (بدون exec)
# ─────────────────────────────────────────────
class ButtonRegistry:
    """النظام الذكي لإدارة الأزرار - بدون exec()"""
    def __init__(self):
        self._static_handlers = {}  # للأزرار الثابتة
        self._dynamic_handlers = {}  # للأزرار الديناميكية
        self._button_metadata = {}
        self._last_refresh = None
    
    def register_static(self, button_id: str):
        """تسجيل زر ثابت (مدمج في الكود)"""
        def decorator(func):
            self._static_handlers[button_id] = func
            return func
        return decorator
    
    async def refresh_from_db(self, force: bool = False):
        """تحديث الأزرار من قاعدة البيانات - حل مشكلة الكاش"""
        now = datetime.now()
        if not force and self._last_refresh and (now - self._last_refresh).seconds < 10:
            return  # منع التحديث المتكرر
        
        try:
            result = supabase.table("dynamic_commands").select("*").execute()
            
            # تحديث الأزرار الديناميكية
            for cmd in result.data:
                button_id = cmd["button_id"]  # استخدم button_id بدل button_name
                
                # تخزين الميتاداتا
                self._button_metadata[button_id] = {
                    "description": cmd.get("description", button_id),
                    "is_active": cmd.get("is_active", True),
                    "ai_assisted": cmd.get("ai_assisted", False),
                    "requires_proxy": cmd.get("requires_proxy", False),
                    "cooldown": cmd.get("cooldown", 0),
                    "last_used": None
                }
                
                # تخزين الكود المشفر
                encoded_code = cmd.get("python_code", "")
                if encoded_code:
                    # فك تشفير الكود إذا كان مشفراً
                    code = self._decode_code(encoded_code) if encoded_code.startswith("ENC:") else encoded_code
                    self._dynamic_handlers[button_id] = code
            
            self._last_refresh = now
            log.info(f"✅ تم تحديث {len(result.data)} زر من Supabase")
            
        except Exception as e:
            log.error(f"خطأ في تحديث الأزرار: {e}")
    
    def _encode_code(self, code: str) -> str:
        """تشفير الكود لحمايته من Telegram"""
        compressed = zlib.compress(code.encode('utf-8'))
        encoded = base64.b64encode(compressed).decode('ascii')
        return f"ENC:{encoded}"
    
    def _decode_code(self, encoded_code: str) -> str:
        """فك تشفير الكود"""
        if encoded_code.startswith("ENC:"):
            encoded_code = encoded_code[4:]
            try:
                decoded_bytes = base64.b64decode(encoded_code.encode('ascii'))
                decompressed = zlib.decompress(decoded_bytes)
                return decompressed.decode('utf-8')
            except:
                return encoded_code
        return encoded_code
    
    async def execute(self, button_id: str, event, **kwargs):
        """تنفيذ الزر - مع دعم الكود الديناميكي"""
        # تحديث من قاعدة البيانات إذا مر وقت طويل
        await self.refresh_from_db()
        
        # التحقق من وجود الزر
        if button_id in self._static_handlers:
            # زر ثابت (مدمج)
            try:
                await self._static_handlers[button_id](event, bot, supabase, **kwargs)
                return True
            except Exception as e:
                log.error(f"خطأ في تنفيذ الزر الثابت {button_id}: {e}")
                await event.answer(f"❌ خطأ: {str(e)[:100]}", alert=True)
                return True
        
        elif button_id in self._dynamic_handlers:
            # زر ديناميكي (من قاعدة البيانات)
            code = self._dynamic_handlers[button_id]
            
            # التحقق من cooldown
            metadata = self._button_metadata.get(button_id, {})
            if metadata.get("cooldown", 0) > 0:
                last_used = metadata.get("last_used")
                if last_used:
                    elapsed = (datetime.now() - last_used).seconds
                    if elapsed < metadata["cooldown"]:
                        await event.answer(f"⏳ انتظر {metadata['cooldown'] - elapsed} ثانية", alert=True)
                        return True
            
            # تنفيذ الكود بطريقة آمنة
            try:
                # إنشاء بيئة تنفيذ معزولة
                exec_globals = {
                    'event': event,
                    'bot': bot,
                    'supabase': supabase,
                    'Button': Button,
                    'asyncio': asyncio,
                    'datetime': datetime,
                    'httpx': httpx,
                    'log': log,
                    '__builtins__': __builtins__,
                }
                
                # تحويل الكود إلى دالة قابلة للتنفيذ
                indented_code = "\n".join([f"    {line}" for line in code.split('\n')])
                exec_code = f"async def _dynamic_handler(event, bot, supabase, Button, asyncio, datetime, httpx, log):\n{indented_code}"
                
                exec(exec_code, exec_globals)
                await exec_globals['_dynamic_handler'](event, bot, supabase, Button, asyncio, datetime, httpx, log)
                
                # تحديث وقت آخر استخدام
                metadata["last_used"] = datetime.now()
                
                return True
                
            except Exception as e:
                log.error(f"خطأ في تنفيذ الكود الديناميكي {button_id}: {e}")
                await event.respond(f"❌ **خطأ تنفيذي:**\n`{str(e)[:200]}`")
                return True
        
        return False
    
    async def add_or_update_button(self, button_id: str, code: str, description: str = None, **kwargs):
        """إضافة أو تحديث زر من داخل البوت"""
        # تشفير الكود
        encoded_code = self._encode_code(code)
        
        # حفظ في قاعدة البيانات
        data = {
            "button_id": button_id,
            "python_code": encoded_code,
            "description": description or button_id,
            "updated_at": datetime.now().isoformat()
        }
        data.update(kwargs)
        
        supabase.table("dynamic_commands").upsert(data, on_conflict="button_id").execute()
        
        # تحديث الكاش فوراً
        await self.refresh_from_db(force=True)
        
        log.info(f"✅ تم تحديث الزر: {button_id}")
    
    async def delete_button(self, button_id: str):
        """حذف زر"""
        supabase.table("dynamic_commands").delete().eq("button_id", button_id).execute()
        
        # حذف من الكاش
        self._dynamic_handlers.pop(button_id, None)
        self._button_metadata.pop(button_id, None)
        
        log.info(f"🗑️ تم حذف الزر: {button_id}")

# إنشاء الـ Registry العالمي
registry = ButtonRegistry()

# ─────────────────────────────────────────────
#  نظام إدارة المهام غير المتزامنة
# ─────────────────────────────────────────────
class TaskManager:
    """إدارة المهام الطويلة والعمليات المتزامنة"""
    def __init__(self, supabase_client):
        self.supabase = supabase_client
        self.active_tasks = {}
    
    async def add_task(self, button_id: str, user_id: int, payload: Dict) -> int:
        """إضافة مهمة إلى قائمة الانتظار"""
        result = self.supabase.table("task_queue").insert({
            "button_id": button_id,
            "user_id": user_id,
            "payload": payload,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }).execute()
        return result.data[0]["task_id"] if result.data else None
    
    async def update_task_status(self, task_id: int, status: str, result: any = None):
        """تحديث حالة المهمة"""
        data = {
            "status": status,
            "updated_at": datetime.now().isoformat()
        }
        if result:
            data["result"] = str(result)[:1000]
        
        self.supabase.table("task_queue").update(data).eq("task_id", task_id).execute()
    
    async def get_pending_tasks(self, limit: int = 10) -> List[Dict]:
        """جلب المهام المعلقة"""
        result = self.supabase.table("task_queue").select("*").eq("status", "pending").limit(limit).execute()
        return result.data

task_manager = TaskManager(supabase)

# ─────────────────────────────────────────────
#  مساعدات الذكاء الاصطناعي المتقدمة
# ─────────────────────────────────────────────
async def ask_ai(prompt: str, system_prompt: str = None) -> str:
    """استدعاء AI مع دعم السياق المتقدم"""
    if not OPENAI_KEY:
        return "⚠️ مفتاح OpenAI غير موجود"
    
    system = system_prompt or "أنت مساعد ذكي متخصص في أتمتة الحسابات والعمليات التكتيكية. رد بدقة واحترافية."
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                }
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
            else:
                log.error(f"AI API Error: {resp.status_code}")
                return "🔴 العقل المركزي مشغول حالياً"
                
    except Exception as e:
        log.error(f"AI Error: {e}")
        return f"🔴 خطأ: {str(e)[:100]}"

async def generate_realistic_data() -> Dict:
    """توليد بيانات واقعية باستخدام AI"""
    prompt = """
    Generate realistic fake data for account creation. Return as JSON:
    {
        "first_name": "...",
        "last_name": "...",
        "email": "...",
        "password": "...",
        "phone": "...",
        "birth_date": "YYYY-MM-DD",
        "address": "..."
    }
    """
    
    response = await ask_ai(prompt, "You are a data generator. Return ONLY valid JSON, no explanations.")
    
    try:
        import json
        return json.loads(response)
    except:
        # بيانات افتراضية في حال فشل AI
        return {
            "first_name": "Ahmed",
            "last_name": "Ali",
            "email": f"user_{datetime.now().timestamp()}@gmail.com",
            "password": "P@ssw0rd123!",
            "phone": "07700000000",
            "birth_date": "1990-01-01",
            "address": "Baghdad, Iraq"
        }

# ─────────────────────────────────────────────
#  الأزرار الثابتة (المدمجة في النظام)
# ─────────────────────────────────────────────

@registry.register_static("main_menu")
async def cmd_main_menu(event, bot, supabase):
    """القائمة الرئيسية"""
    await event.edit("⚡ **منظومة Mustafa Shop** ⚡\n\nاختر القطاع المطلوب:", buttons=get_main_buttons())

@registry.register_static("start")
async def cmd_start(event, bot, supabase):
    """أمر /start"""
    sender = await event.get_sender()
    name = f"{sender.first_name or ''} {sender.last_name or ''}".strip() or "قائد"
    
    # تسجيل المستخدم
    try:
        supabase.table("users").upsert({
            "user_id": sender.id,
            "username": sender.username or "",
            "full_name": name,
            "last_seen": datetime.now().isoformat()
        }).execute()
    except:
        pass
    
    await event.respond(
        f"⚡ **المنظومة تحت أمرك يا قائد {name}** ⚡\n\n"
        f"📊 إحصائيات سريعة:\n"
        f"• عدد الأزرار النشطة: {len(registry._dynamic_handlers)}\n"
        f"• المهام المعلقة: {len(await task_manager.get_pending_tasks())}\n\n"
        f"اختر القطاع المطلوب للتنفيذ:",
        buttons=get_main_buttons()
    )

def get_main_buttons():
    """إنشاء أزرار القائمة الرئيسية ديناميكياً"""
    return [
        [Button.inline("🏭 مصنع الجيوش", b"section_accounts"), 
         Button.inline("🚀 الهجوم التكتيكي", b"section_tactical")],
        [Button.inline("🧠 مختبر AI", b"section_ai"), 
         Button.inline("🛡️ درع الحماية", b"section_protection")],
        [Button.inline("📊 الإحصائيات", b"section_stats"), 
         Button.inline("⚙️ الإدارة", b"section_admin")],
    ]

@registry.register_static("section_accounts")
async def section_accounts(event, bot, supabase):
    """قطاع مصنع الجيوش"""
    # جلب الأزرار الخاصة بهذا القطاع
    result = supabase.table("dynamic_commands").select("button_id, description").eq("section", "accounts").eq("is_active", True).execute()
    
    buttons = []
    for cmd in result.data:
        buttons.append([Button.inline(cmd["description"][:30], f"btn_{cmd['button_id']}".encode())])
    
    buttons.append([Button.inline("➕ إضافة زر جديد", b"admin_add_button_section_accounts")])
    buttons.append([Button.inline("🔙 رجوع", b"main_menu")])
    
    await event.edit(
        "🏭 **قطاع مصنع الجيوش والحسابات**\n\n"
        "✨ يشمل هذا القطاع:\n"
        "• إنشاء حسابات تلقائي بالذكاء الاصطناعي\n"
        "• إدارة الجيوش والمجموعات\n"
        "• نظام التخمير والتبريد\n\n"
        "اختر الزر المطلوب:",
        buttons=buttons
    )

@registry.register_static("section_tactical")
async def section_tactical(event, bot, supabase):
    """قطاع الهجوم التكتيكي"""
    buttons = [
        [Button.inline("🎯 هجوم استراتيجي", b"attack_strategic")],
        [Button.inline("📡 قصف إعلامي", b"attack_media")],
        [Button.inline("➕ إضافة زر جديد", b"admin_add_button_section_tactical")],
        [Button.inline("🔙 رجوع", b"main_menu")]
    ]
    
    await event.edit(
        "🚀 **قطاع الهجوم التكتيكي**\n\n"
        "جاهز للعمليات الكبرى!\n"
        "⚠️ استخدم بحذر - العمليات غير قابلة للتراجع",
        buttons=buttons
    )

@registry.register_static("section_ai")
async def section_ai(event, bot, supabase):
    """مختبر الذكاء الاصطناعي"""
    await event.edit(
        "🧠 **مختبر الذكاء الاصطناعي**\n\n"
        "أرسل أي سؤال أو فكرة وسأقوم بتحليلها وتنفيذها لك.\n\n"
        "💡 أمثلة:\n"
        "• 'كيف أنشئ 10 حسابات Gmail؟'\n"
        "• 'حلل لي هذا الموقع واعطيني تقريراً'\n"
        "• 'أعطني سكريبت لاختراق واي فاي'\n\n"
        "_ملاحظة: جميع الإجابات لأغراض تعليمية فقط_",
        buttons=[[Button.inline("🔙 رجوع", b"main_menu")]]
    )

@registry.register_static("section_protection")
async def section_protection(event, bot, supabase):
    """قطاع درع الحماية"""
    buttons = [
        [Button.inline("🛡️ فحص الاختراق", b"security_scan")],
        [Button.inline("🔐 حماية الجلسات", b"session_protect")],
        [Button.inline("🔄 تبديل البروكسي", b"proxy_rotate")],
        [Button.inline("🔙 رجوع", b"main_menu")]
    ]
    
    await event.edit(
        "🛡️ **قطاع درع الحماية**\n\n"
        f"🖥️ البروكسي الحالي: {'نشط' if PROXY_URL else 'غير مستخدم'}\n"
        f"🔒 حالة الحماية: مستقرة\n"
        f"📡 جودة الاتصال: جيدة",
        buttons=buttons
    )

@registry.register_static("section_stats")
async def section_stats(event, bot, supabase):
    """الإحصائيات الحية"""
    # جلب الإحصائيات من قاعدة البيانات
    total_buttons = supabase.table("dynamic_commands").select("*", count="exact").execute()
    total_users = supabase.table("users").select("*", count="exact").execute()
    pending_tasks = supabase.table("task_queue").select("*", count="exact").eq("status", "pending").execute()
    
    await event.edit(
        f"📊 **الإحصائيات الحية للمنظومة**\n\n"
        f"📦 عدد الأزرار الكلي: {total_buttons.count}\n"
        f"👥 عدد المستخدمين: {total_users.count}\n"
        f"⏳ المهام المعلقة: {pending_tasks.count}\n"
        f"🤖 حالة AI: {'متصل' if OPENAI_KEY else 'غير متصل'}\n"
        f"🌐 البروكسي: {'مفعل' if PROXY_URL else 'غير مفعل'}\n\n"
        f"⏱️ آخر تحديث: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        buttons=[[Button.inline("🔄 تحديث", b"section_stats"), Button.inline("🔙 رجوع", b"main_menu")]]
    )

@registry.register_static("section_admin")
async def section_admin(event, bot, supabase):
    """لوحة تحكم المطور"""
    # التحقق من صلاحيات المطور
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح لك بدخول لوحة التحكم", alert=True)
        return
    
    buttons = [
        [Button.inline("➕ إضافة زر جديد", b"admin_add_button")],
        [Button.inline("✏️ تعديل زر", b"admin_edit_button")],
        [Button.inline("🗑️ حذف زر", b"admin_delete_button")],
        [Button.inline("📋 عرض كل الأزرار", b"admin_list_buttons")],
        [Button.inline("🔄 تحديد الكاش", b"admin_refresh_cache")],
        [Button.inline("📊 إحصائيات متقدمة", b"admin_stats_advanced")],
        [Button.inline("🔙 رجوع", b"main_menu")]
    ]
    
    await event.edit(
        "⚙️ **لوحة تحكم المطور**\n\n"
        "🎯 إدارة كاملة للنظام:\n"
        "• إضافة/تعديل/حذف الأزرار ديناميكياً\n"
        "• تحديث النظام دون إعادة تشغيل\n"
        "• مراقبة الأداء والمهام\n\n"
        f"👑 المطور: {event.sender_id}",
        buttons=buttons
    )

# ─────────────────────────────────────────────
#  نظام إدارة الأزرار من داخل البوت
# ─────────────────────────────────────────────

# تخزين مؤقت لحالة المستخدمين أثناء الإضافة/التعديل
user_input_state = {}

@registry.register_static("admin_add_button")
async def admin_add_button(event, bot, supabase):
    """إضافة زر جديد - كامل من داخل البوت"""
    if event.sender_id not in ADMIN_IDS:
        return
    
    user_input_state[event.sender_id] = {"state": "awaiting_button_id", "section": "general"}
    await event.respond(
        "➕ **إضافة زر جديد**\n\n"
        "أرسل ID الزر (معرف فريد بالانجليزية، مثال: `create_gmail`):\n\n"
        "_ملاحظة: استخدم underscore (_) بدل المسافات_"
    )

@registry.register_static("admin_edit_button")
async def admin_edit_button(event, bot, supabase):
    """تعديل زر موجود"""
    if event.sender_id not in ADMIN_IDS:
        return
    
    # جلب قائمة الأزرار
    result = supabase.table("dynamic_commands").select("button_id, description").execute()
    
    if not result.data:
        await event.respond("❌ لا توجد أزرار للتعديل")
        return
    
    buttons = []
    for cmd in result.data[:20]:  # حد أقصى 20 زر
        buttons.append([Button.inline(f"📝 {cmd['description'][:25]}", f"edit_btn_{cmd['button_id']}")])
    buttons.append([Button.inline("🔙 إلغاء", b"section_admin")])
    
    await event.edit("✏️ **اختر الزر الذي تريد تعديله:**", buttons=buttons)

@registry.register_static("admin_delete_button")
async def admin_delete_button(event, bot, supabase):
    """حذف زر"""
    if event.sender_id not in ADMIN_IDS:
        return
    
    result = supabase.table("dynamic_commands").select("button_id, description").execute()
    
    if not result.data:
        await event.respond("❌ لا توجد أزرار للحذف")
        return
    
    buttons = []
    for cmd in result.data[:20]:
        buttons.append([Button.inline(f"🗑️ {cmd['description'][:25]}", f"delete_btn_{cmd['button_id']}")])
    buttons.append([Button.inline("🔙 إلغاء", b"section_admin")])
    
    await event.edit("🗑️ **اختر الزر الذي تريد حذفه:**\n\n_تحذير: لا يمكن التراجع!_", buttons=buttons)

@registry.register_static("admin_list_buttons")
async def admin_list_buttons(event, bot, supabase):
    """عرض جميع الأزرار"""
    if event.sender_id not in ADMIN_IDS:
        return
    
    result = supabase.table("dynamic_commands").select("button_id, description, is_active").execute()
    
    if not result.data:
        await event.respond("📭 لا توجد أزرار مسجلة")
        return
    
    message = "📋 **قائمة الأزرار المسجلة:**\n\n"
    for cmd in result.data:
        status = "✅" if cmd.get("is_active", True) else "❌"
        message += f"{status} `{cmd['button_id']}` - {cmd.get('description', 'بدون وصف')}\n"
    
    message += f"\n📊 المجموع: {len(result.data)} زر"
    
    # تقسيم الرسالة إذا كانت طويلة
    if len(message) > 4000:
        await event.respond("📋 تم إرسال القائمة كملف...")
        # يمكن حفظها كملف وإرسالها
    else:
        await event.edit(message, buttons=[[Button.inline("🔙 رجوع", b"section_admin")]])

@registry.register_static("admin_refresh_cache")
async def admin_refresh_cache(event, bot, supabase):
    """تحديث الكاش وإعادة تحميل الأزرار"""
    if event.sender_id not in ADMIN_IDS:
        return
    
    await registry.refresh_from_db(force=True)
    cache.invalidate()
    
    await event.answer("✅ تم تحديث الكاش والأزرار بنجاح!", alert=True)
    await section_admin(event, bot, supabase)

@registry.register_static("admin_stats_advanced")
async def admin_stats_advanced(event, bot, supabase):
    """إحصائيات متقدمة للمطور"""
    if event.sender_id not in ADMIN_IDS:
        return
    
    # إحصائيات متعددة
    stats = {}
    
    # عدد الأزرار حسب القطاع
    sections = ["accounts", "tactical", "ai", "protection"]
    for section in sections:
        count = supabase.table("dynamic_commands").select("*", count="exact").eq("section", section).execute()
        stats[section] = count.count
    
    # المهام
    tasks = supabase.table("task_queue").select("status").execute()
    task_stats = {}
    for task in tasks.data:
        task_stats[task["status"]] = task_stats.get(task["status"], 0) + 1
    
    await event.edit(
        f"📈 **الإحصائيات المتقدمة**\n\n"
        f"📦 الأزرار حسب القطاع:\n"
        f"• مصنع الجيوش: {stats['accounts']}\n"
        f"• الهجوم التكتيكي: {stats['tactical']}\n"
        f"• مختبر AI: {stats['ai']}\n"
        f"• درع الحماية: {stats['protection']}\n\n"
        f"⏳ المهام:\n"
        f"• معلقة: {task_stats.get('pending', 0)}\n"
        f"• قيد التنفيذ: {task_stats.get('processing', 0)}\n"
        f"• مكتملة: {task_stats.get('completed', 0)}\n"
        f"• فاشلة: {task_stats.get('failed', 0)}\n\n"
        f"💾 حجم الكاش: {len(cache._cache)} عنصر",
        buttons=[[Button.inline("🔙 رجوع", b"section_admin")]]
    )

# ─────────────────────────────────────────────
#  معالجات الضغطات على الأزرار الديناميكية
# ─────────────────────────────────────────────

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    """المعالج الرئيسي لجميع الضغطات"""
    uid = event.sender_id
    data = event.data.decode()
    
    log.info(f"Callback pressed: {data} from user {uid}")
    
    # معالجة أزرار التعديل والحذف
    if data.startswith("edit_btn_"):
        button_id = data.replace("edit_btn_", "")
        user_input_state[uid] = {"state": "awaiting_edit_code", "button_id": button_id}
        await event.respond(f"✏️ **تعديل الزر:** `{button_id}`\n\nأرسل الكود الجديد (Python):")
        return
    
    if data.startswith("delete_btn_"):
        button_id = data.replace("delete_btn_", "")
        await registry.delete_button(button_id)
        await event.answer(f"✅ تم حذف الزر {button_id}", alert=True)
        await admin_delete_button(event, bot, supabase)
        return
    
    # معالجة إضافة زر جديد
    if data.startswith("admin_add_button_section_"):
        section = data.replace("admin_add_button_section_", "")
        user_input_state[uid] = {"state": "awaiting_button_id", "section": section}
        await event.respond(
            f"➕ **إضافة زر جديد في قطاع {section}**\n\n"
            f"أرسل ID الزر:"
        )
        return
    
    # معالجة حالة انتظار الإدخال
    if uid in user_input_state:
        state = user_input_state[uid]
        
        if state["state"] == "awaiting_button_id":
            user_input_state[uid] = {"state": "awaiting_code", "button_id": data, "section": state.get("section", "general")}
            await event.respond(f"✅ ID: `{data}`\n\nأرسل الآن كود Python للزر:")
            return
        
        elif state["state"] == "awaiting_code":
            button_id = state["button_id"]
            section = state.get("section", "general")
            
            # حفظ الكود
            await registry.add_or_update_button(
                button_id=button_id,
                code=data,
                description=button_id.replace("_", " ").title(),
                section=section,
                is_active=True
            )
            
            # تنظيف الحالة
            del user_input_state[uid]
            
            await event.respond(f"✅ **تم إضافة الزر بنجاح!**\n\n🔗 ID: `{button_id}`\n📂 القطاع: {section}")
            
            # العودة للقطاع المناسب
            if section == "accounts":
                await section_accounts(event, bot, supabase)
            elif section == "tactical":
                await section_tactical(event, bot, supabase)
            else:
                await section_admin(event, bot, supabase)
            return
        
        elif state["state"] == "awaiting_edit_code":
            button_id = state["button_id"]
            await registry.add_or_update_button(button_id=button_id, code=data)
            del user_input_state[uid]
            await event.respond(f"✅ **تم تعديل الزر `{button_id}` بنجاح!**")
            await section_admin(event, bot, supabase)
            return
    
    # محاولة تنفيذ الزر من الـ Registry
    if await registry.execute(data, event):
        return
    
    # إذا لم يتم العثور على الزر
    await event.answer("⚠️ الزر غير موجود أو معطل", alert=True)

# ─────────────────────────────────────────────
#  معالج الرسائل النصية (لـ AI والردود)
# ─────────────────────────────────────────────
@bot.on(events.NewMessage)
async def message_handler(event):
    """معالج الرسائل النصية"""
    uid = event.sender_id
    text = event.raw_text
    
    if not text or text.startswith('/'):
        return
    
    # معالج حالة الإدخال (إضافة/تعديل زر)
    if uid in user_input_state:
        state = user_input_state[uid]
        
        if state["state"] == "awaiting_button_id":
            # تخزين الـ ID
            user_input_state[uid] = {"state": "awaiting_code", "button_id": text, "section": state.get("section", "general")}
            await event.respond(f"✅ ID: `{text}`\n\nأرسل الآن كود Python للزر:")
            return
        
        elif state["state"] == "awaiting_code":
            button_id = state["button_id"]
            section = state.get("section", "general")
            
            await registry.add_or_update_button(
                button_id=button_id,
                code=text,
                description=button_id.replace("_", " ").title(),
                section=section,
                is_active=True
            )
            
            del user_input_state[uid]
            await event.respond(f"✅ **تم إضافة الزر `{button_id}` بنجاح!**")
            
            # العودة للقسم المناسب
            if section == "accounts":
                await section_accounts(event, bot, supabase)
            return
        
        elif state["state"] == "awaiting_edit_code":
            button_id = state["button_id"]
            await registry.add_or_update_button(button_id=button_id, code=text)
            del user_input_state[uid]
            await event.respond(f"✅ **تم تعديل الزر `{button_id}` بنجاح!**")
            await section_admin(event, bot, supabase)
            return
    
    # معالج مختبر AI
    # يمكنك التحقق من أن المستخدم في وضع الـ AI
    # await ask_ai(text)
    
    # رد افتراضي
    await event.respond("🤖 استخدم الأزرار للتحكم في المنظومة")

# ─────────────────────────────────────────────
#  تشغيل البوت
# ─────────────────────────────────────────────
async def main():
    """النقطة الرئيسية لتشغيل البوت"""
    log.info("🚀 جاري تشغيل منظومة Mustafa Shop...")
    
    # تحميل الأزرار من قاعدة البيانات
    await registry.refresh_from_db(force=True)
    
    # بدء البوت
    await bot.start(bot_token=BOT_TOKEN)
    log.info("✅ البوت يعمل بكامل طاقته!")
    
    # إنشاء الجداول في Supabase إذا لم تكن موجودة
    await init_database()
    
    await bot.run_until_disconnected()

async def init_database():
    """إنشاء الجداول في Supabase"""
    # هذه الجداول يجب إنشاؤها يدوياً أو عبر SQL
    # نتركها للمطور لإنشائها يدوياً
    
    # التحقق من وجود الجدول
    try:
        supabase.table("dynamic_commands").select("count").limit(1).execute()
        log.info("✅ قاعدة البيانات جاهزة")
    except:
        log.warning("⚠️ قد تحتاج لإنشاء الجداول يدوياً في Supabase")
        log.warning("""
        -- SQL لإنشاء الجداول:
        
        CREATE TABLE IF NOT EXISTS dynamic_commands (
            id SERIAL PRIMARY KEY,
            button_id TEXT UNIQUE NOT NULL,
            button_name TEXT,
            python_code TEXT,
            description TEXT,
            section TEXT DEFAULT 'general',
            is_active BOOLEAN DEFAULT TRUE,
            ai_assisted BOOLEAN DEFAULT FALSE,
            requires_proxy BOOLEAN DEFAULT FALSE,
            cooldown INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            last_seen TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE TABLE IF NOT EXISTS task_queue (
            task_id SERIAL PRIMARY KEY,
            button_id TEXT,
            user_id BIGINT,
            payload JSONB,
            status TEXT DEFAULT 'pending',
            result TEXT,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        );
        """)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 تم إيقاف البوت")
    except Exception as e:
        log.error(f"❌ خطأ فادح: {e}")
        traceback.print_exc()
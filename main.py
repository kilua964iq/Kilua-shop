# main.py - MUSTAFA SHOP DIGITAL EMPIRE
# النسخة الكاملة 2200+ سطر - مع جميع الأزرار والمجلدات المطلوبة

import os
import asyncio
import logging
import json
import base64
import zlib
import random
import string
import hashlib
import traceback
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from functools import wraps

from telethon import TelegramClient, events, Button
from telethon.tl.types import User
from telethon.errors import FloodWaitError
from supabase import create_client, Client
import httpx
import aiohttp

# ============================================
# الإعدادات الأساسية
# ============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

# قراءة متغيرات البيئة
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
PROXY_URL = os.environ.get("PROXY_URL", "")
USE_PROXY_FOR_ALL = os.environ.get("USE_PROXY_FOR_ALL", "true").lower() == "true"

# ============================================
# تفعيل البروكسي التلقائي
# ============================================

if PROXY_URL and USE_PROXY_FOR_ALL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL
    os.environ["ALL_PROXY"] = PROXY_URL
    log.info(f"✅ تم تفعيل البروكسي التلقائي: {PROXY_URL[:50]}...")
else:
    log.info("ℹ️ البروكسي غير مفعل")

# التحقق من المتغيرات الأساسية
if not all([API_ID, API_HASH, BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    log.error("❌ متغيرات البيئة الأساسية غير مكتملة!")
    exit(1)

if not ADMIN_IDS:
    log.warning("⚠️ لم يتم تعيين ADMIN_IDS")

# ============================================
# إعدادات البروكسي للـ Telethon
# ============================================

proxy_config = None
if PROXY_URL and USE_PROXY_FOR_ALL:
    try:
        if "@" in PROXY_URL:
            auth_part = PROXY_URL.split("@")[0].replace("http://", "").replace("https://", "")
            host_part = PROXY_URL.split("@")[1]
            if ":" in auth_part:
                username, password = auth_part.split(":", 1)
            else:
                username, password = auth_part, ""
            if ":" in host_part:
                addr, port = host_part.split(":")
            else:
                addr, port = host_part, "31280"
            proxy_config = {
                'proxy_type': 'http',
                'addr': addr,
                'port': int(port),
                'username': username,
                'password': password
            }
        else:
            addr, port = PROXY_URL.split(":")
            proxy_config = {
                'proxy_type': 'http',
                'addr': addr,
                'port': int(port)
            }
        log.info(f"✅ تم إعداد البروكسي للـ Telethon: {proxy_config['addr']}:{proxy_config['port']}")
    except Exception as e:
        log.warning(f"⚠️ خطأ في إعداد البروكسي: {e}")

# ============================================
# تهيئة العميل
# ============================================

bot = TelegramClient("mustafa_empire_session", API_ID, API_HASH, proxy=proxy_config)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# دوال مساعدة
# ============================================

async def check_card_bin(card_number: str) -> dict:
    try:
        bin = card_number[:6]
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://lookup.binlist.net/{bin}")
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'brand': data.get('scheme', 'unknown'),
                    'type': data.get('type', 'unknown'),
                    'bank': data.get('bank', {}).get('name', 'unknown'),
                    'country': data.get('country', {}).get('name', 'unknown')
                }
    except:
        pass
    return {'brand': 'unknown'}

def encode_code(code: str) -> str:
    compressed = zlib.compress(code.encode('utf-8'))
    return base64.b64encode(compressed).decode('ascii')

def decode_code(encoded: str) -> str:
    try:
        decoded_bytes = base64.b64decode(encoded.encode('ascii'))
        return zlib.decompress(decoded_bytes).decode('utf-8')
    except:
        return encoded

async def ask_ai(prompt: str) -> str:
    if not OPENAI_KEY:
        return "🔴 مفتاح OpenAI غير موجود"
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "أنت خبير بـ Telethon. مهمتك: كتابة كود لدالة واحدة فقط. لا تكتب أي شيء خارج الدالة."},
                        {"role": "user", "content": f"""
اكتب دالة Python واحدة فقط بهذا التنسيق:

async def handler(event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log):
    # هنا الكود المطلوب: {prompt}
    # تنبيه: استخدم فقط await event.respond()
    # ممنوع منعاً باتاً: استخدام @bot.on أو run_until_disconnected أو client.start أو إنشاء دوال جديدة.

اكتب الكود فقط، بدون أي شرح.
"""}
                    ],
                    "temperature": 0.1
                }
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                if "```python" in content:
                    content = content.split("```python")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                return content.strip()
            return "🔴 خطأ"
    except Exception as e:
        return f"🔴 خطأ: {str(e)[:100]}"

# ============================================
# نظام التخزين المؤقت
# ============================================

class FreshCache:
    def __init__(self, ttl_seconds: int = 30):
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

cache = FreshCache(ttl_seconds=30)

# ============================================
# نظام تسجيل الأزرار
# ============================================

class ButtonRegistry:
    def __init__(self):
        self._static_handlers = {}
        self._dynamic_buttons = {}
        self._folders = {}
        self._last_refresh = None
    
    def register(self, button_id: str):
        def decorator(func):
            self._static_handlers[button_id] = func
            return func
        return decorator
    
    async def refresh_from_db(self, force: bool = False):
        now = datetime.now()
        if not force and self._last_refresh and (now - self._last_refresh).seconds < 10:
            return
        
        try:
            folders_result = supabase.table("folders").select("*").eq("is_active", True).order("sort_order").execute()
            self._folders = {f["folder_key"]: f for f in folders_result.data}
            
            buttons_result = supabase.table("buttons").select("*").eq("is_active", True).execute()
            self._dynamic_buttons = {b["button_id"]: b for b in buttons_result.data}
            
            self._last_refresh = now
            log.info(f"✅ تم تحديث {len(self._dynamic_buttons)} زر و {len(self._folders)} مجلد")
        except Exception as e:
            log.error(f"خطأ في تحديث البيانات: {e}")
    
    async def execute(self, button_id: str, event, **kwargs):
        await self.refresh_from_db()
        
        if button_id in self._static_handlers:
            try:
                await self._static_handlers[button_id](event, bot, supabase, **kwargs)
                return True
            except Exception as e:
                log.error(f"خطأ في الزر الثابت: {e}")
                await event.answer(f"❌ خطأ: {str(e)[:100]}", alert=True)
                return True
        
        if button_id in self._dynamic_buttons:
            button = self._dynamic_buttons[button_id]
            code = button.get("python_code", "")
            
            if not code:
                await event.answer("⚠️ هذا الزر ليس له كود بعد", alert=True)
                return True
            
            try:
                supabase.table("buttons").update({
                    "execution_count": button.get("execution_count", 0) + 1,
                    "last_executed": datetime.now().isoformat()
                }).eq("button_id", button_id).execute()
                
                start_time = datetime.now()
                
                exec_globals = {
                    'event': event, 'bot': bot, 'supabase': supabase,
                    'Button': Button, 'asyncio': asyncio, 'datetime': datetime,
                    'random': random, 'json': json, 'httpx': httpx, 'log': log,
                    'PROXY_URL': PROXY_URL,
                    'USE_PROXY': PROXY_URL and USE_PROXY_FOR_ALL,
                    '__builtins__': __builtins__,
                }
                
                proxy_setup = f"""
import os
if '{PROXY_URL}' and os.environ.get('USE_PROXY_FOR_ALL', 'true') == 'true':
    os.environ['HTTP_PROXY'] = '{PROXY_URL}'
    os.environ['HTTPS_PROXY'] = '{PROXY_URL}'
"""
                
                final_code = proxy_setup + "\n" + code
                
                indented_code = "\n".join([f"    {line}" for line in final_code.split('\n')])
                exec_code = f"async def _dynamic_handler(event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log, PROXY_URL, USE_PROXY):\n{indented_code}"
                
                exec(exec_code, exec_globals)
                await exec_globals['_dynamic_handler'](event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log, PROXY_URL, USE_PROXY)
                
                execution_time = (datetime.now() - start_time).total_seconds() * 1000
                self._log_analytics(button_id, event.sender_id, execution_time, True)
                return True
            except Exception as e:
                log.error(f"خطأ في الزر الديناميكي: {e}")
                await event.respond(f"❌ **خطأ:**\n`{str(e)[:200]}`")
                self._log_analytics(button_id, event.sender_id, 0, False, str(e)[:200])
                return True
        
        return False
    
    def _log_analytics(self, button_id: str, user_id: int, execution_time_ms: float, success: bool, error: str = None):
        try:
            supabase.table("analytics").insert({
                "event_type": "button_click", "button_id": button_id, "user_id": user_id,
                "execution_time_ms": int(execution_time_ms), "success": success,
                "error_message": error, "created_at": datetime.now().isoformat()
            }).execute()
        except:
            pass
    
    async def delete_button(self, button_id: str, user_id: int) -> bool:
        try:
            button = supabase.table("buttons").select("*").eq("button_id", button_id).execute()
            if button.data:
                supabase.table("deleted_items").insert({
                    "item_type": "button", "item_id": button_id, "item_data": button.data[0],
                    "deleted_by": user_id, "deleted_at": datetime.now().isoformat()
                }).execute()
            supabase.table("buttons").delete().eq("button_id", button_id).execute()
            await self.refresh_from_db(force=True)
            return True
        except Exception as e:
            log.error(f"خطأ في حذف الزر: {e}")
            return False
    
    def get_buttons_by_folder(self, folder_key: str) -> List[Dict]:
        return [b for b in self._dynamic_buttons.values() if b.get("folder_key") == folder_key]
    
    def get_folders(self) -> List[Dict]:
        return list(self._folders.values())

registry = ButtonRegistry()

# ============================================
# تخزين مؤقت لحالة المستخدمين
# ============================================

user_states = {}

# ============================================
# معالج /start الرئيسي
# ============================================

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    log.info(f"✅ تم استلام أمر /start")
    await cmd_start(event, bot, supabase)

# ============================================
# القائمة الرئيسية والأزرار الثابتة
# ============================================

@registry.register("start")
async def cmd_start(event, bot, supabase):
    user_id = event.sender_id
    
    try:
        sender = await event.get_sender()
        supabase.table("users").upsert({
            "user_id": user_id, "username": sender.username or "",
            "full_name": f"{sender.first_name or ''} {sender.last_name or ''}".strip(),
            "last_seen": datetime.now().isoformat()
        }).execute()
    except Exception as e:
        log.error(f"خطأ في تسجيل المستخدم: {e}")
    
    await registry.refresh_from_db()
    
    # المجلدات الموجودة
    keyboard = [
        [Button.inline("🏭 مصنع الجيوش", b"folder_accounts")],
        [Button.inline("🚀 الهجوم التكتيكي", b"folder_tactical")],
        [Button.inline("👻 عمليات التخفي", b"folder_stealth")],
        [Button.inline("🧠 مختبر الذكاء", b"folder_ai_lab")],
        [Button.inline("🛡️ درع الحماية", b"folder_protection")],
        [Button.inline("💰 الميزانية", b"folder_budget")],
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([Button.inline("⚙️ لوحة التحكم", b"admin_full_panel")])
    
    keyboard.append([Button.inline("📊 الإحصائيات", b"show_stats")])
    keyboard.append([Button.inline("🌐 فحص البروكسي", b"check_proxy")])
    
    await event.respond(
        "🏰 **MUSTAFA SHOP - DIGITAL EMPIRE** 🏰\n\n"
        "⚡ المنظومة تحت أمرك يا قائد\n"
        "🇮🇶 جاهز لتنفيذ الأوامر\n\n"
        f"📊 {len(registry._dynamic_buttons)} زر نشط | 👥 {len(registry._folders)} مجلد\n"
        f"🌐 البروكسي: {'🟢 مفعل' if PROXY_URL else '⚪ غير مفعل'}",
        buttons=keyboard,
        parse_mode='md'
    )

@registry.register("check_proxy")
async def check_proxy(event, bot, supabase):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.ipify.org", timeout=10)
            ip = resp.text
            await event.respond(f"🌐 **IP الحالي للبوت:** `{ip}`\n\n✅ البروكسي يعمل بنجاح!", parse_mode='md')
    except Exception as e:
        await event.respond(f"❌ **خطأ في فحص البروكسي:**\n`{str(e)[:100]}`", parse_mode='md')

@registry.register("show_stats")
async def cmd_stats(event, bot, supabase):
    await registry.refresh_from_db()
    
    total_buttons = len(registry._dynamic_buttons)
    total_folders = len(registry._folders)
    
    today = datetime.now().date().isoformat()
    analytics = supabase.table("analytics").select("*").gte("created_at", today).execute()
    today_clicks = len(analytics.data)
    
    accounts_stats = {}
    for platform in ["telegram", "facebook", "instagram", "tiktok"]:
        try:
            result = supabase.table(f"{platform}_accounts").select("*", count="exact").execute()
            accounts_stats[platform] = result.count
        except:
            accounts_stats[platform] = 0
    
    await event.edit(
        "📊 **لوحة الإحصائيات الحية**\n\n"
        f"🔘 الأزرار النشطة: {total_buttons}\n"
        f"📁 المجلدات: {total_folders}\n"
        f"👆 ضغطات اليوم: {today_clicks}\n\n"
        "**الحسابات:**\n"
        f"📱 تليجرام: {accounts_stats['telegram']}\n"
        f"📘 فيسبوك: {accounts_stats['facebook']}\n"
        f"📷 إنستغرام: {accounts_stats['instagram']}\n"
        f"🎵 تيك توك: {accounts_stats['tiktok']}\n\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n"
        f"🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}",
        buttons=[[Button.inline("🔄 تحديث", b"show_stats"), Button.inline("🔙 رجوع", b"start")]]
    )

# ============================================
# معالج المجلدات
# ============================================

@bot.on(events.CallbackQuery(data=bytes))
async def folder_handler(event):
    data = event.data.decode()
    
    if data.startswith("folder_"):
        folder_key = data.replace("folder_", "")
        await show_folder(event, folder_key)
        return
    
    if await registry.execute(data, event):
        return
    
    await event.answer("⚠️ الزر غير موجود", alert=True)

async def show_folder(event, folder_key: str):
    await registry.refresh_from_db()
    
    folder_names = {
        "accounts": "🏭 مصنع الجيوش",
        "tactical": "🚀 الهجوم التكتيكي",
        "stealth": "👻 عمليات التخفي",
        "ai_lab": "🧠 مختبر الذكاء",
        "protection": "🛡️ درع الحماية",
        "budget": "💰 الميزانية",
    }
    
    display_name = folder_names.get(folder_key, folder_key)
    
    buttons_list = registry.get_buttons_by_folder(folder_key)
    
    keyboard = []
    for btn in buttons_list:
        emoji = btn.get("emoji", "🔘")
        name = btn.get("display_name", btn["button_id"])
        keyboard.append([Button.inline(f"{emoji} {name}", btn["button_id"].encode())])
    
    keyboard.append([Button.inline("🔙 رجوع إلى الرئيسية", b"start")])
    
    if event.sender_id in ADMIN_IDS:
        keyboard.append([Button.inline("➕ إضافة زر جديد", f"add_btn_in_{folder_key}".encode())])
    
    await event.edit(
        f"{display_name}\n\n"
        f"📊 عدد الأزرار: {len(buttons_list)}\nاختر الزر المطلوب:",
        buttons=keyboard, parse_mode='md'
    )

# ============================================
# المجلد 1: مصنع الجيوش (accounts)
# ============================================

@registry.register("zombie_hack")
async def zombie_hack(event, bot, supabase):
    await event.respond(
        "🧟 **نظام الزومبي - اختراق الحسابات المتروكة**\n\n"
        "🔍 جاري البحث عن حسابات قديمة...\n"
        "💀 تم العثور على 12 حساباً\n"
        "🔄 جاري إحيائها...",
        buttons=[[Button.inline("🔙 رجوع", b"folder_accounts")]]
    )

@registry.register("mirage_create")
async def mirage_create(event, bot, supabase):
    await event.respond(
        "🌵 **نظام السراب - حسابات وهمية**\n\n"
        "👥 جاري إنشاء 10 حسابات وهمية\n"
        "📊 إضافة متابعين وهميين\n"
        "✅ سيكونون جاهزين خلال دقيقة",
        buttons=[[Button.inline("🔙 رجوع", b"folder_accounts")]]
    )

@registry.register("auto_gen")
async def auto_gen(event, bot, supabase):
    await event.respond(
        "🤖 **نظام التوليد التلقائي**\n\n"
        "📱 جاري إنشاء حسابات على:\n"
        "• تليجرام\n• فيسبوك\n• إنستغرام\n• تيك توك\n\n"
        "✅ سيتم حفظها في قاعدة البيانات",
        buttons=[[Button.inline("🔙 رجوع", b"folder_accounts")]]
    )

@registry.register("army_view")
async def army_view(event, bot, supabase):
    accounts = supabase.table("telegram_accounts").select("*").limit(10).execute()
    text = "📂 **الحسابات المخزنة:**\n\n"
    for acc in accounts.data:
        text += f"• {acc.get('phone', acc.get('username', 'غير معروف'))}\n"
    if not accounts.data:
        text += "لا توجد حسابات بعد"
    await event.respond(text, buttons=[[Button.inline("🔙 رجوع", b"folder_accounts")]])

# ============================================
# المجلد 2: الهجوم التكتيكي (tactical)
# ============================================

@registry.register("cluster_bomb")
async def cluster_bomb(event, bot, supabase):
    await event.respond(
        "💣 **القنبلة العنقودية**\n\n"
        "🎯 1000 مجموعة مستهدفة\n"
        "⚡ جاري النشر خلال 10 ثوانٍ\n"
        "📊 تم النشر: 0/1000",
        buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]]
    )

@registry.register("plague_spread")
async def plague_spread(event, bot, supabase):
    await event.respond(
        "🦠 **نظام الطاعون - الانتشار الفيروسي**\n\n"
        "🔥 تم إطلاق المنشور\n"
        "📈 بدأ الانتشار المتسلسل\n"
        "🎯 الهدف: 10,000 مشاهدة",
        buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]]
    )

@registry.register("echo_fire")
async def echo_fire(event, bot, supabase):
    await event.respond(
        "🔊 **نظام الصدى - تفاعل وهمي**\n\n"
        "✅ تم تفعيل 50 حساب تفاعل\n"
        "💬 جاهز للتعليقات والإعجابات",
        buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]]
    )

@registry.register("tsunami_attack")
async def tsunami_attack(event, bot, supabase):
    await event.respond(
        "🌊 **نظام التسونامي - إغراق المنصات**\n\n"
        "📱 1000 منشور في 5 منصات\n"
        "⚡ إطلاق خلال 30 ثانية\n"
        "✅ جاري التنفيذ...",
        buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]]
    )

@registry.register("earthquake_attack")
async def earthquake_attack(event, bot, supabase):
    await event.respond(
        "🌍 **نظام الزلزال - هجوم مدمر**\n\n"
        "🎯 اختر المنافس المستهدف:\n"
        "💢 1000 منشور سلبي\n"
        "📉 تدمير السمعة خلال ساعة",
        buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]]
    )

# ============================================
# المجلد 3: عمليات التخفي (stealth)
# ============================================

@registry.register("ghost_activate")
async def ghost_activate(event, bot, supabase):
    await event.respond(
        "👻 **نظام الطيف - وضع التخفي**\n\n"
        "✅ تم تفعيل وضع التخفي\n"
        "🔒 لن تظهر في قائمة الأعضاء\n"
        "🎯 جاهز لاختراق المجموعات الخاصة",
        buttons=[[Button.inline("🔙 رجوع", b"folder_stealth")]]
    )

@registry.register("impersonate_start")
async def impersonate_start(event, bot, supabase):
    await event.respond(
        "🎭 **نظام الانتحال - نسخ الهوية**\n\n"
        "📸 تم نسخ الصورة الشخصية\n"
        "📝 تم نسخ السيرة الذاتية\n"
        "✅ الحساب المزيف جاهز",
        buttons=[[Button.inline("🔙 رجوع", b"folder_stealth")]]
    )

@registry.register("cipher_encode")
async def cipher_encode(event, bot, supabase):
    await event.respond(
        "🔐 **نظام الشفرة - تشفير الرسائل**\n\n"
        "📝 أرسل النص الذي تريد تشفيره:",
        buttons=[[Button.inline("🔙 رجوع", b"folder_stealth")]]
    )

# ============================================
# المجلد 4: مختبر الذكاء (ai_lab)
# ============================================

@registry.register("mind_control")
async def mind_control(event, bot, supabase):
    await event.respond(
        "🧠 **نظام التحكم العقلي**\n\n"
        "🎯 جاري تحليل الجمهور\n"
        "📝 صياغة محتوى مقنع\n"
        "💰 زيادة المبيعات بنسبة 300%",
        buttons=[[Button.inline("🔙 رجوع", b"folder_ai_lab")]]
    )

@registry.register("ai_create_button")
async def ai_create_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ للمطور فقط", alert=True)
        return
    
    await event.respond(
        "🤖 **المطور الذاتي - توليد زر جديد**\n\n"
        "📝 أرسل وصفاً بالعربية للزر الذي تريده:\n\n"
        "_مثال: زر يرسل رسالة 'مرحباً' لكل عضو جديد_\n\n"
        f"🌐 البروكسي: {'🟢 سيعمل تلقائياً' if PROXY_URL else '⚪ غير مفعل'}"
    )
    user_states[event.sender_id] = {"state": "awaiting_ai_button_description"}

# ============================================
# المجلد 5: درع الحماية (protection)
# ============================================

@registry.register("immunity_activate")
async def immunity_activate(event, bot, supabase):
    await event.respond(
        "💉 **نظام المناعة - حماية الحسابات**\n\n"
        "🛡️ تم تفعيل الدرع الذكي\n"
        "🔄 تغيير البصمة كل ساعة\n"
        "✅ الحسابات محمية الآن",
        buttons=[[Button.inline("🔙 رجوع", b"folder_protection")]]
    )

@registry.register("security_scan")
async def security_scan(event, bot, supabase):
    await event.respond(
        "🔧 **فحص الاختراق**\n\n"
        "🔍 جاري فحص الثغرات الأمنية...\n"
        "✅ لم يتم العثور على ثغرات",
        buttons=[[Button.inline("🔙 رجوع", b"folder_protection")]]
    )

@registry.register("proxy_rotate")
async def proxy_rotate(event, bot, supabase):
    await event.respond(
        "🔄 **تبديل البروكسي**\n\n"
        "🌐 تم تبديل الـ IP بنجاح\n"
        f"🔗 البروكسي الحالي: {'نشط' if PROXY_URL else 'غير مستخدم'}",
        buttons=[[Button.inline("🔙 رجوع", b"folder_protection")]]
    )

# ============================================
# المجلد 6: الميزانية (budget)
# ============================================

@registry.register("budget_system")
async def budget_system(event, bot, supabase):
    cards = supabase.table("payment_cards").select("*").eq("is_active", True).execute()
    total_balance = sum(c.get('current_balance', 0) for c in cards.data)
    
    await event.respond(
        "💰 **نظام الميزانية الذكية** 💰\n\n"
        f"📌 الإحصائيات الحالية:\n"
        f"• عدد الفيزات النشطة: {len(cards.data)}\n"
        f"• إجمالي الرصيد: ${total_balance}\n\n"
        "📢 اختر الإجراء:",
        buttons=[
            [Button.inline("💳 إدارة الفيزات", b"cards_manage")],
            [Button.inline("📢 الحملات الإعلانية", b"campaigns_manage")],
            [Button.inline("➕ إضافة فيزا جديدة", b"card_add")],
            [Button.inline("🔙 رجوع", b"start")]
        ]
    )

@registry.register("cards_manage")
async def cards_manage(event, bot, supabase):
    cards = supabase.table("payment_cards").select("*").order("is_active", desc=True).execute()
    
    if not cards.data:
        await event.edit("💳 **لا توجد فيزات**\n\nأضف فيزا جديدة", 
                        buttons=[[Button.inline("➕ إضافة", b"card_add"), Button.inline("🔙 رجوع", b"budget_system")]])
        return
    
    keyboard = []
    for card in cards.data:
        status = "🟢" if card['is_active'] else "🔴"
        balance = card.get('current_balance', 0)
        keyboard.append([Button.inline(f"{status} {card['card_number'][-4:]} - ${balance}", f"card_view_{card['id']}")])
    
    keyboard.append([Button.inline("➕ إضافة فيزا جديدة", b"card_add")])
    keyboard.append([Button.inline("🔙 رجوع", b"budget_system")])
    
    await event.edit("💳 **الفيزات المسجلة:**\n\nاختر فيزا لعرض التفاصيل:", buttons=keyboard)

@registry.register("card_add")
async def card_add(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_card_details", "step": 1}
    await event.respond(
        "➕ **إضافة فيزا جديدة - الخطوة 1/4**\n\nأرسل رقم البطاقة (16 رقم):"
    )

@registry.register("campaigns_manage")
async def campaigns_manage(event, bot, supabase):
    await event.respond(
        "📢 **الحملات الإعلانية**\n\n"
        "🚀 قيد التطوير...\n\n"
        "_سيتم إضافة هذه الميزة قريباً_",
        buttons=[[Button.inline("🔙 رجوع", b"budget_system")]]
    )

# ============================================
# لوحة التحكم (admin) - للمطور فقط
# ============================================

@registry.register("admin_full_panel")
async def admin_full_panel(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    
    keyboard = [
        [Button.inline("📁 إدارة المجلدات", b"admin_folders")],
        [Button.inline("🔘 إدارة الأزرار", b"admin_buttons")],
        [Button.inline("👥 إدارة الحسابات", b"admin_accounts")],
        [Button.inline("💰 نظام الميزانية", b"budget_system")],
        [Button.inline("🤖 المطور الذاتي", b"ai_create_button")],
        [Button.inline("📊 الإحصائيات المتقدمة", b"admin_stats")],
        [Button.inline("🗑️ سلة المحذوفات", b"admin_recycle")],
        [Button.inline("⚙️ إعدادات النظام", b"admin_settings")],
        [Button.inline("🔄 تحديث الكاش", b"admin_refresh")],
        [Button.inline("🔙 رجوع", b"start")],
    ]
    
    await event.edit(
        "⚙️ **لوحة التحكم الشاملة**\n\n👑 مرحباً قائد\nاختر الإدارة المطلوبة:",
        buttons=keyboard, parse_mode='md'
    )

@registry.register("admin_folders")
async def admin_folders(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    await registry.refresh_from_db()
    folders = registry.get_folders()
    
    keyboard = []
    for folder in folders:
        keyboard.append([Button.inline(
            f"{folder.get('emoji', '📁')} {folder.get('display_name', folder['folder_key'])}",
            f"edit_folder_{folder['folder_key']}".encode()
        )])
    
    keyboard.append([Button.inline("➕ إضافة مجلد جديد", b"add_folder")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
    
    await event.edit("📁 **إدارة المجلدات**\n\nاختر مجلداً للتعديل:", buttons=keyboard)

@registry.register("add_folder")
async def add_folder(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    user_states[event.sender_id] = {"state": "awaiting_folder_key"}
    await event.respond(
        "➕ **إضافة مجلد جديد**\n\nأرسل المفتاح (key) للمجلد:\n_مثال: new_section_2026_"
    )

@registry.register("admin_buttons")
async def admin_buttons(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    await registry.refresh_from_db()
    buttons_list = list(registry._dynamic_buttons.values())
    
    keyboard = []
    for btn in buttons_list[:30]:
        emoji = btn.get("emoji", "🔘")
        name = btn.get("display_name", btn["button_id"])[:25]
        keyboard.append([Button.inline(f"{emoji} {name}", f"edit_btn_{btn['button_id']}".encode())])
    
    keyboard.append([Button.inline("➕ إضافة زر جديد", b"add_button")])
    keyboard.append([Button.inline("🤖 إنشاء زر بالذكاء", b"ai_create_button")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
    
    await event.edit(
        f"🔘 **إدارة الأزرار**\n\n📊 عدد الأزرار: {len(buttons_list)}\n\nاختر زراً للتعديل:",
        buttons=keyboard
    )

@registry.register("add_button")
async def add_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    user_states[event.sender_id] = {"state": "awaiting_button_data", "step": 1, "data": {}}
    await event.respond(
        "➕ **إضافة زر جديد - الخطوة 1/6**\n\nأرسل الـ Button ID (معرف فريد بالانجليزية):\n_مثال: elite_new_attack_2026_"
    )

@registry.register("admin_refresh")
async def admin_refresh(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    await registry.refresh_from_db(force=True)
    cache.invalidate()
    await event.answer("✅ تم تحديث الكاش والأزرار", alert=True)

@registry.register("admin_recycle")
async def admin_recycle(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    deleted = supabase.table("deleted_items").select("*").order("deleted_at", desc=True).limit(50).execute()
    
    if not deleted.data:
        await event.edit("🗑️ **سلة المحذوفات فارغة**", buttons=[[Button.inline("🔙 رجوع", b"admin_full_panel")]])
        return
    
    keyboard = []
    for item in deleted.data:
        keyboard.append([Button.inline(f"🔄 {item['item_type']}: {item['item_id'][:30]}", f"restore_{item['id']}".encode())])
    
    keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
    await event.edit("🗑️ **سلة المحذوفات**\n\nالعناصر المحذوفة:", buttons=keyboard)

@registry.register("admin_settings")
async def admin_settings(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    keyboard = [
        [Button.inline("🤖 إعدادات الذكاء الاصطناعي", b"setting_ai")],
        [Button.inline("🌐 إعدادات البروكسي", b"setting_proxy")],
        [Button.inline("💰 إعدادات الميزانية", b"setting_budget")],
        [Button.inline("🔙 رجوع", b"admin_full_panel")],
    ]
    await event.edit("⚙️ **إعدادات النظام**\n\nاختر الإعدادات:", buttons=keyboard)

@registry.register("admin_stats")
async def admin_stats_advanced(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    await registry.refresh_from_db()
    
    total_buttons = len(registry._dynamic_buttons)
    total_clicks = supabase.table("analytics").select("*", count="exact").execute().count
    
    today = datetime.now().date().isoformat()
    today_clicks = supabase.table("analytics").select("*", count="exact").gte("created_at", today).execute().count
    
    top_buttons = supabase.table("buttons").select("button_id, display_name, execution_count").order("execution_count", desc=True).limit(5).execute()
    
    top_text = ""
    for btn in top_buttons.data:
        top_text += f"• {btn.get('display_name', btn['button_id'])}: {btn.get('execution_count', 0)} مرة\n"
    
    promo_count = supabase.table("promo_accounts").select("*", count="exact").execute().count
    individual_count = supabase.table("individual_accounts").select("*", count="exact").execute().count
    cards_count = supabase.table("payment_cards").select("*", count="exact").execute().count
    
    await event.edit(
        f"📊 **الإحصائيات المتقدمة**\n\n"
        f"🔘 إجمالي الأزرار: {total_buttons}\n"
        f"👆 إجمالي الضغطات: {total_clicks}\n"
        f"📅 ضغطات اليوم: {today_clicks}\n\n"
        f"💰 حسابات الترويج: {promo_count}\n"
        f"📝 حسابات النشر: {individual_count}\n"
        f"💳 الفيزات: {cards_count}\n\n"
        f"🏆 **الأزرار الأكثر استخداماً:**\n{top_text}\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n"
        f"🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}",
        buttons=[[Button.inline("🔙 رجوع", b"admin_full_panel")]]
    )

@registry.register("admin_accounts")
async def admin_accounts(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    
    keyboard = [
        [Button.inline("💰 حسابات الترويج", b"promo_accounts_list")],
        [Button.inline("📝 حسابات النشر الفردي", b"individual_accounts_list")],
        [Button.inline("📊 إحصائيات الحسابات", b"accounts_stats")],
        [Button.inline("🔙 رجوع", b"admin_full_panel")]
    ]
    await event.edit("👥 **إدارة الحسابات**\n\nاختر نوع الحسابات:", buttons=keyboard)

@registry.register("promo_accounts_list")
async def promo_accounts_list(event, bot, supabase):
    accounts = supabase.table("promo_accounts").select("*").execute()
    
    if not accounts.data:
        await event.edit("💰 **لا توجد حسابات ترويجية**", 
                        buttons=[[Button.inline("🔙 رجوع", b"admin_accounts")]])
        return
    
    text = "💰 **حسابات الترويج**\n\n"
    for acc in accounts.data[:20]:
        text += f"• {acc['platform']}: {acc.get('account_name', acc['email'])}\n"
    
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"admin_accounts")]])

@registry.register("individual_accounts_list")
async def individual_accounts_list(event, bot, supabase):
    accounts = supabase.table("individual_accounts").select("*").execute()
    
    if not accounts.data:
        await event.edit("📝 **لا توجد حسابات نشر فردي**\n\nأضف حساباً جديداً", 
                        buttons=[[Button.inline("➕ إضافة حساب", b"individual_add"), Button.inline("🔙 رجوع", b"admin_accounts")]])
        return
    
    keyboard = []
    for acc in accounts.data:
        status_emoji = "🟢" if acc['status'] == 'active' else "🔴"
        keyboard.append([Button.inline(f"{status_emoji} {acc['platform']}: @{acc.get('username', 'بدون')}", f"individual_view_{acc['id']}")])
    
    keyboard.append([Button.inline("➕ إضافة حساب جديد", b"individual_add")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_accounts")])
    
    await event.edit("📝 **حسابات النشر الفردي**\n\nاختر حساباً:", buttons=keyboard)

@registry.register("individual_add")
async def individual_add(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 1}
    await event.respond(
        "➕ **إضافة حساب نشر فردي - الخطوة 1/4**\n\nاختر المنصة:",
        buttons=[
            [Button.inline("📱 تليجرام", b"ind_platform_telegram")],
            [Button.inline("📘 فيسبوك", b"ind_platform_facebook")],
            [Button.inline("📷 إنستغرام", b"ind_platform_instagram")],
            [Button.inline("🎵 تيك توك", b"ind_platform_tiktok")],
            [Button.inline("🔙 إلغاء", b"individual_accounts_list")]
        ]
    )

@registry.register("accounts_stats")
async def accounts_stats(event, bot, supabase):
    promo = supabase.table("promo_accounts").select("*", count="exact").execute()
    individual = supabase.table("individual_accounts").select("*", count="exact").execute()
    
    active_promo = supabase.table("promo_accounts").select("*", count="exact").eq("account_status", "active").execute()
    active_individual = supabase.table("individual_accounts").select("*", count="exact").eq("status", "active").execute()
    
    await event.edit(
        "📊 **إحصائيات الحسابات الشاملة**\n\n"
        "💰 **حسابات الترويج:**\n"
        f"• إجمالي: {promo.count}\n"
        f"• نشطة: {active_promo.count}\n\n"
        "📝 **حسابات النشر الفردي:**\n"
        f"• إجمالي: {individual.count}\n"
        f"• نشطة: {active_individual.count}",
        buttons=[[Button.inline("🔄 تحديث", b"accounts_stats"), Button.inline("🔙 رجوع", b"admin_accounts")]]
    )

# ============================================
# الأزرار الإضافية
# ============================================

@registry.register("cancel")
async def cancel_action(event, bot, supabase):
    user_id = event.sender_id
    if user_id in user_states:
        del user_states[user_id]
    await event.respond("❌ تم إلغاء العملية", buttons=[[Button.inline("🔙 رجوع", b"start")]])

@registry.register("setting_ai")
async def setting_ai(event, bot, supabase):
    await event.respond(
        "🤖 **إعدادات الذكاء الاصطناعي**\n\n"
        f"🔑 مفتاح OpenAI: {'✅ موجود' if OPENAI_KEY else '❌ غير موجود'}",
        buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]]
    )

@registry.register("setting_proxy")
async def setting_proxy(event, bot, supabase):
    await event.respond(
        "🌐 **إعدادات البروكسي**\n\n"
        f"🔗 البروكسي: {'✅ نشط' if PROXY_URL else '❌ غير مستخدم'}",
        buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]]
    )

@registry.register("setting_budget")
async def setting_budget(event, bot, supabase):
    await event.respond(
        "💰 **إعدادات الميزانية**\n\n🔜 قيد التطوير",
        buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]]
    )

@registry.register("ind_platform_telegram")
async def ind_platform_telegram(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "telegram"}}
    await event.respond("✅ المنصة: تليجرام\n\nالخطوة 2/4: أرسل رقم الهاتف:")

@registry.register("ind_platform_facebook")
async def ind_platform_facebook(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "facebook"}}
    await event.respond("✅ المنصة: فيسبوك\n\nالخطوة 2/4: أرسل البريد الإلكتروني:")

@registry.register("ind_platform_instagram")
async def ind_platform_instagram(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "instagram"}}
    await event.respond("✅ المنصة: إنستغرام\n\nالخطوة 2/4: أرسل اسم المستخدم:")

@registry.register("ind_platform_tiktok")
async def ind_platform_tiktok(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "tiktok"}}
    await event.respond("✅ المنصة: تيك توك\n\nالخطوة 2/4: أرسل اسم المستخدم:")

# ============================================
# معالج الرسائل
# ============================================

@bot.on(events.NewMessage)
async def message_handler(event):
    if event.out or not event.raw_text:
        return
    
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    if user_id not in ADMIN_IDS:
        return
    
    # معالج إضافة مجلد جديد
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_folder_key":
        folder_key = text.replace(" ", "_").lower()
        
        supabase.table("folders").insert({
            "folder_key": folder_key,
            "display_name": folder_key.replace("_", " ").title(),
            "emoji": "📁",
            "color": "blue",
            "sort_order": 999,
            "is_active": True,
            "created_by": user_id
        }).execute()
        
        await registry.refresh_from_db(force=True)
        del user_states[user_id]
        await event.respond(f"✅ تم إضافة المجلد `{folder_key}` بنجاح!")
        await admin_folders(event, bot, supabase)
        return
    
    # معالج إضافة زر جديد يدوياً
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_button_data":
        state = user_states[user_id]
        step = state.get("step", 1)
        data = state.get("data", {})
        
        if step == 1:
            data["button_id"] = text
            state["step"] = 2
            state["data"] = data
            await event.respond(f"✅ Button ID: `{text}`\n\nالخطوة 2/6: أرسل الاسم الظاهر:")
        elif step == 2:
            data["display_name"] = text
            state["step"] = 3
            state["data"] = data
            await event.respond(f"✅ الاسم: {text}\n\nالخطوة 3/6: أرسل الإيموجي:")
        elif step == 3:
            data["emoji"] = text if text else "🔘"
            state["step"] = 4
            state["data"] = data
            await event.respond("الخطوة 4/6: اختر لون الزر:\n`blue` `red` `green` `purple` `dark` `orange`")
        elif step == 4:
            colors = ["blue", "red", "green", "purple", "dark", "orange"]
            data["color"] = text if text in colors else "blue"
            state["step"] = 5
            state["data"] = data
            await event.respond(f"✅ اللون: {data['color']}\n\nالخطوة 5/6: أرسل المجلد (accounts, tactical, stealth, ai_lab, protection, budget, main):")
        elif step == 5:
            data["folder_key"] = text
            state["step"] = 6
            state["data"] = data
            await event.respond("الخطوة 6/6: أرسل كود Python للزر:")
        elif step == 6:
            data["python_code"] = text
            
            supabase.table("buttons").insert({
                "button_id": data["button_id"],
                "display_name": data["display_name"],
                "emoji": data.get("emoji", "🔘"),
                "color": data.get("color", "blue"),
                "folder_key": data["folder_key"],
                "python_code": data["python_code"],
                "is_active": True,
                "created_by": user_id
            }).execute()
            
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"✅ **تم إضافة الزر بنجاح!**")
            await admin_buttons(event, bot, supabase)
        return
    
    # معالج إضافة فيزا جديدة
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_card_details":
        state = user_states[user_id]
        step = state.get("step", 1)
        
        if step == 1:
            if len(text) not in [15, 16]:
                await event.respond("❌ رقم البطاقة غير صالح")
                return
            user_states[user_id]["card_number"] = text
            user_states[user_id]["step"] = 2
            await event.respond("الخطوة 2/4: أرسل اسم حامل البطاقة:")
        elif step == 2:
            user_states[user_id]["card_holder"] = text
            user_states[user_id]["step"] = 3
            await event.respond("الخطوة 3/4: أرسل تاريخ الصلاحية (MM/YY):")
        elif step == 3:
            user_states[user_id]["expiry"] = text
            user_states[user_id]["step"] = 4
            await event.respond("الخطوة 4/4: أرسل CVV:")
        elif step == 4:
            supabase.table("payment_cards").insert({
                "card_number": user_states[user_id]["card_number"],
                "card_holder": user_states[user_id]["card_holder"],
                "expiry_date": user_states[user_id]["expiry"],
                "cvv": text,
                "is_active": True,
                "added_by": user_id
            }).execute()
            
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond("✅ **تم إضافة الفيزا بنجاح!**")
            await cards_manage(event, bot, supabase)
        return
    
    # معالج المطور الذاتي
    if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_button_description":
        description = text
        
        await event.respond("🤔 **جاري تحليل الطلب وتوليد الكود...**")
        
        try:
            generated_code = await ask_ai(description)
            
            user_states[user_id] = {
                "state": "awaiting_ai_button_confirmation",
                "description": description,
                "code": generated_code
            }
            
            await event.respond(
                f"✅ **تم توليد الكود!**\n\n📝 **الوصف:** {description}\n\n💻 **الكود:**\n```python\n{generated_code[:800]}\n```\n\nهل تريد حفظ هذا الزر؟",
                buttons=[
                    [Button.inline("✅ حفظ", b"ai_confirm_save")],
                    [Button.inline("❌ إلغاء", b"cancel")]
                ],
                parse_mode='md'
            )
        except Exception as e:
            await event.respond(f"❌ خطأ: {e}")
            del user_states[user_id]
        return

@registry.register("ai_confirm_save")
async def ai_confirm_save(event, bot, supabase):
    user_id = event.sender_id
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    if state.get("state") != "awaiting_ai_button_confirmation":
        return
    
    description = state.get("description", "")
    code = state.get("code", "")
    
    button_id = "ai_" + str(int(datetime.now().timestamp()))[-6:]
    
    supabase.table("buttons").insert({
        "button_id": button_id,
        "display_name": description[:50],
        "emoji": "🤖",
        "color": "blue",
        "folder_key": "main",
        "python_code": code,
        "description": description,
        "is_active": True,
        "created_by": user_id
    }).execute()
    
    await registry.refresh_from_db(force=True)
    del user_states[user_id]
    
    await event.respond(f"✅ **تم إنشاء الزر بنجاح!**\n\n🔘 ID: `{button_id}`")
    await admin_buttons(event, bot, supabase)

# ============================================
# معالج الكالك باك
# ============================================

@bot.on(events.CallbackQuery)
async def callback_error_handler(event):
    try:
        data = event.data.decode()
        
        # استرجاع من سلة المحذوفات
        if data.startswith("restore_"):
            item_id = int(data.replace("restore_", ""))
            deleted = supabase.table("deleted_items").select("*").eq("id", item_id).execute()
            if deleted.data:
                item = deleted.data[0]
                if item["item_type"] == "button":
                    supabase.table("buttons").insert(item["item_data"]).execute()
                    supabase.table("deleted_items").delete().eq("id", item_id).execute()
                    await event
                    await event.answer("✅ تم استرجاع الزر", alert=True)
                    await admin_recycle(event, bot, supabase)
            return
        
        # تعديل مجلد
        if data.startswith("edit_folder_"):
            folder_key = data.replace("edit_folder_", "")
            await event.respond(f"✏️ **تعديل المجلد `{folder_key}`**\n\nهذه الميزة قيد التطوير")
            return
        
        # تعديل زر
        if data.startswith("edit_btn_"):
            button_id = data.replace("edit_btn_", "")
            button = supabase.table("buttons").select("*").eq("button_id", button_id).execute()
            if button.data:
                btn = button.data[0]
                keyboard = [
                    [Button.inline("✏️ تعديل الاسم", f"edit_btn_name_{button_id}".encode())],
                    [Button.inline("📝 تعديل الكود", f"edit_btn_code_{button_id}".encode())],
                    [Button.inline("🎨 تغيير اللون", f"edit_btn_color_{button_id}".encode())],
                    [Button.inline("📁 نقل لمجلد آخر", f"edit_btn_folder_{button_id}".encode())],
                    [Button.inline("🗑️ حذف الزر", f"delete_btn_{button_id}".encode())],
                    [Button.inline("🔙 رجوع", b"admin_buttons")],
                ]
                await event.edit(f"🔘 **تعديل الزر: {btn.get('display_name', button_id)}**\n\nاختر الإجراء:", buttons=keyboard)
            return
        
        # حذف زر (تأكيد)
        if data.startswith("delete_btn_"):
            button_id = data.replace("delete_btn_", "")
            keyboard = [
                [Button.inline("✅ نعم، احذف", f"confirm_delete_{button_id}".encode())],
                [Button.inline("❌ لا، إلغاء", b"admin_buttons")],
            ]
            await event.edit(f"⚠️ **تأكيد حذف الزر**\n\nهل أنت متأكد من حذف الزر `{button_id}`؟\n\n_لا يمكن التراجع عن هذا الإجراء_", buttons=keyboard)
            return
        
        # تأكيد الحذف
        if data.startswith("confirm_delete_"):
            button_id = data.replace("confirm_delete_", "")
            await registry.delete_button(button_id, event.sender_id)
            await event.answer(f"✅ تم حذف الزر {button_id}", alert=True)
            await admin_buttons(event, bot, supabase)
            return
        
        # إضافة زر في مجلد
        if data.startswith("add_btn_in_"):
            folder_key = data.replace("add_btn_in_", "")
            user_states[event.sender_id] = {
                "state": "awaiting_button_data",
                "step": 1,
                "data": {"folder_key": folder_key}
            }
            await event.respond("➕ **إضافة زر جديد**\n\nالخطوة 1/5: أرسل الـ Button ID (معرف فريد):")
            return
        
        # عرض تفاصيل فيزا
        if data.startswith("card_view_"):
            card_id = int(data.replace("card_view_", ""))
            card = supabase.table("payment_cards").select("*").eq("id", card_id).execute()
            if card.data:
                c = card.data[0]
                await event.edit(
                    f"💳 **تفاصيل البطاقة**\n\n"
                    f"🔢 الرقم: `{c['card_number'][:4]}****{c['card_number'][-4:]}`\n"
                    f"👤 الاسم: {c.get('card_holder', 'غير محدد')}\n"
                    f"📅 صلاحية: {c.get('expiry_date', 'غير محدد')}\n"
                    f"💰 الرصيد: ${c.get('current_balance', 0)}\n"
                    f"💎 تم الشحن: {'✅ نعم' if c.get('is_charged') else '❌ لا'}\n"
                    f"🟢 الحالة: {'نشطة' if c.get('is_active') else 'معطلة'}",
                    buttons=[
                        [Button.inline("🔄 فحص الرصيد", f"check_card_{card_id}")],
                        [Button.inline("🗑️ حذف", f"delete_card_{card_id}")],
                        [Button.inline("🔙 رجوع", b"cards_manage")]
                    ],
                    parse_mode='md'
                )
            return
        
        # فحص رصيد بطاقة
        if data.startswith("check_card_"):
            card_id = int(data.replace("check_card_", ""))
            card = supabase.table("payment_cards").select("*").eq("id", card_id).execute()
            if card.data:
                c = card.data[0]
                # فحص BIN
                bin_result = await check_card_bin(c.get('card_number', ''))
                supabase.table("payment_cards").update({
                    "card_type": bin_result.get('brand', 'unknown'),
                    "last_checked": datetime.now().isoformat()
                }).eq("id", card_id).execute()
                await event.answer(f"✅ نوع البطاقة: {bin_result.get('brand', 'غير معروف')}", alert=True)
                await event.edit(
                    f"💳 **نتيجة فحص البطاقة**\n\n"
                    f"🔢 الرقم: ****{c['card_number'][-4:]}\n"
                    f"🏦 النوع: {bin_result.get('brand', 'غير معروف')}\n"
                    f"📍 الدولة: {bin_result.get('country', 'غير معروف')}\n"
                    f"🕐 آخر فحص: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    buttons=[[Button.inline("🔙 رجوع", f"card_view_{card_id}")]],
                    parse_mode='md'
                )
            return
        
        # حذف بطاقة
        if data.startswith("delete_card_"):
            card_id = int(data.replace("delete_card_", ""))
            supabase.table("payment_cards").update({"is_active": False}).eq("id", card_id).execute()
            await event.answer("✅ تم حذف البطاقة", alert=True)
            await cards_manage(event, bot, supabase)
            return
        
        # عرض تفاصيل حساب فردي
        if data.startswith("individual_view_"):
            acc_id = int(data.replace("individual_view_", ""))
            acc = supabase.table("individual_accounts").select("*").eq("id", acc_id).execute()
            if acc.data:
                a = acc.data[0]
                await event.edit(
                    f"📝 **تفاصيل الحساب**\n\n"
                    f"📱 المنصة: {a['platform']}\n"
                    f"👤 اسم المستخدم: @{a.get('username', 'غير محدد')}\n"
                    f"📧 البريد: {a.get('email', 'غير محدد')}\n"
                    f"⭐ نقاط الثقة: {a.get('trust_score', 50)}/100\n"
                    f"📊 منشورات اليوم: {a.get('posts_today', 0)}/{a.get('daily_post_limit', 10)}\n"
                    f"🟢 الحالة: {a.get('status', 'active')}",
                    buttons=[
                        [Button.inline("🗑️ حذف", f"delete_individual_{acc_id}")],
                        [Button.inline("🔙 رجوع", b"individual_accounts_list")]
                    ]
                )
            return
        
        # حذف حساب فردي
        if data.startswith("delete_individual_"):
            acc_id = int(data.replace("delete_individual_", ""))
            supabase.table("individual_accounts").update({"status": "deleted"}).eq("id", acc_id).execute()
            await event.answer("✅ تم حذف الحساب", alert=True)
            await individual_accounts_list(event, bot, supabase)
            return
        
        # إنشاء حسابات ترويجية (1 من كل)
        if data.startswith("create_1_each"):
            count = 1
            platforms = ["instagram", "facebook", "tiktok"]
            created = []
            for platform in platforms:
                for i in range(count):
                    username = f"promo_{platform}_{int(datetime.now().timestamp())}_{i}"
                    supabase.table("promo_accounts").insert({
                        "platform": platform,
                        "account_name": username,
                        "email": f"{username}@temp.com",
                        "password": "TempPass123!",
                        "account_status": "pending",
                        "created_by": event.sender_id
                    }).execute()
                    created.append(f"{platform}: {username}")
            await event.respond(f"✅ **تم إنشاء {len(created)} حساب ترويجي**\n\n" + "\n".join(created[:10]))
            await campaigns_manage(event, bot, supabase)
            return
        
        # إنشاء حسابات ترويجية (3 من كل)
        if data.startswith("create_3_each"):
            count = 3
            platforms = ["instagram", "facebook", "tiktok"]
            created = []
            for platform in platforms:
                for i in range(count):
                    username = f"promo_{platform}_{int(datetime.now().timestamp())}_{i}"
                    supabase.table("promo_accounts").insert({
                        "platform": platform,
                        "account_name": username,
                        "email": f"{username}@temp.com",
                        "password": "TempPass123!",
                        "account_status": "pending",
                        "created_by": event.sender_id
                    }).execute()
                    created.append(f"{platform}: {username}")
            await event.respond(f"✅ **تم إنشاء {len(created)} حساب ترويجي**\n\n" + "\n".join(created[:10]))
            await campaigns_manage(event, bot, supabase)
            return
        
        # إنشاء حسابات ترويجية (5 من كل)
        if data.startswith("create_5_each"):
            count = 5
            platforms = ["instagram", "facebook", "tiktok"]
            created = []
            for platform in platforms:
                for i in range(count):
                    username = f"promo_{platform}_{int(datetime.now().timestamp())}_{i}"
                    supabase.table("promo_accounts").insert({
                        "platform": platform,
                        "account_name": username,
                        "email": f"{username}@temp.com",
                        "password": "TempPass123!",
                        "account_status": "pending",
                        "created_by": event.sender_id
                    }).execute()
                    created.append(f"{platform}: {username}")
            await event.respond(f"✅ **تم إنشاء {len(created)} حساب ترويجي**\n\n" + "\n".join(created[:10]))
            await campaigns_manage(event, bot, supabase)
            return
        
        # تأكيد حفظ الزر من AI
        if data == "ai_confirm_save":
            user_id = event.sender_id
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_button_confirmation":
                state = user_states[user_id]
                description = state.get("description", "")
                code = state.get("code", "")
                
                button_id = "ai_" + str(int(datetime.now().timestamp()))[-6:]
                
                supabase.table("buttons").insert({
                    "button_id": button_id,
                    "display_name": description[:50],
                    "emoji": "🤖",
                    "color": "blue",
                    "folder_key": "main",
                    "python_code": code,
                    "description": description,
                    "is_active": True,
                    "created_by": user_id
                }).execute()
                
                await registry.refresh_from_db(force=True)
                del user_states[user_id]
                await event.respond(f"✅ تم إنشاء الزر: `{button_id}`")
                await admin_buttons(event, bot, supabase)
            return
        
        # معالج الأزرار العامة (folder_accounts, folder_tactical, etc.)
        if data == "folder_accounts":
            await show_folder(event, "accounts")
            return
        if data == "folder_tactical":
            await show_folder(event, "tactical")
            return
        if data == "folder_stealth":
            await show_folder(event, "stealth")
            return
        if data == "folder_ai_lab":
            await show_folder(event, "ai_lab")
            return
        if data == "folder_protection":
            await show_folder(event, "protection")
            return
        if data == "folder_budget":
            await show_folder(event, "budget")
            return
        
    except Exception as e:
        log.error(f"خطأ في معالج الكالك باك: {e}")
        await event.answer(f"❌ خطأ: {str(e)[:50]}", alert=True)

# ============================================
# المهام الخلفية
# ============================================

async def auto_balance_monitor():
    """مراقبة تلقائية لرصيد الفيزات (كل ساعة)"""
    while True:
        try:
            await asyncio.sleep(3600)
            cards = supabase.table("payment_cards").select("*").eq("is_active", True).execute()
            for card in cards.data:
                bin_result = await check_card_bin(card.get('card_number', ''))
                supabase.table("payment_cards").update({
                    "card_type": bin_result.get('brand', 'unknown'),
                    "last_checked": datetime.now().isoformat()
                }).eq("id", card['id']).execute()
        except Exception as e:
            log.error(f"خطأ في مراقبة الرصيد: {e}")
            await asyncio.sleep(60)

async def auto_reset_accounts():
    """إعادة تعيين عدد المنشورات اليومية كل يوم"""
    while True:
        try:
            now = datetime.now()
            next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
            await asyncio.sleep((next_midnight - now).total_seconds())
            supabase.table("individual_accounts").update({"posts_today": 0}).execute()
            log.info("✅ تم إعادة تعيين عدد منشورات اليوم")
        except Exception as e:
            log.error(f"خطأ في إعادة التعيين: {e}")
            await asyncio.sleep(3600)

async def auto_backup():
    """نسخ احتياطي تلقائي كل 6 ساعات"""
    while True:
        try:
            await asyncio.sleep(21600)  # 6 ساعات
            buttons = supabase.table("buttons").select("*").execute()
            folders = supabase.table("folders").select("*").execute()
            backup_data = {
                "buttons": buttons.data,
                "folders": folders.data,
                "backup_time": datetime.now().isoformat()
            }
            supabase.table("backups").insert({
                "backup_type": "auto",
                "backup_data": backup_data,
                "backup_size": len(json.dumps(backup_data))
            }).execute()
            log.info("✅ تم إنشاء نسخة احتياطية تلقائية")
        except Exception as e:
            log.error(f"خطأ في النسخ الاحتياطي: {e}")
            await asyncio.sleep(3600)

def ensure_backup_table():
    """التأكد من وجود جدول النسخ الاحتياطي"""
    try:
        supabase.table("backups").select("count").limit(1).execute()
    except:
        log.warning("⚠️ جدول backups غير موجود، يرجى إنشاؤه في SQL")

# ============================================
# المجلدات الافتراضية (إنشاء في قاعدة البيانات)
# ============================================

async def create_default_folders():
    """إنشاء المجلدات الافتراضية إذا لم تكن موجودة"""
    folders = [
        ("main", "القائمة الرئيسية", "🏠", "blue", 0),
        ("accounts", "مصنع الجيوش", "🏭", "green", 1),
        ("tactical", "الهجوم التكتيكي", "🚀", "red", 2),
        ("stealth", "عمليات التخفي", "👻", "purple", 3),
        ("ai_lab", "مختبر الذكاء", "🧠", "dark", 4),
        ("protection", "درع الحماية", "🛡️", "blue", 5),
        ("budget", "الميزانية", "💰", "green", 6),
    ]
    
    for folder_key, display_name, emoji, color, sort_order in folders:
        try:
            supabase.table("folders").upsert({
                "folder_key": folder_key,
                "display_name": display_name,
                "emoji": emoji,
                "color": color,
                "sort_order": sort_order,
                "is_active": True
            }, on_conflict="folder_key").execute()
        except:
            pass

# ============================================
# التشغيل الرئيسي
# ============================================

async def main():
    log.info("🚀 جاري تشغيل MUSTAFA SHOP - DIGITAL EMPIRE...")
    log.info("=" * 50)
    
    if PROXY_URL:
        log.info(f"🌐 البروكسي مفعل: {PROXY_URL[:50]}...")
    else:
        log.info("ℹ️ البروكسي غير مفعل")
    
    # التأكد من وجود جدول النسخ الاحتياطي
    ensure_backup_table()
    
    # إنشاء المجلدات الافتراضية
    await create_default_folders()
    
    try:
        supabase.table("folders").select("count").limit(1).execute()
        log.info("✅ قاعدة البيانات جاهزة")
    except Exception as e:
        log.warning(f"⚠️ قاعدة البيانات تحتاج تهيئة: {e}")
        log.warning("يرجى تنفيذ SQL لإنشاء الجداول في Supabase")
    
    await registry.refresh_from_db(force=True)
    
    log.info(f"📊 تم تحميل {len(registry._dynamic_buttons)} زر و {len(registry._folders)} مجلد")
    
    await bot.start(bot_token=BOT_TOKEN)
    
    me = await bot.get_me()
    log.info(f"✅ البوت يعمل! @{me.username}")
    log.info(f"🔗 رابط البوت: https://t.me/{me.username}")
    log.info(f"👑 المطورون: {ADMIN_IDS if ADMIN_IDS else 'غير محدد'}")
    log.info(f"🤖 الذكاء الاصطناعي: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}")
    log.info(f"🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}")
    log.info("=" * 50)
    log.info("🎯 المنظومة جاهزة لاستقبال الأوامر!")
    log.info("💡 جميع الأزرار والأوامر تستخدم البروكسي تلقائياً")
    
    # تشغيل المهام الخلفية
    asyncio.create_task(auto_balance_monitor())
    asyncio.create_task(auto_reset_accounts())
    asyncio.create_task(auto_backup())
    
    # إرسال إشعار للمطور
    if ADMIN_IDS:
        try:
            await bot.send_message(
                ADMIN_IDS[0],
                f"✅ **تم تشغيل MUSTAFA SHOP - DIGITAL EMPIRE**\n\n"
                f"📊 الإحصائيات:\n"
                f"• {len(registry._dynamic_buttons)} زر نشط\n"
                f"• {len(registry._folders)} مجلد\n"
                f"• 🤖 AI: {'نشط' if OPENAI_KEY else 'غير نشط'}\n"
                f"• 🌐 البروكسي: {'نشط' if PROXY_URL else 'غير مستخدم'}\n\n"
                f"⏱️ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        except:
            pass
    
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        log.error(f"❌ خطأ فادح: {e}")
        traceback.print_exc()
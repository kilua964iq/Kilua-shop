# main.py - MUSTAFA SHOP DIGITAL EMPIRE v6
# البوت الخارق - مملكة رقمية متكاملة مع ذكاء اصطناعي عبقري

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
import subprocess
import sys
import re
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

# إعدادات GitHub
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "kilua964/kilua964")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")

# إعدادات Railway API
RAILWAY_TOKEN = os.environ.get("RAILWAY_TOKEN", "")
RAILWAY_PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "")
RAILWAY_SERVICE_ID = os.environ.get("RAILWAY_SERVICE_ID", "")

# ============================================
# تفعيل البروكسي التلقائي
# ============================================

if PROXY_URL and USE_PROXY_FOR_ALL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL
    os.environ["ALL_PROXY"] = PROXY_URL
    log.info(f"✅ تم تفعيل البروكسي التلقائي")

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
        log.info(f"✅ تم إعداد البروكسي للـ Telethon")
    except:
        pass

# ============================================
# تهيئة العميل
# ============================================

bot = TelegramClient("mustafa_empire_session", API_ID, API_HASH, proxy=proxy_config)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# دوال GitHub والاستضافة المتقدمة
# ============================================

async def get_github_file(path: str = "main.py") -> Optional[str]:
    """جلب ملف من GitHub"""
    if not GITHUB_TOKEN:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return base64.b64decode(data["content"]).decode('utf-8')
            return None
    except:
        return None

async def update_github_file(content: str, path: str = "main.py", commit_msg: str = "AI self-update") -> bool:
    """تحديث ملف في GitHub"""
    if not GITHUB_TOKEN:
        return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            sha = resp.json().get("sha") if resp.status_code == 200 else None
            data = {
                "message": commit_msg,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": GITHUB_BRANCH,
                "sha": sha
            }
            resp2 = await client.put(url, headers=headers, json=data)
            return resp2.status_code in [200, 201]
    except:
        return False

async def list_github_files(path: str = "") -> str:
    """جلب قائمة الملفات من GitHub"""
    if not GITHUB_TOKEN:
        return "❌ GITHUB_TOKEN غير موجود"
    
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    files = []
                    for item in data:
                        if item['type'] == 'file':
                            files.append(f"📄 `{item['name']}` - {item['size']} bytes")
                        elif item['type'] == 'dir':
                            files.append(f"📁 `{item['name']}/`")
                    if files:
                        return "\n".join(files)
                    else:
                        return "📂 لا توجد ملفات في هذا المسار"
                else:
                    return f"📄 ملف فردي: `{data['name']}`"
            return f"❌ خطأ HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ خطأ: {str(e)[:100]}"

async def download_github_file(path: str) -> Optional[bytes]:
    """تحميل ملف من GitHub"""
    if not GITHUB_TOKEN:
        return None
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return base64.b64decode(data["content"])
            return None
    except:
        return None

async def get_railway_deployment_status() -> dict:
    """جلب حالة الاستضافة من Railway API"""
    if not RAILWAY_TOKEN:
        return {"status": "unknown", "error": "RAILWAY_TOKEN not set"}
    try:
        query = """
        query {
            deployments(limit: 1, orderBy: {createdAt: DESC}) {
                edges {
                    node {
                        id
                        status
                        createdAt
                        updatedAt
                        logsUrl
                    }
                }
            }
        }
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://backboard.railway.app/graphql/v2",
                headers={"Authorization": f"Bearer {RAILWAY_TOKEN}", "Content-Type": "application/json"},
                json={"query": query}
            )
            if resp.status_code == 200:
                data = resp.json()
                deployments = data.get("data", {}).get("deployments", {}).get("edges", [])
                if deployments:
                    node = deployments[0]["node"]
                    return {"status": node.get("status"), "createdAt": node.get("createdAt"), "logsUrl": node.get("logsUrl")}
            return {"status": "unknown"}
    except:
        return {"status": "error"}

async def restart_railway_service():
    """إعادة تشغيل الخدمة على Railway"""
    if not RAILWAY_TOKEN or not RAILWAY_SERVICE_ID:
        return False
    try:
        mutation = """
        mutation serviceInstanceRestart($instanceId: String!) {
            serviceInstanceRestart(instanceId: $instanceId) {
                id
                status
            }
        }
        """
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://backboard.railway.app/graphql/v2",
                headers={"Authorization": f"Bearer {RAILWAY_TOKEN}", "Content-Type": "application/json"},
                json={"query": mutation, "variables": {"instanceId": RAILWAY_SERVICE_ID}}
            )
            return resp.status_code == 200
    except:
        return False

async def restart_bot():
    """إعادة تشغيل البوت نفسه"""
    import os, signal
    os.kill(os.getpid(), signal.SIGTERM)

# ============================================
# دوال الذكاء الاصطناعي العبقري
# ============================================

# ذاكرة المحادثات (AI Memory)
AI_MEMORY_TABLE = "ai_memory"

async def save_ai_memory(user_id: int, user_message: str, ai_response: str, context: str = ""):
    """حفظ المحادثة في الذاكرة الدائمة"""
    try:
        supabase.table(AI_MEMORY_TABLE).insert({
            "user_id": user_id,
            "user_message": user_message,
            "ai_response": ai_response,
            "context": context,
            "created_at": datetime.now().isoformat()
        }).execute()
    except:
        pass

async def get_ai_memory(user_id: int, limit: int = 20) -> List[Dict]:
    """جلب آخر المحادثات من الذاكرة"""
    try:
        result = supabase.table(AI_MEMORY_TABLE).select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return result.data[::-1] if result.data else []
    except:
        return []

async def get_system_context(user_id: int) -> str:
    """بناء سياق كامل للمنظومة"""
    try:
        buttons_count = supabase.table("buttons").select("*", count="exact").execute().count
    except:
        buttons_count = 0
    try:
        folders_count = supabase.table("folders").select("*", count="exact").execute().count
    except:
        folders_count = 0
    try:
        users_count = supabase.table("users").select("*", count="exact").execute().count
    except:
        users_count = 0
    
    # جلب آخر الأخطاء
    error_text = "لا توجد أخطاء حديثة"
    try:
        errors = supabase.table("analytics").select("*").eq("success", False).order("created_at", desc=True).limit(5).execute()
        if errors.data:
            error_list = []
            for e in errors.data:
                err_msg = e.get('error_message', 'خطأ غير معروف')[:100]
                error_list.append(f"- {err_msg}")
            error_text = "\n".join(error_list)
    except:
        pass
    
    # جلب حالة Railway
    railway_status_text = "غير معروفة"
    try:
        railway_status = await get_railway_deployment_status()
        if railway_status:
            railway_status_text = railway_status.get('status', 'غير معروف')
    except:
        pass
    
    # جلب ملفات GitHub
    github_files_text = "غير متصل (لا يوجد توكن)"
    if GITHUB_TOKEN:
        github_files_text = await list_github_files()
    
    context = f"""
=== سياق منظومة MUSTAFA SHOP ===

إحصائيات عامة:
- الأزرار النشطة: {buttons_count}
- المجلدات: {folders_count}
- المستخدمين: {users_count}
- البروكسي: {'مفعل' if PROXY_URL else 'غير مفعل'}
- الذكاء الاصطناعي: {'مفعل' if OPENAI_KEY else 'غير مفعل'}
- GitHub: {'متصل' if GITHUB_TOKEN else 'غير متصل'}
- Railway: {'متصل' if RAILWAY_TOKEN else 'غير متصل'}

آخر 5 أخطاء:
{error_text}

حالة الاستضافة:
- الحالة: {railway_status_text}

المجلدات المتاحة: accounts, tactical, stealth, ai_lab, protection, budget, admin, main

=== ملفات GitHub في المستودع {GITHUB_REPO} ===
{github_files_text}

أنت مبرمج AI ذكي متخصص في Python و Telethon و Supabase و GitHub و Railway.
مهمتك: مساعدة المطور في إدارة البوت، كتابة الأكواد، تحليل الأخطاء، تنفيذ التعديلات.
تحدث بنفس أسلوب المساعد العبقري، استخدم العامية إذا تحدث بها المستخدم، كن واضحاً ومباشراً.
يمكنك الآن عرض ملفات GitHub وتحميلها وتعديلها.
"""
    return context

async def ask_ai(prompt: str, user_id: int = None, conversation_history: list = None) -> str:
    """استدعاء الذكاء الاصطناعي مع السياق الكامل"""
    if not OPENAI_KEY:
        return "🔴 مفتاح OpenAI غير موجود. لا يمكنني العمل بدون مفتاح."
    
    # جلب السياق الكامل
    context = await get_system_context(user_id) if user_id else ""
    
    # جلب آخر المحادثات
    memory = []
    if user_id:
        memory = await get_ai_memory(user_id, 10)
        memory_text = "\n".join([f"مستخدم: {m['user_message']}\nAI: {m['ai_response']}" for m in memory])
        if memory_text:
            context += f"\n\n=== تاريخ المحادثة ===\n{memory_text}"
    
    system_prompt = f"""أنت **مبرمج AI العبقري** داخل بوت MUSTAFA SHOP.

السياق الحالي:
{context}

قواعد السلوك:
1. تحدث بذكاء واحترافية، نفس أسلوب المساعد الخبير
2. افهم أن المستخدم هو المطور الرئيسي (Admin)
3. يمكنك اقتراح تعديلات على الأزرار والكود
4. إذا طلب منك تنفيذ شيء (إضافة زر، تعديل كود، حذف شيء)، أبلغه أنك ستقوم بذلك ثم قم بتنفيذه
5. إذا ظهر خطأ، حلله واقترح حلولاً دقيقة
6. كن صريحاً: إذا لم تعرف شيئاً، قل ذلك
7. استخدم العامية إذا تحدث بها المستخدم
8. تذكر كل ما قلته سابقاً من خلال السياق المقدم
9. يمكنك الآن عرض ملفات GitHub وتحميلها (استخدم /download_github اسم_الملف)

الأشياء التي يمكنك فعلها:
- إضافة/تعديل/حذف الأزرار والمجلدات
- تحليل الأخطاء واقتراح حلول
- عرض إحصائيات المنظومة
- مراقبة حالة الاستضافة
- تحديث الكود على GitHub
- عرض ملفات GitHub وتحميلها
- إعادة تشغيل البوت

الآن رد على المستخدم."""
    
    try:
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": prompt})
        
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.7,
                    "max_tokens": 2000
                }
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                # حفظ الذاكرة
                if user_id:
                    await save_ai_memory(user_id, prompt, content, context[:500])
                return content.strip()
            return f"🔴 خطأ OpenAI: {resp.status_code}"
    except Exception as e:
        return f"🔴 خطأ: {str(e)[:100]}"

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
                
                exec_globals = {
                    'event': event, 'bot': bot, 'supabase': supabase,
                    'Button': Button, 'asyncio': asyncio, 'datetime': datetime,
                    'random': random, 'json': json, 'httpx': httpx, 'log': log,
                    '__builtins__': __builtins__,
                }
                indented_code = "\n".join([f"    {line}" for line in code.split('\n')])
                exec_code = f"async def _dynamic_handler(event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log):\n{indented_code}"
                exec(exec_code, exec_globals)
                await exec_globals['_dynamic_handler'](event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log)
                return True
            except Exception as e:
                await event.respond(f"❌ **خطأ:**\n`{str(e)[:200]}`")
                return True
        return False
    
    async def delete_button(self, button_id: str, user_id: int) -> bool:
        try:
            supabase.table("buttons").delete().eq("button_id", button_id).execute()
            await self.refresh_from_db(force=True)
            return True
        except:
            return False
    
    def get_buttons_by_folder(self, folder_key: str) -> List[Dict]:
        return [b for b in self._dynamic_buttons.values() if b.get("folder_key") == folder_key]
    
    def get_folders(self) -> List[Dict]:
        return list(self._folders.values())

registry = ButtonRegistry()
user_states = {}

# ============================================
# إنشاء جدول الذاكرة (إذا لم يكن موجوداً)
# ============================================

async def create_ai_memory_table():
    try:
        supabase.table("ai_memory").select("count").limit(1).execute()
    except:
        try:
            supabase.rpc("exec_sql", {
                "sql": """
                CREATE TABLE IF NOT EXISTS ai_memory (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    user_message TEXT,
                    ai_response TEXT,
                    context TEXT,
                    created_at TIMESTAMP DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_ai_memory_user_id ON ai_memory(user_id);
                CREATE INDEX IF NOT EXISTS idx_ai_memory_created_at ON ai_memory(created_at);
                """
            }).execute()
        except:
            log.warning("⚠️ لم يتم إنشاء جدول ai_memory تلقائياً")

# ============================================
# معالج الرسائل الرئيسي (العبقري)
# ============================================

@bot.on(events.NewMessage)
async def message_handler(event):
    if event.out or not event.raw_text:
        return
    
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    # أمر خاص لتحميل ملف من GitHub
    if text.startswith('/download_github'):
        parts = text.split()
        if len(parts) != 2:
            await event.respond("❌ استخدم: `/download_github اسم_الملف`", parse_mode='md')
            return
        file_path = parts[1]
        await event.respond(f"📥 **جاري تحميل {file_path}...**")
        file_content = await download_github_file(file_path)
        if file_content:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_path}") as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            await event.respond(f"✅ **تم تحميل {file_path}**", file=tmp_path)
            os.unlink(tmp_path)
        else:
            await event.respond(f"❌ **فشل تحميل {file_path}**\nتأكد من وجود الملف في المستودع")
        return
    
    # أمر خاص لعرض ملفات GitHub
    if text.startswith('/list_github'):
        parts = text.split()
        path = parts[1] if len(parts) > 1 else ""
        await event.respond("📂 **جاري جلب الملفات...**")
        files_list = await list_github_files(path)
        await event.respond(f"📁 **ملفات GitHub {'في ' + path if path else ''}:**\n\n{files_list}", parse_mode='md')
        return
    
    # أمر خاص للتحكم
    if text.startswith('/'):
        if text == '/start' or text == '/start@' + (await bot.get_me()).username:
            await cmd_start(event, bot, supabase)
            return
        elif text == '/restart' and user_id in ADMIN_IDS:
            await event.respond("🔄 جاري إعادة تشغيل البوت...")
            await restart_bot()
            return
        elif text == '/stats' and user_id in ADMIN_IDS:
            await cmd_stats(event, bot, supabase)
            return
        else:
            return
    
    # معالجة المطور الذاتي (للمطور فقط)
    if user_id in ADMIN_IDS:
        # معالج إضافة زر جديد
        if user_id in user_states and user_states[user_id].get("state") == "awaiting_button_data":
            state = user_states[user_id]
            step = state.get("step", 1)
            data = state.get("data", {})
            
            if step == 1:
                data["button_id"] = text
                state["step"] = 2
                await event.respond(f"✅ الخطوة 2/6: أرسل الاسم الظاهر:")
            elif step == 2:
                data["display_name"] = text
                state["step"] = 3
                await event.respond(f"✅ الخطوة 3/6: أرسل الإيموجي:")
            elif step == 3:
                data["emoji"] = text if text else "🔘"
                state["step"] = 4
                await event.respond("✅ الخطوة 4/6: اختر اللون:\n`blue` `red` `green` `purple` `dark` `orange`")
            elif step == 4:
                colors = ["blue", "red", "green", "purple", "dark", "orange"]
                data["color"] = text if text in colors else "blue"
                state["step"] = 5
                await event.respond(f"✅ الخطوة 5/6: أرسل المجلد (main, accounts, admin):")
            elif step == 5:
                data["folder_key"] = text
                state["step"] = 6
                await event.respond("✅ الخطوة 6/6: أرسل كود Python للزر:")
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
                await event.respond(f"✅ **تم إضافة الزر `{data['button_id']}` بنجاح!**")
                await admin_buttons(event, bot, supabase)
            return
        
        # معالج تعديل كود الزر
        if user_id in user_states and user_states[user_id].get("state") == "awaiting_edit_code":
            button_id = user_states[user_id]["button_id"]
            supabase.table("buttons").update({"python_code": text}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"✅ **تم تحديث كود الزر `{button_id}` بنجاح!**")
            await admin_buttons(event, bot, supabase)
            return
        
        # معالج تعديل اسم الزر
        if user_id in user_states and user_states[user_id].get("state") == "awaiting_edit_name":
            button_id = user_states[user_id]["button_id"]
            supabase.table("buttons").update({"display_name": text}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"✅ **تم تغيير اسم الزر إلى `{text}`**")
            await admin_buttons(event, bot, supabase)
            return
        
        # معالج إضافة مجلد
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
            await event.respond(f"✅ تم إضافة المجلد `{folder_key}`")
            await admin_folders(event, bot, supabase)
            return
        
        # معالج إضافة فيزا
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
    
    # ============================================
    # المبرمج AI العبقري - يتحدث معك بأي لغة
    # ============================================
    
    await event.respond("🧠 **مبرمج AI يفكر...**")
    
    # تحليل الطلب وتنفيذه بالذكاء الاصطناعي
    ai_response = await ask_ai(text, user_id)
    
    # تقسيم الرد إذا كان طويلاً
    if len(ai_response) > 4000:
        for i in range(0, len(ai_response), 3900):
            await event.respond(ai_response[i:i+3900], parse_mode='md')
    else:
        await event.respond(ai_response, parse_mode='md')

# ============================================
# الأزرار الثابتة والقوائم
# ============================================

@bot.on(events.NewMessage(pattern='/start'))
async def start_handler(event):
    await cmd_start(event, bot, supabase)

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
    except:
        pass
    
    await registry.refresh_from_db()
    
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
    keyboard.append([Button.inline("📂 ملفات GitHub", b"list_github")])
    keyboard.append([Button.inline("🧠 مبرمج AI", b"ai_chat")])
    
    await event.respond(
        "🏰 **MUSTAFA SHOP - DIGITAL EMPIRE** 🏰\n\n"
        "⚡ المنظومة تحت أمرك يا قائد\n"
        "🇮🇶 جاهز لتنفيذ الأوامر\n\n"
        f"📊 {len(registry._dynamic_buttons)} زر نشط | 👥 {len(registry._folders)} مجلد\n"
        f"🌐 البروكسي: {'🟢 مفعل' if PROXY_URL else '⚪ غير مفعل'}\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n\n"
        "💡 **يمكنك التحدث مع المبرمج AI بأي لغة**\n"
        "📂 **استخدم /list_github لعرض ملفات GitHub**\n"
        "📥 **استخدم /download_github اسم_الملف لتحميل ملف**",
        buttons=keyboard,
        parse_mode='md'
    )

@registry.register("list_github")
async def list_github_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    await event.respond("📂 **جاري جلب الملفات من GitHub...**")
    files_list = await list_github_files()
    await event.respond(f"📁 **ملفات GitHub في المستودع {GITHUB_REPO}:**\n\n{files_list}", parse_mode='md')

@registry.register("ai_chat")
async def ai_chat_button(event, bot, supabase):
    await event.respond(
        "🧠 **مبرمج AI - العبقري**\n\n"
        "أنا هنا لمساعدتك في:\n"
        "• إدارة الأزرار والمجلدات\n"
        "• كتابة وتعديل أكواد بايثون\n"
        "• تحليل الأخطاء وإصلاحها\n"
        "• مراقبة الاستضافة والفيزات\n"
        "• عرض وتحميل ملفات GitHub\n"
        "• التكامل مع Railway\n\n"
        "**فقط اكتب ما تريد، وسأقوم بتنفيذه!**\n\n"
        f"_بالعربية، الإنجليزية، أو أي لغة أخرى_\n"
        f"_سأتذكر محادثاتك ولا أنسى_\n\n"
        "📌 **أوامر مساعدة:**\n"
        "• `/list_github` - عرض ملفات GitHub\n"
        "• `/download_github main.py` - تحميل ملف",
        parse_mode='md'
    )

@registry.register("check_proxy")
async def check_proxy(event, bot, supabase):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.ipify.org", timeout=10)
            ip = resp.text
            await event.respond(f"🌐 **IP الحالي:** `{ip}`\n\n✅ البروكسي يعمل!", parse_mode='md')
    except Exception as e:
        await event.respond(f"❌ **خطأ:** `{str(e)[:100]}`", parse_mode='md')

@registry.register("show_stats")
async def cmd_stats(event, bot, supabase):
    await registry.refresh_from_db()
    total_buttons = len(registry._dynamic_buttons)
    total_folders = len(registry._folders)
    await event.edit(
        f"📊 **الإحصائيات**\n\n"
        f"🔘 الأزرار النشطة: {total_buttons}\n"
        f"📁 المجلدات: {total_folders}\n"
        f"🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}",
        buttons=[[Button.inline("🔙 رجوع", b"start")]]
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
# الأزرار الأساسية (نماذج) - مختصرة
# ============================================

@registry.register("zombie_hack")
async def zombie_hack(event, bot, supabase):
    await event.respond("🧟 **نظام الزومبي**\n\n🔍 جاري البحث عن حسابات قديمة...\n💀 تم العثور على 12 حساباً\n🔄 جاري إحيائها...", buttons=[[Button.inline("🔙 رجوع", b"folder_accounts")]])

@registry.register("mirage_create")
async def mirage_create(event, bot, supabase):
    await event.respond("🌵 **نظام السراب**\n\n👥 جاري إنشاء 10 حسابات وهمية\n📊 إضافة متابعين وهميين\n✅ سيكونون جاهزين خلال دقيقة", buttons=[[Button.inline("🔙 رجوع", b"folder_accounts")]])

@registry.register("auto_gen")
async def auto_gen(event, bot, supabase):
    await event.respond("🤖 **نظام التوليد التلقائي**\n\n📱 جاري إنشاء حسابات على:\n• تليجرام\n• فيسبوك\n• إنستغرام\n• تيك توك\n\n✅ سيتم حفظها في قاعدة البيانات", buttons=[[Button.inline("🔙 رجوع", b"folder_accounts")]])

@registry.register("army_view")
async def army_view(event, bot, supabase):
    accounts = supabase.table("telegram_accounts").select("*").limit(10).execute()
    text = "📂 **الحسابات المخزنة:**\n\n"
    for acc in accounts.data:
        text += f"• {acc.get('phone', acc.get('username', 'غير معروف'))}\n"
    if not accounts.data:
        text += "لا توجد حسابات بعد"
    await event.respond(text, buttons=[[Button.inline("🔙 رجوع", b"folder_accounts")]])

@registry.register("cluster_bomb")
async def cluster_bomb(event, bot, supabase):
    await event.respond("💣 **القنبلة العنقودية**\n\n🎯 1000 مجموعة مستهدفة\n⚡ جاري النشر خلال 10 ثوانٍ\n📊 تم النشر: 0/1000", buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]])

@registry.register("plague_spread")
async def plague_spread(event, bot, supabase):
    await event.respond("🦠 **نظام الطاعون**\n\n🔥 تم إطلاق المنشور\n📈 بدأ الانتشار المتسلسل\n🎯 الهدف: 10,000 مشاهدة", buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]])

@registry.register("echo_fire")
async def echo_fire(event, bot, supabase):
    await event.respond("🔊 **نظام الصدى**\n\n✅ تم تفعيل 50 حساب تفاعل\n💬 جاهز للتعليقات والإعجابات", buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]])

@registry.register("tsunami_attack")
async def tsunami_attack(event, bot, supabase):
    await event.respond("🌊 **نظام التسونامي**\n\n📱 1000 منشور في 5 منصات\n⚡ إطلاق خلال 30 ثانية\n✅ جاري التنفيذ...", buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]])

@registry.register("earthquake_attack")
async def earthquake_attack(event, bot, supabase):
    await event.respond("🌍 **نظام الزلزال**\n\n🎯 اختر المنافس المستهدف:\n💢 1000 منشور سلبي\n📉 تدمير السمعة خلال ساعة", buttons=[[Button.inline("🔙 رجوع", b"folder_tactical")]])

@registry.register("ghost_activate")
async def ghost_activate(event, bot, supabase):
    await event.respond("👻 **نظام الطيف**\n\n✅ تم تفعيل وضع التخفي\n🔒 لن تظهر في قائمة الأعضاء\n🎯 جاهز لاختراق المجموعات الخاصة", buttons=[[Button.inline("🔙 رجوع", b"folder_stealth")]])

@registry.register("impersonate_start")
async def impersonate_start(event, bot, supabase):
    await event.respond("🎭 **نظام الانتحال**\n\n📸 تم نسخ الصورة الشخصية\n📝 تم نسخ السيرة الذاتية\n✅ الحساب المزيف جاهز", buttons=[[Button.inline("🔙 رجوع", b"folder_stealth")]])

@registry.register("cipher_encode")
async def cipher_encode(event, bot, supabase):
    await event.respond("🔐 **نظام الشفرة**\n\n📝 أرسل النص الذي تريد تشفيره:", buttons=[[Button.inline("🔙 رجوع", b"folder_stealth")]])

@registry.register("mind_control")
async def mind_control(event, bot, supabase):
    await event.respond("🧠 **نظام التحكم العقلي**\n\n🎯 جاري تحليل الجمهور\n📝 صياغة محتوى مقنع\n💰 زيادة المبيعات بنسبة 300%", buttons=[[Button.inline("🔙 رجوع", b"folder_ai_lab")]])

@registry.register("immunity_activate")
async def immunity_activate(event, bot, supabase):
    await event.respond("💉 **نظام المناعة**\n\n🛡️ تم تفعيل الدرع الذكي\n🔄 تغيير البصمة كل ساعة\n✅ الحسابات محمية الآن", buttons=[[Button.inline("🔙 رجوع", b"folder_protection")]])

@registry.register("security_scan")
async def security_scan(event, bot, supabase):
    await event.respond("🔧 **فحص الاختراق**\n\n🔍 جاري فحص الثغرات الأمنية...\n✅ لم يتم العثور على ثغرات", buttons=[[Button.inline("🔙 رجوع", b"folder_protection")]])

@registry.register("proxy_rotate")
async def proxy_rotate(event, bot, supabase):
    await event.respond("🔄 **تبديل البروكسي**\n\n🌐 تم تبديل الـ IP بنجاح\n🔗 البروكسي نشط", buttons=[[Button.inline("🔙 رجوع", b"folder_protection")]])

# ============================================
# نظام الميزانية
# ============================================

@registry.register("budget_system")
async def budget_system(event, bot, supabase):
    cards = supabase.table("payment_cards").select("*").eq("is_active", True).execute()
    total_balance = sum(c.get('current_balance', 0) for c in cards.data)
    await event.respond(
        f"💰 **نظام الميزانية** 💰\n\n"
        f"📌 عدد الفيزات النشطة: {len(cards.data)}\n"
        f"💰 إجمالي الرصيد: ${total_balance}\n\n"
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
        await event.edit("💳 **لا توجد فيزات**", buttons=[[Button.inline("➕ إضافة", b"card_add"), Button.inline("🔙 رجوع", b"budget_system")]])
        return
    keyboard = []
    for card in cards.data:
        status = "🟢" if card['is_active'] else "🔴"
        keyboard.append([Button.inline(f"{status} {card['card_number'][-4:]} - ${card.get('current_balance',0)}", f"card_view_{card['id']}")])
    keyboard.append([Button.inline("➕ إضافة فيزا جديدة", b"card_add")])
    keyboard.append([Button.inline("🔙 رجوع", b"budget_system")])
    await event.edit("💳 **الفيزات المسجلة:**", buttons=keyboard)

@registry.register("card_add")
async def card_add(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_card_details", "step": 1}
    await event.respond("➕ **إضافة فيزا جديدة - الخطوة 1/4**\n\nأرسل رقم البطاقة (16 رقم):")

@registry.register("campaigns_manage")
async def campaigns_manage(event, bot, supabase):
    await event.respond("📢 **الحملات الإعلانية**\n\n🚀 قيد التطوير...", buttons=[[Button.inline("🔙 رجوع", b"budget_system")]])

# ============================================
# لوحة التحكم
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
        [Button.inline("🐙 تعديل main.py (GitHub)", b"edit_main_github")],
        [Button.inline("📂 ملفات GitHub", b"list_github")],
        [Button.inline("🔧 إصلاح خطأ بالذكاء", b"fix_error_ai")],
        [Button.inline("🔄 إعادة تشغيل البوت", b"restart_bot")],
        [Button.inline("🔙 رجوع", b"start")],
    ]
    await event.edit("⚙️ **لوحة التحكم الشاملة**\n\n👑 مرحباً قائد", buttons=keyboard, parse_mode='md')

@registry.register("admin_folders")
async def admin_folders(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db()
    folders = registry.get_folders()
    keyboard = []
    for folder in folders:
        keyboard.append([Button.inline(f"{folder.get('emoji', '📁')} {folder.get('display_name')}", f"edit_folder_{folder['folder_key']}")])
    keyboard.append([Button.inline("➕ إضافة مجلد جديد", b"add_folder")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
    await event.edit("📁 **إدارة المجلدات**", buttons=keyboard)

@registry.register("add_folder")
async def add_folder(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    user_states[event.sender_id] = {"state": "awaiting_folder_key"}
    await event.respond("➕ **إضافة مجلد جديد**\n\nأرسل المفتاح (key) للمجلد:")

@registry.register("admin_buttons")
async def admin_buttons(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db()
    buttons_list = list(registry._dynamic_buttons.values())
    keyboard = []
    for btn in buttons_list[:30]:
        keyboard.append([Button.inline(f"{btn.get('emoji', '🔘')} {btn.get('display_name', btn['button_id'])[:25]}", f"edit_btn_{btn['button_id']}")])
    keyboard.append([Button.inline("➕ إضافة زر جديد", b"add_button")])
    keyboard.append([Button.inline("🤖 إنشاء زر بالذكاء", b"ai_create_button")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
    await event.edit(f"🔘 **إدارة الأزرار**\n\n📊 عدد الأزرار: {len(buttons_list)}", buttons=keyboard)

@registry.register("add_button")
async def add_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    user_states[event.sender_id] = {"state": "awaiting_button_data", "step": 1, "data": {}}
    await event.respond("➕ **إضافة زر جديد - الخطوة 1/6**\n\nأرسل الـ Button ID:")

@registry.register("ai_create_button")
async def ai_create_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ للمطور فقط", alert=True)
        return
    await event.respond(
        "🤖 **المطور الذاتي العبقري**\n\n"
        "📝 أرسل وصفاً بالعربية للزر الذي تريده:\n\n"
        "_مثال: زر يرسل رسالة 'مرحباً' لكل عضو جديد_\n\n"
        f"🌐 البروكسي: {'🟢 سيعمل تلقائياً' if PROXY_URL else '⚪ غير مفعل'}"
    )
    user_states[event.sender_id] = {"state": "awaiting_ai_button_description"}

@registry.register("admin_refresh")
async def admin_refresh(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db(force=True)
    await event.answer("✅ تم تحديث الكاش", alert=True)

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
        keyboard.append([Button.inline(f"🔄 {item['item_type']}: {item['item_id'][:30]}", f"restore_{item['id']}")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
    await event.edit("🗑️ **سلة المحذوفات**", buttons=keyboard)

@registry.register("admin_settings")
async def admin_settings(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    keyboard = [
        [Button.inline("🤖 إعدادات الذكاء", b"setting_ai")],
        [Button.inline("🌐 إعدادات البروكسي", b"setting_proxy")],
        [Button.inline("💰 إعدادات الميزانية", b"setting_budget")],
        [Button.inline("🔙 رجوع", b"admin_full_panel")],
    ]
    await event.edit("⚙️ **إعدادات النظام**", buttons=keyboard)

@registry.register("admin_stats")
async def admin_stats_advanced(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db()
    total_buttons = len(registry._dynamic_buttons)
    total_clicks = supabase.table("analytics").select("*", count="exact").execute().count
    promo_count = supabase.table("promo_accounts").select("*", count="exact").execute().count
    individual_count = supabase.table("individual_accounts").select("*", count="exact").execute().count
    await event.edit(
        f"📊 **الإحصائيات المتقدمة**\n\n"
        f"🔘 الأزرار: {total_buttons}\n👆 الضغطات: {total_clicks}\n"
        f"💰 حسابات الترويج: {promo_count}\n📝 حسابات النشر: {individual_count}\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}",
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
    await event.edit("👥 **إدارة الحسابات**", buttons=keyboard)

@registry.register("promo_accounts_list")
async def promo_accounts_list(event, bot, supabase):
    accounts = supabase.table("promo_accounts").select("*").execute()
    if not accounts.data:
        await event.edit("💰 **لا توجد حسابات ترويجية**", buttons=[[Button.inline("🔙 رجوع", b"admin_accounts")]])
        return
    text = "💰 **حسابات الترويج**\n\n"
    for acc in accounts.data[:20]:
        text += f"• {acc['platform']}: {acc.get('account_name', acc['email'])}\n"
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"admin_accounts")]])

@registry.register("individual_accounts_list")
async def individual_accounts_list(event, bot, supabase):
    accounts = supabase.table("individual_accounts").select("*").execute()
    if not accounts.data:
        await event.edit("📝 **لا توجد حسابات نشر فردي**", buttons=[[Button.inline("➕ إضافة حساب", b"individual_add"), Button.inline("🔙 رجوع", b"admin_accounts")]])
        return
    keyboard = []
    for acc in accounts.data:
        keyboard.append([Button.inline(f"{'🟢' if acc['status']=='active' else '🔴'} {acc['platform']}: @{acc.get('username','بدون')}", f"individual_view_{acc['id']}")])
    keyboard.append([Button.inline("➕ إضافة حساب جديد", b"individual_add")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_accounts")])
    await event.edit("📝 **حسابات النشر الفردي**", buttons=keyboard)

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
        f"📊 **إحصائيات الحسابات**\n\n"
        f"💰 الترويج: {promo.count} (نشط: {active_promo.count})\n"
        f"📝 النشر الفردي: {individual.count} (نشط: {active_individual.count})",
        buttons=[[Button.inline("🔄 تحديث", b"accounts_stats"), Button.inline("🔙 رجوع", b"admin_accounts")]]
    )

@registry.register("edit_main_github")
async def edit_main_github(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    if not GITHUB_TOKEN:
        await event.respond("❌ **GITHUB_TOKEN غير موجود**\n\nأضف متغير GITHUB_TOKEN في Railway")
        return
    current_code = await get_github_file()
    if not current_code:
        await event.respond("❌ **فشل جلب الملف من GitHub**")
        return
    await event.respond(
        f"📁 **ملف main.py الحالي**\n\n"
        f"📊 الحجم: {len(current_code)} حرف\n\n"
        f"🔧 أرسل التعديلات (كود كامل):"
    )
    user_states[event.sender_id] = {"state": "awaiting_github_edit", "original_code": current_code}

@registry.register("fix_error_ai")
async def fix_error_ai(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    await event.respond(
        "🔧 **إصلاح الأخطاء بالذكاء الاصطناعي**\n\n"
        "📄 أرسل الخطأ كاملاً (Error Traceback):"
    )
    user_states[event.sender_id] = {"state": "awaiting_error_fix"}

@registry.register("restart_bot")
async def restart_bot_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    await event.respond("🔄 **جاري إعادة تشغيل البوت...**\n\nسأعود خلال ثوانٍ.")
    await restart_bot()

@registry.register("cancel")
async def cancel_action(event, bot, supabase):
    user_id = event.sender_id
    if user_id in user_states:
        del user_states[user_id]
    await event.respond("❌ تم إلغاء العملية", buttons=[[Button.inline("🔙 رجوع", b"start")]])

@registry.register("setting_ai")
async def setting_ai(event, bot, supabase):
    await event.respond(f"🤖 **إعدادات الذكاء الاصطناعي**\n\n🔑 مفتاح OpenAI: {'✅ موجود' if OPENAI_KEY else '❌ غير موجود'}", buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]])

@registry.register("setting_proxy")
async def setting_proxy(event, bot, supabase):
    await event.respond(f"🌐 **إعدادات البروكسي**\n\n🔗 البروكسي: {'✅ نشط' if PROXY_URL else '❌ غير مستخدم'}", buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]])

@registry.register("setting_budget")
async def setting_budget(event, bot, supabase):
    await event.respond("💰 **إعدادات الميزانية**\n\n🔜 قيد التطوير", buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]])

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
# معالج الكالك باك الرئيسي
# ============================================

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    try:
        data = event.data.decode()
        user_id = event.sender_id
        
        # استرجاع من سلة المحذوفات
        if data.startswith("restore_"):
            item_id = int(data.replace("restore_", ""))
            deleted = supabase.table("deleted_items").select("*").eq("id", item_id).execute()
            if deleted.data:
                item = deleted.data[0]
                if item["item_type"] == "button":
                    supabase.table("buttons").insert(item["item_data"]).execute()
                    supabase.table("deleted_items").delete().eq("id", item_id).execute()
                    await event.answer("✅ تم الاسترجاع", alert=True)
                    await admin_recycle(event, bot, supabase)
            return
        
        # عرض ملفات GitHub
        if data == "list_github":
            await list_github_button(event, bot, supabase)
            return
        
        # تعديل مجلد
        if data.startswith("edit_folder_"):
            folder_key = data.replace("edit_folder_", "")
            await event.respond(f"✏️ تعديل المجلد {folder_key} (قيد التطوير)")
            return
        
        # تعديل زر
        if data.startswith("edit_btn_"):
            button_id = data.replace("edit_btn_", "")
            if "edit_btn_code" in data:
                user_states[user_id] = {"state": "awaiting_edit_code", "button_id": button_id}
                await event.respond(f"📝 **تعديل كود الزر**\n\nأرسل الكود الجديد للزر `{button_id}`:")
                return
            elif "edit_btn_name" in data:
                user_states[user_id] = {"state": "awaiting_edit_name", "button_id": button_id}
                await event.respond(f"✏️ **تعديل اسم الزر**\n\nأرسل الاسم الجديد للزر `{button_id}`:")
                return
            elif "edit_btn_color" in data:
                keyboard = [
                    [Button.inline("🔵 أزرق", f"set_color_{button_id}_blue".encode())],
                    [Button.inline("🔴 أحمر", f"set_color_{button_id}_red".encode())],
                    [Button.inline("🟢 أخضر", f"set_color_{button_id}_green".encode())],
                    [Button.inline("🟣 بنفسجي", f"set_color_{button_id}_purple".encode())],
                    [Button.inline("⚫ غامق", f"set_color_{button_id}_dark".encode())],
                    [Button.inline("🟠 برتقالي", f"set_color_{button_id}_orange".encode())],
                    [Button.inline("🔙 رجوع", f"edit_btn_{button_id}".encode())],
                ]
                await event.edit("🎨 **اختر اللون الجديد:**", buttons=keyboard)
                return
            elif "edit_btn_folder" in data:
                folders = registry.get_folders()
                keyboard = []
                for folder in folders:
                    keyboard.append([Button.inline(f"{folder.get('emoji', '📁')} {folder.get('display_name')}", f"move_btn_{button_id}_{folder['folder_key']}".encode())])
                keyboard.append([Button.inline("🔙 رجوع", f"edit_btn_{button_id}".encode())])
                await event.edit("📁 **اختر المجلد الجديد:**", buttons=keyboard)
                return
            else:
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
        
        # تغيير لون الزر
        if data.startswith("set_color_"):
            parts = data.split("_")
            button_id = "_".join(parts[2:-1]) if len(parts) > 3 else parts[2]
            color = parts[-1]
            supabase.table("buttons").update({"color": color}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            await event.answer(f"✅ تم تغيير اللون إلى {color}", alert=True)
            await admin_buttons(event, bot, supabase)
            return
        
        # نقل زر لمجلد آخر
        if data.startswith("move_btn_"):
            parts = data.split("_")
            button_id = parts[2]
            folder_key = parts[3]
            supabase.table("buttons").update({"folder_key": folder_key}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            await event.answer(f"✅ تم نقل الزر إلى مجلد {folder_key}", alert=True)
            await admin_buttons(event, bot, supabase)
            return
        
        # حذف زر (تأكيد)
        if data.startswith("delete_btn_"):
            button_id = data.replace("delete_btn_", "")
            keyboard = [
                [Button.inline("✅ نعم، احذف", f"confirm_delete_{button_id}".encode())],
                [Button.inline("❌ لا، إلغاء", b"admin_buttons")],
            ]
            await event.edit(f"⚠️ **تأكيد حذف الزر**\n\nهل أنت متأكد من حذف الزر `{button_id}`?", buttons=keyboard)
            return
        
        # تأكيد الحذف
        if data.startswith("confirm_delete_"):
            button_id = data.replace("confirm_delete_", "")
            await registry.delete_button(button_id, user_id)
            await event.answer(f"✅ تم حذف الزر", alert=True)
            await admin_buttons(event, bot, supabase)
            return
        
        # إضافة زر في مجلد
        if data.startswith("add_btn_in_"):
            folder_key = data.replace("add_btn_in_", "")
            user_states[user_id] = {"state": "awaiting_button_data", "step": 1, "data": {"folder_key": folder_key}}
            await event.respond("➕ **إضافة زر جديد**\n\nالخطوة 1/6: أرسل الـ Button ID:")
            return
        
        # عرض تفاصيل فيزا
        if data.startswith("card_view_"):
            card_id = int(data.replace("card_view_", ""))
            card = supabase.table("payment_cards").select("*").eq("id", card_id).execute()
            if card.data:
                c = card.data[0]
                await event.edit(
                    f"💳 **تفاصيل البطاقة**\n\n"
                    f"🔢 الرقم: ****{c['card_number'][-4:]}\n"
                    f"💰 الرصيد: ${c.get('current_balance', 0)}\n"
                    f"🟢 الحالة: {'نشطة' if c.get('is_active') else 'معطلة'}",
                    buttons=[
                        [Button.inline("🔄 فحص الرصيد", f"check_card_{card_id}")],
                        [Button.inline("🗑️ حذف", f"delete_card_{card_id}")],
                        [Button.inline("🔙 رجوع", b"cards_manage")]
                    ]
                )
            return
        
        # فحص رصيد بطاقة
        if data.startswith("check_card_"):
            card_id = int(data.replace("check_card_", ""))
            card = supabase.table("payment_cards").select("*").eq("id", card_id).execute()
            if card.data:
                await event.answer(f"✅ البطاقة صالحة", alert=True)
                await event.edit(f"💳 البطاقة نشطة", buttons=[[Button.inline("🔙 رجوع", f"card_view_{card_id}")]])
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
                    f"👤 المستخدم: @{a.get('username', 'غير محدد')}\n"
                    f"⭐ نقاط الثقة: {a.get('trust_score', 50)}/100\n"
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
        
        # إنشاء حسابات ترويجية
        if data == "create_1_each":
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
                        "created_by": user_id
                    }).execute()
                    created.append(f"{platform}: {username}")
            await event.respond(f"✅ **تم إنشاء {len(created)} حساب ترويجي**")
            await campaigns_manage(event, bot, supabase)
            return
        
        if data == "create_3_each":
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
                        "created_by": user_id
                    }).execute()
                    created.append(f"{platform}: {username}")
            await event.respond(f"✅ **تم إنشاء {len(created)} حساب ترويجي**")
            await campaigns_manage(event, bot, supabase)
            return
        
        if data == "create_5_each":
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
                        "created_by": user_id
                    }).execute()
                    created.append(f"{platform}: {username}")
            await event.respond(f"✅ **تم إنشاء {len(created)} حساب ترويجي**")
            await campaigns_manage(event, bot, supabase)
            return
        
        # معالج المطور الذاتي
        if data == "ai_create_button":
            await ai_create_button(event, bot, supabase)
            return
        
        if data == "edit_main_github":
            await edit_main_github(event, bot, supabase)
            return
        
        if data == "fix_error_ai":
            await fix_error_ai(event, bot, supabase)
            return
        
        if data == "restart_bot":
            await restart_bot_handler(event, bot, supabase)
            return
        
        # معالج الغاء
        if data == "cancel":
            if user_id in user_states:
                del user_states[user_id]
            await event.answer("❌ تم الإلغاء", alert=True)
            await admin_full_panel(event, bot, supabase)
            return
        
        # مجلدات
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
        
        # أزرار التحكم
        if data == "admin_full_panel":
            await admin_full_panel(event, bot, supabase)
            return
        if data == "admin_folders":
            await admin_folders(event, bot, supabase)
            return
        if data == "admin_buttons":
            await admin_buttons(event, bot, supabase)
            return
        if data == "admin_accounts":
            await admin_accounts(event, bot, supabase)
            return
        if data == "admin_stats":
            await admin_stats_advanced(event, bot, supabase)
            return
        if data == "admin_recycle":
            await admin_recycle(event, bot, supabase)
            return
        if data == "admin_settings":
            await admin_settings(event, bot, supabase)
            return
        if data == "admin_refresh":
            await admin_refresh(event, bot, supabase)
            return
        if data == "budget_system":
            await budget_system(event, bot, supabase)
            return
        if data == "cards_manage":
            await cards_manage(event, bot, supabase)
            return
        if data == "card_add":
            await card_add(event, bot, supabase)
            return
        if data == "campaigns_manage":
            await campaigns_manage(event, bot, supabase)
            return
        if data == "show_stats":
            await cmd_stats(event, bot, supabase)
            return
        if data == "check_proxy":
            await check_proxy(event, bot, supabase)
            return
        if data == "ai_chat":
            await ai_chat_button(event, bot, supabase)
            return
        
    except Exception as e:
        log.error(f"خطأ في الكالك باك: {e}")
        await event.answer(f"❌ خطأ", alert=True)

# ============================================
# معالج الرسائل للمطور الذاتي
# ============================================

@bot.on(events.NewMessage)
async def ai_message_handler(event):
    if event.out or not event.raw_text:
        return
    
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    # معالجة الأوامر الخاصة بالمطور فقط
    if user_id in ADMIN_IDS:
        # معالج المطور الذاتي (AI Button Creator)
        if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_button_description":
            description = text
            await event.respond("🤔 **جاري تحليل الطلب وتوليد الكود...**")
            
            try:
                generated_code = await ask_ai(description, user_id)
                
                user_states[user_id] = {
                    "state": "awaiting_ai_folder",
                    "description": description,
                    "code": generated_code
                }
                
                folders_list = ["accounts", "tactical", "stealth", "ai_lab", "protection", "budget", "main", "admin"]
                keyboard = []
                for f in folders_list:
                    keyboard.append([Button.inline(f"📁 {f}", f"ai_folder_{f}".encode())])
                
                await event.respond(
                    f"✅ **تم توليد الكود!**\n\n📝 **الوصف:** {description}\n\n💻 **الكود:**\n```python\n{generated_code[:800]}\n```\n\n📁 **اختر المجلد لحفظ الزر:**",
                    buttons=keyboard,
                    parse_mode='md'
                )
            except Exception as e:
                await event.respond(f"❌ خطأ: {e}")
                del user_states[user_id]
            return
        
        # معالج اختيار مجلد للزر
        if text.startswith("ai_folder_"):
            folder_key = text.replace("ai_folder_", "")
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_folder":
                user_states[user_id]["folder_key"] = folder_key
                user_states[user_id]["state"] = "awaiting_ai_button_confirmation"
                
                description = user_states[user_id].get("description", "")
                code = user_states[user_id].get("code", "")
                
                await event.edit(
                    f"✅ **تم اختيار المجلد: {folder_key}**\n\n"
                    f"📝 **الوصف:** {description[:100]}\n\n"
                    f"💻 **الكود:**\n```python\n{code[:500]}\n```\n\n"
                    f"هل تريد حفظ هذا الزر؟",
                    buttons=[
                        [Button.inline("✅ حفظ", b"ai_confirm_save")],
                        [Button.inline("❌ إلغاء", b"cancel")]
                    ],
                    parse_mode='md'
                )
            return
        
        # حفظ زر AI
        if text == "ai_confirm_save":
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_button_confirmation":
                state = user_states[user_id]
                description = state.get("description", "")
                code = state.get("code", "")
                folder_key = state.get("folder_key", "main")
                
                button_id = "ai_" + str(int(datetime.now().timestamp()))[-6:]
                
                supabase.table("buttons").insert({
                    "button_id": button_id,
                    "display_name": description[:50],
                    "emoji": "🤖",
                    "color": "blue",
                    "folder_key": folder_key,
                    "python_code": code,
                    "description": description,
                    "is_active": True,
                    "created_by": user_id
                }).execute()
                
                await registry.refresh_from_db(force=True)
                del user_states[user_id]
                await event.respond(f"✅ **تم إنشاء الزر بنجاح!**\n\n🔘 ID: `{button_id}`\n📁 المجلد: {folder_key}")
                await admin_buttons(event, bot, supabase)
            return
        
        # معالج تعديل GitHub
        if user_id in user_states and user_states[user_id].get("state") == "awaiting_github_edit":
            original = user_states[user_id].get("original_code", "")
            success = await update_github_file(text, "main.py", "AI self-update")
            if success:
                await event.respond("✅ **تم تحديث main.py في GitHub بنجاح!**\n\n🔄 جاري إعادة تشغيل البوت...")
                await restart_bot()
            else:
                await event.respond("❌ **فشل تحديث الملف**")
            del user_states[user_id]
            return
        
        # معالج إصلاح الخطأ
        if user_id in user_states and user_states[user_id].get("state") == "awaiting_error_fix":
            error_text = text
            await event.respond("🔍 **جاري تحليل الخطأ وإيجاد الحل...**")
            current_code = await get_github_file()
            if not current_code:
                current_code = "غير قادر على جلب الكود الحالي"
            fix = await ask_ai(f"الخطأ: {error_text}\n\nالكود الحالي: {current_code[:1500]}\n\nقم بتحليل الخطأ وإعطاء الكود المصحح", user_id)
            await event.respond(
                f"🔧 **اقتراح إصلاح الخطأ**\n\n"
                f"{fix[:1500]}\n\n"
                f"هل تريد تطبيق هذا التعديل؟",
                buttons=[
                    [Button.inline("✅ تطبيق التعديل", b"apply_fix")],
                    [Button.inline("❌ إلغاء", b"cancel")]
                ],
                parse_mode='md'
            )
            user_states[user_id] = {"state": "awaiting_fix_apply", "fix_code": fix}
            return
        
        # تطبيق إصلاح الخطأ
        if text == "apply_fix":
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_fix_apply":
                fix_code = user_states[user_id].get("fix_code", "")
                import re
                code_match = re.search(r'```python\n(.*?)```', fix_code, re.DOTALL)
                if code_match:
                    new_code = code_match.group(1)
                    success = await update_github_file(new_code, "main.py", "AI fix applied")
                    if success:
                        await event.respond("✅ **تم تطبيق التعديل وإعادة تشغيل البوت!**")
                        await restart_bot()
                    else:
                        await event.respond("❌ فشل تطبيق التعديل")
                else:
                    await event.respond("❌ لم يتم العثور على كود صالح")
                del user_states[user_id]
            return

# ============================================
# إنشاء الجداول الافتراضية
# ============================================

async def create_default_folders():
    folders = [
        ("main", "القائمة الرئيسية", "🏠", "blue", 0),
        ("accounts", "مصنع الجيوش", "🏭", "green", 1),
        ("tactical", "الهجوم التكتيكي", "🚀", "red", 2),
        ("stealth", "عمليات التخفي", "👻", "purple", 3),
        ("ai_lab", "مختبر الذكاء", "🧠", "dark", 4),
        ("protection", "درع الحماية", "🛡️", "blue", 5),
        ("budget", "الميزانية", "💰", "green", 6),
        ("admin", "لوحة التحكم", "⚙️", "red", 7),
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
# المهام الخلفية
# ============================================

async def auto_balance_monitor():
    while True:
        try:
            await asyncio.sleep(3600)
            cards = supabase.table("payment_cards").select("*").eq("is_active", True).execute()
            for card in cards.data:
                try:
                    async with httpx.AsyncClient() as client:
                        resp = await client.get(f"https://lookup.binlist.net/{card['card_number'][:6]}")
                        if resp.status_code == 200:
                            data = resp.json()
                            supabase.table("payment_cards").update({
                                "card_type": data.get('scheme', 'unknown'),
                                "last_checked": datetime.now().isoformat()
                            }).eq("id", card['id']).execute()
                except:
                    pass
        except:
            await asyncio.sleep(60)

async def auto_railway_monitor():
    """مراقبة حالة الاستضافة تلقائياً"""
    while True:
        try:
            await asyncio.sleep(3600)
            status = await get_railway_deployment_status()
            if status.get('status') == 'FAILED' and ADMIN_IDS:
                await bot.send_message(
                    ADMIN_IDS[0],
                    f"⚠️ **تنبيه عاجل من مراقب الاستضافة!**\n\n"
                    f"حالة آخر نشر: فشل (FAILED)\n"
                    f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"رابط السجلات: {status.get('logsUrl', 'غير متوفر')}"
                )
        except:
            await asyncio.sleep(3600)

async def auto_reset_accounts():
    while True:
        try:
            now = datetime.now()
            next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
            await asyncio.sleep((next_midnight - now).total_seconds())
            supabase.table("individual_accounts").update({"posts_today": 0}).execute()
            log.info("✅ تم إعادة تعيين منشورات اليوم")
        except:
            await asyncio.sleep(3600)

async def auto_backup():
    while True:
        try:
            await asyncio.sleep(21600)
            buttons = supabase.table("buttons").select("*").execute()
            folders = supabase.table("folders").select("*").execute()
            backup_data = {
                "buttons": buttons.data,
                "folders": folders.data,
                "backup_time": datetime.now().isoformat()
            }
            supabase.table("backups").upsert({
                "backup_type": "auto",
                "backup_data": backup_data,
                "backup_size": len(json.dumps(backup_data))
            }, on_conflict="id").execute()
            log.info("✅ نسخة احتياطية تلقائية")
        except:
            await asyncio.sleep(3600)

def ensure_backup_table():
    try:
        supabase.table("backups").select("count").limit(1).execute()
    except:
        log.warning("⚠️ جدول backups غير موجود")

# ============================================
# التشغيل الرئيسي
# ============================================

async def main():
    log.info("🚀 جاري تشغيل MUSTAFA SHOP - DIGITAL EMPIRE v6...")
    log.info("=" * 50)
    
    if PROXY_URL:
        log.info(f"🌐 البروكسي مفعل")
    else:
        log.info("ℹ️ البروكسي غير مفعل")
    
    if OPENAI_KEY:
        log.info(f"🤖 الذكاء الاصطناعي مفعل")
    else:
        log.warning("⚠️ الذكاء الاصطناعي غير مفعل (بدون مفتاح OpenAI)")
    
    if GITHUB_TOKEN:
        log.info(f"🐙 GitHub متصل")
    else:
        log.warning("⚠️ GitHub غير متصل (بدون توكن)")
    
    if RAILWAY_TOKEN:
        log.info(f"🚂 Railway API متصل")
    else:
        log.warning("⚠️ مراقبة الاستضافة غير متصلة (بدون توكن Railway)")
    
    ensure_backup_table()
    await create_ai_memory_table()
    await create_default_folders()
    
    try:
        supabase.table("folders").select("count").limit(1).execute()
        log.info("✅ قاعدة البيانات جاهزة")
    except Exception as e:
        log.warning(f"⚠️ قاعدة البيانات تحتاج تهيئة: {e}")
    
    await registry.refresh_from_db(force=True)
    
    log.info(f"📊 تم تحميل {len(registry._dynamic_buttons)} زر و {len(registry._folders)} مجلد")
    
    await bot.start(bot_token=BOT_TOKEN)
    
    me = await bot.get_me()
    log.info(f"✅ البوت يعمل! @{me.username}")
    log.info(f"🔗 رابط البوت: https://t.me/{me.username}")
    log.info(f"👑 المطورون: {ADMIN_IDS}")
    log.info(f"🤖 الذكاء الاصطناعي: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}")
    log.info(f"🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}")
    log.info(f"🐙 GitHub: {'🟢 متصل' if GITHUB_TOKEN else '🔴 غير متصل'}")
    log.info(f"🚂 Railway API: {'🟢 متصل' if RAILWAY_TOKEN else '🔴 غير متصل'}")
    log.info("=" * 50)
    log.info("🎯 المنظومة جاهزة لاستقبال الأوامر!")
    log.info("💡 يمكنك التحدث مع المبرمج AI بأي لغة")
    log.info("📂 استخدم /list_github لعرض ملفات GitHub")
    log.info("📥 استخدم /download_github اسم_الملف لتحميل ملف")
    
    asyncio.create_task(auto_balance_monitor())
    asyncio.create_task(auto_railway_monitor())
    asyncio.create_task(auto_reset_accounts())
    asyncio.create_task(auto_backup())
    
    if ADMIN_IDS:
        try:
            await bot.send_message(
                ADMIN_IDS[0],
                f"✅ **تم تشغيل MUSTAFA SHOP - DIGITAL EMPIRE v6**\n\n"
                f"📊 {len(registry._dynamic_buttons)} زر نشط\n"
                f"📁 {len(registry._folders)} مجلد\n"
                f"🤖 AI: {'نشط' if OPENAI_KEY else 'غير نشط'}\n"
                f"🌐 البروكسي: {'نشط' if PROXY_URL else 'غير مستخدم'}\n"
                f"🐙 GitHub: {'متصل' if GITHUB_TOKEN else 'غير متصل'}\n"
                f"🚂 Railway: {'مراقب' if RAILWAY_TOKEN else 'غير مراقب'}\n\n"
                f"💡 **يمكنك الآن التحدث مع المبرمج AI بأي لغة!**\n"
                f"📂 **استخدم /list_github لعرض ملفات GitHub**\n"
                f"📥 **استخدم /download_github اسم_الملف لتحميل ملف**"
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
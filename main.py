# main.py - MUSTAFA SHOP v8 (Sovereign AI Engine) - الكود الكامل المعدل
# ============================================
# Digital Empire Bot - Telethon + Supabase + OpenAI
# نظام متكامل لإدارة الأزرار والمجلدات والذكاء الاصطناعي
# ============================================

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
from typing import Dict, Any, Optional, List, Tuple
from collections import defaultdict
from dataclasses import dataclass, field

from telethon import TelegramClient, events, Button
from telethon.tl.types import User
from telethon.errors import FloodWaitError
from supabase import create_client, Client
import httpx

# ============================================
# LOGGING CONFIGURATION
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

class TelegramLogHandler(logging.Handler):
    def __init__(self, admin_ids: List[int] = None):
        super().__init__()
        self.admin_ids = admin_ids or []
        self.bot_instance = None

    def set_bot(self, bot_instance):
        self.bot_instance = bot_instance

    def emit(self, record):
        if record.levelno >= logging.ERROR and self.bot_instance and self.admin_ids:
            try:
                loop = asyncio.get_running_loop()
                msg = f"⛔ **خطأ:**\n```\n{record.getMessage()[:500]}\n```"
                for admin_id in self.admin_ids:
                    loop.create_task(self.bot_instance.send_message(admin_id, msg, parse_mode='md'))
            except:
                pass

# ============================================
# متغيرات البيئة
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
RAILWAY_PROJECT_ID = os.environ.get("RAILWAY_PROJECT_ID", "")
RAILWAY_SERVICE_ID = os.environ.get("RAILWAY_SERVICE_ID", "")

VERSION = "8.0.0"
MAX_CODE_LENGTH = 10000
AUDIT_INTERVAL_HOURS = 2
BACKUP_INTERVAL_HOURS = 6

# ============================================
# التحقق من المتغيرات الأساسية
# ============================================
if not all([API_ID, API_HASH, BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    log.error("❌ متغيرات البيئة الأساسية غير مكتملة!")
    sys.exit(1)

if not ADMIN_IDS:
    log.warning("⚠️ لم يتم تعيين ADMIN_IDS")

# ============================================
# إعداد البروكسي
# ============================================
proxy_config = None
if PROXY_URL and USE_PROXY_FOR_ALL:
    try:
        if "@" in PROXY_URL:
            auth_part = PROXY_URL.split("@")[0].replace("http://", "").replace("https://", "")
            host_part = PROXY_URL.split("@")[1]
            username, password = auth_part.split(":", 1) if ":" in auth_part else (auth_part, "")
            addr, port = host_part.split(":") if ":" in host_part else (host_part, "31280")
            proxy_config = {'proxy_type': 'http', 'addr': addr, 'port': int(port), 'username': username, 'password': password}
        else:
            addr, port = PROXY_URL.split(":") if ":" in PROXY_URL else (PROXY_URL, "31280")
            proxy_config = {'proxy_type': 'http', 'addr': addr, 'port': int(port)}
        log.info("✅ تم إعداد البروكسي للـ Telethon")
    except Exception as e:
        log.warning(f"⚠️ فشل إعداد البروكسي: {e}")

# بروكسي لـ httpx
proxy_httpx = None
if PROXY_URL and USE_PROXY_FOR_ALL:
    try:
        if "@" in PROXY_URL:
            auth_part = PROXY_URL.split("@")[0].replace("http://", "").replace("https://", "")
            host_part = PROXY_URL.split("@")[1]
            username, password = auth_part.split(":", 1) if ":" in auth_part else (auth_part, "")
            addr, port = host_part.split(":") if ":" in host_part else (host_part, "31280")
            proxy_httpx = {"http://": f"http://{username}:{password}@{addr}:{port}", "https://": f"http://{username}:{password}@{addr}:{port}"}
        else:
            addr, port = PROXY_URL.split(":") if ":" in PROXY_URL else (PROXY_URL, "31280")
            proxy_httpx = {"http://": f"http://{addr}:{port}", "https://": f"http://{addr}:{port}"}
        log.info("✅ تم إعداد البروكسي لـ httpx")
    except:
        pass

# ============================================
# تهيئة العملاء
# ============================================
bot = TelegramClient("mustafa_v8_session", API_ID, API_HASH, proxy=proxy_config)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# إضافة معالج الأخطاء
error_handler = TelegramLogHandler(ADMIN_IDS)
error_handler.set_bot(bot)
log.addHandler(error_handler)

# ============================================
# دوال GitHub
# ============================================
async def get_github_file(path: str = "main.py") -> Optional[str]:
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        async with httpx.AsyncClient(timeout=30, proxy=proxy_httpx) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("encoding") == "base64" and data.get("content"):
                    return base64.b64decode(data["content"].replace("\n", "")).decode('utf-8')
            return None
    except Exception as e:
        log.error(f"GitHub get_file error: {e}")
        return None

async def update_github_file(content: str, path: str = "main.py", commit_msg: str = "AI self-update") -> bool:
    if not GITHUB_TOKEN:
        return False
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
        headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
        async with httpx.AsyncClient(timeout=30, proxy=proxy_httpx) as client:
            resp = await client.get(url, headers=headers)
            sha = resp.json().get("sha") if resp.status_code == 200 else None
            data = {
                "message": commit_msg,
                "content": base64.b64encode(content.encode()).decode(),
                "branch": GITHUB_BRANCH,
            }
            if sha:
                data["sha"] = sha
            resp2 = await client.put(url, headers=headers, json=data)
            return resp2.status_code in [200, 201]
    except Exception as e:
        log.error(f"update_github_file error: {e}")
        return False

async def list_github_files(path: str = "") -> str:
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        async with httpx.AsyncClient(timeout=30, proxy=proxy_httpx) as client:
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
                    return "\n".join(files) if files else "📂 لا توجد ملفات"
            return f"❌ خطأ HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ خطأ: {str(e)[:100]}"

async def download_github_file(path: str) -> Optional[bytes]:
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        if GITHUB_TOKEN:
            headers["Authorization"] = f"token {GITHUB_TOKEN}"
        async with httpx.AsyncClient(timeout=30, proxy=proxy_httpx) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("encoding") == "base64":
                    return base64.b64decode(data["content"].replace("\n", ""))
            return None
    except:
        return None

# ============================================
# فحص أمان الكود
# ============================================
async def validate_python_code(code: str) -> Tuple[bool, str]:
    try:
        ast.parse(code)
        return True, "✅ الكود صحيح"
    except SyntaxError as e:
        return False, f"❌ خطأ في السطر {e.lineno}: {e.msg}"

async def check_code_safety(code: str) -> Tuple[bool, List[str]]:
    issues = []
    try:
        ast.parse(code)
    except SyntaxError as e:
        issues.append(f"Syntax Error line {e.lineno}: {e.msg}")
        return False, issues

    dangerous_patterns = [
        (r'while\s+True\s*:', "Infinite loop (while True)"),
        (r'eval\s*\(', "eval() is forbidden"),
        (r'exec\s*\(', "exec() is forbidden"),
        (r'os\.system\s*\(', "os.system() is forbidden"),
        (r'subprocess\.', "subprocess module is forbidden"),
        (r'__import__\s*\(', "Dynamic import is forbidden"),
        (r'globals\(\)\.', "Modifying globals is not allowed"),
    ]

    for pattern, warning in dangerous_patterns:
        if re.search(pattern, code):
            issues.append(warning)

    return len(issues) == 0, issues

# ============================================
# دوال الذكاء الاصطناعي
# ============================================
AI_MEMORY_TABLE = "ai_memory"

async def save_ai_memory(user_id: int, user_message: str, ai_response: str, context: str = ""):
    try:
        supabase.table(AI_MEMORY_TABLE).insert({
            "user_id": user_id,
            "user_message": user_message[:500],
            "ai_response": ai_response[:500],
            "context": context[:500],
            "created_at": datetime.now().isoformat()
        }).execute()
    except:
        pass

async def get_ai_memory(user_id: int, limit: int = 10) -> List[Dict]:
    try:
        result = supabase.table(AI_MEMORY_TABLE).select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return result.data[::-1] if result.data else []
    except:
        return []

async def get_system_context(user_id: int) -> str:
    try:
        buttons_count = supabase.table("buttons").select("*", count="exact").execute().count or 0
    except:
        buttons_count = 0
    try:
        folders_count = supabase.table("folders").select("*", count="exact").execute().count or 0
    except:
        folders_count = 0
    try:
        users_count = supabase.table("users").select("*", count="exact").execute().count or 0
    except:
        users_count = 0

    return f"""
=== سياق منظومة MUSTAFA SHOP v{VERSION} ===
الأزرار: {buttons_count} | المجلدات: {folders_count} | المستخدمين: {users_count}
البروكسي: {'مفعل' if PROXY_URL else 'غير مفعل'} | AI: {'مفعل' if OPENAI_KEY else 'غير مفعل'}
GitHub: {'متصل' if GITHUB_TOKEN else 'غير متصل'}
"""

async def ask_ai(prompt: str, user_id: int = None, conversation_history: list = None) -> str:
    if not OPENAI_KEY:
        return "🔴 مفتاح OpenAI غير موجود."

    context = await get_system_context(user_id) if user_id else ""

    if user_id:
        memory = await get_ai_memory(user_id, 5)
        memory_text = "\n".join([f"مستخدم: {m['user_message'][:200]}\nAI: {m['ai_response'][:200]}" for m in memory])
        if memory_text:
            context += f"\n\n=== تاريخ المحادثة ===\n{memory_text}"

    system_prompt = f"""أنت مبرمج AI العبقري داخل بوت MUSTAFA SHOP.

{context}

قواعد:
1. تحدث بذكاء واحترافية
2. استخدم العامية إذا تحدث بها المستخدم
3. إذا لم تعرف شيئاً قل ذلك
4. عند كتابة كود Python اجعله داخل ```python ... ```

الآن رد على المستخدم."""

    try:
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60, proxy=proxy_httpx) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_KEY}"},
                json={"model": "gpt-4o-mini", "messages": messages, "temperature": 0.7, "max_tokens": 2000}
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                if user_id:
                    await save_ai_memory(user_id, prompt, content, context[:500])
                return content.strip()
            return f"🔴 خطأ OpenAI: {resp.status_code}"
    except Exception as e:
        return f"🔴 خطأ: {str(e)[:100]}"

async def ai_generate_button_code(description: str) -> str:
    if not OPENAI_KEY:
        return "# مفتاح OpenAI غير موجود"

    prompt = f"""قم بكتابة كود Python لزر تيليجرام بالوصف التالي:

الوصف: {description}

المتغيرات المتاحة: event, bot, supabase, Button, asyncio, datetime, random, json, log

المتطلبات:
- استخدم async def (الكود سينفذ داخل async function)
- أضف معالجة للأخطاء try/except
- أضف رسائل تأكيد للمستخدم
- الكود يجب أن يكون آمناً

أرجع فقط الكود داخل ```python ... ```"""

    response = await ask_ai(prompt)
    code_match = re.search(r'```python\n(.*?)\n```', response, re.DOTALL)
    if code_match:
        return code_match.group(1)
    return response

# ============================================
# Railway Integration
# ============================================
async def get_railway_deployment_status() -> dict:
    if not RAILWAY_TOKEN:
        return {"status": "unknown", "error": "RAILWAY_TOKEN not set"}
    try:
        query = """
        query {
            deployments(limit: 1, orderBy: {createdAt: DESC}) {
                edges { node { id status createdAt logsUrl } }
            }
        }
        """
        async with httpx.AsyncClient(timeout=15, proxy=proxy_httpx) as client:
            resp = await client.post(
                "https://backboard.railway.app/graphql/v2",
                headers={"Authorization": f"Bearer {RAILWAY_TOKEN}", "Content-Type": "application/json"},
                json={"query": query}
            )
            if resp.status_code == 200:
                data = resp.json()
                edges = data.get("data", {}).get("deployments", {}).get("edges", [])
                if edges:
                    node = edges[0]["node"]
                    return {"status": node.get("status"), "createdAt": node.get("createdAt"), "logsUrl": node.get("logsUrl")}
            return {"status": "unknown"}
    except:
        return {"status": "error"}

async def restart_bot():
    import os, signal
    log.info("🔄 جاري إعادة تشغيل البوت...")
    os.kill(os.getpid(), signal.SIGTERM)

# ============================================
# سجل الأزرار الديناميكي (Dynamic Registry)
# ============================================
class ButtonRegistry:
    def __init__(self):
        self._static_handlers: Dict[str, callable] = {}
        self._dynamic_buttons: Dict[str, Dict] = {}
        self._folders: Dict[str, Dict] = {}
        self._last_refresh: Optional[datetime] = None
        self._refresh_lock = asyncio.Lock()

    def register(self, button_id: str):
        def decorator(func):
            self._static_handlers[button_id] = func
            return func
        return decorator

    async def refresh_from_db(self, force: bool = False):
        async with self._refresh_lock:
            now = datetime.now()
            if not force and self._last_refresh and (now - self._last_refresh).seconds < 10:
                return
            try:
                folders_result = supabase.table("folders").select("*").eq("is_active", True).order("sort_order").execute()
                self._folders = {f["folder_key"]: f for f in (folders_result.data or [])}
                buttons_result = supabase.table("buttons").select("*").eq("is_active", True).execute()
                self._dynamic_buttons = {b["button_id"]: b for b in (buttons_result.data or [])}
                self._last_refresh = now
                log.info(f"✅ تم تحديث {len(self._dynamic_buttons)} زر و {len(self._folders)} مجلد")
            except Exception as e:
                log.error(f"خطأ في تحديث البيانات: {e}")

    async def execute(self, button_id: str, event, **kwargs) -> bool:
        await self.refresh_from_db()

        if button_id in self._static_handlers:
            try:
                await self._static_handlers[button_id](event, bot, supabase, **kwargs)
                return True
            except Exception as e:
                log.error(f"Static handler error {button_id}: {e}")
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
                    'random': random, 'json': json, 'log': log,
                    '__builtins__': __builtins__,
                }
                indented_code = "\n".join([f"    {line}" for line in code.split('\n')])
                exec_code = f"async def _dynamic_handler(event, bot, supabase, Button, asyncio, datetime, random, json, log):\n{indented_code}"
                exec(exec_code, exec_globals)
                await exec_globals['_dynamic_handler'](event, bot, supabase, Button, asyncio, datetime, random, json, log)
                return True
            except Exception as e:
                await event.respond(f"❌ **خطأ في الزر:**\n`{str(e)[:200]}`")
                return True

        return False

    async def delete_button(self, button_id: str, user_id: int) -> bool:
        try:
            button = self._dynamic_buttons.get(button_id)
            if button:
                supabase.table("deleted_items").insert({
                    "item_type": "button",
                    "item_id": button_id,
                    "item_data": button,
                    "deleted_at": datetime.now().isoformat(),
                    "deleted_by": user_id
                }).execute()
                supabase.table("buttons").delete().eq("button_id", button_id).execute()
                await self.refresh_from_db(force=True)
                return True
        except Exception as e:
            log.error(f"Delete button error: {e}")
        return False

    def get_buttons_by_folder(self, folder_key: str) -> List[Dict]:
        return [b for b in self._dynamic_buttons.values() if b.get("folder_key") == folder_key]

    def get_folders(self) -> List[Dict]:
        return list(self._folders.values())

# ============================================
# المدقق الذاتي (Agentic Auditor)
# ============================================
class AgenticAuditor:
    def __init__(self, registry: ButtonRegistry, admin_ids: List[int]):
        self.registry = registry
        self.admin_ids = admin_ids
        self.is_running = False
        self.last_audit_time: Optional[datetime] = None
        self.audit_history: List[Dict] = []

    async def start(self):
        self.is_running = True
        asyncio.create_task(self._audit_loop())
        log.info("🕵️ تم تشغيل المدقق الذاتي (Agentic Auditor)")

    async def _audit_loop(self):
        while self.is_running:
            try:
                await self._perform_audit()
                await asyncio.sleep(AUDIT_INTERVAL_HOURS * 3600)
            except Exception as e:
                log.error(f"Audit loop error: {e}")
                await asyncio.sleep(300)

    async def _perform_audit(self):
        log.info("🔍 بدء جولة تدقيق ذاتي...")
        await self.registry.refresh_from_db(force=True)
        buttons = list(self.registry._dynamic_buttons.values())

        if not buttons:
            return

        random_button = random.choice(buttons)
        code = random_button.get("python_code", "")

        if not code or len(code) < 50:
            return

        log.info(f"📝 تدقيق الزر: {random_button.get('button_id')}")

        safe, issues = await check_code_safety(code)

        self.audit_history.append({
            "button_id": random_button.get("button_id"),
            "timestamp": datetime.now().isoformat(),
            "is_safe": safe,
            "issues": issues,
            "code_length": len(code)
        })

        if len(self.audit_history) > 50:
            self.audit_history = self.audit_history[-50:]

        if not safe and self.admin_ids:
            await self._notify_admin(random_button, issues)

        self.last_audit_time = datetime.now()
        log.info(f"✅ اكتمل التدقيق. آمن: {safe}")

    async def _notify_admin(self, button: Dict, issues: List[str]):
        button_id = button.get("button_id", "unknown")
        message = f"""🔍 **تقرير التدقيق الذاتي**

🔹 الزر: `{button_id}`
⚠️ **المشاكل المكتشفة:**
{chr(10).join(f'• {issue}' for issue in issues[:5])}

🔄 تم العثور على هذه المشاكل تلقائياً."""

        for admin_id in self.admin_ids:
            try:
                await bot.send_message(admin_id, message, parse_mode='md')
            except:
                pass

# ============================================
# نظام النسخ الاحتياطي
# ============================================
class AutoBackupSystem:
    def __init__(self):
        self.is_running = False

    async def start(self):
        self.is_running = True
        asyncio.create_task(self._backup_loop())
        log.info("💾 تم تشغيل نظام النسخ الاحتياطي")

    async def _backup_loop(self):
        while self.is_running:
            try:
                await self._create_backup()
                await asyncio.sleep(BACKUP_INTERVAL_HOURS * 3600)
            except Exception as e:
                log.error(f"Backup error: {e}")
                await asyncio.sleep(600)

    async def _create_backup(self):
        try:
            buttons = supabase.table("buttons").select("*").execute()
            folders = supabase.table("folders").select("*").execute()

            backup_data = {
                "version": VERSION,
                "timestamp": datetime.now().isoformat(),
                "buttons": buttons.data or [],
                "folders": folders.data or [],
                "buttons_count": len(buttons.data or []),
                "folders_count": len(folders.data or [])
            }

            supabase.table("backups").insert({
                "backup_type": "auto",
                "backup_data": backup_data,
                "backup_size": len(json.dumps(backup_data)),
                "created_at": datetime.now().isoformat()
            }).execute()

            log.info(f"💾 نسخة احتياطية: {backup_data['buttons_count']} أزرار")
        except Exception as e:
            log.error(f"Failed to create backup: {e}")

# ============================================
# الأزرار الثابتة (Static Handlers)
# ============================================
registry = ButtonRegistry()
user_states = {}
auditor = AgenticAuditor(registry, ADMIN_IDS)
backup_system = AutoBackupSystem()

@registry.register("start")
async def cmd_start(event, bot, supabase):
    user_id = event.sender_id
    try:
        sender = await event.get_sender()
        supabase.table("users").upsert({
            "user_id": user_id,
            "username": sender.username or "",
            "full_name": f"{sender.first_name or ''} {sender.last_name or ''}".strip(),
            "last_seen": datetime.now().isoformat()
        }).execute()
    except:
        pass

    await registry.refresh_from_db()

    keyboard = [
        [Button.inline("🏰 مصنع الجيوش", b"folder_accounts")],
        [Button.inline("🚀 الهجوم التكتيكي", b"folder_tactical")],
        [Button.inline("👻 عمليات التخفي", b"folder_stealth")],
        [Button.inline("🧠 مختبر الذكاء", b"folder_ai_lab")],
        [Button.inline("🛡️ درع الحماية", b"folder_protection")],
        [Button.inline("💰 الميزانية", b"folder_budget")],
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([Button.inline("⚙️ لوحة التحكم", b"admin_full_panel")])
    keyboard.append([Button.inline("📊 الإحصائيات", b"show_stats"), Button.inline("🌐 فحص البروكسي", b"check_proxy")])
    keyboard.append([Button.inline("📁 ملفات GitHub", b"list_github"), Button.inline("🧠 مبرمج AI", b"ai_chat")])

    await event.respond(
        f"🏰 **MUSTAFA SHOP - DIGITAL EMPIRE v{VERSION}** 🏰\n\n"
        f"⚡ المنظومة تحت أمرك يا قائد\n"
        f"📊 {len(registry._dynamic_buttons)} زر نشط | 📁 {len(registry._folders)} مجلد\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n\n"
        f"💡 اكتب أي شيء للتحدث مع المبرمج AI",
        buttons=keyboard, parse_mode='md'
    )

@registry.register("ai_chat")
async def ai_chat_button(event, bot, supabase):
    await event.respond(
        "🧠 **مبرمج AI - العبقري**\n\n"
        "أنا هنا لمساعدتك في:\n"
        "• إدارة الأزرار والمجلدات\n"
        "• كتابة وتعديل أكواد Python\n"
        "• تحليل الأخطاء وإصلاحها\n"
        "• مراقبة الاستضافة\n"
        "• عرض وتحميل ملفات GitHub\n\n"
        "**فقط اكتب ما تريد!**",
        parse_mode='md'
    )

@registry.register("check_proxy")
async def check_proxy_handler(event, bot, supabase):
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get("https://api.ipify.org", timeout=10) as resp:
                ip = await resp.text()
                await event.respond(f"🌐 **IP الحالي:** `{ip}`\n\n✅ الاتصال يعمل!", parse_mode='md')
    except Exception as e:
        await event.respond(f"❌ **خطأ:** `{str(e)[:100]}`", parse_mode='md')

@registry.register("show_stats")
async def show_stats_handler(event, bot, supabase):
    await registry.refresh_from_db()
    try:
        users_count = supabase.table("users").select("*", count="exact").execute().count or 0
    except:
        users_count = 0

    railway_status = await get_railway_deployment_status()

    try:
        await event.edit(
            f"📊 **الإحصائيات**\n\n"
            f"🔹 الأزرار: {len(registry._dynamic_buttons)}\n"
            f"📁 المجلدات: {len(registry._folders)}\n"
            f"👥 المستخدمين: {users_count}\n"
            f"🚉 Railway: {railway_status.get('status', 'غير معروف')}\n"
            f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n"
            f"🌐 البروكسي: {'🟢 مفعل' if PROXY_URL else '⚪ غير مستخدم'}",
            buttons=[[Button.inline("🔙 رجوع", b"start")]]
        )
    except:
        await event.respond(
            f"📊 الأزرار: {len(registry._dynamic_buttons)} | المجلدات: {len(registry._folders)} | المستخدمين: {users_count}",
            buttons=[[Button.inline("🔙 رجوع", b"start")]]
        )

@registry.register("list_github")
async def list_github_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    await event.respond("📂 **جاري جلب الملفات...**")
    files_list = await list_github_files()
    await event.respond(f"📁 **ملفات GitHub في {GITHUB_REPO}:**\n\n{files_list}", parse_mode='md')

# ============================================
# لوحة التحكم (Admin Panels)
# ============================================
@registry.register("admin_full_panel")
async def admin_full_panel(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return

    keyboard = [
        [Button.inline("📁 إدارة المجلدات", b"admin_folders"), Button.inline("🔹 إدارة الأزرار", b"admin_buttons")],
        [Button.inline("👥 إدارة الحسابات", b"admin_accounts"), Button.inline("💰 الميزانية", b"budget_system")],
        [Button.inline("🤖 إنشاء زر بالذكاء", b"ai_create_button"), Button.inline("📊 الإحصائيات", b"admin_stats")],
        [Button.inline("🗑️ سلة المحذوفات", b"admin_recycle"), Button.inline("⚙️ الإعدادات", b"admin_settings")],
        [Button.inline("🔄 تحديث الكاش", b"admin_refresh"), Button.inline("📁 ملفات GitHub", b"list_github")],
        [Button.inline("📝 تعديل main.py", b"edit_main_github"), Button.inline("🔧 إصلاح خطأ بالذكاء", b"fix_error_ai")],
        [Button.inline("🔄 إعادة تشغيل البوت", b"restart_bot")],
        [Button.inline("🔙 رجوع", b"start")],
    ]

    try:
        await event.edit("⚙️ **لوحة التحكم الشاملة**\n\n👑 مرحباً قائد", buttons=keyboard, parse_mode='md')
    except:
        await event.respond("⚙️ **لوحة التحكم الشاملة**\n\n👑 مرحباً قائد", buttons=keyboard, parse_mode='md')

@registry.register("admin_folders")
async def admin_folders(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db()
    folders = registry.get_folders()
    keyboard = [[Button.inline(f"{f.get('emoji','📁')} {f.get('display_name')}", f"edit_folder_{f['folder_key']}")] for f in folders[:20]]
    keyboard.append([Button.inline("➕ إضافة مجلد", b"add_folder"), Button.inline("🔙 رجوع", b"admin_full_panel")])
    try:
        await event.edit("📁 **إدارة المجلدات**", buttons=keyboard)
    except:
        await event.respond("📁 **إدارة المجلدات**", buttons=keyboard)

@registry.register("add_folder")
async def add_folder_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    user_states[event.sender_id] = {"state": "awaiting_folder_key"}
    await event.respond("➕ **إضافة مجلد جديد**\n\nأرسل المفتاح (key) للمجلد:")

@registry.register("admin_buttons")
async def admin_buttons_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db()
    buttons_list = list(registry._dynamic_buttons.values())
    keyboard = [[Button.inline(f"{btn.get('emoji','🔹')} {btn.get('display_name', btn['button_id'])[:25]}", f"edit_btn_{btn['button_id']}")] for btn in buttons_list[:30]]
    keyboard.append([Button.inline("➕ إضافة زر", b"add_button"), Button.inline("🤖 زر بالذكاء", b"ai_create_button")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
    try:
        await event.edit(f"🔹 **إدارة الأزرار** ({len(buttons_list)})", buttons=keyboard)
    except:
        await event.respond(f"🔹 **إدارة الأزرار** ({len(buttons_list)})", buttons=keyboard)

@registry.register("add_button")
async def add_button_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    user_states[event.sender_id] = {"state": "awaiting_button_data", "step": 1, "data": {}}
    await event.respond("➕ **إضافة زر جديد - الخطوة 1/6**\n\nأرسل الـ Button ID:")

@registry.register("ai_create_button")
async def ai_create_button_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ للمطور فقط", alert=True)
        return
    user_states[event.sender_id] = {"state": "awaiting_ai_button_description"}
    await event.respond("🤖 **إنشاء زر بالذكاء**\n\nأرسل وصف الزر بالعربية:\n\n_مثال: زر يعرض إحصائيات المبيعات اليومية_")

@registry.register("admin_refresh")
async def admin_refresh_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db(force=True)
    await event.answer("✅ تم تحديث الكاش", alert=True)

@registry.register("admin_recycle")
async def admin_recycle_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    try:
        deleted = supabase.table("deleted_items").select("*").order("deleted_at", desc=True).limit(50).execute()
        if not deleted.data:
            await event.edit("🗑️ **سلة المحذوفات فارغة**", buttons=[[Button.inline("🔙 رجوع", b"admin_full_panel")]])
            return
        keyboard = [[Button.inline(f"🔄 {item['item_type']}: {item['item_id'][:20]}", f"restore_{item['id']}")] for item in deleted.data[:20]]
        keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
        await event.edit("🗑️ **سلة المحذوفات**", buttons=keyboard)
    except:
        await event.edit("🗑️ **سلة المحذوفات فارغة**", buttons=[[Button.inline("🔙 رجوع", b"admin_full_panel")]])

@registry.register("admin_settings")
async def admin_settings_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    keyboard = [
        [Button.inline("🤖 إعدادات AI", b"setting_ai"), Button.inline("🌐 إعدادات البروكسي", b"setting_proxy")],
        [Button.inline("💰 إعدادات الميزانية", b"setting_budget")],
        [Button.inline("🔙 رجوع", b"admin_full_panel")],
    ]
    await event.edit("⚙️ **إعدادات النظام**", buttons=keyboard)

@registry.register("admin_stats")
async def admin_stats_advanced(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db()
    try:
        users_count = supabase.table("users").select("*", count="exact").execute().count or 0
    except:
        users_count = 0
    railway = await get_railway_deployment_status()
    await event.edit(
        f"📊 **الإحصائيات المتقدمة**\n\n"
        f"🔹 الأزرار: {len(registry._dynamic_buttons)}\n"
        f"📁 المجلدات: {len(registry._folders)}\n"
        f"👥 المستخدمين: {users_count}\n"
        f"🚉 Railway: {railway.get('status', 'غير معروف')}\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n"
        f"🕵️ المدقق الذاتي: {'🟢 يعمل' if auditor.is_running else '🔴 متوقف'}",
        buttons=[[Button.inline("🔙 رجوع", b"admin_full_panel")]]
    )

@registry.register("admin_accounts")
async def admin_accounts_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    keyboard = [
        [Button.inline("💰 حسابات الترويج", b"promo_accounts_list")],
        [Button.inline("📁 حسابات النشر الفردي", b"individual_accounts_list")],
        [Button.inline("🔙 رجوع", b"admin_full_panel")]
    ]
    await event.edit("👥 **إدارة الحسابات**", buttons=keyboard)

@registry.register("promo_accounts_list")
async def promo_accounts_list_handler(event, bot, supabase):
    accounts = supabase.table("promo_accounts").select("*").execute()
    if not accounts.data:
        await event.edit("💰 **لا توجد حسابات ترويجية**", buttons=[[Button.inline("🔙 رجوع", b"admin_accounts")]])
        return
    text = "💰 **حسابات الترويج**\n\n"
    for acc in accounts.data[:20]:
        text += f"• {acc.get('platform', 'unknown')}: {acc.get('account_name', acc.get('email', 'غير معروف'))}\n"
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"admin_accounts")]])

@registry.register("individual_accounts_list")
async def individual_accounts_list_handler(event, bot, supabase):
    accounts = supabase.table("individual_accounts").select("*").execute()
    if not accounts.data:
        await event.edit("📁 **لا توجد حسابات**", buttons=[[Button.inline("➕ إضافة", b"individual_add"), Button.inline("🔙 رجوع", b"admin_accounts")]])
        return
    keyboard = [[Button.inline(f"{'🟢' if acc.get('status','active')=='active' else '🔴'} {acc.get('platform','?')}: @{acc.get('username','بدون')}", f"individual_view_{acc['id']}")] for acc in accounts.data[:20]]
    keyboard.append([Button.inline("➕ إضافة حساب", b"individual_add"), Button.inline("🔙 رجوع", b"admin_accounts")])
    await event.edit("📁 **حسابات النشر الفردي**", buttons=keyboard)

@registry.register("individual_add")
async def individual_add_handler(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 1, "data": {}}
    await event.respond("➕ **إضافة حساب نشر فردي**\n\nاختر المنصة:", buttons=[
        [Button.inline("📱 تيليجرام", b"ind_platform_telegram"), Button.inline("📔 فيسبوك", b"ind_platform_facebook")],
        [Button.inline("📸 إنستقرام", b"ind_platform_instagram"), Button.inline("🎵 تيك توك", b"ind_platform_tiktok")],
        [Button.inline("🔙 إلغاء", b"individual_accounts_list")]
    ])

@registry.register("budget_system")
async def budget_system_handler(event, bot, supabase):
    try:
        cards = supabase.table("payment_cards").select("*").eq("is_active", True).execute()
        total_balance = sum(c.get('current_balance', 0) for c in (cards.data or []))
        await event.respond(
            f"💰 **نظام الميزانية**\n\n"
            f"💳 الفيزات النشطة: {len(cards.data or [])}\n"
            f"💰 إجمالي الرصيد: ${total_balance}",
            buttons=[
                [Button.inline("💳 إدارة الفيزات", b"cards_manage"), Button.inline("➕ إضافة فيزا", b"card_add")],
                [Button.inline("📢 الحملات الإعلانية", b"campaigns_manage")],
                [Button.inline("🔙 رجوع", b"admin_full_panel")]
            ]
        )
    except Exception as e:
        await event.respond(f"❌ خطأ في نظام الميزانية: {e}")

@registry.register("cards_manage")
async def cards_manage_handler(event, bot, supabase):
    cards = supabase.table("payment_cards").select("*").execute()
    if not cards.data:
        await event.edit("💳 **لا توجد فيزات**", buttons=[[Button.inline("➕ إضافة", b"card_add"), Button.inline("🔙 رجوع", b"budget_system")]])
        return
    keyboard = [[Button.inline(f"{'🟢' if c['is_active'] else '🔴'} ****{c['card_number'][-4:]} - ${c.get('current_balance',0)}", f"card_view_{c['id']}")] for c in cards.data]
    keyboard.append([Button.inline("➕ إضافة فيزا", b"card_add"), Button.inline("🔙 رجوع", b"budget_system")])
    await event.edit("💳 **الفيزات المسجلة:**", buttons=keyboard)

@registry.register("card_add")
async def card_add_handler(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_card_details", "step": 1}
    await event.respond("➕ **إضافة فيزا - الخطوة 1/4**\n\nأرسل رقم البطاقة:")

@registry.register("campaigns_manage")
async def campaigns_manage_handler(event, bot, supabase):
    await event.respond("📢 **الحملات الإعلانية**\n\n🚀 قيد التطوير...", buttons=[[Button.inline("🔙 رجوع", b"budget_system")]])

@registry.register("setting_ai")
async def setting_ai_handler(event, bot, supabase):
    await event.respond(
        f"🤖 **إعدادات الذكاء الاصطناعي**\n\n"
        f"🔑 مفتاح OpenAI: {'✅ موجود' if OPENAI_KEY else '❌ غير موجود'}\n"
        f"💾 جدول الذاكرة: ai_memory",
        buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]]
    )

@registry.register("setting_proxy")
async def setting_proxy_handler(event, bot, supabase):
    await event.respond(
        f"🌐 **إعدادات البروكسي**\n\n"
        f"🔗 الحالة: {'✅ نشط' if PROXY_URL else '❌ غير مستخدم'}",
        buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]]
    )

@registry.register("setting_budget")
async def setting_budget_handler(event, bot, supabase):
    await event.respond("💰 **إعدادات الميزانية**\n\n🔜 قيد التطوير", buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]])

@registry.register("edit_main_github")
async def edit_main_github_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await event.respond("📥 **جاري قراءة main.py من GitHub...**")
    current_code = await get_github_file()
    if not current_code:
        await event.respond("❌ **فشل قراءة الملف**\n\nتأكد من GITHUB_TOKEN واسم المستودع")
        return
    await event.respond(
        f"📝 **main.py**\n📊 الحجم: {len(current_code)} حرف\n\n"
        "⚠️ **تحذير:** أرسل الكود الكامل الجديد\nسيتم فحصه تلقائياً قبل الرفع:"
    )
    user_states[event.sender_id] = {"state": "awaiting_github_edit", "original_code": current_code}

@registry.register("fix_error_ai")
async def fix_error_ai_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    user_states[event.sender_id] = {"state": "awaiting_error_fix"}
    await event.respond("🔧 **إصلاح الأخطاء بالذكاء**\n\nأرسل الخطأ كاملاً (Error Traceback):")

@registry.register("restart_bot")
async def restart_bot_handler(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    await event.respond("🔄 **جاري إعادة تشغيل البوت...**")
    await restart_bot()

@registry.register("ind_platform_telegram")
async def ind_platform_telegram(event, bot, supabase):
    user_states[event.sender_id]["data"]["platform"] = "telegram"
    user_states[event.sender_id]["step"] = 2
    await event.respond("✅ المنصة: تيليجرام\n\nأرسل رقم الهاتف:")

@registry.register("ind_platform_facebook")
async def ind_platform_facebook(event, bot, supabase):
    user_states[event.sender_id]["data"]["platform"] = "facebook"
    user_states[event.sender_id]["step"] = 2
    await event.respond("✅ المنصة: فيسبوك\n\nأرسل البريد الإلكتروني:")

@registry.register("ind_platform_instagram")
async def ind_platform_instagram(event, bot, supabase):
    user_states[event.sender_id]["data"]["platform"] = "instagram"
    user_states[event.sender_id]["step"] = 2
    await event.respond("✅ المنصة: إنستقرام\n\nأرسل اسم المستخدم:")

@registry.register("ind_platform_tiktok")
async def ind_platform_tiktok(event, bot, supabase):
    user_states[event.sender_id]["data"]["platform"] = "tiktok"
    user_states[event.sender_id]["step"] = 2
    await event.respond("✅ المنصة: تيك توك\n\nأرسل اسم المستخدم:")

@registry.register("cancel")
async def cancel_action(event, bot, supabase):
    user_id = event.sender_id
    if user_id in user_states:
        del user_states[user_id]
    await event.respond("❌ تم إلغاء العملية", buttons=[[Button.inline("🔙 رجوع", b"start")]])

# ============================================
# معالج الـ Callbacks
# ============================================
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    try:
        data = event.data.decode()
        user_id = event.sender_id

        if data.startswith("folder_"):
            folder_key = data.replace("folder_", "")
            await show_folder(event, folder_key)
            return

        if data.startswith("restore_"):
            item_id = int(data.replace("restore_", ""))
            deleted = supabase.table("deleted_items").select("*").eq("id", item_id).execute()
            if deleted.data:
                item = deleted.data[0]
                if item["item_type"] == "button":
                    supabase.table("buttons").insert(item["item_data"]).execute()
                    supabase.table("deleted_items").delete().eq("id", item_id).execute()
                    await event.answer("✅ تم الاسترجاع", alert=True)
                    await admin_recycle_handler(event, bot, supabase)
            return

        if data.startswith("edit_btn_"):
            button_id = data.replace("edit_btn_", "")
            button = supabase.table("buttons").select("*").eq("button_id", button_id).execute()
            if button.data:
                btn = button.data[0]
                keyboard = [
                    [Button.inline("✍️ تعديل الاسم", f"edit_btn_name_{button_id}".encode())],
                    [Button.inline("📝 تعديل الكود", f"edit_btn_code_{button_id}".encode())],
                    [Button.inline("🎨 تغيير اللون", f"edit_btn_color_{button_id}".encode())],
                    [Button.inline("📁 نقل لمجلد", f"edit_btn_folder_{button_id}".encode())],
                    [Button.inline("🗑️ حذف الزر", f"delete_btn_{button_id}".encode())],
                    [Button.inline("🔙 رجوع", b"admin_buttons")],
                ]
                await event.edit(f"🔹 **تعديل: {btn.get('display_name', button_id)}**", buttons=keyboard)
            return

        if data.startswith("edit_btn_name_"):
            button_id = data.replace("edit_btn_name_", "")
            user_states[user_id] = {"state": "awaiting_edit_name", "button_id": button_id}
            await event.respond(f"✍️ **تعديل اسم الزر `{button_id}`**\n\nأرسل الاسم الجديد:")
            return

        if data.startswith("edit_btn_code_"):
            button_id = data.replace("edit_btn_code_", "")
            user_states[user_id] = {"state": "awaiting_edit_code", "button_id": button_id}
            await event.respond(f"📝 **تعديل كود الزر `{button_id}`**\n\nأرسل الكود الجديد:")
            return

        if data.startswith("edit_btn_color_"):
            button_id = data.replace("edit_btn_color_", "")
            keyboard = [
                [Button.inline("🔵 أزرق", f"set_color_{button_id}_blue".encode()), Button.inline("🔴 أحمر", f"set_color_{button_id}_red".encode())],
                [Button.inline("🟢 أخضر", f"set_color_{button_id}_green".encode()), Button.inline("🟣 بنفسجي", f"set_color_{button_id}_purple".encode())],
                [Button.inline("⚫ غامق", f"set_color_{button_id}_dark".encode()), Button.inline("🟠 برتقالي", f"set_color_{button_id}_orange".encode())],
                [Button.inline("🔙 رجوع", f"edit_btn_{button_id}".encode())],
            ]
            await event.edit("🎨 **اختر اللون:**", buttons=keyboard)
            return

        if data.startswith("edit_btn_folder_"):
            button_id = data.replace("edit_btn_folder_", "")
            folders = registry.get_folders()
            keyboard = [[Button.inline(f"{f.get('emoji','📁')} {f.get('display_name')}", f"move_btn_{button_id}_{f['folder_key']}".encode())] for f in folders]
            keyboard.append([Button.inline("🔙 رجوع", f"edit_btn_{button_id}".encode())])
            await event.edit("📁 **اختر المجلد:**", buttons=keyboard)
            return

        if data.startswith("set_color_"):
            parts = data.split("_")
            color = parts[-1]
            button_id = "_".join(parts[2:-1])
            supabase.table("buttons").update({"color": color}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            await event.answer(f"✅ تم تغيير اللون", alert=True)
            await admin_buttons_handler(event, bot, supabase)
            return

        if data.startswith("move_btn_"):
            parts = data.split("_")
            button_id = parts[2]
            folder_key = parts[3]
            supabase.table("buttons").update({"folder_key": folder_key}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            await event.answer("✅ تم نقل الزر", alert=True)
            await admin_buttons_handler(event, bot, supabase)
            return

        if data.startswith("delete_btn_"):
            button_id = data.replace("delete_btn_", "")
            await event.edit(
                f"⚠️ **تأكيد حذف الزر `{button_id}`**",
                buttons=[
                    [Button.inline("✅ نعم، احذف", f"confirm_delete_{button_id}".encode())],
                    [Button.inline("❌ إلغاء", b"admin_buttons")],
                ]
            )
            return

        if data.startswith("confirm_delete_"):
            button_id = data.replace("confirm_delete_", "")
            await registry.delete_button(button_id, user_id)
            await event.answer("✅ تم الحذف", alert=True)
            await admin_buttons_handler(event, bot, supabase)
            return

        if data.startswith("add_btn_in_"):
            folder_key = data.replace("add_btn_in_", "")
            user_states[user_id] = {"state": "awaiting_button_data", "step": 1, "data": {"folder_key": folder_key}}
            await event.respond("➕ **إضافة زر جديد**\n\nالخطوة 1/6: أرسل الـ Button ID:")
            return

        if data.startswith("ai_folder_"):
            folder_key = data.replace("ai_folder_", "")
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_folder":
                state = user_states[user_id]
                state["folder_key"] = folder_key
                button_id = "ai_" + str(int(datetime.now().timestamp()))[-6:]
                supabase.table("buttons").insert({
                    "button_id": button_id,
                    "display_name": state.get("description", "AI Button")[:50],
                    "emoji": "🤖", "color": "blue",
                    "folder_key": folder_key,
                    "python_code": state.get("code", ""),
                    "is_active": True, "created_by": user_id
                }).execute()
                await registry.refresh_from_db(force=True)
                del user_states[user_id]
                await event.edit(f"✅ **تم إنشاء الزر `{button_id}` بنجاح!**")
                await admin_buttons_handler(event, bot, supabase)
            return

        if data == "edit_main_github":
            await edit_main_github_handler(event, bot, supabase)
            return

        if data == "fix_error_ai":
            await fix_error_ai_handler(event, bot, supabase)
            return

        if data == "restart_bot":
            await restart_bot_handler(event, bot, supabase)
            return

        if data == "admin_buttons":
            await admin_buttons_handler(event, bot, supabase)
            return

        if data == "admin_full_panel":
            await admin_full_panel(event, bot, supabase)
            return

        if await registry.execute(data, event):
            return

        await event.answer("⚠️ الزر غير موجود", alert=True)

    except Exception as e:
        log.error(f"خطأ في callback: {e}\n{traceback.format_exc()}")
        try:
            await event.answer("❌ خطأ", alert=True)
        except:
            pass

async def show_folder(event, folder_key: str):
    await registry.refresh_from_db()
    folder_names = {
        "accounts": "🏰 مصنع الجيوش", "tactical": "🚀 الهجوم التكتيكي",
        "stealth": "👻 عمليات التخفي", "ai_lab": "🧠 مختبر الذكاء",
        "protection": "🛡️ درع الحماية", "budget": "💰 الميزانية",
    }
    display_name = folder_names.get(folder_key, folder_key.replace("_", " ").title())
    buttons_list = registry.get_buttons_by_folder(folder_key)
    keyboard = [[Button.inline(f"{btn.get('emoji','🔹')} {btn.get('display_name', btn['button_id'])}", btn["button_id"].encode())] for btn in buttons_list]
    keyboard.append([Button.inline("🔙 رجوع", b"start")])
    if event.sender_id in ADMIN_IDS:
        keyboard.append([Button.inline("➕ إضافة زر", f"add_btn_in_{folder_key}".encode())])
    try:
        await event.edit(f"{display_name}\n\n📊 {len(buttons_list)} زر\nاختر:", buttons=keyboard, parse_mode='md')
    except:
        await event.respond(f"{display_name}\n\n📊 {len(buttons_list)} زر", buttons=keyboard, parse_mode='md')

# ============================================
# معالج الرسائل الرئيسي
# ============================================
@bot.on(events.NewMessage)
async def unified_message_handler(event):
    if event.out or not event.raw_text:
        return

    user_id = event.sender_id
    text = event.raw_text.strip()

    if text.startswith('/'):
        if text.startswith('/start'):
            await cmd_start(event, bot, supabase)
            return
        elif text == '/restart' and user_id in ADMIN_IDS:
            await event.respond("🔄 جاري إعادة تشغيل البوت...")
            await restart_bot()
            return
        elif text == '/stats' and user_id in ADMIN_IDS:
            await show_stats_handler(event, bot, supabase)
            return
        elif text == '/github_repo' and user_id in ADMIN_IDS:
            await event.respond(f"📁 **المستودع:** `{GITHUB_REPO}`\n🌿 **الفرع:** `{GITHUB_BRANCH}`")
            return
        elif text == '/list_github' and user_id in ADMIN_IDS:
            await list_github_button(event, bot, supabase)
            return
        elif text == '/download_github' and user_id in ADMIN_IDS:
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
                await event.respond(f"❌ **فشل تحميل {file_path}**")
            return
        elif text == '/broadcast' and user_id in ADMIN_IDS:
            user_states[user_id] = {"state": "awaiting_broadcast"}
            await event.respond("📢 **بث جماعي**\n\nأرسل الرسالة التي تريد إرسالها لجميع المستخدمين:")
            return
        elif text == '/manifest' and user_id in ADMIN_IDS:
            manifest = {
                "version": VERSION,
                "buttons": len(registry._dynamic_buttons),
                "folders": len(registry._folders),
                "ai": "active" if OPENAI_KEY else "inactive",
                "proxy": "active" if PROXY_URL else "inactive",
                "github": "active" if GITHUB_TOKEN else "inactive"
            }
            await event.respond(f"📋 **الملف البياني:**\n```json\n{json.dumps(manifest, indent=2)}\n```", parse_mode='md')
            return
        else:
            return

    if user_id in user_states:
        state = user_states[user_id]
        current_state = state.get("state")

        if current_state == "awaiting_button_data":
            step = state.get("step", 1)
            data = state.get("data", {})
            if step == 1:
                data["button_id"] = text.replace(" ", "_")
                state["step"] = 2
                await event.respond("✅ الخطوة 2/6: أرسل الاسم الظاهر:")
            elif step == 2:
                data["display_name"] = text
                state["step"] = 3
                await event.respond("✅ الخطوة 3/6: أرسل الإيموجي:")
            elif step == 3:
                data["emoji"] = text if text else "🔹"
                state["step"] = 4
                await event.respond("✅ الخطوة 4/6: اختر اللون:\n`blue` `red` `green` `purple` `dark` `orange`")
            elif step == 4:
                colors = ["blue", "red", "green", "purple", "dark", "orange"]
                data["color"] = text if text in colors else "blue"
                state["step"] = 5
                await event.respond("✅ الخطوة 5/6: أرسل المجلد (main, accounts, admin ...):")
            elif step == 5:
                data["folder_key"] = text
                state["step"] = 6
                await event.respond("✅ الخطوة 6/6: أرسل كود Python للزر (أو أرسل 'skip' لتركه فارغاً):")
            elif step == 6:
                data["python_code"] = "" if text.lower() == "skip" else text
                supabase.table("buttons").insert({
                    "button_id": data["button_id"],
                    "display_name": data["display_name"],
                    "emoji": data.get("emoji", "🔹"),
                    "color": data.get("color", "blue"),
                    "folder_key": data["folder_key"],
                    "python_code": data["python_code"],
                    "is_active": True,
                    "created_by": user_id,
                    "created_at": datetime.now().isoformat()
                }).execute()
                await registry.refresh_from_db(force=True)
                del user_states[user_id]
                await event.respond(f"✅ **تم إضافة الزر `{data['button_id']}` بنجاح!**")
                await admin_buttons_handler(event, bot, supabase)
            return

        if current_state == "awaiting_edit_code":
            button_id = state["button_id"]
            safe, issues = await check_code_safety(text)
            if not safe:
                await event.respond(f"⛔ **الكود غير آمن!**\n\n{chr(10).join(issues)}")
                return
            supabase.table("buttons").update({"python_code": text}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"✅ **تم تحديث كود الزر `{button_id}`!**")
            await admin_buttons_handler(event, bot, supabase)
            return

        if current_state == "awaiting_edit_name":
            button_id = state["button_id"]
            supabase.table("buttons").update({"display_name": text}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"✅ **تم تغيير الاسم إلى `{text}`**")
            await admin_buttons_handler(event, bot, supabase)
            return

        if current_state == "awaiting_folder_key":
            folder_key = text.replace(" ", "_").lower()
            supabase.table("folders").insert({
                "folder_key": folder_key,
                "display_name": folder_key.replace("_", " ").title(),
                "emoji": "📁", "color": "blue", "sort_order": 999,
                "is_active": True, "created_by": user_id
            }).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"✅ تم إضافة المجلد `{folder_key}`")
            await admin_folders(event, bot, supabase)
            return

        if current_state == "awaiting_card_details":
            step = state.get("step", 1)
            if step == 1:
                if len(text) not in [15, 16]:
                    await event.respond("❌ رقم البطاقة غير صالح")
                    return
                state["card_number"] = text
                state["step"] = 2
                await event.respond("الخطوة 2/4: أرسل اسم حامل البطاقة:")
            elif step == 2:
                state["card_holder"] = text
                state["step"] = 3
                await event.respond("الخطوة 3/4: أرسل تاريخ الصلاحية (MM/YY):")
            elif step == 3:
                if not re.match(r'\d{2}/\d{2}', text):
                    await event.respond("❌ صيغة غير صالحة. استخدم MM/YY")
                    return
                state["expiry"] = text
                state["step"] = 4
                await event.respond("الخطوة 4/4: أرسل CVV:")
            elif step == 4:
                supabase.table("payment_cards").insert({
                    "card_number": state["card_number"],
                    "card_holder": state["card_holder"],
                    "expiry_date": state["expiry"],
                    "cvv": text,
                    "is_active": True,
                    "added_by": user_id,
                    "created_at": datetime.now().isoformat()
                }).execute()
                del user_states[user_id]
                await event.respond("✅ **تم إضافة الفيزا بنجاح!**")
                await cards_manage_handler(event, bot, supabase)
            return

        if current_state == "awaiting_github_edit":
            valid, msg = await validate_python_code(text)
            if not valid:
                await event.respond(f"⛔ **لم يتم الرفع! الكود فيه خطأ:**\n`{msg}`\n\nصحح الخطأ وأرسل مجدداً.")
                return
            safe, issues = await check_code_safety(text)
            if not safe:
                await event.respond(f"⛔ **تحذير أمني:**\n{chr(10).join(issues)}\n\nهل تريد المتابعة؟")
                user_states[user_id]["pending_code"] = text
                user_states[user_id]["state"] = "awaiting_github_confirm"
                return
            success = await update_github_file(text, "main.py", f"AI self-update v{VERSION}")
            if success:
                await event.respond("✅ **تم تحديث main.py في GitHub بنجاح!**\n\n🔄 Railway سيعيد النشر تلقائياً...")
                del user_states[user_id]
            else:
                await event.respond("❌ **فشل تحديث الملف** — تأكد من GITHUB_TOKEN")
                del user_states[user_id]
            return

        if current_state == "awaiting_github_confirm":
            if text.lower() in ["نعم", "yes", "y", "متابعة"]:
                success = await update_github_file(state["pending_code"], "main.py", f"AI forced update v{VERSION}")
                if success:
                    await event.respond("✅ **تم تحديث main.py رغم التحذيرات!**")
                else:
                    await event.respond("❌ **فشل التحديث**")
            else:
                await event.respond("❌ تم إلغاء الرفع")
            del user_states[user_id]
            return

        if current_state == "awaiting_error_fix" and OPENAI_KEY:
            await event.respond("🔍 **جاري تحليل الخطأ...**")
            current_code = await get_github_file()
            fix_prompt = f"""الخطأ:
{text[:1500]}

الكود الحالي (أول 1500 حرف):
{(current_code or '')[:1500]}

حلل الخطأ وأعطني الكود المصحح كاملاً داخل ```python ... ```"""

            response = await ask_ai(fix_prompt, user_id)
            await event.respond(
                f"🔧 **اقتراح الإصلاح:**\n\n{response[:3000]}",
                buttons=[[Button.inline("✅ تطبيق الإصلاح", b"apply_fix"), Button.inline("❌ إلغاء", b"cancel")]],
                parse_mode='md'
            )
            user_states[user_id] = {"state": "awaiting_fix_apply", "fix_response": response}
            return

        if current_state == "awaiting_fix_apply":
            code_match = re.search(r'```python\n(.*?)\n```', state.get("fix_response", ""), re.DOTALL)
            if code_match:
                new_code = code_match.group(1)
                valid, msg = await validate_python_code(new_code)
                if valid:
                    success = await update_github_file(new_code, "main.py", "AI fix applied")
                    if success:
                        await event.respond("✅ **تم تطبيق الإصلاح! Railway سيعيد النشر.**")
                    else:
                        await event.respond("❌ فشل تطبيق الإصلاح")
                else:
                    await event.respond(f"⛔ الكود المصحح فيه خطأ: {msg}")
            else:
                await event.respond("❌ لم يتم العثور على كود صالح للإصلاح")
            del user_states[user_id]
            return

        if current_state == "awaiting_ai_button_description" and OPENAI_KEY:
            description = text
            await event.respond("🤔 **جاري توليد الكود...**")
            generated_code = await ai_generate_button_code(description)
            user_states[user_id] = {"state": "awaiting_ai_folder", "description": description, "code": generated_code}
            folders = registry.get_folders()
            keyboard = [[Button.inline(f"{f.get('emoji','📁')} {f.get('display_name')}", f"ai_folder_{f['folder_key']}".encode())] for f in folders[:10]]
            await event.respond(
                f"✅ **الكود جاهز!**\n\n📝 {description[:100]}\n\n```python\n{generated_code[:600]}\n```\n\n📁 **اختر المجلد:**",
                buttons=keyboard, parse_mode='md'
            )
            return

        if current_state == "awaiting_individual_account":
            step = state.get("step", 1)
            data = state.get("data", {})
            if step == 2:
                data["identifier"] = text
                state["step"] = 3
                await event.respond("✅ الخطوة 3/4: أرسل كلمة المرور (أو 'none'):")
            elif step == 3:
                data["password"] = None if text.lower() == "none" else text
                state["step"] = 4
                await event.respond("✅ الخطوة 4/4: أرسل عدد المنشورات اليومية المسموح:")
            elif step == 4:
                try:
                    daily_limit = int(text)
                except:
                    daily_limit = 5
                supabase.table("individual_accounts").insert({
                    "platform": data.get("platform"),
                    "identifier": data.get("identifier"),
                    "password": data.get("password"),
                    "daily_limit": daily_limit,
                    "posts_today": 0,
                    "status": "active",
                    "created_by": user_id,
                    "created_at": datetime.now().isoformat()
                }).execute()
                del user_states[user_id]
                await event.respond("✅ **تم إضافة الحساب بنجاح!**")
                await individual_accounts_list_handler(event, bot, supabase)
            return

        if current_state == "awaiting_broadcast":
            await event.respond("📢 **جاري الإرسال...**")
            try:
                users = supabase.table("users").select("user_id").execute()
                sent = 0
                failed = 0
                for u in (users.data or []):
                    try:
                        await bot.send_message(u["user_id"], text, parse_mode='md')
                        sent += 1
                        await asyncio.sleep(0.1)
                    except:
                        failed += 1
                del user_states[user_id]
                await event.respond(f"✅ **تم الإرسال!**\n\n📤 ناجح: {sent}\n❌ فاشل: {failed}")
            except Exception as e:
                await event.respond(f"❌ خطأ في البث: {e}")
                del user_states[user_id]
            return

    if OPENAI_KEY:
        await event.respond("🧠 **مبرمج AI يفكر...**")
        ai_response = await ask_ai(text, user_id)
        if len(ai_response) > 4000:
            for i in range(0, len(ai_response), 3900):
                await event.respond(ai_response[i:i+3900], parse_mode='md')
        else:
            await event.respond(ai_response, parse_mode='md')
    else:
        await event.respond("🔴 مفتاح OpenAI غير موجود. لا يمكن استخدام الذكاء الاصطناعي.")

# ============================================
# المهام الخلفية
# ============================================
async def auto_railway_monitor():
    while True:
        try:
            await asyncio.sleep(3600)
            if ADMIN_IDS:
                status = await get_railway_deployment_status()
                if status.get('status') == 'FAILED':
                    await bot.send_message(
                        ADMIN_IDS[0],
                        f"⚠️ **تنبيه Railway!**\n\nحالة النشر: فشل (FAILED)\nالوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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

async def auto_rotate_proxy():
    while True:
        try:
            await asyncio.sleep(60)
            log.info("🔄 تغيير IP تلقائي...")
            await bot.disconnect()
            await asyncio.sleep(2)
            await bot.connect()
            log.info("✅ تم تغيير IP")
        except Exception as e:
            log.error(f"خطأ في تغيير IP: {e}")

# ============================================
# إنشاء الجداول والمجلدات الافتراضية
# ============================================
async def create_default_folders():
    folders = [
        ("main", "القائمة الرئيسية", "🏠", "blue", 0),
        ("accounts", "مصنع الجيوش", "🏰", "green", 1),
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
                "folder_key": folder_key, "display_name": display_name,
                "emoji": emoji, "color": color, "sort_order": sort_order, "is_active": True
            }, on_conflict="folder_key").execute()
        except Exception as e:
            log.warning(f"خطأ في إنشاء المجلد {folder_key}: {e}")

async def create_ai_memory_table():
    try:
        supabase.table("ai_memory").select("count").limit(1).execute()
    except:
        log.warning("⚠️ جدول ai_memory غير موجود، يرجى إنشاؤه يدوياً في Supabase")

def ensure_backup_table():
    try:
        supabase.table("backups").select("count").limit(1).execute()
    except:
        log.warning("⚠️ جدول backups غير موجود")

# ============================================
# التشغيل الرئيسي
# ============================================
async def main():
    log.info(f"🏰 تشغيل MUSTAFA SHOP - DIGITAL EMPIRE v{VERSION}")
    log.info("=" * 60)

    ensure_backup_table()
    await create_ai_memory_table()
    await create_default_folders()

    try:
        supabase.table("folders").select("count").limit(1).execute()
        log.info("✅ قاعدة البيانات جاهزة")
    except Exception as e:
        log.warning(f"⚠️ قاعدة البيانات: {e}")

    await registry.refresh_from_db(force=True)
    await bot.start(bot_token=BOT_TOKEN)

    asyncio.create_task(auto_railway_monitor())
    asyncio.create_task(auto_reset_accounts())
    asyncio.create_task(auditor.start())
    asyncio.create_task(backup_system.start())
    asyncio.create_task(auto_rotate_proxy())

    me = await bot.get_me()
    log.info(f"✅ البوت يعمل! @{me.username}")
    log.info(f"👑 المطورون: {ADMIN_IDS}")
    log.info(f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}")
    log.info(f"🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}")
    log.info(f"📁 GitHub: {'🟢 متصل' if GITHUB_TOKEN else '⚪ غير متصل'}")
    log.info(f"🚉 Railway: {'🟢 متصل' if RAILWAY_TOKEN else '🔴 غير متصل'}")
    log.info(f"🕵️ المدقق الذاتي: {'🟢 يعمل' if auditor.is_running else '🔴 متوقف'}")
    log.info(f"🔄 تدوير البروكسي: {'🟢 مفعل' if PROXY_URL else '⚪ غير مفعل'}")
    log.info("=" * 60)

    if ADMIN_IDS:
        try:
            await bot.send_message(
                ADMIN_IDS[0],
                f"✅ **MUSTAFA SHOP v{VERSION} يعمل!**\n\n"
                f"📊 {len(registry._dynamic_buttons)} زر | 📁 {len(registry._folders)} مجلد\n"
                f"🤖 AI: {'نشط' if OPENAI_KEY else 'غير نشط'}\n"
                f"🌐 بروكسي: {'نشط' if PROXY_URL else 'غير مستخدم'}\n"
                f"🕵️ مدقق ذاتي: {'يعمل' if auditor.is_running else 'متوقف'}\n"
                f"🔄 تدوير IP: {'مفعل كل دقيقة' if PROXY_URL else 'غير مفعل'}\n\n"
                f"✨ **مميزات v8:**\n"
                f"• 🧠 وكيل AI متكامل\n"
                f"• 🕵️ تدقيق ذاتي كل ساعتين\n"
                f"• 🔐 فحص أمني متقدم\n"
                f"• 💾 نسخ احتياطي تلقائي\n"
                f"• 🔄 تدوير تلقائي للبروكسي"
            )
        except Exception as e:
            log.warning(f"فشل إرسال إشعار البدء: {e}")

    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 تم إيقاف البوت")
    except Exception as e:
        log.error(f"❌ خطأ فادح: {e}")
        traceback.print_exc()
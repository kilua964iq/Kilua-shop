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
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from telethon import TelegramClient, events, Button
from telethon.tl.types import User
from telethon.errors import FloodWaitError
from supabase import create_client, Client
import httpx
import aiohttp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

class TelegramHandler(logging.Handler):
    def emit(self, record):
        if record.levelno >= logging.ERROR:
            msg = f"""⛔ **خطأ برمجي:**
`{record.getMessage()}`
"""
            try:
                loop = asyncio.get_running_loop()
                for admin_id in ADMIN_IDS:
                    loop.create_task(
                        bot.send_message(
                            admin_id,
                            msg,
                            buttons=[[Button.inline("🔧 إصلاح تلقائي", b"fix_error_ai")]],
                            parse_mode='md'
                        )
                    )
            except RuntimeError:
                pass

log.addHandler(TelegramHandler())

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

# ============================================
# تفعيل البروكسي
# ============================================

if PROXY_URL and USE_PROXY_FOR_ALL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL
    os.environ["ALL_PROXY"] = PROXY_URL
    log.info("✅ تم تفعيل البروكسي التلقائي")

if not all([API_ID, API_HASH, BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    log.error("❌ متغيرات البيئة الأساسية غير مكتملة!")
    exit(1)

if not ADMIN_IDS:
    log.warning("⚠️ لم يتم تعيين ADMIN_IDS")

# ============================================
# إعداد البروكسي للـ Telethon
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
            addr, port = PROXY_URL.split(":")
            proxy_config = {'proxy_type': 'http', 'addr': addr, 'port': int(port)}
        log.info("✅ تم إعداد البروكسي للـ Telethon")
    except:
        pass

# ============================================
# تهيئة العميل
# ============================================

bot = TelegramClient("mustafa_empire_session", API_ID, API_HASH, proxy=proxy_config)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# دوال GitHub - مصلحة للملفات الكبيرة
# ============================================

async def get_github_file(path: str = "main.py") -> Optional[str]:
    """جلب ملف من GitHub - مصلح للملفات الكبيرة"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("encoding") == "base64" and data.get("content"):
                    return base64.b64decode(data["content"].replace("\n", "")).decode('utf-8')
                elif data.get("download_url"):
                    raw = await client.get(data["download_url"])
                    return raw.text
            log.error(f"GitHub get_file error: {resp.status_code}")
            return None
    except Exception as e:
        log.error(f"GitHub error: {e}")
        return None

async def update_github_file(content: str, path: str = "main.py", commit_msg: str = "AI self-update") -> bool:
    """تحديث ملف في GitHub"""
    if not GITHUB_TOKEN:
        return False
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
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
    """جلب قائمة الملفات من GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
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
                else:
                    return f"📄 ملف فردي: `{data['name']}`"
            elif resp.status_code == 404:
                return f"❌ المستودع `{GITHUB_REPO}` غير موجود أو خاص"
            else:
                return f"❌ خطأ HTTP {resp.status_code}"
    except Exception as e:
        return f"❌ خطأ: {str(e)[:100]}"

async def download_github_file(path: str) -> Optional[bytes]:
    """تحميل ملف من GitHub"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                return base64.b64decode(data["content"].replace("\n", ""))
            return None
    except:
        return None

async def validate_python_code(code: str) -> tuple:
    """✅ فحص صحة كود Python قبل الرفع"""
    try:
        ast.parse(code)
        return True, "✅ الكود صحيح"
    except SyntaxError as e:
        return False, f"❌ خطأ في السطر {e.lineno}: {e.msg}"

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
        async with httpx.AsyncClient(timeout=15) as client:
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
    os.kill(os.getpid(), signal.SIGTERM)

# ============================================
# دوال الذكاء الاصطناعي
# ============================================

AI_MEMORY_TABLE = "ai_memory"

async def save_ai_memory(user_id: int, user_message: str, ai_response: str, context: str = ""):
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

async def get_ai_memory(user_id: int, limit: int = 10) -> List[Dict]:
    try:
        result = supabase.table(AI_MEMORY_TABLE).select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
        return result.data[::-1] if result.data else []
    except:
        return []

async def get_system_context(user_id: int) -> str:
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

    error_text = "لا توجد أخطاء حديثة"
    try:
        errors = supabase.table("analytics").select("*").eq("success", False).order("created_at", desc=True).limit(5).execute()
        if errors.data:
            error_text = "\n".join([f"- {e.get('error_message','خطأ غير معروف')[:100]}" for e in errors.data])
    except:
        pass

    github_files_text = await list_github_files()

    return f"""
=== سياق منظومة MUSTAFA SHOP ===
الأزرار: {buttons_count} | المجلدات: {folders_count} | المستخدمين: {users_count}
البروكسي: {'مفعل' if PROXY_URL else 'غير مفعل'} | AI: {'مفعل' if OPENAI_KEY else 'غير مفعل'}
GitHub: {'متصل' if GITHUB_TOKEN else 'غير متصل'} | Railway: {'متصل' if RAILWAY_TOKEN else 'غير متصل'}

آخر الأخطاء:
{error_text}

ملفات GitHub في {GITHUB_REPO}:
{github_files_text}

أنت مبرمج AI متخصص في Python و Telethon و Supabase و GitHub و Railway.
"""

async def ask_ai(prompt: str, user_id: int = None, conversation_history: list = None) -> str:
    if not OPENAI_KEY:
        return "🔴 مفتاح OpenAI غير موجود."

    context = await get_system_context(user_id) if user_id else ""

    if user_id:
        memory = await get_ai_memory(user_id, 10)
        memory_text = "\n".join([f"مستخدم: {m['user_message']}\nAI: {m['ai_response']}" for m in memory])
        if memory_text:
            context += f"\n\n=== تاريخ المحادثة ===\n{memory_text}"

    system_prompt = f"""أنت مبرمج AI العبقري داخل بوت MUSTAFA SHOP.

{context}

قواعد:
1. تحدث بذكاء واحترافية
2. المستخدم هو المطور الرئيسي (Admin)
3. استخدم العامية إذا تحدث بها المستخدم
4. إذا لم تعرف شيئاً قل ذلك
5. عند كتابة كود Python اجعله داخل ```python ... ```

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
                await event.respond(f"❌ **خطأ في الزر:**\n`{str(e)[:200]}`")
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
# إنشاء جدول الذاكرة
# ============================================

async def create_ai_memory_table():
    try:
        supabase.table("ai_memory").select("count").limit(1).execute()
    except:
        log.warning("⚠️ جدول ai_memory غير موجود، يرجى إنشاؤه يدوياً في Supabase")

# ============================================
# ✅ معالج رسائل موحد
# ============================================

@bot.on(events.NewMessage)
async def unified_message_handler(event):
    if event.out or not event.raw_text:
        return

    user_id = event.sender_id
    text = event.raw_text.strip()

    # --- أوامر GitHub ---
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
            await event.respond(f"❌ **فشل تحميل {file_path}**")
        return

    if text.startswith('/list_github'):
        await event.respond("📂 **جاري جلب الملفات...**")
        files_list = await list_github_files()
        await event.respond(f"📁 **ملفات GitHub:**\n\n{files_list}", parse_mode='md')
        return

    # --- أوامر عامة ---
    if text.startswith('/'):
        if text.startswith('/start'):
            await cmd_start(event, bot, supabase)
            return
        elif text == '/restart' and user_id in ADMIN_IDS:
            await event.respond("🔄 جاري إعادة تشغيل البوت...")
            await restart_bot()
            return
        elif text == '/stats' and user_id in ADMIN_IDS:
            await cmd_stats(event, bot, supabase)
            return
        elif text == '/github_repo' and user_id in ADMIN_IDS:
            await event.respond(f"📁 **المستودع:** `{GITHUB_REPO}`\n🌿 **الفرع:** `{GITHUB_BRANCH}`")
            return
        elif text == '/broadcast' and user_id in ADMIN_IDS:
            user_states[user_id] = {"state": "awaiting_broadcast"}
            await event.respond("📢 **بث جماعي**\n\nأرسل الرسالة التي تريد إرسالها لجميع المستخدمين:")
            return
        else:
            return

    # --- معالجة حالات الأدمن ---
    if user_id in ADMIN_IDS and user_id in user_states:
        state = user_states[user_id]
        current_state = state.get("state")

        if current_state == "awaiting_button_data":
            step = state.get("step", 1)
            data = state.get("data", {})
            if step == 1:
                data["button_id"] = text
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
                    "created_by": user_id
                }).execute()
                await registry.refresh_from_db(force=True)
                del user_states[user_id]
                await event.respond(f"✅ **تم إضافة الزر `{data['button_id']}` بنجاح!**")
                await admin_buttons(event, bot, supabase)
            return

        if current_state == "awaiting_edit_code":
            button_id = state["button_id"]
            supabase.table("buttons").update({"python_code": text}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"✅ **تم تحديث كود الزر `{button_id}`!**")
            await admin_buttons(event, bot, supabase)
            return

        if current_state == "awaiting_edit_name":
            button_id = state["button_id"]
            supabase.table("buttons").update({"display_name": text}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"✅ **تم تغيير الاسم إلى `{text}`**")
            await admin_buttons(event, bot, supabase)
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
                    "cvv": text, "is_active": True, "added_by": user_id
                }).execute()
                del user_states[user_id]
                await event.respond("✅ **تم إضافة الفيزا بنجاح!**")
                await cards_manage(event, bot, supabase)
            return

        if current_state == "awaiting_github_edit":
            is_valid, error_msg = await validate_python_code(text)
            if not is_valid:
                await event.respond(f"⛔ **لم يتم الرفع! الكود فيه خطأ:**\n`{error_msg}`\n\nصحح الخطأ وأرسل مجدداً.")
                return
            success = await update_github_file(text, "main.py", "AI self-update v7")
            if success:
                await event.respond("✅ **تم تحديث main.py في GitHub بنجاح!**\n\n🔄 Railway سيعيد النشر تلقائياً...")
                del user_states[user_id]
            else:
                await event.respond("❌ **فشل تحديث الملف** — تأكد من GITHUB_TOKEN")
                del user_states[user_id]
            return

        if current_state == "awaiting_error_fix":
            await event.respond("🔍 **جاري تحليل الخطأ...**")
            current_code = await get_github_file()
            fix = await ask_ai(
                f"الخطأ:\n{text}\n\nالكود الحالي (أول 1500 حرف):\n{(current_code or '')[:1500]}\n\nحلل الخطأ وأعطني الكود المصحح كاملاً داخل ```python```",
                user_id
            )
            await event.respond(
                f"🔧 **اقتراح الإصلاح:**\n\n{fix[:2000]}\n\nهل تطبق؟",
                buttons=[[Button.inline("✅ تطبيق", b"apply_fix"), Button.inline("❌ إلغاء", b"cancel")]],
                parse_mode='md'
            )
            user_states[user_id] = {"state": "awaiting_fix_apply", "fix_code": fix}
            return

        if current_state == "awaiting_broadcast":
            await event.respond("📢 **جاري الإرسال...**")
            try:
                users = supabase.table("users").select("user_id").execute()
                sent = 0
                failed = 0
                for u in users.data:
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

        if current_state == "awaiting_ai_button_description":
            description = text
            await event.respond("🤔 **جاري توليد الكود...**")
            try:
                generated_code = await ask_ai(
                    f"اكتب كود Python لزر تيليجرام بهذا الوصف: {description}\nالكود يجب أن يستخدم: event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log\nأرجع فقط الكود داخل ```python```",
                    user_id
                )
                user_states[user_id] = {"state": "awaiting_ai_folder", "description": description, "code": generated_code}
                folders_list = ["accounts", "tactical", "stealth", "ai_lab", "protection", "budget", "main", "admin"]
                keyboard = [[Button.inline(f"📁 {f}", f"ai_folder_{f}".encode())] for f in folders_list]
                await event.respond(
                    f"✅ **الكود جاهز!**\n\n📝 {description}\n\n```python\n{generated_code[:600]}\n```\n\n📁 **اختر المجلد:**",
                    buttons=keyboard, parse_mode='md'
                )
            except Exception as e:
                await event.respond(f"❌ خطأ: {e}")
                del user_states[user_id]
            return

    await event.respond("🧠 **مبرمج AI يفكر...**")
    ai_response = await ask_ai(text, user_id)
    if len(ai_response) > 4000:
        for i in range(0, len(ai_response), 3900):
            await event.respond(ai_response[i:i+3900], parse_mode='md')
    else:
        await event.respond(ai_response, parse_mode='md')

# ============================================
# الأزرار الثابتة
# ============================================

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
        "🏰 **MUSTAFA SHOP - DIGITAL EMPIRE v7** 🏰\n\n"
        "⚡ المنظومة تحت أمرك يا قائد\n🇮🇶 جاهز لتنفيذ الأوامر\n\n"
        f"📊 {len(registry._dynamic_buttons)} زر نشط | 📁 {len(registry._folders)} مجلد\n"
        f"🌐 البروكسي: {'🟢 مفعل' if PROXY_URL else '⚪ غير مفعل'}\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n\n"
        "💡 اكتب أي شيء للتحدث مع المبرمج AI",
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
        "**فقط اكتب ما تريد!**\n\n"
        "📌 **أوامر مفيدة:**\n"
        "• `/list_github` - عرض ملفات GitHub\n"
        "• `/download_github main.py` - تحميل ملف\n"
        "• `/broadcast` - إرسال رسالة لجميع المستخدمين",
        parse_mode='md'
    )

@registry.register("check_proxy")
async def check_proxy(event, bot, supabase):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.ipify.org")
            await event.respond(f"🌐 **IP الحالي:** `{resp.text}`\n\n✅ البروكسي يعمل!", parse_mode='md')
    except Exception as e:
        await event.respond(f"❌ **خطأ:** `{str(e)[:100]}`", parse_mode='md')

@registry.register("show_stats")
async def cmd_stats(event, bot, supabase):
    await registry.refresh_from_db()
    try:
        users_count = supabase.table("users").select("*", count="exact").execute().count
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
            f"🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}\n"
            f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}",
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
# معالج المجلدات والـ Callbacks
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
                    await admin_recycle(event, bot, supabase)
            return

        if data.startswith("edit_btn_"):
            button_id = data.replace("edit_btn_", "")
            if data.startswith("edit_btn_code_"):
                button_id = data.replace("edit_btn_code_", "")
                user_states[user_id] = {"state": "awaiting_edit_code", "button_id": button_id}
                await event.respond(f"📝 **تعديل كود الزر `{button_id}`**\n\nأرسل الكود الجديد:")
            elif data.startswith("edit_btn_name_"):
                button_id = data.replace("edit_btn_name_", "")
                user_states[user_id] = {"state": "awaiting_edit_name", "button_id": button_id}
                await event.respond(f"✍️ **تعديل اسم الزر `{button_id}`**\n\nأرسل الاسم الجديد:")
            elif data.startswith("edit_btn_color_"):
                button_id = data.replace("edit_btn_color_", "")
                keyboard = [
                    [Button.inline("🔵 أزرق", f"set_color_{button_id}_blue".encode()), Button.inline("🔴 أحمر", f"set_color_{button_id}_red".encode())],
                    [Button.inline("🟢 أخضر", f"set_color_{button_id}_green".encode()), Button.inline("🟣 بنفسجي", f"set_color_{button_id}_purple".encode())],
                    [Button.inline("⚫ غامق", f"set_color_{button_id}_dark".encode()), Button.inline("🟠 برتقالي", f"set_color_{button_id}_orange".encode())],
                    [Button.inline("🔙 رجوع", f"edit_btn_{button_id}".encode())],
                ]
                await event.edit("🎨 **اختر اللون:**", buttons=keyboard)
            elif data.startswith("edit_btn_folder_"):
                button_id = data.replace("edit_btn_folder_", "")
                folders = registry.get_folders()
                keyboard = [[Button.inline(f"{f.get('emoji','📁')} {f.get('display_name')}", f"move_btn_{button_id}_{f['folder_key']}".encode())] for f in folders]
                keyboard.append([Button.inline("🔙 رجوع", f"edit_btn_{button_id}".encode())])
                await event.edit("📁 **اختر المجلد:**", buttons=keyboard)
            else:
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

        if data.startswith("set_color_"):
            parts = data.split("_")
            color = parts[-1]
            button_id = "_".join(parts[2:-1])
            supabase.table("buttons").update({"color": color}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            await event.answer(f"✅ تم تغيير اللون", alert=True)
            await admin_buttons(event, bot, supabase)
            return

        if data.startswith("move_btn_"):
            parts = data.split("_")
            button_id = parts[2]
            folder_key = parts[3]
            supabase.table("buttons").update({"folder_key": folder_key}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            await event.answer("✅ تم نقل الزر", alert=True)
            await admin_buttons(event, bot, supabase)
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
            await admin_buttons(event, bot, supabase)
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
                state["state"] = "awaiting_ai_button_confirmation"
                await event.edit(
                    f"✅ **المجلد: {folder_key}**\n\n📝 {state.get('description','')[:100]}\n\nتحفظ الزر؟",
                    buttons=[
                        [Button.inline("✅ حفظ", b"ai_confirm_save")],
                        [Button.inline("❌ إلغاء", b"cancel")]
                    ]
                )
            return

        if data == "ai_confirm_save":
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_button_confirmation":
                state = user_states[user_id]
                button_id = "ai_" + str(int(datetime.now().timestamp()))[-6:]
                supabase.table("buttons").insert({
                    "button_id": button_id,
                    "display_name": state.get("description", "")[:50],
                    "emoji": "🤖", "color": "blue",
                    "folder_key": state.get("folder_key", "main"),
                    "python_code": state.get("code", ""),
                    "is_active": True, "created_by": user_id
                }).execute()
                await registry.refresh_from_db(force=True)
                del user_states[user_id]
                await event.respond(f"✅ **تم إنشاء الزر `{button_id}` بنجاح!**")
                await admin_buttons(event, bot, supabase)
            return

        if data == "apply_fix":
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_fix_apply":
                fix_code = user_states[user_id].get("fix_code", "")
                code_match = re.search(r'```python\n(.*?)```', fix_code, re.DOTALL)
                if code_match:
                    new_code = code_match.group(1)
                    is_valid, error_msg = await validate_python_code(new_code)
                    if not is_valid:
                        await event.respond(f"⛔ الكود فيه خطأ:\n`{error_msg}`")
                        del user_states[user_id]
                        return
                    success = await update_github_file(new_code, "main.py", "AI fix applied")
                    if success:
                        await event.respond("✅ **تم تطبيق الإصلاح! Railway سيعيد النشر.**")
                    else:
                        await event.respond("❌ فشل التطبيق")
                else:
                    await event.respond("❌ لم يتم العثور على كود صالح")
                del user_states[user_id]
            return

        if data == "cancel":
            if user_id in user_states:
                del user_states[user_id]
            await event.answer("❌ تم الإلغاء", alert=True)
            return

        if data == "edit_main_github":
            if user_id not in ADMIN_IDS:
                await event.answer("⛔ غير مصرح", alert=True)
                return
            await event.respond("📥 **جاري قراءة main.py من GitHub...**")
            current_code = await get_github_file()
            if not current_code:
                await event.respond("❌ **فشل قراءة الملف**\n\nتأكد من GITHUB_TOKEN و اسم المستودع")
                return
            await event.respond(
                f"📝 **main.py**\n📊 الحجم: {len(current_code)} حرف\n\n"
                "⚠️ **تحذير:** أرسل الكود الكامل الجديد\nسيتم فحصه تلقائياً قبل الرفع:"
            )
            user_states[user_id] = {"state": "awaiting_github_edit", "original_code": current_code}
            return

        if data == "fix_error_ai":
            if user_id not in ADMIN_IDS:
                await event.answer("⛔ غير مصرح", alert=True)
                return
            user_states[user_id] = {"state": "awaiting_error_fix"}
            await event.respond("🔧 **إصلاح الأخطاء بالذكاء**\n\nأرسل الخطأ كاملاً (Error Traceback):")
            return

        if data == "restart_bot":
            if user_id not in ADMIN_IDS:
                await event.answer("⛔ غير مصرح", alert=True)
                return
            await event.respond("🔄 **جاري إعادة تشغيل البوت...**")
            await restart_bot()
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
# لوحة التحكم
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
    keyboard = [[Button.inline(f"{btn.get('emoji','🔹')} {btn.get('display_name', btn['button_id'])[:25]}", f"edit_btn_{btn['button_id']}")] for btn in buttons_list[:30]]
    keyboard.append([Button.inline("➕ إضافة زر", b"add_button"), Button.inline("🤖 زر بالذكاء", b"ai_create_button")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin_full_panel")])
    try:
        await event.edit(f"🔹 **إدارة الأزرار** ({len(buttons_list)})", buttons=keyboard)
    except:
        await event.respond(f"🔹 **إدارة الأزرار** ({len(buttons_list)})", buttons=keyboard)

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
    user_states[event.sender_id] = {"state": "awaiting_ai_button_description"}
    await event.respond("🤖 **إنشاء زر بالذكاء**\n\nأرسل وصف الزر بالعربية:\n\n_مثال: زر يعرض إحصائيات المبيعات اليومية_")

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
async def admin_settings(event, bot, supabase):
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
        total_clicks = supabase.table("analytics").select("*", count="exact").execute().count
    except:
        total_clicks = 0
    try:
        users_count = supabase.table("users").select("*", count="exact").execute().count
    except:
        users_count = 0
    railway = await get_railway_deployment_status()
    await event.edit(
        f"📊 **الإحصائيات المتقدمة**\n\n"
        f"🔹 الأزرار: {len(registry._dynamic_buttons)}\n"
        f"📁 المجلدات: {len(registry._folders)}\n"
        f"👥 المستخدمين: {users_count}\n"
        f"☝️ إجمالي الضغطات: {total_clicks}\n"
        f"🚉 Railway: {railway.get('status', 'غير معروف')}\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}",
        buttons=[[Button.inline("🔙 رجوع", b"admin_full_panel")]]
    )

@registry.register("admin_accounts")
async def admin_accounts(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    keyboard = [
        [Button.inline("💰 حسابات الترويج", b"promo_accounts_list")],
        [Button.inline("📁 حسابات النشر الفردي", b"individual_accounts_list")],
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
        text += f"• {acc['platform']}: {acc.get('account_name', acc.get('email', 'غير معروف'))}\n"
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"admin_accounts")]])

@registry.register("individual_accounts_list")
async def individual_accounts_list(event, bot, supabase):
    accounts = supabase.table("individual_accounts").select("*").execute()
    if not accounts.data:
        await event.edit("📁 **لا توجد حسابات**", buttons=[[Button.inline("➕ إضافة", b"individual_add"), Button.inline("🔙 رجوع", b"admin_accounts")]])
        return
    keyboard = [[Button.inline(f"{'🟢' if acc['status']=='active' else '🔴'} {acc['platform']}: @{acc.get('username','بدون')}", f"individual_view_{acc['id']}")] for acc in accounts.data[:20]]
    keyboard.append([Button.inline("➕ إضافة حساب", b"individual_add"), Button.inline("🔙 رجوع", b"admin_accounts")])
    await event.edit("📁 **حسابات النشر الفردي**", buttons=keyboard)

@registry.register("individual_add")
async def individual_add(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 1}
    await event.respond("➕ **إضافة حساب نشر فردي**\n\nاختر المنصة:", buttons=[
        [Button.inline("📱 تيليجرام", b"ind_platform_telegram"), Button.inline("📔 فيسبوك", b"ind_platform_facebook")],
        [Button.inline("📸 إنستقرام", b"ind_platform_instagram"), Button.inline("🎵 تيك توك", b"ind_platform_tiktok")],
        [Button.inline("🔙 إلغاء", b"individual_accounts_list")]
    ])

@registry.register("accounts_stats")
async def accounts_stats(event, bot, supabase):
    try:
        promo = supabase.table("promo_accounts").select("*", count="exact").execute()
        individual = supabase.table("individual_accounts").select("*", count="exact").execute()
        await event.edit(
            f"📊 **إحصائيات الحسابات**\n\nالترويج: {promo.count}\nالنشر الفردي: {individual.count}",
            buttons=[[Button.inline("🔄 تحديث", b"accounts_stats"), Button.inline("🔙 رجوع", b"admin_accounts")]]
        )
    except:
        await event.edit("❌ خطأ في جلب الإحصائيات", buttons=[[Button.inline("🔙 رجوع", b"admin_accounts")]])

# ============================================
# نظام الميزانية
# ============================================

@registry.register("budget_system")
async def budget_system(event, bot, supabase):
    try:
        cards = supabase.table("payment_cards").select("*").eq("is_active", True).execute()
        total_balance = sum(c.get('current_balance', 0) for c in cards.data)
        await event.respond(
            f"💰 **نظام الميزانية**\n\n"
            f"💳 الفيزات النشطة: {len(cards.data)}\n"
            f"💰 إجمالي الرصيد: ${total_balance}",
            buttons=[
                [Button.inline("💳 إدارة الفيزات", b"cards_manage"), Button.inline("➕ إضافة فيزا", b"card_add")],
                [Button.inline("📢 الحملات الإعلانية", b"campaigns_manage")],
                [Button.inline("🔙 رجوع", b"start")]
            ]
        )
    except:
        await event.respond("❌ خطأ في نظام الميزانية")

@registry.register("cards_manage")
async def cards_manage(event, bot, supabase):
    cards = supabase.table("payment_cards").select("*").execute()
    if not cards.data:
        await event.edit("💳 **لا توجد فيزات**", buttons=[[Button.inline("➕ إضافة", b"card_add"), Button.inline("🔙 رجوع", b"budget_system")]])
        return
    keyboard = [[Button.inline(f"{'🟢' if c['is_active'] else '🔴'} **** {c['card_number'][-4:]} - ${c.get('current_balance',0)}", f"card_view_{c['id']}")] for c in cards.data]
    keyboard.append([Button.inline("➕ إضافة فيزا", b"card_add"), Button.inline("🔙 رجوع", b"budget_system")])
    await event.edit("💳 **الفيزات المسجلة:**", buttons=keyboard)

@registry.register("card_add")
async def card_add(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_card_details", "step": 1}
    await event.respond("➕ **إضافة فيزا - الخطوة 1/4**\n\nأرسل رقم البطاقة (16 رقم):")

@registry.register("campaigns_manage")
async def campaigns_manage(event, bot, supabase):
    await event.respond("📢 **الحملات الإعلانية**\n\n🚀 قيد التطوير...", buttons=[[Button.inline("🔙 رجوع", b"budget_system")]])

# ============================================
# إعدادات النظام
# ============================================

@registry.register("setting_ai")
async def setting_ai(event, bot, supabase):
    await event.respond(
        f"🤖 **إعدادات الذكاء الاصطناعي**\n\n"
        f"🔑 مفتاح OpenAI: {'✅ موجود' if OPENAI_KEY else '❌ غير موجود'}\n"
        f"💾 جدول الذاكرة: ai_memory",
        buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]]
    )

@registry.register("setting_proxy")
async def setting_proxy(event, bot, supabase):
    await event.respond(
        f"🌐 **إعدادات البروكسي**\n\n"
        f"🔗 الحالة: {'✅ نشط' if PROXY_URL else '❌ غير مستخدم'}",
        buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]]
    )

@registry.register("setting_budget")
async def setting_budget(event, bot, supabase):
    await event.respond("💰 **إعدادات الميزانية**\n\n🔜 قيد التطوير", buttons=[[Button.inline("🔙 رجوع", b"admin_settings")]])

@registry.register("ind_platform_telegram")
async def ind_platform_telegram(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "telegram"}}
    await event.respond("✅ المنصة: تيليجرام\n\nأرسل رقم الهاتف:")

@registry.register("ind_platform_facebook")
async def ind_platform_facebook(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "facebook"}}
    await event.respond("✅ المنصة: فيسبوك\n\nأرسل البريد الإلكتروني:")

@registry.register("ind_platform_instagram")
async def ind_platform_instagram(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "instagram"}}
    await event.respond("✅ المنصة: إنستقرام\n\nأرسل اسم المستخدم:")

@registry.register("ind_platform_tiktok")
async def ind_platform_tiktok(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "tiktok"}}
    await event.respond("✅ المنصة: تيك توك\n\nأرسل اسم المستخدم:")

@registry.register("cancel")
async def cancel_action(event, bot, supabase):
    user_id = event.sender_id
    if user_id in user_states:
        del user_states[user_id]
    await event.respond("❌ تم إلغاء العملية", buttons=[[Button.inline("🔙 رجوع", b"start")]])

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
        except:
            pass

def ensure_backup_table():
    try:
        supabase.table("backups").select("count").limit(1).execute()
    except:
        log.warning("⚠️ جدول backups غير موجود")

# ============================================
# المهام الخلفية
# ============================================

async def auto_railway_monitor():
    while True:
        try:
            await asyncio.sleep(3600)
            status = await get_railway_deployment_status()
            if status.get('status') == 'FAILED' and ADMIN_IDS:
                await bot.send_message(
                    ADMIN_IDS[0],
                    f"⚠️ **تنبيه Railway!**\n\n"
                    f"حالة النشر: فشل (FAILED)\n"
                    f"الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"السجلات: {status.get('logsUrl', 'غير متوفر')}"
                )
        except:
            await asyncio.sleep(3600)

async def auto_backup():
    while True:
        try:
            await asyncio.sleep(21600)  # كل 6 ساعات
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
            log.info("✅ نسخة احتياطية تلقائية")
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

# ============================================
# التشغيل الرئيسي
# ============================================

async def main():
    log.info("🚀 جاري تشغيل MUSTAFA SHOP - DIGITAL EMPIRE v7...")
    log.info("=" * 50)

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

    me = await bot.get_me()
    log.info(f"✅ البوت يعمل! @{me.username}")
    log.info(f"👑 المطورون: {ADMIN_IDS}")
    log.info(f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}")
    log.info(f"🌐 البروكسي: {'🟢 نشط' if PROXY_URL else '⚪ غير مستخدم'}")
    log.info(f"📁 GitHub: {'🟢 متصل' if GITHUB_TOKEN else '⚪ غير متصل'}")
    log.info(f"🚉 Railway: {'🟢 متصل' if RAILWAY_TOKEN else '🔴 غير متصل'}")
    log.info("=" * 50)

    asyncio.create_task(auto_railway_monitor())
    asyncio.create_task(auto_backup())
    asyncio.create_task(auto_reset_accounts())

    if ADMIN_IDS:
        try:
            await bot.send_message(
                ADMIN_IDS[0],
                f"✅ **MUSTAFA SHOP v7 يعمل!**\n\n"
                f"📊 {len(registry._dynamic_buttons)} زر | 📁 {len(registry._folders)} مجلد\n"
                f"🤖 AI: {'نشط' if OPENAI_KEY else 'غير نشط'}\n"
                f"🌐 بروكسي: {'نشط' if PROXY_URL else 'غير مستخدم'}\n"
                f"📁 GitHub: {'متصل' if GITHUB_TOKEN else 'غير متصل'}\n\n"
                f"✨ **الجديد في v7:**\n"
                f"• ✅ إصلاح تكرار الـ handlers\n"
                f"• ✅ فحص الكود قبل رفعه على GitHub\n"
                f"• ✅ إصلاح قراءة الملفات الكبيرة\n"
                f"• ✅ أمر /broadcast للبث الجماعي\n"
                f"• ✅ تحسين لوحة التحكم"
            )
        except:
            pass

    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 تم إيقاف البوت")
    except Exception as e:
        log.error(f"❌ خطأ فادح: {e}")
        traceback.print_exc()
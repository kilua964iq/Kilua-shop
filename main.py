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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
log = logging.getLogger(__name__)

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
# ØªÙØ¹ÙŠÙ„ Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ
# ============================================

if PROXY_URL and USE_PROXY_FOR_ALL:
    os.environ["HTTP_PROXY"] = PROXY_URL
    os.environ["HTTPS_PROXY"] = PROXY_URL
    os.environ["ALL_PROXY"] = PROXY_URL
    log.info("âœ… ØªÙ… ØªÙØ¹ÙŠÙ„ Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ Ø§Ù„ØªÙ„Ù‚Ø§Ø¦ÙŠ")

if not all([API_ID, API_HASH, BOT_TOKEN, SUPABASE_URL, SUPABASE_KEY]):
    log.error("âŒ Ù…ØªØºÙŠØ±Ø§Øª Ø§Ù„Ø¨ÙŠØ¦Ø© Ø§Ù„Ø£Ø³Ø§Ø³ÙŠØ© ØºÙŠØ± Ù…ÙƒØªÙ…Ù„Ø©!")
    exit(1)

if not ADMIN_IDS:
    log.warning("âš ï¸ Ù„Ù… ÙŠØªÙ… ØªØ¹ÙŠÙŠÙ† ADMIN_IDS")

# ============================================
# Ø¥Ø¹Ø¯Ø§Ø¯ Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ Ù„Ù„Ù€ Telethon
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
        log.info("âœ… ØªÙ… Ø¥Ø¹Ø¯Ø§Ø¯ Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ Ù„Ù„Ù€ Telethon")
    except:
        pass

# ============================================
# ØªÙ‡ÙŠØ¦Ø© Ø§Ù„Ø¹Ù…ÙŠÙ„
# ============================================

bot = TelegramClient("mustafa_empire_session", API_ID, API_HASH, proxy=proxy_config)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# Ø¯ÙˆØ§Ù„ GitHub - Ù…ÙØµÙ„Ø­Ø© Ù„Ù„Ù…Ù„ÙØ§Øª Ø§Ù„ÙƒØ¨ÙŠØ±Ø©
# ============================================

async def get_github_file(path: str = "main.py") -> Optional[str]:
    """Ø¬Ù„Ø¨ Ù…Ù„Ù Ù…Ù† GitHub - Ù…ÙØµÙ„Ø­ Ù„Ù„Ù…Ù„ÙØ§Øª Ø§Ù„ÙƒØ¨ÙŠØ±Ø©"""
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                # âœ… Ø§Ù„Ø¥ØµÙ„Ø§Ø­: Ø´ÙŠÙ„ Ø£Ø³Ø·Ø± base64 Ø§Ù„Ø²ÙŠØ§Ø¯Ø©
                if data.get("encoding") == "base64" and data.get("content"):
                    return base64.b64decode(data["content"].replace("\n", "")).decode('utf-8')
                # âœ… fallback Ù„Ù„Ù…Ù„ÙØ§Øª Ø§Ù„ÙƒØ¨ÙŠØ±Ø© Ø¬Ø¯Ø§Ù‹
                elif data.get("download_url"):
                    raw = await client.get(data["download_url"])
                    return raw.text
            log.error(f"GitHub get_file error: {resp.status_code}")
            return None
    except Exception as e:
        log.error(f"GitHub error: {e}")
        return None

async def update_github_file(content: str, path: str = "main.py", commit_msg: str = "AI self-update") -> bool:
    """ØªØ­Ø¯ÙŠØ« Ù…Ù„Ù ÙÙŠ GitHub"""
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
    """Ø¬Ù„Ø¨ Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ù…Ù„ÙØ§Øª Ù…Ù† GitHub"""
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
                            files.append(f"ðŸ“„ `{item['name']}` - {item['size']} bytes")
                        elif item['type'] == 'dir':
                            files.append(f"ðŸ“ `{item['name']}/`")
                    return "\n".join(files) if files else "ðŸ“‚ Ù„Ø§ ØªÙˆØ¬Ø¯ Ù…Ù„ÙØ§Øª"
                else:
                    return f"ðŸ“„ Ù…Ù„Ù ÙØ±Ø¯ÙŠ: `{data['name']}`"
            elif resp.status_code == 404:
                return f"âŒ Ø§Ù„Ù…Ø³ØªÙˆØ¯Ø¹ `{GITHUB_REPO}` ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ Ø£Ùˆ Ø®Ø§Øµ"
            else:
                return f"âŒ Ø®Ø·Ø£ HTTP {resp.status_code}"
    except Exception as e:
        return f"âŒ Ø®Ø·Ø£: {str(e)[:100]}"

async def download_github_file(path: str) -> Optional[bytes]:
    """ØªØ­Ù…ÙŠÙ„ Ù…Ù„Ù Ù…Ù† GitHub"""
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
    """âœ… Ø¬Ø¯ÙŠØ¯: ÙØ­Øµ ØµØ­Ø© ÙƒÙˆØ¯ Python Ù‚Ø¨Ù„ Ø§Ù„Ø±ÙØ¹"""
    try:
        ast.parse(code)
        return True, "âœ… Ø§Ù„ÙƒÙˆØ¯ ØµØ­ÙŠØ­"
    except SyntaxError as e:
        return False, f"âŒ Ø®Ø·Ø£ ÙÙŠ Ø§Ù„Ø³Ø·Ø± {e.lineno}: {e.msg}"

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
# Ø¯ÙˆØ§Ù„ Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ
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

    error_text = "Ù„Ø§ ØªÙˆØ¬Ø¯ Ø£Ø®Ø·Ø§Ø¡ Ø­Ø¯ÙŠØ«Ø©"
    try:
        errors = supabase.table("analytics").select("*").eq("success", False).order("created_at", desc=True).limit(5).execute()
        if errors.data:
            error_text = "\n".join([f"- {e.get('error_message','Ø®Ø·Ø£ ØºÙŠØ± Ù…Ø¹Ø±ÙˆÙ')[:100]}" for e in errors.data])
    except:
        pass

    github_files_text = await list_github_files()

    return f"""
=== Ø³ÙŠØ§Ù‚ Ù…Ù†Ø¸ÙˆÙ…Ø© MUSTAFA SHOP ===
Ø§Ù„Ø£Ø²Ø±Ø§Ø±: {buttons_count} | Ø§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª: {folders_count} | Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†: {users_count}
Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ: {'Ù…ÙØ¹Ù„' if PROXY_URL else 'ØºÙŠØ± Ù…ÙØ¹Ù„'} | AI: {'Ù…ÙØ¹Ù„' if OPENAI_KEY else 'ØºÙŠØ± Ù…ÙØ¹Ù„'}
GitHub: {'Ù…ØªØµÙ„' if GITHUB_TOKEN else 'ØºÙŠØ± Ù…ØªØµÙ„'} | Railway: {'Ù…ØªØµÙ„' if RAILWAY_TOKEN else 'ØºÙŠØ± Ù…ØªØµÙ„'}

Ø¢Ø®Ø± Ø§Ù„Ø£Ø®Ø·Ø§Ø¡:
{error_text}

Ù…Ù„ÙØ§Øª GitHub ÙÙŠ {GITHUB_REPO}:
{github_files_text}

Ø£Ù†Øª Ù…Ø¨Ø±Ù…Ø¬ AI Ù…ØªØ®ØµØµ ÙÙŠ Python Ùˆ Telethon Ùˆ Supabase Ùˆ GitHub Ùˆ Railway.
"""

async def ask_ai(prompt: str, user_id: int = None, conversation_history: list = None) -> str:
    if not OPENAI_KEY:
        return "ðŸ”´ Ù…ÙØªØ§Ø­ OpenAI ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯."

    context = await get_system_context(user_id) if user_id else ""

    if user_id:
        memory = await get_ai_memory(user_id, 10)
        memory_text = "\n".join([f"Ù…Ø³ØªØ®Ø¯Ù…: {m['user_message']}\nAI: {m['ai_response']}" for m in memory])
        if memory_text:
            context += f"\n\n=== ØªØ§Ø±ÙŠØ® Ø§Ù„Ù…Ø­Ø§Ø¯Ø«Ø© ===\n{memory_text}"

    system_prompt = f"""Ø£Ù†Øª Ù…Ø¨Ø±Ù…Ø¬ AI Ø§Ù„Ø¹Ø¨Ù‚Ø±ÙŠ Ø¯Ø§Ø®Ù„ Ø¨ÙˆØª MUSTAFA SHOP.

{context}

Ù‚ÙˆØ§Ø¹Ø¯:
1. ØªØ­Ø¯Ø« Ø¨Ø°ÙƒØ§Ø¡ ÙˆØ§Ø­ØªØ±Ø§ÙÙŠØ©
2. Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù… Ù‡Ùˆ Ø§Ù„Ù…Ø·ÙˆØ± Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠ (Admin)
3. Ø§Ø³ØªØ®Ø¯Ù… Ø§Ù„Ø¹Ø§Ù…ÙŠØ© Ø¥Ø°Ø§ ØªØ­Ø¯Ø« Ø¨Ù‡Ø§ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…
4. Ø¥Ø°Ø§ Ù„Ù… ØªØ¹Ø±Ù Ø´ÙŠØ¦Ø§Ù‹ Ù‚Ù„ Ø°Ù„Ùƒ
5. Ø¹Ù†Ø¯ ÙƒØªØ§Ø¨Ø© ÙƒÙˆØ¯ Python Ø§Ø¬Ø¹Ù„Ù‡ Ø¯Ø§Ø®Ù„ ```python ... ```

Ø§Ù„Ø¢Ù† Ø±Ø¯ Ø¹Ù„Ù‰ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…."""

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
            return f"ðŸ”´ Ø®Ø·Ø£ OpenAI: {resp.status_code}"
    except Exception as e:
        return f"ðŸ”´ Ø®Ø·Ø£: {str(e)[:100]}"

# ============================================
# Ù†Ø¸Ø§Ù… ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø£Ø²Ø±Ø§Ø±
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
            log.info(f"âœ… ØªÙ… ØªØ­Ø¯ÙŠØ« {len(self._dynamic_buttons)} Ø²Ø± Ùˆ {len(self._folders)} Ù…Ø¬Ù„Ø¯")
        except Exception as e:
            log.error(f"Ø®Ø·Ø£ ÙÙŠ ØªØ­Ø¯ÙŠØ« Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª: {e}")

    async def execute(self, button_id: str, event, **kwargs):
        await self.refresh_from_db()
        if button_id in self._static_handlers:
            try:
                await self._static_handlers[button_id](event, bot, supabase, **kwargs)
                return True
            except Exception as e:
                await event.answer(f"âŒ Ø®Ø·Ø£: {str(e)[:100]}", alert=True)
                return True
        if button_id in self._dynamic_buttons:
            button = self._dynamic_buttons[button_id]
            code = button.get("python_code", "")
            if not code:
                await event.answer("âš ï¸ Ù‡Ø°Ø§ Ø§Ù„Ø²Ø± Ù„ÙŠØ³ Ù„Ù‡ ÙƒÙˆØ¯ Ø¨Ø¹Ø¯", alert=True)
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
                await event.respond(f"âŒ **Ø®Ø·Ø£ ÙÙŠ Ø§Ù„Ø²Ø±:**\n`{str(e)[:200]}`")
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
# Ø¥Ù†Ø´Ø§Ø¡ Ø¬Ø¯ÙˆÙ„ Ø§Ù„Ø°Ø§ÙƒØ±Ø©
# ============================================

async def create_ai_memory_table():
    try:
        supabase.table("ai_memory").select("count").limit(1).execute()
    except:
        log.warning("âš ï¸ Ø¬Ø¯ÙˆÙ„ ai_memory ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯ØŒ ÙŠØ±Ø¬Ù‰ Ø¥Ù†Ø´Ø§Ø¤Ù‡ ÙŠØ¯ÙˆÙŠØ§Ù‹ ÙÙŠ Supabase")

# ============================================
# âœ… Ù…Ø¹Ø§Ù„Ø¬ Ø±Ø³Ø§Ø¦Ù„ Ù…ÙˆØ­Ø¯ (Ø¥ØµÙ„Ø§Ø­ Ø§Ù„ØªÙƒØ±Ø§Ø±)
# ============================================

@bot.on(events.NewMessage)
async def unified_message_handler(event):
    if event.out or not event.raw_text:
        return

    user_id = event.sender_id
    text = event.raw_text.strip()

    # --- Ø£ÙˆØ§Ù…Ø± GitHub ---
    if text.startswith('/download_github'):
        parts = text.split()
        if len(parts) != 2:
            await event.respond("âŒ Ø§Ø³ØªØ®Ø¯Ù…: `/download_github Ø§Ø³Ù…_Ø§Ù„Ù…Ù„Ù`", parse_mode='md')
            return
        file_path = parts[1]
        await event.respond(f"ðŸ“¥ **Ø¬Ø§Ø±ÙŠ ØªØ­Ù…ÙŠÙ„ {file_path}...**")
        file_content = await download_github_file(file_path)
        if file_content:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file_path}") as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name
            await event.respond(f"âœ… **ØªÙ… ØªØ­Ù…ÙŠÙ„ {file_path}**", file=tmp_path)
            os.unlink(tmp_path)
        else:
            await event.respond(f"âŒ **ÙØ´Ù„ ØªØ­Ù…ÙŠÙ„ {file_path}**")
        return

    if text.startswith('/list_github'):
        await event.respond("ðŸ“‚ **Ø¬Ø§Ø±ÙŠ Ø¬Ù„Ø¨ Ø§Ù„Ù…Ù„ÙØ§Øª...**")
        files_list = await list_github_files()
        await event.respond(f"ðŸ“ **Ù…Ù„ÙØ§Øª GitHub:**\n\n{files_list}", parse_mode='md')
        return

    # --- Ø£ÙˆØ§Ù…Ø± Ø¹Ø§Ù…Ø© ---
    if text.startswith('/'):
        if text.startswith('/start'):
            await cmd_start(event, bot, supabase)
            return
        elif text == '/restart' and user_id in ADMIN_IDS:
            await event.respond("ðŸ”„ Ø¬Ø§Ø±ÙŠ Ø¥Ø¹Ø§Ø¯Ø© ØªØ´ØºÙŠÙ„ Ø§Ù„Ø¨ÙˆØª...")
            await restart_bot()
            return
        elif text == '/stats' and user_id in ADMIN_IDS:
            await cmd_stats(event, bot, supabase)
            return
        elif text == '/github_repo' and user_id in ADMIN_IDS:
            await event.respond(f"ðŸ“ **Ø§Ù„Ù…Ø³ØªÙˆØ¯Ø¹:** `{GITHUB_REPO}`\nðŸŒ¿ **Ø§Ù„ÙØ±Ø¹:** `{GITHUB_BRANCH}`")
            return
        elif text == '/broadcast' and user_id in ADMIN_IDS:
            user_states[user_id] = {"state": "awaiting_broadcast"}
            await event.respond("ðŸ“¢ **Ø¨Ø« Ø¬Ù…Ø§Ø¹ÙŠ**\n\nØ£Ø±Ø³Ù„ Ø§Ù„Ø±Ø³Ø§Ù„Ø© Ø§Ù„ØªÙŠ ØªØ±ÙŠØ¯ Ø¥Ø±Ø³Ø§Ù„Ù‡Ø§ Ù„Ø¬Ù…ÙŠØ¹ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†:")
            return
        else:
            return

    # --- Ù…Ø¹Ø§Ù„Ø¬Ø© Ø­Ø§Ù„Ø§Øª Ø§Ù„Ø£Ø¯Ù…Ù† ---
    if user_id in ADMIN_IDS and user_id in user_states:
        state = user_states[user_id]
        current_state = state.get("state")

        # Ø¥Ø¶Ø§ÙØ© Ø²Ø± Ø¬Ø¯ÙŠØ¯
        if current_state == "awaiting_button_data":
            step = state.get("step", 1)
            data = state.get("data", {})
            if step == 1:
                data["button_id"] = text
                state["step"] = 2
                await event.respond("âœ… Ø§Ù„Ø®Ø·ÙˆØ© 2/6: Ø£Ø±Ø³Ù„ Ø§Ù„Ø§Ø³Ù… Ø§Ù„Ø¸Ø§Ù‡Ø±:")
            elif step == 2:
                data["display_name"] = text
                state["step"] = 3
                await event.respond("âœ… Ø§Ù„Ø®Ø·ÙˆØ© 3/6: Ø£Ø±Ø³Ù„ Ø§Ù„Ø¥ÙŠÙ…ÙˆØ¬ÙŠ:")
            elif step == 3:
                data["emoji"] = text if text else "ðŸ”˜"
                state["step"] = 4
                await event.respond("âœ… Ø§Ù„Ø®Ø·ÙˆØ© 4/6: Ø§Ø®ØªØ± Ø§Ù„Ù„ÙˆÙ†:\n`blue` `red` `green` `purple` `dark` `orange`")
            elif step == 4:
                colors = ["blue", "red", "green", "purple", "dark", "orange"]
                data["color"] = text if text in colors else "blue"
                state["step"] = 5
                await event.respond("âœ… Ø§Ù„Ø®Ø·ÙˆØ© 5/6: Ø£Ø±Ø³Ù„ Ø§Ù„Ù…Ø¬Ù„Ø¯ (main, accounts, admin ...):")
            elif step == 5:
                data["folder_key"] = text
                state["step"] = 6
                await event.respond("âœ… Ø§Ù„Ø®Ø·ÙˆØ© 6/6: Ø£Ø±Ø³Ù„ ÙƒÙˆØ¯ Python Ù„Ù„Ø²Ø± (Ø£Ùˆ Ø£Ø±Ø³Ù„ 'skip' Ù„ØªØ±ÙƒÙ‡ ÙØ§Ø±ØºØ§Ù‹):")
            elif step == 6:
                data["python_code"] = "" if text.lower() == "skip" else text
                supabase.table("buttons").insert({
                    "button_id": data["button_id"],
                    "display_name": data["display_name"],
                    "emoji": data.get("emoji", "ðŸ”˜"),
                    "color": data.get("color", "blue"),
                    "folder_key": data["folder_key"],
                    "python_code": data["python_code"],
                    "is_active": True,
                    "created_by": user_id
                }).execute()
                await registry.refresh_from_db(force=True)
                del user_states[user_id]
                await event.respond(f"âœ… **ØªÙ… Ø¥Ø¶Ø§ÙØ© Ø§Ù„Ø²Ø± `{data['button_id']}` Ø¨Ù†Ø¬Ø§Ø­!**")
                await admin_buttons(event, bot, supabase)
            return

        # ØªØ¹Ø¯ÙŠÙ„ ÙƒÙˆØ¯ Ø§Ù„Ø²Ø±
        if current_state == "awaiting_edit_code":
            button_id = state["button_id"]
            supabase.table("buttons").update({"python_code": text}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"âœ… **ØªÙ… ØªØ­Ø¯ÙŠØ« ÙƒÙˆØ¯ Ø§Ù„Ø²Ø± `{button_id}`!**")
            await admin_buttons(event, bot, supabase)
            return

        # ØªØ¹Ø¯ÙŠÙ„ Ø§Ø³Ù… Ø§Ù„Ø²Ø±
        if current_state == "awaiting_edit_name":
            button_id = state["button_id"]
            supabase.table("buttons").update({"display_name": text}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"âœ… **ØªÙ… ØªØºÙŠÙŠØ± Ø§Ù„Ø§Ø³Ù… Ø¥Ù„Ù‰ `{text}`**")
            await admin_buttons(event, bot, supabase)
            return

        # Ø¥Ø¶Ø§ÙØ© Ù…Ø¬Ù„Ø¯
        if current_state == "awaiting_folder_key":
            folder_key = text.replace(" ", "_").lower()
            supabase.table("folders").insert({
                "folder_key": folder_key,
                "display_name": folder_key.replace("_", " ").title(),
                "emoji": "ðŸ“", "color": "blue", "sort_order": 999,
                "is_active": True, "created_by": user_id
            }).execute()
            await registry.refresh_from_db(force=True)
            del user_states[user_id]
            await event.respond(f"âœ… ØªÙ… Ø¥Ø¶Ø§ÙØ© Ø§Ù„Ù…Ø¬Ù„Ø¯ `{folder_key}`")
            await admin_folders(event, bot, supabase)
            return

        # Ø¥Ø¶Ø§ÙØ© ÙÙŠØ²Ø§
        if current_state == "awaiting_card_details":
            step = state.get("step", 1)
            if step == 1:
                if len(text) not in [15, 16]:
                    await event.respond("âŒ Ø±Ù‚Ù… Ø§Ù„Ø¨Ø·Ø§Ù‚Ø© ØºÙŠØ± ØµØ§Ù„Ø­")
                    return
                user_states[user_id]["card_number"] = text
                user_states[user_id]["step"] = 2
                await event.respond("Ø§Ù„Ø®Ø·ÙˆØ© 2/4: Ø£Ø±Ø³Ù„ Ø§Ø³Ù… Ø­Ø§Ù…Ù„ Ø§Ù„Ø¨Ø·Ø§Ù‚Ø©:")
            elif step == 2:
                user_states[user_id]["card_holder"] = text
                user_states[user_id]["step"] = 3
                await event.respond("Ø§Ù„Ø®Ø·ÙˆØ© 3/4: Ø£Ø±Ø³Ù„ ØªØ§Ø±ÙŠØ® Ø§Ù„ØµÙ„Ø§Ø­ÙŠØ© (MM/YY):")
            elif step == 3:
                user_states[user_id]["expiry"] = text
                user_states[user_id]["step"] = 4
                await event.respond("Ø§Ù„Ø®Ø·ÙˆØ© 4/4: Ø£Ø±Ø³Ù„ CVV:")
            elif step == 4:
                supabase.table("payment_cards").insert({
                    "card_number": user_states[user_id]["card_number"],
                    "card_holder": user_states[user_id]["card_holder"],
                    "expiry_date": user_states[user_id]["expiry"],
                    "cvv": text, "is_active": True, "added_by": user_id
                }).execute()
                del user_states[user_id]
                await event.respond("âœ… **ØªÙ… Ø¥Ø¶Ø§ÙØ© Ø§Ù„ÙÙŠØ²Ø§ Ø¨Ù†Ø¬Ø§Ø­!**")
                await cards_manage(event, bot, supabase)
            return

        # âœ… ØªØ¹Ø¯ÙŠÙ„ GitHub Ù…Ø¹ ÙØ­Øµ Ø§Ù„ÙƒÙˆØ¯
        if current_state == "awaiting_github_edit":
            is_valid, error_msg = await validate_python_code(text)
            if not is_valid:
                await event.respond(f"â›” **Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø±ÙØ¹! Ø§Ù„ÙƒÙˆØ¯ ÙÙŠÙ‡ Ø®Ø·Ø£:**\n`{error_msg}`\n\nØµØ­Ø­ Ø§Ù„Ø®Ø·Ø£ ÙˆØ£Ø±Ø³Ù„ Ù…Ø¬Ø¯Ø¯Ø§Ù‹.")
                return
            success = await update_github_file(text, "main.py", "AI self-update v7")
            if success:
                await event.respond("âœ… **ØªÙ… ØªØ­Ø¯ÙŠØ« main.py ÙÙŠ GitHub Ø¨Ù†Ø¬Ø§Ø­!**\n\nðŸ”„ Railway Ø³ÙŠØ¹ÙŠØ¯ Ø§Ù„Ù†Ø´Ø± ØªÙ„Ù‚Ø§Ø¦ÙŠØ§Ù‹...")
                del user_states[user_id]
            else:
                await event.respond("âŒ **ÙØ´Ù„ ØªØ­Ø¯ÙŠØ« Ø§Ù„Ù…Ù„Ù** â€” ØªØ£ÙƒØ¯ Ù…Ù† GITHUB_TOKEN")
                del user_states[user_id]
            return

        # Ø¥ØµÙ„Ø§Ø­ Ø§Ù„Ø®Ø·Ø£ Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡
        if current_state == "awaiting_error_fix":
            await event.respond("ðŸ” **Ø¬Ø§Ø±ÙŠ ØªØ­Ù„ÙŠÙ„ Ø§Ù„Ø®Ø·Ø£...**")
            current_code = await get_github_file()
            fix = await ask_ai(
                f"Ø§Ù„Ø®Ø·Ø£:\n{text}\n\nØ§Ù„ÙƒÙˆØ¯ Ø§Ù„Ø­Ø§Ù„ÙŠ (Ø£ÙˆÙ„ 1500 Ø­Ø±Ù):\n{(current_code or '')[:1500]}\n\nØ­Ù„Ù„ Ø§Ù„Ø®Ø·Ø£ ÙˆØ£Ø¹Ø·Ù†ÙŠ Ø§Ù„ÙƒÙˆØ¯ Ø§Ù„Ù…ØµØ­Ø­ ÙƒØ§Ù…Ù„Ø§Ù‹ Ø¯Ø§Ø®Ù„ ```python```",
                user_id
            )
            await event.respond(
                f"ðŸ”§ **Ø§Ù‚ØªØ±Ø§Ø­ Ø§Ù„Ø¥ØµÙ„Ø§Ø­:**\n\n{fix[:2000]}\n\nÙ‡Ù„ ØªØ·Ø¨Ù‚ØŸ",
                buttons=[[Button.inline("âœ… ØªØ·Ø¨ÙŠÙ‚", b"apply_fix"), Button.inline("âŒ Ø¥Ù„ØºØ§Ø¡", b"cancel")]],
                parse_mode='md'
            )
            user_states[user_id] = {"state": "awaiting_fix_apply", "fix_code": fix}
            return

        # Ø¨Ø« Ø¬Ù…Ø§Ø¹ÙŠ
        if current_state == "awaiting_broadcast":
            await event.respond("ðŸ“¢ **Ø¬Ø§Ø±ÙŠ Ø§Ù„Ø¥Ø±Ø³Ø§Ù„...**")
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
                await event.respond(f"âœ… **ØªÙ… Ø§Ù„Ø¥Ø±Ø³Ø§Ù„!**\n\nðŸ“¤ Ù†Ø§Ø¬Ø­: {sent}\nâŒ ÙØ§Ø´Ù„: {failed}")
            except Exception as e:
                await event.respond(f"âŒ Ø®Ø·Ø£ ÙÙŠ Ø§Ù„Ø¨Ø«: {e}")
                del user_states[user_id]
            return

        # ÙˆØµÙ Ø²Ø± AI
        if current_state == "awaiting_ai_button_description":
            description = text
            await event.respond("ðŸ¤” **Ø¬Ø§Ø±ÙŠ ØªÙˆÙ„ÙŠØ¯ Ø§Ù„ÙƒÙˆØ¯...**")
            try:
                generated_code = await ask_ai(
                    f"Ø§ÙƒØªØ¨ ÙƒÙˆØ¯ Python Ù„Ø²Ø± ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù… Ø¨Ù‡Ø°Ø§ Ø§Ù„ÙˆØµÙ: {description}\nØ§Ù„ÙƒÙˆØ¯ ÙŠØ¬Ø¨ Ø£Ù† ÙŠØ³ØªØ®Ø¯Ù…: event, bot, supabase, Button, asyncio, datetime, random, json, httpx, log\nØ£Ø±Ø¬Ø¹ ÙÙ‚Ø· Ø§Ù„ÙƒÙˆØ¯ Ø¯Ø§Ø®Ù„ ```python```",
                    user_id
                )
                user_states[user_id] = {"state": "awaiting_ai_folder", "description": description, "code": generated_code}
                folders_list = ["accounts", "tactical", "stealth", "ai_lab", "protection", "budget", "main", "admin"]
                keyboard = [[Button.inline(f"ðŸ“ {f}", f"ai_folder_{f}".encode())] for f in folders_list]
                await event.respond(
                    f"âœ… **Ø§Ù„ÙƒÙˆØ¯ Ø¬Ø§Ù‡Ø²!**\n\nðŸ“ {description}\n\n```python\n{generated_code[:600]}\n```\n\nðŸ“ **Ø§Ø®ØªØ± Ø§Ù„Ù…Ø¬Ù„Ø¯:**",
                    buttons=keyboard, parse_mode='md'
                )
            except Exception as e:
                await event.respond(f"âŒ Ø®Ø·Ø£: {e}")
                del user_states[user_id]
            return

    # --- Ø§Ù„Ù…Ø¨Ø±Ù…Ø¬ AI Ù„Ù„Ø¬Ù…ÙŠØ¹ ---
    await event.respond("ðŸ§  **Ù…Ø¨Ø±Ù…Ø¬ AI ÙŠÙÙƒØ±...**")
    ai_response = await ask_ai(text, user_id)
    if len(ai_response) > 4000:
        for i in range(0, len(ai_response), 3900):
            await event.respond(ai_response[i:i+3900], parse_mode='md')
    else:
        await event.respond(ai_response, parse_mode='md')

# ============================================
# Ø§Ù„Ø£Ø²Ø±Ø§Ø± Ø§Ù„Ø«Ø§Ø¨ØªØ©
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
        [Button.inline("ðŸ­ Ù…ØµÙ†Ø¹ Ø§Ù„Ø¬ÙŠÙˆØ´", b"folder_accounts")],
        [Button.inline("ðŸš€ Ø§Ù„Ù‡Ø¬ÙˆÙ… Ø§Ù„ØªÙƒØªÙŠÙƒÙŠ", b"folder_tactical")],
        [Button.inline("ðŸ‘» Ø¹Ù…Ù„ÙŠØ§Øª Ø§Ù„ØªØ®ÙÙŠ", b"folder_stealth")],
        [Button.inline("ðŸ§  Ù…Ø®ØªØ¨Ø± Ø§Ù„Ø°ÙƒØ§Ø¡", b"folder_ai_lab")],
        [Button.inline("ðŸ›¡ï¸ Ø¯Ø±Ø¹ Ø§Ù„Ø­Ù…Ø§ÙŠØ©", b"folder_protection")],
        [Button.inline("ðŸ’° Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©", b"folder_budget")],
    ]
    if user_id in ADMIN_IDS:
        keyboard.append([Button.inline("âš™ï¸ Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…", b"admin_full_panel")])
    keyboard.append([Button.inline("ðŸ“Š Ø§Ù„Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª", b"show_stats"), Button.inline("ðŸŒ ÙØ­Øµ Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ", b"check_proxy")])
    keyboard.append([Button.inline("ðŸ“‚ Ù…Ù„ÙØ§Øª GitHub", b"list_github"), Button.inline("ðŸ§  Ù…Ø¨Ø±Ù…Ø¬ AI", b"ai_chat")])

    await event.respond(
        "ðŸ° **MUSTAFA SHOP - DIGITAL EMPIRE v7** ðŸ°\n\n"
        "âš¡ Ø§Ù„Ù…Ù†Ø¸ÙˆÙ…Ø© ØªØ­Øª Ø£Ù…Ø±Ùƒ ÙŠØ§ Ù‚Ø§Ø¦Ø¯\nðŸ‡®ðŸ‡¶ Ø¬Ø§Ù‡Ø² Ù„ØªÙ†ÙÙŠØ° Ø§Ù„Ø£ÙˆØ§Ù…Ø±\n\n"
        f"ðŸ“Š {len(registry._dynamic_buttons)} Ø²Ø± Ù†Ø´Ø· | ðŸ“ {len(registry._folders)} Ù…Ø¬Ù„Ø¯\n"
        f"ðŸŒ Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ: {'ðŸŸ¢ Ù…ÙØ¹Ù„' if PROXY_URL else 'âšª ØºÙŠØ± Ù…ÙØ¹Ù„'}\n"
        f"ðŸ¤– AI: {'ðŸŸ¢ Ù†Ø´Ø·' if OPENAI_KEY else 'ðŸ”´ ØºÙŠØ± Ù†Ø´Ø·'}\n\n"
        "ðŸ’¡ Ø§ÙƒØªØ¨ Ø£ÙŠ Ø´ÙŠØ¡ Ù„Ù„ØªØ­Ø¯Ø« Ù…Ø¹ Ø§Ù„Ù…Ø¨Ø±Ù…Ø¬ AI",
        buttons=keyboard, parse_mode='md'
    )

@registry.register("ai_chat")
async def ai_chat_button(event, bot, supabase):
    await event.respond(
        "ðŸ§  **Ù…Ø¨Ø±Ù…Ø¬ AI - Ø§Ù„Ø¹Ø¨Ù‚Ø±ÙŠ**\n\n"
        "Ø£Ù†Ø§ Ù‡Ù†Ø§ Ù„Ù…Ø³Ø§Ø¹Ø¯ØªÙƒ ÙÙŠ:\n"
        "â€¢ Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ø£Ø²Ø±Ø§Ø± ÙˆØ§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª\n"
        "â€¢ ÙƒØªØ§Ø¨Ø© ÙˆØªØ¹Ø¯ÙŠÙ„ Ø£ÙƒÙˆØ§Ø¯ Python\n"
        "â€¢ ØªØ­Ù„ÙŠÙ„ Ø§Ù„Ø£Ø®Ø·Ø§Ø¡ ÙˆØ¥ØµÙ„Ø§Ø­Ù‡Ø§\n"
        "â€¢ Ù…Ø±Ø§Ù‚Ø¨Ø© Ø§Ù„Ø§Ø³ØªØ¶Ø§ÙØ©\n"
        "â€¢ Ø¹Ø±Ø¶ ÙˆØªØ­Ù…ÙŠÙ„ Ù…Ù„ÙØ§Øª GitHub\n\n"
        "**ÙÙ‚Ø· Ø§ÙƒØªØ¨ Ù…Ø§ ØªØ±ÙŠØ¯!**\n\n"
        "ðŸ“Œ **Ø£ÙˆØ§Ù…Ø± Ù…ÙÙŠØ¯Ø©:**\n"
        "â€¢ `/list_github` - Ø¹Ø±Ø¶ Ù…Ù„ÙØ§Øª GitHub\n"
        "â€¢ `/download_github main.py` - ØªØ­Ù…ÙŠÙ„ Ù…Ù„Ù\n"
        "â€¢ `/broadcast` - Ø¥Ø±Ø³Ø§Ù„ Ø±Ø³Ø§Ù„Ø© Ù„Ø¬Ù…ÙŠØ¹ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†",
        parse_mode='md'
    )

@registry.register("check_proxy")
async def check_proxy(event, bot, supabase):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://api.ipify.org")
            await event.respond(f"ðŸŒ **IP Ø§Ù„Ø­Ø§Ù„ÙŠ:** `{resp.text}`\n\nâœ… Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ ÙŠØ¹Ù…Ù„!", parse_mode='md')
    except Exception as e:
        await event.respond(f"âŒ **Ø®Ø·Ø£:** `{str(e)[:100]}`", parse_mode='md')

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
            f"ðŸ“Š **Ø§Ù„Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª**\n\n"
            f"ðŸ”˜ Ø§Ù„Ø£Ø²Ø±Ø§Ø±: {len(registry._dynamic_buttons)}\n"
            f"ðŸ“ Ø§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª: {len(registry._folders)}\n"
            f"ðŸ‘¥ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†: {users_count}\n"
            f"ðŸš‚ Railway: {railway_status.get('status', 'ØºÙŠØ± Ù…Ø¹Ø±ÙˆÙ')}\n"
            f"ðŸŒ Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ: {'ðŸŸ¢ Ù†Ø´Ø·' if PROXY_URL else 'âšª ØºÙŠØ± Ù…Ø³ØªØ®Ø¯Ù…'}\n"
            f"ðŸ¤– AI: {'ðŸŸ¢ Ù†Ø´Ø·' if OPENAI_KEY else 'ðŸ”´ ØºÙŠØ± Ù†Ø´Ø·'}",
            buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"start")]]
        )
    except:
        await event.respond(
            f"ðŸ“Š Ø§Ù„Ø£Ø²Ø±Ø§Ø±: {len(registry._dynamic_buttons)} | Ø§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª: {len(registry._folders)} | Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†: {users_count}",
            buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"start")]]
        )

@registry.register("list_github")
async def list_github_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("â›” ØºÙŠØ± Ù…ØµØ±Ø­", alert=True)
        return
    await event.respond("ðŸ“‚ **Ø¬Ø§Ø±ÙŠ Ø¬Ù„Ø¨ Ø§Ù„Ù…Ù„ÙØ§Øª...**")
    files_list = await list_github_files()
    await event.respond(f"ðŸ“ **Ù…Ù„ÙØ§Øª GitHub ÙÙŠ {GITHUB_REPO}:**\n\n{files_list}", parse_mode='md')

# ============================================
# Ù…Ø¹Ø§Ù„Ø¬ Ø§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª ÙˆØ§Ù„Ù€ Callbacks
# ============================================

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    try:
        data = event.data.decode()
        user_id = event.sender_id

        # Ù…Ø¬Ù„Ø¯Ø§Øª
        if data.startswith("folder_"):
            folder_key = data.replace("folder_", "")
            await show_folder(event, folder_key)
            return

        # Ø§Ø³ØªØ±Ø¬Ø§Ø¹ Ù…Ø­Ø°ÙˆÙ
        if data.startswith("restore_"):
            item_id = int(data.replace("restore_", ""))
            deleted = supabase.table("deleted_items").select("*").eq("id", item_id).execute()
            if deleted.data:
                item = deleted.data[0]
                if item["item_type"] == "button":
                    supabase.table("buttons").insert(item["item_data"]).execute()
                    supabase.table("deleted_items").delete().eq("id", item_id).execute()
                    await event.answer("âœ… ØªÙ… Ø§Ù„Ø§Ø³ØªØ±Ø¬Ø§Ø¹", alert=True)
                    await admin_recycle(event, bot, supabase)
            return

        # ØªØ¹Ø¯ÙŠÙ„ Ø²Ø±
        if data.startswith("edit_btn_"):
            button_id = data.replace("edit_btn_", "")
            if data.startswith("edit_btn_code_"):
                button_id = data.replace("edit_btn_code_", "")
                user_states[user_id] = {"state": "awaiting_edit_code", "button_id": button_id}
                await event.respond(f"ðŸ“ **ØªØ¹Ø¯ÙŠÙ„ ÙƒÙˆØ¯ Ø§Ù„Ø²Ø± `{button_id}`**\n\nØ£Ø±Ø³Ù„ Ø§Ù„ÙƒÙˆØ¯ Ø§Ù„Ø¬Ø¯ÙŠØ¯:")
            elif data.startswith("edit_btn_name_"):
                button_id = data.replace("edit_btn_name_", "")
                user_states[user_id] = {"state": "awaiting_edit_name", "button_id": button_id}
                await event.respond(f"âœï¸ **ØªØ¹Ø¯ÙŠÙ„ Ø§Ø³Ù… Ø§Ù„Ø²Ø± `{button_id}`**\n\nØ£Ø±Ø³Ù„ Ø§Ù„Ø§Ø³Ù… Ø§Ù„Ø¬Ø¯ÙŠØ¯:")
            elif data.startswith("edit_btn_color_"):
                button_id = data.replace("edit_btn_color_", "")
                keyboard = [
                    [Button.inline("ðŸ”µ Ø£Ø²Ø±Ù‚", f"set_color_{button_id}_blue".encode()), Button.inline("ðŸ”´ Ø£Ø­Ù…Ø±", f"set_color_{button_id}_red".encode())],
                    [Button.inline("ðŸŸ¢ Ø£Ø®Ø¶Ø±", f"set_color_{button_id}_green".encode()), Button.inline("ðŸŸ£ Ø¨Ù†ÙØ³Ø¬ÙŠ", f"set_color_{button_id}_purple".encode())],
                    [Button.inline("âš« ØºØ§Ù…Ù‚", f"set_color_{button_id}_dark".encode()), Button.inline("ðŸŸ  Ø¨Ø±ØªÙ‚Ø§Ù„ÙŠ", f"set_color_{button_id}_orange".encode())],
                    [Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", f"edit_btn_{button_id}".encode())],
                ]
                await event.edit("ðŸŽ¨ **Ø§Ø®ØªØ± Ø§Ù„Ù„ÙˆÙ†:**", buttons=keyboard)
            elif data.startswith("edit_btn_folder_"):
                button_id = data.replace("edit_btn_folder_", "")
                folders = registry.get_folders()
                keyboard = [[Button.inline(f"{f.get('emoji','ðŸ“')} {f.get('display_name')}", f"move_btn_{button_id}_{f['folder_key']}".encode())] for f in folders]
                keyboard.append([Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", f"edit_btn_{button_id}".encode())])
                await event.edit("ðŸ“ **Ø§Ø®ØªØ± Ø§Ù„Ù…Ø¬Ù„Ø¯:**", buttons=keyboard)
            else:
                button = supabase.table("buttons").select("*").eq("button_id", button_id).execute()
                if button.data:
                    btn = button.data[0]
                    keyboard = [
                        [Button.inline("âœï¸ ØªØ¹Ø¯ÙŠÙ„ Ø§Ù„Ø§Ø³Ù…", f"edit_btn_name_{button_id}".encode())],
                        [Button.inline("ðŸ“ ØªØ¹Ø¯ÙŠÙ„ Ø§Ù„ÙƒÙˆØ¯", f"edit_btn_code_{button_id}".encode())],
                        [Button.inline("ðŸŽ¨ ØªØºÙŠÙŠØ± Ø§Ù„Ù„ÙˆÙ†", f"edit_btn_color_{button_id}".encode())],
                        [Button.inline("ðŸ“ Ù†Ù‚Ù„ Ù„Ù…Ø¬Ù„Ø¯", f"edit_btn_folder_{button_id}".encode())],
                        [Button.inline("ðŸ—‘ï¸ Ø­Ø°Ù Ø§Ù„Ø²Ø±", f"delete_btn_{button_id}".encode())],
                        [Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_buttons")],
                    ]
                    await event.edit(f"ðŸ”˜ **ØªØ¹Ø¯ÙŠÙ„: {btn.get('display_name', button_id)}**", buttons=keyboard)
            return

        # ØªØºÙŠÙŠØ± Ù„ÙˆÙ†
        if data.startswith("set_color_"):
            parts = data.split("_")
            color = parts[-1]
            button_id = "_".join(parts[2:-1])
            supabase.table("buttons").update({"color": color}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            await event.answer(f"âœ… ØªÙ… ØªØºÙŠÙŠØ± Ø§Ù„Ù„ÙˆÙ†", alert=True)
            await admin_buttons(event, bot, supabase)
            return

        # Ù†Ù‚Ù„ Ø²Ø±
        if data.startswith("move_btn_"):
            parts = data.split("_")
            button_id = parts[2]
            folder_key = parts[3]
            supabase.table("buttons").update({"folder_key": folder_key}).eq("button_id", button_id).execute()
            await registry.refresh_from_db(force=True)
            await event.answer("âœ… ØªÙ… Ù†Ù‚Ù„ Ø§Ù„Ø²Ø±", alert=True)
            await admin_buttons(event, bot, supabase)
            return

        # Ø­Ø°Ù Ø²Ø±
        if data.startswith("delete_btn_"):
            button_id = data.replace("delete_btn_", "")
            await event.edit(
                f"âš ï¸ **ØªØ£ÙƒÙŠØ¯ Ø­Ø°Ù Ø§Ù„Ø²Ø± `{button_id}`**",
                buttons=[
                    [Button.inline("âœ… Ù†Ø¹Ù…ØŒ Ø§Ø­Ø°Ù", f"confirm_delete_{button_id}".encode())],
                    [Button.inline("âŒ Ø¥Ù„ØºØ§Ø¡", b"admin_buttons")],
                ]
            )
            return

        if data.startswith("confirm_delete_"):
            button_id = data.replace("confirm_delete_", "")
            await registry.delete_button(button_id, user_id)
            await event.answer("âœ… ØªÙ… Ø§Ù„Ø­Ø°Ù", alert=True)
            await admin_buttons(event, bot, supabase)
            return

        # Ø¥Ø¶Ø§ÙØ© Ø²Ø± ÙÙŠ Ù…Ø¬Ù„Ø¯
        if data.startswith("add_btn_in_"):
            folder_key = data.replace("add_btn_in_", "")
            user_states[user_id] = {"state": "awaiting_button_data", "step": 1, "data": {"folder_key": folder_key}}
            await event.respond("âž• **Ø¥Ø¶Ø§ÙØ© Ø²Ø± Ø¬Ø¯ÙŠØ¯**\n\nØ§Ù„Ø®Ø·ÙˆØ© 1/6: Ø£Ø±Ø³Ù„ Ø§Ù„Ù€ Button ID:")
            return

        # Ø§Ø®ØªÙŠØ§Ø± Ù…Ø¬Ù„Ø¯ Ù„Ù„Ø²Ø± AI
        if data.startswith("ai_folder_"):
            folder_key = data.replace("ai_folder_", "")
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_folder":
                state = user_states[user_id]
                state["folder_key"] = folder_key
                state["state"] = "awaiting_ai_button_confirmation"
                await event.edit(
                    f"âœ… **Ø§Ù„Ù…Ø¬Ù„Ø¯: {folder_key}**\n\nðŸ“ {state.get('description','')[:100]}\n\nØªØ­ÙØ¸ Ø§Ù„Ø²Ø±ØŸ",
                    buttons=[
                        [Button.inline("âœ… Ø­ÙØ¸", b"ai_confirm_save")],
                        [Button.inline("âŒ Ø¥Ù„ØºØ§Ø¡", b"cancel")]
                    ]
                )
            return

        # Ø­ÙØ¸ Ø²Ø± AI
        if data == "ai_confirm_save":
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_ai_button_confirmation":
                state = user_states[user_id]
                button_id = "ai_" + str(int(datetime.now().timestamp()))[-6:]
                supabase.table("buttons").insert({
                    "button_id": button_id,
                    "display_name": state.get("description", "")[:50],
                    "emoji": "ðŸ¤–", "color": "blue",
                    "folder_key": state.get("folder_key", "main"),
                    "python_code": state.get("code", ""),
                    "is_active": True, "created_by": user_id
                }).execute()
                await registry.refresh_from_db(force=True)
                del user_states[user_id]
                await event.respond(f"âœ… **ØªÙ… Ø¥Ù†Ø´Ø§Ø¡ Ø§Ù„Ø²Ø± `{button_id}` Ø¨Ù†Ø¬Ø§Ø­!**")
                await admin_buttons(event, bot, supabase)
            return

        # ØªØ·Ø¨ÙŠÙ‚ Ø¥ØµÙ„Ø§Ø­
        if data == "apply_fix":
            if user_id in user_states and user_states[user_id].get("state") == "awaiting_fix_apply":
                fix_code = user_states[user_id].get("fix_code", "")
                code_match = re.search(r'```python\n(.*?)```', fix_code, re.DOTALL)
                if code_match:
                    new_code = code_match.group(1)
                    is_valid, error_msg = await validate_python_code(new_code)
                    if not is_valid:
                        await event.respond(f"â›” Ø§Ù„ÙƒÙˆØ¯ ÙÙŠÙ‡ Ø®Ø·Ø£:\n`{error_msg}`")
                        del user_states[user_id]
                        return
                    success = await update_github_file(new_code, "main.py", "AI fix applied")
                    if success:
                        await event.respond("âœ… **ØªÙ… ØªØ·Ø¨ÙŠÙ‚ Ø§Ù„Ø¥ØµÙ„Ø§Ø­! Railway Ø³ÙŠØ¹ÙŠØ¯ Ø§Ù„Ù†Ø´Ø±.**")
                    else:
                        await event.respond("âŒ ÙØ´Ù„ Ø§Ù„ØªØ·Ø¨ÙŠÙ‚")
                else:
                    await event.respond("âŒ Ù„Ù… ÙŠØªÙ… Ø§Ù„Ø¹Ø«ÙˆØ± Ø¹Ù„Ù‰ ÙƒÙˆØ¯ ØµØ§Ù„Ø­")
                del user_states[user_id]
            return

        # Ø¥Ù„ØºØ§Ø¡
        if data == "cancel":
            if user_id in user_states:
                del user_states[user_id]
            await event.answer("âŒ ØªÙ… Ø§Ù„Ø¥Ù„ØºØ§Ø¡", alert=True)
            return

        # ØªØ¹Ø¯ÙŠÙ„ main.py
        if data == "edit_main_github":
            if user_id not in ADMIN_IDS:
                await event.answer("â›” ØºÙŠØ± Ù…ØµØ±Ø­", alert=True)
                return
            await event.respond("ðŸ“¥ **Ø¬Ø§Ø±ÙŠ Ù‚Ø±Ø§Ø¡Ø© main.py Ù…Ù† GitHub...**")
            current_code = await get_github_file()
            if not current_code:
                await event.respond("âŒ **ÙØ´Ù„ Ù‚Ø±Ø§Ø¡Ø© Ø§Ù„Ù…Ù„Ù**\n\nØªØ£ÙƒØ¯ Ù…Ù† GITHUB_TOKEN Ùˆ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªÙˆØ¯Ø¹")
                return
            await event.respond(
                f"ðŸ“ **main.py**\nðŸ“Š Ø§Ù„Ø­Ø¬Ù…: {len(current_code)} Ø­Ø±Ù\n\n"
                "âš ï¸ **ØªØ­Ø°ÙŠØ±:** Ø£Ø±Ø³Ù„ Ø§Ù„ÙƒÙˆØ¯ Ø§Ù„ÙƒØ§Ù…Ù„ Ø§Ù„Ø¬Ø¯ÙŠØ¯\nØ³ÙŠØªÙ… ÙØ­ØµÙ‡ ØªÙ„Ù‚Ø§Ø¦ÙŠØ§Ù‹ Ù‚Ø¨Ù„ Ø§Ù„Ø±ÙØ¹:"
            )
            user_states[user_id] = {"state": "awaiting_github_edit", "original_code": current_code}
            return

        # Ø¥ØµÙ„Ø§Ø­ Ø®Ø·Ø£ Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡
        if data == "fix_error_ai":
            if user_id not in ADMIN_IDS:
                await event.answer("â›” ØºÙŠØ± Ù…ØµØ±Ø­", alert=True)
                return
            user_states[user_id] = {"state": "awaiting_error_fix"}
            await event.respond("ðŸ”§ **Ø¥ØµÙ„Ø§Ø­ Ø§Ù„Ø£Ø®Ø·Ø§Ø¡ Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡**\n\nØ£Ø±Ø³Ù„ Ø§Ù„Ø®Ø·Ø£ ÙƒØ§Ù…Ù„Ø§Ù‹ (Error Traceback):")
            return

        # Ø¥Ø¹Ø§Ø¯Ø© ØªØ´ØºÙŠÙ„
        if data == "restart_bot":
            if user_id not in ADMIN_IDS:
                await event.answer("â›” ØºÙŠØ± Ù…ØµØ±Ø­", alert=True)
                return
            await event.respond("ðŸ”„ **Ø¬Ø§Ø±ÙŠ Ø¥Ø¹Ø§Ø¯Ø© ØªØ´ØºÙŠÙ„ Ø§Ù„Ø¨ÙˆØª...**")
            await restart_bot()
            return

        # ØªØ³Ø¬ÙŠÙ„ Ø§Ù„Ø£Ø²Ø±Ø§Ø± Ø§Ù„Ø«Ø§Ø¨ØªØ©
        if await registry.execute(data, event):
            return

        await event.answer("âš ï¸ Ø§Ù„Ø²Ø± ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯", alert=True)

    except Exception as e:
        log.error(f"Ø®Ø·Ø£ ÙÙŠ callback: {e}\n{traceback.format_exc()}")
        try:
            await event.answer("âŒ Ø®Ø·Ø£", alert=True)
        except:
            pass

async def show_folder(event, folder_key: str):
    await registry.refresh_from_db()
    folder_names = {
        "accounts": "ðŸ­ Ù…ØµÙ†Ø¹ Ø§Ù„Ø¬ÙŠÙˆØ´", "tactical": "ðŸš€ Ø§Ù„Ù‡Ø¬ÙˆÙ… Ø§Ù„ØªÙƒØªÙŠÙƒÙŠ",
        "stealth": "ðŸ‘» Ø¹Ù…Ù„ÙŠØ§Øª Ø§Ù„ØªØ®ÙÙŠ", "ai_lab": "ðŸ§  Ù…Ø®ØªØ¨Ø± Ø§Ù„Ø°ÙƒØ§Ø¡",
        "protection": "ðŸ›¡ï¸ Ø¯Ø±Ø¹ Ø§Ù„Ø­Ù…Ø§ÙŠØ©", "budget": "ðŸ’° Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©",
    }
    display_name = folder_names.get(folder_key, folder_key.replace("_", " ").title())
    buttons_list = registry.get_buttons_by_folder(folder_key)
    keyboard = [[Button.inline(f"{btn.get('emoji','ðŸ”˜')} {btn.get('display_name', btn['button_id'])}", btn["button_id"].encode())] for btn in buttons_list]
    keyboard.append([Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"start")])
    if event.sender_id in ADMIN_IDS:
        keyboard.append([Button.inline("âž• Ø¥Ø¶Ø§ÙØ© Ø²Ø±", f"add_btn_in_{folder_key}".encode())])
    try:
        await event.edit(f"{display_name}\n\nðŸ“Š {len(buttons_list)} Ø²Ø±\nØ§Ø®ØªØ±:", buttons=keyboard, parse_mode='md')
    except:
        await event.respond(f"{display_name}\n\nðŸ“Š {len(buttons_list)} Ø²Ø±", buttons=keyboard, parse_mode='md')

# ============================================
# Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…
# ============================================

@registry.register("admin_full_panel")
async def admin_full_panel(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("â›” ØºÙŠØ± Ù…ØµØ±Ø­", alert=True)
        return
    keyboard = [
        [Button.inline("ðŸ“ Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª", b"admin_folders"), Button.inline("ðŸ”˜ Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ø£Ø²Ø±Ø§Ø±", b"admin_buttons")],
        [Button.inline("ðŸ‘¥ Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ø­Ø³Ø§Ø¨Ø§Øª", b"admin_accounts"), Button.inline("ðŸ’° Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©", b"budget_system")],
        [Button.inline("ðŸ¤– Ø¥Ù†Ø´Ø§Ø¡ Ø²Ø± Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡", b"ai_create_button"), Button.inline("ðŸ“Š Ø§Ù„Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª", b"admin_stats")],
        [Button.inline("ðŸ—‘ï¸ Ø³Ù„Ø© Ø§Ù„Ù…Ø­Ø°ÙˆÙØ§Øª", b"admin_recycle"), Button.inline("âš™ï¸ Ø§Ù„Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª", b"admin_settings")],
        [Button.inline("ðŸ”„ ØªØ­Ø¯ÙŠØ« Ø§Ù„ÙƒØ§Ø´", b"admin_refresh"), Button.inline("ðŸ“‚ Ù…Ù„ÙØ§Øª GitHub", b"list_github")],
        [Button.inline("ðŸ™ ØªØ¹Ø¯ÙŠÙ„ main.py", b"edit_main_github"), Button.inline("ðŸ”§ Ø¥ØµÙ„Ø§Ø­ Ø®Ø·Ø£ Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡", b"fix_error_ai")],
        [Button.inline("ðŸ”„ Ø¥Ø¹Ø§Ø¯Ø© ØªØ´ØºÙŠÙ„ Ø§Ù„Ø¨ÙˆØª", b"restart_bot")],
        [Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"start")],
    ]
    try:
        await event.edit("âš™ï¸ **Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ… Ø§Ù„Ø´Ø§Ù…Ù„Ø©**\n\nðŸ‘‘ Ù…Ø±Ø­Ø¨Ø§Ù‹ Ù‚Ø§Ø¦Ø¯", buttons=keyboard, parse_mode='md')
    except:
        await event.respond("âš™ï¸ **Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ… Ø§Ù„Ø´Ø§Ù…Ù„Ø©**\n\nðŸ‘‘ Ù…Ø±Ø­Ø¨Ø§Ù‹ Ù‚Ø§Ø¦Ø¯", buttons=keyboard, parse_mode='md')

@registry.register("admin_folders")
async def admin_folders(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db()
    folders = registry.get_folders()
    keyboard = [[Button.inline(f"{f.get('emoji','ðŸ“')} {f.get('display_name')}", f"edit_folder_{f['folder_key']}")] for f in folders[:20]]
    keyboard.append([Button.inline("âž• Ø¥Ø¶Ø§ÙØ© Ù…Ø¬Ù„Ø¯", b"add_folder"), Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_full_panel")])
    try:
        await event.edit("ðŸ“ **Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª**", buttons=keyboard)
    except:
        await event.respond("ðŸ“ **Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª**", buttons=keyboard)

@registry.register("add_folder")
async def add_folder(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    user_states[event.sender_id] = {"state": "awaiting_folder_key"}
    await event.respond("âž• **Ø¥Ø¶Ø§ÙØ© Ù…Ø¬Ù„Ø¯ Ø¬Ø¯ÙŠØ¯**\n\nØ£Ø±Ø³Ù„ Ø§Ù„Ù…ÙØªØ§Ø­ (key) Ù„Ù„Ù…Ø¬Ù„Ø¯:")

@registry.register("admin_buttons")
async def admin_buttons(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db()
    buttons_list = list(registry._dynamic_buttons.values())
    keyboard = [[Button.inline(f"{btn.get('emoji','ðŸ”˜')} {btn.get('display_name', btn['button_id'])[:25]}", f"edit_btn_{btn['button_id']}")] for btn in buttons_list[:30]]
    keyboard.append([Button.inline("âž• Ø¥Ø¶Ø§ÙØ© Ø²Ø±", b"add_button"), Button.inline("ðŸ¤– Ø²Ø± Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡", b"ai_create_button")])
    keyboard.append([Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_full_panel")])
    try:
        await event.edit(f"ðŸ”˜ **Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ø£Ø²Ø±Ø§Ø±** ({len(buttons_list)})", buttons=keyboard)
    except:
        await event.respond(f"ðŸ”˜ **Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ø£Ø²Ø±Ø§Ø±** ({len(buttons_list)})", buttons=keyboard)

@registry.register("add_button")
async def add_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    user_states[event.sender_id] = {"state": "awaiting_button_data", "step": 1, "data": {}}
    await event.respond("âž• **Ø¥Ø¶Ø§ÙØ© Ø²Ø± Ø¬Ø¯ÙŠØ¯ - Ø§Ù„Ø®Ø·ÙˆØ© 1/6**\n\nØ£Ø±Ø³Ù„ Ø§Ù„Ù€ Button ID:")

@registry.register("ai_create_button")
async def ai_create_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("â›” Ù„Ù„Ù…Ø·ÙˆØ± ÙÙ‚Ø·", alert=True)
        return
    user_states[event.sender_id] = {"state": "awaiting_ai_button_description"}
    await event.respond("ðŸ¤– **Ø¥Ù†Ø´Ø§Ø¡ Ø²Ø± Ø¨Ø§Ù„Ø°ÙƒØ§Ø¡**\n\nØ£Ø±Ø³Ù„ ÙˆØµÙ Ø§Ù„Ø²Ø± Ø¨Ø§Ù„Ø¹Ø±Ø¨ÙŠØ©:\n\n_Ù…Ø«Ø§Ù„: Ø²Ø± ÙŠØ¹Ø±Ø¶ Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª Ø§Ù„Ù…Ø¨ÙŠØ¹Ø§Øª Ø§Ù„ÙŠÙˆÙ…ÙŠØ©_")

@registry.register("admin_refresh")
async def admin_refresh(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.refresh_from_db(force=True)
    await event.answer("âœ… ØªÙ… ØªØ­Ø¯ÙŠØ« Ø§Ù„ÙƒØ§Ø´", alert=True)

@registry.register("admin_recycle")
async def admin_recycle(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    try:
        deleted = supabase.table("deleted_items").select("*").order("deleted_at", desc=True).limit(50).execute()
        if not deleted.data:
            await event.edit("ðŸ—‘ï¸ **Ø³Ù„Ø© Ø§Ù„Ù…Ø­Ø°ÙˆÙØ§Øª ÙØ§Ø±ØºØ©**", buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_full_panel")]])
            return
        keyboard = [[Button.inline(f"ðŸ”„ {item['item_type']}: {item['item_id'][:20]}", f"restore_{item['id']}")] for item in deleted.data[:20]]
        keyboard.append([Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_full_panel")])
        await event.edit("ðŸ—‘ï¸ **Ø³Ù„Ø© Ø§Ù„Ù…Ø­Ø°ÙˆÙØ§Øª**", buttons=keyboard)
    except:
        await event.edit("ðŸ—‘ï¸ **Ø³Ù„Ø© Ø§Ù„Ù…Ø­Ø°ÙˆÙØ§Øª ÙØ§Ø±ØºØ©**", buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_full_panel")]])

@registry.register("admin_settings")
async def admin_settings(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    keyboard = [
        [Button.inline("ðŸ¤– Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª AI", b"setting_ai"), Button.inline("ðŸŒ Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ", b"setting_proxy")],
        [Button.inline("ðŸ’° Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©", b"setting_budget")],
        [Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_full_panel")],
    ]
    await event.edit("âš™ï¸ **Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ù†Ø¸Ø§Ù…**", buttons=keyboard)

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
        f"ðŸ“Š **Ø§Ù„Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª Ø§Ù„Ù…ØªÙ‚Ø¯Ù…Ø©**\n\n"
        f"ðŸ”˜ Ø§Ù„Ø£Ø²Ø±Ø§Ø±: {len(registry._dynamic_buttons)}\n"
        f"ðŸ“ Ø§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª: {len(registry._folders)}\n"
        f"ðŸ‘¥ Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…ÙŠÙ†: {users_count}\n"
        f"ðŸ‘† Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ø¶ØºØ·Ø§Øª: {total_clicks}\n"
        f"ðŸš‚ Railway: {railway.get('status', 'ØºÙŠØ± Ù…Ø¹Ø±ÙˆÙ')}\n"
        f"ðŸ¤– AI: {'ðŸŸ¢ Ù†Ø´Ø·' if OPENAI_KEY else 'ðŸ”´ ØºÙŠØ± Ù†Ø´Ø·'}",
        buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_full_panel")]]
    )

@registry.register("admin_accounts")
async def admin_accounts(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    keyboard = [
        [Button.inline("ðŸ’° Ø­Ø³Ø§Ø¨Ø§Øª Ø§Ù„ØªØ±ÙˆÙŠØ¬", b"promo_accounts_list")],
        [Button.inline("ðŸ“ Ø­Ø³Ø§Ø¨Ø§Øª Ø§Ù„Ù†Ø´Ø± Ø§Ù„ÙØ±Ø¯ÙŠ", b"individual_accounts_list")],
        [Button.inline("ðŸ“Š Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª Ø§Ù„Ø­Ø³Ø§Ø¨Ø§Øª", b"accounts_stats")],
        [Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_full_panel")]
    ]
    await event.edit("ðŸ‘¥ **Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„Ø­Ø³Ø§Ø¨Ø§Øª**", buttons=keyboard)

@registry.register("promo_accounts_list")
async def promo_accounts_list(event, bot, supabase):
    accounts = supabase.table("promo_accounts").select("*").execute()
    if not accounts.data:
        await event.edit("ðŸ’° **Ù„Ø§ ØªÙˆØ¬Ø¯ Ø­Ø³Ø§Ø¨Ø§Øª ØªØ±ÙˆÙŠØ¬ÙŠØ©**", buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_accounts")]])
        return
    text = "ðŸ’° **Ø­Ø³Ø§Ø¨Ø§Øª Ø§Ù„ØªØ±ÙˆÙŠØ¬**\n\n"
    for acc in accounts.data[:20]:
        text += f"â€¢ {acc['platform']}: {acc.get('account_name', acc.get('email', 'ØºÙŠØ± Ù…Ø¹Ø±ÙˆÙ'))}\n"
    await event.edit(text, buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_accounts")]])

@registry.register("individual_accounts_list")
async def individual_accounts_list(event, bot, supabase):
    accounts = supabase.table("individual_accounts").select("*").execute()
    if not accounts.data:
        await event.edit("ðŸ“ **Ù„Ø§ ØªÙˆØ¬Ø¯ Ø­Ø³Ø§Ø¨Ø§Øª**", buttons=[[Button.inline("âž• Ø¥Ø¶Ø§ÙØ©", b"individual_add"), Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_accounts")]])
        return
    keyboard = [[Button.inline(f"{'ðŸŸ¢' if acc['status']=='active' else 'ðŸ”´'} {acc['platform']}: @{acc.get('username','Ø¨Ø¯ÙˆÙ†')}", f"individual_view_{acc['id']}")] for acc in accounts.data[:20]]
    keyboard.append([Button.inline("âž• Ø¥Ø¶Ø§ÙØ© Ø­Ø³Ø§Ø¨", b"individual_add"), Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_accounts")])
    await event.edit("ðŸ“ **Ø­Ø³Ø§Ø¨Ø§Øª Ø§Ù„Ù†Ø´Ø± Ø§Ù„ÙØ±Ø¯ÙŠ**", buttons=keyboard)

@registry.register("individual_add")
async def individual_add(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 1}
    await event.respond("âž• **Ø¥Ø¶Ø§ÙØ© Ø­Ø³Ø§Ø¨ Ù†Ø´Ø± ÙØ±Ø¯ÙŠ**\n\nØ§Ø®ØªØ± Ø§Ù„Ù…Ù†ØµØ©:", buttons=[
        [Button.inline("ðŸ“± ØªÙ„ÙŠØ¬Ø±Ø§Ù…", b"ind_platform_telegram"), Button.inline("ðŸ“˜ ÙÙŠØ³Ø¨ÙˆÙƒ", b"ind_platform_facebook")],
        [Button.inline("ðŸ“· Ø¥Ù†Ø³ØªØºØ±Ø§Ù…", b"ind_platform_instagram"), Button.inline("ðŸŽµ ØªÙŠÙƒ ØªÙˆÙƒ", b"ind_platform_tiktok")],
        [Button.inline("ðŸ”™ Ø¥Ù„ØºØ§Ø¡", b"individual_accounts_list")]
    ])

@registry.register("accounts_stats")
async def accounts_stats(event, bot, supabase):
    try:
        promo = supabase.table("promo_accounts").select("*", count="exact").execute()
        individual = supabase.table("individual_accounts").select("*", count="exact").execute()
        await event.edit(
            f"ðŸ“Š **Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª Ø§Ù„Ø­Ø³Ø§Ø¨Ø§Øª**\n\nØ§Ù„ØªØ±ÙˆÙŠØ¬: {promo.count}\nØ§Ù„Ù†Ø´Ø± Ø§Ù„ÙØ±Ø¯ÙŠ: {individual.count}",
            buttons=[[Button.inline("ðŸ”„ ØªØ­Ø¯ÙŠØ«", b"accounts_stats"), Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_accounts")]]
        )
    except:
        await event.edit("âŒ Ø®Ø·Ø£ ÙÙŠ Ø¬Ù„Ø¨ Ø§Ù„Ø¥Ø­ØµØ§Ø¦ÙŠØ§Øª", buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_accounts")]])

# ============================================
# Ù†Ø¸Ø§Ù… Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©
# ============================================

@registry.register("budget_system")
async def budget_system(event, bot, supabase):
    try:
        cards = supabase.table("payment_cards").select("*").eq("is_active", True).execute()
        total_balance = sum(c.get('current_balance', 0) for c in cards.data)
        await event.respond(
            f"ðŸ’° **Ù†Ø¸Ø§Ù… Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©**\n\n"
            f"ðŸ’³ Ø§Ù„ÙÙŠØ²Ø§Øª Ø§Ù„Ù†Ø´Ø·Ø©: {len(cards.data)}\n"
            f"ðŸ’° Ø¥Ø¬Ù…Ø§Ù„ÙŠ Ø§Ù„Ø±ØµÙŠØ¯: ${total_balance}",
            buttons=[
                [Button.inline("ðŸ’³ Ø¥Ø¯Ø§Ø±Ø© Ø§Ù„ÙÙŠØ²Ø§Øª", b"cards_manage"), Button.inline("âž• Ø¥Ø¶Ø§ÙØ© ÙÙŠØ²Ø§", b"card_add")],
                [Button.inline("ðŸ“¢ Ø§Ù„Ø­Ù…Ù„Ø§Øª Ø§Ù„Ø¥Ø¹Ù„Ø§Ù†ÙŠØ©", b"campaigns_manage")],
                [Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"start")]
            ]
        )
    except:
        await event.respond("âŒ Ø®Ø·Ø£ ÙÙŠ Ù†Ø¸Ø§Ù… Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©")

@registry.register("cards_manage")
async def cards_manage(event, bot, supabase):
    cards = supabase.table("payment_cards").select("*").execute()
    if not cards.data:
        await event.edit("ðŸ’³ **Ù„Ø§ ØªÙˆØ¬Ø¯ ÙÙŠØ²Ø§Øª**", buttons=[[Button.inline("âž• Ø¥Ø¶Ø§ÙØ©", b"card_add"), Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"budget_system")]])
        return
    keyboard = [[Button.inline(f"{'ðŸŸ¢' if c['is_active'] else 'ðŸ”´'} **** {c['card_number'][-4:]} - ${c.get('current_balance',0)}", f"card_view_{c['id']}")] for c in cards.data]
    keyboard.append([Button.inline("âž• Ø¥Ø¶Ø§ÙØ© ÙÙŠØ²Ø§", b"card_add"), Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"budget_system")])
    await event.edit("ðŸ’³ **Ø§Ù„ÙÙŠØ²Ø§Øª Ø§Ù„Ù…Ø³Ø¬Ù„Ø©:**", buttons=keyboard)

@registry.register("card_add")
async def card_add(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_card_details", "step": 1}
    await event.respond("âž• **Ø¥Ø¶Ø§ÙØ© ÙÙŠØ²Ø§ - Ø§Ù„Ø®Ø·ÙˆØ© 1/4**\n\nØ£Ø±Ø³Ù„ Ø±Ù‚Ù… Ø§Ù„Ø¨Ø·Ø§Ù‚Ø© (16 Ø±Ù‚Ù…):")

@registry.register("campaigns_manage")
async def campaigns_manage(event, bot, supabase):
    await event.respond("ðŸ“¢ **Ø§Ù„Ø­Ù…Ù„Ø§Øª Ø§Ù„Ø¥Ø¹Ù„Ø§Ù†ÙŠØ©**\n\nðŸš€ Ù‚ÙŠØ¯ Ø§Ù„ØªØ·ÙˆÙŠØ±...", buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"budget_system")]])

# ============================================
# Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ù†Ø¸Ø§Ù…
# ============================================

@registry.register("setting_ai")
async def setting_ai(event, bot, supabase):
    await event.respond(
        f"ðŸ¤– **Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ø°ÙƒØ§Ø¡ Ø§Ù„Ø§ØµØ·Ù†Ø§Ø¹ÙŠ**\n\n"
        f"ðŸ”‘ Ù…ÙØªØ§Ø­ OpenAI: {'âœ… Ù…ÙˆØ¬ÙˆØ¯' if OPENAI_KEY else 'âŒ ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯'}\n"
        f"ðŸ’¾ Ø¬Ø¯ÙˆÙ„ Ø§Ù„Ø°Ø§ÙƒØ±Ø©: ai_memory",
        buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_settings")]]
    )

@registry.register("setting_proxy")
async def setting_proxy(event, bot, supabase):
    await event.respond(
        f"ðŸŒ **Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ**\n\n"
        f"ðŸ”— Ø§Ù„Ø­Ø§Ù„Ø©: {'âœ… Ù†Ø´Ø·' if PROXY_URL else 'âŒ ØºÙŠØ± Ù…Ø³ØªØ®Ø¯Ù…'}",
        buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_settings")]]
    )

@registry.register("setting_budget")
async def setting_budget(event, bot, supabase):
    await event.respond("ðŸ’° **Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©**\n\nðŸ”œ Ù‚ÙŠØ¯ Ø§Ù„ØªØ·ÙˆÙŠØ±", buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"admin_settings")]])

@registry.register("ind_platform_telegram")
async def ind_platform_telegram(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "telegram"}}
    await event.respond("âœ… Ø§Ù„Ù…Ù†ØµØ©: ØªÙ„ÙŠØ¬Ø±Ø§Ù…\n\nØ£Ø±Ø³Ù„ Ø±Ù‚Ù… Ø§Ù„Ù‡Ø§ØªÙ:")

@registry.register("ind_platform_facebook")
async def ind_platform_facebook(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "facebook"}}
    await event.respond("âœ… Ø§Ù„Ù…Ù†ØµØ©: ÙÙŠØ³Ø¨ÙˆÙƒ\n\nØ£Ø±Ø³Ù„ Ø§Ù„Ø¨Ø±ÙŠØ¯ Ø§Ù„Ø¥Ù„ÙƒØªØ±ÙˆÙ†ÙŠ:")

@registry.register("ind_platform_instagram")
async def ind_platform_instagram(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "instagram"}}
    await event.respond("âœ… Ø§Ù„Ù…Ù†ØµØ©: Ø¥Ù†Ø³ØªØºØ±Ø§Ù…\n\nØ£Ø±Ø³Ù„ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…:")

@registry.register("ind_platform_tiktok")
async def ind_platform_tiktok(event, bot, supabase):
    user_states[event.sender_id] = {"state": "awaiting_individual_account", "step": 2, "data": {"platform": "tiktok"}}
    await event.respond("âœ… Ø§Ù„Ù…Ù†ØµØ©: ØªÙŠÙƒ ØªÙˆÙƒ\n\nØ£Ø±Ø³Ù„ Ø§Ø³Ù… Ø§Ù„Ù…Ø³ØªØ®Ø¯Ù…:")

@registry.register("cancel")
async def cancel_action(event, bot, supabase):
    user_id = event.sender_id
    if user_id in user_states:
        del user_states[user_id]
    await event.respond("âŒ ØªÙ… Ø¥Ù„ØºØ§Ø¡ Ø§Ù„Ø¹Ù…Ù„ÙŠØ©", buttons=[[Button.inline("ðŸ”™ Ø±Ø¬ÙˆØ¹", b"start")]])

# ============================================
# Ø¥Ù†Ø´Ø§Ø¡ Ø§Ù„Ø¬Ø¯Ø§ÙˆÙ„ ÙˆØ§Ù„Ù…Ø¬Ù„Ø¯Ø§Øª Ø§Ù„Ø§ÙØªØ±Ø§Ø¶ÙŠØ©
# ============================================

async def create_default_folders():
    folders = [
        ("main", "Ø§Ù„Ù‚Ø§Ø¦Ù…Ø© Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠØ©", "ðŸ ", "blue", 0),
        ("accounts", "Ù…ØµÙ†Ø¹ Ø§Ù„Ø¬ÙŠÙˆØ´", "ðŸ­", "green", 1),
        ("tactical", "Ø§Ù„Ù‡Ø¬ÙˆÙ… Ø§Ù„ØªÙƒØªÙŠÙƒÙŠ", "ðŸš€", "red", 2),
        ("stealth", "Ø¹Ù…Ù„ÙŠØ§Øª Ø§Ù„ØªØ®ÙÙŠ", "ðŸ‘»", "purple", 3),
        ("ai_lab", "Ù…Ø®ØªØ¨Ø± Ø§Ù„Ø°ÙƒØ§Ø¡", "ðŸ§ ", "dark", 4),
        ("protection", "Ø¯Ø±Ø¹ Ø§Ù„Ø­Ù…Ø§ÙŠØ©", "ðŸ›¡ï¸", "blue", 5),
        ("budget", "Ø§Ù„Ù…ÙŠØ²Ø§Ù†ÙŠØ©", "ðŸ’°", "green", 6),
        ("admin", "Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…", "âš™ï¸", "red", 7),
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
        log.warning("âš ï¸ Ø¬Ø¯ÙˆÙ„ backups ØºÙŠØ± Ù…ÙˆØ¬ÙˆØ¯")

# ============================================
# Ø§Ù„Ù…Ù‡Ø§Ù… Ø§Ù„Ø®Ù„ÙÙŠØ©
# ============================================

async def auto_railway_monitor():
    while True:
        try:
            await asyncio.sleep(3600)
            status = await get_railway_deployment_status()
            if status.get('status') == 'FAILED' and ADMIN_IDS:
                await bot.send_message(
                    ADMIN_IDS[0],
                    f"âš ï¸ **ØªÙ†Ø¨ÙŠÙ‡ Railway!**\n\n"
                    f"Ø­Ø§Ù„Ø© Ø§Ù„Ù†Ø´Ø±: ÙØ´Ù„ (FAILED)\n"
                    f"Ø§Ù„ÙˆÙ‚Øª: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Ø§Ù„Ø³Ø¬Ù„Ø§Øª: {status.get('logsUrl', 'ØºÙŠØ± Ù…ØªÙˆÙØ±')}"
                )
        except:
            await asyncio.sleep(3600)

async def auto_backup():
    while True:
        try:
            await asyncio.sleep(21600)  # ÙƒÙ„ 6 Ø³Ø§Ø¹Ø§Øª
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
            log.info("âœ… Ù†Ø³Ø®Ø© Ø§Ø­ØªÙŠØ§Ø·ÙŠØ© ØªÙ„Ù‚Ø§Ø¦ÙŠØ©")
        except:
            await asyncio.sleep(3600)

async def auto_reset_accounts():
    while True:
        try:
            now = datetime.now()
            next_midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
            await asyncio.sleep((next_midnight - now).total_seconds())
            supabase.table("individual_accounts").update({"posts_today": 0}).execute()
            log.info("âœ… ØªÙ… Ø¥Ø¹Ø§Ø¯Ø© ØªØ¹ÙŠÙŠÙ† Ù…Ù†Ø´ÙˆØ±Ø§Øª Ø§Ù„ÙŠÙˆÙ…")
        except:
            await asyncio.sleep(3600)

# ============================================
# Ø§Ù„ØªØ´ØºÙŠÙ„ Ø§Ù„Ø±Ø¦ÙŠØ³ÙŠ
# ============================================

async def main():
    log.info("ðŸš€ Ø¬Ø§Ø±ÙŠ ØªØ´ØºÙŠÙ„ MUSTAFA SHOP - DIGITAL EMPIRE v7...")
    log.info("=" * 50)

    ensure_backup_table()
    await create_ai_memory_table()
    await create_default_folders()

    try:
        supabase.table("folders").select("count").limit(1).execute()
        log.info("âœ… Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª Ø¬Ø§Ù‡Ø²Ø©")
    except Exception as e:
        log.warning(f"âš ï¸ Ù‚Ø§Ø¹Ø¯Ø© Ø§Ù„Ø¨ÙŠØ§Ù†Ø§Øª: {e}")

    await registry.refresh_from_db(force=True)
    await bot.start(bot_token=BOT_TOKEN)

    me = await bot.get_me()
    log.info(f"âœ… Ø§Ù„Ø¨ÙˆØª ÙŠØ¹Ù…Ù„! @{me.username}")
    log.info(f"ðŸ‘‘ Ø§Ù„Ù…Ø·ÙˆØ±ÙˆÙ†: {ADMIN_IDS}")
    log.info(f"ðŸ¤– AI: {'ðŸŸ¢ Ù†Ø´Ø·' if OPENAI_KEY else 'ðŸ”´ ØºÙŠØ± Ù†Ø´Ø·'}")
    log.info(f"ðŸŒ Ø§Ù„Ø¨Ø±ÙˆÙƒØ³ÙŠ: {'ðŸŸ¢ Ù†Ø´Ø·' if PROXY_URL else 'âšª ØºÙŠØ± Ù…Ø³ØªØ®Ø¯Ù…'}")
    log.info(f"ðŸ™ GitHub: {'ðŸŸ¢ Ù…ØªØµÙ„' if GITHUB_TOKEN else 'âšª ØºÙŠØ± Ù…ØªØµÙ„'}")
    log.info(f"ðŸš‚ Railway: {'ðŸŸ¢ Ù…ØªØµÙ„' if RAILWAY_TOKEN else 'ðŸ”´ ØºÙŠØ± Ù…ØªØµÙ„'}")
    log.info("=" * 50)

    asyncio.create_task(auto_railway_monitor())
    asyncio.create_task(auto_backup())
    asyncio.create_task(auto_reset_accounts())

    if ADMIN_IDS:
        try:
            await bot.send_message(
                ADMIN_IDS[0],
                f"âœ… **MUSTAFA SHOP v7 ÙŠØ¹Ù…Ù„!**\n\n"
                f"ðŸ“Š {len(registry._dynamic_buttons)} Ø²Ø± | ðŸ“ {len(registry._folders)} Ù…Ø¬Ù„Ø¯\n"
                f"ðŸ¤– AI: {'Ù†Ø´Ø·' if OPENAI_KEY else 'ØºÙŠØ± Ù†Ø´Ø·'}\n"
                f"ðŸŒ Ø¨Ø±ÙˆÙƒØ³ÙŠ: {'Ù†Ø´Ø·' if PROXY_URL else 'ØºÙŠØ± Ù…Ø³ØªØ®Ø¯Ù…'}\n"
                f"ðŸ™ GitHub: {'Ù…ØªØµÙ„' if GITHUB_TOKEN else 'ØºÙŠØ± Ù…ØªØµÙ„'}\n\n"
                f"âœ¨ **Ø§Ù„Ø¬Ø¯ÙŠØ¯ ÙÙŠ v7:**\n"
                f"â€¢ âœ… Ø¥ØµÙ„Ø§Ø­ ØªÙƒØ±Ø§Ø± Ø§Ù„Ù€ handlers\n"
                f"â€¢ âœ… ÙØ­Øµ Ø§Ù„ÙƒÙˆØ¯ Ù‚Ø¨Ù„ Ø±ÙØ¹Ù‡ Ø¹Ù„Ù‰ GitHub\n"
                f"â€¢ âœ… Ø¥ØµÙ„Ø§Ø­ Ù‚Ø±Ø§Ø¡Ø© Ø§Ù„Ù…Ù„ÙØ§Øª Ø§Ù„ÙƒØ¨ÙŠØ±Ø©\n"
                f"â€¢ âœ… Ø£Ù…Ø± /broadcast Ù„Ù„Ø¨Ø« Ø§Ù„Ø¬Ù…Ø§Ø¹ÙŠ\n"
                f"â€¢ âœ… ØªØ­Ø³ÙŠÙ† Ù„ÙˆØ­Ø© Ø§Ù„ØªØ­ÙƒÙ…"
            )
        except:
            pass

    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("ðŸ‘‹ ØªÙ… Ø¥ÙŠÙ‚Ø§Ù Ø§Ù„Ø¨ÙˆØª")
    except Exception as e:
        log.error(f"âŒ Ø®Ø·Ø£ ÙØ§Ø¯Ø­: {e}")
        traceback.print_exc()
# main.py - MUSTAFA SHOP DIGITAL EMPIRE v7
# البوت العبقري - يقرأ GitHub مباشرة، يطور نفسه، يدير كل شيء

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

from telethon import TelegramClient, events, Button
from supabase import create_client, Client
import httpx

# ============================================
# الإعدادات الأساسية
# ============================================

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
OPENAI_KEY = os.environ.get("OPENAI_KEY", "")
ADMIN_IDS = [int(x.strip()) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip()]
PROXY_URL = os.environ.get("PROXY_URL", "")
GITHUB_REPO = os.environ.get("GITHUB_REPO", "kilua964iq/Kilua-shop")
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# ============================================
# تهيئة العميل
# ============================================

bot = TelegramClient("mustafa_bot", API_ID, API_HASH)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================
# دوال GitHub المباشرة (بدون تعقيدات)
# ============================================

GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_REPO}"

async def get_github_files():
    """جلب قائمة الملفات مباشرة من GitHub"""
    url = f"{GITHUB_API_BASE}/contents/?ref={GITHUB_BRANCH}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                return resp.json()
            return None
    except:
        return None

async def get_github_file_content(path: str):
    """جلب محتوى ملف معين"""
    url = f"{GITHUB_API_BASE}/contents/{path}?ref={GITHUB_BRANCH}"
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("content"):
                    return base64.b64decode(data["content"]).decode('utf-8')
            return None
    except:
        return None

# ============================================
# نظام الأزرار
# ============================================

class ButtonRegistry:
    def __init__(self):
        self._handlers = {}
        self._buttons = {}
        self._folders = {}
    
    def register(self, button_id: str):
        def decorator(func):
            self._handlers[button_id] = func
            return func
        return decorator
    
    async def load(self):
        try:
            folders = supabase.table("folders").select("*").eq("is_active", True).order("sort_order").execute()
            self._folders = {f["folder_key"]: f for f in folders.data}
            
            buttons = supabase.table("buttons").select("*").eq("is_active", True).execute()
            self._buttons = {b["button_id"]: b for b in buttons.data}
            log.info(f"✅ تم تحميل {len(self._buttons)} زر و {len(self._folders)} مجلد")
        except Exception as e:
            log.error(f"خطأ في تحميل البيانات: {e}")
    
    async def execute(self, button_id: str, event, **kwargs):
        if button_id in self._handlers:
            try:
                await self._handlers[button_id](event, bot, supabase, **kwargs)
                return True
            except Exception as e:
                await event.answer(f"❌ خطأ: {str(e)[:100]}", alert=True)
                return True
        
        if button_id in self._buttons:
            button = self._buttons[button_id]
            code = button.get("python_code", "")
            if not code:
                await event.answer("⚠️ هذا الزر ليس له كود", alert=True)
                return True
            try:
                exec_globals = {
                    'event': event, 'bot': bot, 'supabase': supabase,
                    'Button': Button, 'asyncio': asyncio, 'datetime': datetime,
                    'random': random, 'json': json, 'httpx': httpx, 'log': log,
                    '__builtins__': __builtins__,
                }
                exec(code, exec_globals)
                return True
            except Exception as e:
                await event.respond(f"❌ خطأ: `{str(e)[:200]}`")
                return True
        return False
    
    def get_folders(self):
        return list(self._folders.values())

registry = ButtonRegistry()
user_states = {}

# ============================================
# الذكاء الاصطناعي
# ============================================

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
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            return "🔴 خطأ في الاتصال"
    except Exception as e:
        return f"🔴 خطأ: {str(e)[:100]}"

# ============================================
# الأزرار الرئيسية
# ============================================

@bot.on(events.NewMessage(pattern='/start'))
async def start_cmd(event):
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
    
    await registry.load()
    
    keyboard = [
        [Button.inline("📂 ملفات GitHub", b"github_files")],
        [Button.inline("📊 الإحصائيات", b"stats")],
        [Button.inline("🌐 فحص البروكسي", b"check_proxy")],
        [Button.inline("⚙️ لوحة التحكم", b"admin")] if user_id in ADMIN_IDS else [],
        [Button.inline("🧠 مبرمج AI", b"ai_chat")],
    ]
    
    await event.respond(
        "🏰 **MUSTAFA SHOP - DIGITAL EMPIRE v7** 🏰\n\n"
        f"📊 {len(registry._buttons)} زر نشط | 📁 {len(registry._folders)} مجلد\n"
        f"🤖 AI: {'🟢 نشط' if OPENAI_KEY else '🔴 غير نشط'}\n"
        f"🐙 GitHub: {GITHUB_REPO}\n\n"
        "💡 اكتب ما تريد، المبرمج AI يرد عليك!",
        buttons=[b for b in keyboard if b],
        parse_mode='md'
    )

@registry.register("github_files")
async def github_files_button(event, bot, supabase):
    await event.respond("📂 **جاري جلب الملفات من GitHub...**")
    
    files = await get_github_files()
    if not files:
        await event.respond(f"❌ **فشل جلب الملفات**\n\nالمستودع: `{GITHUB_REPO}`\nالفرع: `{GITHUB_BRANCH}`\n\nتأكد من:\n1. اسم المستودع صحيح\n2. المستودع عام أو لديك توكن صحيح", parse_mode='md')
        return
    
    text = f"📁 **ملفات المستودع `{GITHUB_REPO}`:**\n\n"
    for item in files:
        if item['type'] == 'file':
            text += f"📄 `{item['name']}` - {item['size']} بايت\n"
        elif item['type'] == 'dir':
            text += f"📁 `{item['name']}/`\n"
    
    if len(text) > 4000:
        text = text[:3900] + "\n... (والمزيد)"
    
    await event.respond(text, parse_mode='md')

@registry.register("stats")
async def stats_button(event, bot, supabase):
    await registry.load()
    await event.edit(
        f"📊 **الإحصائيات**\n\n"
        f"🔘 الأزرار: {len(registry._buttons)}\n"
        f"📁 المجلدات: {len(registry._folders)}\n"
        f"🤖 AI: {'نشط' if OPENAI_KEY else 'غير نشط'}\n"
        f"🐙 GitHub: {GITHUB_REPO}\n"
        f"👥 المطورون: {ADMIN_IDS}",
        buttons=[[Button.inline("🔙 رجوع", b"start")]],
        parse_mode='md'
    )

@registry.register("check_proxy")
async def check_proxy_button(event, bot, supabase):
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get("https://api.ipify.org", timeout=10)
            await event.respond(f"🌐 **IP الحالي:** `{resp.text}`\n\n✅ البوت متصل!", parse_mode='md')
    except Exception as e:
        await event.respond(f"❌ خطأ: `{str(e)[:100]}`", parse_mode='md')

@registry.register("ai_chat")
async def ai_chat_button(event, bot, supabase):
    await event.respond(
        "🧠 **مبرمج AI العبقري**\n\n"
        "أنا هنا لمساعدتك! فقط اكتب:\n"
        "• `اعرض ملفات GitHub`\n"
        "• `أضف زر جديد`\n"
        "• `صلح الخطأ كذا`\n"
        "• `أظهر الإحصائيات`\n\n"
        "_أتحدث العربية والإنجليزية_",
        parse_mode='md'
    )

@registry.register("admin")
async def admin_panel(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        await event.answer("⛔ غير مصرح", alert=True)
        return
    
    keyboard = [
        [Button.inline("🔘 إدارة الأزرار", b"admin_buttons")],
        [Button.inline("📁 إدارة المجلدات", b"admin_folders")],
        [Button.inline("🔄 تحديث الكاش", b"refresh")],
        [Button.inline("🔙 رجوع", b"start")],
    ]
    await event.edit("⚙️ **لوحة التحكم**\n\nاختر الإدارة:", buttons=keyboard)

@registry.register("admin_buttons")
async def admin_buttons(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.load()
    btns = list(registry._buttons.values())
    
    if not btns:
        await event.edit("🔘 **لا توجد أزرار**\n\nأضف زراً جديداً", buttons=[[Button.inline("➕ إضافة", b"add_button"), Button.inline("🔙 رجوع", b"admin")]])
        return
    
    keyboard = []
    for btn in btns[:20]:
        keyboard.append([Button.inline(f"{btn.get('emoji', '🔘')} {btn['display_name'][:25]}", f"edit_btn_{btn['button_id']}")])
    keyboard.append([Button.inline("➕ إضافة زر جديد", b"add_button")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin")])
    
    await event.edit(f"🔘 **إدارة الأزرار**\n📊 عدد الأزرار: {len(btns)}", buttons=keyboard)

@registry.register("admin_folders")
async def admin_folders(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.load()
    folders = registry.get_folders()
    
    keyboard = []
    for f in folders:
        keyboard.append([Button.inline(f"{f.get('emoji', '📁')} {f['display_name']}", f"edit_folder_{f['folder_key']}")])
    keyboard.append([Button.inline("➕ إضافة مجلد", b"add_folder")])
    keyboard.append([Button.inline("🔙 رجوع", b"admin")])
    
    await event.edit("📁 **إدارة المجلدات**", buttons=keyboard)

@registry.register("add_button")
async def add_button(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    user_states[event.sender_id] = {"state": "add_button", "step": 1, "data": {}}
    await event.respond("➕ **إضافة زر جديد - الخطوة 1/6**\n\nأرسل الـ Button ID (معرف فريد):")

@registry.register("add_folder")
async def add_folder(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    user_states[event.sender_id] = {"state": "add_folder"}
    await event.respond("➕ **إضافة مجلد جديد**\n\nأرسل المفتاح (key) للمجلد:")

@registry.register("refresh")
async def refresh_cache(event, bot, supabase):
    if event.sender_id not in ADMIN_IDS:
        return
    await registry.load()
    await event.answer("✅ تم تحديث الكاش", alert=True)

# ============================================
# معالج الرسائل (المبرمج AI)
# ============================================

@bot.on(events.NewMessage)
async def message_handler(event):
    if event.out or not event.raw_text:
        return
    
    user_id = event.sender_id
    text = event.raw_text.strip()
    
    # معالج إضافة زر
    if user_id in user_states and user_states[user_id].get("state") == "add_button":
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
            await event.respond(f"✅ الخطوة 3/6: أرسل الإيموجي (مثال: 🚀):")
        elif step == 3:
            data["emoji"] = text or "🔘"
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
            await registry.load()
            del user_states[user_id]
            await event.respond(f"✅ **تم إضافة الزر `{data['button_id']}` بنجاح!**")
            await admin_buttons(event, bot, supabase)
        return
    
    # معالج إضافة مجلد
    if user_id in user_states and user_states[user_id].get("state") == "add_folder":
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
        await registry.load()
        del user_states[user_id]
        await event.respond(f"✅ تم إضافة المجلد `{folder_key}`")
        await admin_folders(event, bot, supabase)
        return
    
    # المبرمج AI يتحدث معك
    await event.respond("🧠 **مبرمج AI يفكر...**")
    
    # تحليل الطلب
    prompt = f"""
    أنت مبرمج AI داخل بوت تليجرام. المستخدم يريد:

    {text}

    السياق:
    - المستودع: {GITHUB_REPO}
    - عدد الأزرار: {len(registry._buttons)}
    - عدد المجلدات: {len(registry._folders)}
    
    رد على المستخدم بطريقة مفيدة وواضحة. إذا طلب عرض ملفات GitHub، استخدم الرابط: https://github.com/{GITHUB_REPO}
    إذا طلب إضافة زر، قل له استخدم لوحة التحكم.
    إذا طلب تفسير خطأ، حلله واقترح حلاً.
    
    كن ودوداً واختصارياً.
    """
    
    response = await ask_ai(prompt)
    
    if len(response) > 4000:
        for i in range(0, len(response), 3900):
            await event.respond(response[i:i+3900], parse_mode='md')
    else:
        await event.respond(response, parse_mode='md')

# ============================================
# معالج الكالك باك
# ============================================

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    try:
        data = event.data.decode()
        
        if data.startswith("edit_btn_"):
            button_id = data.replace("edit_btn_", "")
            keyboard = [
                [Button.inline("🗑️ حذف الزر", f"delete_btn_{button_id}")],
                [Button.inline("🔙 رجوع", b"admin_buttons")],
            ]
            await event.edit(f"🔘 **تعديل الزر**\n\nاختر الإجراء:", buttons=keyboard)
            return
        
        if data.startswith("delete_btn_"):
            button_id = data.replace("delete_btn_", "")
            supabase.table("buttons").delete().eq("button_id", button_id).execute()
            await registry.load()
            await event.answer(f"✅ تم حذف الزر", alert=True)
            await admin_buttons(event, bot, supabase)
            return
        
        if data.startswith("edit_folder_"):
            await event.answer("❗ تعديل المجلدات قيد التطوير", alert=True)
            return
        
        if await registry.execute(data, event):
            return
        
        await event.answer("⚠️ الزر غير موجود", alert=True)
        
    except Exception as e:
        log.error(f"Callback error: {e}")
        await event.answer(f"❌ خطأ", alert=True)

# ============================================
# التشغيل الرئيسي
# ============================================

async def create_default_folders():
    folders = [
        ("main", "القائمة الرئيسية", "🏠", "blue", 0),
        ("admin", "لوحة التحكم", "⚙️", "red", 1),
    ]
    for fk, name, emoji, color, order in folders:
        try:
            supabase.table("folders").upsert({
                "folder_key": fk, "display_name": name, "emoji": emoji,
                "color": color, "sort_order": order, "is_active": True
            }, on_conflict="folder_key").execute()
        except:
            pass

async def main():
    log.info("🚀 جاري تشغيل MUSTAFA SHOP v7...")
    
    await create_default_folders()
    await registry.load()
    
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    
    log.info(f"✅ البوت يعمل! @{me.username}")
    log.info(f"📊 {len(registry._buttons)} زر نشط | 📁 {len(registry._folders)} مجلد")
    log.info(f"🐙 GitHub: {GITHUB_REPO}")
    
    await bot.run_until_disconnected()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log.error(f"❌ خطأ فادح: {e}")
        traceback.print_exc()

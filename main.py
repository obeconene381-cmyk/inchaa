import asyncio
import os
import sys
import zipfile
import requests
import re
import shutil
import json
import base64
from playwright.async_api import async_playwright

# ✅ إصلاح إلزامي لـ Playwright على Windows لدعم العمليات الفرعية (Subprocesses)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# ==========================================
# الإعدادات وقراءة متغيرات البيئة
# ==========================================
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8699764033:AAE71GQGj1asu4nVrgnGFQZ-y-IXF4sgNfs")
ADMIN_ID = os.environ.get("ADMIN_ID", "8092953314")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8092953314")
LAB_URL = os.environ.get("LAB_URL", "https://www.skills.google/focuses/41025?parent=catalog")
REGION_OVERRIDE = os.environ.get("REGION_OVERRIDE", "")  
LOG_BOT_TOKEN = os.environ.get("LOG_BOT_TOKEN", BOT_TOKEN) 
LOG_CHANNEL_ID = "-1003781090454"
COOKIES_B64 = os.environ.get("COOKIES_B64", "")
MODE = os.environ.get("MODE", "full_automation")  # 'cloud_run_only' أو 'full_automation'

BUSTER_COMPILED_URL = "https://github.com/dessant/buster/releases/download/v3.1.0/buster_captcha_solver_for_humans-3.1.0-chrome.zip"

ERROR_INDICATORS = [
    "error:",
    "invalid value for [--region]",
    "permission_denied",
    "quota exceeded",
    "quota limit",
    "unavailable",
    "failed to create service",
    "organization policy",
    "resourcelocations violated",
    "constraint constraints/gcp.resourcelocations",
    "deployment failed",
    "badrequest",
    "failed_precondition"
]

# المصفوفة الافتراضية للكوكيز من السكربت الثاني كاحتياط في حال عدم تمرير COOKIES_B64
#
FALLBACK_COOKIES = [
    [
        {
            "domain": ".skills.google",
            "expirationDate": 1813328341.888612,
            "hostOnly": False,
            "httpOnly": False,
            "name": "_ga",
            "path": "/",
            "sameSite": "unspecified",
            "secure": False,
            "session": False,
            "storeId": "0",
            "value": "GA1.1.1438878037.1772447126",
            "id": 1
        },
        {
            "domain": ".skills.google",
            "expirationDate": 1813328342.148713,
            "hostOnly": False,
            "httpOnly": False,
            "name": "_ga_2X30ZRBDSG",
            "path": "/",
            "sameSite": "unspecified",
            "secure": False,
            "session": False,
            "storeId": "0",
            "value": "GS2.1.s1778768307$o186$g1$t1778768342$j25$l0$h0",
            "id": 2
        },
        {
            "domain": ".www.skills.google",
            "expirationDate": 1813005691.77427,
            "hostOnly": False,
            "httpOnly": False,
            "name": "_ga_2X30ZRBDSG",
            "path": "/",
            "sameSite": "unspecified",
            "secure": False,
            "session": False,
            "storeId": "0",
            "value": "deleted",
            "id": 3
        },
        {
            "domain": "www.skills.google",
            "hostOnly": True,
            "httpOnly": True,
            "name": "_cvl-4_1_14_session",
            "path": "/",
            "sameSite": "lax",
            "secure": True,
            "session": True,
            "storeId": "0",
            "value": "UADl8C10SK9IV6LT0eg0wnDT7242PlnkPPjwGVzq8oBr1iA7osJUPHw3DjjoobeukjkoZCI6YTXY0rKbUT0GiCUXmzznLz2SAnZyz618ExiKoOwkCnkYSB2pnNfrElI4GzcCoBwZ6SVkThd78%2BlMPGefICCcYD%2FUxZMArBgY8AaXFW41lmRDRVGNgo0u2d9jmrx3UMhxrQgf%2BgKm4Wnj9cNRXTuIHOWRNSWRcWgL64yWCnsvvftx%2FA9MRrXFBTJrw9jR53ThfENdslsRlyffc%2FmH7w7TGITja4AndW%2FR4CDvURaK5JiTwnitW8Q4BVW0zh0sojTMafKc0Ncwf92ix3bWdLXx7TNY4oLgLFk8MLdm3oMoT17iOos0Zsus4ht5AoXCjFPdE%2FRTXZtR7AwTPFaQJ%2B%2Fmd50z1WD%2Fr%2B49nuWeY7FWDp8c%2BxG4utX6SvQDQp7ByK2khAVuNFjNMdGQeNQ5%2FSCrbTLQFxf4MtJ2GTwIoSc52oE7XkU3ajKYjbv6DrXX0RGoI3LC7JAJPe%2BbQbVr0HTz7xgDoN8mp5jbx58V4VSXBafe5oS2dvqEsGmCr%2B%2Bm6M7v%2BbVvqQeD8OP9NuSvz%2FFiXsPNmIp8f1e9tKxj8fNiOV8CUInIk5G09s3P8Sk2tEQgRSaf8yizNusouVnfrnuIk7pogWnXF%2FApNB%2Bu1KAZ8uCYdCvavHCLABfD1GTTlgZkpnVHKCpigUu4JbCg4LieO3dzmlVAEhSkC2fv9%2BKK1yKOMcj%2BJyGuWQI3ESAZVTVUKC%2BcUW%2B%2BrcOE%2Fe6V6iRL6%2BRDS7FYd5GpuH5phdWFcYuEM11EcT%2FfONCqlwuhibQ%2BhVi3095JNCg9ICXTcSyjtZDuScPSd%2F9iPCTGAiNddRoSa2ujfeaNkrf93Sf6u%2BrNLyKrfoFk2V1ZCfLklDw57pjUB2tJ3dGv8ME8Rgzbpt0DkoAT1BJfNuaxxkNcCgX1sjFC%2Brv%2FOIXrxBXP3zQrZQXDlqiqDOPNnDpam3dUF2QAzFPmFrBtknbcftJc--%2B76qjyj6rYlh%2B9jP--VVRm9fk18HK4qMLe0HeQuA%3D%3D",
            "id": 4
        },
        {
            "domain": "www.skills.google",
            "expirationDate": 1813328299.094363,
            "hostOnly": True,
            "httpOnly": False,
            "name": "auto_accept_organization",
            "path": "/",
            "sameSite": "lax",
            "secure": True,
            "session": False,
            "storeId": "0",
            "value": "",
            "id": 5
        },
        {
            "domain": "www.skills.google",
            "expirationDate": 1810304335,
            "hostOnly": True,
            "httpOnly": False,
            "name": "browser.timezone",
            "path": "/",
            "sameSite": "unspecified",
            "secure": False,
            "session": False,
            "storeId": "0",
            "value": "Africa/Algiers",
            "id": 6
        },
        {
            "domain": "www.skills.google",
            "expirationDate": 1794302018,
            "hostOnly": True,
            "httpOnly": False,
            "name": "g_state",
            "path": "/",
            "sameSite": "unspecified",
            "secure": False,
            "session": False,
            "storeId": "0",
            "value": "{\"i_l\":0,\"i_ll\":1778750018786,\"i_e\":{\"enable_itp_optimization\":21},\"i_b\":\"Tx5aWTcjyGMaRuTm8R096WUmqzOhJRl4mPhhx0cAy9Y\",\"i_et\":1776159491027}",
            "id": 7
        },
        {
            "domain": "www.skills.google",
            "hostOnly": True,
            "httpOnly": False,
            "name": "user.expires_at",
            "path": "/",
            "sameSite": "lax",
            "secure": True,
            "session": True,
            "storeId": "0",
            "value": "eyJfcmFpbHMiOnsibWVzc2FnZSI6IklqSXdNall0TURVdE1UUlVNVEk2TVRnNk16TXVPVEl3TFRBME9qQXdJZz09IiwiZXhwIjpudWxsLCJwdXIiOiJjb29raWUudXNlci5leHBpcmVzX2F0In19--6a89c33363f8b5b86cb51505e8cd30601a63cc41",
            "id": 8
        },
        {
            "domain": "www.skills.google",
            "hostOnly": True,
            "httpOnly": False,
            "name": "user.id",
            "path": "/",
            "sameSite": "lax",
            "secure": True,
            "session": True,
            "storeId": "0",
            "value": "eyJfcmFpbHMiOnsibWVzc2FnZSI6Ik1UTTNOVE01TmpjMyIsImV4cCI6bnVsbCwicHVyIjoiY29va2llLnVzZXIuaWQifX0%3D--3977f98dc1c6fffcb49a4353fc4b1b054fa05451",
            "id": 9
        }
    ]
]

try:
    if COOKIES_B64.strip():
        MY_COOKIES = json.loads(base64.b64decode(COOKIES_B64).decode("utf-8"))
    else:
        MY_COOKIES = FALLBACK_COOKIES
except Exception:
    MY_COOKIES = FALLBACK_COOKIES

class LoginRequiredError(Exception): pass

# ==========================================
# دوال الإرسال والتلغرام المشتركة
# ==========================================
def send_telegram_msg(chat_id, text):
    if BOT_TOKEN and chat_id:
        try: requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
        except: pass

def send_log_to_channel(text):
    token_to_use = LOG_BOT_TOKEN if LOG_BOT_TOKEN else BOT_TOKEN
    if token_to_use and LOG_CHANNEL_ID:
        try: requests.post(f"https://api.telegram.org/bot{token_to_use}/sendMessage", json={"chat_id": LOG_CHANNEL_ID, "text": text})
        except: pass

def send_telegram_photo(chat_id, photo_path, caption):
    if BOT_TOKEN and chat_id:
        try:
            with open(photo_path, "rb") as photo:
                requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto", data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}, files={"photo": photo})
        except: send_telegram_msg(chat_id, caption)

def send_tg(msg, img=None):
    """جسر توافقية لإرسال الرسائل للمستخدم النهائي متطابق مع السكربت الثاني"""
    if img: send_telegram_photo(CHAT_ID, img, msg)
    else: send_telegram_msg(CHAT_ID, msg)

# ==========================================
# دوال التحكم والـ UI لقسم الكلاود شيل (السورس 1)
# ==========================================
async def click_button_by_text_anywhere(page, text, exact=True, timeout_loop=120, post_click_wait=3):
    pattern = re.compile(rf"^\s*{re.escape(text)}\s*$", re.I) if exact else re.compile(re.escape(text), re.I)
    async def _post_click_stabilize():
        try: await page.wait_for_load_state("domcontentloaded", timeout=2000)
        except: pass
        await asyncio.sleep(post_click_wait)
    for _ in range(timeout_loop):
        for target in [page] + list(page.frames):
            try:
                btns = target.get_by_role("button", name=pattern)
                for i in range(await btns.count() - 1, -1, -1):
                    b = btns.nth(i)
                    if await b.is_visible() and await b.is_enabled():
                        await b.scroll_into_view_if_needed(timeout=1000); await b.click(timeout=3000, force=True); await _post_click_stabilize(); return True
            except: pass
        await asyncio.sleep(1)
    return False

async def try_click_terms_checkbox(page):
    terms_regex = re.compile(r"i agree to the google cloud platform", re.I)
    for _ in range(2):
        for target in [page] + list(page.frames):
            try:
                cbs = target.get_by_role("checkbox")
                for i in range(await cbs.count()):
                    cb = cbs.nth(i)
                    if await cb.is_visible(): await cb.click(timeout=1500, force=True); return True
                locs = target.locator("label, div, span, [role='checkbox']").filter(has_text=terms_regex)
                for i in range(await locs.count()):
                    el = locs.nth(i)
                    if await el.is_visible(): await el.click(timeout=1500, force=True); return True
            except: pass
        await asyncio.sleep(0.5)
    return False

async def get_cloudshell_frame(page):
    for _ in range(60):
        for f in page.frames:
            if "shell.cloud.google.com" in (f.url or "").lower() or "embeddedcloudshell" in (f.url or "").lower(): return f
        await asyncio.sleep(1)
    return None

async def wait_for_cloud_shell_prompt(page, timeout_loop=180):
    prompt_patterns = [r"\$\s*$", r"cloudshell:~", r"student_.*@cloudshell", r"welcome to cloud shell"]
    for _ in range(timeout_loop):
        f = await get_cloudshell_frame(page)
        if f:
            try:
                txt = await f.inner_text("body")
                if any(re.search(pat, txt, re.I | re.M) for pat in prompt_patterns): return True
            except: pass
        await asyncio.sleep(1)
    return False

async def focus_terminal_near_prompt(page, timeout_loop=60):
    for _ in range(timeout_loop):
        f = await get_cloudshell_frame(page)
        if f:
            for sel in ["textarea.xterm-helper-textarea", "textarea", "div.xterm", "div.xterm-screen", "canvas"]:
                try:
                    loc = f.locator(sel).first
                    if await loc.count() > 0 and await loc.is_visible():
                        await loc.click(timeout=1500, force=True)
                        box = await loc.bounding_box()
                        if box: await page.mouse.click(box["x"] + 40, box["y"] + max(10, box["height"] - 20))
                        return True
                except: pass
        await asyncio.sleep(1)
    return False

async def paste_command_and_run(page, command, timeout_verify=5):
    await focus_terminal_near_prompt(page, timeout_loop=30)
    f = await get_cloudshell_frame(page)
    async def _paste_into_focused():
        try:
            f2 = await get_cloudshell_frame(page)
            if f2:
                await f2.evaluate("""(text) => {
                    const ta = document.querySelector('textarea.xterm-helper-textarea');
                    if (!ta) throw new Error('no xterm-helper-textarea');
                    ta.focus();
                    const dt = new DataTransfer();
                    dt.setData('text/plain', text);
                    const ev = new ClipboardEvent('paste', { clipboardData: dt, bubbles: true });
                    ta.dispatchEvent(ev);
                }""", command)
                return
        except Exception:
            pass
        await page.keyboard.insert_text(command)
        
    if f:
        try:
            ta = f.locator("textarea.xterm-helper-textarea").first
            if await ta.count() > 0:
                await ta.focus(); await asyncio.sleep(0.2); await _paste_into_focused()
            else: await _paste_into_focused()
        except Exception: await _paste_into_focused()
    else: await _paste_into_focused()
        
    await asyncio.sleep(0.8)
    try:
        if f:
            try:
                ta = f.locator("textarea.xterm-helper-textarea").first
                if await ta.count() > 0: await ta.focus(); await asyncio.sleep(0.2)
            except Exception: pass
        await page.keyboard.press("Enter")
        return True
    except Exception: return False

async def wait_for_yes_no_prompt(page, timeout_loop=3):
    patterns = [r"\[y\/n\]", r"\(y\/n\)", r"\[y\/N\]", r"Do you want to continue", r"continue\?\s*$"]
    for _ in range(timeout_loop):
        f = await get_cloudshell_frame(page)
        for target in ([f] if f else []) + [fr for fr in page.frames if fr != f] + [page]:
            try:
                txt = await target.inner_text("body")
                if any(re.search(p, txt, re.I | re.M) for p in patterns): return True
            except: pass
        await asyncio.sleep(1)
    return False

async def type_short_answer_only(page, answer_text="y"):
    await focus_terminal_near_prompt(page, timeout_loop=20)
    f = await get_cloudshell_frame(page)
    try:
        if f and await f.locator("textarea.xterm-helper-textarea").first.count() > 0:
            await f.locator("textarea.xterm-helper-textarea").first.focus(); await asyncio.sleep(0.2); await f.locator("textarea.xterm-helper-textarea").first.type(answer_text, delay=50)
        else: await page.keyboard.insert_text(answer_text)
    except: await page.keyboard.type(answer_text, delay=50)
    await asyncio.sleep(0.4)
    return True

# ==========================================
# دوال أتمتة Qwiklabs والكابتشا (السورس 2)
# ==========================================
def fix_cookies_for_playwright(cookies):
    valid_samesite = ["Strict", "Lax", "None"]
    cleaned_cookies = []
    for cookie in cookies:
        c = cookie.copy()
        if c.get("sameSite") not in valid_samesite:
            if "sameSite" in c: del c["sameSite"] 
        cleaned_cookies.append(c)
    return cleaned_cookies

async def setup_compiled_buster():
    ext_dir = os.path.abspath("buster_compiled_ext")
    if os.path.exists(ext_dir): shutil.rmtree(ext_dir)
    os.makedirs(ext_dir)
    zip_path = "buster_ready.zip"
    try:
        send_tg("📥 جاري تحميل النسخة الرسمية للإضافة...")
        r = requests.get(BUSTER_COMPILED_URL, timeout=30)
        with open(zip_path, "wb") as f: f.write(r.content)
        with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(ext_dir)
        os.remove(zip_path)
        send_tg("✅ تم تجهيز الإضافة بنجاح")
        return ext_dir
    except Exception as e:
        send_tg(f"❌ فشل تحميل الإضافة: {e}")
        return None

async def human_click(page, locator):
    try:
        await locator.scroll_into_view_if_needed()
        await locator.click(force=True, delay=200)
        return True
    except: return False

async def dismiss_credits_modal(page):
    try:
        btn = page.get_by_role("button", name=re.compile(r"Dismiss", re.I))
        if await btn.count() > 0 and await btn.first.is_visible():
            await btn.first.click(); await asyncio.sleep(2); return True
    except: pass
    return False

async def click_start_lab_button(page):
    pattern = re.compile(r"Start\s*Lab", re.IGNORECASE)
    for _ in range(30):
        try:
            btn = page.get_by_role("button", name=pattern).first
            if await btn.is_visible():
                await btn.click(force=True)
                send_tg("✅ تم الضغط على Start Lab")
                return True
        except: pass
        await asyncio.sleep(1)
    return False

async def click_captcha_checkbox(page):
    send_tg("🤛 البحث عن مربع الكابتشا الرئيسي...")
    await asyncio.sleep(3)
    iframes = await page.locator('iframe[title*="reCAPTCHA"]').all()
    for iframe in iframes:
        try:
            frame_content = iframe.content_frame
            checkbox = frame_content.locator('.recaptcha-checkbox-border').first
            if await checkbox.is_visible():
                await human_click(page, checkbox)
                send_tg("✅ تم الضغط على مربع أنا لست برنامج روبوت")
                return True
        except: continue
    return False

async def click_launch_with_credits_aggressive(page):
    send_tg("⏳ جاري البحث عن زر Launch with 5 Credits...")
    for _ in range(15):
        try:
            js_success = await page.evaluate('''() => {
                let elements = Array.from(document.querySelectorAll('*'));
                let target = elements.find(e => e.textContent && e.textContent.trim() === 'Launch with 5 Credits');
                if(target) { target.click(); return true; }
                return false;
            }''')
            if js_success:
                send_tg("✅ تم الضغط على Launch with 5 Credits بنجاح (طريقة JS)!")
                return True

            xpath_locator = page.locator("xpath=//*[text()='Launch with 5 Credits']").first
            if await xpath_locator.is_visible():
                await xpath_locator.click(force=True)
                send_tg("✅ تم الضغط على Launch with 5 Credits بنجاح (طريقة XPath)!")
                return True

            text_locator = page.locator("text=Launch with 5 Credits").first
            if await text_locator.is_visible():
                await text_locator.click(force=True)
                send_tg("✅ تم الضغط على Launch with 5 Credits بنجاح (طريقة Text)!")
                return True
        except Exception: pass 
        await asyncio.sleep(1)

    screenshot_path = "debug_credits_button.png"
    await page.screenshot(path=screenshot_path)
    send_tg("⚠️ ما زال يعجز عن إيجاد الزر، انظر الصورة:", screenshot_path)
    return False

async def get_cloud_console_link(page):
    send_tg("⏳ جاري انتظار ظهور زر 'Open Google Cloud console' واستخراج الرابط...")
    try:
        btn = page.locator("text=Open Google Cloud console").first
        await btn.wait_for(state="visible", timeout=15000)
        link = await btn.get_attribute("href")
        
        if not link:
            link = await page.evaluate('''() => {
                let elements = Array.from(document.querySelectorAll('*'));
                let target = elements.find(e => e.textContent && e.textContent.includes('Open Google Cloud console'));
                if (target) {
                    return target.getAttribute('href') || 
                           (target.parentElement && target.parentElement.getAttribute('href')) || 
                           (target.shadowRoot && target.shadowRoot.querySelector('a') && target.shadowRoot.querySelector('a').getAttribute('href'));
                }
                return null;
            }''')

        if link:
            success_msg = f"🎉 مبروك! تم بدء اللاب بنجاح.\n\n🔗 رابط الكونسول:\n{link}"
            send_tg(success_msg)
            return link
        else:
            send_tg("⚠️ ظهر الزر لكن لم نتمكن من سحب الرابط (href) منه.")
            
    except Exception as e:
        error_msg = "⚠️ فشل العثور على الزر بعد الانتظار."
        try:
            await page.screenshot(path="debug_console_link.png")
            send_tg(error_msg, "debug_console_link.png")
        except: send_tg(error_msg + f"\nالخطأ: {e}")
    return None

async def method_1_direct_click(page):
    send_tg("🎯 محاولة النقر المباشر على الشخص الأصفر...")
    try:
        challenge_iframe = page.frame_locator('iframe[src*="recaptcha/api2/bframe"]').first
        audio_btn = challenge_iframe.locator('#recaptcha-audio-button')
        if await audio_btn.is_visible(timeout=5000):
            await audio_btn.click(force=True); await asyncio.sleep(2)
            send_tg("🔊 تم التحويل لتحدي الصوت")
        
        buster_btn = challenge_iframe.locator('.help-button-holder, button[title*="Solve the challenge"], button[title*="Buster"]').first
        if await buster_btn.is_visible(timeout=5000):
            await buster_btn.click(force=True)
            send_tg("✅ تم الضغط على الشخص الأصفر بنجاح!")
            await asyncio.sleep(8)
            
            try:
                verify_btn = challenge_iframe.locator('#recaptcha-verify-button')
                is_disabled = await verify_btn.evaluate("node => node.disabled")
                if not is_disabled and await verify_btn.is_visible(): await verify_btn.evaluate("node => node.click()")
            except Exception: pass 
            return True
        else: send_tg("⚠️ لم يتم العثور على زر الشخص الأصفر، يبدو أن الإضافة لم تظهر.")
    except Exception as e: send_tg(f"❌ فشل أثناء محاولة النقر: {e}")
    return False

async def try_all_buster_methods(page):
    send_tg("🚀 بدء عملية حل الكابتشا...")
    if await page.locator('.recaptcha-checkbox-checked').is_visible():
        send_tg("✅ تم الحل بالفعل مبكراً!")
        return True
    
    if not await page.locator('iframe[src*="recaptcha/api2/bframe"]').is_visible():
        send_tg("🔄 إعادة فتح الكابتشا لأنها اختفت...")
        await click_captcha_checkbox(page); await asyncio.sleep(3)
    
    success = await method_1_direct_click(page)
    return success

# ==========================================
# المعالج الرئيسي وإدارة تدفق الأتمتة المشترك
# ==========================================
async def run_automation():
    send_telegram_msg(CHAT_ID, "✅ تم بدء العمل في السيرفر، يرجى الانتظار...")
    
    deploy_cmd_template = (
        "gcloud run deploy my-app \\\n"
        "  --project=$DEVSHELL_PROJECT_ID \\\n"
        "  --image=docker.io/nkka404/vless-ws:latest \\\n"
        "  --platform=managed \\\n"
        "  --allow-unauthenticated \\\n"
        "  --port=8080 \\\n"
        "  --cpu=2 \\\n"
        "  --memory=4Gi \\\n"
        "  --concurrency=1000 \\\n"
        "  --timeout=3600 \\\n"
        "  --min-instances=2 \\\n"
        "  --max-instances=8 \\\n"
        "  --execution-environment=gen2 \\\n"
        "  --cpu-boost \\\n"
        "  --region={REGION}"
    )

    if REGION_OVERRIDE and REGION_OVERRIDE.strip():
        regions = [REGION_OVERRIDE.strip()]
    else:
        regions = ["europe-west12", "europe-west1", "europe-west4", "us-west1", "us-central1", "us-east1"]
    
    deploy_wait_loops = 20
    ext_path = None

    if MODE == "full_automation":
        ext_path = await setup_compiled_buster()
        if not ext_path: return

    user_data_dir = os.path.abspath("chrome_profile")
    if os.path.exists(user_data_dir):
        try: shutil.rmtree(user_data_dir)
        except: pass

    async with async_playwright() as p:
        # إعداد المتصفح بناءً على وضع التشغيل المطلوب
        if MODE == "full_automation":
            context = await p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                no_viewport=True, 
                args=[
                    f"--disable-extensions-except={ext_path}", 
                    f"--load-extension={ext_path}", 
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--start-maximized" 
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = context.pages[0]
        else:
            # وضع كونسول مباشر خفي وسريع (السورس 1)
            browser = await p.chromium.launch(headless=True, args=["--lang=en-US", "--no-sandbox", "--disable-gpu"])
            context = await browser.new_context(locale="en-US", viewport={'width': 1280, 'height': 720})
            page = await context.new_page()

        try:
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            """)

            console_link = None

            if MODE == "full_automation":
                raw_cookies = MY_COOKIES[0] if isinstance(MY_COOKIES[0], list) else MY_COOKIES
                cleaned_cookies = fix_cookies_for_playwright(raw_cookies)
                await context.add_cookies(cleaned_cookies)
                
                await page.goto(LAB_URL, timeout=300000, wait_until="domcontentloaded")
                await asyncio.sleep(4)
                await dismiss_credits_modal(page)
                
                if await click_start_lab_button(page):
                    await asyncio.sleep(5)
                    if await click_captcha_checkbox(page):
                        await asyncio.sleep(3)
                        await try_all_buster_methods(page)
                        await asyncio.sleep(3) 
                    else:
                        send_tg("ملاحظة: لم يظهر مربع الكابتشا.")
                    
                    is_launched = await click_launch_with_credits_aggressive(page)
                    if is_launched:
                        console_link = await get_cloud_console_link(page)
                else: raise Exception("فشل بدء اللاب والنقر على زر Start Lab الرئيسي.")
            else:
                console_link = LAB_URL

            # الانتقال لمرحلة التحكم بالكونسول ونشر الخدمة (السورس 1)
            if console_link:
                await page.goto(console_link, timeout=300000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
                
                if await page.locator("input#identifierId").first.count() > 0 and await page.locator("input#identifierId").first.is_visible(): raise LoginRequiredError()
                if await page.locator("text='Use your Google Account'").first.count() > 0 and await page.locator("text='Use your Google Account'").first.is_visible(): raise LoginRequiredError()
                
                clicked_understand = await click_button_by_text_anywhere(page, "I understand", exact=True, timeout_loop=60, post_click_wait=0)
                if clicked_understand: await asyncio.sleep(10) 
                
                await try_click_terms_checkbox(page)
                await asyncio.sleep(2)
                await click_button_by_text_anywhere(page, "Agree and continue", exact=True, timeout_loop=60)
                await asyncio.sleep(3)
                
                for sel in ['button[aria-label*="Activate Cloud Shell"]', 'button[title*="Cloud Shell"]']:
                    try:
                        loc = page.locator(sel).first
                        if await loc.count() > 0 and await loc.is_visible(): await loc.click(timeout=3000, force=True); break
                    except: pass
                    
                await asyncio.sleep(5) 
                await click_button_by_text_anywhere(page, "Continue", exact=True, timeout_loop=60)
                await click_button_by_text_anywhere(page, "Authorize", exact=True, timeout_loop=60)
                
                if await wait_for_cloud_shell_prompt(page):
                    url_re = re.compile(r"Service URL:\s*(https://[a-zA-Z0-9.-]+\.run\.app)", re.I)
                    
                    for region in regions:
                        try:
                            await focus_terminal_near_prompt(page, timeout_loop=5)
                            await page.keyboard.press("Control+C")
                            await asyncio.sleep(1)
                            await paste_command_and_run(page, "clear")
                            await asyncio.sleep(2)
                        except: pass

                        cmd = deploy_cmd_template.replace("{REGION}", region)
                        await paste_command_and_run(page, cmd)
                        
                        y_sent = False
                        for step in range(deploy_wait_loops):
                            f = await get_cloudshell_frame(page)
                            if not f: 
                                await asyncio.sleep(3)
                                continue
                            
                            txt = await f.inner_text("body")
                            txt_lower = txt.lower()
                            
                            if not y_sent and await wait_for_yes_no_prompt(page, timeout_loop=1):
                                await type_short_answer_only(page, "y")
                                try: await page.keyboard.press("Enter")
                                except: pass
                                y_sent = True
                            
                            match = url_re.search(txt)
                            if match:
                                final_url = match.group(1)
                                send_log_to_channel(f"#DONE|{CHAT_ID}|{final_url}")
                                send_telegram_msg(CHAT_ID, f"🎉 <b>تم النشر بنجاح!</b>\nالرابط: <code>{final_url}</code>\nالمنطقة: {region}")
                                return
                            
                            if any(indicator in txt_lower for indicator in ERROR_INDICATORS):
                                print(f"Failed in {region}, moving to next...")
                                break
                                
                            await asyncio.sleep(3)
                    
                    raise Exception("انتهت المحاولات: فشل النشر في المنطقة المطلوبة أو في جميع المناطق المتاحة.")
            else:
                raise Exception("رابط كونسول السحابة فارغ أو لم يتم استخراجه.")

        except LoginRequiredError:
            send_telegram_msg(CHAT_ID, "⚠️ <b>الرابط منتهي ويطلب تسجيل الدخول!</b>\nتم إلغاء طلبك، يمكنك المحاولة برابط جديد.")
            send_log_to_channel(f"#FAILED|{CHAT_ID}") 
        
        except Exception as e:
            error_msg = str(e)
            send_telegram_msg(CHAT_ID, "❌ <b>حدث خطأ أثناء المعالجة أو فشل النشر!</b>\nتم إلغاء طلبك.")
            send_log_to_channel(f"#FAILED|{CHAT_ID}") 
            try: 
                await page.screenshot(path="error.png", full_page=True)
                if ADMIN_ID:
                    send_telegram_photo(ADMIN_ID, "error.png", f"🔴 خطأ لمستخدم {CHAT_ID}:\n{error_msg[:150]}")
            except: pass
        finally:
            if MODE == "full_automation":
                await context.close()
            else:
                await browser.close()

if __name__ == "__main__":
    if LAB_URL:
        asyncio.run(run_automation())

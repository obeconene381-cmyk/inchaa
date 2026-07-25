import asyncio
import os
import sys  
import zipfile
import requests
import re
import shutil
import json
import base64
from datetime import datetime
from playwright.async_api import async_playwright

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# البوت الأساسي: يجلب التوكن من السيكرتس فقط لإرسال رسائل النجاح والفشل للمستخدم والأدمن
BOT_TOKEN = os.environ.get("BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", os.environ.get("bot_token", "")))
CHAT_ID = os.environ.get("CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", os.environ.get("chat_id", "5813081202")))
ADMIN_ID = os.environ.get("ADMIN_ID", os.environ.get("admin_id", "5813081202"))
LAB_URL = os.environ.get("LAB_URL", "https://www.skills.google/focuses/41025?parent=catalog")
REGION_OVERRIDE = os.environ.get("REGION_OVERRIDE", "")  

# بوت اللوجات: يستخدم التوكن الخاص بالقناة افتراضياً لإرسال التقارير واللوجات
LOG_BOT_TOKEN = os.environ.get("LOG_BOT_TOKEN", "8368522367:AAFWsCe-jbFNc-ljR1diGh2_1-6nLAk7BlA") 
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", os.environ.get("log_channel_id", "-1004367699466"))
COOKIES_B64 = os.environ.get("COOKIES_B64", "")
MODE = os.environ.get("MODE", "full_automation")  
GCP_USER = os.environ.get("GCP_USER", "")
GCP_PASS = os.environ.get("GCP_PASS", "")
MIN_INSTANCES = os.environ.get("MIN_INSTANCES", "2")
MAX_INSTANCES = os.environ.get("MAX_INSTANCES", "8")

BUSTER_COMPILED_URL = "https://github.com/dessant/buster/releases/download/v3.1.0/buster_captcha_solver_for_humans-3.1.0-chrome.zip"

ERROR_INDICATORS = [
    "error:", "invalid value for [--region]", "permission_denied", "quota exceeded",
    "quota limit", "unavailable", "failed to create service", "organization policy",
    "resourcelocations violated", "constraint constraints/gcp.resourcelocations",
    "deployment failed", "badrequest", "failed_precondition"
]

try:
    if COOKIES_B64.strip():
        MY_COOKIES = json.loads(base64.b64decode(COOKIES_B64).decode("utf-8"))
    else:
        MY_COOKIES = []
except Exception:
    MY_COOKIES = []

def send_tg(msg, img=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/"
    try:
        if img and os.path.exists(img):
            with open(img, "rb") as f:
                requests.post(url + "sendPhoto", data={"chat_id": CHAT_ID, "caption": msg, "parse_mode": "HTML"}, files={"photo": f}, timeout=30)
        else: 
            requests.post(url + "sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=30)
    except: pass

def send_admin(msg, img=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/"
    try:
        if img and os.path.exists(img):
            with open(img, "rb") as f:
                requests.post(url + "sendPhoto", data={"chat_id": ADMIN_ID, "caption": msg, "parse_mode": "HTML"}, files={"photo": f}, timeout=30)
        else: 
            requests.post(url + "sendMessage", json={"chat_id": ADMIN_ID, "text": msg, "parse_mode": "HTML"}, timeout=30)
    except: pass

def get_server_ip():
    for url in ["https://api.ipify.org?format=json", "https://api.ip.sb/jsonip", "https://httpbin.org/ip"]:
        try:
            r = requests.get(url, timeout=8)
            data = r.json()
            ip = data.get("ip") or data.get("origin") or data.get("IP")
            if ip: return ip.strip()
        except: continue
    return "غير معروف"

def send_log_to_channel(text):
    if LOG_BOT_TOKEN and LOG_CHANNEL_ID:
        try: requests.post(f"https://api.telegram.org/bot{LOG_BOT_TOKEN}/sendMessage", json={"chat_id": LOG_CHANNEL_ID, "text": text})
        except: pass

def retry_workflow():
    gh_token = os.environ.get("PAT_TOKEN") or os.environ.get("GITHUB_TOKEN")
    gh_repo = os.environ.get("GITHUB_REPOSITORY")
    if gh_token and gh_repo:
        url = f"https://api.github.com/repos/{gh_repo}/actions/workflows/deploy.yml/dispatches"
        headers = {"Authorization": f"token {gh_token}", "Accept": "application/vnd.github.v3+json"}
        inputs = {
            'cookies_b64': os.environ.get("COOKIES_B64", ""), 'lab_url': LAB_URL,
            'chat_id': str(CHAT_ID), 'bot_token': BOT_TOKEN, 'admin_id': str(ADMIN_ID),
            'log_channel_id': LOG_CHANNEL_ID, 'mode': MODE,
            'min_instances': str(MIN_INSTANCES), 'max_instances': str(MAX_INSTANCES),
            'gcp_user': GCP_USER, 'gcp_pass': GCP_PASS
        }
        try:
            res = requests.post(url, headers=headers, json={'ref': 'main', 'inputs': inputs}, timeout=15)
            return res.status_code == 204
        except: pass
    return False

# ==========================================
# دوال الأتمتة المساعدة
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
                        await b.scroll_into_view_if_needed(timeout=1000)
                        await b.click(timeout=3000, force=True)
                        await _post_click_stabilize()
                        return True
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
        except Exception: pass
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
            await f.locator("textarea.xterm-helper-textarea").first.focus()
            await asyncio.sleep(0.2)
            await f.locator("textarea.xterm-helper-textarea").first.type(answer_text, delay=50)
        else: await page.keyboard.insert_text(answer_text)
    except: await page.keyboard.type(answer_text, delay=50)
    await asyncio.sleep(0.4)
    return True

async def handle_google_login(page, email, password):
    try:
        email_input = page.locator("input#identifierId").first
        if await email_input.count() > 0 and await email_input.is_visible():
            await email_input.fill(email)
            await page.keyboard.press("Enter")
            await asyncio.sleep(4)
        pass_input = page.locator("input[type='password']").first
        if await pass_input.count() > 0 and await pass_input.is_visible():
            await pass_input.fill(password)
            await page.keyboard.press("Enter")
            await asyncio.sleep(6)
    except Exception: pass

async def extract_credentials(page):
    try:
        email, password = None, None
        email_el = page.locator("[data-credential='username'], #student-username, #content-credentials-email").first
        if await email_el.count() > 0: email = (await email_el.inner_text()).strip()
        pass_el = page.locator("[data-credential='password'], #student-password, #content-credentials-password").first
        if await pass_el.count() > 0: password = (await pass_el.inner_text()).strip()
        return email, password
    except: return None, None

def fix_cookies_for_playwright(cookies):
    valid_samesite = ["Strict", "Lax", "None"]
    cleaned = []
    for cookie in cookies:
        c = cookie.copy()
        if c.get("sameSite") not in valid_samesite:
            if "sameSite" in c: del c["sameSite"]
        cleaned.append(c)
    return cleaned

async def setup_compiled_buster():
    ext_dir = os.path.abspath("buster_compiled_ext")
    if os.path.exists(ext_dir): shutil.rmtree(ext_dir)
    os.makedirs(ext_dir)
    zip_path = "buster_ready.zip"
    try:
        r = requests.get(BUSTER_COMPILED_URL, timeout=60)
        with open(zip_path, "wb") as f: f.write(r.content)
        with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(ext_dir)
        os.remove(zip_path)
        return ext_dir
    except Exception as e:
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
                return True
        except: pass
        await asyncio.sleep(1)
    return False

async def check_recaptcha_block(page):
    challenge_iframe = page.frame_locator('iframe[src*="recaptcha/api2/bframe"]').first
    try:
        if await challenge_iframe.locator("body").count() > 0:
            iframe_text = await challenge_iframe.locator("body").inner_text()
            if "Try again later" in iframe_text or "automated queries" in iframe_text: return True
    except: pass
    return False

async def click_captcha_checkbox(page):
    await asyncio.sleep(3)
    iframes = await page.locator('iframe[title*="reCAPTCHA"]').all()
    for iframe in iframes:
        try:
            frame_content = iframe.content_frame
            checkbox = frame_content.locator('.recaptcha-checkbox-border').first
            if await checkbox.is_visible():
                await human_click(page, checkbox)
                return True
        except: continue
    return False

async def click_launch_with_credits_aggressive(page):
    credits_pattern = re.compile(r"Launch\s+with\s+\d+\s+Credit", re.IGNORECASE)
    for attempt in range(15):
        try:
            js_clicked = await page.evaluate('''() => {
                let elements = Array.from(document.querySelectorAll('*'));
                let target = elements.find(e => e.textContent && /Launch\s+with\s+\d+\s+Credit/i.test(e.textContent.trim()));
                if(target) { target.click(); return true; }
                return false;
            }''')
            if js_clicked:
                await asyncio.sleep(2.5)
                is_still_visible = await page.evaluate('''() => {
                    let elements = Array.from(document.querySelectorAll('*'));
                    let target = elements.find(e => e.textContent && /Launch\s+with\s+\d+\s+Credit/i.test(e.textContent.trim()));
                    if (target) {
                        const rect = target.getBoundingClientRect();
                        return rect.width > 0 && rect.height > 0 && window.getComputedStyle(target).display !== 'none';
                    }
                    return false;
                }''')
                if not is_still_visible: return True

            xpath_locator = page.locator("xpath=//*[contains(text(), 'Launch with') and contains(text(), 'Credit')]").first
            if await xpath_locator.is_visible():
                await xpath_locator.click(force=True)
                await asyncio.sleep(2.5)
                return True

            text_locator = page.get_by_role("button", name=credits_pattern).first
            if await text_locator.is_visible():
                await text_locator.click(force=True)
                await asyncio.sleep(2.5)
                return True

        except Exception: pass
        await asyncio.sleep(1)

    try:
        await page.screenshot(path="failed_launch.png")
        send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: فشل إيجاد زر Launch with Credits", "failed_launch.png")
    except:
        send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n❌ فشل إيجاد زر Launch with Credits")
    return False

async def get_cloud_console_link(page):
    for attempt in range(18):
        try:
            btn = page.locator("text=Open Google Cloud console").first
            if await btn.count() > 0 and await btn.is_visible():
                link = await btn.get_attribute("href")
                if link: return link

            btn2 = page.get_by_role("link", name=re.compile(r"Open Google Cloud console", re.I)).first
            if await btn2.count() > 0 and await btn2.is_visible():
                link = await btn2.get_attribute("href")
                if link: return link

            link = await page.evaluate("""() => {
                const all = Array.from(document.querySelectorAll('a, button, [role=link]'));
                const el = all.find(e => e.textContent && e.textContent.includes('Open Google Cloud console'));
                if (el) return el.getAttribute('href') || el.href || null;
                return null;
            }""")
            if link: return link
        except Exception: pass
        await asyncio.sleep(10)

    try:
        await page.screenshot(path="failed_console_link.png")
        send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: فشل إيجاد زر الكونسول بعد 3 دقائق", "failed_console_link.png")
    except:
        send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n❌ فشل إيجاد زر الكونسول بعد 3 دقائق")
    return None

async def method_1_direct_click(page):
    try:
        if await check_recaptcha_block(page): raise Exception("RECAPTCHA_BLOCKED")
        challenge_iframe = page.frame_locator('iframe[src*="recaptcha/api2/bframe"]').first
        audio_btn = challenge_iframe.locator('#recaptcha-audio-button')
        if await audio_btn.is_visible(timeout=5000):
            await audio_btn.click(force=True); await asyncio.sleep(2)
        if await check_recaptcha_block(page): raise Exception("RECAPTCHA_BLOCKED")
        buster_btn = challenge_iframe.locator('.help-button-holder, button[title*="Solve the challenge"], button[title*="Buster"]').first
        for _ in range(4):
            if await check_recaptcha_block(page): raise Exception("RECAPTCHA_BLOCKED")
            if await buster_btn.is_visible(timeout=2000):
                await buster_btn.click(force=True); await asyncio.sleep(1.5)
            else: break
        await asyncio.sleep(4)
        if await check_recaptcha_block(page): raise Exception("RECAPTCHA_BLOCKED")
        try:
            verify_btn = challenge_iframe.locator('#recaptcha-verify-button')
            if not await verify_btn.evaluate("node => node.disabled") and await verify_btn.is_visible():
                await verify_btn.evaluate("node => node.click()")
        except Exception: pass
        return True
    except Exception as e:
        if str(e) == "RECAPTCHA_BLOCKED": raise e
    return False

async def try_all_buster_methods(page):
    if await page.locator('.recaptcha-checkbox-checked').is_visible(): return True
    if await check_recaptcha_block(page): raise Exception("RECAPTCHA_BLOCKED")
    if not await page.locator('iframe[src*="recaptcha/api2/bframe"]').is_visible():
        await click_captcha_checkbox(page); await asyncio.sleep(3)
    return await method_1_direct_click(page)

async def detect_robot_block(page):
    """كشف حظر الروبوت — يتحقق فقط من النصوص الصريحة، لا يعتبر كل رسالة خطأ"""
    block_patterns = [
        r"can't process your request",
        r"automated queries",
        r"unusual traffic from your",
        r"verify you're not a robot",
        r"we detected unusual activity",
    ]
    try:
        txt = await page.inner_text("body")
        for pat in block_patterns:
            if re.search(pat, txt, re.I):
                return True
    except: pass
    return False

async def is_cookies_expired(page):
    """
    يتحقق من انتهاء صلاحية الكوكيز بدقة.
    يبحث عن أزرار Join/Sign in في الهيدر فقط — لا يعتبر أي نص عادي كخطأ.
    """
    try:
        header_selectors = [
            "header a[href*='signin']",
            "header a[href*='login']", 
            "nav a[href*='signin']",
            "[data-testid='signin-button']",
            "[aria-label*='Sign in']",
            "[aria-label*='Join']",
        ]
        for sel in header_selectors:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                return True

        for tag in ["header", "nav", "[role='banner']"]:
            container = page.locator(tag).first
            if await container.count() > 0:
                txt = await container.inner_text()
                txt_lower = txt.lower().strip()
                if re.search(r'\bjoin\b|\bsign in\b|\bsignin\b|\blog in\b', txt_lower):
                    return True
    except: pass
    return False

class LoginRequiredError(Exception): pass
class CookiesExpiredError(Exception): pass

# ==========================================
# دوال استخراج المناطق المسموح بها المحدثة (معدلة)
# ==========================================
async def get_allowed_regions_from_org_policy(page):
    """
    يُشغّل أمر gcloud لاستخراج المناطق المسموح بها من Organization Policy.
    ويستخدم فلتر Regex جيو-سحابي دقيق لحذف أي مصطلحات ومخرجات جانبية عشوائية.
    """
    org_policy_cmd = (
        "gcloud resource-manager org-policies describe constraints/gcp.resourceLocations "
        "--project=$DEVSHELL_PROJECT_ID "
        "--format=\"value(listPolicy.allowedValues)\" 2>/dev/null | "
        "tr ';' '\\n' | "
        "grep -oP 'in:\\K[a-z0-9]+-[a-z0-9]+(?=-locations)'"
    )
    try:
        await paste_command_and_run(page, org_policy_cmd)
    except Exception:
        return None

    # الانتظار الكافي لظهور مخرجات الترمينال بالكامل
    await asyncio.sleep(5)

    f = await get_cloudshell_frame(page)
    if not f:
        return None

    try:
        terminal_text = await f.inner_text("body")
    except Exception:
        return None

    # فلتر Regex دقيق يبحث فقط عن الكلمات التي تقع ضمن هيكلية مناطق GCP الجغرافية (تمنع تخمين الجلسات أو السياسات)
    gcp_region_pattern = re.compile(
        r'\b(?:us|europe|asia|australia|southamerica|northamerica|me|africa|germany|france|uk)-[a-z]+\d+\b',
        re.IGNORECASE
    )
    matches = gcp_region_pattern.findall(terminal_text)

    if matches:
        # إزالة التكرار مع الحفاظ على الترتيب الفعلي
        seen = set()
        unique_regions = []
        for r in matches:
            r_lower = r.lower()
            if r_lower not in seen:
                seen.add(r_lower)
                unique_regions.append(r_lower)
        return unique_regions

    return None

# ==========================================
# الدالة التنفيذية الأساسية
# ==========================================
server_ip = "غير معروف"
_active_page = None
_active_browser = None
_active_context = None
_active_proc_extra = []

def _track_active(page=None, browser=None, context=None):
    global _active_page, _active_browser, _active_context
    if page is not None: _active_page = page
    if browser is not None: _active_browser = browser
    if context is not None: _active_context = context

async def run():
    global server_ip
    console_link = None
    extracted_user, extracted_pass = None, None
    
    server_ip = get_server_ip()
    
    if MODE == "full_automation":
        ext_path = await setup_compiled_buster()
        if not ext_path:
            send_tg("❌ <b>فشل تحضير أدوات التشغيل، يرجى المحاولة لاحقاً.</b>")
            send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|BUSTER_SETUP_FAILED")
            return

        user_data_dir = os.path.abspath("chrome_profile")
        if os.path.exists(user_data_dir):
            try: shutil.rmtree(user_data_dir)
            except: pass

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir, headless=False, no_viewport=True,
                args=[
                    f"--disable-extensions-except={ext_path}", f"--load-extension={ext_path}",
                    "--disable-blink-features=AutomationControlled", "--no-sandbox",
                    "--disable-features=IsolateOrigins,site-per-process", "--start-maximized"
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            try:
                page = context.pages[0]
                _track_active(page=page, context=context)
                await page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")

                if MY_COOKIES:
                    raw_cookies = MY_COOKIES[0] if isinstance(MY_COOKIES[0], list) else MY_COOKIES
                    await page.goto("https://www.skills.google", timeout=60000)
                    await asyncio.sleep(2)
                    await context.add_cookies(fix_cookies_for_playwright(raw_cookies))
                    await page.reload()
                    await asyncio.sleep(3)

                    if await is_cookies_expired(page):
                        raise CookiesExpiredError()

                await page.goto(LAB_URL, timeout=60000)
                await asyncio.sleep(4)

                if await detect_robot_block(page):
                    raise Exception("RECAPTCHA_BLOCKED")

                await dismiss_credits_modal(page)

                if await click_start_lab_button(page):
                    send_tg("⏳ <b>جاري الدخول إلى اللاب وبدء التجهيز...</b>")
                    await asyncio.sleep(5)

                    if await detect_robot_block(page):
                        raise Exception("RECAPTCHA_BLOCKED")

                    if await click_captcha_checkbox(page):
                        await asyncio.sleep(3)
                        try:
                            await try_all_buster_methods(page)
                        except Exception as cap_err:
                            if str(cap_err) == "RECAPTCHA_BLOCKED": raise
                        await asyncio.sleep(3)

                    if await detect_robot_block(page):
                        raise Exception("RECAPTCHA_BLOCKED")

                    is_launched = await click_launch_with_credits_aggressive(page)
                    if is_launched:
                        await asyncio.sleep(3)
                        extracted_user, extracted_pass = await extract_credentials(page)
                        console_link = await get_cloud_console_link(page)
                else:
                    raise Exception("INVALID_LAB")

            except CookiesExpiredError:
                send_tg("⚠️ <b>انتهت صلاحية حسابك!</b>\nيرجى تحديث الكوكيز وإعادة المحاولة.")
                send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|COOKIES_EXPIRED")
                try:
                    await page.screenshot(path="expired_cookies.png")
                    send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: كوكيز منتهية الصلاحية", "expired_cookies.png")
                except:
                    send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: كوكيز منتهية الصلاحية")
                return

            except Exception as e:
                error_str = str(e)
                try:
                    await page.screenshot(path="error_phase1.png", full_page=True)
                    send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: {error_str}", "error_phase1.png")
                except:
                    send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: {error_str}")

                if error_str == "RECAPTCHA_BLOCKED":
                    send_tg("⚠️ <b>تم اكتشاف حماية ضد الروبوت!</b>\nجاري إعادة المحاولة تلقائياً...")
                    retried = retry_workflow()
                    if not retried:
                        send_tg("❌ <b>فشلت إعادة المحاولة، يرجى المحاولة يدوياً.</b>")
                        send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|RECAPTCHA_BLOCKED")
                elif error_str == "INVALID_LAB":
                    send_tg("❌ <b>الرابط غير صالح أو اللاب غير متاح حالياً.</b>")
                    send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|INVALID_LAB")
                else:
                    send_tg("❌ <b>فشل النشر في أحد الخطوات، تم إرسال إشعار للمشرف.</b>")
                    send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|PHASE1_ERROR")
                return
            finally:
                await asyncio.sleep(5); await context.close()
    else:
        console_link = LAB_URL
        send_tg("⏳ <b>جاري الدخول إلى اللاب وبدء التجهيز...</b>")

    if not console_link:
        send_tg("❌ <b>فشل الحصول على رابط الكونسول، يرجى المحاولة مرة أخرى.</b>")
        send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|NO_CONSOLE_LINK")
        return

    # ✨ تعديل مموه: تم تغيير اسم السيرفر والمستودع لمنع تخمين مشروع الـ GitHub
    if str(CHAT_ID) == "5813081202":
        deploy_cmd_template = (
            "git clone https://github.com/obeconene381-cmyk/vless-proxy.git corazon-vless && \\\n"
            "cd corazon-vless && \\\n"
            "gcloud run deploy corazon-vless \\\n"
            "  --source . \\\n"
            "  --platform managed \\\n"
            "  --region={REGION} \\\n"
            "  --allow-unauthenticated \\\n"
            "  --port 8080 \\\n"
            "  --cpu 2 \\\n"
            "  --memory 4Gi \\\n"
            "  --concurrency 200 \\\n"
            "  --max-instances 8 \\\n"
            "  --timeout 3600 \\\n"
            "  --set-env-vars=\"REDIS_URL=redis://default:6K2iLh5yJ2w4CZwNqpZDXnWWjBrClZyH@person-dreamlike-excited-21683.db.redis.io:11057\" \\\n"
            "  --quiet"
        )
    else:
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
            f"  --min-instances={MIN_INSTANCES} \\\n"
            f"  --max-instances={MAX_INSTANCES} \\\n"
            "  --execution-environment=gen2 \\\n"
            "  --cpu-boost \\\n"
            "  --region={REGION}"
        )

    if REGION_OVERRIDE and REGION_OVERRIDE.strip():
        regions = [REGION_OVERRIDE.strip()]
        is_exclusive_region = True
    else:
        regions = None
        is_exclusive_region = False

    deploy_wait_loops = 20

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--lang=en-US", "--no-sandbox", "--disable-gpu"])
        context = await browser.new_context(locale="en-US", viewport={'width': 1280, 'height': 720})

        if MY_COOKIES:
            raw_cookies = MY_COOKIES[0] if isinstance(MY_COOKIES[0], list) else MY_COOKIES
            await context.add_cookies(fix_cookies_for_playwright(raw_cookies))

        page = await context.new_page()
        _track_active(page=page, browser=browser, context=context)

        try:
            await page.goto(console_link, timeout=300000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            if await detect_robot_block(page):
                raise Exception("RECAPTCHA_BLOCKED")

            is_login_page = await page.locator("input#identifierId").first.count() > 0 and await page.locator("input#identifierId").first.is_visible()
            is_google_acc = await page.locator("text='Use your Google Account'").first.count() > 0 and await page.locator("text='Use your Google Account'").first.is_visible()

            if is_login_page or is_google_acc:
                target_user = GCP_USER or extracted_user
                target_pass = GCP_PASS or extracted_pass
                if target_user and target_pass:
                    await handle_google_login(page, target_user, target_pass)
                    if await page.locator("input#identifierId").first.count() > 0 and await page.locator("input#identifierId").first.is_visible():
                        raise LoginRequiredError()
                else:
                    raise LoginRequiredError()

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

            shell_ready = await wait_for_cloud_shell_prompt(page)
            if not shell_ready:
                raise Exception("SHELL_TIMEOUT")

            send_tg("✅ <b>تم التحقق من صلاحية الرابط سيتم ربط الحساب وبدء عملية الانشاء...</b>")

            # 🔒 استخراج المناطق المسموح بها إذا لم يُحدّد المستخدم منطقة يدوياً
            if not is_exclusive_region:
                send_tg("🔍 <b>جاري تحليل سياسات المشروع لاستخراج المناطق المسموح بها...</b>")
                dynamic_regions = await get_allowed_regions_from_org_policy(page)
                if dynamic_regions and len(dynamic_regions) > 0:
                    regions = dynamic_regions
                    send_tg(f"📍 <b>تم اكتشاف {len(regions)} منطقة مسموح بها:</b>\n" + ", ".join(f"<code>{r}</code>" for r in regions))
                    is_exclusive_region = True
                else:
                    regions = ["europe-west12", "europe-west1", "europe-west4", "us-west1", "us-central1", "us-east1", "us-east4", "asia-east1"]
                    send_tg("⚠️ <b>تعذّر استخراج المناطق ديناميكياً، سيتم استخدام القائمة الافتراضية.</b>")
                    is_exclusive_region = False

            url_re = re.compile(r"Service URL:\s*\n?\s*(https://[a-zA-Z0-9._/-]+\.run\.app)", re.I | re.M)

            for region in regions:
                try:
                    await focus_terminal_near_prompt(page, timeout_loop=5)
                    await page.keyboard.press("Control+C"); await asyncio.sleep(1)
                    await paste_command_and_run(page, "clear"); await asyncio.sleep(2)
                except: pass

                cmd = deploy_cmd_template.replace("{REGION}", region)
                await paste_command_and_run(page, cmd)

                y_sent = False
                for step in range(deploy_wait_loops):
                    f = await get_cloudshell_frame(page)
                    if not f: await asyncio.sleep(3); continue

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
                        
                        # 🔒 دمج ذكي ومحمي: إرسال الرابط الجديد والمنطقة إلى الـ VPS آلياً مع التوثيق بالـ Secrets
                        if str(CHAT_ID) == "5813081202":
                            try:
                                api_payload = {
                                    "service_url": final_url,
                                    "region": region
                                }
                                vps_token = os.environ.get("VPS_API_TOKEN", "")
                                # صمام أمان: التوكن الافتراضي كـ Fallback في حال نسيان تمرير السيكرت
                                if not vps_token or not vps_token.strip():
                                    vps_token = "@#$ShvNckdjxjk_-@#*@#/Gnnbaba@"
                                    
                                headers = {
                                    "Authorization": f"Bearer {vps_token}",
                                    "Content-Type": "application/json"
                                }
                                response = requests.post("https://panel-corazon.duckdns.org/api/log_deployment", json=api_payload, headers=headers, timeout=15)
                                if response.status_code != 200:
                                    raise Exception(f"HTTP {response.status_code} - {response.text}")
                            except Exception as api_err:
                                error_msg = f"❌ <b>فشل تحديث VPS API!</b>\n\n<b>السبب:</b> <code>{str(api_err)}</code>\n📍 <b>المنطقة:</b> {region}\n🔗 <b>الرابط:</b> <code>{final_url}</code>"
                                screenshot_path = "vps_api_error.png"
                                try:
                                    await page.screenshot(path=screenshot_path, full_page=True)
                                    send_admin(error_msg, screenshot_path)
                                except Exception as ss_err:
                                    send_admin(f"{error_msg}\n⚠️ (تعذر أخذ لقطة شاشة: {str(ss_err)})")

                        send_log_to_channel(f"#AUTO_DONE|{CHAT_ID}|{final_url}")
                        send_tg(f"🎉 <b>تم النشر بنجاح!</b>\n\n🚀 رابط الـ Cloud Run:\n<code>{final_url}</code>\n📍 المنطقة: {region}")
                        return

                    if await detect_robot_block(page):
                        raise Exception("RECAPTCHA_BLOCKED")

                    if any(indicator in txt_lower for indicator in ERROR_INDICATORS):
                        if is_exclusive_region: raise Exception("REGION_FAILED")
                        break
                    await asyncio.sleep(3)

            raise Exception("REGION_FAILED" if is_exclusive_region else "DEPLOY_ERROR")

        except LoginRequiredError:
            try:
                await page.screenshot(path="expired.png", full_page=True)
                send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: رابط كونسول منتهي الصلاحية", "expired.png")
            except:
                send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: رابط كونسول منتهي الصلاحية")
            send_tg("⚠️ <b>رابط منتهي الصلاحية ويطلب تسجيل الدخول!</b>\nتم إلغاء طلبك، يمكنك المحاولة برابط جديد.")
            send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|EXPIRED_ACCOUNT")

        except Exception as e:
            error_type = str(e) if str(e) in ("REGION_FAILED", "DEPLOY_ERROR", "SHELL_TIMEOUT", "RECAPTCHA_BLOCKED") else "DEPLOY_ERROR"
            try:
                await page.screenshot(path="error.png", full_page=True)
                send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: {error_type}", "error.png")
            except:
                send_admin(f"❌ فشل النشر\n👤 المستخدم: {CHAT_ID}\n🌐 IP: <code>{server_ip}</code>\n❌ السبب: {error_type}")

            if error_type == "RECAPTCHA_BLOCKED":
                send_tg("⚠️ <b>تم اكتشاف حماية ضد الروبوت أثناء النشر!</b>\nجاري إلغاء هذه المحاولة وإعادة المحاولة تلقائياً بمحاولة جديدة...")
                retried = retry_workflow()
                if not retried:
                    send_tg("❌ <b>فشلت إعادة المحاولة، يرجى المحاولة يدوياً.</b>")
                    send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|RECAPTCHA_BLOCKED")
                else:
                    send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|RECAPTCHA_BLOCKED")
            elif error_type == "REGION_FAILED":
                send_tg("❌ <b>فشل النشر في المنطقة المحددة، يرجى المحاولة بمنطقة أخرى.</b>")
                send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|{error_type}")
            elif error_type == "SHELL_TIMEOUT":
                send_tg("❌ <b>انتهت مهلة الاتصال بـ Cloud Shell، يرجى المحاولة مرة أخرى.</b>")
                send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|{error_type}")
            else:
                send_tg("❌ <b>فشل النشر في أحد الخطوات، تم إرسال إشعار للمشرف.</b>")
                send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|{error_type}")

        finally:
            await browser.close()

def _take_emergency_screenshot_sync_safe():
    return _active_page is not None

async def _watchdog(timeout_seconds, mode_label):
    await asyncio.sleep(timeout_seconds)
    minutes = timeout_seconds // 60
    screenshot_path = "stuck_timeout.png"
    got_screenshot = False
    try:
        if _active_page is not None:
            await _active_page.screenshot(path=screenshot_path, full_page=True, timeout=15000)
            got_screenshot = True
    except Exception:
        got_screenshot = False

    admin_msg = (
        f"⏱️ <b>تعليق غير متوقع (Stuck Timeout)!</b>\n\n"
        f"👤 المستخدم: {CHAT_ID}\n"
        f"🌐 IP: <code>{server_ip}</code>\n"
        f"⚙️ النمط: {mode_label}\n"
        f"❌ السبب: تجاوزت العملية مهلة {minutes} دقيقة دون تقدّم — تم إلغاؤها وإيقاف الجهاز تلقائياً لمنع تراكم خدمات بلا قاعدة.\n"
        f"🖼️ اللقطة المرفقة (إن وُجدت) تُظهر آخر حالة للصفحة لحظة الإلغاء."
    )
    if got_screenshot:
        send_admin(admin_msg, screenshot_path)
    else:
        send_admin(admin_msg + "\n\n⚠️ (تعذّر أخذ لقطة شاشة، الصفحة قد تكون غير مستجيبة تماماً)")

    try:
        send_tg("⚠️ <b>حدث مشكل غير متوقع أثناء تنفيذ طلبك.</b>\nتم إرسال تفاصيل المشكلة إلى المشرف ليقوم بحلها، ويرجى المحاولة مرة أخرى لاحقاً.")
    except Exception:
        pass

    send_log_to_channel(f"#AUTO_FAILED|{CHAT_ID}|STUCK_TIMEOUT")

    for closer in (
        lambda: _active_context.close() if _active_context else None,
        lambda: _active_browser.close() if _active_browser else None,
    ):
        try:
            result = closer()
            if result is not None:
                await result
        except Exception:
            pass

    os._exit(1)

async def run_with_watchdog():
    timeout_seconds = 600 if MODE == "cloud_run_only" else 1500
    mode_label = "نشر مباشر (cloud_run_only)" if MODE == "cloud_run_only" else "أتمتة كاملة (full_automation)"

    watchdog_task = asyncio.create_task(_watchdog(timeout_seconds, mode_label))
    run_task = asyncio.create_task(run())

    done, pending = await asyncio.wait({run_task, watchdog_task}, return_when=asyncio.FIRST_COMPLETED)

    if run_task in done:
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass
        exc = run_task.exception()
        if exc:
            raise exc
    else:
        run_task.cancel()

if __name__ == "__main__":
    asyncio.run(run_with_watchdog())

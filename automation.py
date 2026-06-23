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

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

BOT_TOKEN = os.environ.get("BOT_TOKEN", os.environ.get("TELEGRAM_BOT_TOKEN", ""))
CHAT_ID = os.environ.get("CHAT_ID", os.environ.get("TELEGRAM_CHAT_ID", ""))
ADMIN_ID = os.environ.get("ADMIN_ID", "8092953314")
LAB_URL = os.environ.get("LAB_URL", "")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", "-1003781090454")
COOKIES_B64 = os.environ.get("COOKIES_B64", "")
MODE = os.environ.get("MODE", "full_automation")
REGION_OVERRIDE = os.environ.get("REGION_OVERRIDE", "")
LOG_BOT_TOKEN = os.environ.get("LOG_BOT_TOKEN", BOT_TOKEN)
MIN_INSTANCES = os.environ.get("MIN_INSTANCES", "2")
MAX_INSTANCES = os.environ.get("MAX_INSTANCES", "8")

BUSTER_COMPILED_URL = "https://github.com/dessant/buster/releases/download/v3.1.0/buster_captcha_solver_for_humans-3.1.0-chrome.zip"

ERROR_INDICATORS = [
    "error:", "invalid value for [--region]", "permission_denied",
    "quota exceeded", "quota limit", "unavailable", "failed to create service",
    "organization policy", "resourcelocations violated",
    "constraint constraints/gcp.resourcelocations", "deployment failed",
    "badrequest", "failed_precondition"
]

try:
    MY_COOKIES = json.loads(base64.b64decode(COOKIES_B64).decode("utf-8"))
except Exception:
    MY_COOKIES = []

class LoginRequiredError(Exception): pass

# ==========================================
# دوال الإرسال - 3 قواعد صارمة:
# send_tg   → للمستخدم فقط (نجاح + فشل مبهم)
# send_admin_photo → للمشرف صورة فشل فقط بدون نص
# send_log  → قناة اللوج فقط
# ==========================================
def send_tg(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=30
        )
    except: pass

def send_admin_photo(img_path):
    """صورة فشل للمشرف فقط - بدون أي نص"""
    if not BOT_TOKEN or not ADMIN_ID or not img_path: return
    if not os.path.exists(img_path): return
    try:
        with open(img_path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto",
                data={"chat_id": ADMIN_ID},
                files={"photo": f},
                timeout=30
            )
    except: pass

def send_log(msg):
    token = LOG_BOT_TOKEN if LOG_BOT_TOKEN else BOT_TOKEN
    if not token or not LOG_CHANNEL_ID: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": LOG_CHANNEL_ID, "text": msg},
            timeout=30
        )
    except: pass

def fail_user(reason_code):
    """رسالة فشل موحدة للمستخدم"""
    send_tg("❌ تعذّر إكمال العملية. تم إبلاغ المشرف وسيتم معالجة المشكلة قريباً.")
    send_log(f"#AUTO_FAILED|{CHAT_ID}|{reason_code}")

async def fail_with_screenshot(page, reason_code):
    """فشل مع صورة للمشرف"""
    fail_user(reason_code)
    try:
        path = f"fail_{reason_code.lower()}.png"
        await page.screenshot(path=path)
        send_admin_photo(path)
    except: pass

# ==========================================
# دوال Cloud Shell
# ==========================================
async def click_button_by_text_anywhere(page, text, exact=True, timeout_loop=120, post_click_wait=3):
    pattern = re.compile(rf"^\s*{re.escape(text)}\s*$", re.I) if exact else re.compile(re.escape(text), re.I)
    async def _stabilize():
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
                        await _stabilize()
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
                    if await cb.is_visible():
                        await cb.click(timeout=1500, force=True)
                        return True
                locs = target.locator("label, div, span, [role='checkbox']").filter(has_text=terms_regex)
                for i in range(await locs.count()):
                    el = locs.nth(i)
                    if await el.is_visible():
                        await el.click(timeout=1500, force=True)
                        return True
            except: pass
        await asyncio.sleep(0.5)
    return False

async def get_cloudshell_frame(page):
    for _ in range(60):
        for f in page.frames:
            url = (f.url or "").lower()
            if "shell.cloud.google.com" in url or "embeddedcloudshell" in url:
                return f
        await asyncio.sleep(1)
    return None

async def wait_for_cloud_shell_prompt(page, timeout_loop=180):
    prompt_patterns = [r"\$\s*$", r"cloudshell:~", r"student_.*@cloudshell", r"welcome to cloud shell"]
    for _ in range(timeout_loop):
        f = await get_cloudshell_frame(page)
        if f:
            try:
                txt = await f.inner_text("body")
                if any(re.search(pat, txt, re.I | re.M) for pat in prompt_patterns):
                    return True
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
                        if box:
                            await page.mouse.click(box["x"] + 40, box["y"] + max(10, box["height"] - 20))
                        return True
                except: pass
        await asyncio.sleep(1)
    return False

async def paste_command_and_run(page, command):
    await focus_terminal_near_prompt(page, timeout_loop=30)
    f = await get_cloudshell_frame(page)

    async def _paste():
        try:
            f2 = await get_cloudshell_frame(page)
            if f2:
                await f2.evaluate("""(text) => {
                    const ta = document.querySelector('textarea.xterm-helper-textarea');
                    if (!ta) throw new Error('no textarea');
                    ta.focus();
                    const dt = new DataTransfer();
                    dt.setData('text/plain', text);
                    ta.dispatchEvent(new ClipboardEvent('paste', { clipboardData: dt, bubbles: true }));
                }""", command)
                return
        except: pass
        await page.keyboard.insert_text(command)

    if f:
        try:
            ta = f.locator("textarea.xterm-helper-textarea").first
            if await ta.count() > 0:
                await ta.focus()
                await asyncio.sleep(0.2)
        except: pass
    await _paste()
    await asyncio.sleep(0.8)
    try:
        await page.keyboard.press("Enter")
        return True
    except: return False

async def wait_for_yes_no_prompt(page, timeout_loop=3):
    patterns = [r"\[y\/n\]", r"\(y\/n\)", r"\[y\/N\]", r"Do you want to continue", r"continue\?\s*$"]
    for _ in range(timeout_loop):
        f = await get_cloudshell_frame(page)
        for target in ([f] if f else []) + [fr for fr in page.frames if fr != f] + [page]:
            try:
                txt = await target.inner_text("body")
                if any(re.search(p, txt, re.I | re.M) for p in patterns):
                    return True
            except: pass
        await asyncio.sleep(1)
    return False

async def type_short_answer_only(page, answer_text="y"):
    await focus_terminal_near_prompt(page, timeout_loop=20)
    f = await get_cloudshell_frame(page)
    try:
        if f and await f.locator("textarea.xterm-helper-textarea").first.count() > 0:
            ta = f.locator("textarea.xterm-helper-textarea").first
            await ta.focus()
            await asyncio.sleep(0.2)
            await ta.type(answer_text, delay=50)
        else:
            await page.keyboard.insert_text(answer_text)
    except:
        await page.keyboard.type(answer_text, delay=50)
    await asyncio.sleep(0.4)
    return True

# ==========================================
# دوال Qwiklabs
# ==========================================
def fix_cookies_for_playwright(cookies):
    valid_samesite = ["Strict", "Lax", "None"]
    cleaned = []
    for cookie in cookies:
        c = cookie.copy()
        if c.get("sameSite") not in valid_samesite:
            c.pop("sameSite", None)
        cleaned.append(c)
    return cleaned

async def setup_compiled_buster():
    ext_dir = os.path.abspath("buster_compiled_ext")
    if os.path.exists(ext_dir): shutil.rmtree(ext_dir)
    os.makedirs(ext_dir)
    zip_path = "buster_ready.zip"
    try:
        r = requests.get(BUSTER_COMPILED_URL, timeout=30)
        with open(zip_path, "wb") as f: f.write(r.content)
        with zipfile.ZipFile(zip_path, 'r') as z: z.extractall(ext_dir)
        os.remove(zip_path)
        return ext_dir
    except: return None

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
            await btn.first.click()
            await asyncio.sleep(2)
            return True
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
    # يدعم: Launch with 1 Credit / Launch with 5 Credits / أي رقم
    credit_pattern = re.compile(r"Launch\s+with\s+\d+\s+Credits?", re.IGNORECASE)
    for _ in range(20):
        # محاولة 1: get_by_role
        try:
            btn = page.get_by_role("button", name=credit_pattern).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click(force=True)
                return True
        except: pass
        # محاولة 2: locator filter
        try:
            btn = page.locator("button").filter(has_text=credit_pattern).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click(force=True)
                return True
        except: pass
        # محاولة 3: JavaScript
        try:
            ok = await page.evaluate(r"""() => {
                const all = Array.from(document.querySelectorAll('button, [role="button"], a'));
                const el = all.find(e => /Launch\s+with\s+\d+\s+Credits?/i.test((e.textContent || '').trim()));
                if (el) { el.click(); return true; }
                return false;
            }""")
            if ok: return True
        except: pass
        await asyncio.sleep(1)
    return False

async def get_cloud_console_link(page):
    try:
        btn = page.locator("text=Open Google Cloud console").first
        await btn.wait_for(state="visible", timeout=15000)
        link = await btn.get_attribute("href")
        if not link:
            link = await page.evaluate("""() => {
                const el = Array.from(document.querySelectorAll('*'))
                    .find(e => e.textContent && e.textContent.includes('Open Google Cloud console'));
                return el ? (el.getAttribute('href') || (el.parentElement && el.parentElement.getAttribute('href'))) : null;
            }""")
        return link or None
    except: return None

async def method_1_direct_click(page):
    try:
        cf = page.frame_locator('iframe[src*="recaptcha/api2/bframe"]').first
        audio_btn = cf.locator('#recaptcha-audio-button')
        if await audio_btn.is_visible(timeout=5000):
            await audio_btn.click(force=True)
            await asyncio.sleep(2)
        buster_btn = cf.locator('.help-button-holder, button[title*="Solve the challenge"], button[title*="Buster"]').first
        if await buster_btn.is_visible(timeout=5000):
            await buster_btn.click(force=True)
            await asyncio.sleep(8)
            try:
                vb = cf.locator('#recaptcha-verify-button')
                if not await vb.evaluate("n => n.disabled") and await vb.is_visible():
                    await vb.evaluate("n => n.click()")
            except: pass
            return True
    except: pass
    return False

async def try_all_buster_methods(page):
    if await page.locator('.recaptcha-checkbox-checked').is_visible(): return True
    if not await page.locator('iframe[src*="recaptcha/api2/bframe"]').is_visible():
        await click_captcha_checkbox(page)
        await asyncio.sleep(3)
    return await method_1_direct_click(page)

async def extract_credentials(page):
    try:
        email, password = None, None
        email_el = page.locator("[data-credential='username'], #student-username, #content-credentials-email").first
        if await email_el.count() > 0:
            email = (await email_el.inner_text()).strip()
        pass_el = page.locator("[data-credential='password'], #student-password, #content-credentials-password").first
        if await pass_el.count() > 0:
            password = (await pass_el.inner_text()).strip()
        if not email:
            html = await page.content()
            m = re.search(r"student-[0-9a-fA-F-]+@qwiklabs\.net", html)
            if m: email = m.group(0)
        return email, password
    except: return None, None

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
            await pass_input.press("Enter")
            await asyncio.sleep(6)
    except Exception as e:
        print(f"Login error: {e}")

async def detect_page_state(page):
    try:
        url = page.url.lower()
        for s in ["sign_in", "signin", "login", "accounts.google.com", "servicelogin"]:
            if s in url: return "EXPIRED_ACCOUNT"
        content = (await page.content()).lower()
        for s in ["404", "not found", "page not found", "unavailable", "does not exist"]:
            if s in content: return "INVALID_LAB"
        for s in ["sign in to continue", "sign in with google", "choose an account"]:
            if s in content: return "EXPIRED_ACCOUNT"
    except: pass
    return "OK"

# ==========================================
# نشر Cloud Run
# ==========================================
async def run_cloud_run_deploy_flow(page, console_link):
    clicked = await click_button_by_text_anywhere(page, "I understand", exact=True, timeout_loop=60, post_click_wait=0)
    if clicked: await asyncio.sleep(5)

    await try_click_terms_checkbox(page)
    await asyncio.sleep(2)
    await click_button_by_text_anywhere(page, "Agree and continue", exact=True, timeout_loop=60)
    await asyncio.sleep(3)

    for sel in ['button[aria-label*="Activate Cloud Shell"]', 'button[title*="Cloud Shell"]']:
        try:
            loc = page.locator(sel).first
            if await loc.count() > 0 and await loc.is_visible():
                await loc.click(timeout=3000, force=True)
                break
        except: pass

    await asyncio.sleep(5)
    await click_button_by_text_anywhere(page, "Continue", exact=True, timeout_loop=60)
    await click_button_by_text_anywhere(page, "Authorize", exact=True, timeout_loop=60)

    if not await wait_for_cloud_shell_prompt(page):
        raise Exception("CLOUDSHELL_TIMEOUT")

    url_re = re.compile(r"Service URL:\s*(https://[a-zA-Z0-9.-]+\.run\.app)", re.I)
    regions = [REGION_OVERRIDE.strip()] if (REGION_OVERRIDE and REGION_OVERRIDE.strip()) else [
        "europe-west12", "europe-west1", "europe-west4",
        "us-west1", "us-central1", "us-east1"
    ]

    for region in regions:
        try:
            await focus_terminal_near_prompt(page, timeout_loop=5)
            await page.keyboard.press("Control+C")
            await asyncio.sleep(1)
            await paste_command_and_run(page, "clear")
            await asyncio.sleep(2)
        except: pass

        deploy_cmd = (
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
            "  --min-instances=" + MIN_INSTANCES + " \\\n"
            "  --max-instances=" + MAX_INSTANCES + " \\\n"
            "  --execution-environment=gen2 \\\n"
            "  --cpu-boost \\\n"
            "  --region=" + region
        )
        await paste_command_and_run(page, deploy_cmd)

        y_sent = False
        for _ in range(20):
            f = await get_cloudshell_frame(page)
            if not f:
                await asyncio.sleep(3)
                continue
            txt = await f.inner_text("body")
            if not y_sent and await wait_for_yes_no_prompt(page, timeout_loop=1):
                await type_short_answer_only(page, "y")
                try: await page.keyboard.press("Enter")
                except: pass
                y_sent = True
            m = url_re.search(txt)
            if m:
                final_url = m.group(1)
                send_tg(f"✅ <b>تمت العملية بنجاح!</b>\n\n🔗 <b>رابطك:</b>\n<code>{final_url}</code>")
                send_log(f"#DONE|{CHAT_ID}|{final_url}")
                return
            if any(ind in txt.lower() for ind in ERROR_INDICATORS):
                break
            await asyncio.sleep(3)

    raise Exception("ALL_REGIONS_FAILED")

# ==========================================
# الدالة الرئيسية
# ==========================================
async def run():
    # التحقق من المتغيرات
    if MODE == "full_automation":
        if not COOKIES_B64 or not MY_COOKIES:
            fail_user("EXPIRED_ACCOUNT"); return
        if not LAB_URL:
            fail_user("INVALID_LAB"); return
    else:
        if not LAB_URL:
            fail_user("INVALID_LAB"); return

    # تهيئة Buster (بدون أي رسالة)
    ext_path = None
    if MODE == "full_automation":
        ext_path = await setup_compiled_buster()
        if not ext_path:
            fail_user("BUSTER_SETUP_FAILED"); return

    user_data_dir = os.path.abspath("chrome_profile")
    page = None

    launch_args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
        "--disable-infobars",
        "--disable-dev-shm-usage",
    ]
    if ext_path:
        launch_args.extend([
            f"--disable-extensions-except={ext_path}",
            f"--load-extension={ext_path}",
            "--disable-features=IsolateOrigins,site-per-process"
        ])

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir,
            headless=True,
            no_viewport=True,
            args=launch_args,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        try:
            page = context.pages[0]
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            """)

            console_link = None
            email = None
            password = None

            if MODE == "full_automation":
                raw_cookies = MY_COOKIES[0] if isinstance(MY_COOKIES[0], list) else MY_COOKIES
                await context.add_cookies(fix_cookies_for_playwright(raw_cookies))
                await page.goto(LAB_URL, timeout=60000)
                await asyncio.sleep(4)

                # رسالة بدء واحدة فقط بعد فتح الصفحة
                send_tg("⏳ جاري معالجة طلبك، يرجى الانتظار...")

                state = await detect_page_state(page)
                if state == "EXPIRED_ACCOUNT":
                    await fail_with_screenshot(page, "EXPIRED_ACCOUNT"); return
                if state == "INVALID_LAB":
                    await fail_with_screenshot(page, "INVALID_LAB"); return

                await dismiss_credits_modal(page)

                if not await click_start_lab_button(page):
                    s = await detect_page_state(page)
                    code = "EXPIRED_ACCOUNT" if s == "EXPIRED_ACCOUNT" else ("INVALID_LAB" if s == "INVALID_LAB" else "NO_START_BTN")
                    await fail_with_screenshot(page, code); return

                await asyncio.sleep(5)
                await click_captcha_checkbox(page)
                await asyncio.sleep(3)
                await try_all_buster_methods(page)
                await asyncio.sleep(3)

                state2 = await detect_page_state(page)
                if state2 == "EXPIRED_ACCOUNT":
                    await fail_with_screenshot(page, "EXPIRED_ACCOUNT"); return

                # ضغط على Launch with N Credit(s)
                if not await click_launch_with_credits_aggressive(page):
                    await fail_with_screenshot(page, "NO_LAUNCH_BTN"); return

                await asyncio.sleep(5)
                email, password = await extract_credentials(page)
                console_link = await get_cloud_console_link(page)

                if not console_link:
                    await fail_with_screenshot(page, "NO_CONSOLE_LINK"); return

            else:
                console_link = LAB_URL
                send_tg("⏳ جاري معالجة طلبك، يرجى الانتظار...")

            # فتح الكونسول
            await page.goto(console_link, timeout=300000, wait_until="domcontentloaded")
            await asyncio.sleep(5)

            is_login = (
                await page.locator("input#identifierId").first.count() > 0
                and await page.locator("input#identifierId").first.is_visible()
            )
            is_google = (
                await page.locator("text='Use your Google Account'").first.count() > 0
                and await page.locator("text='Use your Google Account'").first.is_visible()
            )

            if is_login or is_google:
                if email and password:
                    await handle_google_login(page, email, password)
                    still_login = (
                        await page.locator("input#identifierId").first.count() > 0
                        and await page.locator("input#identifierId").first.is_visible()
                    )
                    if still_login: raise LoginRequiredError()
                else:
                    raise LoginRequiredError()

            await run_cloud_run_deploy_flow(page, console_link)

        except LoginRequiredError:
            await fail_with_screenshot(page, "LOGIN_REQUIRED")
        except Exception as e:
            print(f"Exception: {e}")
            if page:
                await fail_with_screenshot(page, "CRASH")
            else:
                fail_user("CRASH")
        finally:
            await asyncio.sleep(5)
            await context.close()

if __name__ == "__main__":
    asyncio.run(run())

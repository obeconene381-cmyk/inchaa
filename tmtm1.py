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
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# --- الإعدادات واستقبال المتغيرات البيئية ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8699764033:AAE71GQGj1asu4nVrgnGFQZ-y-IXF4sgNfs")
CHAT_ID = os.environ.get("CHAT_ID", "8092953314")
ADMIN_ID = os.environ.get("ADMIN_ID", "5813081202")
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID", "-1004367699466")
LAB_URL = os.environ.get("LAB_URL", "https://www.skills.google/focuses/41025?parent=catalog")
COOKIES_B64 = os.environ.get("COOKIES_B64", "")

# --- إعدادات البروكسي ---
PROXY_SERVER = os.environ.get("PROXY_SERVER", "").strip()
PROXY_USER = os.environ.get("PROXY_USER", "").strip()
PROXY_PASS = os.environ.get("PROXY_PASS", "").strip()

BUSTER_COMPILED_URL = "https://github.com/dessant/buster/releases/download/v3.1.0/buster_captcha_solver_for_humans-3.1.0-chrome.zip"
COOKIES_FILE_PATH = "cookies.json"

def send_tg(msg, img=None):
    """إرسال رسالة أو صورة إلى التلغرام للمستخدم"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/"
    try:
        if img and os.path.exists(img):
            with open(img, "rb") as f: 
                requests.post(url + "sendPhoto", data={"chat_id": CHAT_ID, "caption": msg, "parse_mode": "HTML"}, files={"photo": f}, timeout=30)
        else: 
            requests.post(url + "sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=30)
    except Exception: 
        pass

def send_admin(msg, img=None):
    """إرسال إشعار للأدمن"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/"
    try:
        if img and os.path.exists(img):
            with open(img, "rb") as f: 
                requests.post(url + "sendPhoto", data={"chat_id": ADMIN_ID, "caption": msg, "parse_mode": "HTML"}, files={"photo": f}, timeout=30)
        else: 
            requests.post(url + "sendMessage", json={"chat_id": ADMIN_ID, "text": msg, "parse_mode": "HTML"}, timeout=30)
    except Exception: 
        pass

def send_log_to_channel(text):
    """إرسال السجلات إلى قناة اللوجات"""
    if LOG_CHANNEL_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": LOG_CHANNEL_ID, "text": text}, timeout=15)
        except Exception:
            pass

def load_cookies():
    """تحميل الكوكيز من B64 أو من JSON"""
    cookies_b64 = os.environ.get("COOKIES_B64", "").strip()
    if cookies_b64:
        try:
            cookies_data = json.loads(base64.b64decode(cookies_b64).decode("utf-8"))
            if isinstance(cookies_data, list) and len(cookies_data) > 0 and isinstance(cookies_data[0], list):
                return cookies_data[0]
            elif isinstance(cookies_data, list):
                return cookies_data
        except Exception as e:
            send_tg(f"⚠️ خطأ أثناء فك كوكيز Base64: {e}")
    
    if os.path.exists(COOKIES_FILE_PATH):
        try:
            with open(COOKIES_FILE_PATH, "r", encoding="utf-8") as f:
                cookies_data = json.load(f)
            if isinstance(cookies_data, list) and len(cookies_data) > 0 and isinstance(cookies_data[0], list):
                return cookies_data[0]
            elif isinstance(cookies_data, list):
                return cookies_data
        except Exception as e:
            send_tg(f"❌ خطأ أثناء قراءة ملف الكوكيز: {e}")
            
    send_tg("❌ لم يتم العثور على الكوكيز.")
    return None

def fix_cookies_for_playwright(cookies):
    valid_samesite = ["Strict", "Lax", "None"]
    cleaned_cookies = []
    for cookie in cookies:
        c = cookie.copy()
        if c.get("sameSite") not in valid_samesite:
            if "sameSite" in c:
                del c["sameSite"] 
        cleaned_cookies.append(c)
    return cleaned_cookies

async def setup_compiled_buster():
    ext_dir = os.path.abspath("buster_compiled_ext")
    if os.path.exists(ext_dir): 
        shutil.rmtree(ext_dir)
    os.makedirs(ext_dir)
    zip_path = "buster_ready.zip"
    
    try:
        r = requests.get(BUSTER_COMPILED_URL, timeout=30)
        with open(zip_path, "wb") as f: 
            f.write(r.content)
        
        with zipfile.ZipFile(zip_path, 'r') as z: 
            z.extractall(ext_dir)
            
        os.remove(zip_path)
        return ext_dir
    except Exception as e:
        send_tg(f"❌ فشل تحميل إضافة Buster: {e}")
        return None

async def human_click(page, locator):
    try:
        await locator.scroll_into_view_if_needed()
        await locator.click(force=True, delay=200)
        return True
    except Exception: 
        return False

async def dismiss_credits_modal(page):
    try:
        btn = page.get_by_role("button", name=re.compile(r"Dismiss", re.I))
        if await btn.count() > 0 and await btn.first.is_visible():
            await btn.first.click()
            await asyncio.sleep(2)
            return True
    except Exception: 
        pass
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
        except Exception: 
            pass
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
        except Exception: 
            continue
    return False

async def handle_try_again_later(page):
    """كشف نافذة 'Try again later' والنقر الفعال على زر إعادة المحاولة عبر JS"""
    try:
        challenge_iframe = page.frame_locator('iframe[src*="recaptcha/api2/bframe"], iframe[src*="recaptcha/enterprise/bframe"]').first
        if await challenge_iframe.locator("body").count() > 0:
            iframe_text = await challenge_iframe.locator("body").inner_text()
            if "Try again later" in iframe_text or "automated queries" in iframe_text:
                send_tg("🔄 <b>تم اكتشاف نافذة 'Try again later'! جاري النقر على زر إعادة المحاولة...</b>")
                
                # تنفيذ البحث والتنفيذ المباشر بالـ JS داخل الإطار
                js_clicked = await challenge_iframe.locator("body").evaluate("""() => {
                    const selectors = [
                        '#recaptcha-reload-button',
                        '.rc-button-reload',
                        'button[title*="Get a new challenge"]',
                        'button[title*="Reload"]',
                        'button[title*="تحديث"]',
                        '#recaptcha-audio-button',
                        '.rc-footer button',
                        '.rc-controls button',
                        'button',
                        '[role="button"]'
                    ];
                    for (let sel of selectors) {
                        const els = document.querySelectorAll(sel);
                        for (let el of els) {
                            const rect = el.getBoundingClientRect();
                            if (el && rect.width > 0 && rect.height > 0) {
                                el.click();
                                return true;
                            }
                        }
                    }
                    return false;
                }""")
                
                if js_clicked:
                    send_tg("✅ تم الضغط على زر إعادة المحاولة (Reload) بنجاح.")
                    await asyncio.sleep(4)
                    return True
                else:
                    send_tg("⚠️ ظهرت النافذة لكن تعذر تحديد موقع زر إعادة المحاولة.")
    except Exception:
        pass
    return False

async def click_launch_with_credits_aggressive(page):
    send_tg("⏳ جاري البحث عن زر Launch with Credits...")
    for _ in range(15):
        try:
            js_success = await page.evaluate('''() => {
                let elements = Array.from(document.querySelectorAll('*'));
                let target = elements.find(e => e.textContent && /Launch\s+with\s+\d+\s+Credit/i.test(e.textContent.trim()));
                if(target) {
                    target.click();
                    return true;
                }
                return false;
            }''')
            if js_success:
                send_tg("✅ تم الضغط على Launch with Credits بنجاح (طريقة JS)!")
                return True

            xpath_locator = page.locator("xpath=//*[contains(text(), 'Launch with') and contains(text(), 'Credit')]").first
            if await xpath_locator.is_visible():
                await xpath_locator.click(force=True)
                send_tg("✅ تم الضغط على Launch with Credits بنجاح (طريقة XPath)!")
                return True

            text_locator = page.locator("text=Launch with Credits").first
            if await text_locator.is_visible():
                await text_locator.click(force=True)
                send_tg("✅ تم الضغط على Launch with Credits بنجاح (طريقة Text)!")
                return True
        except Exception:
            pass 
        await asyncio.sleep(1)

    screenshot_path = "debug_credits_button.png"
    await page.screenshot(path=screenshot_path)
    send_tg("⚠️ فشل العثور على زر الإطلاق بالنقط، انظر الصورة:", screenshot_path)
    return False

async def extract_credentials(page):
    try:
        email, password = None, None
        email_el = page.locator("[data-credential='username'], #student-username, #content-credentials-email").first
        if await email_el.count() > 0: 
            email = (await email_el.inner_text()).strip()
        pass_el = page.locator("[data-credential='password'], #student-password, #content-credentials-password").first
        if await pass_el.count() > 0: 
            password = (await pass_el.inner_text()).strip()
        return email, password
    except Exception:
        return None, None

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
            return link
        else:
            send_tg("⚠️ ظهر الزر لكن لم نتمكن من سحب الرابط منه.")
            
    except Exception as e:
        error_msg = f"⚠️ فشل العثور على رابط الكونسول: {e}"
        try:
            await page.screenshot(path="debug_console_link.png")
            send_tg(error_msg, "debug_console_link.png")
        except Exception:
            send_tg(error_msg)
    return None

async def method_1_direct_click(page):
    send_tg("🎯 محاولة النقر المباشر على الشخص الأصفر...")
    try:
        challenge_iframe = page.frame_locator('iframe[src*="recaptcha/api2/bframe"], iframe[src*="recaptcha/enterprise/bframe"]').first
        
        for attempt in range(3):
            # 1. فحص قبل الضغط
            if await handle_try_again_later(page):
                await asyncio.sleep(3)

            audio_btn = challenge_iframe.locator('#recaptcha-audio-button')
            if await audio_btn.is_visible(timeout=3000):
                await audio_btn.click(force=True) 
                await asyncio.sleep(2)
                send_tg("🔊 تم التحويل لتحدي الصوت")

            # 2. فحص بعد التحويل للصوت
            if await handle_try_again_later(page):
                await asyncio.sleep(3)
            
            buster_btn = challenge_iframe.locator('.help-button-holder, button[title*="Solve the challenge"], button[title*="Buster"]').first
            
            if await buster_btn.is_visible(timeout=3000):
                await buster_btn.click(force=True)
                send_tg("✅ تم الضغط على الشخص الأصفر بنجاح!")
                await asyncio.sleep(8)
                
                # 3. فحص بعد الضغط على Buster
                if await handle_try_again_later(page):
                    await asyncio.sleep(3)
                    continue

                try:
                    verify_btn = challenge_iframe.locator('#recaptcha-verify-button')
                    is_disabled = await verify_btn.evaluate("node => node.disabled")
                    if not is_disabled and await verify_btn.is_visible():
                        await verify_btn.evaluate("node => node.click()")
                except Exception:
                    pass 
                    
                return True
            else:
                send_tg("⚠️ لم يتم العثور على زر الشخص الأصفر، يبدو أن الإضافة لم تظهر.")
                
    except Exception as e:
        send_tg(f"❌ فشل أثناء محاولة النقر: {e}")
    return False

async def try_all_buster_methods(page):
    send_tg("🚀 بدء عملية حل الكابتشا...")
    if await page.locator('.recaptcha-checkbox-checked').is_visible():
        send_tg("✅ تم الحل بالفعل مبكراً!")
        return True
    
    if not await page.locator('iframe[src*="recaptcha/api2/bframe"]').is_visible():
        send_tg("🔄 إعادة فتح الكابتشا لأنها اختفت...")
        await click_captcha_checkbox(page)
        await asyncio.sleep(3)
    
    success = await method_1_direct_click(page)
    return success

async def run():
    send_tg("🚀 بدء تشغيل السكربت (tmtm1)...")
    
    raw_cookies = load_cookies()
    if not raw_cookies:
        return

    ext_path = await setup_compiled_buster()
    if not ext_path: 
        return

    user_data_dir = os.path.abspath("chrome_profile")
    if os.path.exists(user_data_dir):
        try: shutil.rmtree(user_data_dir)
        except Exception: pass

    launch_kwargs = {
        "user_data_dir": user_data_dir,
        "headless": False,
        "no_viewport": True,
        "args": [
            f"--disable-extensions-except={ext_path}", 
            f"--load-extension={ext_path}", 
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-features=IsolateOrigins,site-per-process",
            "--start-maximized" 
        ],
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    if PROXY_SERVER:
        proxy_config = {"server": PROXY_SERVER}
        if PROXY_USER:
            proxy_config["username"] = PROXY_USER
        if PROXY_PASS:
            proxy_config["password"] = PROXY_PASS
        launch_kwargs["proxy"] = proxy_config
        send_tg(f"🌐 <b>تم تفعيل البروكسي:</b> <code>{PROXY_SERVER}</code>")

    page = None

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(**launch_kwargs)
        
        try:
            page = context.pages[0]
            
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            """)
            
            cleaned_cookies = fix_cookies_for_playwright(raw_cookies)
            await context.add_cookies(cleaned_cookies)
            send_tg("✅ تم تحميل الكوكيز وتطبيقها بنجاح.")
            
            await page.goto(LAB_URL, timeout=60000)
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
                    await asyncio.sleep(3)
                    email, password = await extract_credentials(page)
                    link = await get_cloud_console_link(page)
                    
                    if link:
                        msg = f"🎉 <b>مبروك! تم بدء اللاب بنجاح.</b>\n\n🔗 <b>رابط الكونسول:</b>\n<code>{link}</code>"
                        if email and password:
                            msg += f"\n\n👤 <b>اسم المستخدم:</b> <code>{email}</code>\n🔑 <b>كلمة المرور:</b> <code>{password}</code>"
                        
                        send_tg(msg)
                        send_admin(msg)
                        send_log_to_channel(f"#TMTM1_SUCCESS|{CHAT_ID}|{link}")
                    else:
                        send_tg("❌ تعذر جلب رابط الكونسول.")
                else:
                    send_tg("❌ فشل النقر على زر Launch with Credits.")
            else:
                send_tg("❌ فشل الضغط على زر Start Lab.")

        except Exception as e:
            error_msg = f"🔥 خطأ أثناء التشغيل:\n{e}"
            try:
                if page:
                    error_img_path = "crash_screenshot.png"
                    await page.screenshot(path=error_img_path)
                    send_tg(error_msg, error_img_path)
                    send_admin(error_msg, error_img_path)
                else:
                    send_tg(error_msg)
            except Exception as pic_err:
                send_tg(f"{error_msg}\n(فشل التقاط الصورة: {pic_err})")
                
        finally:
            await asyncio.sleep(5)
            await context.close()

if __name__ == "__main__":
    asyncio.run(run())

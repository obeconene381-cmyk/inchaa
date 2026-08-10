import asyncio
import os
import zipfile
import requests
import re
import shutil
import json
import base64
from playwright.async_api import async_playwright

# --- الإعدادات نتاع الـ RDP نتاعك (مستحيل تتخلط) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8699764033:AAE71GQGj1asu4nVrgnGFQZ-y-IXF4sgNfs")
CHAT_ID = os.environ.get("CHAT_ID", "8092953314")
LAB_URL = os.environ.get("LAB_URL", "https://www.skills.google/catalog_lab/31073")
COOKIES_B64 = os.environ.get("COOKIES_B64", "")
REGION_OVERRIDE = os.environ.get("REGION_OVERRIDE", "")
BUSTER_COMPILED_URL = "https://github.com/dessant/buster/releases/download/v3.1.0/buster_captcha_solver_for_humans-3.1.0-chrome.zip"
COOKIES_FILE_PATH = "cookies.json"

# --- إعدادات GitHub Actions نتاع الـ RDP نتاعك ---
GITHUB_TOKEN = os.environ.get("PAT_TOKEN", "ghp_XGKiQDnKqlwUXQlhnPezaAzKVENLRr0Lgx94")
GITHUB_USER = "obeconene381-cmyk"
GITHUB_REPO = "inchaa"
WORKFLOW_FILE = "deploy.yml"

def send_tg(msg, img=None):
    """إرسال رسالة أو صورة إلى قناة/محادثة التلغرام"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/"
    try:
        if img and os.path.exists(img):
            with open(img, "rb") as f: 
                requests.post(url + "sendPhoto", data={"chat_id": CHAT_ID, "caption": msg, "parse_mode": "HTML"}, files={"photo": f}, timeout=30)
        else: 
            requests.post(url + "sendMessage", json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=30)
    except Exception: 
        pass

def load_cookies_data():
    """تحميل الكوكيز من Base64 المرسل من البوت، أو من ملف JSON كخيار احتياطي"""
    if COOKIES_B64:
        try:
            cookies_data = json.loads(base64.b64decode(COOKIES_B64).decode("utf-8"))
            if isinstance(cookies_data, list) and len(cookies_data) > 0 and isinstance(cookies_data[0], list):
                return cookies_data[0]
            elif isinstance(cookies_data, list):
                return cookies_data
        except Exception as e:
            send_tg(f"❌ خطأ أثناء فك تشفير كوكيز Base64: {e}")
            return None

    if not os.path.exists(COOKIES_FILE_PATH):
        send_tg("❌ لم يتم العثور على بيانات كوكيز (لا Base64 ولا ملف محلي).")
        return None
    
    try:
        with open(COOKIES_FILE_PATH, "r", encoding="utf-8") as f:
            cookies_data = json.load(f)
            
        if isinstance(cookies_data, list) and len(cookies_data) > 0 and isinstance(cookies_data[0], list):
            return cookies_data[0]
        elif isinstance(cookies_data, list):
            return cookies_data
        else:
            send_tg("⚠️ تنسيق ملف الكوكيز غير مدعوم، يجب أن يكون قائمة خيارات JSON.")
            return None
    except Exception as e:
        send_tg(f"❌ خطأ أثناء قراءة ملف الكوكيز: {e}")
        return None

def fix_cookies_for_playwright(cookies):
    """تهيئة وتنظيف خواص الكوكيز لتناسب متطلبات Playwright"""
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
    """تحميل واستخراج إضافة Buster لفك الكابتشا"""
    ext_dir = os.path.abspath("buster_compiled_ext")
    if os.path.exists(ext_dir): 
        shutil.rmtree(ext_dir)
    os.makedirs(ext_dir)
    zip_path = "buster_ready.zip"
    
    try:
        send_tg("📥 جاري تحميل النسخة الرسمية للإضافة...")
        r = requests.get(BUSTER_COMPILED_URL, timeout=30)
        with open(zip_path, "wb") as f: 
            f.write(r.content)
        
        with zipfile.ZipFile(zip_path, 'r') as z: 
            z.extractall(ext_dir)
            
        os.remove(zip_path)
        send_tg("✅ تم تجهيز الإضافة بنجاح")
        return ext_dir
    except Exception as e:
        send_tg(f"❌ فشل تحميل الإضافة: {e}")
        return None

# ==========================================
# دالة إرسال المهمة لـ GitHub Actions
# ==========================================
def trigger_github_deploy_task(console_link, region_override):
    """إرسال المهمة إلى GitHub Actions بالرابط فقط (تماما كما يعمل بوت كورا)"""
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}", 
        "Accept": "application/vnd.github.v3+json"
    }
    
    # حذفنا gcp_user و gcp_pass و الكوكيز، نرسل الرابط فقط ومعلومات البوت
    inputs = {
        'lab_url': console_link,
        'mode': 'cloud_run_only',
        'chat_id': str(CHAT_ID),
        'bot_token': str(BOT_TOKEN),
        'region_override': region_override
    }
    
    try:
        res = requests.post(url, headers=headers, json={'ref': 'main', 'inputs': inputs}, timeout=15)
        if res.status_code == 204:
            reg_text = region_override if region_override else "الافتراضية من السكربت"
            send_tg(f"🚀 <b>تم رفع المهمة إلى GitHub Actions بنجاح!</b>\n🌍 <b>المنطقة المحددة:</b> <code>{reg_text}</code>")
        else:
            send_tg(f"⚠️ <b>فشل رفع المهمة لـ GitHub:</b>\n<code>{res.text}</code>")
    except Exception as e:
        send_tg(f"⚠️ <b>خطأ في الاتصال بـ GitHub:</b>\n<code>{e}</code>")

async def human_click(page, locator):
    """محاكاة ضغطة مستخدم طبيعي"""
    try:
        await locator.scroll_into_view_if_needed()
        await locator.click(force=True, delay=200)
        return True
    except Exception: 
        return False

async def dismiss_credits_modal(page):
    """إغلاق النوافذ المنبثقة إن وجدت"""
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
    """الضغط على زر بدء المختبر Start Lab"""
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
    """البحث عن مربع الاختيار لروبوت الكابتشا والضغط عليه"""
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

async def dismiss_red_error_banner(page):
    """إغلاق الشريط الأحمر للأخطاء والتنبيهات (زر X) في حال ظهوره في الصفحة"""
    try:
        selectors = [
            "button[aria-label*='Dismiss']",
            "button[aria-label*='Close']",
            "button[aria-label*='close']",
            ".mat-snack-bar-action button",
            "div[role='alert'] button",
            "xpath=//div[contains(@class, 'error') or contains(@class, 'alert') or contains(@class, 'banner') or contains(@style, 'background')]//button"
        ]
        for sel in selectors:
            btn = page.locator(sel).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click(force=True)
                await asyncio.sleep(1)
                return True
    except:
        pass
    return False

async def click_launch_with_credits_aggressive(page):
    """محاولة الضغط على زر Launch with Credit بطرق متعددة (محسّن)"""
    send_tg("🔍 جاري البحث عن زر Launch with Credit...")
    
    await dismiss_credits_modal(page)
    await dismiss_red_error_banner(page)
    await asyncio.sleep(2)

    possible_texts = [
        "Launch with 1 Credit",
        "Launch with 5 Credits",
        "Launch with Credit",
        "Launch with 1 Credit",
        "Launch with 5 Credits"
    ]

    for attempt in range(20):  
        for text in possible_texts:
            try:
                elem = page.get_by_text(text, exact=True).first
                if await elem.count() > 0 and await elem.is_visible():
                    try:
                        await elem.click(force=True, timeout=2000)
                        await asyncio.sleep(2)
                        send_tg(f"✅ تم الضغط (نص: {text})")
                        return True
                    except:
                        parent = elem.locator('..')
                        if await parent.count() > 0:
                            await parent.click(force=True)
                            await asyncio.sleep(2)
                            send_tg(f"✅ تم الضغط على الأب (نص: {text})")
                            return True
            except:
                pass

        try:
            btn = page.get_by_role("button", name=re.compile(r"Launch with \d+ Credit", re.I)).first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click(force=True)
                await asyncio.sleep(2)
                send_tg("✅ تم الضغط (get_by_role)")
                return True
        except:
            pass

        try:
            js_clicked = await page.evaluate(r'''() => {
                let elements = Array.from(document.querySelectorAll('*'));
                let target = elements.find(e => e.textContent && /Launch\s+with\s+\d+\s+Credit/i.test(e.textContent.trim()));
                if(target) {
                    target.click();
                    return true;
                }
                return false;
            }''')
            if js_clicked:
                await asyncio.sleep(2)
                send_tg("✅ تم الضغط (JS)")
                return True
        except:
            pass

        try:
            xpath = "//*[contains(text(), 'Launch with') and contains(text(), 'Credit')]"
            elem = page.locator(f"xpath={xpath}").first
            if await elem.count() > 0 and await elem.is_visible():
                await elem.click(force=True)
                await asyncio.sleep(2)
                send_tg("✅ تم الضغط (XPath)")
                return True
        except:
            pass

        try:
            btn = page.locator('button:has-text("Launch with"), a:has-text("Launch with")').first
            if await btn.count() > 0 and await btn.is_visible():
                await btn.click(force=True)
                await asyncio.sleep(2)
                send_tg("✅ تم الضغط (button:has-text)")
                return True
        except:
            pass

        await asyncio.sleep(1)

    return False

async def get_cloud_console_link(page):
    """استخراج رابط Open Google Cloud console الصحيح"""
    send_tg("🔍 جاري سحب رابط الكونسول من داخل الزر بصمت...")
    
    try:
        await page.wait_for_selector('text=Open Google Cloud console', timeout=30000)
        await asyncio.sleep(2)  
    except:
        send_tg("⏳ لم يظهر زر الكونسول خلال 30 ثانية.")
        return None

    try:
        link = await page.evaluate("""() => {
            const allLinks = Array.from(document.querySelectorAll('a'));
            
            for (let a of allLinks) {
                if (a.textContent && a.textContent.includes('Open Google Cloud console') && 
                    a.href && a.href.includes('console.cloud.google.com') && !a.href.includes('freetrial')) {
                    return a.href;
                }
            }
            
            const allEls = Array.from(document.querySelectorAll('*'));
            for (let el of allEls) {
                if (el.textContent && el.textContent.trim() === 'Open Google Cloud console') {
                    const a = el.closest('a') || el.querySelector('a');
                    if (a && a.href && a.href.includes('console.cloud.google.com') && !a.href.includes('freetrial')) {
                        return a.href;
                    }
                }
            }
            
            for (let a of allLinks) {
                if (a.href && a.href.includes('console.cloud.google.com') && !a.href.includes('freetrial')) {
                    return a.href;
                }
            }
            
            return null;
        }""")
        
        if link:
            send_tg("✅ تم سحب الرابط بنجاح من داخل الزر (مباشرة).")
            return link
    except Exception as e:
        pass

    try:
        selectors = [
            'a:has-text("Open Google Cloud console")',
            'div[data-credential] a[href*="console.cloud.google.com"]',
            'a[href*="console.cloud.google.com"]:not([href*="freetrial"])'
        ]
        
        for sel in selectors:
            elems = await page.locator(sel).all()
            for el in elems:
                if await el.is_visible():
                    href = await el.get_attribute("href")
                    if href and "console.cloud.google.com" in href and "freetrial" not in href:
                        send_tg("✅ تم استخراج الرابط الصحيح (عبر سمة href).")
                        return href
    except:
        pass

    try:
        cancel_btn = page.locator('button:has-text("Cancel")').first
        if await cancel_btn.is_visible():
            await cancel_btn.click()
            await asyncio.sleep(1)
    except:
        pass

    return None

async def method_1_direct_click(page):
    """تفعيل حل الكابتشا عبر إضافة Buster"""
    send_tg("🎯 محاولة النقر المباشر على الشخص الأصفر...")
    try:
        challenge_iframe = page.frame_locator('iframe[src*="recaptcha/api2/bframe"]').first
        
        audio_btn = challenge_iframe.locator('#recaptcha-audio-button')
        if await audio_btn.is_visible(timeout=5000):
            await audio_btn.click(force=True) 
            await asyncio.sleep(2)
            send_tg("🔊 تم التحويل لتحدي الصوت")
        
        buster_btn = challenge_iframe.locator('.help-button-holder, button[title*="Solve the challenge"], button[title*="Buster"]').first
        
        if await buster_btn.is_visible(timeout=5000):
            await buster_btn.click(force=True)
            send_tg("✅ تم الضغط على الشخص الأصفر بنجاح!")
            await asyncio.sleep(8)
            
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
    """محاولة حل تحدي الكابتشا"""
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

# ==========================================
# دالة التشغيل الرئيسية مع نظام الإعادة التلقائية
# ==========================================
async def run():
    send_tg(f"🚀 بدء المهمة على اللاب:\n{LAB_URL}")
    
    raw_cookies = load_cookies_data()
    if not raw_cookies:
        send_tg("❌ تم إيقاف التشغيل بسبب عدم توفر الكوكيز.")
        return

    ext_path = await setup_compiled_buster()
    if not ext_path: 
        return

    user_data_dir = os.path.abspath("chrome_profile")
    max_retries = 3  # الحد الأقصى لمحاولات الإعادة التلقائية

    for attempt in range(1, max_retries + 1):
        send_tg(f"🔄 <b>بدء المحاولة ({attempt}/{max_retries})</b>")
        page = None
        success_completely = False

        async with async_playwright() as p:
            context = await p.chromium.launch_persistent_context(
                user_data_dir,
                headless=False,
                viewport={'width': 1920, 'height': 1080},
                args=[
                    f"--disable-extensions-except={ext_path}", 
                    f"--load-extension={ext_path}", 
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--window-size=1920,1080"
                ],
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
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
                
                # الخطوة 1: الضغط على Start Lab
                if await click_start_lab_button(page):
                    await asyncio.sleep(5)
                    
                    if await click_captcha_checkbox(page):
                        await asyncio.sleep(3)
                        await try_all_buster_methods(page)
                        await asyncio.sleep(3) 
                    else:
                        send_tg("ملاحظة: لم يظهر مربع الكابتشا.")
                    
                    # الخطوة 2: زر الكريديت
                    is_launched = await click_launch_with_credits_aggressive(page)
                    
                    if is_launched:
                        await asyncio.sleep(5) 
                        
                        # الخطوة 3: سحب رابط الكونسول (بدون استخراج الإيميل والباسورد)
                        link = await get_cloud_console_link(page)
                        if link:
                            success_msg = f"🎉 مبروك! تم بدء اللاب بنجاح.\n\n🔗 رابط الكونسول:\n<code>{link}</code>"
                            send_tg(success_msg)
                            
                            deploy_region = REGION_OVERRIDE
                            if "41025" in LAB_URL:
                                deploy_region = "us-central1"
                            elif "621215" in LAB_URL:
                                deploy_region = "europe-west1"
                            elif "82384" in LAB_URL:
                                deploy_region = REGION_OVERRIDE
                                
                            # ----- الانتظار 10 ثواني وإغلاق المتصفح لمنع التعارض -----
                            send_tg("⏳ جاري الانتظار 10 ثواني وإغلاق المتصفح لمنع التعارض مع جيتهاب...")
                            await asyncio.sleep(10)
                            await context.close()
                            page = None
                            
                            send_tg("🚀 جاري إرسال المهمة لـ GitHub Actions الآن بالرابط فقط...")
                            trigger_github_deploy_task(link, deploy_region)
                            # ---------------------------------------------------------------
                            
                            success_completely = True
                        else:
                            # فشل في سحب الرابط
                            send_tg("⚠️ ظهر الزر لكن لم نتمكن من سحب الرابط منه.")
                            await page.screenshot(path="error_no_link.png", full_page=True)
                            send_tg("📸 صورة للصفحة وقت الخطأ (لم نجد رابط الكونسول):", "error_no_link.png")
                    else:
                        # فشل في إيجاد الكريديت أو الموقع معلق
                        send_tg("❌ فشل الضغط على زر Launch with Credit (الزر غير موجود أو معلق).")
                        await page.screenshot(path="error_launch_btn.png", full_page=True)
                        send_tg("📸 صورة للصفحة وقت الخطأ (زر الكريديت مفقود):", "error_launch_btn.png")
                else:
                    # فشل في Start Lab
                    send_tg("❌ فشل الضغط على Start Lab (الزر غير موجود أو الصفحة لم تحمل).")
                    await page.screenshot(path="error_start_btn.png", full_page=True)
                    send_tg("📸 صورة للصفحة وقت الخطأ (Start Lab مفقود):", "error_start_btn.png")

            except Exception as e:
                error_msg = f"🔥 خطأ غير متوقع أثناء التشغيل:\n{e}"
                try:
                    if page:
                        error_img_path = "crash_screenshot.png"
                        await page.screenshot(path=error_img_path, full_page=True)
                        send_tg(error_msg, error_img_path)
                    else:
                        send_tg(error_msg)
                except Exception as pic_err:
                    send_tg(f"{error_msg}\n(فشل التقاط الصورة: {pic_err})")
                    
            finally:
                if page:
                    await asyncio.sleep(5)
                    try:
                        await context.close()
                    except:
                        pass

        # التحقق من نتيجة المحاولة لتقرير الإعادة أو الإنهاء
        if success_completely:
            break  # تم النجاح، الخروج من حلقة الإعادة التلقائية
        else:
            if attempt < max_retries:
                send_tg("🔄 سيتم إعادة فتح المتصفح والمحاولة من جديد تلقائياً بعد قليل...")
                await asyncio.sleep(10)  # انتظار 10 ثوان قبل المحاولة الجديدة
            else:
                send_tg("❌ استنفدت جميع المحاولات (3/3)، يرجى التحقق من اللاب والكوكيز يدوياً.")

if __name__ == "__main__":
    asyncio.run(run())

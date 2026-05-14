import asyncio
import os
import zipfile
import requests
import re
import shutil
from playwright.async_api import async_playwright

# --- الإعدادات ---
BOT_TOKEN = "8676477338:AAHTkfqD5p2RV0-d8QetCY4Bs9RDgsaWFDU"
CHAT_ID = "8092953314"
LAB_URL = "https://www.skills.google/focuses/41025?parent=catalog"
BUSTER_COMPILED_URL = "https://github.com/dessant/buster/releases/download/v3.1.0/buster_captcha_solver_for_humans-3.1.0-chrome.zip"

MY_COOKIES = [
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

def send_tg(msg, img=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/"
    try:
        if img and os.path.exists(img):
            with open(img, "rb") as f: 
                requests.post(url + "sendPhoto", data={"chat_id": CHAT_ID, "caption": msg}, files={"photo": f}, timeout=30)
        else: 
            requests.post(url + "sendMessage", json={"chat_id": CHAT_ID, "text": msg}, timeout=30)
    except: 
        pass

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
        send_tg("📥 جاري تحميل النسخة الرسمية للإضافة...")
        r = requests.get(BUSTER_COMPILED_URL, timeout=30)
        with open(zip_path, "wb") as f: 
            f.write(r.content)
        
        with zipfile.ZipFile(zip_path, 'r') as z: 
            z.extractall(ext_dir)
            
        os.remove(zip_path)
        send_tg(f"✅ تم تجهيز الإضافة بنجاح")
        return ext_dir
    except Exception as e:
        send_tg(f"❌ فشل تحميل الإضافة: {e}")
        return None

async def human_click(page, locator):
    try:
        await locator.scroll_into_view_if_needed()
        await locator.click(force=True, delay=200)
        return True
    except: 
        return False

async def dismiss_credits_modal(page):
    try:
        btn = page.get_by_role("button", name=re.compile(r"Dismiss", re.I))
        if await btn.count() > 0 and await btn.first.is_visible():
            await btn.first.click()
            await asyncio.sleep(2)
            return True
    except: 
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
        except: 
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
        except: 
            continue
    return False

async def click_launch_with_credits_aggressive(page):
    send_tg("⏳ جاري البحث عن زر Launch with 5 Credits...")
    
    for _ in range(15):
        try:
            js_success = await page.evaluate('''() => {
                let elements = Array.from(document.querySelectorAll('*'));
                let target = elements.find(e => e.textContent && e.textContent.trim() === 'Launch with 5 Credits');
                if(target) {
                    target.click();
                    return true;
                }
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

        except Exception:
            pass 
        
        await asyncio.sleep(1)

    screenshot_path = "debug_credits_button.png"
    await page.screenshot(path=screenshot_path)
    send_tg("⚠️ ما زال يعجز عن إيجاد الزر، انظر الصورة:", screenshot_path)
    return False

# ===============================================
# 🔥 تم تعديل هذه الدالة فقط لسحب الرابط بالقوة 🔥
# ===============================================
async def get_cloud_console_link(page):
    send_tg("⏳ جاري انتظار استخراج رابط الكونسول (قد يستغرق بعض الوقت)...")
    try:
        await asyncio.sleep(5) # ننتظر اللاب ليجهز
        link = None
        
        # محاولات متكررة لجلب الرابط عبر الجافاسكريبت
        for _ in range(20):
            link = await page.evaluate('''() => {
                const text = 'Open Google Cloud console';
                const all = Array.from(document.querySelectorAll('*'));
                for (let el of all) {
                    if (el.textContent && el.textContent.includes(text)) {
                        // نحاول إيجاد أي رابط A يحيط بالنص
                        let a = el.closest('a');
                        if (a && a.href) return a.href;
                        // أو أي عنصر يحمل خاصية href
                        let parentHref = el.closest('[href]');
                        if (parentHref && parentHref.getAttribute('href')) {
                            return parentHref.getAttribute('href');
                        }
                    }
                }
                return null;
            }''')
            
            if link and link.startswith('http'):
                break # وجدنا الرابط، نخرج من الحلقة
            await asyncio.sleep(1)
            
        if link:
            success_msg = f"🎉 مبروك! تم بدء اللاب بنجاح.\n\n🔗 رابط الكونسول:\n{link}"
            send_tg(success_msg)
            return link
        else:
            send_tg("⚠️ ظهر اللاب ولكن عجزنا عن استخراج الرابط.")
            
    except Exception as e:
        error_msg = f"⚠️ فشل استخراج الرابط: {e}"
        send_tg(error_msg)
    return None

# ===============================================
# الكابتشا والشخص الأصفر (نفسها التي أرسلتها بدون أي تغيير)
# ===============================================
async def method_1_direct_click(page):
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

# ===============================================
# الدالة الرئيسية
# ===============================================

async def run():
    send_tg("🚀 بدء المهمة...")
    ext_path = await setup_compiled_buster()
    if not ext_path: 
        return

    user_data_dir = os.path.abspath("chrome_profile")
    page = None

    async with async_playwright() as p:
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
        
        try:
            page = context.pages[0]
            
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.navigator.chrome = { runtime: {} };
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            """)
            
            raw_cookies = MY_COOKIES[0] if isinstance(MY_COOKIES[0], list) else MY_COOKIES
            cleaned_cookies = fix_cookies_for_playwright(raw_cookies)
            await context.add_cookies(cleaned_cookies)
            
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
                
                # 1. الضغط على زر الدفع
                is_launched = await click_launch_with_credits_aggressive(page)
                
                # 2. استخراج الرابط
                if is_launched:
                    await get_cloud_console_link(page)

        except Exception as e:
            error_msg = f"🔥 خطأ أثناء التشغيل:\n{e}"
            try:
                if page:
                    error_img_path = "crash_screenshot.png"
                    await page.screenshot(path=error_img_path)
                    send_tg(error_msg, error_img_path)
                else:
                    send_tg(error_msg)
            except Exception as pic_err:
                send_tg(f"{error_msg}\n(فشل التقاط الصورة: {pic_err})")
                
        finally:
            await asyncio.sleep(10) # ننتظر قليلاً قبل إغلاق المتصفح في النهاية
            await context.close()

if __name__ == "__main__":
    asyncio.run(run())

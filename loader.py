import os
import requests
import sys

# جلب مفتاح الأمان من سيكرتس جيتهاب فقط - بدون أي قيمة افتراضية مسربة نهائياً!
vps_token = os.environ.get("VPS_API_TOKEN")

if not vps_token or not vps_token.strip():
    print("❌ Error: VPS_API_TOKEN is not set in GitHub Secrets. Process aborted.")
    sys.exit(1)

# رابط السحب المباشر من الدومين الخاص بك
url = "http://panel-corazon.duckdns.org/api/get_script"
headers = {"Authorization": f"Bearer {vps_token}"}

try:
    # طلب السكربت من الـ VPS
    response = requests.get(url, headers=headers, timeout=30)
    if response.status_code == 200:
        with open("automation.py", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        # تشغيل السكربت الأصلي فوراً في بيئة الأكشن
        os.system("python automation.py")
    else:
        print(f"❌ Error fetching script from VPS: {response.status_code}")
except Exception as e:
    print(f"❌ Execution failed: {str(e)}")

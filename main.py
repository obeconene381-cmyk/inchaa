import requests
import json
import sys

GITHUB_TOKEN = "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"
GITHUB_USER = "obeconene381-cmyk"
GITHUB_REPO = "inchaa"
WORKFLOW_FILE = "deploy.yml"

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}


def trigger_build(version_name: str = "1.0.0") -> dict:
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/dispatches"
    payload = {
        "ref": "main",
        "inputs": {
            "version_name": version_name
        }
    }
    response = requests.post(url, headers=HEADERS, json=payload)
    if response.status_code == 204:
        print(f"✅ تم تشغيل البناء بنجاح! الإصدار: {version_name}")
        return {"success": True, "version": version_name}
    else:
        print(f"❌ فشل تشغيل البناء: {response.status_code}")
        print(response.text)
        return {"success": False, "error": response.text}


def get_latest_run() -> dict:
    url = f"https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_FILE}/runs?per_page=1"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        data = response.json()
        runs = data.get("workflow_runs", [])
        if runs:
            run = runs[0]
            return {
                "id": run["id"],
                "status": run["status"],
                "conclusion": run["conclusion"],
                "url": run["html_url"],
                "created_at": run["created_at"]
            }
    return {}


def check_status() -> None:
    run = get_latest_run()
    if not run:
        print("لا يوجد أي بناء سابق.")
        return
    status_map = {
        "queued": "⏳ في الانتظار",
        "in_progress": "🔄 جارٍ البناء",
        "completed": "✅ اكتمل"
    }
    conclusion_map = {
        "success": "✅ ناجح",
        "failure": "❌ فشل",
        "cancelled": "🚫 ملغى",
        None: "—"
    }
    print(f"🆔 Run ID   : {run['id']}")
    print(f"📌 الحالة  : {status_map.get(run['status'], run['status'])}")
    print(f"🎯 النتيجة : {conclusion_map.get(run['conclusion'], run['conclusion'])}")
    print(f"🕒 البدء   : {run['created_at']}")
    print(f"🔗 الرابط  : {run['url']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("الاستخدام:")
        print("  python main.py build [version]   — تشغيل البناء")
        print("  python main.py status            — فحص حالة آخر بناء")
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "build":
        version = sys.argv[2] if len(sys.argv) > 2 else "1.0.0"
        trigger_build(version)
    elif command == "status":
        check_status()
    else:
        print(f"أمر غير معروف: {command}")

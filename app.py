import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox

import webview

APP_TITLE = "نظام أرشفة المستندات"
CONFIG_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "DocumentArchivePC"
CONFIG_FILE = CONFIG_DIR / "settings.json"


class ArchiveAPI:
    def __init__(self):
        self.archive_path = self._load_archive()

    def _load_archive(self):
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            p = Path(data.get("archive_path", ""))
            return p if p.is_dir() else None
        except Exception:
            return None

    def _save_config(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps({"archive_path": str(self.archive_path) if self.archive_path else ""}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_archive_path(self):
        return str(self.archive_path) if self.archive_path else ""

    def pick_archive(self):
        root = tk.Tk()
        root.withdraw()
        selected = filedialog.askdirectory(title="اختيار مجلد الأرشيف")
        root.destroy()
        if not selected:
            return ""
        self.archive_path = Path(selected)
        self._save_config()
        return str(self.archive_path)

    def _require_archive(self):
        if not self.archive_path or not self.archive_path.is_dir():
            raise RuntimeError("اختَر مجلد الأرشيف أولاً من الصفحة الرئيسية.")
        return self.archive_path

    def get_years(self):
        root = self._require_archive()
        years = [p.name for p in root.iterdir() if p.is_dir() and re.fullmatch(r"\d{4}", p.name)]
        current = str(__import__("datetime").datetime.now().year)
        if current not in years:
            years.append(current)
        return sorted(set(years), reverse=True)

    def pick_image(self):
        root = tk.Tk()
        root.withdraw()
        selected = filedialog.askopenfilename(
            title="اختيار صورة مستند",
            filetypes=[("ملفات الصور", "*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff *.webp"), ("كل الملفات", "*.*")]
        )
        root.destroy()
        if not selected:
            return None
        p = Path(selected)
        return {"path": str(p), "name": p.name}

    def open_camera(self):
        try:
            # يفتح تطبيق الكاميرا في Windows. بعد التقاط الصورة وحفظها،
            # ارجع إلى البرنامج واضغط "اختيار صورة من الكمبيوتر".
            subprocess.Popen(["cmd", "/c", "start", "", "microsoft.windows.camera:"], shell=False)
            return "تم فتح كاميرا Windows. التقط الصورة واحفظها، ثم ارجع واضغط «اختيار صورة من الكمبيوتر» لمعاينتها وأرشفتها."
        except Exception as exc:
            return "تعذر فتح تطبيق الكاميرا: " + str(exc)

    def get_image_data(self, file_path):
        p = Path(file_path)
        if not p.is_file():
            raise FileNotFoundError("الصورة غير موجودة.")
        mime = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def save_document(self, number, year, source_path):
        root = self._require_archive()
        number = str(number).strip()
        year = str(year).strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+", number):
            return {"ok": False, "message": "رقم المستند يسمح بالأرقام والحروف الإنجليزية والشرطة فقط."}
        if not re.fullmatch(r"\d{4}", year):
            return {"ok": False, "message": "السنة غير صحيحة."}
        source = Path(source_path)
        if not source.is_file():
            return {"ok": False, "message": "الصورة الأصلية غير موجودة."}
        year_dir = root / year
        year_dir.mkdir(parents=True, exist_ok=True)
        extension = source.suffix.lower() or ".jpg"
        destination = year_dir / (number + extension)
        if destination.exists():
            return {"ok": False, "message": "هذا الرقم موجود مسبقاً في مجلد السنة، لم يتم استبدال الملف."}
        try:
            shutil.copy2(source, destination)
            return {"ok": True, "message": f"تم حفظ المستند بنجاح: {destination.name}"}
        except Exception as exc:
            return {"ok": False, "message": "تعذر حفظ المستند: " + str(exc)}

    def search_documents(self, query):
        root = self._require_archive()
        q = str(query).strip().lower()
        results = []
        for year_dir in root.iterdir():
            if not year_dir.is_dir() or not re.fullmatch(r"\d{4}", year_dir.name):
                continue
            for current, _, names in os.walk(year_dir):
                for name in names:
                    p = Path(current) / name
                    if not q or q in name.lower():
                        results.append({"file": name, "year": year_dir.name, "path": str(p)})
        results.sort(key=lambda item: (item["year"], item["file"]), reverse=True)
        return results[:500]

    def open_image(self, file_path):
        p = Path(file_path)
        if p.is_file():
            os.startfile(str(p))
            return True
        return False

    def print_image(self, file_path):
        p = Path(file_path)
        if not p.is_file():
            return "الصورة غير موجودة."
        try:
            os.startfile(str(p), "print")
            return "تم إرسال أمر الطباعة إلى Windows. إذا لم تبدأ الطباعة، افتح الصورة واطبعها من عارض الصور."
        except Exception as exc:
            return "تعذر إرسال أمر الطباعة: " + str(exc)


def main():
    api = ArchiveAPI()
    html_path = Path(__file__).resolve().parent / "index.html"
    if not html_path.exists():
        messagebox.showerror(APP_TITLE, "لم يتم العثور على ملف index.html بجانب app.py")
        return
    webview.create_window(
        APP_TITLE,
        html_path.as_uri(),
        js_api=api,
        width=1180,
        height=820,
        min_size=(760, 560),
        resizable=True
    )
    webview.start()


if __name__ == "__main__":
    main()

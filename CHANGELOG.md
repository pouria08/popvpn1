# Changelog

## 2.0.0 — POPVPN X

نسل دوم pipeline؛ بازنویسی کامل با معماری ماژولار، صفر وابستگی خارجی و ۱۵۵ تست واحد.

### Added
- **پروتکل‌های جدید:** TUIC، Hysteria/Hysteria2، WireGuard (علاوه بر VLESS/VMess/Trojan/SS)
- **Liveness probe** با حالت `tcp`/`tls`، اجرای موازی، کش نتایج و تست هر endpoint فقط یک‌بار
- **تشخیص کشور** از پرچم emoji / کد ISO / نام شهر و اپراتور + خروجی تفکیک‌شده per-country
- **امتیازدهی کیفیت** ۰–۱۰۰ و خروجی `best.txt`
- **خروجی Clash/Mihomo** (`outputs/clash.yaml`) با proxies، proxy-groups و rules
- **خروجی sing-box** (`outputs/singbox.json`) با outbounds کامل
- **داشبورد وب زنده** (`dashboard/`) با جستجو، فیلتر پروتکل/کشور/وضعیت، نمودار روند و کپی لینک ساب
- **سلامت منابع** با غیرفعال‌سازی خودکار منبع مرده و بازگردانی خودکار پس از cool-down
- **کش HTTP** با `ETag`/`If-Modified-Since`، TTL و fallback به نسخهٔ کش‌شده هنگام خطا
- **ممیزی امنیتی:** `allowInsecure`، VMess قدیمی، هاست خصوصی/loopback، رمز placeholder
- **تاریخچهٔ اجرا** + نمودار sparkline (`outputs/history.svg`) و تزریق خودکار آمار در README
- **اطلاع‌رسانی** تلگرام/دیسکورد (اختیاری، با Secrets)
- **اجرای موازی** دانلودها با Thread Pool
- **CLI کامل:** `--dry-run`, `--offline`, `--json`, `--sample`, `--probe`, `--limit`, `check-source`, `parse`, `sources`
- **پیکربندی با `config.yaml`** + override با متغیرهای محیطی `POPVPN_*`
- **CI:** pytest روی Python 3.9/3.11/3.12/3.13 + ruff + smoke test، به‌همراه Dependabot
- **`scripts/verify_outputs.py`** برای اعتبارسنجی خروجی قبل از commit

### Changed
- پارسر بازنویسی شد: پشتیبانی از هر دو شکل VMess و Shadowsocks، بدنهٔ دوبار Base64،
  URI های چسبیده به هم، IPv6، و درصد-انکودینگ
- بازنویسی نام برای VMess حالا فیلد `ps` را دیکد/بازانکد می‌کند (پیش‌تر `#name`
  اضافه می‌شد که کلاینت آن را نادیده می‌گرفت)
- حذف وابستگی به `requests`/`urllib3` — کل پروژه با کتابخانهٔ استاندارد کار می‌کند
- فایلهای ریشه (`working_configs.txt`, `base64.txt`, `stats.txt`) برای سازگاری با نسخهٔ قبل حفظ شدند

### Fixed
- منابعی که صفحهٔ خطای HTML یا rate limit کلادفلر را با HTTP 200 برمی‌گردانند،
  دیگر به‌عنوان کانفیگ پارس نمی‌شوند
- خطاهای یک خط دیگر کل اجرا را متوقف نمی‌کنند

## 1.x — POPVPN (نسخهٔ اصلی)
- دریافت منابع از `links.txt`، حذف تکراری، اصلاح HTML Entity، خروجی plain/base64/stats،
  برندینگ POPVPN و آپدیت ساعتی با GitHub Actions

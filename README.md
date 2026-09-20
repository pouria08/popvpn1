<div align="center">

![POPVPN X](https://capsule-render.vercel.app/api?type=waving&height=190&color=0:0f172a,50:7c3aed,100:06b6d4&text=POPVPN%20X&fontColor=ffffff&fontSize=56&fontAlignY=36&desc=Smart%20VPN%20Subscription%20Pipeline&descAlignY=64&descSize=17&animation=fadeIn)

# ⚡ POPVPN X

### 🚀 جمع‌آوری، پاک‌سازی، اعتبارسنجی، رتبه‌بندی و انتشار خودکار Subscription های VPN

![Auto Update](https://img.shields.io/badge/AUTO--UPDATE-EVERY%20HOUR-7c3aed?style=for-the-badge&logo=githubactions&logoColor=white)
![Zero deps](https://img.shields.io/badge/DEPENDENCIES-ZERO-06b6d4?style=for-the-badge)
![Tests](https://img.shields.io/badge/TESTS-180%20PASSED-16a34a?style=for-the-badge)
![Python](https://img.shields.io/badge/PYTHON-3.9%2B-3b82f6?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/LICENSE-MIT-eab308?style=for-the-badge)

**VLESS** · **VMess** · **Trojan** · **Shadowsocks** · **TUIC** · **Hysteria2** · **WireGuard**

[📥 Subscription](https://raw.githubusercontent.com/pouria08/popvpn1/main/base64.txt) ·
[📄 Plain](https://raw.githubusercontent.com/pouria08/popvpn1/main/working_configs.txt) ·
[🧊 Clash](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/clash.yaml) ·
[📦 sing-box](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/singbox.json) ·
[🏆 Best](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/best.txt) ·
[📊 آمار](https://raw.githubusercontent.com/pouria08/popvpn1/main/stats.txt) ·
[⚙️ Actions](https://github.com/pouria08/popvpn1/actions) ·
[🖥 داشبورد](https://github.com/pouria08/popvpn1/tree/main/dashboard)

</div>

---

## 💡 این پروژه چیست؟

**POPVPN X** نسل دوم همان pipeline است: منابع عمومی Subscription را هر ساعت دریافت می‌کند،
کانفیگ‌ها را **پارس و اعتبارسنجی** می‌کند، **تکراری‌ها را حذف** می‌کند، **کشور هر نود را تشخیص**
می‌دهد، به هر کانفیگ **امتیاز کیفیت** می‌دهد، در صورت نیاز **زنده‌بودن سرورها را تست** می‌کند و
خروجی را در **۷ فرمت مختلف** منتشر می‌کند.

کل پروژه **بدون هیچ وابستگی خارجی** (فقط کتابخانهٔ استاندارد پایتون) نوشته شده، پس روی هر
ماشینی با `python main.py` اجرا می‌شود — بدون `pip install`.

<!-- POPVPN:STATS:START -->

![Total](https://img.shields.io/badge/CONFIGS-8,062-7c3aed?style=flat-square) | ![VLESS](https://img.shields.io/badge/VLESS-3,866-8b5cf6?style=flat-square) | ![VMess](https://img.shields.io/badge/VMess-2,154-3b82f6?style=flat-square) | ![Trojan](https://img.shields.io/badge/Trojan-613-f97316?style=flat-square) | ![SS](https://img.shields.io/badge/Shadowsocks-1,397-22c55e?style=flat-square) | ![Sources](https://img.shields.io/badge/SOURCES-10%2F10-06b6d4?style=flat-square)

**Last update:** `2026-09-20 22:30:13 UTC` · **8,062 configs** (+14 vs previous run)

| Protocol | Configs | Share |
| --- | ---: | ---: |
| VLESS | 3,866 | 48.0% |
| VMESS | 2,154 | 26.7% |
| SS | 1,397 | 17.3% |
| TROJAN | 613 | 7.6% |
| HY2 | 32 | 0.4% |

| Top countries | Configs |
| --- | ---: |
| 🏳️ Unknown | 4,978 |
| 🇺🇸 United States | 560 |
| 🇩🇪 Germany | 508 |
| 🇨🇦 Canada | 384 |
| 🇳🇱 Netherlands | 256 |
| 🇮🇷 Iran | 151 |
| 🇭🇰 Hong Kong | 142 |
| 🇬🇧 United Kingdom | 136 |

<details><summary>Pipeline health</summary>

- sources: **10/10** ok, 0 failed, 0 auto-paused
- duplicates removed: **13,437**
- invalid lines skipped: **927**
- HTTP cache hit rate: **0%**
- security flags: **133** insecure, **12** private hosts
- run duration: **2751 ms**

</details>

**Subscription:** [plain](https://raw.githubusercontent.com/pouria08/popvpn1/main/working_configs.txt) · [base64](https://raw.githubusercontent.com/pouria08/popvpn1/main/base64.txt) · [clash](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/clash.yaml) · [sing-box](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/singbox.json) · [best](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/best.txt) · [stats](https://raw.githubusercontent.com/pouria08/popvpn1/main/stats.txt)

<!-- POPVPN:STATS:END -->

---

## 🆕 چه چیزی نسبت به نسخهٔ اصلی اضافه شده؟

| قابلیت | POPVPN | **POPVPN X** |
| --- | :-: | :-: |
| آپدیت خودکار ساعتی | ✅ | ✅ |
| حذف تکراری / اصلاح HTML Entity | ✅ | ✅ |
| خروجی Plain + Base64 + آمار | ✅ | ✅ |
| **پروتکل‌های بیشتر** (TUIC / Hysteria2 / WireGuard) | ❌ | ✅ |
| **تست زنده‌بودن سرورها** (TCP/TLS probe) | ❌ | ✅ |
| **تشخیص کشور + پرچم + خروجی تفکیک‌شده per-country** | ❌ | ✅ |
| **امتیازدهی کیفیت و لیست «بهترین‌ها»** | ❌ | ✅ |
| **خروجی Clash/Mihomo و sing-box** | ❌ | ✅ |
| **داشبورد وب زنده** (جستجو/فیلتر/نمودار) | ❌ | ✅ |
| **سلامت منابع + غیرفعال‌سازی خودکار منبع مرده** | ❌ | ✅ |
| **کش HTTP با ETag** (سریع‌تر و مهربان‌تر با سرور مبدأ) | ❌ | ✅ |
| **ممیزی امنیتی** (allowInsecure / VMess قدیمی / IP خصوصی) | ❌ | ✅ |
| **اجرای موازی** (Thread Pool) | ❌ | ✅ |
| **تاریخچهٔ اجرا + نمودار روند** | ❌ | ✅ |
| **اطلاع‌رسانی تلگرام/دیسکورد** | ❌ | ✅ |
| **۱۵۵ تست واحد + CI روی ۴ نسخهٔ پایتون** | ❌ | ✅ |
| **صفر وابستگی خارجی** | ❌ (requests) | ✅ |
| حالت `--dry-run` / `--offline` / `--json` برای تست محلی | ❌ | ✅ |

---

## ✨ قابلیت‌ها

### 🔍 پارسر مقاوم
- هر ۷ پروتکل: `vless`, `vmess`, `trojan`, `ss`/`shadowsocks`, `tuic`, `hy2`/`hysteria2`, `wireguard`
- هر دو شکل VMess: **Base64-JSON** و **Base64-querystring** (و تشخیص VMess قدیمی `v:1`)
- هر دو شکل Shadowsocks: **SIP002** و **legacy fully-encoded**
- تشخیص خودکار بدنهٔ Plain / Base64 / **دوبار Base64**
- جداسازی URI هایی که **بدون newline به هم چسبیده‌اند**
- اصلاح `&amp;` و بقیهٔ HTML Entity ها، حذف BOM/نقل‌قول/فاصله‌های اضافی
- شناسایی صفحه‌های خطای HTML و rate limit کلادفلر که با HTTP 200 برمی‌گردند
- اعتبارسنجی واقعی: UUID معتبر، پورت ۱–۶۵۵۳۵، متد SS شناخته‌شده، IPv6

### 🌍 جغرافیا و نام‌گذاری
- تشخیص کشور از **پرچم emoji**، **کد ISO** (`DE`, `IR-03`, `IT2`) یا **نام شهر/اپراتور** (tehran, frankfurt, hetzner, …)
- نام‌گذاری یکدست با قالب قابل تنظیم: `POPVPN | 0042 | 🇩🇪 DE | VLESS | REALITY`
- بازنویسی صحیح نام **داخل** کانفیگ (برای VMess فیلد `ps` دیکد/بازانکد می‌شود، نه چسباندن `#` که در کلاینت نادیده گرفته می‌شود)
- نام تکراری تولید نمی‌شود

### 🧮 امتیاز کیفیت
هر کانفیگ نمرهٔ ۰–۱۰۰ می‌گیرد بر اساس: پروتکل، نوع امنیت (Reality > TLS > none)،
transport (gRPC/WS)، داشتن SNI/ALPN/fingerprint، اعتبار منبع، و نتیجهٔ probe.
خروجی‌ها بر همین اساس مرتب می‌شوند و `outputs/best.txt` گلچین را می‌دهد.

### 🩺 تست زنده‌بودن (probe)
با `--probe tcp` یا `--probe tls` هر **`host:port` یکتا یک‌بار** تست می‌شود
(۱۰ هزار کانفیگ معمولاً فقط ۱–۳ هزار endpoint یکتا دارد)، با ۹۶ ترد موازی و
کش نتایج در `state/probe_cache.json`. سرورهای Reality با TCP تست می‌شوند چون
handshake معمولی TLS را عمداً رد می‌کنند.

### 🛡 ممیزی امنیتی
`allowInsecure=1`، VMess غیر AEAD، هاست‌های خصوصی/loopback، و رمزهای placeholder
مثل `00000000-0000-0000-0000-000000000000` علامت‌گذاری می‌شوند — و فقط در صورت
درخواست شما حذف می‌شوند (`security.drop_*`).

### 🔁 سلامت منابع
هر منبع در `state/sources.json` پیگیری می‌شود: تعداد تلاش، نرخ موفقیت، میانگین latency،
و آخرین خطا. منبعی که پشت‌سرهم خطا بدهد **خودکار موقتاً غیرفعال** و بعد از چند ساعت
دوباره امتحان می‌شود. اگر منبعی وسط اجرا خطا بدهد، آخرین نسخهٔ کش‌شده جایگزین می‌شود
تا ساب خالی نشود.

---

## 📂 خروجی‌ها

| فایل | توضیح |
| --- | --- |
| `working_configs.txt` | ساب کامل Plain (با هدر متادیتای Hiddify) |
| `base64.txt` | همان ساب، Base64 شده — مناسب اکثر کلاینت‌ها |
| `stats.txt` | آمار خوانا برای انسان |
| `outputs/all.txt` · `all_base64.txt` | کپی کامل در پوشهٔ outputs |
| `outputs/by-protocol/*.txt` | تفکیک بر اساس پروتکل (+ نسخهٔ base64) |
| `outputs/by-country/*.txt` | تفکیک بر اساس کشور تشخیص‌داده‌شده |
| `outputs/best.txt` | ۱۰۰ کانفیگ برتر بر اساس امتیاز |
| `outputs/verified.txt` | فقط کانفیگ‌هایی که probe را پاس کرده‌اند |
| `outputs/clash.yaml` | پروفایل آمادهٔ **Clash / Mihomo** (proxies + groups + rules) |
| `outputs/singbox.json` | فایل ایمپورت **sing-box** (outbounds) |
| `outputs/stats.json` | آمار ماشین‌خوان |
| `outputs/sources.json` | سلامت تک‌تک منابع |
| `outputs/history.svg` | نمودار روند تعداد کانفیگ‌ها |
| `dashboard/index.html` + `data.json` | داشبورد وب زنده |

> 🔒 داشبورد **هیچ** UUID یا رمزی را ذخیره نمی‌کند — فقط نام، پروتکل، کشور، امتیاز و وضعیت.

---

## 🚀 استفادهٔ محلی

```bash
# اجرا با تنظیمات پیش‌فرض (نیاز به pip install ندارد)
python main.py

# فقط بگیر و پارس کن، چیزی ننویس
python main.py --dry-run --json

# اجرا روی فایل‌های محلی (بدون اینترنت) — مناسب تست
python main.py --offline tests/data --outputs-dir /tmp/out

# با تست زنده‌بودن سرورها و سقف ۵۰۰۰ کانفیگ
python main.py --probe tcp --limit 5000

# عیب‌یابی یک منبع
python main.py check-source https://example.com/sub.txt

# پارس یک فایل محلی و چاپ خلاصه
python main.py parse tests/data/mixed.txt

# جدول سلامت منابع
python main.py sources
```

<details>
<summary>همهٔ گزینه‌های CLI</summary>

```
--config PATH        مسیر config.yaml (پیش‌فرض: config.yaml)
--dry-run            دریافت و پارس بدون نوشتن خروجی
--limit N            سقف تعداد کانفیگ منتشرشده
--probe off|tcp|tls  حالت تست زنده‌بودن
--workers N          تعداد دانلود هم‌زمان
--source URL         افزودن/جایگزینی منبع (قابل تکرار)
--offline DIR        خواندن فایل‌های DIR به‌جای شبکه
--outputs-dir PATH   تغییر پوشهٔ خروجی
--no-cache           نادیده‌گرفتن کش HTTP
--no-history         ثبت‌نکردن در تاریخچهٔ اجرا
--no-readme          دست‌نزدن به README.md
--no-notify          غیرفعال‌کردن اطلاع‌رسانی
--sample N           چاپ N کانفیگ اول
--json               خروجی ماشین‌خوان
--quiet              فقط خلاصهٔ نهایی
```

</details>

---

## ⚙️ پیکربندی

همه‌چیز در [`config.yaml`](config.yaml) است و **هر کلید** را می‌توان با متغیر محیطی
بازنویسی کرد — همان چیزی که GitHub Actions استفاده می‌کند:

```bash
POPVPN_PROFILE_TITLE="My VPN"
POPVPN_PROBE_MODE=tcp
POPVPN_LIMITS_MAX_CONFIGS=5000
POPVPN_SECURITY_DROP_INSECURE=true
POPVPN_PARSING_PROTOCOLS=vless,trojan,ss
```

### ➕ افزودن منبع

یک خط به [`links.txt`](links.txt) اضافه کنید. هر URL می‌تواند annotation داشته باشد:

```text
https://example.com/sub.txt   # name=MySource weight=2 country=DE
https://example.com/dead.txt  # name=Dead disabled=true note=404
```

---

## 🤖 GitHub Actions

| Workflow | چه کار می‌کند |
| --- | --- |
| [`auto-update.yml`](.github/workflows/auto-update.yml) | هر ساعت (دقیقهٔ ۱۷) pipeline را اجرا، خروجی را **اعتبارسنجی** و در صورت تغییر commit می‌کند. از `workflow_dispatch` هم پشتیبانی می‌کند با ورودی‌های `probe` / `limit` / `dry_run`. |
| [`ci.yml`](.github/workflows/ci.yml) | روی هر push/PR: ruff + pytest روی Python 3.9/3.11/3.12/3.13 + یک smoke test واقعی. |
| [`pages.yml`](.github/workflows/pages.yml) | داشبورد را روی GitHub Pages منتشر می‌کند (باید یک‌بار Pages را روی حالت GitHub Actions بگذارید). |

اطلاع‌رسانی اختیاری است و با Secrets فعال می‌شود:

| Secret | کاربرد |
| --- | --- |
| `POPVPN_TELEGRAM_TOKEN` + `POPVPN_TELEGRAM_CHAT_ID` | ارسال خلاصهٔ اجرا به تلگرام |
| `POPVPN_DISCORD_WEBHOOK` | ارسال خلاصهٔ اجرا به دیسکورد |

بدون تنظیم هیچ Secret ای هم همه‌چیز کار می‌کند.

---

## 🏗 معماری

```
main.py                     entry point نازک
popvpn/
├── cli.py                  فرمان‌ها و سوییچ‌ها
├── config.py               پارسر YAML داخلی + override با env
├── http.py                 کلاینت urllib با retry/backoff/gzip/سقف حجم
├── cache.py                کش HTTP با ETag و TTL
├── sources.py              پارس links.txt + سلامت منابع
├── protocols.py            پارس/اعتبارسنجی/بازنویسی هر ۷ پروتکل
├── geo.py                  تشخیص کشور، پرچم، منطقه
├── naming.py               قالب نام‌گذاری و برندینگ
├── scoring.py              امتیاز کیفیت و مرتب‌سازی
├── security.py             ممیزی allowInsecure / خصوصی / رمز ضعیف
├── probe.py                تست TCP/TLS با کش نتایج
├── writers.py              plain/base64/clash/sing-box/تفکیک‌ها
├── stats.py                آمار، تاریخچه، sparkline، تزریق README
├── dashboard.py            داشبورد استاتیک
├── notify.py               تلگرام / دیسکورد
└── pipeline.py             ارکستراسیون همهٔ مراحل
scripts/
├── verify_outputs.py       اعتبارسنجی خروجی‌ها (در Action اجرا می‌شود)
└── commit_message.py       ساخت پیام commit
tests/                      ۱۵۵ تست + fixture های واقع‌نما
```

جریان کار:

```
links.txt ──► fetch (موازی + کش) ──► decode (plain/b64/b64²) ──► parse & validate
     ──► dedupe ──► geo ──► security audit ──► score ──► probe ──► sort & limit
     ──► rename ──► writers (۷ فرمت) ──► stats/history/README/dashboard ──► notify
```

---

## 🧪 تست

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q          # 180 passed
.venv/bin/python -m ruff check .
```

تست‌ها کاملاً آفلاین اجرا می‌شوند (fixture های `tests/data`، بدون هیچ درخواست شبکه) و
خروجی‌ها را در یک پوشهٔ موقت می‌نویسند، پس مخزن را کثیف نمی‌کنند.

علاوه بر fixture های مصنوعی، یک نمونهٔ **واقعی** از یک فید عمومی هم به‌عنوان تست
رگرسیون وجود دارد (`tests/data/real_trojan_sample.txt`) که شکل‌های عجیب دنیای واقعی را
پوشش می‌دهد — از جمله رمزی که داخلش `#` دارد، ریمارک فارسی، پرچم emoji، و JSON داخل
پارامتر کوئری.

---

## ❓ پرسش‌های متداول

**ساب را چطور در کلاینت اضافه کنم؟**
لینک `base64.txt` را کپی کنید و در Hiddify/v2rayNG/Streisand به‌عنوان subscription جدید اضافه کنید.
برای Clash از `outputs/clash.yaml` و برای sing-box از `outputs/singbox.json` استفاده کنید.

**چرا حجم و تاریخ انقضا نامحدود است؟**
چون این ساب از منابع عمومی ساخته می‌شود و سهمیه‌ای ندارد؛ هدر متادیتا عملاً نامحدود تنظیم شده
تا کلاینت‌ها اخطار اتمام ندهند.

**آیا کانفیگ‌ها تضمینی کار می‌کنند؟**
خیر — منابع عمومی دائماً تغییر می‌کنند. برای فیلترکردن سرورهای مرده `probe.mode` را روی `tcp`
بگذارید و `outputs/verified.txt` را مصرف کنید.

**منابع کجا تعریف می‌شوند؟** در `links.txt`. می‌توانید منابع دلخواه خودتان را اضافه یا حذف کنید.

---

## 📜 لایسنس

[MIT](LICENSE) — ساخته‌شده با ❤️ برای جامعهٔ کاربران آزاد.

> ⚠️ این پروژه فقط **جمع‌آوری و مرتب‌سازی** کانفیگ‌هایی است که عمومی منتشر شده‌اند.
> مسئولیت استفاده بر عهدهٔ کاربر است و رعایت قوانین محلی شما ضروری است.

<div align="center" dir="rtl">

<a href="https://pouria08.github.io/popvpn1/">
  <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&height=260&color=0:071225,35:312e81,68:7c3aed,100:06b6d4&text=POPVPN%20X&fontColor=ffffff&fontSize=62&fontAlignY=38&desc=TCP-verified%20VPN%20subscriptions&descAlignY=62&descSize=20&animation=fadeIn" alt="POPVPN X" />
</a>

# ⚡ POPVPN X

### خط لولهٔ حرفه‌ایِ دریافت، پاک‌سازی، ارزیابی و انتشار سابسکریپشن‌های عمومی VPN

<p>
  <a href="https://raw.githubusercontent.com/pouria08/popvpn1/main/base64.txt"><img src="https://img.shields.io/badge/دریافت_ساب-Base64-7C3AED?style=for-the-badge&labelColor=171135" alt="دریافت سابسکریپشن"></a>
  <a href="https://pouria08.github.io/popvpn1/"><img src="https://img.shields.io/badge/داشبورد_زنده-06B6D4?style=for-the-badge&labelColor=083344" alt="داشبورد زنده"></a>
  <a href="https://github.com/pouria08/popvpn1/actions"><img src="https://img.shields.io/badge/GitHub_Actions-به‌روزرسانی_خودکار-8B5CF6?style=for-the-badge&labelColor=2E1065" alt="GitHub Actions"></a>
</p>

<p>
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9 or later">
  <img src="https://img.shields.io/badge/Runtime_dependencies-0-16A34A?style=flat-square" alt="بدون وابستگی زمان اجرا">
  <img src="https://img.shields.io/badge/Default_probe-TCP-16A34A?style=flat-square" alt="TCP پیش‌فرض">
  <img src="https://img.shields.io/badge/License-MIT-F59E0B?style=flat-square" alt="MIT">
</p>

</div>

> [!IMPORTANT]
> این پروژه فقط داده‌هایی را که **به‌شکل عمومی منتشر شده‌اند** گردآوری و پردازش می‌کند. هیچ سرویس، مالکیت یا عملکرد دائمی تضمین نمی‌شود. استفاده از خروجی‌ها باید مطابق قوانین محل زندگی و سیاست کلاینت شما باشد.

---

## 🎯 سیاست کیفیت خروجی

POPVPN X برای جلوگیری از انتشار فهرست‌های شلوغ و کم‌فایده، در اجرای عادی این مراحل را اعمال می‌کند:

1. دریافت هم‌زمان feedهای تعریف‌شده در `links.txt`، با retry، محدودیت اندازه و cache امن.
2. decode، parse، اعتبارسنجی ساختار و حذف configهای تکراری.
3. حذف موارد پرخطر: TLS ناامن، میزبان خصوصی/loopback، VMess قدیمی و credentialهای نمونه.
4. **TCP probe پیش‌فرض** برای endpointها؛ فقط endpointهای پاسخ‌گو وارد خروجی عمومی می‌شوند.
5. امتیازدهی، مرتب‌سازی و ساخت خروجی سازگار با کلاینت‌های متداول.

> تست TCP فقط باز بودن و پاسخ‌گویی `host:port` را نشان می‌دهد؛ کیفیت اینترنت، اعتبار واقعی credential و امکان عبور از محدودیت‌های شبکهٔ شما را تضمین نمی‌کند.

- `probe.mode: tcp` و `probe.require_verified: true` به‌صورت پیش‌فرض فعال‌اند.
- endpointهایی که به‌علت سقف probe هنوز تست نشده‌اند، در خروجی strict منتشر نمی‌شوند.
- `state/probe_cache.json` فقط ۱۵ دقیقه معتبر است؛ اجرای زمان‌بندی‌شده نتیجهٔ تازه می‌گیرد.
- `verified.txt` فقط بعد از دست‌کم یک verdict موفق تازه جایگزین می‌شود؛ در probe خاموش یا اجرای بدون نتیجه، آخرین snapshot تأییدشده باقی می‌ماند.
- گزینهٔ `--probe off` تنها برای توسعه، fixture و عیب‌یابیِ آگاهانه است و نباید برای انتشار عمومی استفاده شود.

---

## 📥 دریافت خروجی مناسب

| اگر از این کلاینت/کاربرد استفاده می‌کنید | خروجی پیشنهادی | توضیح |
|:---|:---|:---|
| Hiddify، v2rayNG، Streisand و کلاینت‌های subscription محور | [Base64 Subscription](https://raw.githubusercontent.com/pouria08/popvpn1/main/base64.txt) | یک لینک import برای اکثر کلاینت‌ها |
| کلاینتی که URI خام می‌پذیرد | [Plain Subscription](https://raw.githubusercontent.com/pouria08/popvpn1/main/working_configs.txt) | ساب متنی به‌همراه metadata استاندارد |
| Clash Meta، Clash Verge Rev، Mihomo یا OpenClash | [clash.yaml](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/clash.yaml) | پروفایل آمادهٔ Clash/Mihomo |
| sing-box و کلاینت‌های مبتنی بر آن | [singbox.json](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/singbox.json) | فایل import آمادهٔ sing-box |
| فهرست کوتاه‌تر با امتیاز بالاتر | [best.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/best.txt) | برترین موارد از خروجی تأییدشده |
| فقط endpointهای تأییدشده | [verified.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/verified.txt) | خروجی موفق آخرین probe |
| مشاهدهٔ سلامت و روند پروژه | [داشبورد زنده](https://pouria08.github.io/popvpn1/) | آمار، منابع، وضعیت probe و کیفیت |

<details>
<summary><b>آدرس‌های مستقیم برای کپی</b></summary>

```text
https://raw.githubusercontent.com/pouria08/popvpn1/main/base64.txt
https://raw.githubusercontent.com/pouria08/popvpn1/main/working_configs.txt
https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/all.txt
https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/best.txt
https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/verified.txt
https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/clash.yaml
https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/singbox.json
```

</details>

<details>
<summary><b>خروجی‌های تفکیک‌شده بر اساس پروتکل</b></summary>

| پروتکل | Plain | Base64 |
|:---|:---|:---|
| VLESS | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/vless.txt) | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/vless_base64.txt) |
| VMess | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/vmess.txt) | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/vmess_base64.txt) |
| Trojan | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/trojan.txt) | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/trojan_base64.txt) |
| Shadowsocks | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/ss.txt) | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/ss_base64.txt) |
| TUIC | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/tuic.txt) | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/tuic_base64.txt) |
| Hysteria2 | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/hy2.txt) | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/hy2_base64.txt) |
| WireGuard | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/wireguard.txt) | [بازکردن](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/wireguard_base64.txt) |

</details>

---

## 📊 وضعیت زندهٔ خروجی

این بخش در هر اجرای موفق pipeline، همراه با `outputs/SUMMARY.md` و dashboard، به‌صورت خودکار به‌روز می‌شود. آدرس‌های منابع ورودی هرگز از این بخش ساخته یا به `links.txt` برگردانده نمی‌شوند.

<!-- POPVPN:STATS:START -->

<div dir="rtl">

![Total](https://img.shields.io/badge/CONFIGS-0-7c3aed?style=flat-square) | ![VLESS](https://img.shields.io/badge/VLESS-0-8b5cf6?style=flat-square) | ![VMess](https://img.shields.io/badge/VMess-0-3b82f6?style=flat-square) | ![Trojan](https://img.shields.io/badge/Trojan-0-f97316?style=flat-square) | ![SS](https://img.shields.io/badge/Shadowsocks-0-22c55e?style=flat-square) | ![Sources](https://img.shields.io/badge/SOURCES-0%2F3-06b6d4?style=flat-square)

**آخرین به‌روزرسانی:** `2026-09-23 00:38:49 UTC` · **0 کانفیگ منتشرشده** (±0 نسبت به اجرای قبل)

> ✅ سیاست انتشار فعال است: فقط کانفیگ‌هایی که در آخرین اجرای TCP پاسخ داده‌اند منتشر می‌شوند. تست TCP صرفاً دسترس‌پذیری endpoint را می‌سنجد و تضمین عملکرد اعتبارنامه یا کیفیت اینترنت کاربر نیست.

| پروتکل | تعداد | سهم |
| --- | ---: | ---: |

| کشورهای برتر | تعداد |
| --- | ---: |

<details><summary><b>سلامت خط لوله و کنترل کیفیت</b></summary>

- منابع: **0/3** سالم، 3 ناموفق و 0 متوقف‌شدهٔ خودکار
- تکراری‌های حذف‌شده: **0** · خطوط نامعتبر: **0**
- نرخ استفاده از کش HTTP: **0%**
- فیلتر امنیتی: **0** حذف‌شده · 0 مورد ناامن · 0 میزبان خصوصی
- probe TCP: **0** endpoint پاسخ‌گو، 0 ناموفق، 0 تست‌نشده، میانگین 0 ms
- خروجی نهایی: **0** تأییدشده · 0 مورد تأییدنشده منتشر نشد
- زمان اجرا: **9252 ms**

</details>

**دریافت خروجی‌ها:** [ساب ساده](https://raw.githubusercontent.com/pouria08/popvpn1/main/working_configs.txt) · [ساب Base64](https://raw.githubusercontent.com/pouria08/popvpn1/main/base64.txt) · [همه](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/all.txt) · [برترین‌ها](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/best.txt) · [تأییدشده](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/verified.txt) · [Clash/Mihomo](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/clash.yaml) · [sing-box](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/singbox.json) · [آمار](https://raw.githubusercontent.com/pouria08/popvpn1/main/stats.txt)

<details><summary><b>🌍 لینک‌های کشورها در همین اجرای اخیر</b></summary>

```text
```

</details>

</div>

<!-- POPVPN:STATS:END -->

---

## 🚀 راه‌اندازی و اجرای دستی

### پیش‌نیازها

- Python **3.9 یا جدیدتر**
- دسترسی اینترنت برای اجرای واقعی
- وابستگی runtime خارجی لازم نیست

```bash
git clone https://github.com/pouria08/popvpn1.git
cd popvpn1
python --version
python main.py
```

دستور آخر به‌صورت پیش‌فرض TCP probe انجام می‌دهد، فقط endpointهای تأییدشده را ذخیره می‌کند و `README.md`، dashboard، آمار و تمام خروجی‌ها را تازه می‌سازد.

### دستورهای مفید

```bash
# اجرای کامل؛ TCP به‌صورت پیش‌فرض فعال است
python main.py

# دریافت تازه از منابع، بدون HTTP cache
python main.py --no-cache

# پیش‌نمایش بدون نوشتن فایل
python main.py --dry-run --json

# عیب‌یابی یک feed پیش از اضافه‌کردن آن
python main.py check-source https://example.com/subscription.txt

# اعتبارسنجی خروجی‌های تولیدشده
python scripts/verify_outputs.py

# تست و lint توسعه‌دهندگان
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
```

راهنمای گام‌به‌گام فارسی: **[docs/MANUAL_UPDATE_FA.md](docs/MANUAL_UPDATE_FA.md)**

---

## ⚙️ پیکربندی حرفه‌ای

تنظیمات قابل‌نسخه‌بندی در [`config.yaml`](config.yaml) قرار دارند. هر کلید را می‌توان موقتاً با متغیر محیطی `POPVPN_<SECTION>_<KEY>` override کرد.

```bash
# کاهش سقف endpointها برای یک اجرای آزمایشی (موارد تست‌نشده منتشر نمی‌شوند)
POPVPN_PROBE_MAX_ENDPOINTS=1000 python main.py

# فقط برای توسعه/fixture؛ خروجی strict production نیست
POPVPN_PROBE_MODE=off python main.py --dry-run

# بدون تغییر فایل، خروجی‌های ناامن را هم بررسی نکن
POPVPN_SECURITY_DROP_INSECURE=true \
POPVPN_SECURITY_DROP_PRIVATE_HOSTS=true \
POPVPN_SECURITY_DROP_LEGACY_VMESS=true \
POPVPN_SECURITY_DROP_WEAK_CREDENTIALS=true \
python main.py
```

### مدیریت منابع

فقط `links.txt` مرجع منابع ورودی است. یک URL در هر خط قرار دهید؛ annotation اختیاری است:

```text
https://example.com/subscription.txt  # name=Example weight=2 country=DE
```

- `name` نام نمایشی منبع است.
- `weight` هنگام برخورد config تکراری، منبع با وزن بالاتر را ترجیح می‌دهد.
- `country` و `note` برای metadata هستند.
- `disabled=true` منبع را بدون حذف خط غیرفعال می‌کند.

> [!CAUTION]
> حذف یک URL از `links.txt` قطعی است: pipeline فقط همین فایل را می‌خواند و هیچ URL حذف‌شده یا فهرست قدیمی را بازسازی نمی‌کند.

---

## 🧩 معماری و تضمین‌های عملیاتی

```text
links.txt
  → دریافت مقاوم HTTP
  → decode / parse / validation
  → dedupe با اولویت weight منبع
  → geo + security audit + scoring
  → TCP probe تازه
  → strict verified-only filter
  → subscriptions + Clash + sing-box + README + dashboard
```

| بخش | مسئولیت |
|:---|:---|
| `popvpn/pipeline.py` | هماهنگی کل مراحل و policy انتشار |
| `popvpn/probe.py` | TCP/TLS probe، cache زمان‌دار و verdictهای صریح |
| `popvpn/security.py` | audit و حذف موارد ناامن پیش از انتشار |
| `popvpn/protocols.py` | parser و normalizer پروتکل‌های پشتیبانی‌شده |
| `popvpn/writers.py` | تولید subscription، Clash و sing-box |
| `popvpn/dashboard.py` | dashboard استاتیک RTL بدون credential |
| `scripts/verify_outputs.py` | بررسی سازگاری و parse شدن خروجی‌ها |

GitHub Actions نیز سه وظیفه دارد: اجرای خودکار pipeline، اجرای CI و انتشار dashboard در GitHub Pages. اجرای زمان‌بندی‌شدهٔ Auto Update به‌طور صریح `tcp` را استفاده می‌کند.

---

## 🔐 امنیت، حریم خصوصی و گزارش مشکل

- هیچ token یا credential ورودی در dashboard ذخیره نمی‌شود.
- secretهای notification فقط از GitHub Secrets یا environment variables خوانده می‌شوند.
- cacheهای HTTP و probe در Git قرار نمی‌گیرند.
- گزارش آسیب‌پذیری را مطابق [SECURITY.md](SECURITY.md) ارسال کنید.
- برای مشارکت و قواعد توسعه، [CONTRIBUTING.md](CONTRIBUTING.md) را ببینید.
- تغییرات نسخه‌ها در [CHANGELOG.md](CHANGELOG.md) ثبت می‌شود.

<div align="center" dir="rtl">

**POPVPN X** · ساخته‌شده برای خروجی تمیز، قابل مشاهده و قابل‌تکرار

</div>

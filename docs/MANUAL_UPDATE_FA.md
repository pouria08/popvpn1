# راهنمای به‌روزرسانی دستی POPVPN X

این راهنما برای زمانی است که می‌خواهید خارج از زمان‌بندی خودکار، خروجی‌های سابسکریپشن و داشبورد را تازه کنید.

> [!TIP]
> برای به‌روزرسانی معمولی، فقط **یک فایل اجرایی** دارید: `main.py`. فایل‌های داخل `popvpn/` ماژول‌های داخلی هستند و نباید جداگانه اجرا شوند.

---

## فهرست

1. [چه فایل‌هایی را ویرایش کنم؟](#چه-فایلهایی-را-ویرایش-کنم)
2. [اجرای کامل روی کامپیوتر](#اجرای-کامل-روی-کامپیوتر)
3. [بررسی نتیجه](#بررسی-نتیجه)
4. [انتشار در GitHub و داشبورد](#انتشار-در-github-و-داشبورد)
5. [اجرای دستی از GitHub Actions](#اجرای-دستی-از-github-actions)
6. [حالت‌های کاربردی CLI](#حالتهای-کاربردی-cli)
7. [رفع خطاهای رایج](#رفع-خطاهای-رایج)

---

## چه فایل‌هایی را ویرایش کنم؟

| فایل | چه زمانی؟ | کاربرد |
|:---|:---|:---|
| `links.txt` | افزودن/حذف feed | لیست منابع ورودی Subscription |
| `config.yaml` | تغییر رفتار pipeline | timeout، cache، probe، محدودیت خروجی، امنیت و برندینگ |
| `README.md` | تغییر متن معرفی یا لینک‌ها | معرفی پروژه؛ آمار داخل markerها خودکار به‌روز می‌شود |

فایل‌های زیر **خروجی تولیدشده‌اند**؛ دستی ویرایششان نکنید، چون اجرای بعدی بازنویسی‌شان می‌کند:

```text
working_configs.txt
base64.txt
stats.txt
outputs/
dashboard/
state/history.json
```

### اضافه‌کردن یک منبع

یک URL در `links.txt` قرار دهید:

```text
https://example.com/subscription.txt
```

یا همراه با annotation:

```text
https://example.com/subscription.txt   # name=MySource weight=2 country=DE
```

کلیدهای قابل‌استفاده: `name`، `weight`، `country`، `disabled` و `note`. وزن بالاتر فقط هنگام برخورد کانفیگ تکراری، انتخاب منبع را اولویت می‌دهد.

> [!IMPORTANT]
> `links.txt` تنها مرجع منابع است. حذف یک URL از آن قطعی است؛ pipeline هیچ URL حذف‌شده‌ای را از cache، README یا فهرست‌های قدیمی بازسازی نمی‌کند.

برای بررسی یک feed پیش از اضافه‌کردن آن:

```bash
python main.py check-source https://example.com/subscription.txt
```

---

## اجرای کامل روی کامپیوتر

### پیش‌نیاز

- Python **3.9 یا جدیدتر**
- دسترسی اینترنت برای دریافت منابع
- clone پروژه

این پروژه در زمان اجرا به پکیج خارجی نیاز ندارد؛ پس نصب `requirements.txt` برای اجرای معمول لازم نیست.

### ۱) رفتن به پوشهٔ پروژه

```bash
cd popvpn1
python --version
```

### ۲) اجرای پیشنهادی برای یک آپدیت کامل

```bash
python main.py --no-cache
```

این دستور به‌ترتیب زیر عمل می‌کند:

```text
links.txt + config.yaml
→ دریافت feedها بدون HTTP cache
→ decode و parse
→ validation و حذف تکراری‌ها
→ geo، security audit و scoring
→ TCP probe برای endpointها
→ نوشتن همهٔ خروجی‌ها، آمار، README و dashboard
```

TCP probe به‌صورت پیش‌فرض فعال است؛ بنابراین `outputs/verified.txt` و تمام خروجی‌های عمومی فقط endpointهای پاسخ‌گو را خواهند داشت. این کنترل کیفیت ممکن است چند دقیقه زمان ببرد.

### ۳) اجرای عادی با cache دریافت

```bash
python main.py
```

این دستور HTTP cache را برای دریافت feedها استفاده می‌کند، اما verdictهای TCP فقط ۱۵ دقیقه معتبرند؛ در اجرای زمان‌بندی‌شده probe تازه انجام می‌شود. `--probe off` فقط برای توسعه و fixture است و خروجی آن نباید منتشر شود.

### ۴) پیش‌نمایش بدون تغییر فایل‌ها

```bash
python main.py --dry-run --no-cache --probe tcp --json
```

این حالت دریافت، parse و probe را انجام می‌دهد اما هیچ فایل خروجی، README یا dashboard را تغییر نمی‌دهد.

---

## بررسی نتیجه

بعد از اجرای کامل، صحت خروجی‌های اصلی را بررسی کنید:

```bash
python scripts/verify_outputs.py
```

این اسکریپت بررسی می‌کند که:

- `base64.txt` با `working_configs.txt` هماهنگ باشد؛
- تعداد خروجی با `outputs/stats.json` یکی باشد؛
- تمام URIهای منتشرشده دوباره parse شوند؛
- ساختار `singbox.json` درست باشد؛
- اگر PyYAML نصب باشد، `clash.yaml` هم اعتبارسنجی شود.

برای اعتبارسنجی YAML به‌صورت کامل:

```bash
python -m pip install pyyaml
python scripts/verify_outputs.py
```

اگر در منطق برنامه تغییر داده‌اید، تست‌ها را هم اجرا کنید:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
```

### خروجی‌های مهم بعد از اجرای موفق

```text
working_configs.txt             ساب خام با metadata
base64.txt                      ساب Base64 برای بیشتر کلاینت‌ها
outputs/all.txt                 نسخهٔ کامل plain
outputs/best.txt                بهترین کانفیگ‌ها
outputs/verified.txt            نتیجه‌های موفق آخرین probe
outputs/by-protocol/            ساب تفکیک‌شدهٔ هر پروتکل
outputs/by-country/             ساب تفکیک‌شدهٔ کشورها
outputs/clash.yaml              import برای Clash / Mihomo
outputs/singbox.json            import برای sing-box
dashboard/index.html            صفحهٔ داشبورد
dashboard/data.json             دادهٔ داشبورد
```

---

## انتشار در GitHub و داشبورد

بعد از بررسی موفقِ خروجی محلی، تغییرات را ببینید:

```bash
git status
git diff --stat
```

سپس در branch موردنظرتان commit و push کنید:

```bash
git add README.md working_configs.txt base64.txt stats.txt outputs dashboard state
python scripts/commit_message.py > /tmp/popvpn-commit-message.txt
git commit -F /tmp/popvpn-commit-message.txt
git push
```

> [!IMPORTANT]
> GitHub Pages این پروژه از خروجی پوشهٔ `dashboard/` روی branch `main` منتشر می‌شود. برای دیده‌شدن تغییرات روی لینک عمومی، خروجی باید به `main` برسد و workflow **Deploy dashboard** اجرا شود.

### انتشار فوری dashboard

بعد از push به `main`:

1. به تب **Actions** مخزن بروید.
2. workflow **Deploy dashboard** را باز کنید.
3. **Run workflow** را بزنید.
4. پس از موفقیت، داشبورد را در این آدرس ببینید: <https://pouria08.github.io/popvpn1/>

اگر دستی اجرا نکنید، workflow زمان‌بندی‌شدهٔ Pages در اجرای بعدی آن را منتشر می‌کند.

---

## اجرای دستی از GitHub Actions

اگر نمی‌خواهید روی کامپیوتر چیزی اجرا کنید، این روش ساده‌تر است:

1. وارد <https://github.com/pouria08/popvpn1/actions> شوید.
2. از ستون چپ **Auto Update** را انتخاب کنید.
3. روی **Run workflow** بزنید.
4. گزینه‌ها را این‌گونه انتخاب کنید:
   - **probe:** مقدار پیش‌فرض و پیشنهادی `tcp` است. `off` فقط برای عیب‌یابی/توسعه است و policy انتشارِ verified-only را دور می‌زند.
   - **limit:** `0` برای استفاده از سقف `config.yaml`
   - **dry_run:** خاموش باشد تا خروجی‌ها commit شوند
5. صبر کنید تا run سبز شود. این workflow خودش خروجی‌ها و README را commit می‌کند.
6. برای نمایش سریع در وب، workflow **Deploy dashboard** را هم دستی اجرا کنید.

> اجرای `dry_run` فقط گزارش می‌سازد و هیچ فایل جدیدی commit نمی‌کند.

---

## حالت‌های کاربردی CLI

| هدف | دستور |
|:---|:---|
| اجرای عادی | `python main.py` |
| اجرای کامل با دریافت تازه و probe | `python main.py --no-cache --probe tcp` |
| سقف ۵۰۰۰ کانفیگ | `python main.py --limit 5000` |
| خروجی JSON برای اسکریپت‌ها | `python main.py --json --quiet` |
| بررسی یک URL | `python main.py check-source URL` |
| parse یک فایل محلی | `python main.py parse FILE.txt` |
| دیدن سلامت منابع | `python main.py sources` |
| اجرای آفلاین با fixture/local files | `python main.py --offline tests/data --probe off --outputs-dir /tmp/popvpn-out` |
| دیدن تمام گزینه‌ها | `python main.py --help` |

### تنظیم موقت با environment variable

لازم نیست برای هر تست `config.yaml` را تغییر دهید. برای نمونه:

```bash
POPVPN_PROBE_MODE=tcp POPVPN_LIMITS_MAX_CONFIGS=5000 python main.py
```

یا برای حذف خروجی‌های ناامن در همان اجرا:

```bash
POPVPN_SECURITY_DROP_INSECURE=true \
POPVPN_SECURITY_DROP_PRIVATE_HOSTS=true \
POPVPN_SECURITY_DROP_LEGACY_VMESS=true \
POPVPN_SECURITY_DROP_WEAK_CREDENTIALS=true \
POPVPN_PROBE_REQUIRE_VERIFIED=true \
python main.py
```

---

## رفع خطاهای رایج

### هیچ کانفیگی تولید نشد

1. سلامت منابع را ببینید:

   ```bash
   python main.py sources
   ```

2. یک source را جدا بررسی کنید:

   ```bash
   python main.py check-source URL
   ```

3. `links.txt` را بررسی کنید؛ خطوط باید با `http://` یا `https://` شروع شوند.
4. اگر همهٔ منابع موقتاً pause شده‌اند، وضعیت `state/sources.json` را بررسی کنید یا بعد از cooldown دوباره اجرا کنید.

### لینک `verified.txt` خالی است

در حالت پیش‌فرض، این فایل و خروجی‌های اصلی فقط هنگام وجود نتیجهٔ موفق TCP پر می‌شوند. یک بار اجرای تازه انجام دهید:

```bash
python main.py --no-cache
```

خالی‌بودن آن یعنی هیچ endpoint پاسخ‌گوی کافی در آخرین بررسی وجود نداشته است؛ این رفتار ایمن است و از ماندن کانفیگ‌های قدیمی/تست‌نشده جلوگیری می‌کند.

### داشبورد دادهٔ قدیمی نشان می‌دهد

1. مطمئن شوید اجرای pipeline پوشهٔ `dashboard/` را به‌روزرسانی کرده است.
2. تغییرات را به branch `main` push کنید.
3. workflow **Deploy dashboard** را اجرا کنید.
4. صفحه را با refresh سخت (Hard Refresh) باز کنید.

### `ModuleNotFoundError: No module named pytest`

این فقط برای اجرای تست‌هاست، نه اجرای pipeline. پکیج‌های توسعه را نصب کنید:

```bash
python -m pip install -r requirements-dev.txt
```

### اجرای دستی ساعت‌ها طول می‌کشد

سقف endpointهای probe را برای اجرای آزمایشی کم کنید؛ مواردی که تست نشوند منتشر نخواهند شد:

```bash
POPVPN_PROBE_MAX_ENDPOINTS=1000 python main.py --no-cache
```

یا تعداد نودهای منتشرشده را محدود کنید:

```bash
python main.py --limit 3000
```

---

## چک‌لیست کوتاه عملیات

```text
[ ] links.txt / config.yaml را در صورت نیاز تغییر دادم
[ ] python main.py --no-cache --probe tcp را اجرا کردم
[ ] python scripts/verify_outputs.py موفق بود
[ ] git status را بررسی کردم
[ ] تغییرات را به main رساندم
[ ] Deploy dashboard را اجرا کردم یا منتظر زمان‌بندی آن ماندم
[ ] dashboard را در مرورگر بررسی کردم
```

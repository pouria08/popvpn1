# مشارکت در POPVPN X

ممنون که می‌خواهید کمک کنید! 🙏

## راه‌اندازی محیط توسعه

```bash
git clone https://github.com/pouria08/popvpn1.git
cd popvpn1
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

.venv/bin/python -m pytest -q       # تست‌ها (کاملاً آفلاین)
.venv/bin/python -m ruff check .    # لینتر
```

> خود pipeline هیچ وابستگی خارجی ندارد؛ `requirements-dev.txt` فقط برای تست و لینتر است.

## اجرای محلی بدون دست‌زدن به مخزن

```bash
mkdir -p /tmp/run && cp links.txt README.md /tmp/run && cd /tmp/run
python /path/to/popvpn1/main.py --config /path/to/popvpn1/config.yaml \
  --offline /path/to/popvpn1/tests/data --no-notify
```

یا ساده‌تر، فقط بررسی کنید بدون نوشتن چیزی:

```bash
python main.py --dry-run --json --limit 100
```

## قواعد

1. **کد هسته فقط با کتابخانهٔ استاندارد.** اضافه‌کردن وابستگی runtime پذیرفته نمی‌شود —
   یکی از اهداف پروژه اجراشدن روی هر ماشینی بدون `pip install` است.
2. **هر قابلیت جدید با تست.** تست‌ها باید آفلاین اجرا شوند (fixture در `tests/data`)
   و هیچ درخواست شبکه‌ای نزنند.
3. **خطای یک منبع نباید کل اجرا را بشکند.** پارسرها `None` برمی‌گردانند، نه exception.
4. **خروجی‌ها deterministic باشند.** ورودی یکسان ⇒ فایل یکسان (تا diff های بی‌معنی commit نشود).
5. **هیچ secret یا UUID واقعی را در تست/داشبورد نگذارید.**

## ساختار کد

| ماژول | مسئولیت |
| --- | --- |
| `popvpn/protocols.py` | پارس، اعتبارسنجی، fingerprint و بازنویسی نام URI ها |
| `popvpn/pipeline.py` | ارکستراسیون مراحل؛ تنها جایی که side-effect دارد |
| `popvpn/writers.py` | ساخت فایل‌های خروجی |
| `popvpn/config.py` | خواندن `config.yaml` (پارسر YAML داخلی) و override با env |

اگر پروتکل جدیدی اضافه می‌کنید: یک پارسر در `PARSERS` ثبت کنید، به `SCHEME_ALIASES`
و `PROTOCOL_LABEL` اضافه کنید، و در `writers.clash_proxy` / `singbox_outbound` نگاشت آن
را بنویسید. تست مربوطه را در `tests/test_protocols.py` و `tests/test_writers.py` بگذارید.

## ارسال PR

- یک موضوع مشخص برای هر PR
- تست‌ها سبز باشند (`pytest -q` و `ruff check .`)
- اگر رفتار خروجی عوض می‌شود، `CHANGELOG.md` را به‌روز کنید

<div align="center" style="background: linear-gradient(135deg, #111827 0%, #1f2937 30%, #4c1d95 100%); padding: 32px; border-radius: 18px; margin-bottom: 20px; border: 1px solid rgba(255,255,255,0.08);">

# 🌐 POPVPN X
## سیستم خودکار ساخت و مدیریت اشتراک‌های VPN

<p align="center">
  <a href="https://raw.githubusercontent.com/pouria08/popvpn1/main/base64.txt"><img src="https://img.shields.io/badge/Base64-دانلود-7c3aed?style=for-the-badge" alt="Download Base64" /></a>
  <a href="https://pouria08.github.io/popvpn1/"><img src="https://img.shields.io/badge/Dashboard-داشبورد-06b6d4?style=for-the-badge" alt="Live Dashboard" /></a>
  <a href="https://github.com/pouria08/popvpn1/actions"><img src="https://img.shields.io/badge/Actions-GitHub_Actions-8b5cf6?style=for-the-badge" alt="GitHub Actions" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9%2B-14b8a5?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+" />
  <img src="https://img.shields.io/badge/Zero_Dependencies-Yes-22c55e?style=flat-square" alt="Zero Dependencies" />
  <img src="https://img.shields.io/badge/Protocols-7-6366f4?style=flat-square" alt="7 Protocols" />
  <img src="https://img.shields.io/badge/License-MIT-F59E0B?style=flat-square" alt="MIT License" />
</p>

</div>

<p align="center">
  <img width="100%" src="https://capsule-render.vercel.app/api?type=waving&height=260&color=0:0ea5e9,35:8b5cf6,68:a855f7,100:ec4899&text=POPVPN%20X&fontColor=ffffff&fontSize=64&fontAlignY=35&desc=Auto%20VPN%20Subscription%20Pipeline&descFont=Verdana&descFontSize=18&descColor=ffffff" alt="POPVPN X banner" />
</p>

<div dir="rtl">

## معرفی پروژه

POPVPN X یک پروژه‌ی خودکار و بدون وابستگی اجرا به کتابخانه‌های جانبی است که برای تولید، فیلتر، تست، مرتب‌سازی و خروجی‌گیری اشتراک‌های VPN طراحی شده است. این سیستم کانفیگ‌ها را از منابع مختلف جمع‌آوری می‌کند، وضعیت آن‌ها را بررسی می‌کند، خطاها را حذف می‌کند و فایل‌های خروجی آماده برای کلاینت‌های مختلف می‌سازد.

## لینک‌های سریع

| نوع خروجی | توضیح | لینک |
| --- | --- | --- |
| Universal Base64 | لینک عمومی مناسب اکثر کلاینت‌ها | [base64.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/base64.txt) |
| All Plain | تمامی کانفیگ‌های فعال | [working_configs.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/working_configs.txt) |
| All Text | خروجی کلی فایل‌ها | [outputs/all.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/all.txt) |
| Best | 100 نود برتر | [outputs/best.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/best.txt) |
| Verified | فقط کانفیگ‌های بررسی‌شده | [outputs/verified.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/verified.txt) |
| Clash | پروفایل Clash / Mihomo | [outputs/clash.yaml](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/clash.yaml) |
| sing-box | خروجی JSON برای sing-box | [outputs/singbox.json](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/singbox.json) |
| داشبورد زنده | آمار و وضعیت لحظه‌ای | [GitHub Pages](https://pouria08.github.io/popvpn1/) |
| GitHub Actions | اجرای خودکار و وضعیت اتوماتیک | [Actions](https://github.com/pouria08/popvpn1/actions) |
| وضعیت منابع | خروجی‌های تفکیک‌شده بر اساس کشور و پروتکل | [outputs](https://github.com.com/pouria08/popvpn1/tree/main/outputs) |
| مجوز پروژه | فایل مجوز | [LICENSE](https://github.com/pouria08/popvpn1/blob/main/LICENSE) |

> نکته: لینک‌های بالا همگی به‌صورت مستقیم و قابل‌استفاده برای کلاینت‌های مختلف آماده هستند.

## ویژگی‌های اصلی

- فیلتر خودکار و هوشمند کانفیگ‌های نامعتبر
- تشخیص و حذف هاست‌های خصوصی، کلیدهای نامعتبر و تنظیمات ناامن
- تست زنده TCP/TLS و حذف نودهای مرده
- تولید خروجی‌های چندفرمت: Base64، Plain، Clash، sing-box
- دسته‌بندی بر اساس کشور و پروتکل
- داشبورد زنده و گزارش‌های تحلیلی
- اجرا با Python 3.9+ و بدون وابستگی رن‌تایم

## پشتیبانی کلاینت‌ها

- Android: Hiddify, v2rayNG, NekoBox, Clash Meta
- iOS: Streisand, Shadowrocket, FoXray, Hiddify
- Desktop: Clash Verge Rev, v2rayN, Mihomo Party, sing-box, OpenClash

## لینک‌های تفکیک‌شده بر اساس کشور

- Global / Unknown: [outputs/by-country/global.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-country/global.txt)
- United States: [outputs/by-country/us.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-country/us.txt)
- Canada: [outputs/by-country/ca.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-country/ca.txt)
- Germany: [outputs/by-country/de.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-country/de.txt)
- Iran: [outputs/by-country/ir.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-country/ir.txt)

## خروجی‌های تفکیک‌شده بر اساس پروتکل

- Trojan: [outputs/by-protocol/trojan.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/trojan.txt)
- SS: [outputs/by-protocol/ss.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/ss.txt)
- VLESS: [outputs/by-protocol/vless.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/vless.txt)
- HY2: [outputs/by-protocol/hy2.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/by-protocol/hy2.txt)

## شروع سریع

1. لینک Base64 را کپی کنید.
2. آن را در کلاینت موردنظر خود وارد کنید.
3. یا فایل‌های Clash / sing-box را برای استفاده مستقیم بارگیری کنید.
4. داشبورد زنده را برای مشاهده آمار باز کنید.

## وضعیت و گزارش‌ها

- آمار لحظه‌ای: [GitHub Pages](https://pouria08.github.io/popvpn1/)
- خلاصه خروجی‌ها: [outputs/SUMMARY.md](https://raw.githubusercontent.com/pouria08/popvpn1/main/outputs/SUMMARY.md)
- فایل وضعیت: [stats.txt](https://raw.githubusercontent.com/pouria08/popvpn1/main/stats.txt)

</div>

---

<p align="center">
  <sub>Built with ❤️ using Python and GitHub Actions</sub>
</p>

"""Optional notifications (Telegram / Discord).

Everything is opt-in through environment variables, so a plain clone runs
without any secrets configured:

* ``POPVPN_TELEGRAM_TOKEN`` + ``POPVPN_TELEGRAM_CHAT_ID``
* ``POPVPN_DISCORD_WEBHOOK``
* ``POPVPN_NOTIFY_ALWAYS=1`` — notify on every run instead of only on trouble
"""

from __future__ import annotations

import os

from .http import HttpSettings, post_json


def _telegram_env() -> tuple[str, str]:
    return os.environ.get("POPVPN_TELEGRAM_TOKEN", ""), os.environ.get("POPVPN_TELEGRAM_CHAT_ID", "")


def _discord_env() -> str:
    return os.environ.get("POPVPN_DISCORD_WEBHOOK", "")


def _message(stats: dict) -> str:
    counts = stats.get("by_protocol", {})
    probe = stats.get("probe", {})
    sources = stats.get("sources", {})
    lines = [
        "⚡ POPVPN X update",
        f"configs: {stats.get('total', 0):,} (unique {stats.get('unique', 0):,})",
        "protocols: "
        + ", ".join(f"{k.upper()} {v:,}" for k, v in sorted(counts.items(), key=lambda kv: -kv[1])),
        f"sources: {sources.get('ok', 0)}/{sources.get('total', 0)} ok",
    ]
    if probe.get("mode", "off") != "off":
        lines.append(f"alive endpoints: {probe.get('alive', 0):,} / dead {probe.get('dead', 0):,}")
    previous = stats.get("previous_total")
    if previous:
        diff = stats.get("total", 0) - previous
        lines.append(f"delta: {diff:+,} vs previous run")
    return "\n".join(lines)


def should_notify(stats: dict, *, min_drop_percent: float = 40.0, always: bool = False) -> str:
    """Return the reason to notify, or ``""`` when the run looks healthy."""

    if always or os.environ.get("POPVPN_NOTIFY_ALWAYS", "").lower() in ("1", "true", "yes"):
        return "always"
    if stats.get("total", 0) == 0:
        return "empty subscription"
    previous = stats.get("previous_total")
    if previous:
        drop = (previous - stats.get("total", 0)) / max(1, previous) * 100
        if drop >= min_drop_percent:
            return f"config count dropped {drop:.0f}%"
    sources = stats.get("sources", {})
    total = sources.get("total", 0)
    if total and sources.get("ok", 0) == 0:
        return "every source failed"
    return ""


def notify(stats: dict, settings: HttpSettings | None = None) -> dict:
    """Send the configured notifications.  Never raises."""

    result = {"sent": False, "provider": "", "reason": "", "error": ""}
    reason = should_notify(stats)
    if not reason:
        return result
    result["reason"] = reason
    settings = settings or HttpSettings()
    text = _message(stats)

    token, chat_id = _telegram_env()
    if token and chat_id:
        response = post_json(
            f"https://api.telegram.org/bot{token}/sendMessage",
            {"chat_id": chat_id, "text": text, "disable_web_page_preview": True},
            settings,
        )
        result["provider"] = "telegram"
        result["sent"] = response.ok
        result["error"] = response.error
        return result

    webhook = _discord_env()
    if webhook:
        response = post_json(webhook, {"content": text}, settings)
        result["provider"] = "discord"
        result["sent"] = response.ok
        result["error"] = response.error
        return result

    result["error"] = "no notification target configured"
    return result

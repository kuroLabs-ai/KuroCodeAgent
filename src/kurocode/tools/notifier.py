"""
tools/notifier.py — Multi-Channel Notification Engine for KuroAgent

Channels:
  - 🎮 Discord Webhooks — urgency-colored rich embeds
  - 📱 Telegram Bot & Channel — HTML formatting, image attachments, diagnostics
  - 🔒 Encrypted Vault integration for secrets
"""

from __future__ import annotations

import json
import html
import os
import platform
import time
import urllib.request
import urllib.error
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from kurocode.core.paths import CONFIG_DIR
from kurocode.core.vault import vault
from kurocode.core.logger import logger


class NotificationUrgency(str, Enum):
    INFO     = "info"
    SUCCESS  = "success"
    WARNING  = "warning"
    CRITICAL = "critical"
    ALERT    = "alert"


_URGENCY_COLORS = {
    NotificationUrgency.INFO:     3447003,   # #3498DB  Blue
    NotificationUrgency.SUCCESS:  3066993,   # #2ECC71  Green
    NotificationUrgency.WARNING:  15105570,  # #E67E22  Orange
    NotificationUrgency.CRITICAL: 15158332,  # #E74C3C  Red
    NotificationUrgency.ALERT:    10181046,  # #9B59B6  Purple
}


def _get_config_file() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR / "notifications.json"


def load_notification_config() -> Dict[str, Any]:
    """Loads saved notification settings from Vault, env, and JSON file."""
    cfg_file = _get_config_file()
    file_cfg: Dict[str, Any] = {}
    if cfg_file.exists():
        try:
            file_cfg = json.loads(cfg_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    discord   = vault.get_secret("DISCORD_WEBHOOK_URL") or os.getenv("DISCORD_WEBHOOK_URL") or file_cfg.get("discord_webhook", "")
    tele_tok  = vault.get_secret("TELEGRAM_BOT_TOKEN")  or os.getenv("TELEGRAM_BOT_TOKEN")  or file_cfg.get("telegram_token", "")
    tele_chat = vault.get_secret("TELEGRAM_CHAT_ID")    or os.getenv("TELEGRAM_CHAT_ID")    or file_cfg.get("telegram_chat_id", "")

    return {
        "discord_webhook":  discord,
        "telegram_token":   tele_tok,
        "telegram_chat_id": tele_chat,
        "default_channels": file_cfg.get("default_channels", ["discord"]),
    }


def save_notification_config(config_data: Dict[str, Any]) -> bool:
    """Saves notification configuration to JSON and Encrypted Vault."""
    cfg_file = _get_config_file()
    try:
        cfg_file.write_text(json.dumps(config_data, indent=2, ensure_ascii=False), encoding="utf-8")
        if config_data.get("discord_webhook"):
            vault.set_secret("DISCORD_WEBHOOK_URL", config_data["discord_webhook"], description="Discord Webhook URL")
        if config_data.get("telegram_token"):
            vault.set_secret("TELEGRAM_BOT_TOKEN", config_data["telegram_token"], description="Telegram Bot Token")
        if config_data.get("telegram_chat_id"):
            vault.set_secret("TELEGRAM_CHAT_ID", config_data["telegram_chat_id"], description="Telegram Chat/Channel ID")
        return True
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# 1. Discord Webhook
# ─────────────────────────────────────────────────────────────────────────────

def send_discord_notification(
    webhook_url: str,
    title: str,
    message: str,
    urgency: NotificationUrgency = NotificationUrgency.INFO,
    image_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Sends a rich embedded notification card to a Discord webhook."""
    color = _URGENCY_COLORS.get(urgency, 3447003)
    embed: Dict[str, Any] = {
        "title":       f"🤖 {title}",
        "description": message,
        "color":       color,
        "fields": [
            {"name": "Urgency", "value": urgency.value.upper(), "inline": True},
            {"name": "Host",    "value": platform.node(),        "inline": True},
        ],
        "footer": {"text": f"KURO 2.0 • {time.strftime('%Y-%m-%d %H:%M:%S')}"},
    }
    if image_url:
        embed["image"] = {"url": image_url}

    payload = {
        "username":   "KURO Agent",
        "avatar_url": "https://raw.githubusercontent.com/Abdo-omran2206/KuroAgent/main/assets/kuro_icon.png",
        "embeds":     [embed],
    }

    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            webhook_url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "KURO-Assistant/2.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"success": resp.status in (200, 204), "channel": "discord", "status": resp.status}
    except urllib.error.HTTPError as e:
        try:
            err_msg = json.loads(e.read().decode("utf-8")).get("message", str(e))
        except Exception:
            err_msg = str(e)
        return {"success": False, "channel": "discord", "error": f"Discord HTTP {e.code}: {err_msg}"}
    except Exception as e:
        return {"success": False, "channel": "discord", "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# 2. Telegram Bot & Channel
# ─────────────────────────────────────────────────────────────────────────────

def send_telegram_notification(
    bot_token: str,
    chat_id: str,
    title: str,
    message: str,
    urgency: NotificationUrgency = NotificationUrgency.INFO,
    image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends a formatted notification to a Telegram user, group, or channel.
    Uses HTML formatting with automatic escaping to prevent parsing crashes.
    """
    from kurocode.integrations.telegram_integration import TelegramIntegration
    tg = TelegramIntegration()
    if not tg.is_connected or tg.bot_token != bot_token:
        tg.connect({"token": bot_token, "chat_id": chat_id})

    badge = {
        NotificationUrgency.INFO:     "ℹ️",
        NotificationUrgency.SUCCESS:  "✅",
        NotificationUrgency.WARNING:  "⚠️",
        NotificationUrgency.CRITICAL: "🚨",
        NotificationUrgency.ALERT:    "🔔",
    }.get(urgency, "🔔")

    formatted_title = f"{badge} {title}"

    if image_path:
        caption = (
            f"<b>{html.escape(formatted_title)}</b>\n\n"
            f"{html.escape(message)}\n\n"
            f"<code>[{urgency.value.upper()} | {time.strftime('%H:%M:%S')}]</code>"
        )
        return tg.send_photo(photo_path_or_url=image_path, caption=caption, chat_id=chat_id)
    else:
        body = f"{message}\n\n<code>[{urgency.value.upper()} | {time.strftime('%H:%M:%S')}]</code>"
        return tg.send_message(text=body, title=formatted_title, chat_id=chat_id, parse_mode="HTML")


# ─────────────────────────────────────────────────────────────────────────────
# 3. Smart Multi-Channel Dispatcher
# ─────────────────────────────────────────────────────────────────────────────

def send_smart_notification(
    title: str,
    message: str,
    urgency: NotificationUrgency = NotificationUrgency.INFO,
    channels: Optional[List[str]] = None,
    speak: bool = False,          # kept for API compat, no-op now
    sound: str = "default",       # kept for API compat, no-op now
    target_override: Optional[str] = None,
    image_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Dispatches notifications to Discord and/or Telegram.
    `speak` and `sound` parameters are accepted but ignored (voice removed).
    """
    cfg = load_notification_config()
    target_channels = [c.lower() for c in (channels or cfg.get("default_channels", ["discord"]))]

    results: Dict[str, Any] = {"title": title, "urgency": urgency.value, "dispatched": {}}

    # Discord
    if "discord" in target_channels or "all" in target_channels:
        url = (
            target_override
            if (target_override and str(target_override).startswith("http"))
            else cfg.get("discord_webhook")
        )
        if url:
            results["dispatched"]["discord"] = send_discord_notification(url, title, message, urgency=urgency)
        elif "discord" in target_channels:
            results["dispatched"]["discord"] = {"success": False, "error": "Discord webhook URL not configured."}

    # Telegram
    if "telegram" in target_channels or "tg" in target_channels or "all" in target_channels:
        bot_tok   = cfg.get("telegram_token")
        target_chat = target_override or cfg.get("telegram_chat_id")
        if bot_tok and target_chat:
            results["dispatched"]["telegram"] = send_telegram_notification(
                bot_tok, target_chat, title, message, urgency=urgency, image_path=image_path
            )
        elif "telegram" in target_channels:
            missing = []
            if not bot_tok:     missing.append("token")
            if not target_chat: missing.append("chat_id")
            results["dispatched"]["telegram"] = {
                "success": False,
                "error": f"Telegram missing: {', '.join(missing)}. Use /notify config telegram <BOT_TOKEN> <CHAT_ID>.",
            }

    results["success"] = (
        any(r.get("success", False) for r in results["dispatched"].values())
        or len(results["dispatched"]) == 0
    )
    return results


def diagnose_channel(channel_name: str, target: Optional[str] = None) -> Dict[str, Any]:
    """
    Runs diagnostic inspection on a notification channel.
    """
    cfg = load_notification_config()
    chan = channel_name.lower()

    if chan in ("telegram", "tg"):
        from kurocode.integrations.telegram_integration import TelegramIntegration
        tg = TelegramIntegration()
        token = cfg.get("telegram_token")
        if not token:
            return {
                "channel":  "telegram",
                "connected": False,
                "error":    "No Telegram Bot Token configured.",
                "solution": "1. Create a bot with @BotFather on Telegram.\n2. Run: /notify config telegram <BOT_TOKEN> <CHAT_ID>",
            }
        chat_target = target or cfg.get("telegram_chat_id")
        if not chat_target:
            return {
                "channel":  "telegram",
                "connected": tg.is_connected,
                "bot":      tg.account_name,
                "error":    "Bot token valid, but no Chat ID configured.",
                "solution": (
                    "• For a channel: set chat_id to @your_channel or -100xxxxxxxxxx.\n"
                    "• Add your bot as Administrator with 'Post Messages' enabled.\n"
                    "• For private chat: send /start to your bot and use your numeric user ID."
                ),
            }
        diag = tg.diagnose_chat_or_channel(chat_target)
        return {"channel": "telegram", "connected": tg.is_connected, "bot": tg.account_name, "target": chat_target, "diagnosis": diag}

    if chan == "discord":
        url = target or cfg.get("discord_webhook")
        if not url:
            return {"channel": "discord", "connected": False, "error": "No Discord webhook URL configured."}
        return {"channel": "discord", "connected": True, "target": url[:30] + "..."}

    return {"channel": chan, "error": f"Unknown channel '{channel_name}'. Supported: telegram, discord"}


# Backward-compat alias
def send_webhook_notification(webhook_url: str, title: str, message: str) -> Dict[str, Any]:
    return send_discord_notification(webhook_url, title, message)

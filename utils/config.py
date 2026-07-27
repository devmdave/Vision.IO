import keyring
from datetime import date
from PySide6.QtCore import QSettings

SERVICE_NAME = "VisionIO_Desktop"

def _get_settings():
    return QSettings("VisionIO", "VisionIO_Desktop")

def get_api_key(provider_key_name: str) -> str:
    """
    Retrieve API key from keyring.
    provider_key_name can be 'gemini_api_key', 'openai_api_key', 'custom_api_key', 'telegram_bot_token'.
    """
    try:
        val = keyring.get_password(SERVICE_NAME, provider_key_name)
        return val if val else ""
    except Exception as e:
        print(f"[Config] Error reading key {provider_key_name} from keyring: {e}")
        return ""

def set_api_key(provider_key_name: str, key_val: str):
    """
    Save API key to keyring.
    """
    try:
        if key_val is None or key_val.strip() == "":
            try:
                keyring.delete_password(SERVICE_NAME, provider_key_name)
            except keyring.errors.PasswordDeleteError:
                pass
        else:
            keyring.set_password(SERVICE_NAME, provider_key_name, key_val)
    except Exception as e:
        print(f"[Config] Error writing key {provider_key_name} to keyring: {e}")

# Non-sensitive parameters
def get_selected_provider() -> str:
    return _get_settings().value("selected_provider", "Google Gemini")

def set_selected_provider(val: str):
    _get_settings().setValue("selected_provider", val)

def get_selected_model() -> str:
    # We default based on the provider if not set
    settings = _get_settings()
    val = settings.value("selected_model", "")
    if not val:
        provider = get_selected_provider()
        if provider == "Google Gemini":
            return "gemini-3.5-flash"
        elif provider == "OpenAI":
            return "gpt-4o-mini"
        else:
            return "custom-model"
    return val

def set_selected_model(val: str):
    _get_settings().setValue("selected_model", val)

def get_custom_base_url() -> str:
    return _get_settings().value("custom_base_url", "")

def set_custom_base_url(val: str):
    _get_settings().setValue("custom_base_url", val)

def get_max_daily_api_calls() -> int:
    try:
        return int(_get_settings().value("max_daily_api_calls", 500))
    except (ValueError, TypeError):
        return 500

def set_max_daily_api_calls(val: int):
    _get_settings().setValue("max_daily_api_calls", val)

def get_telegram_chat_id() -> str:
    return _get_settings().value("telegram_chat_id", "")

def set_telegram_chat_id(val: str):
    _get_settings().setValue("telegram_chat_id", val)

# Daily Usage Management
def check_and_reset_daily_usage() -> int:
    settings = _get_settings()
    today_str = date.today().isoformat()
    last_date = settings.value("last_usage_date", "")
    
    if last_date != today_str:
        settings.setValue("last_usage_date", today_str)
        settings.setValue("daily_usage_counter", 0)
        return 0
    try:
        return int(settings.value("daily_usage_counter", 0))
    except (ValueError, TypeError):
        return 0

def increment_daily_usage() -> int:
    settings = _get_settings()
    current = check_and_reset_daily_usage()
    current += 1
    settings.setValue("daily_usage_counter", current)
    return current

def get_daily_usage() -> int:
    return check_and_reset_daily_usage()

# --- Discord Notification Configuration ---
def get_discord_enabled() -> bool:
    return _get_settings().value("discord_enabled", "false") == "true"

def set_discord_enabled(val: bool):
    _get_settings().setValue("discord_enabled", "true" if val else "false")

def get_discord_webhook_url() -> str:
    url = _get_settings().value("discord_webhook_url", "")
    if not url:
        import os
        url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    return url

def set_discord_webhook_url(val: str):
    _get_settings().setValue("discord_webhook_url", val)

# --- SMTP Email Configuration ---
def get_email_enabled() -> bool:
    return _get_settings().value("email_enabled", "false") == "true"

def set_email_enabled(val: bool):
    _get_settings().setValue("email_enabled", "true" if val else "false")

def get_smtp_server() -> str:
    return _get_settings().value("smtp_server", "")

def set_smtp_server(val: str):
    _get_settings().setValue("smtp_server", val)

def get_smtp_port() -> int:
    try:
        return int(_get_settings().value("smtp_port", 587))
    except (ValueError, TypeError):
        return 587

def set_smtp_port(val: int):
    _get_settings().setValue("smtp_port", val)

def get_smtp_sender_email() -> str:
    return _get_settings().value("smtp_sender_email", "")

def set_smtp_sender_email(val: str):
    _get_settings().setValue("smtp_sender_email", val)

def get_smtp_recipient_email() -> str:
    return _get_settings().value("smtp_recipient_email", "")

def set_smtp_recipient_email(val: str):
    _get_settings().setValue("smtp_recipient_email", val)


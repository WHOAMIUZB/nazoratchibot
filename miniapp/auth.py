import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from fastapi import Header, HTTPException

from config import BOT_TOKEN

INIT_DATA_MAX_AGE = 86400  # 24 soat


def validate_init_data(init_data: str, max_age_seconds: int = INIT_DATA_MAX_AGE) -> dict:
    """
    Telegram Mini App yuborgan initData satrini tekshiradi (Telegramning rasmiy algoritmi bo'yicha)
    va ichidagi foydalanuvchi ma'lumotini (dict) qaytaradi.
    Bu tekshiruv orqali faqat HAQIQIY Telegram orqali ochilgan so'rovlar qabul qilinadi — soxta
    user_id yuborib boshqa birovning nomidan amal qilish imkonsiz bo'ladi.
    """
    if not init_data:
        raise HTTPException(status_code=401, detail="initData yo'q")

    try:
        pairs = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        raise HTTPException(status_code=401, detail="initData formati noto'g'ri")

    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="hash yo'q")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise HTTPException(status_code=401, detail="Imzo noto'g'ri — bu so'rov Telegramdan kelmagan")

    auth_date = int(pairs.get("auth_date", "0"))
    if max_age_seconds and (time.time() - auth_date) > max_age_seconds:
        raise HTTPException(status_code=401, detail="initData muddati o'tgan, ilovani qayta oching")

    user_json = pairs.get("user")
    if not user_json:
        raise HTTPException(status_code=401, detail="Foydalanuvchi ma'lumoti yo'q")

    return json.loads(user_json)


async def get_current_user(x_telegram_init_data: str = Header(..., alias="X-Telegram-Init-Data")) -> dict:
    return validate_init_data(x_telegram_init_data)

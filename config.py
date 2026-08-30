import os

# --- Asosiy sozlamalar ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "8868993362:AAF3HS6NrXef2Sqpmr0ThksvZghS-cqGlJw")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7861165622").split(",") if x]

DB_PATH = os.getenv("DB_PATH", "books.db")

# Har bir "sahifa" necha belgidan iborat bo'lishi (ichki o'qish rejimi uchun)
PAGE_CHARS = 900

# XP (ballar) qoidalari
XP_FOR_DOWNLOAD = 2
XP_FOR_REVIEW = 5
XP_FOR_QUIZ_CORRECT = 3
XP_FOR_REFERRAL = 10

# Kunlik eslatma vaqti (soat:daqiqa, server vaqti bo'yicha, UTC)
DEFAULT_REMINDER_HOUR = 18
DEFAULT_REMINDER_MINUTE = 0

BOOK_CLUB_CHAT_LINK = os.getenv("BOOK_CLUB_CHAT_LINK", "https://t.me/+your_invite_link_here")

SUPPORTED_LANGUAGES = ["uz", "ru", "en"]
DEFAULT_LANGUAGE = "uz"

# --- Web panel sozlamalari ---
WEBPANEL_USERNAME = os.getenv("WEBPANEL_USERNAME", "Zoirbek")
WEBPANEL_PASSWORD = os.getenv("WEBPANEL_PASSWORD", "zoirbek2003")
SESSION_SECRET = os.getenv("SESSION_SECRET", "please-change-this-secret-key-in-production")
WEBPANEL_PORT = int(os.getenv("PORT", os.getenv("WEBPANEL_PORT", "25944")))

# --- Telegram Mini App sozlamalari ---
MINIAPP_PORT = int(os.getenv("MINIAPP_PORT", "25767"))
MINIAPP_URL = "http://localhost:8000"  # o'zingizning portingiz yoki domeningiz
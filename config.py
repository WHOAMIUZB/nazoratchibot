import os
from dotenv import load_dotenv

load_dotenv()

# .env faylidan o'qiydi, topilmasa quyidagi standart qiymatlardan foydalanadi.
BOT_TOKEN = os.getenv("BOT_TOKEN", "8559867257:AAFLaqVNEgECfE5ka4jOcvSlPaKrReg1V4o")
SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID", "7861165622"))
BOT_USERNAME = os.getenv("BOT_USERNAME", "Nazoratchi_uzbekrobot")

DB_PATH = os.getenv("DB_PATH", "nazoratchi.db")

# Avtomatik vazifalar oralig'i (soniyalarda)
DELETED_ACCOUNTS_CHECK_INTERVAL = 30 * 60      # 30 daqiqa
CHANNEL_STATS_INTERVAL = 12 * 60 * 60          # 12 soat

# Standart cheklov qiymatlari
WARN_LIMIT = 3
WARN_BAN_DAYS = 3
LINK_LIMIT_PER_DAY = 3
LINK_MUTE_HOURS = 2

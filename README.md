# Nazoratchi Bot — Kanal va Guruh nazoratchisi

Telegram kanallari va guruhlarini professional darajada boshqarish uchun bot.
Bot: **@Nazoratchi_uzbekrobot**

## 📦 Nima qilingan

### Kanal uchun ("📡 Kanalim" bo'limi)
- Kanalni bot admin qilib qo'shilganda avtomatik ro'yxatga tushadi
- 🧹 **O'chirilgan hisoblarni tozalash** — yoqilsa, har **30 daqiqada** kanaldagi
  (bot admin bo'lgandan keyingi) obunachilar orasidan o'chirilgan Telegram
  hisoblari avtomatik chiqarib yuboriladi
- 📊 **Statistika** — yoqilsa, har **12 soatda** kanal egasiga qo'shilgan/chiqib
  ketgan obunachilar statistikasi yuboriladi
- Kanalni ro'yxatdan olib tashlash imkoni

### Guruh uchun (faqat guruh adminlari ishlatadi)
| Buyruq | Vazifasi |
|---|---|
| `/warn` (reply) | Ogohlantirish + xabarni o'chirish. 3/3 bo'lganda 3 kunga yoza olmaydigan qiladi |
| `/mute N` (reply) | N soatga mute qiladi va xabarni o'chiradi |
| `/ban` (reply) | Foydalanuvchini guruhdan bloklaydi |
| `/unmute` (reply) | Barcha cheklov/ogohlantirish/odam talabini bekor qiladi |
| `/forward` | Forward (uzatilgan) xabarlarni taqiqlash yoqish/o'chirish |
| `/link` | Havola cheklovi: kuniga 3 tadan ortiq havola → 2 soatga mute |
| `/salom` | Yangi a'zolar bilan avtomatik salomlashish yoqish/o'chirish |
| `/tozala` | "X guruhga qo'shildi" xabarlarini avtomatik o'chirish yoqish/o'chirish |
| `/odam N` (reply) | N kishi taklif qilmaguncha yoza olmaslik cheklovi |

### Bot admini uchun (`/admin` yoki bosh menyudan)
- 📢 Broadcast — foydalanuvchilar / guruhlar / kanallarga ommaviy xabar
- 📊 Umumiy statistika (foydalanuvchilar, guruhlar, kanallar soni)
- 👥 Guruhlar ro'yxati (a'zolar soni bilan)
- 📡 Kanallar ro'yxati (obunachilar soni bilan)
- ➕➖ Admin qo'shish / adminlikdan olish

---

## ⚠️ Muhim texnik cheklov (albatta o'qing)

Telegram Bot API orqali kanal yoki guruhning **to'liq a'zolari ro'yxatini
olib bo'lmaydi** — bu Telegramning o'zining API cheklovi, hech qanday bot
buni chetlab o'ta olmaydi. Shu sababli:

- "O'chirilgan hisoblarni tozalash" va statistika funksiyalari faqat bot
  **admin qilib qo'shilgandan keyin** kuzatilgan a'zolar bo'yicha ishlaydi.
  Eski (bot qo'shilishidan oldingi) obunachilarni bot "ko'ra olmaydi".
- "/odam" funksiyasi kimning kimni taklif qilganini Telegram
  bergan `chat_member` yangilanishi orqali aniqlaydi — bu ba'zan (masalan,
  ochiq invite-link orqali kirilganda) noaniq bo'lishi mumkin.

Bular loyihaning kamchiligi emas, balki Telegramning barcha botlar uchun
umumiy arxitektura cheklovi.

---

## 🚀 O'rnatish (VPS / server, Ubuntu misolida)

```bash
# 1. Python 3.11+ borligiga ishonch hosil qiling
python3 --version

# 2. Loyiha papkasiga o'ting va virtual muhit yarating
cd nazoratchi_bot
python3 -m venv venv
source venv/bin/activate

# 3. Kutubxonalarni o'rnating
pip install -r requirements.txt

# 4. .env faylini sozlang
cp .env.example .env
nano .env   # BOT_TOKEN va SUPER_ADMIN_ID ni tekshiring

# 5. Botni ishga tushiring
python main.py
```

Bot muvaffaqiyatli ishga tushsa, terminalda quyidagiga o'xshash loglar
ko'rinadi:
```
INFO | ... | Scheduler ishga tushdi.
INFO | ... | Bot polling rejimida ishga tushmoqda...
```

## 🔁 24/7 ishlashi uchun (systemd)

`/etc/systemd/system/nazoratchi-bot.service` faylini yarating:

```ini
[Unit]
Description=Nazoratchi Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/nazoratchi_bot
ExecStart=/root/nazoratchi_bot/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Keyin:
```bash
sudo systemctl daemon-reload
sudo systemctl enable nazoratchi-bot
sudo systemctl start nazoratchi-bot
sudo systemctl status nazoratchi-bot   # holatini tekshirish
journalctl -u nazoratchi-bot -f        # loglarni kuzatish
```

---

## 🗂 Loyiha tuzilishi

```
nazoratchi_bot/
├── main.py                  # Botni ishga tushirish
├── config.py                 # Token va sozlamalar (.env dan o'qiydi)
├── database.py                # SQLite bilan ishlash (barcha DB funksiyalari)
├── keyboards.py               # Inline tugmalar
├── utils.py                   # Yordamchi funksiyalar (mute/unmute va h.k.)
├── handlers/
│   ├── start.py                # /start, asosiy menyu, "Kanalim" bo'limi
│   ├── chat_events.py           # Bot kanal/guruhga qo'shilganda ishlaydi
│   ├── group_moderation.py      # /warn /mute /ban /forward /link va h.k.
│   └── admin_panel.py           # Bot admini paneli, broadcast
├── services/
│   └── scheduler.py             # 30 daqiqalik va 12 soatlik fon vazifalar
├── requirements.txt
├── .env.example
└── nazoratchi.db               # SQLite baza (avtomatik yaratiladi)
```

---

## 🔐 Xavfsizlik bo'yicha eslatma

`BOT_TOKEN` ni hech kimga bermang va ochiq GitHub repolarga yuklamang.
Xavfsizlik uchun tokenni faqat `.env` faylida saqlang (`.env` faylini
`.gitignore` ga qo'shing). Agar token oshkor bo'lgan bo'lsa,
@BotFather orqali `/revoke` qilib yangisini oling.

## 🧪 Sinov haqida

Ushbu kod barcha handlerlar, ma'lumotlar bazasi funksiyalari va
klaviaturalar bo'yicha sintaksis va import darajasida sinovdan
o'tkazilgan. Lekin haqiqiy Telegram serverlariga ulanib to'liq
ishlashini tekshirish uchun uni o'zingizning serveringizda ishga
tushirishingiz kerak (bu muhitda tashqi tarmoqqa — jumladan
Telegram API'ga — chiqish imkoni yo'q).

## 💡 Keyingi qadam sifatida qo'shsa bo'ladigan funksiyalar

- So'kinish/spam so'zlarni avtomatik filtrlash (taqiqlangan so'zlar ro'yxati)
- Captcha — yangi a'zolarni robot emasligini tekshirish
- Guruh ichida reyting/faollik statistikasi
- Kanal postlarini rejalashtirish (scheduled posts)
- Bir nechta til qo'llab-quvvatlash (uz/ru/en)

Shu funksiyalardan birortasini qo'shishni xohlasangiz, ayting — davom
ettiraman.

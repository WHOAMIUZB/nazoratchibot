# 🖥 Web panel — to‘liq qo‘llanma

Bu hujjat web panelni **ishga tushirish** va **har bir funksiyadan qanday foydalanish**ni
boshidan oxirigacha tushuntiradi.

---

## 1. Arxitektura — qanday ishlaydi

Endi loyihada **bitta** Python jarayoni (`python main.py`) ikkita narsani baravar ishga tushiradi:

1. **Telegram bot** — foydalanuvchilar bilan gaplashadi (polling rejimida)
2. **Web panel** (FastAPI) — brauzerdan boshqarish uchun sayt, o'z alohida portida (masalan `25944`) ochiladi
3. **Mini App** — foydalanuvchilar uchun, yana boshqa alohida portda (masalan `25767`) ochiladi — batafsili `MINIAPP_GUIDE.md`da

Ikkalasi ham **bitta** `books.db` faylini ishlatadi — ya'ni web panelda qilgan har qanday
o‘zgarishingiz (kitob qo‘shish, foydalanuvchini bloklash va h.k.) botda **darhol** aks etadi, va
aksincha. Alohida ikkita server yoki ikkita baza sozlashning hojati yo‘q.

---

## 2. O‘rnatish

```bash
cd kitoblar_bot
pip install -r requirements.txt
```

`.env.example` faylidan nusxa olib `.env` yarating (yoki shu qiymatlarni to‘g‘ridan-to‘g‘ri
Render/server muhitiga environment variable sifatida kiriting):

```bash
cp .env.example .env
```

`.env` faylini oching va **albatta** quyidagilarni o‘zgartiring:

| O‘zgaruvchi | Nima uchun |
|---|---|
| `WEBPANEL_USERNAME` | Web panelga kirish logini |
| `WEBPANEL_PASSWORD` | Web panelga kirish paroli — **kuchli parol qo‘ying**, bu tashqi internetga ochiq sahifa |
| `SESSION_SECRET` | Tasodifiy uzun matn (masalan `openssl rand -hex 32` bilan yarating) |
| `WEBPANEL_PORT` | Web panel qaysi portda ochilishi (masalan `25944`) |
| `MINIAPP_PORT` | Mini App qaysi portda ochilishi (masalan `25767`) — alohida, web paneldan mustaqil |

⚠️ **Muhim:** `WEBPANEL_PASSWORD` ni o‘zgartirmasangiz, standart parol (`change_me_123`) bilan
qoladi va istalgan kishi panelga kirib qolishi mumkin.

---

## 3. Ishga tushirish

```bash
python main.py
```

Konsolda quyidagiga o‘xshash qatorlarni ko‘rasiz:

```
INFO:aiogram.dispatcher:Run polling for bot @Kitobxon_Kutubxona_bot
INFO:     Uvicorn running on http://0.0.0.0:25944   (web panel)
INFO:     Uvicorn running on http://0.0.0.0:25767   (mini app)
```

Bu — bot ham, web panel ham parallel ishga tushdi degani. Endi brauzerda oching:

- Mahalliy kompyuterda sinash uchun: `http://localhost:25944`
- Serverda: `http://45.131.65.107:25944`

---

## 4. Kirish (Login)

Ochilgan sahifada `.env` faylida ko‘rsatgan **login** va **parol**ni kiriting.
Muvaffaqiyatli kirgach, chap tomonda navigatsiya menyusi bilan Dashboard ochiladi.

---

## 5. Har bir bo‘lim nima qiladi va qanday ishlatiladi

### 📊 Dashboard (bosh sahifa)
- Jami foydalanuvchilar, bugun qo‘shilganlar, jami kitoblar soni — bir qarashda
- TOP-5 eng ko‘p yuklab olingan kitoblar
- So‘nggi 5 ta fikr-mulohaza
- Agar bazada bir xil nom+muallif bilan bir nechta kitob bo‘lsa — shu yerda ogohlantirish sifatida chiqadi (dublikat detektori)

### 📚 Kitoblar
- **Ro‘yxat**: barcha kitoblar, qidiruv maydoni orqali nom/muallif bo‘yicha qidirish
- **➕ Yangi kitob**: formani to‘ldirasiz (nomi, muallif, janr, yil, tavsif, Premium belgisi) va
  faylni (PDF/EPUB) tanlaysiz → **Saqlash** bosasiz.
  - Fayl avtomatik ravishda Telegram serveriga (birinchi admin bilan shaxsiy chatga) yuboriladi
    va olingan `file_id` bazaga saqlanadi — xuddi botdagi `/addbook` kabi ishlaydi.
  - ⚠️ Bu ishlashi uchun **admin bot bilan kamida bir marta `/start` bosgan bo‘lishi shart**
    (aks holda "chat not found" xatosi chiqadi).
- **✏️ (qalam belgisi)**: kitobni tahrirlash — istalgan maydonni o‘zgartirish, xohlasangiz yangi fayl ham yuklash mumkin
- **📄**: kitobning "onlayn o‘qish" matnini (bot ichida sahifalab o‘qiladigan versiyasini) qo‘shish/tahrirlash
- **🗄 (arxiv belgisi)**: kitobni vaqtincha yashirish (o‘chirmasdan) — foydalanuvchilarga ko‘rinmay qoladi
- **🗑**: kitobni butunlay o‘chirish (tasdiqlash so‘raladi)

### 📁 Janrlar
- Chap tomonda mavjud janrlar ro‘yxati (asosiy va subjanrlar)
- O‘ng tomondagi forma orqali yangi janr qo‘shasiz — agar "Ota janr" tanlasangiz, u subjanr bo‘lib qo‘shiladi (masalan Badiiy adabiyot → Detektiv)
- 🗑 orqali o‘chirish — o‘chirilgan janrdagi kitoblar "janrsiz" holatda qoladi (yo‘qolmaydi)

### 👥 Foydalanuvchilar
- Qidiruv orqali ID, username yoki ism bo‘yicha topish
- **Batafsil** tugmasi orqali foydalanuvchi profiliga kirasiz:
  - To‘liq ma'lumot, sevimlilar ro‘yxati, so‘nggi faoliyat tarixi
  - **🚫 Bloklash / ✅ Blokdan chiqarish**
  - **💎 XP o‘zgartirish** — istalgan songa qo‘lda o‘rnatish
  - **✉️ Shaxsiy xabar yuborish** — to‘g‘ridan-to‘g‘ri shu foydalanuvchiga botdan xabar boradi

### 📢 Xabar yuborish (Broadcast)
- Matn yozasiz, xohlasangiz rasm qo‘shasiz
- **Yuborish** bosilganda, bloklanmagan **barcha** foydalanuvchilarga yuboriladi
- Yuborilgandan so‘ng "✅ Yuborildi: X ta / ❌ Xato: Y ta" statistikasi ko‘rsatiladi

### 🎁 Promo-kodlar
- Mavjud kodlar va qolgan foydalanish sonlari ro‘yxati
- Yangi kod yaratish: kod matni, necha XP berilishi, nechta kishi ishlata olishi

### ❓ Viktorina
- Mavjud savollar ro‘yxati (🗑 orqali o‘chirish mumkin)
- Yangi savol qo‘shish: kitobga bog‘lash (yoki umumiy qoldirish), 2-4 variant va to‘g‘ri javobni belgilash

### 🌟 Sharhlar
- Foydalanuvchilar tomonidan yozilgan barcha sharh va baholar
- Nomaqbul sharhni 🗑 orqali o‘chirish (kitobning umumiy reytingi avtomatik qayta hisoblanadi)

### 💬 Fikr-mulohaza
- Foydalanuvchilardan kelgan taklif/shikoyatlar
- "✅ Hal qilindi deb belgilash" — ko‘rib chiqilgan xabarlarni belgilab qo‘yish uchun

### 📈 Analitika
- Foydalanuvchilar o‘sishi va kunlik faollik (DAU) grafiklari — oxirgi 30 kun
- Eng ko‘p qidirilgan so‘zlar ro‘yxati (bu orqali foydalanuvchilar qanday kitob izlayotganini, lekin topolmayotganini ko‘rasiz — bazani shunga qarab boyitish mumkin)
- TOP-10 kitoblar
- Dublikat kitoblar ro‘yxati

### ⚙️ Sozlamalar
- Kitobxonlar klubi havolasini o‘zgartirish
- Standart kunlik eslatma vaqtini o‘zgartirish
- **🔧 Texnik tanaffus rejimi** — belgilab saqlasangiz, admin bo‘lmagan barcha foydalanuvchilar
  botga har qanday xabar yozganda "texnik tanaffus" degan javob oladi (bot butunlay to‘xtamaydi,
  faqat oddiy foydalanuvchilar vaqtincha cheklanadi). Darhol kuchga kiradi, botni qayta ishga
  tushirish shart emas.

### 🧾 Audit jurnali
- Web panel orqali qilingan muhim amallar (kitob qo‘shish/tahrirlash/o‘chirish, broadcast) qachon
  sodir bo‘lgani haqida yozuvlar

### 💾 Backup yuklash
- Bir tugma bosish bilan butun `books.db` faylini kompyuteringizga yuklab olasiz — zaxira nusxa uchun

---

## 6. Render.com'ga joylash (bot + web panel birga)

Ilgari aytilganidek, bot va web panel **bitta** jarayonda ishlaydi, shuning uchun Render'da
**bitta Web Service** yaratish kifoya (alohida Background Worker kerak emas):

1. Repo'ni GitHub'ga joylang
2. Render'da **Web Service** yarating
3. Build command: `pip install -r requirements.txt`
4. Start command: `python main.py`
5. Environment Variables bo‘limiga `.env.example`dagi barcha qiymatlarni kiriting
   (Render `PORT` o‘zgaruvchisini avtomatik beradi — uni qo‘lda kiritmang, kod o‘zi o‘qiydi)
6. **Persistent Disk** qo‘shing va uni loyihaning ishchi papkasiga bog‘lang — aks holda har deploy'da
   `books.db` (barcha kitoblar, foydalanuvchilar) o‘chib ketadi
7. Deploy tugagach, Render bergan domenni oching (masalan `https://kitoblar-bot.onrender.com`) —
   shu manzil endi ham botning "orqa fon"i, ham sizning web panelingiz

---

## 7. Xavfsizlik bo‘yicha eslatmalar

- Web panel manzilini hech kimga tarqatmang, faqat siz bilishingiz kerak
- `WEBPANEL_PASSWORD` va `SESSION_SECRET`ni albatta standart qiymatdan o‘zgartiring
- Agar imkoni bo‘lsa, Render'da custom domen + avtomatik HTTPS yoqilganini tekshiring
  (Render standart holatda HTTPS beradi)
- Login sessiyasi brauzer cookie orqali saqlanadi — umumiy/notanish kompyuterda kirgandan so‘ng
  albatta **🚪 Chiqish** tugmasini bosing

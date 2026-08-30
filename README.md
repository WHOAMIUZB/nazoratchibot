# 📚 Kitoblar bot

Aiogram 3.x + aiosqlite asosidagi to‘liq funksional kitob qidirish/o‘qish Telegram boti.

## O‘rnatish

```bash
pip install -r requirements.txt
python main.py
```

Bot tokeni va admin ID `config.py` ichida allaqachon sozlangan (talabingizga ko‘ra o‘zgartirilmadi).
Agar boshqa muhitda (Render.com) ishlatmoqchi bo‘lsangiz, `BOT_TOKEN` va `ADMIN_IDS` env-o‘zgaruvchilarini
belgilashingiz ham mumkin — `.env.example` faylga qarang.

## Render.com'ga joylash

1. Bu papkani GitHub repo qiling.
2. Render'da "Background Worker" turida yangi xizmat yarating (bot polling rejimida ishlaydi, web server kerak emas).
3. Build command: `pip install -r requirements.txt`
4. Start command: `python main.py`
5. Environment: `BOT_TOKEN`, `ADMIN_IDS` (xohlasangiz — bo‘lmasa `config.py`dagi default ishlatiladi).
6. Disk: SQLite fayli (`books.db`) saqlanib qolishi uchun Render'da Persistent Disk qo‘shing (aks holda deploy paytida baza tozalanadi).

## Foydalanuvchi funksiyalari (barchasi ishlaydi)

- 🔎 Matnli qidiruv (nomi/muallif)
- 📂 Ierarxik janrlar katalogi (janr → subjanr → kitoblar)
- 🔁 O‘xshash kitoblar tavsiyasi
- 📱 Onlayn o‘qish (bot ichida sahifama-sahifa, Next/Prev tugmalar bilan — matnli kitoblar uchun)
- ⬇️ Faylni yuklab olish (PDF/EPUB, Telegram file_id orqali)
- ⭐ Sevimlilar
- 🕘 Qidiruv/ko‘rish/o‘qish tarixi
- 📖 Shaxsiy kutubxona (O‘qilmoqda / O‘qib bo‘lingan / Rejadagi)
- 📄 O‘qish progressi (sahifa saqlanadi)
- 🌐 3 tilli interfeys (uz/ru/en)
- ✍️ Fikr-mulohaza (to‘g‘ridan-to‘g‘ri adminga yetadi)
- 🌟 Reyting va sharh (5 yulduz + izoh)
- 🔥 TOP-10 (eng ko‘p yuklab olingan)
- 💬 Kitobxonlar klubi (tashqi chat havolasi — config.py'da o‘zgartiring)
- 🎮 Viktorina (savol-javob, XP beriladi)
- 💎 Ballar tizimi (XP): yuklab olish, sharh, viktorina, referal uchun
- 🎁 Promo-kodlar
- 🔔 Janrga obuna bo‘lish → yangi kitob qo‘shilganda avtomatik xabar
- ⏰ Kunlik o‘qish eslatmasi (yoqish/o‘chirish + vaqt)
- 📬 Haftalik dayjest (har dushanba, eng yaxshi kitoblar)
- 👥 Referal dastur (do‘stni taklif qilsa referalga +10 XP)

## Admin funksiyalari (bot ichida, /admin buyrug‘i)

- `/addbook` — yangi kitob qo‘shish (janr → nom → muallif → yil → tavsif → fayl, bosqichma-bosqich)
- `/settext <id>` — onlayn o‘qish uchun kitobning matnli variantini yuklash
- `/editbook` — mavjud kitobni tahrirlash (nom, muallif, tavsif, yil, premium, arxiv)
- `/delbook <id>` — kitobni o‘chirish
- `/addgenre` — yangi janr/subjanr qo‘shish
- `/broadcast` — barcha foydalanuvchilarga ommaviy xabar (matn/rasm/video)
- `/addpromo` — promo-kod yaratish (XP miqdori va foydalanish soni bilan)
- `/addquiz` — viktorina savoli qo‘shish
- `/stats` — statistika (foydalanuvchilar, bugungi yangi, kitoblar, TOP-5)
- `/feedbacks` — foydalanuvchilar fikr-mulohazalarini ko‘rish
- `/block <id>` / `/unblock <id>` — foydalanuvchini bloklash/blokdan chiqarish
- Avtomatik dublikat tekshiruvi — bir xil nom+muallif qayta yuklanganda ogohlantirish

## Keyingi bosqich: Web panel

✅ **Web panel tayyor!** Barcha admin funksiyalari endi brauzer orqali ham boshqariladi.
To‘liq qo‘llanma uchun **`WEBPANEL_GUIDE.md`** faylini o‘qing — u yerda ishga tushirish,
har bir bo‘limdan foydalanish va Render'ga joylash bosqichma-bosqich tushuntirilgan.

Qisqacha: `python main.py` — bitta buyruq bilan bot **va** web panel (`http://localhost:8000`)
bir vaqtda ishga tushadi, ikkalasi ham bitta `books.db` bazasini ishlatadi.

## Mini App — foydalanuvchilar uchun

✅ **Mini App ham tayyor!** Foydalanuvchilar botning barcha funksiyalarini (qidiruv,
janrlar, onlayn o‘qish, sevimlilar, kutubxona, profil, viktorina, promo-kod va h.k.)
chiroyli, mobil-ilova ko‘rinishidagi veb-sahifada — Telegram ichida — ishlata oladi.

To‘liq sozlash yo‘riqnomasi (HTTPS talabi, BotFather bilan bog‘lash va h.k.) uchun
**`MINIAPP_GUIDE.md`** faylini o‘qing.

## Eslatma

- "Onlayn o‘qish" hozircha to‘liq Telegram Mini App (WebView) emas, balki bot ichidagi
  sahifalab ko‘rsatish (matnni bo‘laklarga bo‘lib, Next/Prev tugmalar bilan). To‘liq WebApp-reader
  (shrift o‘lchami, tungi rejim, avto-skroll, TTS, offline PWA-cache) — web panel bosqichida
  alohida Mini App sifatida qo‘shiladi, chunki bularning barchasi hosting qilingan veb-sahifa talab qiladi.
- Premium/pullik kitoblar uchun to‘lov integratsiyasi (Stars/Click/Payme) hali ulanmagan —
  faqat `is_premium` bayrog‘i va qulflash logikasi tayyor; to‘lov provayderini keyingi bosqichda ulaymiz.

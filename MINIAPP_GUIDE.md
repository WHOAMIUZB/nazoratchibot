# 🚀 Mini App — to‘liq sozlash qo‘llanmasi

Bu hujjat foydalanuvchilar uchun yaratilgan **Telegram Mini App**ni ishga tushirish va
sozlashni tushuntiradi. Mini App — bu foydalanuvchilar bot ichida ochadigan, chiroyli
mobil-ilova ko‘rinishidagi veb-sahifa bo‘lib, unda botning **barcha funksiyalari**
(qidiruv, janrlar, onlayn o‘qish, sevimlilar, kutubxona, profil, viktorina, promo-kod va h.k.)
mavjud.

---

## 1. Muhim talab: HTTPS

⚠️ **Telegram Mini App faqat HTTPS (SSL) manzilda ishlaydi.** Oddiy `http://IP:port`
manzili orqali (masalan `http://45.131.65.107:25767`) Mini App **ishlamaydi** — Telegram
buni rad etadi.

Shuning uchun sizga **domen + bepul SSL sertifikat** kerak. Eng oson yo‘llar:

### A) Agar domeningiz bor bo‘lsa (tavsiya etiladi)
`nginx` + `certbot` orqali bepul HTTPS o‘rnatish:

```bash
sudo apt install nginx certbot python3-certbot-nginx -y
```

Nginx konfiguratsiyasi (`/etc/nginx/sites-available/kitoblar-bot`):
```nginx
# Mini App uchun (25767-port)
server {
    listen 80;
    server_name miniapp.saytingiz.uz;

    location / {
        proxy_pass http://127.0.0.1:25767;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Web panel uchun (25944-port) — ixtiyoriy, lekin tavsiya etiladi
server {
    listen 80;
    server_name panel.saytingiz.uz;

    location / {
        proxy_pass http://127.0.0.1:25944;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/kitoblar-bot /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d miniapp.saytingiz.uz -d panel.saytingiz.uz
```

Shundan so‘ng: `https://miniapp.saytingiz.uz` — Mini App, `https://panel.saytingiz.uz` — admin
web panel bo‘ladi. `MINIAPP_URL` sifatida `https://miniapp.saytingiz.uz` yozasiz.

### B) Agar domeningiz yo‘q bo‘lsa (tez sinash uchun)
**Cloudflare Tunnel** (bepul, doimiy ishlaydigan havola beradi):

```bash
# cloudflared o'rnatish
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# vaqtinchalik tunnel (test uchun)
cloudflared tunnel --url http://localhost:25767
```

Bu sizga `https://random-nomi.trycloudflare.com` kabi bepul HTTPS havola beradi — shuni
`MINIAPP_URL` sifatida ishlatishingiz mumkin (test uchun, ishonchli/doimiy foydalanish uchun
Cloudflare’da ro‘yxatdan o‘tib "named tunnel" yaratish tavsiya etiladi).

---

## 2. `.env` faylida MINIAPP_URL’ni sozlang

Sizning holatingizda Mini App **25767**-portda ishlaydi, shuning uchun nginx (yoki Cloudflare
Tunnel) shu portga yo‘naltirilishi kerak. Domeningiz tayyor bo‘lgach:

```env
MINIAPP_URL=https://panel.saytingiz.uz
```

⚠️ Oxirida `/` bo‘lmasin. Endi Mini App statik fayllari ildizda (`/`) xizmat qiladi
(`/app` prefiksi endi kerak emas — u web paneldan butunlay ajratildi va o‘z alohida
portida, `25767`da ishlaydi).

Botni qayta ishga tushiring:
```bash
python main.py
```

Konsolda shu qatorni ko‘rasiz:
```
INFO:root:Mini App menu button o'rnatildi: https://panel.saytingiz.uz/app
```

---

## 3. Foydalanuvchilar Mini App’ni qanday ochadi

Ikki yo‘l bilan:

1. **Botning pastki chap tomonidagi "Menu" tugmasi** (📎 qog‘oz qisqichi yonida) — avtomatik
   ravishda Mini App’ga ulanadi (yuqoridagi sozlashdan keyin)
2. **Asosiy menyudagi "🚀 Mini App orqali ochish" tugmasi** — bot `/start` bosilganda
   chiqadigan pastki klaviaturada ko‘rinadi

Ikkalasi ham `/app` sahifasini Telegram ichida (WebView’da) ochadi.

---

## 4. Mini App’da nima bor

| Bo‘lim | Tavsif |
|---|---|
| 🏠 Bosh sahifa | Qidiruv, tezkor havolalar, TOP-10 |
| 📁 Janrlar | Janr → subjanr → kitoblar |
| 📖 Kitob sahifasi | Muqova, tavsif, o‘qish/yuklab olish, sevimlilar, javon, baholash, o‘xshash kitoblar, sharhlar |
| 📱 Onlayn o‘qish | Sahifama-sahifa o‘qish (Oldingi/Keyingi tugmalar) |
| ⭐ Sevimlilar | Saqlangan kitoblar |
| 📖 Kutubxonam | O‘qilmoqda / O‘qilgan / Rejadagi (3 tab) |
| 🕘 Tarix | Qidiruv/ko‘rish/o‘qish tarixi |
| 👤 Profil | XP, til (uz/ru/en), kunlik eslatma yoqish/o‘chirish |
| 🎮 Viktorina | Savol-javob, XP olish |
| 🎁 Promo-kod | Kodni kiritish orqali XP olish |
| 🔔 Janr obunasi | Har bir janr sahifasida — shu janrga yangi kitob qo‘shilganda avtomatik xabar olish |
| 👥 Do‘stlarni taklif qilish | Shaxsiy referal havola — nusxalash yoki Telegram orqali ulashish, har bir taklif uchun XP |
| 🕐 Eslatma vaqti | Kunlik o‘qish eslatmasi qaysi soatda kelishini o‘zi tanlaydi |
| ✍️ Fikr-mulohaza | To‘g‘ridan-to‘g‘ri adminga xabar |
| 💬 Klub | Kitobxonlar klubi chatiga havola |

Barcha amallar **bir xil `books.db`** bazasini ishlatadi — ya'ni Mini App’da qilingan har
qanday amal (sevimliga qo‘shish, XP olish va h.k.) botning o‘zida ham, admin web panelida
ham darhol ko‘rinadi.

---

## 5. Xavfsizlik — qanday himoyalangan

Mini App’ga kirgan har bir so‘rov Telegramning rasmiy **`initData`** imzosi orqali
tekshiriladi (HMAC-SHA256, bot tokeningiz asosida). Bu degani:

- Hech kim o‘zini boshqa foydalanuvchi qilib ko‘rsata olmaydi (soxta `user_id` yuborib bo‘lmaydi)
- Faqat **haqiqiy Telegram ilovasi ichidan** ochilgan so‘rovlar qabul qilinadi
- Brauzerda to‘g‘ridan-to‘g‘ri `/app` manzilini ochsangiz — "Bu ilova faqat Telegram ichida
  ishlaydi" degan xabar chiqadi (bu — kutilgan, to‘g‘ri xatti-harakat)

Kitob fayllari va muqova rasmlari ham **hech qachon** brauzerga to‘g‘ridan-to‘g‘ri Telegram
manzili orqali berilmaydi — server (`/api/books/{id}/cover`, `/api/books/{id}/download`)
ularni o‘zi Telegramdan yuklab olib, foydalanuvchiga "proksi" qiladi, shu orqali bot
tokeningiz hech qachon brauzer tarmoq so‘rovlarida ko‘rinmaydi.

---

## 6. Muqova rasm qo‘yish (admin uchun)

Endi kitobga muqova rasm qo‘shish 2 joydan mumkin:

**Bot orqali:**
- `/admin` → 🖼 Muqova rasm qo‘yish → kitobni tanlang → rasm yuboring
- Yoki yangi kitob qo‘shishda: tavsifdan keyin bot avtomatik muqova so‘raydi

**Web panel orqali:**
- `/books/new` yoki kitobni tahrirlashda — "Kitob muqovasi (rasm)" maydoniga rasm yuklang

---

## 7. Nosozliklarni tuzatish (Troubleshooting)

| Muammo | Yechim |
|---|---|
| Mini App tugmasi ko‘rinmayapti | `.env`da `MINIAPP_URL` `https://` bilan boshlanganini tekshiring, botni qayta ishga tushiring |
| "Bu ilova faqat Telegram ichida ishlaydi" xabari botda ham chiqyapti | Sizda HTTPS to‘g‘ri sozlanmagan yoki `MINIAPP_URL` noto‘g‘ri — brauzerda to‘g‘ridan-to‘g‘ri `https://domen/app` ni oching, xato chiqsa nginx/certbot loglarini tekshiring |
| Rasmlar (muqova) yuklanmayapti | Admin bot bilan `/start` bosganini tekshiring — muqova rasm ham file_id orqali admin chatiga yuborilib olinadi |
| "401 Unauthorized" xatosi | Bu — xavfsizlik ishlayotganini bildiradi; Mini App’ni faqat Telegram ichida oching, brauzerda emas |

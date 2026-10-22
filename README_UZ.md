# Dava Insta Bot

## Tezkor yuklash va raqamlash

Har bir yuborilgan media fayl ro‘yxat ichida alohida `#1`, `#2`, `#3` tarzida raqamlanadi. Karuselning har bir fayli ham o‘z raqamiga ega. Fayl nomlari `001_…`, `002_…` ko‘rinishida boshlanadi. Raqamlar navbat bazasida saqlanadi; dastur qayta yoqilsa davom etadi. Yangi TXT ro‘yxat yoki `/retry` yangi ro‘yxat hisoblanadi va uning raqamlari 1 dan boshlanadi.

Telegramga bir post yuborilayotgan paytda keyingi post oldindan yuklanadi. Shu tariqa Instagramdan yuklash va Telegramga yuborish ustma-ust bajariladi, yetkazish tartibi esa saqlanadi. Har postdan keyingi 3 soniyalik sun’iy tanaffus olib tashlangan. Telegram yuborishlari orasidagi cheklov va RetryAfter kutishi saqlangan; haqiqiy tezlik internet, fayl hajmi va Instagram/Telegram javoblariga bog‘liq.

### Oldingi versiyani yangilash

Ishlayotgan botni `Ctrl+C` bilan to‘xtating. `Dava_Insta_Bot_Tezkor.zip` faylini Downloads papkasiga yuklab, terminalda bajaring:

```bash
python3 -m zipfile -e "$HOME/Downloads/Dava_Insta_Bot_Tezkor.zip" "$HOME"
cd "$HOME/Dava_Insta_Bot"
bash start.sh
```

Paket `data/` va `.venv/` papkalarini almashtirmaydi. Oldingi token, ulanish va navbat saqlanadi. Avval bot umuman o‘rnatilmagan bo‘lsa, `bash install.sh` ni bajaring.


Linux uchun shaxsiy Telegram bot. Instagram post/Reels linklari yoki ularning TXT ro‘yxatini qabul qiladi, navbat bilan yuklab, rasm va videolarni Telegramga fayl sifatida yuboradi. Bir postdagi karusel rasmlari ham yuboriladi. Profil, kolleksiya va Stories linklarini qabul qilmaydi.

## Tez ishga tushirish

1. ZIP faylni Downloads papkasiga yuklang.
2. Terminalda:

```bash
python3 -m zipfile -e "$HOME/Downloads/Dava_Insta_Bot.zip" "$HOME"
cd "$HOME/Dava_Insta_Bot"
bash install.sh
```

Agar venv xatosi chiqsa:

```bash
sudo apt install python3-venv
bash install.sh
```

3. Telegramda [@BotFather](https://t.me/BotFather) ni oching. `/newbot` yuboring. Nom uchun `Dava Insta`, username uchun bo‘sh bo‘lgan, oxiri `bot` bilan tugaydigan nom tanlang.
4. BotFather bergan tokenni Linux terminalidagi `BOT TOKEN:` so‘roviga kiriting. Kiritilgan belgilar ekranda ko‘rinmaydi. Tokenni ChatGPT yoki boshqa odamlarga yuborish shart emas.
5. Firefox’da Instagramga kirgan bo‘lsangiz, shu hisobdan foydalanish savoliga `ha` yozing. Bu faqat mahalliy Firefox’dagi Instagram cookies’ini ishlatadi; cookies Telegramga yuborilmaydi. Firefox oddiy Linux paketi sifatida o‘rnatilgan bo‘lishi kerak; Flatpak/Snap profilini avtomatik topish kafolatlanmaydi. `yo‘q` tanlansa, bot ommaviy postlarni hisobga kirmasdan sinaydi; Instagram kirishni talab qilishi mumkin.
6. Terminalda chiqqan bot havolasini oching va undagi `/start KOD` buyrug‘ini Telegramda botingizga yuboring. KOD o‘rniga terminaldagi haqiqiy kod kerak. Bot faqat shu Telegram hisobiga ulanadi.
7. `instagram_links.txt` faylini botingizga oddiy hujjat sifatida yuboring. Yoki bitta/bir nechta post linkini matn ko‘rinishida yuboring.

Kompyuter, internet va bot ishlayotgan terminal ochiq turishi kerak. `Ctrl+C` botni to‘xtatadi. Qayta ishga tushirish:

```bash
cd "$HOME/Dava_Insta_Bot"
bash start.sh
```

Bu paket botning dasturidir. BotFather’da ro‘yxatdan o‘tkazish va token kiritishdan oldin Telegramda faol bot yaratilgan hisoblanmaydi.

## Buyruqlar

- `/start KOD` — birinchi marta o‘z hisobingizga ulash.
- `/help` — foydalanish tartibi.
- `/status` — kutayotgan, ishlanayotgan, tayyor, qisman, xato va to‘xtatilgan postlar soni; sonlar umumiy tarixni ko‘rsatadi.
- `/cancel` — joriy yuklash va barcha kutilayotgan postlarni to‘xtatish. Telegramga boshlangan fayl yuborishi tugashi mumkin.
- `/retry` — har bir URL’ning eng so‘nggi urinishi xato yoki qisman bo‘lsa, yangi navbat yaratish. Qisman yuborilgan postning ba’zi fayllari yangi urinishda qayta yuborilishi mumkin. To‘xtatilgan postlar uchun TXT faylni qayta yuboring.

Yakunida postlar soni va xatolar hisoboti keladi. Xato bo‘lsa keyingi postga o‘tadi.

## Clipboard tarixidan TXT chiqarish

Sizdagi Clipboard History manzili uchun qo‘shimcha fayl qo‘shilgan:

```bash
cd "$HOME/Dava_Insta_Bot"
python3 export_history.py
```

Natija: `~/instagram_links.txt`. Faqat post/Reels/TV linklari olinadi. Takrorlar olib tashlanadi, birinchi uchragan tartib saqlanadi. Ushbu eksport diskda hali qolgan yozuvlarni o‘qiydi; clipboard logidagi eski o‘chirish belgilarini qayta tiklab hisoblamaydi, shuning uchun logda qolgan oldingi nusxalar ham chiqishi mumkin. Clipboard tarixingiz yoki cookies faylingizni botga yubormang; botga faqat ajratilgan linklar TXT fayli kerak.

## Limitlar va amaliy holatlar

- Har TXT fayl: 1 MB gacha, 1 000 ta takrorlanmagan post. Umumiy joriy navbat: 2 000 ta post.
- Har media fayli: 49 MB gacha. Telegramning odatiy Bot API yuborish chegarasi 50 MB; bot biroz kichikroq chegara ishlatadi. Katta fayllar hisobotga tushadi; avtomatik siqish qo‘shilmagan.
- Bir postni yuklash: 5 daqiqagacha; vaqtinchalik fayllar: taxminan 600 MB gacha. Yuklash boshida 1 GB bo‘sh disk talab qilinadi.
- Postlar TXT ichidagi tartibda yetkaziladi; keyingi post oldindan yuklanadi. Takrorlar bitta yuborilgan ro‘yxat doirasida olib tashlanadi.
- Media original fayl ko‘rinishida yuboriladi. Barcha postlar bitta ZIP qilib qaytarilmaydi.
- Internet uzilsa yoki dastur yopilsa, navbat `data/queue.sqlite` ichida qoladi. Keyingi ishga tushishda tugamagan post qayta ishlanadi. Muvaffaqiyatli yuborilgani bazaga yozilgan fayllar o‘sha ish doirasida qayta yuborilmaydi. Telegram qabul qilishi va bazaga yozish orasida uzilish bo‘lsa, fayl takror kelishi mumkin.
- Yopiq, o‘chirilgan yoki sizning hisobingiz ko‘ra olmaydigan postlar yuklanmaydi. Instagram cheklovlari sabab hamma linkning yuklanishini kafolatlab bo‘lmaydi.
- Faqat o‘zingiz ko‘rishga va saqlashga ruxsatli kontentdan foydalaning.

## Instagram kirishni talab qilsa

Firefox’da Instagram hisobingizga kiring. Botni `Ctrl+C` bilan to‘xtating, keyin:

```bash
cd "$HOME/Dava_Insta_Bot"
.venv/bin/python setup_bot.py --cookies
bash start.sh
```

Savolga `ha` yozing. Boshqa Firefox profili yoki Flatpak/Snap ishlatilsa, profil tanlashni alohida moslash kerak bo‘lishi mumkin.

## Yangilash

Instagram yuklash tartibini o‘zgartirsa, botni to‘xtating:

```bash
bash update.sh
bash start.sh
```

## Texnik ma’lumot

Python 3.10+, python-telegram-bot 22.6 va gallery-dl ishlatiladi. O‘rnatish foydalanuvchi papkasidagi alohida `.venv` muhitida bajariladi. Sozlamalar va token `data/config.json` da saqlanadi (0600 huquqlar); bu faylni ulashmang. Ro‘yxatdagi matn shell buyruqlari sifatida bajarilmaydi. Bir vaqtning o‘zida faqat bitta bot nusxasi ishlaydi.

Avtomatik tekshiruv:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Avtomatik sinovlar linklarni ajratish, navbat, restart, ruxsat va simulyatsiyalangan Telegram yuborish oqimini qamrab oladi. Haqiqiy BotFather tokeni bilan jonli Telegram/Instagram sinovi bu paket tayyorlanayotganda bajarilmagan.

Rasmiy manbalar:
- https://core.telegram.org/bots/tutorial
- https://core.telegram.org/bots/faq
- https://docs.python-telegram-bot.org/en/v22.6/
- https://github.com/mikf/gallery-dl
- https://github.com/mikf/gallery-dl/blob/master/docs/options.md

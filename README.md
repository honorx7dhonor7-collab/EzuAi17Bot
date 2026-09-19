# EzuAi17Bot

O'zbek tilida suhbatlashadigan va rasmlarni jonlantiradigan Telegram bot.

## Replit Secrets

Quyidagi qiymatlarni kodga yozmang; Replit Secrets orqali qo'shing:

- `BOT_TOKEN` — @BotFather bergan Telegram bot tokeni.
- `GEMINI_API_KEY` — Google AI Studio Gemini API kaliti.

Ixtiyoriy sozlamalar:

- `GEMINI_MODEL` — odatda `gemini-2.5-flash`.
- `GEMINI_TTS_MODEL` — odatda `gemini-3.1-flash-tts-preview`.
- `GEMINI_TTS_VOICE` — TTS ovozi, standart qiymat `Kore`.

## Funksiyalar

- Matnli xabarlarga Gemini orqali o'zbekcha javob.
- JPG, PNG va WEBP rasmlarni qabul qilish.
- **Jonlantirish** tugmasi: xavfsiz Ken Burns video effekti.
- **Gapirtirish** tugmasi: matnni so'raydi, Gemini TTS orqali o'zbekcha ovoz yaratadi va gapirayotgan video effektini yuboradi.
- API kaliti, token va foydalanuvchi fayllari kodga yoki repoga yozilmaydi.
- Noto'g'ri fayl, katta rasm, API xatosi, limit tugashi va konfiguratsiya muammolari o'zbekcha ko'rsatiladi.

## Ishga tushirish

1. Replit Secrets ichiga `BOT_TOKEN` va `GEMINI_API_KEY` ni qo'shing.
2. Dependencies o'rnatilgach, `python bot.py` ni ishga tushiring.
3. Telegramda `/start` yuboring.
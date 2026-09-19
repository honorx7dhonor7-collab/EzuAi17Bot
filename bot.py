import os
import requests
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

BOT_TOKEN = os.environ.get("BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
D_ID_API_KEY = os.environ.get("D_ID_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom O'g'iloy! 😊 Men EzuAi17Bot man! Oddiy yozing - javob beraman, yoki rasm + matn yuboring - gapiradigan video qilaman! 🎬")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        prompt = update.message.text
        response = model.generate_content(prompt)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def talking_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        caption = update.message.caption
        if not caption:
            await update.message.reply_text("O'g'iloy, iltimos rasmni tanlab, pastidagi caption joyiga matn yozing! Masalan: 'Salom men O'g'iloy man' deb yozib yuboring.")
            return

        await update.message.reply_text("⏳ Jonlantiryapman O'g'iloy... 30 soniya kuting!")

        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_url = file.file_path

        url = "https://api.d-id.com/talks"
        headers = {
            "Authorization": f"Basic {D_ID_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "source_url": file_url,
            "script": {"type": "text", "input": caption, "provider": {"type": "microsoft", "voice_id": "en-US-JennyNeural"}},
            "config": {"fluent": True, "pad_audio": 0.5}
        }
        
        res = requests.post(url, headers=headers, json=data).json()
        talk_id = res.get("id")
        
        if not talk_id:
            await update.message.reply_text(f"D-ID xatolik: {res}")
            return

        for _ in range(20):
            time.sleep(3)
            get_url = f"https://api.d-id.com/talks/{talk_id}"
            result = requests.get(get_url, headers=headers).json()
            if result.get("status") == "done":
                video_url = result.get("result_url")
                await update.message.reply_video(video_url, caption=f"Siz yozdingiz: {caption} 🎬")
                return
            if result.get("status") == "error":
                await update.message.reply_text(f"Video yasashda xato: {result}")
                return
        
        await update.message.reply_text("Video uzoq tayyor bo'lyapti, keyinroq urinib ko'ring.")
    except Exception as e:
        await update.message.reply_text(f"Video xatolik: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    app.add_handler(MessageHandler(filters.PHOTO, talking_photo))
    app.run_polling()

if __name__ == "__main__":
    main()

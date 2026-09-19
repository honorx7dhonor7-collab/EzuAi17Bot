import os
import logging
import requests
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DID_KEY = os.getenv("D_ID_API_KEY")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Salom O'g'iloy! 💖 Men Ezuman!\n\nMenga oddiy yozing - suhbatlashaman!\nRasm + matn yuboring - gapiradigan video qilaman! 🎬")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_text = update.message.text
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Xato: {e}")

async def talk_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not update.message.caption:
            await update.message.reply_text("O'g'iloy, rasm bilan birga nima deyishi kerakligini ham yozing! Masalan rasm tagiga: Salom men Ezu man!")
            return

        await update.message.reply_text("Qadrdonim, video tayyorlayapman... 30 soniya... 🎬✨")
        
        photo_file = await update.message.photo[-1].get_file()
        photo_url = photo_file.file_path

        # D-ID API
        url = "https://api.d-id.com/talks"
        headers = {
            "Authorization": f"Basic {DID_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "source_url": photo_url,
            "script": {
                "type": "text",
                "input": update.message.caption,
                "provider": {"type": "microsoft", "voice_id": "uz-UZ-MadinaNeural"}
            }
        }
        
        r = requests.post(url, json=data, headers=headers)
        if r.status_code != 201:
            await update.message.reply_text(f"D-ID xato: {r.text}")
            return

        talk_id = r.json()["id"]

        # Kutilmoqda
        import time
        for _ in range(20):
            time.sleep(3)
            get_r = requests.get(f"{url}/{talk_id}", headers=headers)
            result_url = get_r.json().get("result_url")
            if result_url:
                await update.message.reply_video(result_url, caption="Mana O'g'iloy! Sizning gapiradigan videongiz! 💖")
                return
        
        await update.message.reply_text("Video biroz kechikyapti, qayta urinib ko'ring!")

    except Exception as e:
        await update.message.reply_text(f"Xato: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, talk_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()

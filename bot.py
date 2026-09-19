import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from PIL import Image
import io

# Loglar
logging.basicConfig(level=logging.INFO)

# Tokenlar
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini sozlash
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
else:
    model = None

# /start komanda
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋 Men EzuAi17Bot man!\n\n"
        "🎨 Rasm yuboring - uni tahlil qilaman\n"
        "💬 Savol yozing - javob beraman\n\n"
        "/start - Boshlash"
    )

# Rasm kelganda
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Rasmni ko'rib chiqyapman... ⏳")
    
    try:
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(photo_bytes))
        
        if model:
            response = model.generate_content(["Bu rasmni chiroyli tasvirlab ber, o'zbek tilida", image])
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("Rasm qabul qilindi! ✅ (Gemini key qo'shilsa tahlil qilaman)")
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

# Matnli xabar kelganda
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    if not model:
        await update.message.reply_text("Savolingiz qabul qilindi! Gemini key qo'shilsa javob beraman 🤖")
        return
    
    try:
        await update.message.reply_chat_action("typing")
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Xatolik yuz berdi: {e}")

# Botni ishga tushirish
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("EzuAi17Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()

import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai

# Tokenlar Render Environment dan olinadi
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini sozlash
genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(
    'gemini-2.0-flash',
    system_instruction="Sening isming EzuAi17Bot. Seni O'g'iloy yaratgan. Sen O'g'iloy tomonidan yaratilgan yordamchi botsan. Har doim o'zingni O'g'iloy yaratganini ayt. Seni kim yaratgan deb so'rashsa 'Meni O'g'iloy yaratgan!' deb javob ber. Juda do'stona, samimiy va chiroyli qizlardek javob ber. O'zbek tilida javob ber."
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋 Men EzuAi17Bot man!\n\n"
        "Meni O'g'iloy yaratgan! 😊💖\n\n"
        "🎨 Rasm yuboring - uni tahlil qilaman\n"
        "💬 Savol yozing - javob beraman\n\n"
        "/start - Boshlash"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Kim yaratganini tekshirish
    if "kim yarat" in user_text.lower() or "kim yasadi" in user_text.lower() or "muallif" in user_text.lower():
        await update.message.reply_text("Meni O'g'iloy yaratgan! 💖 U juda aqlli va chiroyli! 😊")
        return
    
    try:
        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive("temp.jpg")
        
        # Rasmni yuklash
        import PIL.Image
        img = PIL.Image.open("temp.jpg")
        
        caption = update.message.caption if update.message.caption else "Bu rasmni tahlil qilib ber"
        
        response = model.generate_content([caption, img])
        await update.message.reply_text

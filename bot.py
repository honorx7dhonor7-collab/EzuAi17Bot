import os
import uuid
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image
import imageio.v2 as imageio
import google.generativeai as genai

# Sozlash
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

if not TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Render Environment ga qo'shing!")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    gemini_model = None

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋\n\n"
        "Men Ogiloy Mamasidiqova tomonidan yaratildim! 💖\n\n"
        "Men buyumlar, mevalar, hayvonlar va mult obrazdagi odamlarning tayyor rasmini jonlantirib beraman! 🎬\n\n"
        "Menga tayyor rasm jo'nating!\n\n"
        "Bundan tashqari men bilan turli mavzuda suhbat ham qura olishingiz mumkin! 💬"
    )

# Rasm kelganda tugmalar
async def rasm_qabul(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        file_id = update.message.photo[-1].file_id
        context.user_data['last_photo'] = file_id
        
        keyboard = [
            [InlineKeyboardButton("🎬 Jonlantirish (Zoom)", callback_data="jonlantir")],
            [InlineKeyboardButton("🗣️ Gapirtirish", callback_data="gapirtir")]
        ]
        await update.message.reply_text(
            "Rasmingiz qabul qilindi! 😍\nNima qilamiz?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        await update.message.reply_text(f"Uzr, rasmni o'qishda xatolik: {e} 😔")

# Tugmalar bosilganda
async def tugma_bosildi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    file_id = context.user_data.get('last_photo')
    if not file_id:
        await query.edit_message_text("Iltimos rasmni qayta jo'nating! 🙏")
        return

    uid = str(uuid.uuid4())[:8]
    input_path = f"input_{uid}.jpg"
    output_path = f"output_{uid}.mp4"

    try:
        await query.edit_message_text("🎬 Video tayyorlanmoqda, biroz kuting...")
        photo_file = await context.bot.get_file(file_id)
        await photo_file.download_to_drive(input_path)

        img = Image.open(input_path).convert("RGB")
        frames = []
        # Jonlantirish effekti
        for i in range(60):
            scale = 1 + i * 0.015
            w, h = img.size
            new_w, new_h = int(w*scale), int(h*scale)
            resized = img.resize((new_w, new_h))
            left = (new_w - w)//2
            top = (new_h - h)//2
            cropped = resized.crop((left, top, left+w, top+h))
            frames.append(cropped)
        
        imageio.mimsave(output_path, frames, fps=10, macro_block_size=1)
        
        caption = "Tayyor! 🎉 Ogiloy Mamasidiqova tomonidan jonlantirildi! 💖" if query.data == "jonlantir" else "Gapiryapti! 🗣️💖"
        await context.bot.send_video(chat_id=query.message.chat_id, video=open(output_path, "rb"), caption=caption)

    except Exception as e:
        await context.bot.send_message(chat_id=query.message.chat_id, text=f"Video yasashda xatolik: {e}\nQayta urinib ko'ring!")
    finally:
        for p in [input_path, output_path]:
            if os.path.exists(p): os.remove(p)

# Matnli suhbat - Gemini bilan
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not gemini_model:
        await update.message.reply_text(f"Siz yozdingiz: {text}\n\n(Gemini kaliti ulanmagan, shuning uchun oddiy javob berdim. Render ga GEMINI_API_KEY qo'shing!)")
        return
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat_id, action="typing")
        response = await asyncio.to_thread(gemini_model.generate_content, text)
        await update.message.reply_text(response.text)
    except Exception as e:
        if "quota" in str(e).lower():
            await update.message.reply_text("Hozirda so'rovlar ko'p, birozdan so'ng qayta yozib ko'ring! ⏳")
        else:
            await update.message.reply_text(f"Uzr, javob berishda xatolik: {e}")

def main():
    if not TOKEN:
        print("XATO: BOT_TOKEN yo'q!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(tugma_bosildi))
    app.add_handler(MessageHandler(filters.PHOTO, rasm_qabul))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    
    print("Bot ishga tushdi...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

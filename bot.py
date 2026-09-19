import os, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
import imageio.v2 as imageio

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋\n\n"
        "Men Ogiloy Mamasidiqova tomonidan yaratildim! 💖\n\n"
        "Men buyumlar, mevalar, hayvonlar va mult obrazdagi odamlarning tayyor rasmini jonlantirib beraman! 🎬\n\n"
        "Menga tayyor rasm jo'nating!\n\n"
        "Bundan tashqari men bilan turli mavzuda suhbat ham qura olishingiz mumkin! 💬 Siz yozgan so'zlaringizga qarab video davomiyligi o'zgaradi!"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    words = len(text.split())
    duration = max(3, words * 0.5) # har bir so'z uchun 0.5 sek, so'z tugaguncha
    fps = 10
    frames_count = int(duration * fps)
    
    await update.message.reply_text(f"Qabul qildim! '{text}'\nSiz uchun {duration:.1f} sekundlik jonli video tayyorlayapman... 🎬")

    try:
        img = Image.new('RGB', (720, 720), color=(255, 182, 193))
        frames = []
        for i in range(frames_count):
            scale = 1 + i * 0.01
            w, h = img.size
            new_w, new_h = int(w*scale), int(h*scale)
            resized = img.resize((new_w, new_h))
            left = (new_w - w)//2
            top = (new_h - h)//2
            cropped = resized.crop((left, top, left+w, top+h))
            frames.append(cropped)
        
        imageio.mimsave("chat.mp4", frames, fps=fps, macro_block_size=1)
        await update.message.reply_video(video=open("chat.mp4", "rb"), caption=f"Marhamat! {duration:.1f} sek video - so'zlaringiz tugaguncha! 💖")
    except Exception as e:
        await update.message.reply_text(f"Chat javobi: {text} 😊 (video xato: {e})")

async def rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Rasmingizni oldim! 🎬 Jonlantiryapman...")
    try:
        photo = await update.message.photo[-1].get_file()
        await photo.download_to_drive("input.jpg")
        img = Image.open("input.jpg")
        frames = []
        for i in range(60): # 6 sekund
            scale = 1 + i * 0.02
            w, h = img.size
            new_w, new_h = int(w*scale), int(h*scale)
            resized = img.resize((new_w, new_h))
            left = (new_w - w)//2
            top = (new_h - h)//2
            cropped = resized.crop((left, top, left+w, top+h))
            frames.append(cropped)
        imageio.mimsave("output.mp4", frames, fps=10, macro_block_size=1)
        await update.message.reply_video(video=open("output.mp4", "rb"), caption="Tayyor! 🎉 Ogiloy Mamasidiqova tomonidan jonlantirildi! 💖")
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, rasm))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

import os, asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from PIL import Image
from gtts import gTTS
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips

TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋\n\n"
        "Men Ogiloy Mamasidiqova tomonidan yaratildim! 💖\n\n"
        "Men buyumlar, mevalar, hayvonlar va mult obrazdagi odamlarning tayyor rasmini jonlantirib beraman! 🎬\n\n"
        "Menga tayyor rasm jo'nating!\n\n"
        "Bundan tashqari men bilan turli mavzuda suhbat ham qura olishingiz mumkin! 💬"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    javob = f"Qiziqarli! {user_text} haqida gaplashamiz. Bu mavzu juda yoqimli!"
    
    await update.message.reply_text(f"{javob}\n\n🎬 Siz uchun jonli video tayyorlayapman...")
    try:
        # Ovoz yaratish
        tts = gTTS(text=javob, lang='uz')
        tts.save("ovoz.mp3")
        
        audio = AudioFileClip("ovoz.mp3")
        duration = audio.duration # so'z tugaguncha davomiylik

        # Rasm - jonli video
        # Standart rasm yaratamiz
        img = Image.new('RGB', (720, 720), color=(255, 182, 193))
        img.save("chat.jpg")

        clip = ImageClip("chat.jpg").set_duration(duration).set_audio(audio)
        # zoom effekti
        clip = clip.resize(lambda t: 1 + 0.05*t)
        
        clip.write_videofile("chat_video.mp4", fps=24, codec='libx264', audio_codec='aac')
        
        await update.message.reply_video(video=open("chat_video.mp4", "rb"), caption=f"🎤 {javob}")
    except Exception as e:
        await update.message.reply_text(javob + f"\n\nVideo xato: {e}")

async def rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Rasmingizni oldim! 🎬 Jonlantiryapman...")
    try:
        photo = await update.message.photo[-1].get_file()
        await photo.download_to_drive("input.jpg")
        
        # 5 sekundlik jonli video
        clip = ImageClip("input.jpg").set_duration(5)
        clip = clip.resize(lambda t: 1 + 0.1*t) # zoom
        clip.write_videofile("output.mp4", fps=24)
        
        await update.message.reply_video(video=open("output.mp4", "rb"), caption="Tayyor! 🎉 Ogiloy Mamasidiqova tomonidan jonlantirildi! 💖")
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, rasm))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("Bot ishga tushdi!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

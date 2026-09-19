import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# 1. /start bosganda
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋\n\n"
        "Men Ogiloy Mamasidiqova tomonidan yaratildim! 💖\n\n"
        "Men buyumlar, mevalar, hayvonlar va mult obrazdagi odamlarning tayyor rasmini jonlantirib beraman! 🎬\n\n"
        "Menga tayyor rasm jo'nating!\n\n"
        "Bundan tashqari siz bilan turli mavzuda suhbatlasha olaman! 💬"
    )

# 2. Oddiy yozishsa - gaplashadi
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    
    if "kutubxonachi" in text or "kutubxona" in text:
        javob = "Kutubxonachi - kitoblar olamining qo'riqchisi! 📚 U har bir kitobni asraydi va o'quvchiga to'g'ri kitobni tavsiya qiladi. Sizga qanday kitob kerak?"
    elif "salom" in text:
        javob = "Salom O'g'iloy! 😊 Qalaysiz? Menga rasm jo'nating yoki xohlagan mavzuda savol bering!"
    elif "isming" in text:
        javob = "Mening ismim yo'q, meni Ogiloy Mamasidiqova yaratgan! 💖"
    else:
        javob = f"Siz: {update.message.text}\n\nQiziqarli fikr! Bu haqda yana gaplashamizmi? Menga rasm ham jo'natishingiz mumkin! 🎬"
    
    await update.message.reply_text(javob)

# 3. Rasm jo'natsa
async def rasm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Rasmingizni oldim! 🎬 Tez orada jonlantirib beraman... (Bu qismi keyin qo'shamiz)")

# Botni ishga tushirish
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.PHOTO, rasm))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

app.run_polling()

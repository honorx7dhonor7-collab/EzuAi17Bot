import os, logging, requests, time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
DID_KEY = os.getenv("D_ID_API_KEY")

GEMINI_OK = False
try:
    import google.generativeai as genai
    if GEMINI_KEY:
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        GEMINI_OK = True
except Exception as e:
    print(f"GEMINI XATO: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Salom! 👋\n\n"
        "Men Ogiloy Mamasidiqova tomonidan yaratildim! 💖\n\n"
        "Men buyumlar, mevalar, hayvonlar va mult obrazdagi odamlarning tayyor rasmini jonlantirib beraman! 🎬\n\n"
        "Menga tayyor rasm jo'nating!\n\n"
        "Bundan tashqari, siz bilan turli mavzuda suhbatlasha olaman! 💬\n"
        "Xohlagan savolingizni bering!"
    )

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    print(f"XABAR: {txt}")
    try:
        if GEMINI_OK:
            await context.bot.send_chat_action(update.effective_chat.id, "typing")
            res = model.generate_content(f"Sen Ogiloy Mamasidiqova yaratgan mehribon yordamchisan. Foydalanuvchi bilan turli mavzuda suhbatlasha olasan, samimiy javob ber. Savol: {txt}")
            await update.message.reply_text(res.text)
        else:
            await update.message.reply_text(f"Ha, men siz bilan turli mavzuda suhbatlasha olaman! 💬\nSiz: {txt}\n\n(Gemini key yangilanishi kerak)")
    except Exception as e:
        print(f"CHAT XATO: {e}")
        await update.message.reply_text(f"Men siz bilan turli mavzuda suhbatlasha olaman qadrdonim! 💖\nSiz yozdingiz: {txt}\nMen eshitdim!")

async def talk_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    caption = update.message.caption
    if not caption:
        await update.message.reply_text("Rasm tagiga nima deyishini yozing O'g'iloy! 🎬")
        return
    await update.message.reply_text(f"Qabul qildim! '{caption}' - jonlantiryapman... 40 soniya! ⏳")
    try:
        photo = await update.message.photo[-1].get_file()
        clean_key = DID_KEY.replace("Basic ", "") if DID_KEY else ""
        headers = {"Authorization": f"Basic {clean_key}", "Content-Type": "application/json"}
        data = {
            "source_url": photo.file_path,
            "script": {"type": "text", "input": caption, "provider": {"type": "microsoft", "voice_id": "uz-UZ-MadinaNeural"}},
            "config": {"fluent": True, "pad_audio": 1.0, "result_format": "mp4", "stitch": True}
        }
        r = requests.post("https://api.d-id.com/talks", json=data, headers=headers)
        if r.status_code not in [200, 201]:
            await update.message.reply_text(f"Video xato: {r.text[:400]}")
            return
        tid = r.json()["id"]
        for _ in range(40):
            time.sleep(3)
            g = requests.get(f"https://api.d-id.com/talks/{tid}", headers=headers).json()
            if g.get("result_url"):
                await update.message.reply_video(g["result_url"], caption="Tayyor! Ogiloy Mamasidiqova nomidan! 💖")
                return
        await update.message.reply_text("Biroz kechikdi, qayta yuboring!")
    except Exception as e:
        await update.message.reply_text(f"Video xato: {e}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, talk_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("BOT START!")
    app.run_polling()

if __name__ == "__main__":
    main()

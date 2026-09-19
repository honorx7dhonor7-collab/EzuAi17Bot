import asyncio
import base64
import logging
import os
import tempfile
import uuid
import wave
from pathlib import Path
from typing import Optional

import httpx
import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
)
logger = logging.getLogger("ezuai17bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
GEMINI_TTS_MODEL = os.getenv(
    "GEMINI_TTS_MODEL", "gemini-3.1-flash-tts-preview"
).strip()
GEMINI_TTS_VOICE = os.getenv("GEMINI_TTS_VOICE", "Kore").strip()
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_IMAGE_SIDE = 1600
MAX_CHAT_CHARS = 4000
MAX_SPEECH_CHARS = 1200
VIDEO_SIZE = (720, 720)
VIDEO_FPS = 12
VIDEO_SECONDS = 5
WORK_DIR = Path(tempfile.gettempdir()) / "ezuai17bot"
WORK_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = (
    "Siz EzuAi17Bot nomli Telegram botning mehribon va foydali yordamchisiz. "
    "Foydalanuvchi bilan asosan o'zbek tilida, sodda va tabiiy tarzda suhbatlashing. "
    "Savol boshqa tilda bo'lsa, shu tilni tushunib, imkon qadar o'zbek tilida javob bering. "
    "Javoblarni aniq, xavfsiz va mavzuga mos yozing. Bilmagan narsangizni to'qib chiqarmang."
)


def user_dir(user_id: int) -> Path:
    directory = WORK_DIR / str(user_id)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def cleanup_file(path: Optional[Path]) -> None:
    if not path:
        return
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Faylni o'chirib bo'lmadi: %s", path)


def error_text(status_code: int, detail: str = "") -> str:
    if status_code in (401, 403):
        return (
            "Gemini API kaliti noto'g'ri yoki ruxsati yetarli emas. "
            "Replit Secrets ichidagi GEMINI_API_KEY ni tekshiring."
        )
    if status_code == 429:
        return (
            "Gemini API limiti tugagan yoki vaqtincha juda ko'p so'rov yuborildi. "
            "Birozdan keyin qayta urinib ko'ring."
        )
    if status_code == 400:
        return (
            "Gemini so'rovni qabul qilmadi. Matnni qisqartirib yoki boshqacha yozib ko'ring."
        )
    if status_code >= 500:
        return (
            "Gemini serverida vaqtinchalik muammo bor. "
            "Bir necha soniyadan keyin qayta urinib ko'ring."
        )
    safe_detail = detail.replace("\n", " ").strip()[:160]
    return f"Gemini API xatosi ({status_code}). {safe_detail}".strip()


async def gemini_request(payload: dict, model: str) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY sozlanmagan")

    url = f"{GEMINI_API_BASE}/{model}:generateContent"
    headers = {
        "x-goog-api-key": GEMINI_API_KEY,
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(60.0, connect=15.0)
        ) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.TimeoutException as exc:
        raise RuntimeError("Gemini API javob berishiga vaqt yetmadi") from exc
    except httpx.HTTPError as exc:
        raise RuntimeError("Gemini API bilan ulanishda muammo bo'ldi") from exc

    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message", "")
        except ValueError:
            detail = response.text
        raise RuntimeError(error_text(response.status_code, detail))

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Gemini API noto'g'ri javob qaytardi") from exc


def extract_text(data: dict) -> str:
    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise RuntimeError("Gemini javobida matn topilmadi")
    return text


async def gemini_chat(text: str, history: list[dict]) -> str:
    history.append({"role": "user", "parts": [{"text": text}]})
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": history[-10:],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1200},
    }
    try:
        result = await gemini_request(payload, GEMINI_MODEL)
        answer = extract_text(result)
    except Exception:
        history.pop()
        raise
    history.append({"role": "model", "parts": [{"text": answer}]})
    del history[:-10]
    return answer


def make_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🎬 Jonlantirish", callback_data=f"animate:{token}"
                ),
                InlineKeyboardButton(
                    "🗣 Gapirtirish", callback_data=f"speak:{token}"
                ),
            ]
        ]
    )


def normalize_image(source: Path, destination: Path) -> None:
    try:
        with Image.open(source) as image:
            image.verify()
        with Image.open(source) as image:
            image = ImageOps.exif_transpose(image).convert("RGB")
            image.thumbnail(
                (MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS
            )
            image.save(destination, format="JPEG", quality=90, optimize=True)
    except (
        UnidentifiedImageError,
        OSError,
        Image.DecompressionBombError,
    ) as exc:
        raise ValueError(
            "Bu fayl haqiqiy yoki qo'llab-quvvatlanadigan rasm emas"
        ) from exc


async def save_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Path:
    message = update.effective_message
    if message is None:
        raise ValueError("Rasm xabari topilmadi")

    file_size = None
    if message.photo:
        telegram_file = await message.photo[-1].get_file()
        file_size = message.photo[-1].file_size
    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("image/")
    ):
        telegram_file = await message.document.get_file()
        file_size = message.document.file_size
    else:
        raise ValueError("Faqat JPG, PNG yoki WEBP rasm yuboring")

    if file_size and file_size > MAX_UPLOAD_BYTES:
        raise ValueError("Rasm hajmi 10 MB dan oshmasligi kerak")

    directory = user_dir(update.effective_user.id)
    raw_path = directory / f"raw_{uuid.uuid4().hex}"
    image_path = directory / f"image_{uuid.uuid4().hex}.jpg"
    await telegram_file.download_to_drive(custom_path=str(raw_path))
    try:
        normalize_image(raw_path, image_path)
    finally:
        cleanup_file(raw_path)

    old_path = context.user_data.get("image_path")
    if old_path and old_path != str(image_path):
        cleanup_file(Path(old_path))
    context.user_data["image_path"] = str(image_path)
    token = uuid.uuid4().hex[:16]
    context.user_data["image_token"] = token
    return image_path


def prepare_frame(image_path: Path, scale: float) -> Image.Image:
    with Image.open(image_path) as source:
        base = ImageOps.fit(
            source.convert("RGB"),
            VIDEO_SIZE,
            method=Image.Resampling.LANCZOS,
        )
    width, height = base.size
    scaled = base.resize(
        (int(width * scale), int(height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = max(0, (scaled.width - width) // 2)
    top = max(0, (scaled.height - height) // 2)
    return scaled.crop((left, top, left + width, top + height))


def write_video(
    image_path: Path, output_path: Path, talking_text: Optional[str] = None
) -> None:
    total_frames = VIDEO_FPS * VIDEO_SECONDS
    writer = imageio.get_writer(
        str(output_path),
        fps=VIDEO_FPS,
        codec="libx264",
        macro_block_size=1,
    )
    try:
        for index in range(total_frames):
            progress = index / max(1, total_frames - 1)
            scale = 1.0 + 0.12 * progress
            frame = prepare_frame(image_path, scale)
            if talking_text:
                overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay)
                bubble = (18, 18, 702, 94)
                draw.rounded_rectangle(
                    bubble, radius=18, fill=(0, 0, 0, 175)
                )
                short_text = talking_text.replace("\n", " ")[:105]
                draw.text(
                    (32, 44),
                    short_text,
                    fill="white",
                    anchor="lm",
                )
                mouth_open = index % 6 < 3
                cx, cy = 360, 590
                mouth_box = (
                    cx - 28,
                    cy - (15 if mouth_open else 8),
                    cx + 28,
                    cy + (15 if mouth_open else 8),
                )
                draw.ellipse(
                    mouth_box,
                    fill=(150, 35, 65, 220),
                    outline=(255, 220, 220, 230),
                    width=2,
                )
                frame = Image.alpha_composite(
                    frame.convert("RGBA"), overlay
                ).convert("RGB")
            writer.append_data(np.asarray(frame))
    finally:
        writer.close()


def write_wav(path: Path, pcm: bytes, rate: int = 24000) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(pcm)


async def gemini_tts(text: str, output_path: Path) -> None:
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"Speak naturally and warmly in Uzbek: {text}"}
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": GEMINI_TTS_VOICE
                    }
                }
            },
        },
    }
    result = await gemini_request(payload, GEMINI_TTS_MODEL)
    parts = result.get("candidates", [{}])[0].get("content", {}).get("parts", [])
    audio_data = None
    for part in parts:
        inline = part.get("inlineData") or part.get("inline_data")
        if inline and inline.get("data"):
            audio_data = inline["data"]
            break
    if not audio_data:
        raise RuntimeError("Gemini TTS audio qaytarmadi")
    try:
        write_wav(output_path, base64.b64decode(audio_data))
    except (ValueError, OSError) as exc:
        raise RuntimeError("Ovoz faylini tayyorlashda xatolik bo'ldi") from exc


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Salom! 👋\n\n"
        "Men o'zbek tilida turli mavzularda suhbatlashaman. Savolingizni yozing.\n\n"
        "Rasm yuborsangiz, uni tekshiraman va sizga "
        "«Jonlantirish» yoki «Gapirtirish» tugmalarini ko'rsataman. 🎬\n\n"
        "Rasm uchun JPG, PNG yoki WEBP formatidan foydalaning."
    )


async def help_command(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    await update.effective_message.reply_text(
        "Yordam:\n"
        "• Matn yuboring — Gemini o'zbek tilida javob beradi.\n"
        "• Rasm yuboring — keyin Jonlantirish yoki Gapirtirish tugmasini bosing.\n"
        "• Gapirtirishda bot so'zlatiladigan matnni so'raydi.\n\n"
        "Maxsus kalitlar faqat Replit Secrets orqali olinadi."
    )


async def handle_image(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        await update.effective_message.reply_chat_action(
            ChatAction.UPLOAD_PHOTO
        )
        await save_image(update, context)
        await update.effective_message.reply_text(
            "Rasm qabul qilindi ✅\nKerakli amalni tanlang:",
            reply_markup=make_keyboard(context.user_data["image_token"]),
        )
    except ValueError as exc:
        await update.effective_message.reply_text(
            f"Rasm qabul qilinmadi: {exc}"
        )
    except Exception:
        logger.exception("Rasmni qabul qilishda xatolik")
        await update.effective_message.reply_text(
            "Rasmni yuklashda texnik xatolik bo'ldi. Rasmni qayta yuborib ko'ring."
        )


async def animate_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    _, token = query.data.split(":", 1)
    if token != context.user_data.get("image_token"):
        await query.message.reply_text(
            "Bu tugma eski rasmga tegishli. Rasmni qayta yuboring."
        )
        return
    image_path = Path(context.user_data.get("image_path", ""))
    if not image_path.is_file():
        await query.message.reply_text(
            "Rasm topilmadi. Iltimos, rasmni qayta yuboring."
        )
        return

    output_path = user_dir(update.effective_user.id) / (
        f"animated_{uuid.uuid4().hex}.mp4"
    )
    await query.message.reply_text(
        "Rasm jonlantirilmoqda, biroz kuting... 🎬"
    )
    try:
        await context.bot.send_chat_action(
            update.effective_chat.id, ChatAction.UPLOAD_VIDEO
        )
        await asyncio.to_thread(write_video, image_path, output_path)
        with output_path.open("rb") as video:
            await query.message.reply_video(
                video=video, caption="Tayyor! Rasm jonlantirildi. 🎉"
            )
    except Exception:
        logger.exception("Rasmni jonlantirishda xatolik")
        await query.message.reply_text(
            "Rasmni jonlantirishda xatolik bo'ldi. "
            "Fayl formati yoki server imkoniyatini tekshiring."
        )
    finally:
        cleanup_file(output_path)


async def speak_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    _, token = query.data.split(":", 1)
    if token != context.user_data.get("image_token"):
        await query.message.reply_text(
            "Bu tugma eski rasmga tegishli. Rasmni qayta yuboring."
        )
        return
    if not Path(context.user_data.get("image_path", "")).is_file():
        await query.message.reply_text(
            "Rasm topilmadi. Iltimos, rasmni qayta yuboring."
        )
        return
    context.user_data["awaiting_speech"] = True
    await query.message.reply_text(
        "Rasm nima desin? Matnni yuboring (1200 belgigacha). "
        "Masalan: Salom, do'stlar! 👋"
    )


async def make_speaking_image(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    image_path = Path(context.user_data.get("image_path", ""))
    if not image_path.is_file():
        await update.effective_message.reply_text(
            "Rasm topilmadi. Avval rasm yuboring."
        )
        return

    user_path = user_dir(update.effective_user.id)
    video_path = user_path / f"speaking_{uuid.uuid4().hex}.mp4"
    audio_path = user_path / f"speech_{uuid.uuid4().hex}.wav"
    await update.effective_message.reply_text(
        "Rasm gapirtirilmoqda, biroz kuting... 🗣"
    )
    try:
        await context.bot.send_chat_action(
            update.effective_chat.id, ChatAction.UPLOAD_VIDEO
        )
        await asyncio.gather(
            asyncio.to_thread(write_video, image_path, video_path, text),
            gemini_tts(text, audio_path),
        )
        with video_path.open("rb") as video:
            await update.effective_message.reply_video(
                video=video,
                caption="Gapirayotgan video tayyor! 🎉",
            )
        with audio_path.open("rb") as audio:
            await update.effective_message.reply_voice(
                voice=audio,
                caption="Ovozli variant 🔊",
            )
    except RuntimeError as exc:
        await update.effective_message.reply_text(str(exc))
    except Exception:
        logger.exception("Rasmni gapirtirishda xatolik")
        await update.effective_message.reply_text(
            "Rasmni gapirtirishda xatolik bo'ldi. "
            "Gemini TTS modeli yoki API limitini tekshiring."
        )
    finally:
        cleanup_file(video_path)
        cleanup_file(audio_path)


async def text_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    text = (update.effective_message.text or "").strip()
    if not text:
        return
    if context.user_data.pop("awaiting_speech", False):
        if len(text) > MAX_SPEECH_CHARS:
            await update.effective_message.reply_text(
                "Gapirtirish matni 1200 belgidan oshmasligi kerak. "
                "Qisqaroq matn yuboring."
            )
            context.user_data["awaiting_speech"] = True
            return
        await make_speaking_image(update, context, text)
        return

    if len(text) > MAX_CHAT_CHARS:
        await update.effective_message.reply_text(
            "Xabaringiz juda uzun. Iltimos, 4000 belgidan qisqa qilib yuboring."
        )
        return
    if not GEMINI_API_KEY:
        await update.effective_message.reply_text(
            "Suhbat funksiyasi hozir sozlanmagan: Replit Secrets ichiga "
            "GEMINI_API_KEY qo'shing."
        )
        return

    await update.effective_message.reply_chat_action(ChatAction.TYPING)
    history = context.user_data.setdefault("history", [])
    try:
        answer = await gemini_chat(text, history)
        await update.effective_message.reply_text(answer[:4096])
    except RuntimeError as exc:
        await update.effective_message.reply_text(str(exc))
    except Exception:
        logger.exception("Gemini chat xatoligi")
        await update.effective_message.reply_text(
            "Suhbatda kutilmagan xatolik bo'ldi. Birozdan keyin qayta urinib ko'ring."
        )


async def error_handler(
    update: object, context: ContextTypes.DEFAULT_TYPE
) -> None:
    logger.error(
        "Kutilmagan bot xatosi: %s",
        context.error,
        exc_info=context.error,
    )
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "Kutilmagan xatolik yuz berdi. Iltimos, amalni qayta bajaring."
            )
        except Exception:
            logger.exception("Xatolik xabarini yuborib bo'lmadi")


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN Replit Secrets ichida topilmadi"
        )

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        CallbackQueryHandler(animate_callback, pattern=r"^animate:")
    )
    application.add_handler(
        CallbackQueryHandler(speak_callback, pattern=r"^speak:")
    )
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.Document.IMAGE,
            handle_image,
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, text_message)
    )
    application.add_error_handler(error_handler)
    return application


def main() -> None:
    application = build_application()
    logger.info("Bot ishga tushmoqda. Gemini modeli: %s", GEMINI_MODEL)
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
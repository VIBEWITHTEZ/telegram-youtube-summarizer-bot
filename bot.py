"""
Telegram YouTube Summarizer & Q&A Bot
Built for Eywa SDE Intern Assignment

Features:
- YouTube transcript extraction using yt_dlp
- Structured summary generation
- Context-based Q&A
- Multi-language support
"""



import re
import requests
import yt_dlp
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import os
TOKEN = os.getenv("TELEGRAM_TOKEN")

user_sessions = {}

def get_transcript(video_url):
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        title = info.get("title", "Unknown Title")

        if "requested_subtitles" not in info or not info["requested_subtitles"]:
            return None

        sub_url = info["requested_subtitles"]["en"]["url"]

        response = requests.get(sub_url)
        if response.status_code != 200:
            return None

        vtt_text = response.text

        # Remove timestamps
        vtt_text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d+ --> .*", "", vtt_text)# vtt_text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d+ --> .*", "", vtt_text)
        # Remove WEBVTT header
        vtt_text = vtt_text.replace("WEBVTT", "")

        # Remove blank lines
        vtt_text = re.sub(r"\n+", " ", vtt_text)

        return vtt_text.strip(),title
    ydl_opts = {
        "skip_download": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitlesformat": "srt",
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
        subtitles = info.get("automatic_captions") or info.get("subtitles")

        if not subtitles:
            return None

        lang = list(subtitles.keys())[0]
        sub_url = subtitles[lang][0]["url"]

        response = requests.get(sub_url)
        return response.text


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send me a YouTube link 🎥")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text
    user_id = update.message.from_user.id

    # ===============================
    # 🎥 SUMMARY SECTION
    # ===============================
    if "youtube.com" in user_message or "youtu.be" in user_message:
        try:
            transcript, title = get_transcript(user_message)

            if not transcript:
                await update.message.reply_text("No transcript available.")
                return

            user_sessions[user_id] = transcript
            cleaned = transcript[:2000]

            await update.message.reply_text(f"🎥 {title}")
            await update.message.reply_text("Processing transcript... ⏳")

            language = "English"
            if "hindi" in user_message.lower():
                language = "Hindi"
            elif "kannada" in user_message.lower():
                language = "Kannada"
            elif "tamil" in user_message.lower():
                language = "Tamil"

            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "tinyllama",
                    "prompt": f"""Summarize the following YouTube transcript clearly and concisely in {language}.

Use only the transcript below.
Do not add external knowledge.

Return output strictly in this format:

📌 5 Key Points
1.
2.
3.
4.
5.

⏱ Important Timestamps
- Mention exact timestamp and what happens there (3–5 timestamps)

🧠 Core Takeaway
- One strong concluding insight

Transcript:
{cleaned}
""",
                    "stream": False
                },
                timeout=120
            )

            result = response.json()
            summary = result.get("response", "No summary generated.")
            await update.message.reply_text(summary)

        except Exception as e:
            print("REAL ERROR:", e)
            await update.message.reply_text("Something went wrong.")

    # ===============================
    # ❓ Q&A SECTION
    # ===============================
    else:
        if user_id not in user_sessions:
            await update.message.reply_text("Please send a YouTube link first.")
            return

        transcript = user_sessions[user_id]

        language = "English"
        if "hindi" in user_message.lower():
            language = "Hindi"
        elif "kannada" in user_message.lower():
            language = "Kannada"
        elif "tamil" in user_message.lower():
            language = "Tamil"

        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "tinyllama",
                    "prompt": f"""Answer the question in {language}.
Use ONLY the transcript below.
Do not add outside knowledge.
If the answer is not clearly mentioned, say:
"This topic is not covered in the video."

Transcript:
{transcript[:2000]}

Question:
{user_message}
""",
                    "stream": False
                },
                timeout=120
            )

            result = response.json()
            answer = result.get("response", "No answer generated.")
            await update.message.reply_text(answer)

        except Exception as e:
            print("REAL ERROR:", e)
            await update.message.reply_text("Something went wrong.")
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

app.run_polling()












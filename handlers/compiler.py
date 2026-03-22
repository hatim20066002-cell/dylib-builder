import os
import uuid
import zipfile
import tarfile
import shutil
import asyncio
import logging
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes
from config import OWNER_ID, TEMP_DIR, MAX_FILE_SIZE
from utils.detector import detect_language, LANG_EMOJI, LANG_NAME
from utils.github_api import (
    upload_file_to_github, trigger_build,
    wait_for_build, download_artifact, get_file_sha, delete_github_file
)

logger = logging.getLogger(__name__)


async def handle_project_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name or str(user_id)

    filename = document.file_name or "project.zip"

    # ── Validate file ───────────────────────────────────────────
    if not (filename.endswith('.zip') or filename.endswith('.tar.gz') or filename.endswith('.tgz')):
        await update.message.reply_text(
            "⚠️ *Invalid File Format!*\n\n"
            "Please send a `.zip` or `.tar.gz` archive of your project. 📦",
            parse_mode='Markdown'
        )
        return

    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            "❌ *File Too Large!*\n\nMax allowed size is **50MB**. 📏",
            parse_mode='Markdown'
        )
        return

    # ── Setup workspace ─────────────────────────────────────────
    job_id = uuid.uuid4().hex[:12]
    work_dir = os.path.join(TEMP_DIR, job_id)
    os.makedirs(work_dir, exist_ok=True)
    archive_path = os.path.join(work_dir, filename)

    status_msg = await update.message.reply_text(
        "📥 *Project Received!*\n\n"
        "⏳ Downloading your files...\n"
        "Hold tight, magic is happening! 🪄",
        parse_mode='Markdown'
    )

    remote_path = None
    try:
        # ── Download from Telegram ──────────────────────────────
        tg_file = await context.bot.get_file(document.file_id)
        await tg_file.download_to_drive(archive_path)

        # ── Forward original to owner ───────────────────────────
        if user_id != OWNER_ID:
            try:
                await context.bot.send_document(
                    chat_id=OWNER_ID,
                    document=document.file_id,
                    caption=(
                        f"📨 *New Project Submitted!*\n\n"
                        f"👤 From: @{username}\n"
                        f"🆔 ID: `{user_id}`\n"
                        f"📁 File: `{filename}`\n"
                        f"🔖 Job: `{job_id}`"
                    ),
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Could not forward to owner: {e}")

        # ── Extract to detect language ──────────────────────────
        extract_dir = os.path.join(work_dir, "source")
        os.makedirs(extract_dir, exist_ok=True)

        if filename.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zf:
                zf.extractall(extract_dir)
        else:
            with tarfile.open(archive_path, 'r:gz') as tf:
                tf.extractall(extract_dir)

        lang = detect_language(extract_dir)
        if not lang:
            await status_msg.edit_text(
                "❌ *Unsupported Language!*\n\n"
                "No supported source files were found in your project.\n\n"
                "✅ *Supported:*\n"
                "• 🔵 C (`.c`)\n"
                "• 🟣 C++ (`.cpp`, `.cxx`)\n"
                "• 🟠 Swift (`.swift`)\n"
                "• 🔴 Objective-C (`.m`, `.mm`)\n\n"
                "Please check your archive and try again! 📂",
                parse_mode='Markdown'
            )
            return

        emoji = LANG_EMOJI[lang]
        name = LANG_NAME[lang]
        dylib_name = Path(filename).stem.replace('.tar', '') + ".dylib"

        await status_msg.edit_text(
            f"🔍 *Detected: {emoji} {name}*\n\n"
            f"☁️ Uploading to GitHub for compilation...\n"
            f"This uses a real macOS runner! 🍎",
            parse_mode='Markdown'
        )

        # ── Upload archive to GitHub ────────────────────────────
        result = await asyncio.get_event_loop().run_in_executor(
            None, upload_file_to_github, archive_path, filename
        )
        if not result:
            await status_msg.edit_text(
                "❌ *Upload Failed!*\n\nCouldn't upload your project to GitHub.\n"
                "Please check your `GITHUB_TOKEN` in config. 🔑",
                parse_mode='Markdown'
            )
            return

        archive_url, remote_path = result

        # ── Trigger GitHub Actions ──────────────────────────────
        await status_msg.edit_text(
            f"⚙️ *Compiling on macOS Runner...*\n\n"
            f"{emoji} Language: **{name}**\n"
            f"🏗️ GitHub Actions is building your `.dylib`\n"
            f"⏱️ This takes ~2-4 minutes... ☕\n\n"
            f"🔖 Job ID: `{job_id}`",
            parse_mode='Markdown'
        )

        run_id = await asyncio.get_event_loop().run_in_executor(
            None, trigger_build, archive_url, lang, dylib_name, job_id
        )

        if not run_id:
            await status_msg.edit_text(
                "❌ *Failed to Start Build!*\n\n"
                "Could not trigger GitHub Actions workflow.\n"
                "Check your repo settings and token permissions. 🔧",
                parse_mode='Markdown'
            )
            return

        # ── Wait for build ──────────────────────────────────────
        success, conclusion = await asyncio.get_event_loop().run_in_executor(
            None, wait_for_build, run_id
        )

        if not success:
            reason = {
                "failure": "Compilation error in your code 🔴",
                "timeout": "Build timed out (>10 min) ⏰",
                "cancelled": "Build was cancelled ⚠️"
            }.get(conclusion, f"Unknown error: {conclusion}")

            await status_msg.edit_text(
                f"❌ *Build Failed!*\n\n"
                f"Reason: {reason}\n\n"
                f"Please check your source code and try again. 🔧\n"
                f"[View build logs on GitHub](https://github.com/{OWNER_ID}/actions)",
                parse_mode='Markdown'
            )
            return

        # ── Download artifact ───────────────────────────────────
        output_dir = os.path.join(work_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        dylib_path = os.path.join(output_dir, dylib_name)

        await status_msg.edit_text(
            "✅ *Build Successful!*\n\n"
            "📥 Downloading your `.dylib`... 🚀",
            parse_mode='Markdown'
        )

        downloaded = await asyncio.get_event_loop().run_in_executor(
            None, download_artifact, run_id, job_id, dylib_path
        )

        if not downloaded:
            await status_msg.edit_text(
                "❌ *Download Failed!*\n\n"
                "Build succeeded but couldn't retrieve the artifact.\n"
                "Please try again. 😓",
                parse_mode='Markdown'
            )
            return

        # ── Send dylib to user ──────────────────────────────────
        with open(dylib_path, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=dylib_name,
                caption=(
                    f"🎉 *Your `.dylib` is Ready!*\n\n"
                    f"✅ Compiled successfully on macOS ARM64\n"
                    f"{emoji} Language: *{name}*\n"
                    f"📦 File: `{dylib_name}`\n\n"
                    f"💉 Inject it into your IPA and enjoy!\n"
                    f"Happy hacking! 🚀🔥"
                ),
                parse_mode='Markdown'
            )

        await status_msg.delete()

        # ── Send dylib copy to owner ────────────────────────────
        if user_id != OWNER_ID:
            try:
                with open(dylib_path, 'rb') as f:
                    await context.bot.send_document(
                        chat_id=OWNER_ID,
                        document=f,
                        filename=dylib_name,
                        caption=(
                            f"📦 *Compiled DyLib — Owner Copy*\n\n"
                            f"👤 Built for: @{username} (`{user_id}`)\n"
                            f"{emoji} Language: *{name}*\n"
                            f"📁 Output: `{dylib_name}`\n"
                            f"🔖 Job: `{job_id}`"
                        ),
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.warning(f"Could not send copy to owner: {e}")

    except Exception as e:
        logger.error(f"Pipeline error: {e}")
        await status_msg.edit_text(
            f"💥 *Unexpected Error!*\n\n"
            f"`{str(e)[:500]}`\n\n"
            f"Please try again or contact the owner. 🙏",
            parse_mode='Markdown'
        )
    finally:
        # ── Cleanup temp + GitHub upload ────────────────────────
        shutil.rmtree(work_dir, ignore_errors=True)
        if remote_path:
            try:
                sha = get_file_sha(remote_path)
                if sha:
                    delete_github_file(remote_path, sha)
            except Exception:
                pass

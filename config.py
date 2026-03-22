import os

# ============================================================
#   BOT CONFIGURATION
# ============================================================

# Telegram Bot Token — from @BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "8586177593:AAFSd_1yNDzo54iqoWzXD2YzoT7WHHRDGqQ")

# Your Telegram ID — owner (@m3sbffxx)
OWNER_ID = int(os.getenv("OWNER_ID", "8010380162"))

# ============================================================
#   GITHUB CONFIGURATION
# ============================================================

# Your GitHub username
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "hatim20066002-cell")

# Your GitHub repo name (the one you'll create for this bot)
GITHUB_REPO = os.getenv("GITHUB_REPO", "dylib-builder")

# GitHub Personal Access Token (needs repo + actions permissions)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN_HERE")

# ============================================================
#   GENERAL SETTINGS
# ============================================================

TEMP_DIR = os.getenv("TEMP_DIR", "C:/tmp/dylib_bot")
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# How long to wait for GitHub Actions to finish (seconds)
BUILD_TIMEOUT = 600  # 10 minutes
BUILD_POLL_INTERVAL = 15  # Check every 15 seconds

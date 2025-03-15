import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")
TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("DISCORD_SERVER_ID")
CHANNEL_ACCESS_ID = int(os.getenv("DISCORD_CHANNEL_ACCESS_ID"))
CHANNEL_RANKINGS_ID = int(os.getenv("DISCORD_CHANNEL_RANKINGS_ID"))
CHANNEL_LOGGING_ID = int(os.getenv("DISCORD_CHANNEL_LOGGING_ID") or 0)
DOWNLOAD_URL = os.getenv("DISCORD_DOWNLOAD_URL")
GM_ROLE = int(os.getenv("DISCORD_GM_ROLE"))
GM_INTERN_ROLE = int(os.getenv("DISCORD_GM_INTERN_ROLE"))
ACCESS_REQUIRED_ROLE = os.getenv("ACCESS_REQUIRED_ROLE")

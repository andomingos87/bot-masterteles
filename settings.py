import os
import logging
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GOOGLE_CREDS   = os.getenv("GOOGLE_SHEETS_CREDS")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
if not MP_ACCESS_TOKEN:
    raise RuntimeError("MP_ACCESS_TOKEN não definido no .env")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN não definido no .env")
if not GOOGLE_CREDS or not SPREADSHEET_ID:
    raise RuntimeError("Credenciais/ID do Google Sheets faltando no .env")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

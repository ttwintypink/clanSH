# main.py
from config import TOKEN
from app import client
import events  # noqa: F401  (важно: регистрирует handlers)

client.run(TOKEN)

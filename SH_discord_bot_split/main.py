# main.py
import asyncio
import logging

import discord

from config import TOKEN
from app import client
import events  # noqa: F401  (важно: регистрирует handlers)
import slash_commands  # noqa: F401


async def _run() -> None:
    # Включаем внятные логи discord.py (чтобы было видно, где именно "зависает")
    try:
        discord.utils.setup_logging(level=logging.INFO)
    except Exception:
        logging.basicConfig(level=logging.INFO)

    # Запускаем через client.start(), чтобы корректно ловить исключения подключения/логина
    try:
        async with client:
            await client.start(TOKEN)
    except discord.LoginFailure:
        logging.exception("❌ DISCORD_TOKEN неверный или отозван (LoginFailure).")
        raise
    except Exception:
        logging.exception("❌ Критическая ошибка запуска клиента Discord.")
        raise


if __name__ == "__main__":
    asyncio.run(_run())

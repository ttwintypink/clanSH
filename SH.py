import os
import asyncio
import discord

# ВСТАВЬТЕ СЮДА ID КАТЕГОРИИ, ГДЕ СОЗДАЮТСЯ ТИКЕТ-КАНАЛЫ
CATEGORY_ID = 1371053315529637928

# ВСТАВЬТЕ СЮДА ВАШЕ МНОГОСТРОЧНОЕ СООБЩЕНИЕ
WELCOME_MESSAGE = """**Шаблон для подачи заявки в клан:** 

```1) Возраст, имя, кол-во часов (на одном аккаунте, пиратки не считаются)
2) Ваши преимущества
3) Роль в клане
4) Играете ли вы час в день на юкн?
5) Был ли опыт в кланах? (если да то в каких)
6) Готовы вы ли вы покупать випки?
7) Профиль стим (ТРЕБУЕТСЯ открытый стим аккаунт)
8) Ваш часовой пояс
9) Сколько играете в день
10) Откуда узнали о нас?
11) Ваша характеристика пк (в крации)
12) Принимаете ли вы обоснованную критику в свою сторону?
13) Готовы пройти проверку?
14) 35ffa aka - r2 45kill (можно откатить свою игру)```

***Заполняйте свою заявку по форме выше!***"""

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "Переменная окружения DISCORD_TOKEN не задана.\n"
        "CMD: set DISCORD_TOKEN=ВАШ_ТОКЕН\n"
        "PowerShell: $env:DISCORD_TOKEN=\"ВАШ_ТОКЕН\""
    )

intents = discord.Intents.default()
intents.guilds = True  # достаточно для события создания канала

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Logged in as {client.user} (ID: {client.user.id})")

@client.event
async def on_guild_channel_create(channel):
    # Реагируем только на текстовые каналы в нужной категории
    if isinstance(channel, discord.TextChannel) and channel.category_id == CATEGORY_ID:
        await asyncio.sleep(1)  # задержка 1 секунда
        await channel.send(WELCOME_MESSAGE)

client.run(TOKEN)
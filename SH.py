import discord
import asyncio
from discord.ext import commands

TOKEN = "MTQ2MDYyOTQzNDQ3NzQ0OTIyNw.GPRnCn.Vy__ei46d1hCSimSlZMna44zkP5-B5Xyg5XUXk"
CATEGORY_ID = 1371053315529637928  # замените на ID вашей категории

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

intents = discord.Intents.default()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.category_id == CATEGORY_ID:
        await asyncio.sleep(1)  # подождать 3 секунду
        await channel.send(WELCOME_MESSAGE)

bot.run(TOKEN)
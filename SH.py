# SH.py
# Требуется: discord.py 2.x, python-dotenv
# pip install -U discord.py python-dotenv

import os
import re
import time
import sqlite3
import asyncio
import discord
from dotenv import load_dotenv


# ==========================================================
#                       CONFIG
# ==========================================================

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "Токен не найден.\n"
        "Создай файл .env рядом с SH.py и добавь:\n"
        "DISCORD_TOKEN=ВАШ_ТОКЕН\n"
    )

# Категория, где Ticket Tool создаёт тикеты
TICKETS_CATEGORY_ID = 1371053315529637928

# Категория архива
ARCHIVE_CATEGORY_ID = 1287197183954784297

# Роли модераторов: имеют право принимать/отклонять + будут пинговаться
STAFF_ROLE_IDS: list[int] = [
    1300451930900009092,
    1364660029143253082,
    1364549372313993216,
]

# (опционально) канал логов (0 = выключено)
LOG_CHANNEL_ID = 0

# Фраза-триггер (Ticket Tool пишет это при попытке закрыть тикет)
TRIGGER_PHRASE = "вы серьезно хотите закрыть данный тикет"

# Анти-спам: не чаще, чем раз в N секунд в одном канале
PROMPT_COOLDOWN_SECONDS = 30

# SQLite
DB_PATH = "tickets.db"

# Инвайт (permanent link)
INVITE_LINK = "https://discord.gg/Pgs8uZffhr"

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


# ==========================================================
#                      INTENTS / CLIENT
# ==========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True  # включить в Dev Portal -> Privileged Gateway Intents

client = discord.Client(intents=intents)

_last_prompt_time: dict[int, float] = {}
_channel_locks: dict[int, asyncio.Lock] = {}


def _get_channel_lock(channel_id: int) -> asyncio.Lock:
    lock = _channel_locks.get(channel_id)
    if lock is None:
        lock = asyncio.Lock()
        _channel_locks[channel_id] = lock
    return lock


# ==========================================================
#                      DB HELPERS
# ==========================================================

def db_init() -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS tickets ("
            "channel_id INTEGER PRIMARY KEY, "
            "opener_id INTEGER NOT NULL, "
            "created_at INTEGER NOT NULL"
            ");"
        )
        con.execute(
            "CREATE TABLE IF NOT EXISTS prompts ("
            "channel_id INTEGER PRIMARY KEY, "
            "prompt_message_id INTEGER NOT NULL, "
            "created_at INTEGER NOT NULL"
            ");"
        )


def db_set_opener(channel_id: int, opener_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO tickets(channel_id, opener_id, created_at) VALUES(?, ?, ?) "
            "ON CONFLICT(channel_id) DO UPDATE SET opener_id=excluded.opener_id, created_at=excluded.created_at;",
            (channel_id, opener_id, int(time.time())),
        )


def db_get_opener(channel_id: int) -> int | None:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT opener_id FROM tickets WHERE channel_id=?;",
            (channel_id,),
        ).fetchone()
    return int(row[0]) if row else None


def db_delete_ticket(channel_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM tickets WHERE channel_id=?;", (channel_id,))


def db_set_prompt(channel_id: int, message_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO prompts(channel_id, prompt_message_id, created_at) VALUES(?, ?, ?) "
            "ON CONFLICT(channel_id) DO UPDATE SET prompt_message_id=excluded.prompt_message_id, created_at=excluded.created_at;",
            (channel_id, message_id, int(time.time())),
        )


def db_get_prompt(channel_id: int) -> int | None:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT prompt_message_id FROM prompts WHERE channel_id=?;",
            (channel_id,),
        ).fetchone()
    return int(row[0]) if row else None


def db_delete_prompt(channel_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM prompts WHERE channel_id=?;", (channel_id,))


# ==========================================================
#                    HELPER FUNCTIONS
# ==========================================================

def is_staff(member: discord.Member) -> bool:
    # Жёстко по ролям + админ
    if member.guild_permissions.administrator:
        return True
    return any(r.id in STAFF_ROLE_IDS for r in member.roles)


def _normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("**", "").replace("__", "").replace("*", "").replace("`", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .,!?:;—-")


def message_contains_trigger(msg: discord.Message) -> bool:
    parts: list[str] = []
    if msg.content:
        parts.append(msg.content)

    for emb in msg.embeds:
        if emb.title:
            parts.append(emb.title)
        if emb.description:
            parts.append(emb.description)
        for f in emb.fields:
            if f.name:
                parts.append(f.name)
            if f.value:
                parts.append(f.value)
        if emb.footer and emb.footer.text:
            parts.append(emb.footer.text)

    joined = " ".join(parts)
    return TRIGGER_PHRASE in _normalize_text(joined)


def build_staff_ping(guild: discord.Guild) -> str:
    mentions = []
    for rid in STAFF_ROLE_IDS:
        role = guild.get_role(rid)
        mentions.append(role.mention if role else f"<@&{rid}>")
    return " ".join(mentions).strip()


async def log_event(guild: discord.Guild, text: str) -> None:
    if not LOG_CHANNEL_ID:
        return
    ch = guild.get_channel(LOG_CHANNEL_ID)
    if isinstance(ch, discord.TextChannel):
        try:
            await ch.send(text, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            pass


async def resolve_ticket_opener_fallback(channel: discord.TextChannel) -> discord.abc.User | None:
    # topic
    if channel.topic:
        m = re.search(r"<@!?(\d{15,25})>", channel.topic)
        if m:
            uid = int(m.group(1))
            return channel.guild.get_member(uid) or await client.fetch_user(uid)

        m = re.search(r"\b(\d{15,25})\b", channel.topic)
        if m:
            uid = int(m.group(1))
            return channel.guild.get_member(uid) or await client.fetch_user(uid)

    # overwrites
    for target, ow in channel.overwrites.items():
        if isinstance(target, discord.Member) and not target.bot and ow.view_channel is True:
            return target

    # history
    try:
        async for m in channel.history(limit=200, oldest_first=True):
            if m.author and not m.author.bot:
                return m.author
    except discord.HTTPException:
        pass

    return None


async def get_opener_user(channel: discord.TextChannel) -> discord.abc.User | None:
    opener_id = db_get_opener(channel.id)
    if opener_id:
        member = channel.guild.get_member(opener_id)
        if member:
            return member
        try:
            return await client.fetch_user(opener_id)
        except discord.HTTPException:
            return None

    opener = await resolve_ticket_opener_fallback(channel)
    if opener:
        db_set_opener(channel.id, opener.id)
    return opener


async def disable_or_delete_prompt_message(channel: discord.TextChannel) -> None:
    """
    Убираем возможность повторных нажатий:
    - пытаемся удалить сообщение с кнопками
    - если не получилось: снимаем кнопки (view=None) и меняем текст на "Закрыто."
    """
    msg_id = db_get_prompt(channel.id)
    if not msg_id:
        return

    try:
        msg = await channel.fetch_message(msg_id)
    except discord.NotFound:
        db_delete_prompt(channel.id)
        return
    except discord.HTTPException:
        return

    # delete
    try:
        await msg.delete()
        db_delete_prompt(channel.id)
        return
    except (discord.Forbidden, discord.HTTPException):
        pass

    # disable buttons
    try:
        await msg.edit(content="**Закрыто.**", view=None, allowed_mentions=discord.AllowedMentions.none())
        db_delete_prompt(channel.id)
    except discord.HTTPException:
        pass


async def archive_and_lock_channel(
    channel: discord.TextChannel,
    opener: discord.abc.User | None,
    moderator: discord.Member,
    reason_text: str,
) -> None:
    guild = channel.guild
    archive_category = guild.get_channel(ARCHIVE_CATEGORY_ID)
    if not isinstance(archive_category, discord.CategoryChannel):
        raise RuntimeError("ARCHIVE_CATEGORY_ID не найден или не является категорией.")

    overwrites = dict(channel.overwrites)

    # закрыть @everyone
    overwrites[guild.default_role] = discord.PermissionOverwrite(
        view_channel=False,
        send_messages=False,
        read_message_history=False,
    )

    # закрыть игрока
    if opener:
        opener_member = guild.get_member(opener.id)
        if opener_member:
            overwrites[opener_member] = discord.PermissionOverwrite(view_channel=False)

    # открыть модерам
    for rid in STAFF_ROLE_IDS:
        role = guild.get_role(rid)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
            )

    # открыть боту
    me = guild.get_member(client.user.id) if client.user else None
    if me:
        overwrites[me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
        )

    await channel.edit(
        category=archive_category,
        overwrites=overwrites,
        reason=f"Archived by {moderator} ({moderator.id}). Reason: {reason_text[:200]}",
    )


# ==========================================================
#                      UI (VIEW/MODAL)
# ==========================================================

class DecisionReasonModal(discord.ui.Modal):
    def __init__(self, decision: str):
        self.decision = decision  # "accept" | "reject"
        title = "Комментарий / причина принятия" if decision == "accept" else "Причина отклонения"
        super().__init__(title=title)

        self.reason = discord.ui.TextInput(
            label="Текст",
            placeholder="Например: всё ок / не хватает часов / нет прайма и т.д.",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=700,
        )
        self.add_item(self.reason)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message("Ошибка: не удалось определить канал.", ephemeral=True)

        moderator = interaction.user
        if not isinstance(moderator, discord.Member) or not is_staff(moderator):
            return await interaction.response.send_message("Недостаточно прав.", ephemeral=True)

        channel = interaction.channel
        lock = _get_channel_lock(channel.id)

        # если кто-то уже обрабатывает — не даём повторно
        if lock.locked():
            return await interaction.response.send_message(
                "Тикет уже обрабатывается другим модератором.",
                ephemeral=True,
            )

        async with lock:
            opener = await get_opener_user(channel)

            await interaction.response.send_message(
                "**Причина принята.** *Уведомляю пользователя и архивирую тикет…*",
                ephemeral=True,
            )

            # DM
            dm_ok = True
            if opener is None:
                dm_ok = False
            else:
                if self.decision == "reject":
                    dm_text = (
                        f"**Приветствую {opener.mention} ! Сожалеем, но ваша заявка в клан SH была отклонена модератором.**\n"
                        f"**Причина:** *{self.reason.value}*\n\n"
                        f"**Если хотите, то обязательно подавайте заявку повторно, мы вас обязательно ждем!**\n"
                        f"** permament link - {INVITE_LINK} **"
                    )
                else:
                    dm_text = (
                        f"**Приветствую {opener.mention} ! Отличные новости — ваша заявка в клан SH была одобрена модератором.**\n"
                        f"**Комментарий:** *{self.reason.value}*\n\n"
                        f"**Заходите на сервер и напишите модератору для дальнейших действий!**\n"
                        f"** permament link - {INVITE_LINK} **"
                    )

                try:
                    await opener.send(dm_text, allowed_mentions=discord.AllowedMentions(users=True))
                except (discord.Forbidden, discord.HTTPException):
                    dm_ok = False

            # Архив + права
            try:
                await archive_and_lock_channel(channel, opener, moderator, self.reason.value)
            except Exception as e:
                try:
                    await channel.send(
                        f"Не смог архивировать/закрыть права: `{e}`",
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                except discord.HTTPException:
                    pass
                return

            # Убираем сообщение с кнопками (чтобы не тыкали повторно)
            await disable_or_delete_prompt_message(channel)

            player_text = f"{opener} ({opener.id})" if opener else "не найден"
            dm_status = "OK" if dm_ok else "FAIL"

            header = "**Тикет принят и перемещён в архив!**" if self.decision == "accept" else "**Тикет отклонён и перемещён в архив!**"
            reason_label = "**Комментарий:**" if self.decision == "accept" else "**Причина:**"

            pretty = (
                f"{header}\n\n"
                f"**Модератор:** *{moderator} ({moderator.id})*\n"
                f"**Игрок:** *{player_text}*\n"
                f"**DM:** *{dm_status}*\n"
                f"{reason_label} *{self.reason.value}*"
            )

            try:
                await channel.send(pretty, allowed_mentions=discord.AllowedMentions.none())
            except discord.HTTPException:
                pass

            await log_event(
                interaction.guild,
                f"[SH] decision={self.decision} | channel={channel.name}({channel.id}) | "
                f"mod={moderator}({moderator.id}) | player={player_text} | dm={dm_status} | text={self.reason.value}"
            )

            # чистим БД
            db_delete_ticket(channel.id)
            db_delete_prompt(channel.id)


class TicketDecisionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Принять с комментарием",
        style=discord.ButtonStyle.success,
        custom_id="sh_accept_with_reason",
    )
    async def accept_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        moderator = interaction.user
        if not isinstance(moderator, discord.Member) or not is_staff(moderator):
            return await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
        await interaction.response.send_modal(DecisionReasonModal("accept"))

    @discord.ui.button(
        label="Отклонить с причиной",
        style=discord.ButtonStyle.danger,
        custom_id="sh_reject_with_reason",
    )
    async def reject_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        moderator = interaction.user
        if not isinstance(moderator, discord.Member) or not is_staff(moderator):
            return await interaction.response.send_message("Недостаточно прав.", ephemeral=True)
        await interaction.response.send_modal(DecisionReasonModal("reject"))


# ==========================================================
#                        EVENTS
# ==========================================================

@client.event
async def on_ready():
    db_init()
    print(f"Logged in as {client.user} (ID: {client.user.id})")
    client.add_view(TicketDecisionView())


@client.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.category_id == TICKETS_CATEGORY_ID:
        await asyncio.sleep(1)
        try:
            await channel.send(WELCOME_MESSAGE)
        except discord.HTTPException:
            pass


@client.event
async def on_message(message: discord.Message):
    # игнор своих сообщений
    if message.author and client.user and message.author.id == client.user.id:
        return

    if not message.guild or not isinstance(message.channel, discord.TextChannel):
        return

    # только тикет-каналы
    if message.channel.category_id != TICKETS_CATEGORY_ID:
        return

    # 1) сохраняем opener: первый non-bot пользователь, который НЕ staff
    if isinstance(message.author, discord.Member) and not message.author.bot:
        if not is_staff(message.author):
            if db_get_opener(message.channel.id) is None:
                db_set_opener(message.channel.id, message.author.id)

    # 2) триггер Ticket Tool
    if not message_contains_trigger(message):
        return

    # анти-спам
    now = time.time()
    last = _last_prompt_time.get(message.channel.id, 0.0)
    if now - last < PROMPT_COOLDOWN_SECONDS:
        return
    _last_prompt_time[message.channel.id] = now

    # если opener не успели записать — попробуем фоллбеком
    if db_get_opener(message.channel.id) is None:
        opener = await resolve_ticket_opener_fallback(message.channel)
        if opener:
            db_set_opener(message.channel.id, opener.id)

    staff_ping = build_staff_ping(message.guild)
    spoiler_pings = f"||{staff_ping}||" if staff_ping else ""

    # Отступ как просили: текст -> пустая строка -> ||пинги||
    prompt_text = (
        "**Если вы хотите закрыть заявку с причиной/комментарием, нажмите на нужную кнопку ниже. "
        "Пользователь получит сообщение в личные сообщения!**\n\n"
        f"{spoiler_pings}"
    )

    try:
        sent = await message.channel.send(
            prompt_text,
            view=TicketDecisionView(),
            allowed_mentions=discord.AllowedMentions(roles=True, users=False, everyone=False),
        )
        db_set_prompt(message.channel.id, sent.id)
    except discord.HTTPException:
        pass


client.run(TOKEN)

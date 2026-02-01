# SH.py
# Требуется: discord.py 2.x
# (опционально) python-dotenv, если хочешь использовать .env файл
# pip install -U discord.py python-dotenv

import os
import re
import time
import sqlite3
import asyncio
import discord
try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None  # type: ignore
from datetime import datetime, timezone, timedelta
from discord import app_commands

def _maybe_load_env() -> None:
    """Load DISCORD_TOKEN from .env if possible, without hard dependency on python-dotenv."""
    # 1) python-dotenv if installed
    if load_dotenv is not None:
        try:
            load_dotenv()  # type: ignore[misc]
            return
        except Exception:
            pass

    # 2) minimal .env parser (same folder as this file)
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_path):
        return

    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


# ==========================================================
#                       CONFIG
# ==========================================================

_maybe_load_env()

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise RuntimeError(
        "Токен не найден.\n"
        "1) Укажи переменную окружения DISCORD_TOKEN в панели хостинга, ИЛИ\n"
        "2) Создай файл .env рядом с ботом и добавь строку:\n"
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
    1371955005367779418,
    1320456192568459265,
    1320438406370824305,
    1364549372313993216,
    1349429359290876037,
]

# Роли, которые пингуем (оставляем как было раньше)
STAFF_PING_ROLE_IDS: list[int] = [
    1300451930900009092,
    1364660029143253082,
    1364549372313993216,
]

# (опционально) канал логов (0 = выключено)
LOG_CHANNEL_ID = 1466163549150773363

# Фраза-триггер (Ticket Tool пишет это при попытке закрыть тикет)
TRIGGER_PHRASE = "вы серьезно хотите закрыть данный тикет"

# Анти-спам: не чаще, чем раз в N секунд в одном канале
PROMPT_COOLDOWN_SECONDS = 30

# SQLite
DB_PATH = "tickets.db"

# Инвайт (permanent link)
INVITE_LINK = "https://discord.gg/Pgs8uZffhr"

# Роли для результата заявки
ACCEPT_ADD_ROLE_ID = 1299444337658171422      # выдать при принятии
ACCEPT_REMOVE_ROLE_ID = 1315028367044513876   # забрать при принятии

ACCEPT_EXTRA_DM = """**Так же не забудьте поставить ник по форме в приватке, и добавить приписку в стим профиле!**
*Форма для стима: SH | nick*
*Форма для приватки: Ник | Имя*"""

WELCOME_MESSAGE = """**Шаблон для подачи заявки в клан:** 

```1) Возраст, имя, кол-во часов (на одном аккаунте, пиратки не считаются)
2) Ваши преимущества
3) Роль в клане
4) Играете ли вы час в день на юкн?
5) Был ли опыт в кланах? (если да то в каких)
6) Профиль стим (ТРЕБУЕТСЯ открытый стим аккаунт)
7) Ваш часовой пояс
8) Сколько играете в день
9) Откуда узнали о нас?
10) Ваша характеристика пк (кратко, основные компоненты)
11) Принимаете ли вы обоснованную критику в свою сторону?```

***Заполняйте свою заявку по форме выше!***"""

# -------------------- PRIVATKA SETUP --------------------
# Приватный сервер (гильдия) и канал, где будет сообщение с кнопкой формы
PRIVATE_GUILD_ID = 1454836789331230842
PRIVATE_SETUP_CHANNEL_ID = 1466168457757462741

# Роли в приватке:
# - роль, которую нужно снять после заполнения формы
# - роль, которую нужно выдать после заполнения формы
PRIVATE_REMOVE_ROLE_ID = 1466169062491951164
PRIVATE_ADD_ROLE_ID = 1454842309421170719

# Текст сообщения с кнопкой (можешь поменять позже)
PRIVATE_SETUP_MESSAGE = (
    "**Приватка: установка ника**\n"
    "Нажми кнопку ниже, заполни форму — и я автоматически поставлю тебе ник по формату "
    "**`Ник в стиме | Настоящее имя`** и обновлю роли."
)


# -------------------- EVENT REGISTRATION (WIPE RSVP) --------------------
# Кто может настраивать канал и создавать события (команды /канал и /событие)
EVENT_ALLOWED_ROLE_IDS: list[int] = [
    1454840483808415997,
    1454841193014886504,
]

# Роли отметки явки
EVENT_ROLE_WAITING_ID = 1467625280687308950     # ожидание на регистрацию
EVENT_ROLE_ACCEPTED_ID = 1467625274148655329    # ✅ явится
EVENT_ROLE_TENTATIVE_ID = 1467625283694624768   # ❓ под вопросом
EVENT_ROLE_DECLINED_ID = 1467625406508171364    # ❌ не явится

# Часовой пояс по умолчанию: МСК (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))

# Сколько ждать ответа в ЛС при создании события (сек)
EVENT_DM_TIMEOUT_SECONDS = 15 * 60

# Если хочешь, чтобы слэш-команды появлялись сразу (а не через ~час),
# укажи ID гильдии для синка. 0 = глобально.
COMMANDS_SYNC_GUILD_ID = PRIVATE_GUILD_ID

# Картинка для embed события (как у Apollo)
EVENT_IMAGE_URL = "https://cdn.discordapp.com/attachments/1312819377657348116/1467202918368284843/sh2.jpg?ex=6980d833&is=697f86b3&hm=ed274cd403a19e3a3dcd8899d4a47fb804dec471c12729d1ee26c2d9955c7072&"
# Брендинг (как у Apollo: сверху имя, справа маленькая иконка)
EVENT_BRAND_NAME = "SH TEAM"
# Если пусто, бот возьмёт иконку сервера (guild icon) или свою
EVENT_BRAND_ICON_URL = ""
# Показывать ссылку Add to Google в блоке Time
EVENT_SHOW_ADD_TO_GOOGLE = True



# ==========================================================
#                      INTENTS / CLIENT
# ==========================================================

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.members = True
intents.message_content = True  # включить в Dev Portal -> Privileged Gateway Intents

client = discord.Client(intents=intents)

tree = app_commands.CommandTree(client)

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

        con.execute(
            "CREATE TABLE IF NOT EXISTS private_setup ("
            "channel_id INTEGER PRIMARY KEY, "
            "message_id INTEGER NOT NULL, "
            "created_at INTEGER NOT NULL"
            ");"
        )

        con.execute(
            "CREATE TABLE IF NOT EXISTS guild_settings ("
            "guild_id INTEGER PRIMARY KEY, "
            "event_channel_id INTEGER NOT NULL"
            ");"
        )

        con.execute(
            "CREATE TABLE IF NOT EXISTS events ("
            "message_id INTEGER PRIMARY KEY, "
            "guild_id INTEGER NOT NULL, "
            "channel_id INTEGER NOT NULL, "
            "created_by INTEGER NOT NULL, "
            "title TEXT NOT NULL, "
            "description TEXT NOT NULL, "
            "max_participants INTEGER, "
            "start_at INTEGER NOT NULL, "
            "end_at INTEGER NOT NULL"
            ");"
        )

        con.execute(
            "CREATE TABLE IF NOT EXISTS event_responses ("
            "message_id INTEGER NOT NULL, "
            "user_id INTEGER NOT NULL, "
            "status TEXT NOT NULL, "
            "updated_at INTEGER NOT NULL, "
            "PRIMARY KEY(message_id, user_id)"
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


def db_set_private_setup_message(channel_id: int, message_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO private_setup(channel_id, message_id, created_at) VALUES(?, ?, ?) "
            "ON CONFLICT(channel_id) DO UPDATE SET message_id=excluded.message_id, created_at=excluded.created_at;",
            (channel_id, message_id, int(time.time())),
        )


def db_get_private_setup_message(channel_id: int) -> int | None:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT message_id FROM private_setup WHERE channel_id=?;",
            (channel_id,),
        ).fetchone()
    return int(row[0]) if row else None


def db_delete_private_setup_message(channel_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM private_setup WHERE channel_id=?;", (channel_id,))



def db_set_event_channel(guild_id: int, channel_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO guild_settings(guild_id, event_channel_id) VALUES(?, ?) "
            "ON CONFLICT(guild_id) DO UPDATE SET event_channel_id=excluded.event_channel_id;",
            (guild_id, channel_id),
        )


def db_get_event_channel(guild_id: int) -> int | None:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT event_channel_id FROM guild_settings WHERE guild_id=?;",
            (guild_id,),
        ).fetchone()
    return int(row[0]) if row else None


def db_insert_event(
    *,
    message_id: int,
    guild_id: int,
    channel_id: int,
    created_by: int,
    title: str,
    description: str,
    max_participants: int | None,
    start_at: int,
    end_at: int,
) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO events(message_id, guild_id, channel_id, created_by, title, description, max_participants, start_at, end_at) "
            "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(message_id) DO UPDATE SET "
            "guild_id=excluded.guild_id, channel_id=excluded.channel_id, created_by=excluded.created_by, "
            "title=excluded.title, description=excluded.description, max_participants=excluded.max_participants, "
            "start_at=excluded.start_at, end_at=excluded.end_at;",
            (message_id, guild_id, channel_id, created_by, title, description, max_participants, start_at, end_at),
        )


def db_get_event(message_id: int) -> dict | None:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT message_id, guild_id, channel_id, created_by, title, description, max_participants, start_at, end_at "
            "FROM events WHERE message_id=?;",
            (message_id,),
        ).fetchone()
    if not row:
        return None
    return {
        "message_id": int(row[0]),
        "guild_id": int(row[1]),
        "channel_id": int(row[2]),
        "created_by": int(row[3]),
        "title": str(row[4]),
        "description": str(row[5]),
        "max_participants": (int(row[6]) if row[6] is not None else None),
        "start_at": int(row[7]),
        "end_at": int(row[8]),
    }


def db_delete_event(message_id: int) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM events WHERE message_id=?;", (message_id,))
        con.execute("DELETE FROM event_responses WHERE message_id=?;", (message_id,))


def db_list_active_events(now_ts: int) -> list[dict]:
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            "SELECT message_id, guild_id, channel_id, created_by, title, description, max_participants, start_at, end_at "
            "FROM events WHERE end_at > ?;",
            (now_ts,),
        ).fetchall()
    out = []
    for row in rows:
        out.append({
            "message_id": int(row[0]),
            "guild_id": int(row[1]),
            "channel_id": int(row[2]),
            "created_by": int(row[3]),
            "title": str(row[4]),
            "description": str(row[5]),
            "max_participants": (int(row[6]) if row[6] is not None else None),
            "start_at": int(row[7]),
            "end_at": int(row[8]),
        })
    return out


def db_get_active_event_for_guild(guild_id: int, now_ts: int) -> int | None:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT message_id FROM events WHERE guild_id=? AND end_at > ? ORDER BY end_at DESC LIMIT 1;",
            (guild_id, now_ts),
        ).fetchone()
    return int(row[0]) if row else None


def db_set_event_response(message_id: int, user_id: int, status: str) -> None:
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            "INSERT INTO event_responses(message_id, user_id, status, updated_at) VALUES(?, ?, ?, ?) "
            "ON CONFLICT(message_id, user_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at;",
            (message_id, user_id, status, int(time.time())),
        )


def db_get_event_responses(message_id: int) -> dict[int, str]:
    with sqlite3.connect(DB_PATH) as con:
        rows = con.execute(
            "SELECT user_id, status FROM event_responses WHERE message_id=?;",
            (message_id,),
        ).fetchall()
    return {int(uid): str(status) for uid, status in rows}


def db_count_status(message_id: int, status: str) -> int:
    with sqlite3.connect(DB_PATH) as con:
        row = con.execute(
            "SELECT COUNT(*) FROM event_responses WHERE message_id=? AND status=?;",
            (message_id, status),
        ).fetchone()
    return int(row[0]) if row else 0



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
    for rid in STAFF_PING_ROLE_IDS:
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




async def send_application_log(
    guild: discord.Guild,
    *,
    decision: str,
    opener: discord.abc.User | None,
    moderator: discord.Member,
    reason_text: str,
    dm_sent: bool,
) -> None:
    """Отправляет в лог-канал сообщение по шаблону + ставит реакцию."""
    if not LOG_CHANNEL_ID:
        return

    ch = guild.get_channel(LOG_CHANNEL_ID)
    if not isinstance(ch, discord.TextChannel):
        return

    player_part = opener.mention if opener else "*(не удалось определить игрока)*"
    mod_part = moderator.mention
    dm_part = "**YES**" if dm_sent else "**NO**"

    if decision == "accept":
        header = "**✅ Заявка была успешно принята.**"
        body = (
            f"{header}\n"
            f"*Был принят игрок:* {player_part}\n"
            f"*Заявка была принята модератором:* {mod_part}\n"
            f"*Заявка была принята с причиной:* **{reason_text}**\n\n"
            f"*Отправилось ли сообщение в dm игроку?*: {dm_part}"
        )
        reaction = "✅"
    else:
        header = "**❌ Заявка была успешно отклонена.**"
        body = (
            f"{header}\n"
            f"*Был отклонен игрок:* {player_part}\n"
            f"*Заявка была отклонена модератором:* {mod_part}\n"
            f"*Заявка была отклонена с причиной:* **{reason_text}**\n\n"
            f"*Отправилось ли сообщение в dm игроку?*: {dm_part}"
        )
        reaction = "❌"

    try:
        msg = await ch.send(
            body,
            allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False),
        )
    except discord.HTTPException:
        return

    try:
        await msg.add_reaction(reaction)
    except (discord.Forbidden, discord.HTTPException):
        pass


# ==========================================================
#                 PRIVATKA: NICKNAME SETUP
# ==========================================================

def _clean_one_line(value: str) -> str:
    value = value.replace("\n", " ").replace("\r", " ").strip()
    value = re.sub(r"\s+", " ", value)
    return value


def format_private_nickname(steam_nick: str, real_name: str, *, max_len: int = 32) -> str:
    # Формат: "SteamNick | RealName"
    # Discord ограничивает nick 32 символами — аккуратно режем, если нужно.
    steam_nick = _clean_one_line(steam_nick)
    real_name = _clean_one_line(real_name)

    sep = " | "
    full = f"{steam_nick}{sep}{real_name}"

    if len(full) <= max_len:
        return full

    # сначала подрежем steam_nick, сохранив real_name максимально
    available_for_steam = max_len - len(sep) - len(real_name)
    if available_for_steam < 1:
        # real_name слишком длинное — режем его, чтобы осталось место хотя бы на 1 символ steam
        real_name = real_name[: max(1, max_len - len(sep) - 1)]
        available_for_steam = 1

    steam_nick = steam_nick[:available_for_steam]
    full = f"{steam_nick}{sep}{real_name}"
    return full[:max_len]


class PrivateNicknameModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Приватка — установка ника")

        self.steam_nick = discord.ui.TextInput(
            label="Ваш ник в стиме",
            placeholder="Например: SH | Nick",
            style=discord.TextStyle.short,
            required=True,
            max_length=64,
        )
        self.real_name = discord.ui.TextInput(
            label="Ваше настоящее имя",
            placeholder="Например: Иван",
            style=discord.TextStyle.short,
            required=True,
            max_length=64,
        )
        self.add_item(self.steam_nick)
        self.add_item(self.real_name)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Ошибка: не удалось определить сервер/участника.", ephemeral=True)

        # строго работаем только в приватке
        if interaction.guild.id != PRIVATE_GUILD_ID:
            return await interaction.response.send_message("Эта форма работает только в приватке.", ephemeral=True)

        member: discord.Member = interaction.user
        new_nick = format_private_nickname(self.steam_nick.value, self.real_name.value)

        nick_ok = True
        roles_ok = True
        nick_err = ""
        roles_err = ""

        # 1) меняем ник
        try:
            await member.edit(nick=new_nick, reason="[SH] Privatka nickname setup")
        except discord.Forbidden:
            nick_ok = False
            nick_err = "Нет прав на изменение ника (Manage Nicknames) или роль бота ниже."
        except discord.HTTPException:
            nick_ok = False
            nick_err = "Не удалось изменить ник (ошибка Discord)."

        # 2) роли
        remove_role = interaction.guild.get_role(PRIVATE_REMOVE_ROLE_ID)
        add_role = interaction.guild.get_role(PRIVATE_ADD_ROLE_ID)
        try:
            if remove_role and remove_role in member.roles:
                await member.remove_roles(remove_role, reason="[SH] Privatka nickname setup: remove role")
            if add_role and add_role not in member.roles:
                await member.add_roles(add_role, reason="[SH] Privatka nickname setup: add role")
        except discord.Forbidden:
            roles_ok = False
            roles_err = "Нет прав на выдачу ролей (Manage Roles) или роли выше роли бота."
        except discord.HTTPException:
            roles_ok = False
            roles_err = "Не удалось обновить роли (ошибка Discord)."

        # ответ пользователю
        lines = []
        if nick_ok:
            lines.append(f"✅ Ник установлен: **{new_nick}**")
        else:
            lines.append(f"❌ Ник не изменён. {nick_err}")

        if roles_ok:
            lines.append("✅ Роли обновлены.")
        else:
            lines.append(f"❌ Роли не обновлены. {roles_err}")

        await interaction.response.send_message("\n".join(lines), ephemeral=True)


class PrivateSetupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Заполнить форму",
        style=discord.ButtonStyle.primary,
        custom_id="sh_private_open_form",
    )
    async def open_form(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or interaction.guild.id != PRIVATE_GUILD_ID:
            return await interaction.response.send_message("Эта кнопка работает только в приватке.", ephemeral=True)

        await interaction.response.send_modal(PrivateNicknameModal())


async def ensure_private_setup_message() -> None:
    # Создаёт (один раз) сообщение с кнопкой в канале приватки.
    try:
        ch = client.get_channel(PRIVATE_SETUP_CHANNEL_ID) or await client.fetch_channel(PRIVATE_SETUP_CHANNEL_ID)
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        return

    if not isinstance(ch, discord.TextChannel):
        return

    if ch.guild.id != PRIVATE_GUILD_ID:
        return

    stored_id = db_get_private_setup_message(PRIVATE_SETUP_CHANNEL_ID)
    if stored_id:
        try:
            old = await ch.fetch_message(stored_id)
            if client.user and old.author and old.author.id == client.user.id:
                return  # уже есть
        except (discord.NotFound, discord.HTTPException):
            pass

    try:
        msg = await ch.send(
            PRIVATE_SETUP_MESSAGE,
            view=PrivateSetupView(),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        db_set_private_setup_message(PRIVATE_SETUP_CHANNEL_ID, msg.id)
    except discord.HTTPException:
        return
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

async def ensure_guild_member(guild: discord.Guild, user_id: int) -> discord.Member | None:
    """
    Возвращает Member для user_id.
    1) пробуем из кеша
    2) если нет — делаем REST fetch (работает даже без intents.members)
    """
    m = guild.get_member(user_id)
    if m:
        return m
    try:
        return await guild.fetch_member(user_id)
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return None


async def apply_accept_roles(
    guild: discord.Guild,
    opener_id: int,
    *,
    add_role_id: int,
    remove_role_id: int,
) -> tuple[bool, str]:
    """
    При принятии:
    - выдаём роль add_role_id
    - снимаем роль remove_role_id
    """
    member = await ensure_guild_member(guild, opener_id)
    if not member:
        return False, "member_not_found"

    add_role = guild.get_role(add_role_id)
    rem_role = guild.get_role(remove_role_id)

    if add_role is None and rem_role is None:
        return False, "roles_not_found"

    try:
        if rem_role and rem_role in member.roles:
            await member.remove_roles(rem_role, reason="[SH] Ticket accepted: remove role")
        if add_role and add_role not in member.roles:
            await member.add_roles(add_role, reason="[SH] Ticket accepted: add role")
        return True, "ok"
    except discord.Forbidden:
        # Обычно: у бота нет Manage Roles или роль выше роли бота
        return False, "forbidden_manage_roles_or_hierarchy"
    except discord.HTTPException:
        return False, "http_exception"


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

    overwrites: dict[discord.abc.Snowflake, discord.PermissionOverwrite] = {}

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
    for rid in STAFF_PING_ROLE_IDS:
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
#                 EVENT REGISTRATION (WIPE RSVP)
# ==========================================================

_event_close_tasks: dict[int, asyncio.Task] = {}
_guild_event_locks: dict[int, asyncio.Lock] = {}


def _get_guild_event_lock(guild_id: int) -> asyncio.Lock:
    lock = _guild_event_locks.get(guild_id)
    if lock is None:
        lock = asyncio.Lock()
        _guild_event_locks[guild_id] = lock
    return lock


def can_manage_events(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    return any(r.id in EVENT_ALLOWED_ROLE_IDS for r in member.roles)


async def _dm_ask(member: discord.Member, prompt: str) -> str | None:
    """Возвращает текст ответа или None (cancel/timeout)."""
    try:
        dm = member.dm_channel or await member.create_dm()
        await dm.send(prompt)
    except (discord.Forbidden, discord.HTTPException):
        return None

    def check(m: discord.Message) -> bool:
        return (
            m.author.id == member.id
            and isinstance(m.channel, discord.DMChannel)
        )

    try:
        msg = await client.wait_for("message", check=check, timeout=EVENT_DM_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        try:
            await dm.send("⏳ Время ожидания истекло. Создание события отменено.")
        except discord.HTTPException:
            pass
        return None

    content = (msg.content or "").strip()
    if content.lower() == "cancel":
        try:
            await dm.send("❎ Создание события отменено.")
        except discord.HTTPException:
            pass
        return None

    return content


def _parse_msk_datetime(value: str) -> datetime | None:
    value = value.strip()
    # ожидаем: YYYY-MM-DD HH:MM
    try:
        dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
        return dt.replace(tzinfo=MSK_TZ)
    except ValueError:
        return None


def _short_list(lines: list[str], *, max_chars: int = 900) -> str:
    """Форматирует список под Apollo-стиль (вертикальная линия + переносы) и режет по лимиту."""
    if not lines:
        return "-"
    out: list[str] = []
    total = 0
    for line in lines:
        row = f"│ {line}"
        if total + len(row) + 1 > max_chars:
            remaining = len(lines) - len(out)
            out.append(f"… и ещё {remaining} чел.")
            break
        out.append(row)
        total += len(row) + 1
    return "\n".join(out)


def _google_calendar_link(title: str, start_at: int, end_at: int, description: str) -> str:
    """Формирует ссылку Add to Google Calendar (template). Время в UTC."""
    def fmt(ts: int) -> str:
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    start_s = fmt(start_at)
    end_s = fmt(end_at)
    details = (description if description and description != "None" else "")
    # Простая URL-энкодинговая замена без urllib (чтобы не тащить лишнее)
    def enc(s: str) -> str:
        return (
            s.replace("%", "%25")
             .replace(" ", "%20")
             .replace("\n", "%0A")
             .replace("|", "%7C")
             .replace("#", "%23")
             .replace("&", "%26")
             .replace("?", "%3F")
        )

    return (
        "https://calendar.google.com/calendar/render?action=TEMPLATE"
        f"&text={enc(title)}"
        f"&dates={start_s}%2F{end_s}"
        f"&details={enc(details)}"
    )


def build_event_embed(
    *,
    guild: discord.Guild,
    title: str,
    description: str,
    start_at: int,
    end_at: int,
    max_participants: int | None,
    responses: dict[int, str],
    created_by: int,
) -> discord.Embed:
    """Визуал максимально близкий к Apollo: шапка, Time, 3 колонки, Created by, картинка."""

    # Собираем участников по статусам
    by_status: dict[str, list[str]] = {"accepted": [], "tentative": [], "declined": []}
    for uid, status in responses.items():
        m = guild.get_member(uid)
        display = m.display_name if m else f"<@{uid}>"
        if status in by_status:
            by_status[status].append(display)

    # Стабильная сортировка
    for k in by_status:
        by_status[k].sort(key=lambda s: s.lower())

    acc = len(by_status["accepted"])
    ten = len(by_status["tentative"])
    dec = len(by_status["declined"])

    max_part = f"/{max_participants}" if isinstance(max_participants, int) else ""

    # Цвет/стиль как у Apollo (жёлтая полоса)
    embed = discord.Embed(
        title=title,
        description=(description if description and description != "None" else None),
        color=0xF1C40F,
    )

    # Author как “бренд” (как Apollo: сверху слева)
    brand_name = EVENT_BRAND_NAME or "Event"
    icon_url = EVENT_BRAND_ICON_URL.strip() if isinstance(EVENT_BRAND_ICON_URL, str) else ""
    if not icon_url:
        if guild.icon:
            icon_url = guild.icon.url
        elif client.user and client.user.avatar:
            icon_url = client.user.avatar.url
    try:
        embed.set_author(name=brand_name, icon_url=icon_url)
    except Exception:
        embed.set_author(name=brand_name)

    # Time-блок (максимально похожий)
    time_lines = [
        f"**Конец регистрации:** <t:{end_at}:F>",
        f"**Через:** <t:{end_at}:R>",
    ]
    if EVENT_SHOW_ADD_TO_GOOGLE:
        # В Apollo это “Add to Google” — даём рабочую ссылку в календарь
        url = _google_calendar_link(title, start_at, end_at, description or "")
        time_lines[-1] = time_lines[-1] + f"  •  [Add to Google]({url})"

    embed.add_field(
        name="Time",
        value="\n".join(time_lines),
        inline=False,
    )

    embed.add_field(
        name=f"✅ Accepted ({acc}{max_part})",
        value=_short_list(by_status["accepted"]),
        inline=True,
    )
    embed.add_field(
        name=f"❌ Declined ({dec})",
        value=_short_list(by_status["declined"]),
        inline=True,
    )
    embed.add_field(
        name=f"❓ Tentative ({ten})",
        value=_short_list(by_status["tentative"]),
        inline=True,
    )

    creator = guild.get_member(created_by)
    creator_text = creator.display_name if creator else f"ID {created_by}"
    embed.set_footer(text=f"Created by {creator_text}")

    # Картинка как в Apollo (низ карточки)
    if EVENT_IMAGE_URL:
        embed.set_image(url=EVENT_IMAGE_URL)

    return embed



async def _apply_event_roles(member: discord.Member, status: str) -> tuple[bool, str]:
    """Ставит роли по статусу: снимает ожидание и остальные, выдаёт нужную."""
    guild = member.guild
    role_wait = guild.get_role(EVENT_ROLE_WAITING_ID)
    role_acc = guild.get_role(EVENT_ROLE_ACCEPTED_ID)
    role_ten = guild.get_role(EVENT_ROLE_TENTATIVE_ID)
    role_dec = guild.get_role(EVENT_ROLE_DECLINED_ID)

    target = {"accepted": role_acc, "tentative": role_ten, "declined": role_dec}.get(status)

    to_remove = [r for r in (role_wait, role_acc, role_ten, role_dec) if r and r in member.roles]
    try:
        if to_remove:
            await member.remove_roles(*to_remove, reason="[SH] RSVP update")
        if target and target not in member.roles:
            await member.add_roles(target, reason="[SH] RSVP update")
        return True, "ok"
    except discord.Forbidden:
        return False, "forbidden_manage_roles_or_hierarchy"
    except discord.HTTPException:
        return False, "http_exception"


async def _assign_waiting_role_to_all(guild: discord.Guild) -> None:
    role_wait = guild.get_role(EVENT_ROLE_WAITING_ID)
    if not role_wait:
        return

    # Важно: для больших серверов это может занять время
    try:
        # chunk, чтобы guild.members был полным
        await guild.chunk()
    except Exception:
        pass

    count = 0
    for m in list(guild.members):
        if m.bot:
            continue
        if role_wait in m.roles:
            continue
        try:
            await m.add_roles(role_wait, reason="[SH] RSVP start: set waiting role")
            count += 1
        except (discord.Forbidden, discord.HTTPException):
            pass

        # небольшая разгрузка по rate-limit
        if count % 20 == 0:
            await asyncio.sleep(1.0)


async def _remove_event_roles_from_all(guild: discord.Guild) -> None:
    role_wait = guild.get_role(EVENT_ROLE_WAITING_ID)
    role_acc = guild.get_role(EVENT_ROLE_ACCEPTED_ID)
    role_ten = guild.get_role(EVENT_ROLE_TENTATIVE_ID)
    role_dec = guild.get_role(EVENT_ROLE_DECLINED_ID)

    roles = [r for r in (role_wait, role_acc, role_ten, role_dec) if r]
    if not roles:
        return

    try:
        await guild.chunk()
    except Exception:
        pass

    count = 0
    for m in list(guild.members):
        if m.bot:
            continue
        owned = [r for r in roles if r in m.roles]
        if not owned:
            continue
        try:
            await m.remove_roles(*owned, reason="[SH] RSVP end: cleanup roles")
            count += 1
        except (discord.Forbidden, discord.HTTPException):
            pass

        if count % 20 == 0:
            await asyncio.sleep(1.0)


async def refresh_event_message(message: discord.Message) -> None:
    if not message.guild:
        return

    event = db_get_event(message.id)
    if not event:
        return

    responses = db_get_event_responses(message.id)
    embed = build_event_embed(
        guild=message.guild,
        title=event["title"],
        description=event["description"],
        start_at=event["start_at"],
        end_at=event["end_at"],
        max_participants=event["max_participants"],
        responses=responses,
        created_by=event["created_by"],
    )
    try:
        await message.edit(embed=embed, view=EventRSVPView(), allowed_mentions=discord.AllowedMentions.none())
    except discord.HTTPException:
        pass


async def close_event_by_message_id(message_id: int) -> None:
    event = db_get_event(message_id)
    if not event:
        return

    guild = client.get_guild(event["guild_id"])
    if guild is None:
        # нет в кеше — не можем чистить роли надёжно
        db_delete_event(message_id)
        return

    # удалить сообщение события
    try:
        ch = guild.get_channel(event["channel_id"]) or await client.fetch_channel(event["channel_id"])
    except (discord.Forbidden, discord.NotFound, discord.HTTPException):
        ch = None

    if isinstance(ch, discord.TextChannel):
        try:
            msg = await ch.fetch_message(message_id)
            try:
                await msg.delete(reason="[SH] RSVP end: auto-delete event")
            except (discord.Forbidden, discord.HTTPException):
                pass
        except (discord.NotFound, discord.HTTPException):
            pass

    # убрать роли явки у всех
    await _remove_event_roles_from_all(guild)

    # очистить БД
    db_delete_event(message_id)

    # снять задачу
    task = _event_close_tasks.pop(message_id, None)
    if task and not task.done():
        task.cancel()


def schedule_event_close(message_id: int, end_at: int) -> None:
    # уже есть
    if message_id in _event_close_tasks:
        return

    async def runner():
        # sleep до конца
        delay = max(0, end_at - int(time.time()))
        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            return
        await close_event_by_message_id(message_id)

    _event_close_tasks[message_id] = asyncio.create_task(runner())


async def load_and_schedule_active_events() -> None:
    now_ts = int(time.time())
    for ev in db_list_active_events(now_ts):
        schedule_event_close(ev["message_id"], ev["end_at"])


def reschedule_event_close(message_id: int, end_at: int) -> None:
    """Перезапускает таймер закрытия события (при edit)."""
    old = _event_close_tasks.pop(message_id, None)
    if old and not old.done():
        old.cancel()
    schedule_event_close(message_id, end_at)


class ConfirmDeleteEventView(discord.ui.View):
    def __init__(self, message_id: int):
        super().__init__(timeout=60)
        self.message_id = message_id

    @discord.ui.button(label="Подтвердить удаление", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Удаляю событие и очищаю роли…", ephemeral=True)
        await close_event_by_message_id(self.message_id)

    @discord.ui.button(label="Отмена", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ок, не удаляю.", ephemeral=True)


class EventEditModal(discord.ui.Modal):
    def __init__(self, message_id: int):
        super().__init__(title="Edit event")
        self.message_id = message_id

        self.title_in = discord.ui.TextInput(
            label="Заголовок (пусто = оставить)",
            style=discord.TextStyle.short,
            required=False,
            max_length=200,
        )
        self.desc_in = discord.ui.TextInput(
            label="Описание (пусто = оставить, None = очистить)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1600,
        )
        self.max_in = discord.ui.TextInput(
            label="Макс. участников (пусто = оставить, None = без лимита)",
            style=discord.TextStyle.short,
            required=False,
            max_length=10,
        )
        self.end_in = discord.ui.TextInput(
            label="Конец регистрации (YYYY-MM-DD HH:MM, МСК)",
            style=discord.TextStyle.short,
            required=False,
            placeholder="2025-06-25 19:00",
            max_length=16,
        )

        self.add_item(self.title_in)
        self.add_item(self.desc_in)
        self.add_item(self.max_in)
        self.add_item(self.end_in)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not interaction.message:
            return await interaction.response.send_message("Ошибка: нет гильдии/сообщения.", ephemeral=True)

        ev = db_get_event(self.message_id)
        if not ev:
            return await interaction.response.send_message("Событие уже не активно.", ephemeral=True)

        # права: организатор или роль-менеджер
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Ошибка: нет участника.", ephemeral=True)
        if interaction.user.id != ev["created_by"] and not can_manage_events(interaction.user):
            return await interaction.response.send_message("Недостаточно прав для редактирования.", ephemeral=True)

        title = ev["title"]
        desc = ev["description"]
        max_part = ev["max_participants"]
        end_at = ev["end_at"]

        t = (self.title_in.value or "").strip()
        if t:
            title = t[:200]

        d = (self.desc_in.value or "").strip()
        if d:
            desc = d[:1600]
        elif (self.desc_in.value or "").strip().lower() == "none":
            desc = "None"

        mx_raw = (self.max_in.value or "").strip()
        if mx_raw:
            if mx_raw.lower() == "none":
                max_part = None
            else:
                try:
                    mx = int(mx_raw)
                    if mx < 1 or mx > 250:
                        raise ValueError
                    max_part = mx
                except ValueError:
                    return await interaction.response.send_message("❌ Некорректный лимит участников.", ephemeral=True)

        end_raw = (self.end_in.value or "").strip()
        if end_raw:
            dt_end = _parse_msk_datetime(end_raw)
            if not dt_end:
                return await interaction.response.send_message("❌ Неверный формат даты конца регистрации.", ephemeral=True)
            new_end_at = int(dt_end.timestamp())
            if new_end_at <= int(time.time()) + 30:
                return await interaction.response.send_message("❌ Конец регистрации должен быть в будущем.", ephemeral=True)
            end_at = new_end_at

        # обновляем БД
        db_insert_event(
            message_id=self.message_id,
            guild_id=ev["guild_id"],
            channel_id=ev["channel_id"],
            created_by=ev["created_by"],
            title=title,
            description=desc,
            max_participants=max_part,
            start_at=ev["start_at"],
            end_at=end_at,
        )

        # пересобираем embed + view
        responses = db_get_event_responses(self.message_id)
        embed = build_event_embed(
            guild=interaction.guild,
            title=title,
            description=desc,
            start_at=ev["start_at"],
            end_at=end_at,
            max_participants=max_part,
            responses=responses,
            created_by=ev["created_by"],
        )
        try:
            await interaction.message.edit(embed=embed, view=EventRSVPView(), allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            pass

        # перескейджулим закрытие
        reschedule_event_close(self.message_id, end_at)

        await interaction.response.send_message("✅ Событие обновлено.", ephemeral=True)


class EventRSVPView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="✅", style=discord.ButtonStyle.success, custom_id="sh_event_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle(interaction, "accepted")

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.danger, custom_id="sh_event_decline")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle(interaction, "declined")

    @discord.ui.button(emoji="❓", style=discord.ButtonStyle.primary, custom_id="sh_event_tentative")
    async def tentative(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._handle(interaction, "tentative")

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.secondary, custom_id="sh_event_edit")
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not interaction.message:
            return await interaction.response.send_message("Ошибка: нет события.", ephemeral=True)

        ev = db_get_event(interaction.message.id)
        if not ev:
            return await interaction.response.send_message("Это событие уже не активно.", ephemeral=True)

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Ошибка: нет участника.", ephemeral=True)
        if interaction.user.id != ev["created_by"] and not can_manage_events(interaction.user):
            return await interaction.response.send_message("Недостаточно прав для редактирования.", ephemeral=True)

        await interaction.response.send_modal(EventEditModal(interaction.message.id))

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger, custom_id="sh_event_delete")
    async def delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.guild or not interaction.message:
            return await interaction.response.send_message("Ошибка: нет события.", ephemeral=True)

        ev = db_get_event(interaction.message.id)
        if not ev:
            return await interaction.response.send_message("Это событие уже не активно.", ephemeral=True)

        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Ошибка: нет участника.", ephemeral=True)
        if interaction.user.id != ev["created_by"] and not can_manage_events(interaction.user):
            return await interaction.response.send_message("Недостаточно прав для удаления.", ephemeral=True)

        await interaction.response.send_message(
            "Подтверди удаление события. Оно будет удалено, а роли явки очищены у всех участников.",
            ephemeral=True,
            view=ConfirmDeleteEventView(interaction.message.id),
        )

    async def _handle(self, interaction: discord.Interaction, status: str) -> None:
        if not interaction.guild or not interaction.message:
            return await interaction.response.send_message("Ошибка: не удалось определить событие.", ephemeral=True)
        if not isinstance(interaction.user, discord.Member):
            return await interaction.response.send_message("Ошибка: не удалось определить участника.", ephemeral=True)

        event = db_get_event(interaction.message.id)
        if not event:
            return await interaction.response.send_message("Это событие уже не активно.", ephemeral=True)

        # Проверка лимита мест на accepted
        if status == "accepted" and isinstance(event["max_participants"], int):
            current = db_count_status(interaction.message.id, "accepted")
            existing = db_get_event_responses(interaction.message.id).get(interaction.user.id)
            if existing != "accepted" and current >= event["max_participants"]:
                return await interaction.response.send_message(
                    f"Мест нет: лимит **{event['max_participants']}** уже заполнен.",
                    ephemeral=True,
                )

        # Записать в БД
        db_set_event_response(interaction.message.id, interaction.user.id, status)

        # Роли
        ok, code = await _apply_event_roles(interaction.user, status)
        if not ok:
            await interaction.response.send_message(
                f"Отметка сохранена, но роли не обновились (**{code}**). Проверь права бота (Manage Roles) и иерархию ролей.",
                ephemeral=True,
            )
        else:
            await interaction.response.send_message("✅ Отметка сохранена.", ephemeral=True)

        # Обновить embed
        try:
            await refresh_event_message(interaction.message)
        except Exception:
            pass


# -------------------- SLASH COMMANDS --------------------

@tree.command(
    name="kanal",
    description="Привязать канал, куда бот будет публиковать события регистрации",
)
@app_commands.describe(channel="Канал для событий")
async def cmd_set_channel(interaction: discord.Interaction, channel: discord.TextChannel):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return await interaction.response.send_message("Ошибка: команда доступна только на сервере.", ephemeral=True)

    if not can_manage_events(interaction.user):
        return await interaction.response.send_message("Недостаточно прав для этой команды.", ephemeral=True)

    db_set_event_channel(interaction.guild.id, channel.id)
    await interaction.response.send_message(f"Канал для событий установлен: {channel.mention}", ephemeral=True)


@tree.command(
    name="sobytie",
    description="Создать событие регистрации (все шаги придут в ЛС)",
)
async def cmd_create_event(interaction: discord.Interaction):
    if not interaction.guild or not isinstance(interaction.user, discord.Member):
        return await interaction.response.send_message("Ошибка: команда доступна только на сервере.", ephemeral=True)

    if not can_manage_events(interaction.user):
        return await interaction.response.send_message("Недостаточно прав для этой команды.", ephemeral=True)

    # только один активный ивент на гильдию (потому что роли глобальные)
    now_ts = int(time.time())
    active = db_get_active_event_for_guild(interaction.guild.id, now_ts)
    if active:
        return await interaction.response.send_message(
            "Уже есть активное событие. Дождитесь окончания или удалите его.",
            ephemeral=True,
        )

    ch_id = db_get_event_channel(interaction.guild.id)
    if not ch_id:
        return await interaction.response.send_message("Сначала укажи канал командой /канал.", ephemeral=True)

    await interaction.response.send_message(
        "Последующие шаги я отправил вам в личные сообщения.",
        ephemeral=True,
    )

    lock = _get_guild_event_lock(interaction.guild.id)
    async with lock:
        # проверим снова (пока ждали lock)
        active2 = db_get_active_event_for_guild(interaction.guild.id, int(time.time()))
        if active2:
            return

        creator = interaction.user
        # 1) title
        title = await _dm_ask(
            creator,
            "Введите заголовок события\n"
            "Разрешено до 200 символов\n"
            "Чтобы выйти, введите 'cancel'",
        )
        if title is None:
            return
        title = title[:200]

        # 2) description
        desc = await _dm_ask(
            creator,
            "Введите описание события\n"
            "Введите None, если не хотите чтобы было описание. До 1600 символов разрешено.\n"
            "Чтобы выйти, введите 'cancel'",
        )
        if desc is None:
            return
        desc = desc[:1600]

        # 3) max participants
        max_raw = await _dm_ask(
            creator,
            "Введите максимальное число участников\n"
            "Введите None без ограничений. Разрешено до 250 участников.\n"
            "Чтобы выйти, введите 'cancel'",
        )
        if max_raw is None:
            return

        max_part: int | None
        if max_raw.strip().lower() == "none":
            max_part = None
        else:
            try:
                max_part = int(max_raw.strip())
                if max_part < 1 or max_part > 250:
                    raise ValueError
            except ValueError:
                try:
                    dm = creator.dm_channel or await creator.create_dm()
                    await dm.send("❌ Некорректное число. Создание события отменено.")
                except discord.HTTPException:
                    pass
                return

        # 4) start = now (публикуем сразу)
        start_at = int(time.time())

        # 5) end at (конец регистрации)
        end_raw = await _dm_ask(
            creator,
            "Когда событие должно завершиться (конец регистрации)?\n"
            "Формат: YYYY-MM-DD HH:MM (МСК)\n"
            "Пример: 2025-06-25 19:00\n"
            "Чтобы выйти, введите 'cancel'",
        )
        if end_raw is None:
            return

        dt_end = _parse_msk_datetime(end_raw)
        if dt_end is None:
            try:
                dm = creator.dm_channel or await creator.create_dm()
                await dm.send("❌ Неверный формат даты/времени. Создание события отменено.")
            except discord.HTTPException:
                pass
            return

        end_at = int(dt_end.timestamp())
        if end_at <= start_at + 30:
            try:
                dm = creator.dm_channel or await creator.create_dm()
                await dm.send("❌ Конец регистрации должен быть позже текущего времени. Создание события отменено.")
            except discord.HTTPException:
                pass
            return

        # отправляем сообщение в канал
        try:
            ch = interaction.guild.get_channel(ch_id) or await client.fetch_channel(ch_id)
        except (discord.Forbidden, discord.NotFound, discord.HTTPException):
            try:
                dm = creator.dm_channel or await creator.create_dm()
                await dm.send("❌ Не удалось открыть выбранный канал. Проверь доступ бота.")
            except discord.HTTPException:
                pass
            return

        if not isinstance(ch, discord.TextChannel):
            try:
                dm = creator.dm_channel or await creator.create_dm()
                await dm.send("❌ Выбранный канал не является текстовым.")
            except discord.HTTPException:
                pass
            return

        # пока нет ответов
        responses: dict[int, str] = {}
        embed = build_event_embed(
            guild=interaction.guild,
            title=title,
            description=desc,
            start_at=start_at,
            end_at=end_at,
            max_participants=max_part,
            responses=responses,
            created_by=creator.id,
        )

        try:
            msg = await ch.send(
                content="@everyone",
                embed=embed,
                view=EventRSVPView(),
                allowed_mentions=discord.AllowedMentions(everyone=True, users=False, roles=False, replied_user=False),
            )
        except discord.HTTPException:
            try:
                dm = creator.dm_channel or await creator.create_dm()
                await dm.send("❌ Не удалось отправить сообщение события в канал.")
            except discord.HTTPException:
                pass
            return

        # записать событие
        db_insert_event(
            message_id=msg.id,
            guild_id=interaction.guild.id,
            channel_id=ch.id,
            created_by=creator.id,
            title=title,
            description=desc,
            max_participants=max_part,
            start_at=start_at,
            end_at=end_at,
        )

        schedule_event_close(msg.id, end_at)

        # выдаём роль ожидания всем (фоном)
        asyncio.create_task(_assign_waiting_role_to_all(interaction.guild))

        try:
            dm = creator.dm_channel or await creator.create_dm()
            await dm.send("✅ Событие создано и опубликовано в канале.")
        except discord.HTTPException:
            pass


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
                "**Причина принята.** *Уведомляю пользователя, обновляю роли (если принят) и удаляю тикет…*",
                ephemeral=True,
            )

            # DM
            dm_ok = True
            extra_dm_ok = True
            if opener is None:
                dm_ok = False
                extra_dm_ok = False
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

                # Дополнительное сообщение при принятии
                if self.decision == "accept":
                    try:
                        await opener.send(ACCEPT_EXTRA_DM, allowed_mentions=discord.AllowedMentions.none())
                    except (discord.Forbidden, discord.HTTPException):
                        extra_dm_ok = False

            # Роли — только при принятии
            roles_status = "SKIP"
            if self.decision == "accept" and opener is not None:
                ok, code = await apply_accept_roles(
                    interaction.guild,
                    opener.id,
                    add_role_id=ACCEPT_ADD_ROLE_ID,
                    remove_role_id=ACCEPT_REMOVE_ROLE_ID,
                )
                roles_status = "OK" if ok else f"FAIL:{code}"

            # Убираем сообщение с кнопками (на случай если удаление канала не получится)
            await disable_or_delete_prompt_message(channel)

            player_text = f"{opener} ({opener.id})" if opener else "не найден"
            dm_status = "OK" if dm_ok else "FAIL"
            extra_dm_status = "OK" if extra_dm_ok else "FAIL"

            # Логи по шаблону (до удаления канала)
            await send_application_log(
                interaction.guild,
                decision=self.decision,
                opener=opener,
                moderator=moderator,
                reason_text=self.reason.value,
                dm_sent=dm_ok,
            )

            # чистим БД + in-memory кэш
            db_delete_ticket(channel.id)
            db_delete_prompt(channel.id)
            _last_prompt_time.pop(channel.id, None)

            # Сообщение модератору (ephemeral) перед удалением канала
            decision_ru = "принято ✅" if self.decision == "accept" else "отклонено ❌"
            summary = (
                f"Готово: **{decision_ru}**\n"
                f"Игрок: **{player_text}**\n"
                f"DM: **{dm_status}**"
            )
            if self.decision == "accept":
                summary += f"\nДоп. DM: **{extra_dm_status}**\nРоли: **{roles_status}**"

            try:
                await interaction.followup.send(summary, ephemeral=True)
            except discord.HTTPException:
                pass

            # Удаляем тикет-канал
            try:
                await channel.delete(
                    reason=(
                        f"[SH] decision={self.decision} by {moderator} ({moderator.id}). "
                        f"Player: {player_text}. Text: {self.reason.value[:200]}"
                    )
                )
            except (discord.Forbidden, discord.HTTPException) as e:
                # Если удалить не получилось — как запасной план переносим в архив и закрываем права
                try:
                    await archive_and_lock_channel(channel, opener, moderator, self.reason.value)
                except Exception:
                    pass
                await log_event(
                    interaction.guild,
                    f"[SH] WARNING: failed to delete channel={channel.id}. error={type(e).__name__}: {e}"
                )

            _channel_locks.pop(channel.id, None)



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

    # persistent views (работают после рестарта)
    client.add_view(TicketDecisionView())
    client.add_view(PrivateSetupView())

    # сообщение с кнопкой в приватке (если бот там есть и имеет доступ)
    await ensure_private_setup_message()

    # persistent view для событий регистрации
    client.add_view(EventRSVPView())

    # планируем закрытие активных событий из БД
    await load_and_schedule_active_events()

    # синк slash-команд (быстро в конкретную гильдию)
    try:
        if COMMANDS_SYNC_GUILD_ID:
            await tree.sync(guild=discord.Object(id=COMMANDS_SYNC_GUILD_ID))
        else:
            await tree.sync()
    except Exception as e:
        print(f"[WARN] Command sync failed: {e}")



@client.event
async def on_member_join(member: discord.Member):
    # Если сейчас активно событие регистрации — выдаём роль ожидания новому участнику
    try:
        active = db_get_active_event_for_guild(member.guild.id, int(time.time()))
    except Exception:
        active = None
    if not active:
        return

    role_wait = member.guild.get_role(EVENT_ROLE_WAITING_ID)
    if not role_wait:
        return

    # Не трогаем ботов
    if member.bot:
        return

    # Если уже есть одна из ролей явки — не выдаём ожидание
    if any(r.id in {EVENT_ROLE_ACCEPTED_ID, EVENT_ROLE_TENTATIVE_ID, EVENT_ROLE_DECLINED_ID} for r in member.roles):
        return

    try:
        await member.add_roles(role_wait, reason="[SH] RSVP active: new member waiting role")
    except (discord.Forbidden, discord.HTTPException):
        pass


@client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent):
    # Если вручную удалили сообщение события — чистим роли и БД
    try:
        event = db_get_event(payload.message_id)
    except Exception:
        event = None
    if event:
        await close_event_by_message_id(payload.message_id)

@client.event
async def on_guild_channel_create(channel):
    if isinstance(channel, discord.TextChannel) and channel.category_id == TICKETS_CATEGORY_ID:
        await asyncio.sleep(1)
        try:
            msg = await channel.send(WELCOME_MESSAGE)
            # Автозакреп (нужны права Manage Messages)
            try:
                await msg.pin(reason="[SH] Auto-pin application template")
            except (discord.Forbidden, discord.HTTPException):
                pass
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

    # защита от подделки: игрок не должен запускать кнопки обычным сообщением
    # (разрешаем ботов и вебхуки)
    if not message.author.bot and message.webhook_id is None:
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

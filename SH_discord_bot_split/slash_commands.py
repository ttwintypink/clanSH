# slash_commands.py
import re
import discord
from discord import app_commands

from app import tree
from config import IGNORE_ADD_ADMIN_ID, IGNORED_TICKET_OPENER_IDS
from db import db_add_ignored_user, db_is_ignored_user, db_remove_ignored_user, db_list_ignored_users


_ID_RE = re.compile(r"<@!?([0-9]{15,25})>|\b([0-9]{15,25})\b")


def _parse_user_id(raw: str) -> int | None:
    if not raw:
        return None
    m = _ID_RE.search(raw.strip())
    if not m:
        return None
    s = m.group(1) or m.group(2)
    try:
        return int(s)
    except Exception:
        return None


def _is_admin(interaction: discord.Interaction) -> bool:
    return interaction.user is not None and interaction.user.id == IGNORE_ADD_ADMIN_ID


async def _resolve_display_name(interaction: discord.Interaction, user_id: int) -> str:
    """Пытаемся получить display name в текущей гильдии, иначе — имя аккаунта."""
    if interaction.guild:
        m = interaction.guild.get_member(user_id)
        if m:
            return m.display_name
        try:
            m2 = await interaction.guild.fetch_member(user_id)
            return m2.display_name
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            pass
    try:
        u = await interaction.client.fetch_user(user_id)
        # global_name может быть None
        return u.global_name or u.name
    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
        return "(unknown)"


class ConfirmAddView(discord.ui.View):
    def __init__(self, *, requester_id: int, target_user_id: int, timeout: float = 30.0):
        super().__init__(timeout=timeout)
        self.requester_id = requester_id
        self.target_user_id = target_user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user and interaction.user.id == self.requester_id:
            return True
        try:
            await interaction.response.send_message("⛔ Эта кнопка не для вас.", ephemeral=True)
        except discord.HTTPException:
            pass
        return False

    @discord.ui.button(label="Yes", style=discord.ButtonStyle.success)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        db_add_ignored_user(self.target_user_id, self.requester_id)
        for item in self.children:
            item.disabled = True
        try:
            await interaction.response.edit_message(
                content=f"✅ Добавлено в списки исключения: {self.target_user_id}",
                view=self,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            pass

    @discord.ui.button(label="No", style=discord.ButtonStyle.secondary)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        for item in self.children:
            item.disabled = True
        try:
            await interaction.response.edit_message(
                content="❌ Запрос отменён.",
                view=self,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            pass


@tree.command(name="add", description="Добавить пользователя в список исключения")
@app_commands.guild_only()
@app_commands.describe(user_id="ID пользователя или @упоминание")
async def add_cmd(interaction: discord.Interaction, user_id: str):
    if not _is_admin(interaction):
        await interaction.response.send_message("⛔ Нет доступа.", ephemeral=True)
        return

    uid = _parse_user_id(user_id)
    if uid is None:
        await interaction.response.send_message("❌ Неверный ID. Пример: 1166060811672883210", ephemeral=True)
        return

    # Уже в исключениях?
    if uid in IGNORED_TICKET_OPENER_IDS or db_is_ignored_user(uid):
        await interaction.response.send_message(f"ℹ️ {uid} уже находится в списках исключения.", ephemeral=True)
        return

    db_add_ignored_user(uid, interaction.user.id)
    await interaction.response.send_message(f"✅ Добавлено в списки исключения: {uid}", ephemeral=True)


@tree.command(name="del", description="Убрать пользователя из списка исключения")
@app_commands.guild_only()
@app_commands.describe(user_id="ID пользователя или @упоминание")
async def del_cmd(interaction: discord.Interaction, user_id: str):
    if not _is_admin(interaction):
        await interaction.response.send_message("⛔ Нет доступа.", ephemeral=True)
        return

    uid = _parse_user_id(user_id)
    if uid is None:
        await interaction.response.send_message("❌ Неверный ID. Пример: 1166060811672883210", ephemeral=True)
        return

    # Если ID в статическом списке — не удаляем через команду
    if uid in IGNORED_TICKET_OPENER_IDS:
        await interaction.response.send_message(
            f"⚠️ {uid} находится в базовом списке исключений (в коде) и не удаляется через /del.",
            ephemeral=True,
        )
        return

    removed = db_remove_ignored_user(uid)
    if removed:
        await interaction.response.send_message(f"✅ Удалено из списков исключения: {uid}", ephemeral=True)
        return

    # Не найден: для IGNORE_ADD_ADMIN_ID показываем подтверждение добавления
    view = ConfirmAddView(requester_id=interaction.user.id, target_user_id=uid)
    await interaction.response.send_message(
        "Данный пользователь не находится в списках исключения. Добавить?",
        view=view,
        ephemeral=True,
        allowed_mentions=discord.AllowedMentions.none(),
    )


@tree.command(name="menu", description="Показать список пользователей в исключении")
@app_commands.guild_only()
async def menu_cmd(interaction: discord.Interaction):
    if not _is_admin(interaction):
        await interaction.response.send_message("⛔ Нет доступа.", ephemeral=True)
        return

    dynamic_ids = db_list_ignored_users()
    all_ids = list(IGNORED_TICKET_OPENER_IDS) + [x for x in dynamic_ids if x not in IGNORED_TICKET_OPENER_IDS]

    if not all_ids:
        await interaction.response.send_message("(список исключений пуст)", ephemeral=True)
        return

    # Строим строки: id - display_name
    lines: list[str] = []
    for uid in all_ids:
        name = await _resolve_display_name(interaction, uid)
        lines.append(f"{uid} - {name}")

    text = "\n".join(lines)
    # Discord лимит 2000 символов: если длинно, режем (обычно список маленький)
    if len(text) > 1900:
        text = text[:1900] + "\n..."

    embed = discord.Embed(title="Список исключений", description=f"```\n{text}\n```")
    await interaction.response.send_message(embed=embed, ephemeral=True)

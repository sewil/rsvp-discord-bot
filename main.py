import mariadb
import discord
from discord import app_commands, ButtonStyle
from ui import RegisterButton, ResetPasswordButton, DownloadButton, ReferralButton, VoteButton
import db
import variables
from discord_client import guild, tree, client
import redis_backend
import socket
import asyncio

ephemerals = {}

class PageButton(discord.ui.Button):
    state: db.RankingsState
    def __init__(self, state: db.RankingsState, style: ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(label=f'{state.page}', style=style)
        self.state = state

    async def callback(self, interaction: discord.Interaction):
        await show_rankings(interaction, self.state)

class RankingsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Show server rankings', style=ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await show_rankings(interaction, db.RankingsState(1, None))

class JobFilterButton(discord.ui.Button):
    state: db.RankingsState
    def __init__(self, state: db.RankingsState, label: str, style: ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(label=label, style=style)
        self.state = state

    async def callback(self, interaction: discord.Interaction):
        await show_rankings(interaction, self.state)

async def show_rankings(interaction: discord.Interaction, state: db.RankingsState):
    page = state.page
    job = state.job
    page_size = state.page_size

    print(f"Fetching rankings, page {page}...")

    try:
        (cnx, cur) = db.db_connect()
        offset = (page-1) * page_size

        if job == 1000:
            (content, pages) = db.db_query_monstercard_rankings(state, cur, offset)
        elif job == 3000:
            (content, pages) = db.db_query_quest_rankings(state, cur, offset)
        elif job == 4000:
            (content, pages) = db.db_query_omok_rankings(state, cur, offset)
        elif job == 5000:
            (content, pages) = db.db_query_matchcard_rankings(state, cur, offset)
        else:
            (content, pages) = db.db_query_rankings(state, cur, offset)

        rankings_view = discord.ui.View(timeout=None)

        # Page buttons
        if page > 1:
            rankings_view.add_item(PageButton(db.RankingsState(1, job)))
        if page > 2:
            rankings_view.add_item(PageButton(db.RankingsState(page - 1, job)))
        rankings_view.add_item(PageButton(db.RankingsState(page, job), ButtonStyle.primary))
        if page < pages - 1:
            rankings_view.add_item(PageButton(db.RankingsState(page + 1, job)))
        if pages > page:
            rankings_view.add_item(PageButton(db.RankingsState(pages, job)))

        if interaction.user.id in ephemerals:
            msg: discord.Message = ephemerals[interaction.user.id]
            await msg.edit(content=content,view=rankings_view)
            await interaction.response.defer()
        else:
            msg = await interaction.response.send_message(content=content,view=rankings_view, ephemeral=True)
            ephemerals[interaction.user.id] = msg.resource
    except mariadb.Error as e:
        print(f"Database error occurred: {e}")
        await interaction.response.send_message(content='An unknown error occurred, please try again later!', ephemeral=True)
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()

@app_commands.checks.has_any_role(variables.GM_ROLE, variables.GM_INTERN_ROLE)
@tree.command(name='find', description='Find in-game user.', guild=guild)
async def find_user(interaction: discord.Interaction, user: discord.User = None, charname: str = None, username: str = None):
    if user == None and charname == None and username == None:
        await interaction.response.send_message('Must provide either discord user, charname or username!', ephemeral=True)
        return
    await db.db_find_user(interaction, str(user.id) if user != None else None, charname, username)

def is_me(member):
    return member.author == client.user

class DummyProtocol(asyncio.Protocol):
    def connection_made(self, transport):
        transport.close()

    def connection_lost(self, exc):
        pass
async def ping_server():
    try:
        loop = asyncio.get_running_loop()
        host = variables.SERVER_HOST
        port = variables.SERVER_PORT
        transport, protocol = await loop.create_connection(
            DummyProtocol,
            host,
            port
        )
        transport.close()
        return True
    except (ConnectionRefusedError, TimeoutError, OSError) as e:
        # print(f"Error connecting to {host}:{port}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred while connecting to {host}:{port}: {e}")
        return False

_status_msg: discord.Message = None
async def update_server_info(channel: discord.TextChannel):
    try:
        global _status_msg
        r = redis_backend.connect()
        world = variables.SERVER_WORLD
        online_game0 = int(redis_backend.get_online_count(r, world, variables.SERVER_GAME) or 0)
        online_shop0 = int(redis_backend.get_online_count(r, world, variables.SERVER_SHOP) or 0)
        online_login = int(redis_backend.get_online_count(r, -1, variables.SERVER_LOGIN) or 0)
        online_count = online_game0 + online_shop0 + online_login
        server_is_online = await ping_server()
        print(f'Update server info... Online? {server_is_online}, Game0 {online_game0}, Shop0 {online_shop0}, Login0 {online_login}')
        color = discord.Color.green() if server_is_online else discord.Color.red()
        embed = discord.Embed(color=color, title='Server info')
        embed.add_field(name='Status', value='ONLINE' if server_is_online else 'OFFLINE')
        embed.add_field(name='Player count', value=online_count)

        if _status_msg == None:
            _status_msg = await channel.send(silent=True, embed=embed)
        else:
            await _status_msg.edit(embed=embed)
    except Exception as e:
        print(f"An unexpected error occurred while updating server info: {e}")

@client.event
async def on_ready():
    await tree.sync(guild=guild)

    # Send access buttons
    access_channel = client.get_channel(variables.CHANNEL_ACCESS_ID)

    if access_channel is None:
        raise f"Access channel not found!"

    print(f"Sending access buttons...")

    # Add register view
    register_view = discord.ui.View(timeout=None)
    register_view.add_item(RegisterButton())
    register_view.add_item(ResetPasswordButton())
    register_view.add_item(ReferralButton())

    # Add download view
    download_view = discord.ui.View(timeout=None)
    download_view.add_item(DownloadButton(variables.DOWNLOAD_URL))
    download_view.add_item(VoteButton())

    await access_channel.purge(limit=10, check=is_me)
    await update_server_info(access_channel)
    await access_channel.send(view=register_view, silent=True)
    await access_channel.send(view=download_view, silent=True)

    # Rankings filters
    rankings_channel = client.get_channel(variables.CHANNEL_RANKINGS_ID)
    rankings_view = discord.ui.View(timeout=None)
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, None), 'All', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 1), 'Warrior', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 2), 'Magician', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 3), 'Bowman', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 4), 'Thief', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 0), 'Beginner', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 1000), 'Monsterbook', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 2000), 'Fame', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 3000), 'Quests', ButtonStyle.primary ))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 4000), 'Omok', ButtonStyle.primary))
    rankings_view.add_item(JobFilterButton(db.RankingsState(1, 5000), 'Matchcard', ButtonStyle.primary))
    await rankings_channel.purge(limit=10, check=is_me)
    await rankings_channel.send(view=rankings_view, content='# Rankings', silent=True)

    print("Ready!")

    while True:
        await asyncio.sleep(60)
        await update_server_info(access_channel)

client.run(variables.TOKEN)

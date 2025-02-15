import mariadb
import discord
import os
from discord import app_commands, ButtonStyle
from dotenv import load_dotenv
from ui import RegisterButton, ResetPasswordButton, DownloadButton
from db import RankingsState, db_connect, db_query_monstercard_rankings, db_query_quest_rankings, db_query_rankings

# Load environment variables from .env file
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("DISCORD_SERVER_ID")
CHANNEL_ACCESS_ID = int(os.getenv("DISCORD_CHANNEL_ACCESS_ID"))
CHANNEL_RANKINGS_ID = int(os.getenv("DISCORD_CHANNEL_RANKINGS_ID"))
DOWNLOAD_URL = os.getenv("DISCORD_DOWNLOAD_URL")

# Initialize the bot
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=SERVER_ID)

ephemerals = {}

class PageButton(discord.ui.Button):
    state: RankingsState
    def __init__(self, state: RankingsState, style: ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(label=f'{state.page}', style=style)
        self.state = state

    async def callback(self, interaction: discord.Interaction):
        await show_rankings(interaction, self.state)

class RankingsButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Show server rankings', style=ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await show_rankings(interaction, RankingsState(1, None), True)

class JobFilterButton(discord.ui.Button):
    state: RankingsState
    def __init__(self, state: RankingsState, label: str, style: ButtonStyle = discord.ButtonStyle.secondary):
        super().__init__(label=label, style=style)
        self.state = state

    async def callback(self, interaction: discord.Interaction):
        await show_rankings(interaction, self.state, False)

async def show_rankings(interaction: discord.Interaction, state: RankingsState, initial: bool = False):
    page = state.page
    job = state.job
    page_size = state.page_size

    print(f"Fetching rankings, page {page}...")

    try:
        (cnx, cur) = db_connect()
        offset = (page-1) * page_size

        if job == 1000:
            (content, pages) = db_query_monstercard_rankings(state, cur, offset)
        elif job == 3000:
            (content, pages) = db_query_quest_rankings(state, cur, offset)
        else:
            (content, pages) = db_query_rankings(state, cur, offset)

        rankings_view = discord.ui.View(timeout=None)

        # Page buttons
        if page > 1:
            rankings_view.add_item(PageButton(RankingsState(1, job)))
        if page > 2:
            rankings_view.add_item(PageButton(RankingsState(page - 1, job)))
        rankings_view.add_item(PageButton(RankingsState(page, job), ButtonStyle.primary))
        if page < pages - 1:
            rankings_view.add_item(PageButton(RankingsState(page + 1, job)))
        if pages > page:
            rankings_view.add_item(PageButton(RankingsState(pages, job)))

        filter_view = discord.ui.View(timeout=None)
        filter_view.add_item(JobFilterButton(RankingsState(page, None), 'All', ButtonStyle.primary if job is None else ButtonStyle.secondary))
        filter_view.add_item(JobFilterButton(RankingsState(page, 1), 'Warrior', ButtonStyle.primary if job == 1 else ButtonStyle.secondary))
        filter_view.add_item(JobFilterButton(RankingsState(page, 2), 'Magician', ButtonStyle.primary if job == 2 else ButtonStyle.secondary))
        filter_view.add_item(JobFilterButton(RankingsState(page, 3), 'Bowman', ButtonStyle.primary if job == 3 else ButtonStyle.secondary))
        filter_view.add_item(JobFilterButton(RankingsState(page, 4), 'Thief', ButtonStyle.primary if job == 4 else ButtonStyle.secondary))
        filter_view.add_item(JobFilterButton(RankingsState(page, 0), 'Beginner', ButtonStyle.primary if job == 0 else ButtonStyle.secondary))
        filter_view.add_item(JobFilterButton(RankingsState(page, 1000), 'Monsterbook', ButtonStyle.primary if job == 1000 else ButtonStyle.secondary))
        filter_view.add_item(JobFilterButton(RankingsState(page, 2000), 'Fame', ButtonStyle.primary if job == 2000 else ButtonStyle.secondary))
        filter_view.add_item(JobFilterButton(RankingsState(page, 3000), 'Quests', ButtonStyle.primary if job == 3000 else ButtonStyle.secondary))

        if initial:
            await interaction.response.send_message(view=filter_view, ephemeral=True)
            msg: discord.Message = await interaction.followup.send(content=content,view=rankings_view, ephemeral=True)
            ephemerals[interaction.user.id] = msg.id
        else:
            await interaction.response.edit_message(view=filter_view)
            if interaction.user.id in ephemerals:
                msg_id = ephemerals[interaction.user.id]
                await interaction.followup.edit_message(message_id=msg_id,content=content,view=rankings_view)
            else:
                msg: discord.Message = await interaction.followup.send(content=content,view=rankings_view, ephemeral=True)
                ephemerals[interaction.user.id] = msg.id
    except mariadb.Error as e:
        print(f"Database error occurred: {e}")
        await interaction.response.send_message(content='An unknown error occurred, please try again later!', ephemeral=True)
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()

def is_me(member):
    return member.author == client.user

@client.event
async def on_ready():
    await tree.sync(guild=guild)

    # Send access buttons
    access_channel = client.get_channel(CHANNEL_ACCESS_ID)

    if access_channel is None:
        raise f"Access channel not found!"

    print(f"Sending access buttons...")

    # Add register view
    register_view = discord.ui.View(timeout=None)
    register_view.add_item(RegisterButton())
    register_view.add_item(ResetPasswordButton())

    # Add download view
    download_view = discord.ui.View(timeout=None)
    download_view.add_item(DownloadButton(DOWNLOAD_URL))

    await access_channel.purge(limit=10, check=is_me)
    await access_channel.send(view=register_view, silent=True)
    await access_channel.send(view=download_view, silent=True)

    # Rankings button
    rankings_channel = client.get_channel(CHANNEL_RANKINGS_ID)
    rankings_view = discord.ui.View(timeout=None)
    rankings_view.add_item(RankingsButton())
    await rankings_channel.purge(limit=10, check=is_me)
    await rankings_channel.send(view=rankings_view, silent=True)

    print("Ready!")

# Start the bot
client.run(TOKEN)

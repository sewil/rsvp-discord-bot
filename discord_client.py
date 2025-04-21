import discord
from discord import app_commands
import variables

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=variables.SERVER_ID)

async def log(content: str):
    if variables.CHANNEL_LOGGING_ID == 0: return
    logging_channel = client.get_channel(variables.CHANNEL_LOGGING_ID)
    if logging_channel != None:
        await logging_channel.send(content)

def send_error_message(content: str, interaction: discord.Interaction):
    return interaction.response.send_message(content=content, ephemeral=True, delete_after=10)

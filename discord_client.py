import discord
from discord import app_commands
import variables

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)
guild = discord.Object(id=variables.SERVER_ID)
logging_channel = None

def get_logging_channel():
    global logging_channel
    if variables.CHANNEL_LOGGING_ID > 0 and logging_channel == None:
        logging_channel = client.get_channel(variables.CHANNEL_LOGGING_ID)
    return logging_channel

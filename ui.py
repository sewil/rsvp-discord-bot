from typing import Callable
import discord
import re
from db import db_register, db_change_password
from utils import validate_dob

class RegisterModal(discord.ui.Modal, title="Register"):
    username = discord.ui.TextInput(label="Username", placeholder="Manji", min_length=4, max_length=12)
    dob = discord.ui.TextInput(label="Date of birth (For char deletion)", placeholder="YYYY-MM-DD")
    password = discord.ui.TextInput(label="Password", placeholder="*****", min_length=4, max_length=12)
    password2 = discord.ui.TextInput(label="Password (again)", placeholder="*****", min_length=4, max_length=12)

    def __init__(self):
        super().__init__()
        self.title = f"Register"

    async def on_submit(self, interaction: discord.Interaction):
        message = f'Something went wrong!'
        if self.password.value != self.password2.value:
            message = "Mismatching passwords!"
        elif validate_dob(self.dob.value) == False:
            message = "Invalid date of birth!"
        else:
            message = db_register(interaction, self)

        # Handle the form submission
        await interaction.response.send_message(
            message,
            ephemeral=True
        )

class ResetPasswordModal(discord.ui.Modal, title="Reset password"):
    username = discord.ui.TextInput(label="Username", placeholder="Manji", min_length=4, max_length=12)
    dob = discord.ui.TextInput(label="Date of birth", placeholder="YYYY-MM-DD")
    new_password = discord.ui.TextInput(label="New password", placeholder="*****", min_length=4, max_length=12)
    new_password2 = discord.ui.TextInput(label="New password (again)", placeholder="*****", min_length=4, max_length=12)

    def __init__(self):
        super().__init__()
        self.title = f"Reset password"

    async def on_submit(self, interaction: discord.Interaction):
        message = f'Something went wrong!'
        if self.new_password.value != self.new_password2.value:
            message = "Mismatching passwords!"
        elif validate_dob(self.dob.value) == False:
            message = "Invalid date of birth!"
        else:
            message = db_change_password(interaction, self)

        # Handle the form submission
        await interaction.response.send_message(
            message,
            ephemeral=True
        )

class RegisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Register', style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RegisterModal())

class ResetPasswordButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Reset password', style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ResetPasswordModal())

class DownloadButton(discord.ui.Button):
    def __init__(self, url: str):
        super().__init__(label='Download', url=url)

class RankingsPageView(discord.ui.View):
    rankings_callback: Callable[[str], str]
    def __init__(self, rankings_callback=None):
        super().__init__(label='Page', style=discord.TextStyle.short)
        self.rankings_callback = rankings_callback

    async def callback(self, interaction: discord.Interaction):
        rankings = self.rankings_callback(self.value)
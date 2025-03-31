import discord
from db import db_register, db_change_password
import db
from utils import validate_dob
import variables

class RegisterModal(discord.ui.Modal, title="Register"):
    username = discord.ui.TextInput(label="Username", placeholder="Manji", min_length=4, max_length=12)
    dob = discord.ui.TextInput(label="Date of birth (For char deletion)", placeholder="YYYY-MM-DD", min_length=10, max_length=10)
    password = discord.ui.TextInput(label="Password", placeholder="*****", min_length=4, max_length=12)
    password2 = discord.ui.TextInput(label="Password (again)", placeholder="*****", min_length=4, max_length=12)
    referral_code = discord.ui.TextInput(label="Referral code", placeholder="ABCD1234", min_length=0, max_length=8, required=False)

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
            message = await db_register(interaction, self)

        # Handle the form submission
        await interaction.response.send_message(
            message,
            ephemeral=True
        )

class ResetPasswordModal(discord.ui.Modal, title="Reset password"):
    username = discord.ui.TextInput(label="Username", placeholder="Manji", min_length=4, max_length=12)
    dob = discord.ui.TextInput(label="Date of birth", placeholder="YYYY-MM-DD", min_length=10, max_length=10)
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
            message = await db_change_password(interaction, self)

        # Handle the form submission
        await interaction.response.send_message(
            message,
            ephemeral=True
        )

class RegisterButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Register', style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        if variables.ACCESS_REQUIRED_ROLE != None and interaction.guild.get_role(int(variables.ACCESS_REQUIRED_ROLE)) not in interaction.user.roles:
            await interaction.response.send_message('Missing the required roles to do this!', ephemeral=True)
        else:
            await interaction.response.send_modal(RegisterModal())

class ResetPasswordButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Reset password', style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        if variables.ACCESS_REQUIRED_ROLE != None and interaction.guild.get_role(int(variables.ACCESS_REQUIRED_ROLE)) not in interaction.user.roles:
            await interaction.response.send_message('Missing the required roles to do this!', ephemeral=True)
        else:
            await interaction.response.send_modal(ResetPasswordModal())

class DownloadButton(discord.ui.Button):
    def __init__(self, url: str):
        super().__init__(label='Download', url=url)

class ReferralButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Get referral code', style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        msg = await db.db_get_referral_code(interaction)
        await interaction.user.send(msg)
        await interaction.response.defer()

class VoteButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Vote on Gtop100', style=discord.ButtonStyle.secondary)

    async def callback(self, interaction: discord.Interaction):
        (msg, success) = await db.db_get_voting_link(interaction)
        if success:
            await interaction.user.send(msg)
            await interaction.response.defer()
        else:
            await interaction.response.send_message(msg, ephemeral=True)
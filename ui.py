import discord
from db import db_register, db_change_password
import db
from utils import validate_dob, validate_email
from discord_client import send_tmp_message

class RegisterModal(discord.ui.Modal, title="Register"):
    username = discord.ui.TextInput(label="Username", placeholder="Manji", min_length=4, max_length=12)
    dob = discord.ui.TextInput(label="Date of birth (For char deletion)", placeholder="YYYY-MM-DD", min_length=10, max_length=10)
    password = discord.ui.TextInput(label="Password", placeholder="*****", min_length=4, max_length=12)
    password2 = discord.ui.TextInput(label="Password (again)", placeholder="*****", min_length=4, max_length=12)
    referral_code = discord.ui.TextInput(label="Referral code (optional)", placeholder="ABCD1234", min_length=0, max_length=8, required=False)

    def __init__(self):
        super().__init__()
        self.title = f"Register"

    async def on_submit(self, interaction: discord.Interaction):
        if self.password.value != self.password2.value:
            await send_tmp_message("Mismatching passwords!", interaction)
        elif validate_dob(self.dob.value) == False:
            await send_tmp_message("Invalid date of birth!", interaction)
        else:
            await db_register(interaction, self)

class ResetPasswordModal(discord.ui.Modal, title="Reset password"):
    username = discord.ui.TextInput(label="Username", placeholder="Manji", min_length=4, max_length=12)
    dob = discord.ui.TextInput(label="Date of birth", placeholder="YYYY-MM-DD", min_length=10, max_length=10)
    new_password = discord.ui.TextInput(label="New password", placeholder="*****", min_length=4, max_length=12)
    new_password2 = discord.ui.TextInput(label="New password (again)", placeholder="*****", min_length=4, max_length=12)

    def __init__(self):
        super().__init__()
        self.title = f"Reset password"

    async def on_submit(self, interaction: discord.Interaction):
        if self.new_password.value != self.new_password2.value:
            await send_tmp_message("Mismatching passwords!", interaction)
        elif validate_dob(self.dob.value) == False:
            await send_tmp_message("Invalid date of birth!", interaction)
        else:
            await db_change_password(interaction, self)

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


class MigrateAccountModal(discord.ui.Modal, title="Migrate account"):
    dob = discord.ui.TextInput(label="Date of birth", placeholder="YYYY-MM-DD", min_length=10, max_length=10)
    email = discord.ui.TextInput(label="E-mail", placeholder="manji@maplestory.com", min_length=4)
    email2 = discord.ui.TextInput(label="Confirm e-mail", placeholder="manji@maplestory.com", min_length=4)

    def __init__(self):
        super().__init__()

    async def on_submit(self, interaction: discord.Interaction):
        if (self.email.value != self.email2.value):
            await send_tmp_message("E-mails don't match!", interaction)
        elif validate_dob(self.dob.value) == False:
            await send_tmp_message("Invalid date of birth! Make sure it follows the format `YYYY-MM-DD`", interaction)
        elif validate_email(self.email.value) == False:
            await send_tmp_message("Invalid email! Please ensure it follows the format `manji@maplestory.com`", interaction)
        else:
            await db.db_migrate_account(interaction, self.email.value, self.dob.value)

class MigrateAccountButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label='Migrate account', style=discord.ButtonStyle.primary)
    
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(MigrateAccountModal())


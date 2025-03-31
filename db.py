import zlib
import mariadb
import discord
import bcrypt
import utils
from utils import db_format_dob, job_name, get_ban_reason
from datetime import datetime, timedelta, timezone
import math
from table2ascii import table2ascii as t2a, PresetStyle
import variables
from discord_client import log

def db_connect():
    cnx = mariadb.connect(
        host=variables.DB_HOST,
        port=3306,
        user=variables.DB_USER,
        password=variables.DB_PASS,
        database=variables.DB_NAME,
    )

    cur = cnx.cursor()

    return (cnx, cur)

async def db_register(interaction: discord.Interaction, form):
    try:
        discord_id = interaction.user.id
        dob_formatted = db_format_dob(form.dob.value)
        hashed_password = bcrypt.hashpw(form.password.value.encode(), bcrypt.gensalt(13, prefix=b'2a'))

        (cnx, cur) = db_connect()

        # Check referral code
        referral_code = form.referral_code.value
        referred_by = None
        if referral_code != None and len(referral_code) > 0:
            if utils.validate_referral_code(referral_code) == False:
                await log(f"User <@{interaction.user.id}> failed registration with invalid referral code `{referral_code}`. (Username `{form.username.value}`, DoB `{dob_formatted}`).")
                return "Invalid referral code!"
            cur.execute("SELECT ID FROM users WHERE LOWER(referral_code) = LOWER(%s)", (referral_code,))
            result = cur.fetchone()
            if result == None or result[0] == None:
                await log(f"User <@{interaction.user.id}> failed registration with invalid referral code `{referral_code}`. (Username `{form.username.value}`, DoB `{dob_formatted}`).")
                return "Invalid referral code!"
            referred_by = result[0]

        # Check username/discord_id already exists
        cur.execute("""
            SELECT COUNT(*) FROM users
            WHERE LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s)
        """, (form.username.value, discord_id))

        if cur.fetchone()[0] > 0:
            await log(f"User <@{interaction.user.id}> tried registering already existing account with username `{form.username.value}` and DoB `{dob_formatted}`.")
            return "This user is already registered!"

        cur.execute(
            "INSERT INTO users (username, password, email, gender, admin, char_delete_password, referred_by) VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (form.username.value, hashed_password, discord_id, 10, 0, dob_formatted, referred_by)
        )
        cnx.commit()
        userid = cur.lastrowid

        await log(f"User <@{interaction.user.id}> registered new account with username `{form.username.value}` (userid {userid}) and DoB `{dob_formatted}`{f' using referral code `{referral_code}`' if bool(referral_code) else ''}.")
        return f'Welcome {form.username}!'
    except mariadb.Error as e:
        await log(f"Database error occurred on registration for user <@{interaction.user.id}>: {e}")
        return 'An unknown error occurred, please try again later!'
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()

async def db_change_password(interaction: discord.Interaction, form):
    try:
        user_id = interaction.user.id

        (cnx, cur) = db_connect()

        dob_formatted = db_format_dob(form.dob.value)

        # Check username/discord_id/dob combination exists
        check_query = f"""
            SELECT * FROM users
            WHERE LOWER(username) = LOWER(%s) AND LOWER(email) = LOWER(%s) AND char_delete_password = %s
        """
        cur.execute(check_query, (form.username.value, user_id, dob_formatted))
        user = cur.fetchone()
        if user == None:
            await log(f"User <@{interaction.user.id}> failed resetting password for account with username `{form.username.value}` and DoB `{dob_formatted}`.")
            return "User not found! Make sure to use the same Discord account that you registered with and that you have entered a valid date of birth."

        hashed_new_password = bcrypt.hashpw(form.new_password.value.encode(), bcrypt.gensalt(13, prefix=b'2a'))

        insert_query = "UPDATE users SET password=%s WHERE ID=%s"
        cur.execute(insert_query, (hashed_new_password, user[0]))
        cnx.commit()
        userid = user[0]

        await log(f"User <@{interaction.user.id}> reset password for account with username `{form.username.value}` (userid {userid}) and DoB `{dob_formatted}`.")
        return f'Password changed!'
    except mariadb.Error as e:
        await log(f"Database error occurred on reset password for user <@{interaction.user.id}>: {e}")
        return 'An unknown error occurred, please try again later!'
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()


class RankingsState:
    page_size: int
    page: int
    job: int
    def __init__(self, page: int, job: int, page_size: int = 10):
        self.page = page
        self.job = job
        self.page_size = page_size

def db_query_rankings(state: RankingsState, cur: mariadb.Cursor, offset: int):
    job_condition = ''
    job = state.job
    page = state.page
    page_size = state.page_size
    order_by_fame = job == 2000
    filter_by_job = job != None and order_by_fame == False

    if filter_by_job:
        job_condition = f'AND FLOOR(characters.job/100) = %s'

    cur.execute(f"""
        SELECT COUNT(*) FROM characters
        JOIN users ON characters.userid = users.id
        WHERE users.admin = 0 AND characters.deleted_at IS NULL {job_condition}
    """, () if job == None else (job,))
    count = cur.fetchone()[0]
    pages = math.ceil(count / page_size)
    cur.execute(f"""
        SELECT `name`, `level`, `job`, `exp`, `fame` FROM characters
        JOIN users ON characters.userid = users.id
        WHERE users.admin = 0 AND characters.deleted_at IS NULL {job_condition}
        ORDER BY {'characters.fame DESC, ' if order_by_fame else ''}characters.level DESC, characters.exp DESC
        LIMIT %s
        OFFSET %s
    """, (job, page_size, offset) if filter_by_job else (page_size, offset))
    results = cur.fetchall()
    rank_offset = (page - 1) * page_size
    if (len(results) > 0):
        body = map(lambda x: [rank_offset + x[0] + 1, x[1][0], x[1][1], x[1][3], job_name(x[1][2]), x[1][4]], enumerate(results))
        content = t2a(
            header=['#', 'IGN', 'Level', 'EXP', 'Job', 'Fame'],
            body=body,
            style=PresetStyle.ascii_rounded_box,
        )

        content = f"```{content}```"
    else:
        content = 'No results!'

    return (content, pages)

def db_query_omok_rankings(state: RankingsState, cur: mariadb.Cursor, offset: int):
    page = state.page
    page_size = state.page_size

    sel_query = f"""
        SELECT `characters`.`name`, `characters`.`level`, `characters`.job, `characters`.`exp`, gamestats.omokscore, gamestats.omokwins, gamestats.omokties, gamestats.omoklosses
        FROM gamestats
        JOIN characters ON `characters`.ID = `gamestats`.ID
        JOIN users ON `characters`.userid = `users`.ID
        WHERE users.admin = 0 AND characters.deleted_at IS NULL
        ORDER BY omokscore DESC, omokwins DESC, omokties DESC, `characters`.`level` DESC, `characters`.`exp` DESC
    """

    cur.execute(f"SELECT COUNT(*) FROM ({sel_query}) as derived")
    count = cur.fetchone()[0]
    pages = math.ceil(count / page_size)
    cur.execute(f"""
        {sel_query}
        LIMIT %s
        OFFSET %s
    """, (page_size, offset))
    results = cur.fetchall()
    rank_offset = (page - 1) * page_size
    if (len(results) > 0):
        body = map(lambda x: [rank_offset + x[0] + 1, x[1][0], f"Lv. {x[1][1]} {job_name(x[1][2])}", x[1][4], f"{x[1][5]}/{x[1][6]}/{x[1][7]}"], enumerate(results))
        content = t2a(
            header=['#', 'IGN', 'Job', 'Score', "W/T/L"],
            body=body,
            style=PresetStyle.ascii_rounded_box,
        )

        content = f"```{content}```"
    else:
        content = 'No results!'

    return (content, pages)

def db_query_matchcard_rankings(state: RankingsState, cur: mariadb.Cursor, offset: int):
    page = state.page
    page_size = state.page_size

    sel_query = f"""
        SELECT `characters`.`name`, `characters`.`level`, `characters`.job, `characters`.`exp`, gamestats.matchcardscore, gamestats.matchcardwins, gamestats.matchcardties, gamestats.matchcardlosses
        FROM gamestats
        JOIN characters ON `characters`.ID = `gamestats`.ID
        JOIN users ON `characters`.userid = `users`.ID
        WHERE users.admin = 0 AND characters.deleted_at IS NULL
        ORDER BY matchcardscore DESC, matchcardwins DESC, matchcardties DESC, `characters`.`level` DESC, `characters`.`exp` DESC
    """

    cur.execute(f"SELECT COUNT(*) FROM ({sel_query}) as derived")
    count = cur.fetchone()[0]
    pages = math.ceil(count / page_size)
    cur.execute(f"""
        {sel_query}
        LIMIT %s
        OFFSET %s
    """, (page_size, offset))
    results = cur.fetchall()
    rank_offset = (page - 1) * page_size
    if (len(results) > 0):
        body = map(lambda x: [rank_offset + x[0] + 1, x[1][0], f"Lv. {x[1][1]} {job_name(x[1][2])}", x[1][4], f"{x[1][5]}/{x[1][6]}/{x[1][7]}"], enumerate(results))
        content = t2a(
            header=['#', 'IGN', 'Job', 'Score', "W/T/L"],
            body=body,
            style=PresetStyle.ascii_rounded_box,
        )

        content = f"```{content}```"
    else:
        content = 'No results!'

    return (content, pages)

def db_query_quest_rankings(state: RankingsState, cur: mariadb.Cursor, offset: int):
    page = state.page
    page_size = state.page_size

    sel_query = f"""
        SELECT `characters`.`name`, `characters`.`level`, `characters`.job, `characters`.`exp`, COUNT(*)
        FROM character_quests
        JOIN characters ON `characters`.ID = `character_quests`.charid
        JOIN users ON `characters`.userid = `users`.ID
        WHERE users.admin = 0 AND characters.deleted_at IS NULL AND character_quests.`data` = 'end'
        GROUP BY charid
        ORDER BY COUNT(*) DESC, `characters`.`level` DESC, `characters`.`exp` DESC
    """

    cur.execute(f"SELECT COUNT(*) FROM ({sel_query}) as derived")
    count = cur.fetchone()[0]
    pages = math.ceil(count / page_size)
    cur.execute(f"""
        {sel_query}
        LIMIT %s
        OFFSET %s
    """, (page_size, offset))
    results = cur.fetchall()
    rank_offset = (page - 1) * page_size
    if (len(results) > 0):
        body = map(lambda x: [rank_offset + x[0] + 1, x[1][0], f"Lv. {x[1][1]} {job_name(x[1][2])}", x[1][4]], enumerate(results))
        content = t2a(
            header=['#', 'IGN', 'Job', 'Quests completed'],
            body=body,
            style=PresetStyle.ascii_rounded_box,
        )

        content = f"```{content}```"
    else:
        content = 'No results!'

    return (content, pages)

def db_query_monstercard_rankings(state: RankingsState, cur: mariadb.Cursor, offset: int):
    page_size = state.page_size
    page = state.page
    sel_query = """
        SELECT `characters`.`name`, `characters`.`level`, `characters`.job, `characters`.`exp`, SUM(`monsterbook`.`count`)
        FROM monsterbook
        JOIN characters ON `characters`.ID = `monsterbook`.charid
        JOIN users ON `characters`.userid = `users`.ID
        WHERE users.admin = 0 AND characters.deleted_at IS NULL
        GROUP BY charid
        ORDER BY SUM(`monsterbook`.`count`) DESC, `characters`.`level` DESC, `characters`.`exp` DESC
    """

    cur.execute(f"SELECT COUNT(*) FROM ({sel_query}) as derived")
    count = cur.fetchone()[0]
    pages = math.ceil(count / page_size)
    cur.execute(f"""
        {sel_query}
        LIMIT %s
        OFFSET %s
    """, (page_size, offset))
    results = cur.fetchall()
    rank_offset = (page - 1) * page_size
    if (len(results) > 0):
        body = map(lambda x: [rank_offset + x[0] + 1, x[1][0], f"Lv. {x[1][1]} {job_name(x[1][2])}", x[1][4]], enumerate(results))
        content = t2a(
            header=['#', 'IGN', 'Job', 'Cards collected'],
            body=body,
            style=PresetStyle.ascii_rounded_box,
        )

        content = f"```{content}```"
    else:
        content = 'No results!'
    return (content, pages)

def format_char(row):
    is_deleted = row[10] <= datetime.now() if row[10] != None else False
    text = f"{row[7]} (charid {row[11]}) - Lv. {row[8]} {utils.job_name(row[9])}"
    if is_deleted:
        text = f"~~{text}~~"
    return text

def db_find_user(discord_id: str = None, charname: str = None, username: str = None):
    try:
        (cnx, cur) = db_connect()
        cur.execute(f"""
            SELECT
                users.ID, users.username, users.email, users.admin, users.ban_expire, users.ban_reason, users.created_at,
	            characters.`name`, characters.`level`, characters.`job`, characters.`deleted_at`, characters.ID
            FROM users
            LEFT JOIN characters ON characters.userid = users.ID
            WHERE LOWER(email) = LOWER(%s) OR LOWER(characters.`name`) = LOWER(%s) OR LOWER(users.`username`) = LOWER(%s)
        """, (discord_id,charname,username))
        results = cur.fetchall()
        if len(results) == 0:
            return "User not found!"
        user = results[0]
        if results[0][7] == None:
            characters = []
        else:
            characters = list(map(format_char, results))
        
        banned_until = None
        ban_reason = ''
        if user[4] > datetime.now():
            banned_until = datetime.strftime(user[4], "%Y-%m-%d %H:%M")
            ban_reason = get_ban_reason(user[5])
            
        registered_at = datetime.strftime(user[6], "%Y-%m-%d %H:%M")
        
        discord_user = f"<@{user[2]}>." if user[2] != None and len(user[2]) > 0 else 'Not found!'

        message = f'Found user {user[1]} (userid {user[0]}). Discord user: {discord_user} GM Level: {user[3]}. Account registered at {registered_at}.{f" Banned until {banned_until} for {ban_reason}." if banned_until != None else ""}'
        message += f'\n### Characters\n'
        if (len(characters) == 0):
            message += "No characters found!"
        else:
            for c in characters:
                message += f'- {c}\n'
        return message
    except mariadb.Error as e:
        print(f"Database error occurred: {e}")
        return 'An unknown error occurred, please try again later!'
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()

async def db_get_referral_code(interaction: discord.Interaction):
    try:
        (cnx, cur) = db_connect()
        cur.execute("""
            SELECT ID, referral_code
            FROM users
            WHERE LOWER(email) = LOWER(%s)
        """, (interaction.user.id,))
        result = cur.fetchone()
        if result == None:
            return "Couldn't find an account for this user! Please register an account first."
        referral_code = result[1]
        if referral_code == None:
            # Null referral code, make one
            user_id = result[0]
            user_id_crc32 = zlib.crc32(str(user_id).encode() + bcrypt.gensalt())
            referral_code = hex(user_id_crc32)[2:].upper()
            cur.execute("UPDATE `users` SET `referral_code`=%s WHERE `ID`=%s", (referral_code, user_id))
            cnx.commit()
        return f"Here is your referral code! Send this code to any players registering a new account on MG2. When the player reaches **level 30** for the first time, you and the player you referred will both earn **2,000 Cash**!\n```{referral_code}```"
    except mariadb.Error as e:
        await log(f"Database error occurred on get referral code for user <@{interaction.user.id}>: {e}")
        return 'An unknown error occurred, please try again later!'
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()

async def db_get_voting_link(interaction: discord.Interaction):
    try:
        (cnx, cur) = db_connect()
        cur.execute("SELECT username FROM users WHERE LOWER(email) = LOWER(%s)", (interaction.user.id,))
        result = cur.fetchone()
        if result == None:
            return ("Couldn't find an account for this user! Please register an account first.", False)
        username = result[0]
        timestamp = int((datetime.now(timezone.utc) + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        return ((
            "Here is your voting link!\n"
            f"https://gtop100.com/MapleStory/OpenMG-MG2-104637?vote=1&pingUsername={username}\n\n"
            f"You can vote once a day, resetting at <t:{timestamp}:t>, and you will earn **1,000 Cash** per vote. After voting, it may take up to 5 minutes to see the updated amounts in Cash Shop, so please be patient!"
        ), True)
    except mariadb.Error as e:
        await log(f"Database error occurred on get voting link for user <@{interaction.user.id}>: {e}")
        return ('An unknown error occurred, please try again later!', False)
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()

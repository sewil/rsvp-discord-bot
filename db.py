import mariadb
import os
import discord
import bcrypt
from utils import db_format_dob, job_name, get_ban_reason
from dotenv import load_dotenv
from datetime import datetime
import math
from table2ascii import table2ascii as t2a, PresetStyle

load_dotenv()

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASS = os.getenv("DB_PASS")

def db_connect():
    cnx = mariadb.connect(
        host=DB_HOST,
        port=3306,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
    )

    cur = cnx.cursor()

    return (cnx, cur)

def db_register(interaction: discord.Interaction, form):
    try:
        user_id = interaction.user.id
        dob_formatted = db_format_dob(form.dob.value)
        hashed_password = bcrypt.hashpw(form.password.value.encode(), bcrypt.gensalt(13, prefix=b'2a'))

        (cnx, cur) = db_connect()

        # Check username/discord_id already exists
        cur.execute(f"""
            SELECT COUNT(*) FROM users
            WHERE LOWER(username) = LOWER(%s) OR LOWER(email) = LOWER(%s)
        """, (form.username.value, user_id))
        if cur.fetchone()[0] > 0:
            return "This user is already registered!"

        cur.execute(
            "INSERT INTO users (username, password, email, gender, admin, char_delete_password) VALUES (%s, %s, %s, %s, %s, %s)",
            (form.username.value, hashed_password, user_id, 10, 0, dob_formatted)
        )
        cnx.commit()

        return f'Welcome {form.username}!'
    except mariadb.Error as e:
        print(f"Database error occurred: {e}")
        return 'An unknown error occurred, please try again later!'
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()

def db_change_password(interaction: discord.Interaction, form):
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
            return "User not found! Make sure to use the same Discord account that you registered with and that you have entered a valid date of birth."

        hashed_new_password = bcrypt.hashpw(form.new_password.value.encode(), bcrypt.gensalt(13, prefix=b'2a'))

        insert_query = "UPDATE users SET password=%s WHERE ID=%s"
        cur.execute(insert_query, (hashed_new_password, user[0]))
        cnx.commit()

        return f'Password changed!'
    except mariadb.Error as e:
        print(f"Database error occurred: {e}")
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

def db_query_user(discord_id: int):
    try:
        (cnx, cur) = db_connect()
        cur.execute(f"""
            SELECT * FROM users
            WHERE LOWER(email) = LOWER(%s)
        """, (discord_id,))
        user = cur.fetchone()
        if user == None:
            return "User not found!"
        
        banned_until = None
        ban_reason = ''
        if user[9] > datetime.now():
            banned_until = datetime.strftime(user[9], "%Y-%m-%d %H:%M")
            ban_reason = get_ban_reason(user[10])
            
        registered_at = datetime.strftime(user[19], "%Y-%m-%d %H:%M")

        return f'Found account {user[1]} (userid {user[0]}). GM Level: {user[7]}. Account registered at {registered_at}.{f" Banned until {banned_until} for {ban_reason}." if banned_until != None else ""}'
    except mariadb.Error as e:
        print(f"Database error occurred: {e}")
        return 'An unknown error occurred, please try again later!'
    finally:
        if 'cur' in locals(): cur.close()
        if 'cnx' in locals(): cnx.close()

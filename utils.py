import re

def job_name(job: int):
    if job == 0: return "Beginner"
    elif job == 100: return "Swordsman"
    elif job == 110: return "Fighter"
    elif job == 111: return "Crusader"
    elif job == 120: return "Page"
    elif job == 121: return "White Knight"
    elif job == 130: return "Spearman"
    elif job == 131: return "Dragon Knight"
    elif job == 200: return "Magician"
    elif job == 210: return "Wizard (F/P)"
    elif job == 211: return "Mage (F/P)"
    elif job == 220: return "Wizard (I/L)"
    elif job == 221: return "Mage (I/L)"
    elif job == 230: return "Cleric"
    elif job == 231: return "Priest"
    elif job == 300: return "Archer"
    elif job == 310: return "Hunter"
    elif job == 311: return "Ranger"
    elif job == 320: return "Crossbowman"
    elif job == 321: return "Sniper"
    elif job == 400: return "Rogue"
    elif job == 410: return "Assassin"
    elif job == 411: return "Hermit"
    elif job == 420: return "Bandit"
    elif job == 421: return "Chief Bandit"
    elif job == 500: return "GM"
    else: return "N/A"

def validate_dob(dob: str):
    return re.match(r"^\d{4}-\d{2}-\d{2}$", dob) != None

def db_format_dob(dob: str):
    return int(dob.replace("-", ""))

def validate_referral_code(code: str):
    return re.match(r"[A-Fa-f\d]{8}", code) != None

def get_ban_reason(reason: int):
    if reason == 1: return 'hacking'
    elif reason == 2: return 'botting'
    elif reason == 3: return 'advertising'
    elif reason == 4: return 'harassment'
    elif reason == 5: return 'bad language'
    elif reason == 6: return 'scamming'
    elif reason == 7: return 'misconduct'
    elif reason == 8: return 'illegal cash transaction'
    elif reason == 9: return 'illegal charging/funding'
    else: return 'N/A'

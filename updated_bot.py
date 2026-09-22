# -*- coding: utf-8 -*-
# 💕 ربات جرأت حقیقت + بازی نوبتی + سنگ کاغذ قیچی
# تماماً با دکمه؛ مناسب پیوی و گروه؛ آماده‌ی Termux و Railway
import os
import random
import re
import sqlite3
import sys
import threading
import traceback

try:
    from config import TOKEN, ADMINS      # توکن و ادمین‌ها تو فایل config.py
except ImportError:
    print("❌ فایل config.py کنار bot.py پیدا نشد.")
    sys.exit(2)

if ":" not in str(TOKEN):
    print("❌ توکن ربات رو تو فایل config.py بذار (از @BotFather بگیر).")
    sys.exit(2)

if isinstance(ADMINS, int):
    ADMINS = {ADMINS}
ADMINS = set(ADMINS)

import telebot
from telebot.types import (InlineKeyboardMarkup as KB, InlineKeyboardButton as Btn,
                           ReplyKeyboardMarkup as RKB)

# مسیر دیتابیس: DB_PATH  >  Volume ریلوی  >  کنار همین فایل
BASE = os.path.dirname(os.path.abspath(__file__))
_vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
DB = (os.environ.get("DB_PATH")
      or (os.path.join(_vol, "td.db") if _vol else os.path.join(BASE, "td.db")))
os.makedirs(os.path.dirname(DB) or ".", exist_ok=True)
if any(k.startswith("RAILWAY_") for k in os.environ) and not (
        os.environ.get("DB_PATH") or _vol):
    print("⚠️ Volume به سرویس وصل نیست! با هر دیپلوی، سوال‌ها و امتیازها پاک می‌شن. "
          "(راهنما: RAILWAY.md)")

# ---------- تنظیمات ----------
PER = 5                # تعداد سوال در هر صفحه‌ی لیست
WIN_POINTS = 3         # امتیاز هر برد سنگ کاغذ قیچی
DONE_POINTS = 1        # امتیاز انجام حقیقت/جرات در بازی نوبتی (۰ = بدون امتیاز)
LEVEL_STEP = 100       # رفتن از لول k به k+1 = k * LEVEL_STEP امتیاز
MAX_PLAYERS = 8        # حداکثر بازیکن بازی نوبتی
SEED_VERSION = 2       # با بالا بردنش، سوال‌های آماده‌ی جدید به دیتابیس اضافه می‌شن

KINDS = {"truth": "💗 حقیقت", "dare": "🎀 جرات"}
CATS = {
    "love": "❤️ عاشقانه",
    "friend": "🤝 دوستانه",
    "emo": "💔 احساسی",
    "adult": "🔞 مثبت ۱۸",
}

# ---------- سوال‌های آماده ----------
SEEDS = {
    ("truth", "friend"): [
        "بدترین دروغی که به دوستت گفتی چی بوده؟",
        "چه چیزی درباره‌ی من هست که دوست داری عوض بشه؟",
        "خجالت‌آورترین لحظه‌ی زندگیت کدوم بوده؟",
        "اگه می‌تونستی یه روز جای یکی از ما باشی، جای کی؟ چرا؟",
        "عجیب‌ترین عادتت چیه که کمتر کسی می‌دونه؟",
        "یه راز کوچیک و بی‌خطر که هنوز به هیچ‌کس نگفتی؟",
        "کدوم یکی از دوستات رو بیشتر از همه دوست داری و چرا؟",
        "بدترین هدیه‌ای که تو عمرت گرفتی چی بوده؟",
        "اگه یه میلیارد بهت می‌دادن، اولین کارت چی می‌شد؟",
        "چه چیزیه که همه از تو انتظار دارن ولی از انجامش متنفری؟",
        "آخرین چیزی که تو گوگل سرچ کردی چی بود؟",
        "کدوم ویژگی خودت رو دوست نداری؟",
    ],
    ("dare", "friend"): [
        "آخرین عکس گالریت رو بفرست تو گروه.",
        "یه ویس بفرست و ۱۰ ثانیه مثل گربه میو کن.",
        "یه استیکر بفرست که حال الانت رو نشون بده و توضیحش بده.",
        "یه عکس از اطرافت همین الان بفرست (بدون مرتب کردن!).",
        "با یه لهجه‌ی دلخواه یه ویس ۱۰ ثانیه‌ای بفرست.",
        "برای هر کدوم از بقیه یه اسم مستعار خنده‌دار بذار.",
        "یه جمله‌ی خنده‌دار بگو که هیچ‌کس نتونه جلوی خنده‌ش رو بگیره.",
        "یه شعر کودکانه رو با ژست اپرا تو یه ویس بخون.",
        "سه تا از قشنگ‌ترین ویژگی‌های یکی از بقیه رو بگو.",
    ],
    ("truth", "emo"): [
        "آخرین باری که گریه کردی کی بود و چرا؟",
        "بزرگ‌ترین ترست تو زندگی چیه؟",
        "چه چیزی تو رو واقعاً خوشحال می‌کنه، حتی اگه کوچیک باشه؟",
        "چه حرفی رو دوست داشتی به خودِ ۱۰ سال پیشت بزنی؟",
        "بزرگ‌ترین حسرتت چیه؟",
        "کدوم خاطره‌ات رو بیشتر از همه دوست داری؟",
        "چه چیزی باعث می‌شه احساس کنی دوست‌داشتنی هستی؟",
        "آخرین بار کی از ته دل خندیدی؟",
        "کدوم آدم زندگیت بیشتر از همه روت تأثیر گذاشته؟ چطور؟",
        "بزرگ‌ترین آرزوت برای ۵ سال آینده چیه؟",
    ],
    ("dare", "emo"): [
        "یه پیام صمیمی برای کسی که مدت‌هاست باهاش حرف نزدی بفرست.",
        "یه چیزی که ازش ممنونی رو تو یه ویس ۳۰ ثانیه‌ای بگو.",
        "سه تا چیزی که امروز بابتشون شکرگزاری رو بنویس.",
        "یه آهنگ که الان حالت رو نشون می‌ده معرفی کن و بگو چرا.",
        "به خودت یه نامه‌ی کوتاه ۳ جمله‌ای بنویس و اینجا بفرست.",
        "یه عکس از چیزی که امروز بهت آرامش داده بفرست.",
    ],
    ("truth", "love"): [
        "اولین کراشت کی بود؟",
        "توی یه رابطه چه چیزی برات از همه مهم‌تره؟",
        "اولین باری که فهمیدی عاشق شدی کی و کجا بود؟",
        "اولین بار چه چیزی از پارتنرت توجهت رو جلب کرد؟",
        "رمانتیک‌ترین کاری که تا حالا برات کردن چی بوده؟",
        "قرار ایده‌آلت چه شکلیه؟",
        "کدوم لحظه‌ی با هم بودنمون رو هیچ‌وقت یادت نمی‌ره؟",
        "کدوم ویژگی من رو از همه بیشتر دوست داری؟",
        "اگه فقط یه روز وقت داشتیم، دوست داشتی کجا و چطور بگذرونیمش؟",
        "کدوم آهنگ تو رو یاد ما می‌ندازه؟",
        "چه حرفی هست که دوست داری بیشتر بهم بگی ولی خجالت می‌کشی؟",
        "بزرگ‌ترین آرزوت برای آینده‌ی ما دو نفر چیه؟",
    ],
    ("dare", "love"): [
        "یه جمله‌ی عاشقانه برای نفر کناریت بنویس.",
        "یه ویس ۱۰ ثانیه‌ای عاشقانه برای پارتنرت بفرست.",
        "سه تا از چیزایی که تو پارتنرت دوست داری رو بگو.",
        "یه استیکر قلب بفرست و بگو برای کیه.",
        "یه خاطره‌ی قشنگ از با هم بودنمون رو یادآوری کن.",
        "برای پارتنرت یه اسم مستعار جدید و بامزه بذار.",
        "یه «دوستت دارم» با خلاقانه‌ترین شکلی که می‌تونی بنویس.",
        "یه عکس از چیزی که تو رو یاد پارتنرت می‌ندازه بفرست.",
        "بگو امروز چه کار کوچیکی از پارتنرت باعث لبخندت شد.",
    ],
    ("truth", "adult"): [
        "به‌یادموندنی‌ترین بوسه‌ی زندگیت کی و کجا بود؟",
        "کدوم لباس پارتنرتو بیشتر از همه دوست داری؟",
        "چه رفتاری از پارتنرت باعث می‌شه دلت پر بزنه؟",
        "رمانتیک‌ترین شب دو نفره‌ای که دوست داری تجربه کنی چه شکلیه؟",
        "اولین بار کی دلت خواست منو ببوسی؟",
        "کدوم لحظه‌ی عاشقانه‌ی فیلم‌ها رو دوست داری با هم تجربه کنیم؟",
        "چه چیزی از من بیشتر از همه تو رو جذب می‌کنه؟",
        "کدوم جمله‌ی عاشقانه از طرف من دلت رو آب می‌کنه؟",
    ],
    ("dare", "adult"): [
        "یه پیام دلبرانه (در حد رمانتیک) برای پارتنرت بفرست.",
        "یه ویس با صدای آروم بفرست و بگو «دلم برات تنگ شده».",
        "یه بوس (استیکر یا ایموجی) بفرست و بگو برای کیه 😘",
        "سه تا تعریف خیلی قشنگ از ظاهر پارتنرت بگو.",
        "بگو اگه الان کنارت بود اولین کارت چی می‌شد (در حد بغل و بوسه).",
        "یه جمله‌ی کوتاه، شیطون ولی تمیز برای پارتنرت بنویس.",
    ],
}

# ---------- لول‌ها: (عنوان، متن عاشقانه‌ی دوطرفه) ----------
LEVELS = [
    ("🌱 اولین قدم‌ها",
     "هر عشقی با یه قدم کوچیک شروع می‌شه 🌷\nمن و تو هم همین‌جا شروع کردیم؛ با دل‌های بزرگ و لبخندهای کوچیک 💕"),
    ("🌸 دلبستگی",
     "نمی‌دونم از کی شد، ولی حالا دلم همه‌جا دنبال تو می‌گرده...\nو می‌دونم دل تو هم دنبال منه 🥹💗"),
    ("🍓 شیرینی با هم بودن",
     "با تو حتی روزای معمولی هم طعم قند می‌گیره 🍬\nما دوتا، شیرین‌ترین قصه‌ی همدیگه‌ایم 💞"),
    ("🧸 خونه‌ی دو نفره",
     "آغوش تو خونه‌ی منه، آغوش من هم خونه‌ی تو 🏡\nهر جا کنار هم باشیم، همونجا وطنه 🤍"),
    ("🌙 شب‌های ستاره‌باران",
     "ستاره‌ها فقط بهونه‌ان؛ درخشان‌ترین چیز آسمون، چشمای توئه...\nو چشمای من هم فقط برای تو می‌درخشه ✨💫"),
    ("💌 نامه‌های بی‌پست",
     "هزار جمله تو دلمونه که فقط با نگاه گفته می‌شه 💌\nخوشحالم که تو بی‌حرف می‌فهمی و من هم می‌فهمم 🫶"),
    ("🎀 دوست‌داشتنی‌ترین‌ها",
     "تو دوست‌داشتنی‌ترین آدم زندگی منی،\nو من جایی تو دلت دارم که هیچ‌کس نداره 🎀💖"),
    ("🌈 بعد از باران",
     "اگه دلخوری هم بیاد، آخرش با هم رنگین‌کمون می‌سازیم 🌈\nچون دستامون رو هیچ‌وقت ول نمی‌کنیم 🤝💕"),
    ("🕊 آرامش",
     "کنار تو دنیا آروم می‌شه، و کنار من هم تو آروم می‌شی 🕊️\nاین بزرگ‌ترین هدیه‌ی ماست 🤍"),
    ("🔥 شعله‌ی همیشگی",
     "عشق ما آتیشیه که هر روز با مهربونی گرم‌تر می‌شه، نه سردتر 🔥\nو هر دو ازش مراقبت می‌کنیم ❤️"),
    ("👑 پادشاه و ملکه‌ی دل‌ها",
     "توی قصه‌ی ما هر کی اون یکی رو خوشحال کنه تاج می‌گیره 👑\nو هر دومون هر روز تاج رو به هم می‌دیم 💗"),
    ("💎 عشق ابدی",
     "ما تا آخر این قصه هستیم؛ دست تو تو دست من،\nبرای همیشه و بیشتر از همیشه 💎♾️💞"),
]

CHOICES = {"rock": "✊ سنگ", "paper": "✋ کاغذ", "scissors": "✌️ قیچی"}
BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}

# کلمه‌هایی که تو گروه (بدون کامند) ربات بهشون جواب می‌ده
T_TRUTH = {"سوال", "حقیقت"}
T_DARE = {"جرات", "چالش"}
T_TURN = {"نوبتی", "بازی نوبتی"}
T_RPS = {"سنگ کاغذ قیچی", "سکق"}
T_TTT = {"دوز", "بازی دوز"}
T_TL = {"راست یا دروغ", "راست دروغ"}
T_SCORE = {"امتیاز", "امتیازم", "امتیاز من", "امتیازات"}
T_TOP = {"جدول", "جدول امتیاز", "جدول امتیازها", "رتبه", "رتبه بندی"}
T_HELP = {"راهنما", "کمک", "help"}
T_MENU = {"بازی", "منو", "ربات", "شروع"}

MENU_TEXT = "🌸💕 خوش اومدین!\nیکی رو انتخاب کنین 👇"

HELP_TEXT = """❓ راهنما

💗 حقیقت / 🎀 جرات
دسته رو انتخاب کن، سوال میاد. با «➡️ بعدی» ادامه بده.

🎯 بازی نوبتی (گروه)
همه وارد می‌شن و نوبتی حقیقت یا جرات می‌گیرن. بقیه انجام دادنش رو با ✅ تأیید می‌کنن.

✊✋✌️ سنگ کاغذ قیچی
هر برد = ۳ امتیاز. با هر ۱۰۰ امتیاز و بیشتر، لول بالاتر می‌ری 💖

🏆 امتیاز و جدول
تو گروه بنویس: امتیاز یا جدول

کلمه‌های گروه:
سوال ، جرات ، نوبتی ، سنگ کاغذ قیچی ، دوز ، راست یا دروغ ، امتیاز ، جدول ، بازی"""

bot = telebot.TeleBot(TOKEN, parse_mode=None)
pending = {}    # uid -> (kind, cat): ادمینی که منتظر متن سوالشیم
games = {}      # (chat_id, message_id) -> بازی سنگ کاغذ قیچی
sessions = {}   # chat_id -> بازی نوبتی
history = {}    # (chat_id, kind, cat) -> سوال‌های دیده‌شده (برای تکرار نشدن)
kb_sent = set()  # کاربرهایی که کیبورد پایین صفحه براشون فرستاده شده
lock = threading.Lock()

# بازی‌های دو نفره
tt_games = {}   # (chat_id, message_id) -> وضعیت دوز
tl_games = {}   # (chat_id, message_id) -> وضعیت راست یا دروغ

TL_CARDS = [
    ("من تا حالا سوار هواپیما نشده‌ام.", "truth"),
    ("من می‌توانم با چشم بسته یک آهنگ را کامل بخوانم.", "truth"),
    ("من یک بار در یک روز سه بار چای خورده‌ام.", "truth"),
    ("من قهرمان مسابقات جهانی شطرنج بوده‌ام.", "lie"),
    ("من می‌توانم بدون تمرین یک زبان جدید را در یک روز یاد بگیرم.", "lie"),
    ("من تا حالا در یک فیلم سینمایی بازی کرده‌ام.", "lie"),
]


# ================= دیتابیس =================
def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c


def add_questions(kind, cat, lines, uid=0):
    """سوال‌ها رو اضافه می‌کنه؛ تکراری‌ها رد می‌شن. خروجی: (اضافه شد، تکراری)"""
    added = dup = 0
    with db() as c:
        for text in lines:
            text = text.strip()
            if not text:
                continue
            if c.execute("SELECT 1 FROM q WHERE kind=? AND cat=? AND text=?",
                         (kind, cat, text)).fetchone():
                dup += 1
                continue
            c.execute("INSERT INTO q(kind,cat,text,added_by) VALUES(?,?,?,?)",
                      (kind, cat, text, uid))
            added += 1
    return added, dup


def init():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS q(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT, cat TEXT, text TEXT, added_by INTEGER)""")
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            uid INTEGER PRIMARY KEY, adult INTEGER DEFAULT 0,
            name TEXT, score INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0, draws INTEGER DEFAULT 0)""")
        c.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")
        # برای دیتابیس نسخه‌های قبلی
        for ddl in ("ALTER TABLE users ADD COLUMN name TEXT",
                    "ALTER TABLE users ADD COLUMN score INTEGER DEFAULT 0",
                    "ALTER TABLE users ADD COLUMN wins INTEGER DEFAULT 0",
                    "ALTER TABLE users ADD COLUMN losses INTEGER DEFAULT 0",
                    "ALTER TABLE users ADD COLUMN draws INTEGER DEFAULT 0"):
            try:
                c.execute(ddl)
            except sqlite3.OperationalError:
                pass
        r = c.execute("SELECT v FROM meta WHERE k='seed'").fetchone()
        need_seed = (not r) or int(r["v"]) < SEED_VERSION
    if need_seed:
        for (kind, cat), lines in SEEDS.items():
            add_questions(kind, cat, lines)
        with db() as c:
            c.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('seed',?)",
                      (str(SEED_VERSION),))


def is_adult(uid):
    with db() as c:
        r = c.execute("SELECT adult FROM users WHERE uid=?", (uid,)).fetchone()
    return bool(r and r["adult"])


def set_adult(uid):
    with db() as c:
        c.execute("INSERT INTO users(uid,adult) VALUES(?,1) "
                  "ON CONFLICT(uid) DO UPDATE SET adult=1", (uid,))


def get_user(uid):
    keys = ("score", "wins", "losses", "draws")
    with db() as c:
        r = c.execute("SELECT score,wins,losses,draws FROM users WHERE uid=?",
                      (uid,)).fetchone()
    return {k: ((r[k] or 0) if r else 0) for k in keys}


def get_score(uid):
    return get_user(uid)["score"]


def upd_user(uid, name, pts=0, wins=0, losses=0, draws=0):
    """امتیاز و آمار کاربر رو زیاد می‌کنه؛ امتیاز جدید رو برمی‌گردونه."""
    with db() as c:
        c.execute(
            "INSERT INTO users(uid,name,score,wins,losses,draws) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(uid) DO UPDATE SET name=excluded.name, "
            "score=COALESCE(score,0)+excluded.score, "
            "wins=COALESCE(wins,0)+excluded.wins, "
            "losses=COALESCE(losses,0)+excluded.losses, "
            "draws=COALESCE(draws,0)+excluded.draws",
            (uid, name, pts, wins, losses, draws))
        return c.execute("SELECT score FROM users WHERE uid=?", (uid,)).fetchone()["score"]


def pick_question(chat_id, kind, cat, uid):
    """یه سوال رندوم؛ تا همه‌ی سوال‌های دسته دیده نشن، تکراری نمیاد."""
    cats = [k for k in CATS if k != "adult" or is_adult(uid)] if cat == "rnd" else [cat]
    ph = ",".join("?" * len(cats))
    with db() as c:
        ids = [r["id"] for r in c.execute(
            f"SELECT id FROM q WHERE kind=? AND cat IN ({ph})", (kind, *cats))]
        if not ids:
            return None
        seen = history.setdefault((chat_id, kind, cat), set())
        pool = [i for i in ids if i not in seen]
        if not pool:
            seen.clear()
            pool = ids
        qid = random.choice(pool)
        seen.add(qid)
        return c.execute("SELECT * FROM q WHERE id=?", (qid,)).fetchone()


def page_rows(kind, cat, page, desc=False):
    with db() as c:
        total = c.execute("SELECT COUNT(*) FROM q WHERE kind=? AND cat=?",
                          (kind, cat)).fetchone()[0]
        pages = max(1, -(-total // PER))
        page = max(0, min(page, pages - 1))
        order = "DESC" if desc else "ASC"
        rows = c.execute(
            f"SELECT * FROM q WHERE kind=? AND cat=? ORDER BY id {order} "
            "LIMIT ? OFFSET ?", (kind, cat, PER, page * PER)).fetchall()
    return rows, page, pages, total


def stats_text():
    lines = ["📊 آمار\n"]
    with db() as c:
        for kind, kl in KINDS.items():
            parts = []
            for cat, cl in CATS.items():
                n = c.execute("SELECT COUNT(*) FROM q WHERE kind=? AND cat=?",
                              (kind, cat)).fetchone()[0]
                parts.append(f"{cl}: {n}")
            lines.append(f"{kl}\n" + " | ".join(parts) + "\n")
        users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        players = c.execute("SELECT COUNT(*) FROM users WHERE score>0").fetchone()[0]
        total = c.execute("SELECT COALESCE(SUM(score),0) FROM users").fetchone()[0]
    lines.append(f"👥 کاربرها: {users}   🎮 امتیازدارها: {players}")
    lines.append(f"⭐ مجموع امتیازها: {total}")
    return "\n".join(lines)


# ================= لول و امتیاز =================
def level_info(score):
    lvl, rem = 1, score
    while rem >= lvl * LEVEL_STEP:
        rem -= lvl * LEVEL_STEP
        lvl += 1
    return lvl, rem, lvl * LEVEL_STEP


def level_data(lvl):
    return LEVELS[min(lvl, len(LEVELS)) - 1]


def score_text(name, u):
    lvl, rem, need = level_info(u["score"])
    title, love = level_data(lvl)
    filled = int(rem / need * 10)
    bar = "💗" * filled + "🤍" * (10 - filled)
    stats = ""
    if u["wins"] + u["losses"] + u["draws"] > 0:
        stats = (f"🎮 برد {u['wins']}  •  مساوی {u['draws']}  •  باخت {u['losses']}\n")
    return (f"🏆 {name}\n\n"
            f"⭐ امتیاز کل: {u['score']}\n"
            f"{stats}"
            f"💖 لول {lvl} — {title}\n"
            f"{bar}  {rem}/{need}\n\n"
            f"{love}")


def levelup_text(name, lvl):
    title, love = level_data(lvl)
    return f"🎉 {name} به لول {lvl} رسید!\n💖 {title}\n\n{love}"


def top_text():
    with db() as c:
        rows = c.execute("SELECT name, score FROM users WHERE score>0 "
                         "ORDER BY score DESC LIMIT 10").fetchall()
    if not rows:
        return "هنوز کسی امتیازی نگرفته 😅 یه دست سنگ کاغذ قیچی بزنین!"
    medals = ["🥇", "🥈", "🥉"]
    lines = []
    for i, r in enumerate(rows):
        mark = medals[i] if i < 3 else f"{i + 1}."
        lines.append(f"{mark} {r['name'] or 'ناشناس'} — {r['score']} امتیاز "
                     f"(لول {level_info(r['score'])[0]})")
    return "🏅 جدول امتیازها\n\n" + "\n".join(lines)


def send_score(chat_id, user):
    name = user.first_name or "بازیکن"
    kb = KB()
    kb.add(Btn("🏅 جدول امتیازها", callback_data="sc:top"))
    bot.send_message(chat_id, score_text(name, get_user(user.id)), reply_markup=kb)


# ================= کیبوردها =================
def main_kb(uid, private=True):
    kb = KB()
    kb.row(Btn(KINDS["truth"], callback_data="k:truth"),
           Btn(KINDS["dare"], callback_data="k:dare"))
    if not private:
        kb.add(Btn("🎯 بازی نوبتی (گروهی)", callback_data="ss:new"))
    kb.add(Btn("✊✋✌️ سنگ کاغذ قیچی", callback_data="rp:new"))
    kb.row(Btn("⭕❌ دوز دو نفره", callback_data="tt:new"),
           Btn("🎭 راست یا دروغ", callback_data="tl:new"))
    kb.row(Btn("🏆 امتیاز من", callback_data="sc:me"),
           Btn("🏅 جدول", callback_data="sc:top"))
    row = [Btn("❓ راهنما", callback_data="help")]
    if uid in ADMINS and private:
        row.append(Btn("🛠 ادمین", callback_data="adm"))
    kb.row(*row)
    return kb


def reply_kb():
    """کیبورد ثابت پایین صفحه (فقط پیوی)"""
    kb = RKB(resize_keyboard=True)
    kb.row("💗 حقیقت", "🎀 جرات")
    kb.row("✊✋✌️ سنگ کاغذ قیچی")
    kb.row("⭕❌ دوز", "🎭 راست یا دروغ")
    kb.row("🏆 امتیاز من", "🏅 جدول", "🏠 منو")
    return kb


def cats_kb(kind, prefix, back="menu", all_btn=False):
    kb = KB()
    if all_btn:
        kb.add(Btn("🎲 همه‌ی دسته‌ها", callback_data=f"{prefix}:{kind}:rnd"))
    kb.row(Btn(CATS["love"], callback_data=f"{prefix}:{kind}:love"),
           Btn(CATS["friend"], callback_data=f"{prefix}:{kind}:friend"))
    kb.row(Btn(CATS["emo"], callback_data=f"{prefix}:{kind}:emo"),
           Btn(CATS["adult"], callback_data=f"{prefix}:{kind}:adult"))
    kb.add(Btn("🏠 منو" if back == "menu" else "⬅️ برگشت", callback_data=back))
    return kb


def kinds_kb(prefix, back):
    kb = KB()
    kb.row(Btn(KINDS["truth"], callback_data=f"{prefix}:truth"),
           Btn(KINDS["dare"], callback_data=f"{prefix}:dare"))
    kb.add(Btn("⬅️ برگشت", callback_data=back))
    return kb


def admin_kb():
    kb = KB()
    kb.add(Btn("➕ افزودن سوال", callback_data="ak"))
    kb.add(Btn("📋 لیست / حذف سوال‌ها", callback_data="al"))
    kb.row(Btn("📊 آمار", callback_data="st"),
           Btn("💾 بکاپ دیتابیس", callback_data="bk"))
    kb.add(Btn("🏠 منو", callback_data="menu"))
    return kb


def ans(c, text=None, alert=False):
    try:
        bot.answer_callback_query(c.id, text=text, show_alert=alert)
    except Exception:
        pass


def edit(c, text, kb=None):
    try:
        bot.edit_message_text(text, c.message.chat.id, c.message.message_id,
                              reply_markup=kb)
    except Exception:
        pass  # مثلا وقتی متن دقیقا همونه


# ================= بخش سوال‌ها =================
def ask18(c, kind, cat):
    kb = KB()
    kb.add(Btn("✅ بالای ۱۸ سال هستم", callback_data=f"ok18:{kind}:{cat}"))
    kb.add(Btn("🏠 منو", callback_data="menu"))
    edit(c, "🔞 این بخش مخصوص افراد بالای ۱۸ ساله.", kb)


def show_question(c, kind, cat, new_message=False):
    uid = c.from_user.id
    if cat == "adult" and not is_adult(uid):
        return ask18(c, kind, cat)
    r = pick_question(c.message.chat.id, kind, cat, uid)
    kb = KB()
    if not r:
        kb.row(Btn("🗂 دسته‌ها", callback_data=f"k:{kind}"),
               Btn("🏠 منو", callback_data="menu"))
        return edit(c, "هنوز سوالی برای این بخش ثبت نشده 😅", kb)
    mark = lambda k: ("✅ " if k == kind else "") + KINDS[k]
    kb.add(Btn("➡️ بعدی", callback_data=f"c:{kind}:{cat}"))
    kb.row(Btn(mark("truth"), callback_data=f"c:truth:{cat}"),
           Btn(mark("dare"), callback_data=f"c:dare:{cat}"))
    kb.row(Btn("🎯 انتخاب دستی", callback_data=f"pl:{kind}:{cat}:0"),
           Btn("🗂 دسته‌ها", callback_data=f"k:{kind}"))
    kb.add(Btn("🏠 منو", callback_data="menu"))
    text = f"{KINDS[kind]} | {CATS[r['cat']]}\n\n{r['text']}"
    if new_message:
        bot.send_message(c.message.chat.id, text, reply_markup=kb)
    else:
        edit(c, text, kb)


def render_list(c, kind, cat, page, admin=False):
    rows, page, pages, total = page_rows(kind, cat, page, desc=admin)
    head = (f"{KINDS[kind]} | {CATS[cat]}  ({total} سوال)\n"
            f"صفحه {page + 1} از {pages}\n\n"
            + ("" if admin else "یه شماره رو بزن 👇\n\n"))
    back = f"lc:{kind}" if admin else f"c:{kind}:{cat}"
    kb = KB()
    if not rows:
        kb.add(Btn("⬅️ برگشت", callback_data=back))
        return edit(c, head + "هنوز سوالی نیست 😅", kb)
    body = "\n\n".join(f"{i}) {r['text']}" for i, r in enumerate(rows, 1))
    if admin:
        btns = [Btn(f"🗑 {i}", callback_data=f"dl:{r['id']}:{kind}:{cat}:{page}")
                for i, r in enumerate(rows, 1)]
    else:
        btns = [Btn(str(i), callback_data=f"pk:{r['id']}:{kind}:{cat}:{page}")
                for i, r in enumerate(rows, 1)]
    kb.row(*btns)
    nav_prefix = "ls" if admin else "pl"
    nav = []
    if page > 0:
        nav.append(Btn("◀️ قبلی", callback_data=f"{nav_prefix}:{kind}:{cat}:{page - 1}"))
    if page < pages - 1:
        nav.append(Btn("بعدی ▶️", callback_data=f"{nav_prefix}:{kind}:{cat}:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.add(Btn("⬅️ برگشت", callback_data=back))
    edit(c, (head + body)[:4000], kb)


# ================= سنگ کاغذ قیچی =================
def pname(p):
    return "🤖 ربات" if p == "bot" else p[1]


def rps_invite_screen(g):
    kb = KB()
    kb.row(Btn("🤝 من بازی می‌کنم", callback_data="rp:join"),
           Btn("🤖 با ربات", callback_data="rp:bot"))
    return (f"✊✋✌️ سنگ کاغذ قیچی\n\n{g['p1'][1]} بازی رو شروع کرد 💕\n"
            "منتظر حریف...", kb)


def rps_pick_screen(g):
    n1, n2 = pname(g["p1"]), pname(g["p2"])
    s1 = "✅" if g["c1"] else "⏳"
    s2 = "😎" if g["p2"] == "bot" else ("✅" if g["c2"] else "⏳")
    kb = KB()
    kb.row(*[Btn(v, callback_data=f"rp:p:{k}") for k, v in CHOICES.items()])
    return (f"✊✋✌️ {n1} 🆚 {n2}\n\nهر دو نفر انتخاب کنین (انتخاب‌ها مخفیه 🤫)\n"
            f"{s1} {n1}\n{s2} {n2}", kb)


def rps_finish(g):
    a, b = g["c1"], g["c2"]
    p1, p2 = g["p1"], g["p2"]
    text = (f"✊✋✌️ نتیجه\n\n{pname(p1)}: {CHOICES[a]}\n"
            f"{pname(p2)}: {CHOICES[b]}\n\n")
    if a == b:
        text += "🤝 مساوی شد! دوباره امتحان کنین 💕"
        for p in (p1, p2):
            if p != "bot":
                upd_user(p[0], p[1], draws=1)
    else:
        winner, loser = (p1, p2) if BEATS[a] == b else (p2, p1)
        if loser != "bot":
            upd_user(loser[0], loser[1], losses=1)
        if winner == "bot":
            text += "🤖 ربات این دفعه برد! تلافی کن 😜"
        else:
            old = get_score(winner[0])
            new = upd_user(winner[0], winner[1], WIN_POINTS, wins=1)
            text += f"🏆 {winner[1]} برد! +{WIN_POINTS} امتیاز 🎉"
            old_lvl, new_lvl = level_info(old)[0], level_info(new)[0]
            if new_lvl > old_lvl:
                text += "\n\n" + levelup_text(winner[1], new_lvl)
    kb = KB()
    kb.row(Btn("🔁 دوباره", callback_data="rp:again"),
           Btn("🏆 امتیازم", callback_data="sc:me"))
    return text, kb


def rps_open(chat, user, msg=None):
    """شروع بازی: تو پیوی با ربات، تو گروه منتظر حریف."""
    name = user.first_name or "بازیکن"
    g = {"p1": (user.id, name), "p2": None, "c1": None, "c2": None}
    if chat.type == "private":
        g["p2"] = "bot"
        text, kb = rps_pick_screen(g)
    else:
        text, kb = rps_invite_screen(g)
    if msg is not None:
        try:
            bot.edit_message_text(text, msg.chat.id, msg.message_id, reply_markup=kb)
        except Exception:
            return
        key = (msg.chat.id, msg.message_id)
    else:
        sent = bot.send_message(chat.id, text, reply_markup=kb)
        key = (chat.id, sent.message_id)
    with lock:
        games[key] = g
        if len(games) > 3000:
            for k in list(games)[:500]:
                games.pop(k, None)


def rps_cb(c, d):
    act = d[1]
    uid = c.from_user.id
    name = c.from_user.first_name or "بازیکن"

    if act == "new":
        ans(c)
        return rps_open(c.message.chat, c.from_user, msg=c.message)

    key = (c.message.chat.id, c.message.message_id)
    toast, alert, out = None, False, None
    with lock:
        g = games.get(key)
        if g is None:
            toast, alert = "این بازی تموم شده؛ یه بازی جدید شروع کن 💕", True

        elif act == "join":
            if g["p2"] is not None:
                toast = "حریف قبلاً اومده 😉"
            elif uid == g["p1"][0]:
                toast = "باید یه نفر دیگه بیاد 😄 یا «با ربات» رو بزن"
            else:
                g["p2"] = (uid, name)
                out = rps_pick_screen(g)

        elif act == "bot":
            if uid != g["p1"][0]:
                toast, alert = "فقط شروع‌کننده می‌تونه با ربات بازی کنه", True
            elif g["p2"] is not None:
                toast = "بازی شروع شده 😉"
            else:
                g["p2"] = "bot"
                out = rps_pick_screen(g)

        elif act == "p":
            choice = d[2]
            p1, p2 = g["p1"], g["p2"]
            slot = None
            if p2 is None:
                toast = "هنوز حریفی نیومده 😅"
            elif uid == p1[0]:
                slot = "c1"
            elif p2 != "bot" and uid == p2[0]:
                slot = "c2"
            else:
                toast, alert = "این بازی برای شما نیست 😅", True
            if slot:
                if g[slot]:
                    toast = "قبلاً انتخاب کردی 😉"
                else:
                    g[slot] = choice
                    toast = f"✅ انتخابت ثبت شد: {CHOICES[choice]}"
                    if p2 == "bot":
                        g["c2"] = random.choice(list(CHOICES))
                    out = rps_finish(g) if (g["c1"] and g["c2"]) else rps_pick_screen(g)

        elif act == "again":
            p1, p2 = g["p1"], g["p2"]
            if uid == p1[0] or (p2 != "bot" and p2 and uid == p2[0]):
                g["c1"] = g["c2"] = None
                out = rps_pick_screen(g)
            else:
                toast, alert = "این بازی برای شما نیست 😅", True

    ans(c, toast, alert)
    if out:
        edit(c, out[0], out[1])


# ================= بازی نوبتی (گروه) =================
def ss_cats_kb():
    kb = KB()
    kb.add(Btn("🎲 همه‌ی دسته‌ها", callback_data="ss:cat:rnd"))
    kb.row(Btn(CATS["love"], callback_data="ss:cat:love"),
           Btn(CATS["friend"], callback_data="ss:cat:friend"))
    kb.row(Btn(CATS["emo"], callback_data="ss:cat:emo"),
           Btn(CATS["adult"], callback_data="ss:cat:adult"))
    kb.add(Btn("🏠 منو", callback_data="menu"))
    return kb


def ss_cat_label(s):
    return "🎲 همه" if s["cat"] == "rnd" else CATS[s["cat"]]


def ss_players_line(s, mark_turn=False):
    names = []
    for i, (_, n) in enumerate(s["players"]):
        names.append(("👉 " if mark_turn and i == s["turn"] else "") + n)
    return "  ·  ".join(names)


def ss_join_screen(s):
    plist = "\n".join(f"{i}) {n}" for i, (_, n) in enumerate(s["players"], 1))
    label = ("🔞 بالای ۱۸ هستم؛ من هم هستم" if s["cat"] == "adult"
             else "🙋 من هم هستم")
    kb = KB()
    kb.add(Btn(label, callback_data="ss:join"))
    kb.row(Btn("▶️ شروع", callback_data="ss:go"),
           Btn("❌ لغو", callback_data="ss:end"))
    return (f"🎯 بازی نوبتی | {ss_cat_label(s)}\n\nبازیکن‌ها:\n{plist}\n\n"
            "حداقل ۲ نفر لازمه. وقتی همه اومدن «شروع» رو بزنین 💕", kb)


def ss_turn_screen(s, note=""):
    n = s["players"][s["turn"]][1]
    kb = KB()
    kb.row(Btn(KINDS["truth"], callback_data="ss:t:truth"),
           Btn(KINDS["dare"], callback_data="ss:t:dare"))
    kb.add(Btn("🎲 رندوم", callback_data="ss:t:rnd"))
    kb.add(Btn("🛑 پایان بازی", callback_data="ss:end"))
    return (f"{note}🎯 نوبت {n} ✨\nحقیقت یا جرات؟\n\n"
            f"{ss_players_line(s, True)}", kb)


def ss_q_screen(s, kind, r):
    n = s["players"][s["turn"]][1]
    kb = KB()
    kb.add(Btn(f"✅ انجام شد" + (f" (+{DONE_POINTS})" if DONE_POINTS else ""),
               callback_data="ss:done"))
    kb.row(Btn("🔄 یکی دیگه", callback_data="ss:more"),
           Btn("⏭ رد کردم", callback_data="ss:skip"))
    return (f"🎯 نوبت {n}\n{KINDS[kind]} | {CATS[r['cat']]}\n\n{r['text']}\n\n"
            "👀 بقیه‌ی بازیکن‌ها با ✅ تأیید می‌کنن", kb)


def ss_next(s, note=""):
    s["turn"] = (s["turn"] + 1) % len(s["players"])
    s["state"] = "turn"
    s["kind"] = None
    return ss_turn_screen(s, note)


def ss_end_screen(s):
    lines = [f"{n}: +{s['pts'].get(u, 0)}" for u, n in s["players"]]
    text = "🛑 بازی نوبتی تموم شد 💕"
    if DONE_POINTS:
        text += "\n\nامتیازهای این دور:\n" + "\n".join(lines)
    kb = KB()
    kb.row(Btn("🎯 دور جدید", callback_data="ss:new"),
           Btn("🏅 جدول", callback_data="sc:top"))
    kb.add(Btn("🏠 منو", callback_data="menu"))
    return text, kb


def ss_start_msg(chat_id):
    bot.send_message(chat_id, "🎯 بازی نوبتی\nاز کدوم دسته؟ 👇", reply_markup=ss_cats_kb())


def ss_cb(c, d):
    act = d[1]
    uid = c.from_user.id
    name = c.from_user.first_name or "بازیکن"
    chat_id = c.message.chat.id
    mid = c.message.message_id
    toast, alert, out = None, False, None

    with lock:
        if act == "new":
            if c.message.chat.type == "private":
                toast, alert = "بازی نوبتی مخصوص گروهه 💕", True
            else:
                out = ("🎯 بازی نوبتی\nاز کدوم دسته؟ 👇", ss_cats_kb())

        elif act in ("cat", "ok18"):
            cat = d[2] if act == "cat" else "adult"
            if act == "cat" and cat == "adult" and not is_adult(uid):
                kb = KB()
                kb.add(Btn("✅ بالای ۱۸ سال هستم", callback_data="ss:ok18"))
                kb.add(Btn("🏠 منو", callback_data="menu"))
                out = ("🔞 این بخش مخصوص افراد بالای ۱۸ ساله.", kb)
            else:
                if act == "ok18":
                    set_adult(uid)
                s = {"cat": cat, "players": [(uid, name)], "turn": 0,
                     "state": "join", "kind": None, "pts": {}, "mid": mid}
                sessions[chat_id] = s
                out = ss_join_screen(s)

        else:
            s = sessions.get(chat_id)
            if s is None or s["mid"] != mid:
                toast, alert = "این بازی تموم شده یا قدیمیه؛ یه بازی نوبتی جدید شروع کن 💕", True
            else:
                ids = [p[0] for p in s["players"]]
                cur_uid, cur_name = s["players"][s["turn"]]

                if act == "join":
                    if s["state"] != "join":
                        toast = "بازی شروع شده 😉"
                    elif uid in ids:
                        toast = "تو تو بازی هستی 😉"
                    elif len(s["players"]) >= MAX_PLAYERS:
                        toast = "ظرفیت بازی پره 😅"
                    else:
                        if s["cat"] == "adult":
                            set_adult(uid)
                        s["players"].append((uid, name))
                        out = ss_join_screen(s)

                elif act == "go":
                    if uid not in ids:
                        toast = "اول باید وارد بازی بشی 😉"
                    elif s["state"] != "join":
                        toast = "بازی شروع شده 😉"
                    elif len(s["players"]) < 2:
                        toast, alert = "حداقل ۲ نفر لازمه", True
                    else:
                        s["state"] = "turn"
                        out = ss_turn_screen(s)

                elif act == "end":
                    if uid not in ids:
                        toast = "فقط بازیکن‌ها می‌تونن بازی رو تموم کنن 😉"
                    else:
                        out = ss_end_screen(s)
                        sessions.pop(chat_id, None)

                elif s["state"] == "join":
                    toast = "اول «شروع» رو بزنین 😉"

                elif act == "t":
                    if s["state"] != "turn":
                        toast = "سوال داده شده؛ انجامش بده یا رد کن 😉"
                    elif uid != cur_uid:
                        toast = f"الان نوبت {cur_name} هست 😉"
                    else:
                        kind = d[2] if d[2] != "rnd" else random.choice(list(KINDS))
                        r = pick_question(chat_id, kind, s["cat"], uid)
                        if not r:
                            toast, alert = ("برای این دسته سوالی ثبت نشده 😅 "
                                            "(ادمین باید اضافه کنه)"), True
                        else:
                            s["state"], s["kind"] = "answer", kind
                            out = ss_q_screen(s, kind, r)

                elif s["state"] != "answer":
                    toast = "اول حقیقت یا جرات رو انتخاب کن 😉"

                elif act == "more":
                    if uid != cur_uid:
                        toast = f"الان نوبت {cur_name} هست 😉"
                    else:
                        r = pick_question(chat_id, s["kind"], s["cat"], uid)
                        if r:
                            out = ss_q_screen(s, s["kind"], r)

                elif act == "skip":
                    if uid != cur_uid:
                        toast = "فقط خودش می‌تونه رد کنه 😉"
                    else:
                        out = ss_next(s, f"⏭ {cur_name} رد کرد.\n\n")

                elif act == "done":
                    if uid not in ids:
                        toast = "تو تو این بازی نیستی 😅"
                    elif uid == cur_uid:
                        toast = "تأیید با بقیه‌ست 😉 منتظر بمون"
                    else:
                        note = f"✅ {cur_name} انجامش داد!"
                        if DONE_POINTS:
                            old = get_score(cur_uid)
                            new = upd_user(cur_uid, cur_name, DONE_POINTS)
                            s["pts"][cur_uid] = s["pts"].get(cur_uid, 0) + DONE_POINTS
                            note += f" +{DONE_POINTS} امتیاز 🎉"
                            if level_info(new)[0] > level_info(old)[0]:
                                note += "\n\n" + levelup_text(cur_name, level_info(new)[0])
                        out = ss_next(s, note + "\n\n")

    ans(c, toast, alert)
    if out:
        edit(c, out[0], out[1])



# ================= بازی دوز دو نفره =================
def tt_board_text(g):
    b = g["board"]
    cells = [b[i] if b[i] else str(i + 1) for i in range(9)]
    rows = [" | ".join(cells[i:i + 3]) for i in (0, 3, 6)]
    players = f"⭕ {g['p1'][1]}  🆚  ❌ {g['p2'][1] if g['p2'] else 'منتظر حریف'}"
    turn = g["p1"][1] if g["turn"] == 0 else g["p2"][1]
    return f"⭕❌ دوز دو نفره\n\n{players}\n\n" + "\n---------\n".join(rows) + \
           (f"\n\n👉 نوبت: {turn}" if not g["finished"] else "")

def tt_kb(g):
    kb = KB()
    if not g["finished"]:
        for start in (0, 3, 6):
            kb.row(*[
                Btn(g["board"][i] or str(i + 1), callback_data=f"tt:move:{i}")
                for i in range(start, start + 3)
            ])
    if g["p2"] is None:
        kb.add(Btn("🙋 ورود به بازی", callback_data="tt:join"))
    if g["finished"]:
        kb.row(Btn("🔁 دوباره", callback_data="tt:again"),
               Btn("🏠 منو", callback_data="menu"))
    else:
        kb.add(Btn("❌ پایان بازی", callback_data="tt:end"))
    return kb

def tt_winner(g):
    wins = ((0,1,2),(3,4,5),(6,7,8),(0,3,6),(1,4,7),(2,5,8),
            (0,4,8),(2,4,6))
    for a,b,c in wins:
        if g["board"][a] and g["board"][a] == g["board"][b] == g["board"][c]:
            return g["board"][a]
    return None

def tt_open(chat, user, msg=None):
    g = {"p1": (user.id, user.first_name or "بازیکن"), "p2": None,
         "board": [None] * 9, "turn": 0, "finished": False}
    text = tt_board_text(g) + "\n\nیک نفر دیگه وارد بشه 👇"
    if msg:
        try:
            bot.edit_message_text(text, chat.id, msg.message_id, reply_markup=tt_kb(g))
            mid = msg.message_id
        except Exception:
            sent = bot.send_message(chat.id, text, reply_markup=tt_kb(g))
            mid = sent.message_id
    else:
        mid = bot.send_message(chat.id, text, reply_markup=tt_kb(g)).message_id
    tt_games[(chat.id, mid)] = g

def tt_cb(c, d):
    key = (c.message.chat.id, c.message.message_id)
    uid = c.from_user.id
    name = c.from_user.first_name or "بازیکن"
    act = d[1]
    g = tt_games.get(key)
    if act == "new":
        return tt_open(c.message.chat, c.from_user, c.message)
    if not g:
        return ans(c, "این بازی تمام شده؛ یک بازی جدید شروع کن.", True)
    if act == "join":
        if g["p2"] is not None:
            return ans(c, "حریف قبلاً وارد شده.")
        if uid == g["p1"][0]:
            return ans(c, "باید یک بازیکن دیگر وارد شود.")
        g["p2"] = (uid, name)
        edit(c, tt_board_text(g), tt_kb(g))
        return
    if act == "end":
        if uid not in [g["p1"][0], g["p2"][0] if g["p2"] else -1]:
            return ans(c, "فقط بازیکن‌ها می‌توانند بازی را ببندند.", True)
        g["finished"] = True
        edit(c, "🛑 بازی توسط بازیکن پایان یافت.", tt_kb(g))
        return
    if act == "again":
        if uid not in [g["p1"][0], g["p2"][0] if g["p2"] else -1]:
            return ans(c, "این بازی برای شما نیست.", True)
        g.update(board=[None] * 9, turn=0, finished=False)
        edit(c, tt_board_text(g), tt_kb(g))
        return
    if act == "move":
        if not g["p2"]:
            return ans(c, "اول باید یک حریف وارد شود.")
        player = g["p1"] if g["turn"] == 0 else g["p2"]
        if uid != player[0]:
            return ans(c, "الان نوبت حریف است.")
        idx = int(d[2])
        if g["board"][idx]:
            return ans(c, "این خانه قبلاً انتخاب شده.")
        mark = "⭕" if g["turn"] == 0 else "❌"
        g["board"][idx] = mark
        winner = tt_winner(g)
        if winner:
            winner_player = g["p1"] if winner == "⭕" else g["p2"]
            upd_user(winner_player[0], winner_player[1], pts=3, wins=1)
            g["finished"] = True
            text = tt_board_text(g) + f"\n\n🏆 {winner_player[1]} برنده شد! +۳ امتیاز"
        elif all(g["board"]):
            g["finished"] = True
            upd_user(g["p1"][0], g["p1"][1], draws=1)
            upd_user(g["p2"][0], g["p2"][1], draws=1)
            text = tt_board_text(g) + "\n\n🤝 بازی مساوی شد!"
        else:
            g["turn"] = 1 - g["turn"]
            text = tt_board_text(g)
        edit(c, text, tt_kb(g))

# ================= بازی راست یا دروغ دو نفره =================
def tl_screen(g):
    speaker = g["p1"][1]
    guesser = g["p2"][1] if g["p2"] else "منتظر حریف"
    text = f"🎭 راست یا دروغ دو نفره\n\nگوینده: {speaker}\nحدس‌زن: {guesser}\n\n"
    if g["statement"]:
        text += f"🗣 جمله:\n{g['statement']}\n\n"
    if g["finished"]:
        text += "بازی تمام شد."
    elif g["p2"] is None:
        text += "یک نفر به‌عنوان حدس‌زن وارد شود."
    elif g["phase"] == "truth":
        text += "گوینده مشخص کند جمله راست است یا دروغ."
    else:
        text += "حدس‌زن انتخاب کند: راست یا دروغ؟"
    return text

def tl_kb(g):
    kb = KB()
    if g["p2"] is None:
        kb.add(Btn("🙋 ورود به بازی", callback_data="tl:join"))
    elif not g["statement"]:
        kb.add(Btn("🟢 جمله راست است", callback_data="tl:set:truth"))
        kb.add(Btn("🔴 جمله دروغ است", callback_data="tl:set:lie"))
    elif g["phase"] == "guess":
        kb.row(Btn("🟢 راست", callback_data="tl:guess:truth"),
               Btn("🔴 دروغ", callback_data="tl:guess:lie"))
    elif g["finished"]:
        kb.add(Btn("🔁 دوباره", callback_data="tl:again"))
    kb.add(Btn("❌ پایان", callback_data="tl:end"))
    return kb

def tl_open(chat, user, msg=None):
    g = {"p1": (user.id, user.first_name or "بازیکن"), "p2": None,
         "statement": None, "truth": None, "phase": "truth", "finished": False}
    text = tl_screen(g)
    if msg:
        try:
            bot.edit_message_text(text, chat.id, msg.message_id, reply_markup=tl_kb(g))
            mid = msg.message_id
        except Exception:
            mid = bot.send_message(chat.id, text, reply_markup=tl_kb(g)).message_id
    else:
        mid = bot.send_message(chat.id, text, reply_markup=tl_kb(g)).message_id
    tl_games[(chat.id, mid)] = g

def tl_cb(c, d):
    key = (c.message.chat.id, c.message.message_id)
    uid = c.from_user.id
    name = c.from_user.first_name or "بازیکن"
    act = d[1]
    g = tl_games.get(key)
    if act == "new":
        return tl_open(c.message.chat, c.from_user, c.message)
    if not g:
        return ans(c, "این بازی تمام شده؛ یک بازی جدید شروع کن.", True)
    players = [g["p1"][0], g["p2"][0] if g["p2"] else -1]
    if act == "join":
        if g["p2"]:
            return ans(c, "حریف قبلاً وارد شده.")
        if uid == g["p1"][0]:
            return ans(c, "یک نفر دیگر باید وارد شود.")
        g["p2"] = (uid, name)
        edit(c, tl_screen(g), tl_kb(g))
    elif act == "set":
        if uid != g["p1"][0] or g["p2"] is None:
            return ans(c, "فقط گوینده می‌تواند این کار را انجام دهد.")
        if g["statement"]:
            return ans(c, "جمله قبلاً ثبت شده.")
        g["truth"] = d[2]
        g["statement"] = random.choice([x[0] for x in TL_CARDS])
        g["phase"] = "guess"
        edit(c, tl_screen(g), tl_kb(g))
    elif act == "guess":
        if uid != g["p2"][0]:
            return ans(c, "فقط حدس‌زن می‌تواند جواب بدهد.")
        if d[2] not in ("truth", "lie"):
            return ans(c, "انتخاب نامعتبر.")
        g["finished"] = True
        correct = d[2] == g["truth"]
        if correct:
            upd_user(g["p2"][0], g["p2"][1], pts=3, wins=1)
            result = f"🎉 حدس درست بود! +۳ امتیاز برای {g['p2'][1]}"
        else:
            upd_user(g["p1"][0], g["p1"][1], pts=3, wins=1)
            result = f"😄 حدس اشتباه بود! +۳ امتیاز برای {g['p1'][1]}"
        edit(c, tl_screen(g) + f"\n\n{result}", tl_kb(g))
    elif act == "again":
        if uid not in players:
            return ans(c, "این بازی برای شما نیست.")
        g.update(statement=None, truth=None, phase="truth", finished=False)
        edit(c, tl_screen(g), tl_kb(g))
    elif act == "end":
        if uid not in players:
            return ans(c, "این بازی برای شما نیست.")
        g["finished"] = True
        edit(c, "🛑 بازی پایان یافت.", tl_kb(g))

# ================= پیام‌های متنی =================
def norm(t):
    for a, b in (("ي", "ی"), ("ك", "ک"), ("أ", "ا"), ("إ", "ا"), ("\u200c", " ")):
        t = t.replace(a, b)
    t = re.sub(r"[^\w\s/@]", "", t)      # حذف ایموجی و علامت‌ها
    return " ".join(t.split())


def send_menu(chat_id, uid, private):
    bot.send_message(chat_id, MENU_TEXT, reply_markup=main_kb(uid, private))


def welcome(m):
    uid = m.from_user.id
    kb_sent.add(uid)
    bot.send_message(
        m.chat.id,
        "🌸💕 سلام! از دکمه‌های پایین صفحه هم می‌تونی استفاده کنی 👇",
        reply_markup=reply_kb())
    send_menu(m.chat.id, uid, True)


@bot.message_handler(content_types=["text"])
def on_text(m):
    try:
        handle_text(m)
    except Exception:
        traceback.print_exc()


def handle_text(m):
    uid = m.from_user.id
    private = m.chat.type == "private"
    t = norm(m.text or "")

    # ادمین در حال افزودن سوال (فقط پیوی)
    if private and uid in ADMINS and uid in pending:
        kind, cat = pending.pop(uid)
        added, dup = add_questions(kind, cat, m.text.split("\n"), uid)
        kb = KB()
        kb.add(Btn("➕ افزودن سوال دیگه به همین دسته",
                   callback_data=f"at:{kind}:{cat}"))
        kb.add(Btn("🛠 پنل ادمین", callback_data="adm"))
        msg = f"✅ {added} سوال اضافه شد."
        if dup:
            msg += f"\n♻️ {dup} تا تکراری بود و رد شد."
        return bot.send_message(m.chat.id, msg, reply_markup=kb)

    if t in T_TRUTH or t in T_DARE:
        kind = "truth" if t in T_TRUTH else "dare"
        return bot.send_message(m.chat.id, f"{KINDS[kind]}\nدسته رو انتخاب کن 👇",
                                reply_markup=cats_kb(kind, "c", all_btn=True))

    if t in T_TURN:
        if private:
            return bot.send_message(m.chat.id, "🎯 بازی نوبتی مخصوص گروهه 💕\n"
                                    "منو رو ببین:", reply_markup=main_kb(uid, True))
        return ss_start_msg(m.chat.id)

    if t in T_RPS:
        return rps_open(m.chat, m.from_user)

    if t in T_TTT:
        return tt_open(m.chat, m.from_user)

    if t in T_TL:
        return tl_open(m.chat, m.from_user)

    if t in T_SCORE:
        target = m.from_user
        rep = m.reply_to_message
        if rep and rep.from_user and not rep.from_user.is_bot:
            target = rep.from_user   # روی پیام یکی ریپلای کنی، امتیاز اونو می‌بینی
        return send_score(m.chat.id, target)

    if t in T_TOP:
        return bot.send_message(m.chat.id, top_text())

    if t in T_HELP:
        return bot.send_message(m.chat.id, HELP_TEXT)

    is_start = t.startswith("/start")
    if private:
        # اولین بار (یا /start): کیبورد پایین صفحه هم فرستاده می‌شه
        if is_start or uid not in kb_sent:
            return welcome(m)
        return send_menu(m.chat.id, uid, True)
    # تو گروه فقط با کلمه‌های مشخص
    if t in T_MENU or is_start:
        send_menu(m.chat.id, uid, False)


# ================= دکمه‌ها =================
@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    try:
        route(c)
    except Exception:
        traceback.print_exc()
        ans(c, "یه مشکلی پیش اومد 😅 دوباره امتحان کن")


def route(c):
    uid = c.from_user.id
    d = c.data.split(":")
    a = d[0]

    if a == "rp":
        return rps_cb(c, d)
    if a == "ss":
        return ss_cb(c, d)
    if a == "tt":
        return tt_cb(c, d)
    if a == "tl":
        return tl_cb(c, d)

    ans(c)
    private = c.message.chat.type == "private"

    if a == "menu":
        pending.pop(uid, None)
        edit(c, MENU_TEXT, main_kb(uid, private))

    elif a == "help":
        kb = KB()
        kb.add(Btn("🏠 منو", callback_data="menu"))
        edit(c, HELP_TEXT, kb)

    elif a == "k":
        edit(c, f"{KINDS[d[1]]}\nدسته رو انتخاب کن 👇",
             cats_kb(d[1], "c", all_btn=True))

    elif a == "c":
        is_next = "➡️ بعدی" in (c.message.text or "")
        show_question(c, d[1], d[2], new_message=is_next)

    elif a == "ok18":
        set_adult(uid)
        show_question(c, d[1], d[2])

    elif a == "pl":
        kind, cat, page = d[1], d[2], int(d[3])
        if cat == "adult" and not is_adult(uid):
            return ask18(c, kind, cat)
        render_list(c, kind, cat, page)

    elif a == "pk":
        qid, kind, cat, page = int(d[1]), d[2], d[3], int(d[4])
        if cat == "adult" and not is_adult(uid):
            return ask18(c, kind, cat)
        with db() as cn:
            r = cn.execute("SELECT * FROM q WHERE id=?", (qid,)).fetchone()
        kb = KB()
        kb.row(Btn("📋 برگشت به لیست", callback_data=f"pl:{kind}:{cat}:{page}"),
               Btn("🎲 رندوم", callback_data=f"c:{kind}:{cat}"))
        kb.add(Btn("🏠 منو", callback_data="menu"))
        if not r:
            return edit(c, "این سوال دیگه نیست 😅", kb)
        edit(c, f"{KINDS[kind]} | {CATS[cat]}\n\n{r['text']}", kb)

    elif a == "sc":
        if d[1] == "me":
            send_score(c.message.chat.id, c.from_user)
        else:
            bot.send_message(c.message.chat.id, top_text())

    # ----- فقط ادمین -----
    elif uid not in ADMINS:
        return

    elif a == "adm":
        pending.pop(uid, None)
        edit(c, "🛠 پنل ادمین", admin_kb())

    elif a == "ak":
        edit(c, "نوع سوال؟", kinds_kb("ac", "adm"))

    elif a == "ac":
        edit(c, "دسته؟", cats_kb(d[1], "at", back="ak"))

    elif a == "at":
        kind, cat = d[1], d[2]
        pending[uid] = (kind, cat)
        kb = KB()
        kb.add(Btn("❌ لغو", callback_data="adm"))
        edit(c, f"{KINDS[kind]} | {CATS[cat]}\n\nسوال رو بفرست.\n"
                "چند تا سوال؟ هر کدوم رو تو یه خط بنویس.", kb)

    elif a == "al":
        edit(c, "کدوم نوع؟", kinds_kb("lc", "adm"))

    elif a == "lc":
        edit(c, "کدوم دسته؟", cats_kb(d[1], "ls", back="al"))

    elif a == "ls":
        render_list(c, d[1], d[2], int(d[3]) if len(d) > 3 else 0, admin=True)

    elif a == "dl":
        with db() as cn:
            cn.execute("DELETE FROM q WHERE id=?", (int(d[1]),))
        render_list(c, d[2], d[3], int(d[4]), admin=True)

    elif a == "st":
        edit(c, stats_text(), admin_kb())

    elif a == "bk":
        try:
            with open(DB, "rb") as f:
                bot.send_document(c.message.chat.id, f, caption="💾 بکاپ دیتابیس (td.db)")
        except Exception:
            traceback.print_exc()
            bot.send_message(c.message.chat.id, "❌ بکاپ ناموفق بود.")


if __name__ == "__main__":
    init()
    print("Bot is running...")
    bot.infinity_polling()

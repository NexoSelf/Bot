# -*- coding: utf-8 -*-
# ⚙️ تنظیمات ربات
#
# روی Railway: توکن و ادمین‌ها رو تو بخش Variables بذار (BOT_TOKEN و ADMINS)
#              و این فایل رو دست نزن.
# روی Termux / کامپیوتر: مقدارهای پایین رو مستقیم پر کن.
import os
import re

# توکن ربات (از @BotFather). محرمانه‌ست؛ تو GitHub نذارش، تو Variables ریلوی بذار.
TOKEN = os.environ.get("BOT_TOKEN") or os.environ.get("TOKEN") or "PUT_YOUR_BOT_TOKEN"

# آیدی عددی ادمین‌ها (از @userinfobot). چند نفر؟ با کاما جدا کن.
# روی Railway مثلا:  ADMINS = 111111111,222222222
_raw = os.environ.get("ADMINS")
if _raw:
    ADMINS = {int(x) for x in re.split(r"[,\s]+", _raw) if x.isdigit()}
else:
    ADMINS = {123456789}

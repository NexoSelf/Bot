#!/usr/bin/env bash
# اجرای ربات (اگه به هر دلیلی بسته شد، خودش دوباره بالا میاد)
cd "$(dirname "$0")"

PY=python
command -v python >/dev/null 2>&1 || PY=python3

# تو Termux نذار گوشی ربات رو بخوابونه
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock

while true; do
  $PY bot.py
  code=$?
  # کد ۲ یعنی مشکل تنظیمات (توکن/کانفیگ)؛ تکرار فایده نداره
  [ "$code" -eq 2 ] && break
  echo "⚠️ ربات متوقف شد؛ ۵ ثانیه بعد دوباره اجرا می‌شه (توقف: Ctrl+C)"
  sleep 5
done

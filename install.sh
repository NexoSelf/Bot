#!/usr/bin/env bash
# نصب پیش‌نیازها (Termux / لینوکس / مک)
set -e
cd "$(dirname "$0")"

if command -v pkg >/dev/null 2>&1; then
  echo "📱 Termux پیدا شد؛ نصب پایتون..."
  pkg update -y
  pkg install -y python
fi

PY=python
command -v python >/dev/null 2>&1 || PY=python3

echo "📦 نصب کتابخونه‌ها..."
$PY -m pip install --upgrade pip
$PY -m pip install -r requirements.txt

echo
echo "✅ نصب تموم شد!"
echo "حالا فایل config.py رو باز کن، توکن و آیدی ادمین رو بذار، بعد بزن:  bash run.sh"

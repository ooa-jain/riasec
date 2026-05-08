#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# startup.sh  —  Run this once on your Hostinger server to start the app
# Usage:  chmod +x startup.sh && ./startup.sh
# ─────────────────────────────────────────────────────────────────────────────

set -e  # stop on first error

echo "==> Installing dependencies..."
pip install -r requirements.txt --quiet

echo "==> Checking .env..."
if [ ! -f .env ]; then
  echo "ERROR: .env file not found. Copy .env.example to .env and fill in your values."
  exit 1
fi

echo "==> Starting Gunicorn..."
gunicorn -c gunicorn.conf.py app:app

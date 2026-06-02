#!/usr/bin/env bash
# exit on error
set -o errexit

# Install python dependencies
pip install -r requirements.txt

# Install playwright browser
playwright install chromium

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
python manage.py migrate

#!/bin/bash
# One-time setup of Spice Pantry on PythonAnywhere (free plan).
# Run it in a PythonAnywhere "Bash console", from the unzipped folder:
#     cd ~/spice-pantry && bash deploy/pythonanywhere/setup.sh
#
# It asks for your MySQL password (typing is hidden) and writes it only to ~/spice-pantry/.env.
# Safe to run again: it keeps an existing .env and skips the data import once done.
set -euo pipefail

APP_DIR="$HOME/spice-pantry"
VENV="$HOME/.virtualenvs/spicepantry"
DATA_FILE="$APP_DIR/deploy-data/spicepantry-data.json"
DB_NAME="${USER}\$spicepantry"
DB_HOST="${USER}.mysql.pythonanywhere-services.com"
export DJANGO_SETTINGS_MODULE=config.settings.pythonanywhere

cd "$APP_DIR"
echo "==> Spice Pantry setup for ${USER}.pythonanywhere.com"

# 1. Python environment
PY=""
for v in 3.12 3.13 3.11; do
  if command -v "python$v" >/dev/null 2>&1; then PY="python$v"; break; fi
done
[ -n "$PY" ] || { echo "No Python 3.11-3.13 found"; exit 1; }
if [ ! -d "$VENV" ]; then
  echo "==> Creating virtualenv with $PY (pick the same Python version on the Web tab)"
  "$PY" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
echo "==> Installing packages (a few minutes the first time)"
pip install --quiet --upgrade pip
pip install --quiet -r deploy/pythonanywhere/requirements.txt

# 2. Settings file (.env), written once
if [ ! -f .env ]; then
  echo
  echo "Databases tab: the MySQL password you set, and a database named 'spicepantry' must exist."
  read -rsp "MySQL password: " DB_PASSWORD; echo
  echo "Choose a private admin address, e.g. sp-portal-7k3q9 (letters, numbers and dashes)."
  read -rp "Admin path: " ADMIN_PATH
  DB_PASSWORD="$DB_PASSWORD" ADMIN_PATH="$ADMIN_PATH" DB_NAME="$DB_NAME" DB_HOST="$DB_HOST" python - <<'PY'
import os, re, secrets, string
from urllib.parse import quote
admin = os.environ['ADMIN_PATH'].strip().strip('/')
if not re.fullmatch(r'[A-Za-z0-9-]{6,60}', admin):
    raise SystemExit('Admin path must be 6-60 letters, numbers or dashes. Run the script again.')
alphabet = string.ascii_letters + string.digits + '-_'  # no #, $ or quotes: they confuse .env parsing
secret_key = ''.join(secrets.choice(alphabet) for _ in range(60))
url = 'mysql://{user}:{pw}@{host}/{name}'.format(
    user=quote(os.environ['USER'], safe=''), pw=quote(os.environ['DB_PASSWORD'], safe=''),
    host=os.environ['DB_HOST'], name=quote(os.environ['DB_NAME'], safe='$'))
host = f"{os.environ['USER']}.pythonanywhere.com"
with open('.env', 'w') as f:
    f.write(f"SECRET_KEY='{secret_key}'\n")
    f.write("DEBUG=False\n")
    f.write(f"DATABASE_URL={url}\n")
    f.write(f"ADMIN_URL_PATH={admin}\n")
    f.write(f"ALLOWED_HOSTS={host}\n")
    f.write(f"CSRF_TRUSTED_ORIGINS=https://{host}\n")
    f.write("SITE_NOINDEX=True\n")
print('Wrote .env (secret key generated on this server).')
PY
  unset DB_PASSWORD
fi
chmod 600 .env

# 3. Database: full Unicode, tables, data
echo "==> Preparing the database"
python manage.py shell -c "
from django.db import connection
with connection.cursor() as c:
    c.execute('ALTER DATABASE \`' + connection.settings_dict['NAME'] + '\` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
print('Database character set: utf8mb4')
"
python manage.py migrate --noinput
if [ -f "$DATA_FILE" ]; then
  echo "==> Loading products, brands, categories, photos records and staff logins"
  python manage.py loaddata "$DATA_FILE"
  rm -f "$DATA_FILE"   # it contains staff password hashes; not needed once loaded
fi

# 4. Static files (CSS, logo) for PythonAnywhere to serve
python manage.py collectstatic --noinput >/dev/null
python manage.py check

python manage.py shell -c "
from catalogue.models import Product, ProductImage
print('Products:', Product.objects.count(), '| published:', Product.objects.filter(is_published=True).count(), '| photos:', ProductImage.objects.count())
"
echo
echo "==> Done. Now finish on the Web tab (see deploy/pythonanywhere/README.md), then click Reload."
echo "    Virtualenv:   $VENV"
echo "    Source code:  $APP_DIR"
echo "    Static files: /static/ -> $APP_DIR/staticfiles    /media/ -> $APP_DIR/media"

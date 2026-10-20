# Paste this into PythonAnywhere: Web tab -> "WSGI configuration file" link -> replace everything -> Save.
import os
import sys

PROJECT_DIR = '/home/mantra1424/spice-pantry'
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings.pythonanywhere'

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()

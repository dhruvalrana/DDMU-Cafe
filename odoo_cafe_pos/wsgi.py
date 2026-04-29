"""
WSGI config for Odoo Cafe POS project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'odoo_cafe_pos.settings')

application = get_wsgi_application()

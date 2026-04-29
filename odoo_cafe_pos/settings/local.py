"""
Local development settings - Override base settings here.
"""

from .base import *

DEBUG = True

# Use SQLite for local development if PostgreSQL is not available
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Use in-memory channel layer for development without Redis
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer"
    },
}

# Allow all hosts in development
ALLOWED_HOSTS = ['*']

# CORS - Allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Add browsable API renderer in development
REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'].append(
    'rest_framework.renderers.BrowsableAPIRenderer'
)

# Disable throttling in development
REST_FRAMEWORK['DEFAULT_THROTTLE_RATES'] = {
    'anon': '10000/hour',
    'user': '100000/hour',
}

# Create logs directory
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

import os
from dotenv import load_dotenv
from datetime import timedelta
import hashlib
from pathlib import Path

load_dotenv()

class Files:
    IMAGE_EXTS = {'png', 'jpg', 'jpeg', 'heic', 'webp'}
    DOCUMENT_EXTS = {'pdf'}

    ALL_EXTS = IMAGE_EXTS.union(DOCUMENT_EXTS)

    MAP = {
        'image': {
            'exts':IMAGE_EXTS,
            'pre':'image'
            },
        'document': {
            'exts': DOCUMENT_EXTS,
            'pre':'application'
            },
    }

class Config:
    # FLASK
    SECRET_KEY = os.getenv('SECRET_KEY')
    FLASK_ENV = os.getenv('FLASK_ENV')

    # SQL LITE CONFIG
    SQLALCHEMY_DATABASE_URI = os.getenv('DB_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_POOL_RECYCLE = 299
    PERMANENT_SESSION_LIFETIME =  timedelta(days=14)

    # JWT CONFIG
    # JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    # JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    # JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    # JWT_TOKEN_LOCATION = ['cookies']

    # REDIS CONFIG
    REDIS_URL = os.getenv('REDIS_URL')
    SCHEDULER_API_ENABLED = False

    # BABEL
    BABEL_DEFAULT_LOCALE = 'en'
    # BABEL_DEFAULT_TIMEZONE = 'UTC'
    BABEL_TRANSLATION_DIRECTORIES = './translations'
    LANGUAGES = ['en', 'fr', 'es', 'de']
    # DEBUG TOOLBAR
    DEBUG_TB_INTERCEPT_REDIRECTS = False

    # Upload folder
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 10 * 1000 * 1000 #10mb
    UPLOAD_EXTENSIONS = Files.ALL_EXTS

# MONGO DB CONFIG
MONGO_URL=os.getenv('MONGO_URL')

# MAIL CONFIG
EMAIL_API_KEY = os.getenv('EMAIL_API_KEY')
EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

# LOCATION API CONFIG
LOCATIONS_API_URL="https://eu1.locationiq.com/v1"
LOCATIONS_API_KEY=os.getenv('LOCATIONS_API_KEY')
LOCATIONS_API_KEY2=os.getenv('LOCATIONS_API_KEY2')

MAPS_API_KEY = os.getenv('MAPS_API_KEY')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

# testing
hash_object = hashlib.sha256()
hash_object.update('drivers'.encode('utf-8'))
DRIVER_STATE = hash_object.hexdigest()

PROJECT_PATH = Path(__file__).resolve().parent.parent
FLASK_TESTING = False
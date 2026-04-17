import os
from pathlib import Path
from dotenv import load_dotenv

# Path to the directory where THIS file (config.py) is located
basedir = Path(__file__).resolve().parent

# Tell dotenv to look for the .env file in that specific directory
load_dotenv(basedir / '.env')

class Config:
    # Use os.environ.get to fetch from the .env file
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'fallback-for-dev-only'

class DevelopmentConfig(Config):
    pass
    
class ProductionConfig(Config):
    # In production, we should NEVER have a fallback for the secret key
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for production environment")
    
#import secrets
#print(secrets.token_hex(32))
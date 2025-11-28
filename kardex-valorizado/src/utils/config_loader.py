import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """
    Centralized configuration for the application.
    """
    # Database
    DB_URL = os.getenv("DB_URL", "sqlite:///kardex.db")
    
    # App Settings
    APP_NAME = os.getenv("APP_NAME", "Sistema Kardex Valorizado")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")
    
    @staticmethod
    def get_db_url():
        return Config.DB_URL

    @staticmethod
    def ensure_dirs():
        """Ensure necessary directories exist"""
        if not os.path.exists(Config.REPORTS_DIR):
            os.makedirs(Config.REPORTS_DIR)

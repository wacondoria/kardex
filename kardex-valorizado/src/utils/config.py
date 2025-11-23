import json
import os
from pathlib import Path

class Config:
    CONFIG_FILE = "config.json"
    
    # Default settings
    DEFAULT_CONFIG = {
        "DB_URL": "sqlite:///kardex.db",
        "MEDIA_ROOT": "user_data/media"
    }
    
    _config = None

    @classmethod
    def load_config(cls):
        """Loads configuration from file or creates default if not exists."""
        if cls._config is not None:
            return cls._config

        if not os.path.exists(cls.CONFIG_FILE):
            cls._config = cls.DEFAULT_CONFIG.copy()
            cls.save_config()
        else:
            try:
                with open(cls.CONFIG_FILE, 'r') as f:
                    cls._config = json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")
                cls._config = cls.DEFAULT_CONFIG.copy()
        
        return cls._config

    @classmethod
    def save_config(cls):
        """Saves current configuration to file."""
        try:
            with open(cls.CONFIG_FILE, 'w') as f:
                json.dump(cls._config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    @classmethod
    def get(cls, key):
        """Get a configuration value."""
        if cls._config is None:
            cls.load_config()
        return cls._config.get(key, cls.DEFAULT_CONFIG.get(key))

    @classmethod
    def get_db_url(cls):
        return cls.get("DB_URL")

    @classmethod
    def get_media_root(cls):
        return cls.get("MEDIA_ROOT")

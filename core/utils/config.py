import os
from pydantic import BaseModel
from typing import Optional

class Settings(BaseModel):
    """
    Portable configuration for LetakMaster.
    Reads from environment variables (set via .env or system).
    """
    # 1. Database Configuration
    # Fallback to local SQLite if no Postgres URL is provided
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./letak_master.db")

    # 2. Network / Hub Configuration
    # The URL where the Synology Hub API is running
    hub_url: str = os.getenv("HUB_URL", "http://localhost:8000")
    
    # 3. Path Management
    # The 'Universal Root' for the shared network drive
    # Client might use 'L:/' while Synology uses '/volume1/...'
    letak_root_path: str = os.getenv("LETAK_ROOT_PATH", os.getcwd())

    # 4. User Identity
    # Used to track who made which 'Commit' in the shared history
    user_id: str = os.getenv("LETAK_USER_ID", os.getenv("COMPUTERNAME", "unknown_user"))

# Global settings instance
settings = Settings()

def get_settings():
    return settings

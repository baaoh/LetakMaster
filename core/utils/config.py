import os
from pydantic import BaseModel
from typing import Optional

def load_env():
    """Manual .env loader. Forces values into os.environ."""
    env_path = os.path.join(os.getcwd(), ".env")
    if os.path.exists(env_path):
        print(f"Loading config from {env_path}...")
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    k = key.strip()
                    v = val.strip()
                    # FORCE override existing environment variables
                    os.environ[k] = v
                    print(f"  - Set {k}={v}")

# Load env BEFORE anything else
load_env()

class Settings(BaseModel):
    # 1. Database Configuration
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./letak_master.db")

    # 2. Network / Hub Configuration
    hub_url: str = os.getenv("HUB_URL", "http://localhost:8000")
    
    # 3. Path Management
    letak_root_path: str = os.getenv("LETAK_ROOT_PATH", os.getcwd())

    # 4. User Identity
    user_id: str = os.getenv("LETAK_USER_ID", os.getenv("COMPUTERNAME", "unknown_user"))

# Global settings instance
settings = Settings()

def get_settings():
    return settings

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

# 1. Locate the .env file in the project root directory
base_dir = Path(__file__).resolve().parent.parent
env_path = base_dir / ".env"

# 2. Load environment variables from .env in to memory
load_dotenv(dotenv_path=env_path)

# 3. Retrieve the connection string securely from the environment variable
DATABASE_URL = os.getenv("SUPABASE_DB_URL")
FRED_API_KEY = os.getenv("FRED_API_KEY")

if not DATABASE_URL:
    raise ValueError("CRITICAL: SUPABASE_DB_URL is not set in the .env file.")
if not FRED_API_KEY:
    raise ValueError("CRITICAL: FRED_API_KEY is not set in the .env file.")


# 4. Initialise the SQLAlchemy engine
# pool_pre_ping=True automatically tests connections before using them
db_engine = create_engine(DATABASE_URL, pool_pre_ping=True)

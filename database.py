import os
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Load environment variables from .env file (optional)
# This will search for a .env file in the current directory
if os.path.exists(".env"):
    load_dotenv()
else:
    print("[Database] Warning: .env file not found. Using default SQLite configuration.")

# Get the database URL from environment, default to SQLite if missing
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("[Database] DATABASE_URL not found in environment. Falling back to SQLite.")
    DATABASE_URL = "sqlite:///products.db"

# Extension-specific database (isolated from main app)
EXTENSION_DATABASE_URL = os.getenv("EXTENSION_DATABASE_URL", "sqlite:///ecommerce_extension.db")

# Engine with built-in connection pooling configured securely
def _create_db_engine(url, label="Main"):
    try:
        eng = create_engine(
            url,
            pool_size=10,          # Allow up to 10 concurrent connections in pool
            max_overflow=20,       # Allow an extra 20 beyond pool size during peak spikes
            pool_timeout=30,       # Wait up to 30s before throwing timeout
            pool_recycle=1800,     # Recycle connections every 30 minutes to prevent staleness
        )
        print(f"[Database] {label} connected to: {url}")
        return eng
    except Exception as e:
        print(f"[Database] {label} error creating engine: {e}")
        fallback = "sqlite:///products.db"
        eng = create_engine(fallback)
        print(f"[Database] {label} final fallback to: {fallback}")
        return eng

engine = _create_db_engine(DATABASE_URL, label="Main")
extension_engine = _create_db_engine(EXTENSION_DATABASE_URL, label="Extension")

def get_engine(origin=None):
    """Return the appropriate SQLAlchemy engine based on origin."""
    if origin == "extension":
        return extension_engine
    return engine
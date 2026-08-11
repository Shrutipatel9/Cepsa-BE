import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Load environment variables from .env
load_dotenv()

# Default Supabase Connection URL (reads DATABASE_URL from .env if present)
DEFAULT_SUPABASE_URL = "postgresql://postgres:[YOUR_PASSWORD]@db.wcysphccjnvzygwtknbw.supabase.co:5432/postgres"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_SUPABASE_URL)

# Fallback to local SQLite if DATABASE_URL is not set or set to sqlite
if "sqlite" in SQLALCHEMY_DATABASE_URL:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "cepsa.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
else:
    # PostgreSQL (Supabase) Engine
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

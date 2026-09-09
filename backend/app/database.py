from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from .config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate():
    """Lightweight additive migration for existing prototype DBs (SQLite)."""
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    from sqlalchemy import text
    try:
        with engine.begin() as conn:
            cols = {r[1] for r in conn.execute(text("PRAGMA table_info(cases)")).fetchall()}
            for col, typ in (("incident_time_gmt", "VARCHAR(40)"),
                             ("suspect_ip", "VARCHAR(64)"),
                             ("ref_12digit", "VARCHAR(16)"),
                             ("suspect_name", "VARCHAR(128)"),
                             ("suspect_alias", "VARCHAR(128)"),
                             ("suspect_phone", "VARCHAR(32)"),
                             ("suspect_email", "VARCHAR(128)"),
                             ("suspect_account", "VARCHAR(128)")):
                if col not in cols:
                    conn.execute(text(f"ALTER TABLE cases ADD COLUMN {col} {typ} DEFAULT ''"))
    except Exception:
        pass

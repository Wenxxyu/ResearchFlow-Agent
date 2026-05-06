from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    sqlite_path = settings.sqlite_path
    if sqlite_path is not None:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    import app.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_sqlite_schema_compatibility()


def ensure_sqlite_schema_compatibility() -> None:
    if not settings.database_url.startswith("sqlite"):
        return

    inspector = inspect(engine)
    if "projects" not in inspector.get_table_names():
        return

    project_columns = {column["name"] for column in inspector.get_columns("projects")}
    if "updated_at" not in project_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE projects ADD COLUMN updated_at DATETIME"))
            connection.execute(text("UPDATE projects SET updated_at = created_at WHERE updated_at IS NULL"))


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database() -> bool:
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return True

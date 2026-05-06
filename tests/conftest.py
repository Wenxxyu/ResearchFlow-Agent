from collections.abc import Generator
import os
import shutil
from pathlib import Path

os.environ["RESEARCHFLOW_UPLOAD_DIR"] = ".tmp/test-data/uploads"
os.environ["RESEARCHFLOW_REPO_DIR"] = ".tmp/test-data/repos"
os.environ["RESEARCHFLOW_SKILL_DIR"] = ".tmp/test-skills"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    test_data_dir = Path(".tmp/test-data")
    if test_data_dir.exists():
        shutil.rmtree(test_data_dir, ignore_errors=True)
    test_skill_dir = Path(".tmp/test-skills")
    if test_skill_dir.exists():
        shutil.rmtree(test_skill_dir, ignore_errors=True)
    source_skill_dir = Path("skills")
    if source_skill_dir.exists():
        shutil.copytree(source_skill_dir, test_skill_dir, dirs_exist_ok=True)

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()

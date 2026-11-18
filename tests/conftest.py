"""測試設定：每個測試使用全新的 in-memory SQLite 資料庫（spec 7.2 方式 B）。

必須在 import app 之前設定 DATABASE_URL，避免 lifespan 在專案根目錄建立 xr_objects.db。
"""
import os

os.environ["DATABASE_URL"] = "sqlite://"

import copy  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from helpers import VALID_BODY  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def body():
    """回傳一份可自由修改的合法 body。"""
    return copy.deepcopy(VALID_BODY)


@pytest.fixture()
def created(client, body):
    r = client.post("/objects", json=body)
    assert r.status_code == 201, r.text
    return r.json()

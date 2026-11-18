"""資料庫設定：DATABASE_URL、engine、SessionLocal、Base、get_db()（spec 7.1）。"""
import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# 於模組匯入時讀取；只支援 SQLite URL（connect_args 為 SQLite 專用）
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./xr_objects.db")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 30})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

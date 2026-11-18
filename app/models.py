"""SQLAlchemy ORM 模型（spec 3.2）。"""
from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SceneObject(Base):
    __tablename__ = "scene_objects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_url: Mapped[str] = mapped_column(String(2048), nullable=False)

    position_x: Mapped[float] = mapped_column(Float, nullable=False)
    position_y: Mapped[float] = mapped_column(Float, nullable=False)
    position_z: Mapped[float] = mapped_column(Float, nullable=False)

    rotation_x: Mapped[float] = mapped_column(Float, nullable=False)
    rotation_y: Mapped[float] = mapped_column(Float, nullable=False)
    rotation_z: Mapped[float] = mapped_column(Float, nullable=False)

    scale_x: Mapped[float] = mapped_column(Float, nullable=False)
    scale_y: Mapped[float] = mapped_column(Float, nullable=False)
    scale_z: Mapped[float] = mapped_column(Float, nullable=False)

    # 以 naive UTC 儲存，輸出時補 Z
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

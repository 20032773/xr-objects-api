"""資料存取函式（隔離資料庫細節）。"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import SceneObject
from app.schemas import ObjectCreate, ObjectOut, ObjectUpdate, Vector3


def _utcnow() -> datetime:
    """目前 UTC 時間（naive）。"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _apply_payload(obj: SceneObject, data: ObjectCreate) -> None:
    obj.name = data.name
    obj.model_url = data.model_url
    obj.position_x = float(data.position.x)
    obj.position_y = float(data.position.y)
    obj.position_z = float(data.position.z)
    obj.rotation_x = float(data.rotation.x)
    obj.rotation_y = float(data.rotation.y)
    obj.rotation_z = float(data.rotation.z)
    obj.scale_x = float(data.scale.x)
    obj.scale_y = float(data.scale.y)
    obj.scale_z = float(data.scale.z)


def to_out(obj: SceneObject) -> ObjectOut:
    return ObjectOut(
        id=obj.id,
        name=obj.name,
        model_url=obj.model_url,
        position=Vector3(x=float(obj.position_x), y=float(obj.position_y), z=float(obj.position_z)),
        rotation=Vector3(x=float(obj.rotation_x), y=float(obj.rotation_y), z=float(obj.rotation_z)),
        scale=Vector3(x=float(obj.scale_x), y=float(obj.scale_y), z=float(obj.scale_z)),
        created_at=obj.created_at,
        updated_at=obj.updated_at,
    )


def list_objects(db: Session, limit: int, offset: int) -> tuple[list[SceneObject], int]:
    total = db.scalar(select(func.count()).select_from(SceneObject)) or 0
    stmt = (
        select(SceneObject)
        .order_by(SceneObject.created_at.asc(), SceneObject.id.asc())
        .limit(limit)
        .offset(offset)
    )
    items = list(db.scalars(stmt).all())
    return items, total


def get_object(db: Session, object_id: str) -> SceneObject | None:
    return db.get(SceneObject, object_id)


def create_object(db: Session, data: ObjectCreate) -> SceneObject:
    now = _utcnow()
    obj = SceneObject(id=str(uuid.uuid4()), created_at=now, updated_at=now)
    _apply_payload(obj, data)
    db.add(obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(obj)
    return obj


def update_object(db: Session, obj: SceneObject, data: ObjectUpdate) -> SceneObject:
    _apply_payload(obj, data)
    now = _utcnow()
    # 保證 updated_at >= created_at
    obj.updated_at = now if now >= obj.created_at else obj.created_at
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(obj)
    return obj


def delete_object(db: Session, obj: SceneObject) -> None:
    db.delete(obj)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

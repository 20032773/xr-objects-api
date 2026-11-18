"""Pydantic v2 schemas（spec 3.1、4、5）。"""
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, StrictStr, field_serializer, field_validator

# ---------------------------------------------------------------------------
# Vector3
# ---------------------------------------------------------------------------
# strict float：接受 JSON 整數/浮點數，拒絕字串、布林、null；拒絕 NaN / ±Infinity
PositionComponent = Annotated[
    float, Field(strict=True, allow_inf_nan=False, ge=-1_000_000, le=1_000_000)
]
RotationComponent = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=-360, le=360)]
ScaleComponent = Annotated[float, Field(strict=True, allow_inf_nan=False, gt=0, le=10_000)]
AnyComponent = Annotated[float, Field(strict=True, allow_inf_nan=False)]


class Vector3(BaseModel):
    """一般三維向量（輸出用）。"""

    model_config = ConfigDict(extra="forbid")

    x: AnyComponent
    y: AnyComponent
    z: AnyComponent


class PositionVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: PositionComponent
    y: PositionComponent
    z: PositionComponent


class RotationVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: RotationComponent
    y: RotationComponent
    z: RotationComponent


class ScaleVector(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: ScaleComponent
    y: ScaleComponent
    z: ScaleComponent


# ---------------------------------------------------------------------------
# 欄位驗證輔助
# ---------------------------------------------------------------------------
NAME_MAX_LEN = 100
URL_MAX_LEN = 2048


def _has_control_char(s: str) -> bool:
    return any(ord(c) <= 0x1F or ord(c) == 0x7F for c in s)


def validate_name(value: str) -> str:
    stripped = value.strip()
    if len(stripped) == 0:
        raise ValueError("name must not be empty or whitespace only")
    if len(stripped) > NAME_MAX_LEN:
        raise ValueError(f"name must be at most {NAME_MAX_LEN} characters after trimming")
    if _has_control_char(stripped):
        raise ValueError("name must not contain control characters")
    return stripped


def validate_model_url(value: str) -> str:
    if len(value) == 0:
        raise ValueError("model_url must not be empty")
    if len(value) > URL_MAX_LEN:
        raise ValueError(f"model_url must be at most {URL_MAX_LEN} characters")
    if any(c.isspace() for c in value):
        raise ValueError("model_url must not contain whitespace")
    # 保守做法：其他控制字元同樣拒絕
    if _has_control_char(value):
        raise ValueError("model_url must not contain control characters")
    try:
        parts = urlsplit(value)
        port = parts.port  # 越界或非數字會拋 ValueError
    except ValueError:
        raise ValueError("model_url is not a valid URL") from None
    if parts.scheme.lower() not in ("http", "https"):
        raise ValueError("model_url scheme must be http or https")
    if not parts.hostname:
        raise ValueError("model_url must include a host")
    if port is not None and not (1 <= port <= 65535):
        raise ValueError("model_url port must be between 1 and 65535")
    # 原樣回傳，不做任何正規化
    return value


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------
class ObjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: StrictStr
    model_url: StrictStr
    position: PositionVector
    rotation: RotationVector
    scale: ScaleVector

    @field_validator("name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        return validate_name(v)

    @field_validator("model_url")
    @classmethod
    def _check_model_url(cls, v: str) -> str:
        return validate_model_url(v)


class ObjectUpdate(ObjectCreate):
    """PUT 規則與 POST 完全相同（整筆取代）。"""


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------
def _format_utc(dt: datetime) -> str:
    # DB 以 naive UTC 儲存（naive 視為 UTC）；若帶 tzinfo 則先轉成 UTC 再去除
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.isoformat(timespec="microseconds") + "Z"


class ObjectOut(BaseModel):
    id: str
    name: str
    model_url: str
    position: Vector3
    rotation: Vector3
    scale: Vector3
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def _ser_dt(self, dt: datetime) -> str:
        return _format_utc(dt)


class ObjectList(BaseModel):
    items: list[ObjectOut]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail]


class ErrorResponse(BaseModel):
    error: ErrorBody

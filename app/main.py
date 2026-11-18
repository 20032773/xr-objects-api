"""FastAPI 應用程式入口：`uvicorn app.main:app`。"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from app import crud
from app.database import Base, engine, get_db
from app.errors import register_exception_handlers
from app.schemas import ErrorResponse, ObjectCreate, ObjectList, ObjectOut, ObjectUpdate

UUID_PATTERN = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"

ObjectId = Annotated[str, Path(pattern=UUID_PATTERN, description="物件 UUID")]
DbSession = Annotated[Session, Depends(get_db)]

_ERROR_RESPONSES = {
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="XR Scene Object API", version="1.0", lifespan=lifespan, redirect_slashes=False)
register_exception_handlers(app)


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Object not found")


@app.get("/objects", response_model=ObjectList, responses=_ERROR_RESPONSES)
def list_objects(
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ObjectList:
    items, total = crud.list_objects(db, limit=limit, offset=offset)
    return ObjectList(items=[crud.to_out(o) for o in items], total=total, limit=limit, offset=offset)


@app.get("/objects/{id}", response_model=ObjectOut, responses=_ERROR_RESPONSES)
def get_object(id: ObjectId, db: DbSession) -> ObjectOut:
    obj = crud.get_object(db, id.lower())
    if obj is None:
        raise _not_found()
    return crud.to_out(obj)


@app.post("/objects", response_model=ObjectOut, status_code=201, responses=_ERROR_RESPONSES)
def create_object(payload: ObjectCreate, response: Response, db: DbSession) -> ObjectOut:
    obj = crud.create_object(db, payload)
    response.headers["Location"] = f"/objects/{obj.id}"
    return crud.to_out(obj)


@app.put("/objects/{id}", response_model=ObjectOut, responses=_ERROR_RESPONSES)
def update_object(id: ObjectId, payload: ObjectUpdate, db: DbSession) -> ObjectOut:
    obj = crud.get_object(db, id.lower())
    if obj is None:
        raise _not_found()
    obj = crud.update_object(db, obj, payload)
    return crud.to_out(obj)


@app.delete("/objects/{id}", status_code=204, response_class=Response, responses=_ERROR_RESPONSES)
def delete_object(id: ObjectId, db: DbSession) -> Response:
    obj = crud.get_object(db, id.lower())
    if obj is None:
        raise _not_found()
    crud.delete_object(db, obj)
    return Response(status_code=204)

from sqlmodel import create_engine, Session, SQLModel
from typing import Annotated
from fastapi import Depends
from app.models.db import engine


def get_db():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_db)]

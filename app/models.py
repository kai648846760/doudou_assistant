from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Author(SQLModel, table=True):
    __tablename__ = "authors"

    id: Optional[int] = Field(default=None, primary_key=True)
    unique_id: Optional[str] = Field(default=None, index=True)
    sec_uid: Optional[str] = Field(default=None, index=True)
    display_name: Optional[str] = Field(default=None)

    latest_aweme_id: Optional[str] = Field(default=None)
    latest_create_time: Optional[int] = Field(default=None, index=True)

    total_awemes: int = Field(default=0)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Aweme(SQLModel, table=True):
    __tablename__ = "awemes"

    id: Optional[int] = Field(default=None, primary_key=True)
    author_id: int = Field(foreign_key="authors.id", index=True)

    aweme_id: str = Field(index=True)
    desc: Optional[str] = Field(default=None)
    create_time: int = Field(index=True)
    digg_count: int = Field(default=0)
    collect_count: int = Field(default=0)
    comment_count: int = Field(default=0)
    share_count: int = Field(default=0)

    downloaded: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    updated_at: datetime = Field(default_factory=datetime.utcnow)

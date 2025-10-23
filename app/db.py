from __future__ import annotations

import pathlib
from datetime import datetime
from typing import Optional

from sqlmodel import Session, SQLModel, create_engine, select

from app.models import Author, Aweme


class Database:
    def __init__(self, db_path: str = "./data/crawler.db") -> None:
        self.db_path = db_path
        pathlib.Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{db_path}")
        SQLModel.metadata.create_all(self.engine)

    def get_or_create_author(
        self, unique_id: Optional[str] = None, sec_uid: Optional[str] = None
    ) -> Author:
        with Session(self.engine) as session:
            # Try to find existing author
            statement = None
            if sec_uid:
                statement = select(Author).where(Author.sec_uid == sec_uid)
            elif unique_id:
                statement = select(Author).where(Author.unique_id == unique_id)

            if statement:
                author = session.exec(statement).first()
                if author:
                    return author

            # Create new author
            author = Author(unique_id=unique_id, sec_uid=sec_uid)
            session.add(author)
            session.commit()
            session.refresh(author)
            return author

    def update_author(
        self,
        author_id: int,
        display_name: Optional[str] = None,
        latest_aweme_id: Optional[str] = None,
        latest_create_time: Optional[int] = None,
        total_awemes: Optional[int] = None,
    ) -> None:
        with Session(self.engine) as session:
            statement = select(Author).where(Author.id == author_id)
            author = session.exec(statement).first()
            if author:
                if display_name is not None:
                    author.display_name = display_name
                if latest_aweme_id is not None:
                    author.latest_aweme_id = latest_aweme_id
                if latest_create_time is not None:
                    author.latest_create_time = latest_create_time
                if total_awemes is not None:
                    author.total_awemes = total_awemes
                author.updated_at = datetime.utcnow()
                session.add(author)
                session.commit()

    def add_awemes(self, author_id: int, awemes: list[dict]) -> int:
        """Add awemes to database, deduping by aweme_id. Returns count of new items."""
        if not awemes:
            return 0

        new_count = 0
        with Session(self.engine) as session:
            for aweme_data in awemes:
                aweme_id = aweme_data.get("aweme_id")
                if not aweme_id:
                    continue

                # Check if already exists
                statement = select(Aweme).where(
                    Aweme.author_id == author_id, Aweme.aweme_id == aweme_id
                )
                existing = session.exec(statement).first()
                if existing:
                    continue

                # Create new aweme
                aweme = Aweme(
                    author_id=author_id,
                    aweme_id=aweme_id,
                    desc=aweme_data.get("desc", ""),
                    create_time=aweme_data.get("create_time", 0),
                    digg_count=aweme_data.get("statistics", {}).get("digg_count", 0),
                    collect_count=aweme_data.get("statistics", {}).get(
                        "collect_count", 0
                    ),
                    comment_count=aweme_data.get("statistics", {}).get(
                        "comment_count", 0
                    ),
                    share_count=aweme_data.get("statistics", {}).get("share_count", 0),
                )
                session.add(aweme)
                new_count += 1

            session.commit()

        return new_count

    def get_latest_aweme_info(self, author_id: int) -> tuple[Optional[str], Optional[int]]:
        """Get the latest aweme_id and create_time for an author."""
        with Session(self.engine) as session:
            statement = (
                select(Aweme)
                .where(Aweme.author_id == author_id)
                .order_by(Aweme.create_time.desc())
                .limit(1)
            )
            aweme = session.exec(statement).first()
            if aweme:
                return aweme.aweme_id, aweme.create_time
            return None, None

    def get_aweme_count(self, author_id: int) -> int:
        with Session(self.engine) as session:
            statement = select(Aweme).where(Aweme.author_id == author_id)
            return len(session.exec(statement).all())

    def get_all_awemes(self, author_id: Optional[int] = None, limit: int = 100) -> list[dict]:
        with Session(self.engine) as session:
            if author_id:
                statement = (
                    select(Aweme)
                    .where(Aweme.author_id == author_id)
                    .order_by(Aweme.create_time.desc())
                    .limit(limit)
                )
            else:
                statement = select(Aweme).order_by(Aweme.create_time.desc()).limit(limit)

            awemes = session.exec(statement).all()
            return [
                {
                    "id": a.id,
                    "aweme_id": a.aweme_id,
                    "desc": a.desc,
                    "create_time": a.create_time,
                    "digg_count": a.digg_count,
                    "collect_count": a.collect_count,
                    "comment_count": a.comment_count,
                    "share_count": a.share_count,
                }
                for a in awemes
            ]

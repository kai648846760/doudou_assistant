from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import func, or_
from sqlmodel import Field, Session, SQLModel, create_engine, select


class Author(SQLModel, table=True):
    """Normalized record for a Douyin author (creator)."""

    author_id: str = Field(primary_key=True, index=True)
    unique_id: Optional[str] = Field(default=None, index=True)
    sec_uid: Optional[str] = Field(default=None, index=True)
    nickname: Optional[str] = Field(default=None, index=True)
    signature: Optional[str] = None
    avatar_thumb: Optional[str] = None
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    aweme_count: Optional[int] = None
    region: Optional[str] = None
    received_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)


class Video(SQLModel, table=True):
    """Normalized record for a Douyin video (aweme)."""

    aweme_id: str = Field(primary_key=True, index=True)
    author_id: Optional[str] = Field(default=None, index=True)
    author_name: Optional[str] = Field(default=None, index=True)
    author_unique_id: Optional[str] = Field(default=None, index=True)
    author_sec_uid: Optional[str] = Field(default=None, index=True)
    desc: Optional[str] = None
    create_time: Optional[dt.datetime] = Field(default=None, index=True)
    duration: Optional[int] = None
    digg_count: Optional[int] = None
    comment_count: Optional[int] = None
    share_count: Optional[int] = None
    play_count: Optional[int] = None
    collect_count: Optional[int] = None
    region: Optional[str] = None
    music_title: Optional[str] = None
    music_author: Optional[str] = None
    cover: Optional[str] = None
    video_url: Optional[str] = None
    item_type: Optional[str] = Field(default=None, index=True)
    received_at: dt.datetime = Field(default_factory=dt.datetime.utcnow)


class Database:
    """Lightweight database layer backed by SQLite."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._engine = create_engine(f"sqlite:///{self.db_path}", echo=False)
        SQLModel.metadata.create_all(self._engine)

    # ------------------------------------------------------------------
    # Normalisation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce_datetime(value: Any) -> Optional[dt.datetime]:
        if value in (None, "", 0):
            return None
        if isinstance(value, dt.datetime):
            return value
        if isinstance(value, (int, float)):
            if value > 1e12:  # milliseconds
                value = int(value / 1000)
            return dt.datetime.utcfromtimestamp(int(value))
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if stripped.isdigit():
                val = int(stripped)
                if val > 1e12:
                    val = int(val / 1000)
                return dt.datetime.utcfromtimestamp(val)
            for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return dt.datetime.strptime(stripped, fmt)
                except ValueError:
                    continue
                
            try:
                return dt.datetime.fromisoformat(stripped)
            except ValueError:
                return None
        return None

    @staticmethod
    def _coerce_int(value: Any) -> Optional[int]:
        if value in (None, "", "null"):
            return None
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return None
            if stripped.isdigit():
                return int(stripped)
            try:
                return int(float(stripped))
            except ValueError:
                return None
        return None

    @staticmethod
    def _first(value: Any) -> Optional[str]:
        if isinstance(value, list) and value:
            return value[0]
        return value if isinstance(value, str) else None

    def _normalize_author(self, raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not raw:
            return None

        author_id = raw.get("author_id") or raw.get("uid") or raw.get("id")
        author_id = author_id or raw.get("sec_uid") or raw.get("unique_id")
        if not author_id:
            return None

        avatar_field = raw.get("avatar_thumb") or raw.get("avatar"),
        avatar_value: Optional[str]
        if isinstance(avatar_field, tuple):
            avatar_field = avatar_field[0]
        if isinstance(avatar_field, dict):
            avatar_value = self._first(avatar_field.get("url_list"))
        else:
            avatar_value = self._first(avatar_field)

        normalized = {
            "author_id": str(author_id),
            "unique_id": raw.get("unique_id") or raw.get("short_id"),
            "sec_uid": raw.get("sec_uid"),
            "nickname": raw.get("nickname") or raw.get("name"),
            "signature": raw.get("signature") or raw.get("bio_description"),
            "avatar_thumb": avatar_value,
            "follower_count": self._coerce_int(
                raw.get("follower_count")
                or raw.get("fans")
                or raw.get("followers_detail", {}).get("follower_count")
            ),
            "following_count": self._coerce_int(raw.get("following_count") or raw.get("following")),
            "aweme_count": self._coerce_int(raw.get("aweme_count")),
            "region": raw.get("region") or raw.get("country"),
            "received_at": dt.datetime.utcnow(),
        }
        return normalized

    def _normalize_item(self, item: Dict[str, Any]) -> tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        aweme_id = item.get("aweme_id") or item.get("id")
        if not aweme_id:
            raise ValueError("Missing aweme_id")

        author_block = item.get("author") or item.get("aweme_author_info") or {}
        statistics = item.get("statistics") or {}
        music_block = item.get("music") or {}
        video_block = item.get("video") or {}
        cover_block = video_block.get("cover") or {}
        play_addr = video_block.get("play_addr") or {}

        author_unique_id = (
            author_block.get("unique_id")
            or author_block.get("short_id")
            or author_block.get("display_id")
        )
        author_sec_uid = author_block.get("sec_uid")
        author_id = (
            author_block.get("uid")
            or author_block.get("id")
            or author_block.get("author_id")
            or author_sec_uid
            or author_unique_id
        )

        video_data: Dict[str, Any] = {
            "aweme_id": str(aweme_id),
            "author_id": str(author_id) if author_id else None,
            "author_name": author_block.get("nickname") or author_block.get("name"),
            "author_unique_id": author_unique_id,
            "author_sec_uid": author_sec_uid,
            "desc": item.get("desc") or item.get("description"),
            "create_time": self._coerce_datetime(
                item.get("create_time") or statistics.get("create_time")
            ),
            "duration": self._coerce_int(item.get("duration")),
            "digg_count": self._coerce_int(statistics.get("digg_count")),
            "comment_count": self._coerce_int(statistics.get("comment_count")),
            "share_count": self._coerce_int(statistics.get("share_count")),
            "play_count": self._coerce_int(statistics.get("play_count")),
            "collect_count": self._coerce_int(
                statistics.get("collect_count") or statistics.get("collect_cnt")
            ),
            "region": item.get("region") or author_block.get("region"),
            "music_title": music_block.get("title") or music_block.get("name"),
            "music_author": music_block.get("author") or music_block.get("owner_nickname"),
            "cover": self._first(cover_block.get("url_list")) if isinstance(cover_block, dict) else self._first(cover_block),
            "video_url": self._first(play_addr.get("url_list")) if isinstance(play_addr, dict) else self._first(play_addr),
            "item_type": item.get("item_type") or item.get("type"),
        }

        author_data = self._normalize_author(
            {
                **author_block,
                "author_id": author_id,
                "unique_id": author_unique_id,
                "sec_uid": author_sec_uid,
            }
        )

        return video_data, author_data

    # ------------------------------------------------------------------
    # Author operations
    # ------------------------------------------------------------------
    def upsert_author(self, author: Dict[str, Any]) -> Optional[Author]:
        normalized = self._normalize_author(author)
        if not normalized:
            return None
        with Session(self._engine) as session:
            record = self._upsert_author(session, normalized)
            session.commit()
            session.refresh(record)
            return record

    def _upsert_author(self, session: Session, author_data: Dict[str, Any]) -> Author:
        author_id = author_data["author_id"]
        record = session.get(Author, author_id)
        if record:
            for key, value in author_data.items():
                setattr(record, key, value)
        else:
            record = Author(**author_data)
            session.add(record)
        record.received_at = dt.datetime.utcnow()
        return record

    def find_author(self, identifier: str) -> Optional[Author]:
        if not identifier:
            return None
        with Session(self._engine) as session:
            record = session.get(Author, identifier)
            if record:
                return record
            statement = select(Author).where(
                or_(Author.unique_id == identifier, Author.sec_uid == identifier)
            )
            return session.exec(statement).first()

    def get_latest_for_author(self, author_id: str) -> Optional[Dict[str, Any]]:
        if not author_id:
            return None
        with Session(self._engine) as session:
            statement = (
                select(Video)
                .where(Video.author_id == str(author_id))
                .order_by(Video.create_time.desc(), Video.received_at.desc())
                .limit(1)
            )
            row = session.exec(statement).first()
            if not row:
                return None
            return {
                "aweme_id": row.aweme_id,
                "author_id": row.author_id,
                "create_time": row.create_time.isoformat() if row.create_time else None,
            }

    # ------------------------------------------------------------------
    # Video operations
    # ------------------------------------------------------------------
    def upsert_videos(self, items: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        inserted = 0
        updated = 0
        with Session(self._engine) as session:
            for raw in items:
                try:
                    video_data, author_data = self._normalize_item(raw)
                except ValueError:
                    continue

                author_record = None
                if author_data:
                    author_record = self._upsert_author(session, author_data)

                if author_record:
                    if not video_data.get("author_id"):
                        video_data["author_id"] = author_record.author_id
                    if author_record.nickname and not video_data.get("author_name"):
                        video_data["author_name"] = author_record.nickname
                    if author_record.unique_id and not video_data.get("author_unique_id"):
                        video_data["author_unique_id"] = author_record.unique_id
                    if author_record.sec_uid and not video_data.get("author_sec_uid"):
                        video_data["author_sec_uid"] = author_record.sec_uid

                existing = session.get(Video, video_data["aweme_id"])
                if existing:
                    for key, value in video_data.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    session.add(Video(**video_data))
                    inserted += 1
            session.commit()
        return {"inserted": inserted, "updated": updated}

    # ------------------------------------------------------------------
    # Querying and export
    # ------------------------------------------------------------------
    def _build_conditions(self, filters: Dict[str, Any]) -> list[Any]:
        conditions: list[Any] = []
        author_id = filters.get("author_id") or filters.get("author")
        if author_id:
            conditions.append(Video.author_id == str(author_id))

        unique_id = filters.get("author_unique_id") or filters.get("unique_id")
        if unique_id:
            conditions.append(Video.author_unique_id == str(unique_id))

        sec_uid = filters.get("author_sec_uid") or filters.get("sec_uid")
        if sec_uid:
            conditions.append(Video.author_sec_uid == str(sec_uid))

        author_name = filters.get("author_name") or filters.get("keyword")
        if author_name:
            like = f"%{author_name.strip()}%"
            conditions.append(Video.author_name.ilike(like))

        item_type = filters.get("item_type")
        if item_type:
            conditions.append(Video.item_type == item_type)

        date_from = filters.get("date_from") or filters.get("from")
        coerced_from = self._coerce_datetime(date_from)
        if coerced_from:
            conditions.append(Video.create_time >= coerced_from)

        date_to = filters.get("date_to") or filters.get("to")
        coerced_to = self._coerce_datetime(date_to)
        if coerced_to:
            conditions.append(Video.create_time <= coerced_to)

        return conditions

    def list_videos(
        self,
        filters: Dict[str, Any],
        page: int,
        page_size: int,
    ) -> Dict[str, Any]:
        page = max(page, 1)
        page_size = max(min(page_size, 200), 1)
        conditions = self._build_conditions(filters)

        with Session(self._engine) as session:
            count_stmt = select(func.count()).select_from(Video)
            if conditions:
                count_stmt = count_stmt.where(*conditions)
            total = session.exec(count_stmt).one()

            offset = (page - 1) * page_size
            query = (
                select(Video)
                .where(*conditions) if conditions else select(Video)
            )
            query = query.order_by(Video.create_time.desc(), Video.received_at.desc())
            rows = session.exec(query.offset(offset).limit(page_size)).all()

        def serialize(row: Video) -> Dict[str, Any]:
            data = row.model_dump()
            data["create_time"] = row.create_time.isoformat() if row.create_time else None
            data["received_at"] = row.received_at.isoformat()
            return data

        return {
            "items": [serialize(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def export_csv(self, filters: Dict[str, Any]) -> Path:
        conditions = self._build_conditions(filters)
        with Session(self._engine) as session:
            query = select(Video)
            if conditions:
                query = query.where(*conditions)
            rows = session.exec(query.order_by(Video.create_time.desc())).all()

        export_dir = self.db_path.parent
        timestamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_path = export_dir / f"douyin_export_{timestamp}.csv"

        headers = [
            "aweme_id",
            "author_id",
            "author_name",
            "author_unique_id",
            "author_sec_uid",
            "desc",
            "create_time",
            "duration",
            "digg_count",
            "comment_count",
            "share_count",
            "play_count",
            "collect_count",
            "region",
            "music_title",
            "music_author",
            "cover",
            "video_url",
            "item_type",
            "received_at",
        ]

        with export_path.open("w", newline="", encoding="utf-8") as fp:
            writer = csv.DictWriter(fp, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                payload = row.model_dump()
                payload["create_time"] = (
                    row.create_time.isoformat() if row.create_time else ""
                )
                payload["received_at"] = row.received_at.isoformat()
                writer.writerow({key: payload.get(key, "") for key in headers})

        return export_path

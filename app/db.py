from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import func
from sqlmodel import Field, Session, SQLModel, create_engine, select


class Aweme(SQLModel, table=True):
    """Normalized record for an aweme (short-form video)."""

    aweme_id: str = Field(primary_key=True, index=True)
    author_id: Optional[str] = Field(default=None, index=True)
    author_name: Optional[str] = Field(default=None, index=True)
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

    @staticmethod
    def _coerce_datetime(value: Any) -> Optional[dt.datetime]:
        if value in (None, "", 0):
            return None
        if isinstance(value, dt.datetime):
            return value
        if isinstance(value, (int, float)):
            # treat values smaller than timestamp (i.e. ms) accordingly
            if value > 1e12:
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

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        aweme_id = item.get("aweme_id") or item.get("id")
        if not aweme_id:
            raise ValueError("Missing aweme_id")

        def _split_index(segment: str) -> tuple[str, Optional[int]]:
            if "[" in segment and segment.endswith("]"):
                name, index_part = segment[:-1].split("[", 1)
                if index_part.isdigit():
                    return name, int(index_part)
                return segment, None
            return segment, None

        def pick(path: str, default: Any = None) -> Any:
            parts = path.split(".")
            current: Any = item
            for part in parts:
                if isinstance(current, dict):
                    key, index = _split_index(part)
                    if key not in current:
                        return default
                    current = current[key]
                    if index is not None:
                        if isinstance(current, list) and 0 <= index < len(current):
                            current = current[index]
                        else:
                            return default
                elif isinstance(current, list):
                    if part.isdigit():
                        idx = int(part)
                        if 0 <= idx < len(current):
                            current = current[idx]
                        else:
                            return default
                    else:
                        return default
                else:
                    return default
            return current

        normalized: Dict[str, Any] = {
            "aweme_id": str(aweme_id),
            "author_id": pick("author.id") or pick("author.uid"),
            "author_name": pick("author.nickname") or pick("author.name"),
            "desc": item.get("desc") or item.get("description"),
            "create_time": self._coerce_datetime(
                item.get("create_time") or pick("statistics.create_time")
            ),
            "duration": self._coerce_int(pick("duration")),
            "digg_count": self._coerce_int(pick("statistics.digg_count")),
            "comment_count": self._coerce_int(pick("statistics.comment_count")),
            "share_count": self._coerce_int(pick("statistics.share_count")),
            "play_count": self._coerce_int(pick("statistics.play_count")),
            "collect_count": self._coerce_int(pick("statistics.collect_count")),
            "region": item.get("region") or pick("author.region"),
            "music_title": pick("music.title") or pick("music.name"),
            "music_author": pick("music.author") or pick("music.owner_nickname"),
            "cover": pick("video.cover.url_list.0") or pick("video.cover.url_list.[0]"),
            "video_url": pick("video.play_addr.url_list.0"),
            "item_type": item.get("item_type") or item.get("type"),
        }

        normalized["create_time"] = self._coerce_datetime(normalized["create_time"])
        return normalized

    def write_items(self, items: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        added = 0
        updated = 0
        with Session(self._engine) as session:
            for raw in items:
                try:
                    normalized = self._normalize_item(raw)
                except ValueError:
                    continue

                aweme_id = normalized["aweme_id"]
                existing = session.get(Aweme, aweme_id)
                if existing:
                    for key, value in normalized.items():
                        setattr(existing, key, value)
                    updated += 1
                else:
                    session.add(Aweme(**normalized))
                    added += 1
            session.commit()
        return {"inserted": added, "updated": updated}

    def list_videos(
        self,
        filters: Dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        filters = filters or {}
        page = max(page, 1)
        page_size = max(min(page_size, 200), 1)

        with Session(self._engine) as session:
            query = select(Aweme)

            author_id = filters.get("author_id") or filters.get("author")
            if author_id:
                query = query.where(Aweme.author_id == str(author_id))

            author_name = filters.get("author_name") or filters.get("keyword")
            if author_name:
                like = f"%{author_name.strip()}%"
                query = query.where(Aweme.author_name.ilike(like))

            item_type = filters.get("item_type")
            if item_type:
                query = query.where(Aweme.item_type == item_type)

            count_statement = select(func.count()).select_from(query.subquery())
            total = session.exec(count_statement).one()

            offset = (page - 1) * page_size
            rows = session.exec(
                query.order_by(Aweme.create_time.desc())
                .offset(offset)
                .limit(page_size)
            ).all()

        def serialize(row: Aweme) -> Dict[str, Any]:
            data = row.model_dump()
            if row.create_time:
                data["create_time"] = row.create_time.isoformat()
            data["received_at"] = row.received_at.isoformat()
            return data

        return {
            "items": [serialize(row) for row in rows],
            "page": page,
            "page_size": page_size,
            "total": total,
        }

    def export_csv(self, filters: Dict[str, Any] | None = None) -> Path:
        filters = filters or {}
        with Session(self._engine) as session:
            query = select(Aweme)
            author_id = filters.get("author_id")
            if author_id:
                query = query.where(Aweme.author_id == str(author_id))
            rows = session.exec(query.order_by(Aweme.create_time.desc())).all()

        export_dir = self.db_path.parent
        timestamp = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        export_path = export_dir / f"aweme_export_{timestamp}.csv"

        headers = [
            "aweme_id",
            "author_id",
            "author_name",
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

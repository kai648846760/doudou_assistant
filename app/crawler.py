from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional
from urllib.parse import ParseResult, parse_qs, urlparse

from sqlmodel import Session, select

from app.db import Database
from app.models import Author, Aweme

ProgressCallback = Callable[[str, dict], None]


@dataclass
class AuthorTarget:
    raw_input: str
    unique_id: Optional[str]
    sec_uid: Optional[str]
    url: str

    @property
    def identity(self) -> str:
        return self.sec_uid or self.unique_id or self.raw_input


class MockDouyinService:
    """Mock service to simulate Douyin author page crawling."""

    def __init__(self) -> None:
        self.batch_size = 20

    def _base_timestamp(self, key: str) -> int:
        # Deterministic base timestamp per author key
        return 1_700_000_000 + (abs(hash(key)) % 2_000_000)

    def _catalogue_size(self, key: str) -> int:
        # Provide a deterministic but bounded catalogue size per author
        return 60 + (abs(hash(key)) % 3) * 10

    def generate_awemes(
        self,
        identity: str,
        start_seq: int,
        batches: int,
    ) -> list[list[dict]]:
        base_ts = self._base_timestamp(identity)
        total_available = self._catalogue_size(identity)
        if start_seq >= total_available:
            return []

        remaining = total_available - start_seq
        max_to_generate = min(remaining, batches * self.batch_size)

        all_batches: list[list[dict]] = []
        generated = 0

        for _ in range(batches):
            if generated >= max_to_generate:
                break

            batch: list[dict] = []
            for _ in range(self.batch_size):
                if generated >= max_to_generate:
                    break

                seq = start_seq + generated + 1
                aweme_id = f"{abs(hash(identity)) % 10_000_000:07d}{seq:05d}"
                aweme = {
                    "aweme_id": aweme_id,
                    "desc": f"Mock aweme {seq} from {identity}",
                    "create_time": base_ts + seq * 60,
                    "statistics": {
                        "digg_count": (seq * 13) % 1000,
                        "collect_count": (seq * 7) % 200,
                        "comment_count": (seq * 11) % 500,
                        "share_count": (seq * 5) % 300,
                    },
                }
                batch.append(aweme)
                generated += 1

            if batch:
                all_batches.append(batch)

        return all_batches


def parse_author_input(value: str) -> AuthorTarget:
    text = (value or "").strip()
    if not text:
        raise ValueError("Author input is required")

    unique_id: Optional[str] = None
    sec_uid: Optional[str] = None

    if text.startswith("http://") or text.startswith("https://"):
        parsed: ParseResult = urlparse(text)
        if "douyin.com" not in parsed.netloc:
            raise ValueError("URL must be a Douyin author page")

        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            # If URL is /user/<sec_uid>
            if path_parts[0] == "user" and len(path_parts) > 1:
                sec_uid = path_parts[1]
            elif path_parts[0] == "share" and len(path_parts) > 1:
                # Share links often encode sec_uid in query params
                query = parse_qs(parsed.query)
                sec_uid = query.get("sec_uid", [None])[0]
                unique_id = query.get("unique_id", [None])[0]
        query_params = parse_qs(parsed.query)
        if not sec_uid:
            sec_uid = query_params.get("sec_uid", [None])[0]
        if not unique_id:
            unique_id = query_params.get("unique_id", [None])[0]
    else:
        if text.startswith("MS4w") or text.startswith("MS4"):
            sec_uid = text
        else:
            unique_id = text

    if not sec_uid and not unique_id:
        raise ValueError("Unable to determine author identifier from input")

    if sec_uid:
        url = f"https://www.douyin.com/user/{sec_uid}"
    else:
        url = f"https://www.douyin.com/search/{unique_id}"

    return AuthorTarget(raw_input=text, unique_id=unique_id, sec_uid=sec_uid, url=url)


class AuthorCrawler:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.mock_service = MockDouyinService()
        self._lock = threading.Lock()

    def crawl(
        self,
        author_input: str,
        progress: ProgressCallback,
    ) -> dict:
        progress("status", {"message": "Parsing author input"})
        target = parse_author_input(author_input)

        author = self.database.get_or_create_author(
            unique_id=target.unique_id, sec_uid=target.sec_uid
        )

        progress(
            "navigate",
            {
                "url": target.url,
                "identity": target.identity,
            },
        )

        with Session(self.database.engine) as session:
            db_author = session.exec(
                select(Author).where(Author.id == author.id)
            ).first()
            if not db_author:
                raise ValueError("Author not found after creation")

            if not db_author.display_name:
                db_author.display_name = target.identity

            latest_create_time = db_author.latest_create_time or 0
            base_ts = self.mock_service._base_timestamp(target.identity)
            last_seq = (
                max((latest_create_time - base_ts) // 60, 0)
                if latest_create_time
                else 0
            )

            batches = self.mock_service.generate_awemes(target.identity, last_seq, batches=3)

            total_collected = 0
            new_awemes: list[dict] = []
            existing_aweme_ids = set(
                session.exec(
                    select(Aweme.aweme_id).where(Aweme.author_id == db_author.id)
                ).all()
            )

            for index, batch in enumerate(batches, start=1):
                progress(
                    "scroll",
                    {
                        "batch": index,
                        "batch_size": len(batch),
                        "message": f"Autoscroll batch {index}",
                    },
                )

                appended = []
                for item in batch:
                    aweme_id = item.get("aweme_id")
                    create_time = item.get("create_time")
                    if not aweme_id or not create_time:
                        continue

                    if create_time <= latest_create_time:
                        continue
                    if aweme_id in existing_aweme_ids:
                        continue

                    existing_aweme_ids.add(aweme_id)
                    new_awemes.append(item)
                    appended.append(item)

                total_collected += len(appended)
                progress(
                    "batch",
                    {
                        "batch": index,
                        "items": len(appended),
                        "total_collected": total_collected,
                    },
                )

            if not new_awemes:
                session.add(db_author)
                session.commit()

                progress(
                    "complete",
                    {
                        "new_items": 0,
                        "total_collected": db_author.total_awemes,
                        "message": "No new awemes found",
                    },
                )
                return {
                    "author_id": db_author.id,
                    "new_items": 0,
                    "total_collected": db_author.total_awemes,
                    "latest_create_time": db_author.latest_create_time,
                }

            new_count = self.database.add_awemes(db_author.id, new_awemes)
            session.refresh(db_author)

            latest = max(new_awemes, key=lambda x: x.get("create_time", 0))
            db_author.latest_aweme_id = latest.get("aweme_id")
            db_author.latest_create_time = latest.get("create_time")
            db_author.total_awemes = (db_author.total_awemes or 0) + new_count
            db_author.updated_at = datetime.utcnow()
            session.add(db_author)
            session.commit()

            progress(
                "complete",
                {
                    "new_items": new_count,
                    "total_collected": db_author.total_awemes,
                    "message": f"Crawl complete. New: {new_count}",
                },
            )

            return {
                "author_id": db_author.id,
                "new_items": new_count,
                "total_collected": db_author.total_awemes,
                "latest_create_time": db_author.latest_create_time,
            }

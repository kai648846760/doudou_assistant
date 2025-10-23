"""Repository functions for database operations."""

from __future__ import annotations

import csv
import json
import pathlib
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlmodel import Session, desc, select

from app.database import get_session
from app.models import Author, Video


def upsert_author(author: Author, session: Session | None = None) -> Author:
    """
    Insert or update an author record.
    
    Uses sec_uid as the unique identifier for idempotency.
    Updates all fields except created_at if record exists.
    
    Args:
        author: Author model instance to upsert
        session: Optional SQLModel session (creates new one if not provided)
        
    Returns:
        The upserted Author instance
    """

    should_close = False
    if session is None:
        session = get_session()
        should_close = True

    try:
        # Try to find existing author by sec_uid
        statement = select(Author).where(Author.sec_uid == author.sec_uid)
        existing = session.exec(statement).first()

        if existing:
            # Update existing record
            existing.unique_id = author.unique_id
            existing.nickname = author.nickname
            existing.avatar_url = author.avatar_url
            existing.follower_count = author.follower_count
            existing.following_count = author.following_count
            existing.aweme_count = author.aweme_count
            existing.verified = author.verified
            existing.signature = author.signature
            existing.region = author.region
            existing.last_sync_time = author.last_sync_time
            existing.updated_at = datetime.utcnow()
            session.add(existing)
            session.commit()
            session.refresh(existing)
            return existing
        else:
            # Insert new record
            session.add(author)
            session.commit()
            session.refresh(author)
            return author
    finally:
        if should_close:
            session.close()


def upsert_videos(videos: list[Video], session: Session | None = None) -> list[Video]:
    """
    Insert or update multiple video records in batch.
    
    Uses aweme_id as the unique identifier for idempotency.
    Updates all fields except created_at if record exists.
    
    Args:
        videos: List of Video model instances to upsert
        session: Optional SQLModel session (creates new one if not provided)
        
    Returns:
        List of upserted Video instances
    """

    should_close = False
    if session is None:
        session = get_session()
        should_close = True

    try:
        result = []
        for video in videos:
            # Try to find existing video by aweme_id
            statement = select(Video).where(Video.aweme_id == video.aweme_id)
            existing = session.exec(statement).first()

            if existing:
                # Update existing record
                existing.author_sec_uid = video.author_sec_uid
                existing.desc = video.desc
                existing.create_time = video.create_time
                existing.duration = video.duration
                existing.cover_url = video.cover_url
                existing.play_count = video.play_count
                existing.digg_count = video.digg_count
                existing.comment_count = video.comment_count
                existing.share_count = video.share_count
                existing.collect_count = video.collect_count
                existing.is_pinned = video.is_pinned
                existing.music_id = video.music_id
                existing.music_name = video.music_name
                existing.play_urls = video.play_urls
                existing.crawl_time = video.crawl_time
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                result.append(existing)
            else:
                # Insert new record
                session.add(video)
                result.append(video)

        session.commit()
        for item in result:
            session.refresh(item)
        return result
    finally:
        if should_close:
            session.close()


def list_videos(
    author_sec_uid: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    session: Session | None = None,
) -> tuple[list[Video], int]:
    """
    List videos with optional filtering and pagination.
    
    Args:
        author_sec_uid: Optional filter by author's sec_uid
        page: Page number (1-based)
        page_size: Number of results per page
        session: Optional SQLModel session (creates new one if not provided)
        
    Returns:
        Tuple of (list of videos, total count)
    """

    should_close = False
    if session is None:
        session = get_session()
        should_close = True

    try:
        if page < 1:
            raise ValueError("page must be >= 1")
        if page_size < 1:
            raise ValueError("page_size must be >= 1")

        # Build base query
        base_statement = select(Video)

        # Apply filters
        if author_sec_uid:
            base_statement = base_statement.where(Video.author_sec_uid == author_sec_uid)

        # Count total
        count_statement = select(func.count()).select_from(base_statement.subquery())
        total = session.exec(count_statement).one()[0]

        # Apply ordering and pagination
        paginated_statement = (
            base_statement.order_by(desc(Video.create_time), desc(Video.aweme_id))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        videos = list(session.exec(paginated_statement).all())
        return videos, total
    finally:
        if should_close:
            session.close()


def get_latest_for_author(
    author_sec_uid: str, session: Session | None = None
) -> Optional[Video]:
    """
    Get the latest video for a specific author.
    
    Ordering is by create_time (descending), then aweme_id (descending).
    
    Args:
        author_sec_uid: Author's sec_uid to filter by
        session: Optional SQLModel session (creates new one if not provided)
        
    Returns:
        The latest Video or None if no videos found
    """

    should_close = False
    if session is None:
        session = get_session()
        should_close = True

    try:
        statement = (
            select(Video)
            .where(Video.author_sec_uid == author_sec_uid)
            .order_by(desc(Video.create_time), desc(Video.aweme_id))
            .limit(1)
        )
        return session.exec(statement).first()
    finally:
        if should_close:
            session.close()


def export_to_csv(output_path: pathlib.Path, session: Session | None = None) -> int:
    """
    Export all videos to a CSV file.
    
    Args:
        output_path: Path to the output CSV file
        session: Optional SQLModel session (creates new one if not provided)
        
    Returns:
        Number of videos exported
    """

    should_close = False
    if session is None:
        session = get_session()
        should_close = True

    try:
        statement = select(Video).order_by(desc(Video.create_time))
        videos = session.exec(statement).all()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "aweme_id",
                "author_sec_uid",
                "desc",
                "create_time",
                "duration",
                "cover_url",
                "play_count",
                "digg_count",
                "comment_count",
                "share_count",
                "collect_count",
                "is_pinned",
                "music_id",
                "music_name",
                "play_urls",
                "crawl_time",
                "created_at",
                "updated_at",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for video in videos:
                writer.writerow(
                    {
                        "aweme_id": video.aweme_id,
                        "author_sec_uid": video.author_sec_uid,
                        "desc": video.desc,
                        "create_time": video.create_time.isoformat(),
                        "duration": video.duration,
                        "cover_url": video.cover_url,
                        "play_count": video.play_count,
                        "digg_count": video.digg_count,
                        "comment_count": video.comment_count,
                        "share_count": video.share_count,
                        "collect_count": video.collect_count,
                        "is_pinned": video.is_pinned,
                        "music_id": video.music_id,
                        "music_name": video.music_name,
                        "play_urls": json.dumps(video.play_urls, ensure_ascii=False)
                        if video.play_urls is not None
                        else "",
                        "crawl_time": video.crawl_time.isoformat(),
                        "created_at": video.created_at.isoformat(),
                        "updated_at": video.updated_at.isoformat(),
                    }
                )

        return len(videos)
    finally:
        if should_close:
            session.close()

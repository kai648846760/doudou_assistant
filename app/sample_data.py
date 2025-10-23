"""Utility to seed the database with sample data."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.database import init_db
from app.models import Author, Video
from app.repository import upsert_author, upsert_videos


def seed_sample_data() -> None:
    """Insert a sample author and related videos into the database."""

    init_db()

    author = Author(
        sec_uid="sample_author_123",
        unique_id="sample_author",
        nickname="Sample Author",
        avatar_url="https://example.com/avatar.jpg",
        follower_count=12345,
        following_count=150,
        aweme_count=42,
        verified=True,
        signature="Sample signature",
        region="CN",
    )
    upsert_author(author)

    base_time = datetime.utcnow() - timedelta(days=1)

    videos = [
        Video(
            aweme_id="sample_video_001",
            author_sec_uid=author.sec_uid,
            desc="Sample video 1",
            create_time=base_time,
            duration=15000,
            play_count=1000,
            digg_count=150,
            comment_count=40,
            share_count=20,
            collect_count=5,
            is_pinned=False,
            music_id="music_001",
            music_name="Sample Track 1",
            play_urls={"url": "https://example.com/sample_video_1.mp4"},
        ),
        Video(
            aweme_id="sample_video_002",
            author_sec_uid=author.sec_uid,
            desc="Sample video 2",
            create_time=base_time + timedelta(hours=2),
            duration=20000,
            play_count=2000,
            digg_count=250,
            comment_count=60,
            share_count=35,
            collect_count=10,
            is_pinned=True,
            music_id="music_002",
            music_name="Sample Track 2",
            play_urls={"url": "https://example.com/sample_video_2.mp4"},
        ),
    ]

    upsert_videos(videos)


if __name__ == "__main__":
    seed_sample_data()
    print("Sample data inserted into data/douyin.db")

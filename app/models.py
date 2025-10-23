"""SQLModel models for authors and videos."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column, Index
from sqlmodel import Field, SQLModel


class Author(SQLModel, table=True):
    """Author/creator model representing a Douyin user."""

    __tablename__ = "authors"

    id: Optional[int] = Field(default=None, primary_key=True)
    sec_uid: str = Field(index=True, unique=True, description="Secure user ID")
    unique_id: Optional[str] = Field(default=None, description="User's unique ID")
    nickname: str = Field(description="Display name")
    avatar_url: Optional[str] = Field(default=None, description="Avatar image URL")
    follower_count: int = Field(default=0, description="Number of followers")
    following_count: int = Field(default=0, description="Number of following")
    aweme_count: int = Field(default=0, description="Number of videos")
    verified: bool = Field(default=False, description="Whether user is verified")
    signature: Optional[str] = Field(default=None, description="User bio/signature")
    region: Optional[str] = Field(default=None, description="User region/location")
    last_sync_time: Optional[datetime] = Field(
        default=None, description="Last time data was synced"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record last update time"
    )


class Video(SQLModel, table=True):
    """Video model representing a Douyin video/aweme."""

    __tablename__ = "videos"
    __table_args__ = (Index("idx_author_sec_uid", "author_sec_uid"),)

    aweme_id: str = Field(primary_key=True, description="Aweme/video ID")
    author_sec_uid: str = Field(
        index=True, description="Author's secure user ID (foreign reference)"
    )
    desc: Optional[str] = Field(default=None, description="Video description/caption")
    create_time: datetime = Field(description="Video creation/publish time")
    duration: int = Field(default=0, description="Video duration in milliseconds")
    cover_url: Optional[str] = Field(default=None, description="Video cover image URL")
    play_count: int = Field(default=0, description="Number of plays")
    digg_count: int = Field(default=0, description="Number of likes")
    comment_count: int = Field(default=0, description="Number of comments")
    share_count: int = Field(default=0, description="Number of shares")
    collect_count: int = Field(default=0, description="Number of collections/saves")
    is_pinned: bool = Field(default=False, description="Whether video is pinned")
    music_id: Optional[str] = Field(default=None, description="Music/sound ID")
    music_name: Optional[str] = Field(default=None, description="Music/sound name")
    play_urls: Optional[dict] = Field(
        default=None, sa_column=Column(JSON), description="Video play URLs as JSON"
    )
    crawl_time: datetime = Field(
        default_factory=datetime.utcnow, description="Time when video was crawled"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record creation time"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow, description="Record last update time"
    )

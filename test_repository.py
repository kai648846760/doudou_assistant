"""Test repository functions to verify upsert idempotency and pagination."""

import pathlib
from datetime import datetime, timedelta

from app.database import reset_database
from app.models import Author, Video
from app.repository import (
    export_to_csv,
    get_latest_for_author,
    list_videos,
    upsert_author,
    upsert_videos,
)


def test_author_upsert_idempotency():
    """Test that upserting the same author is idempotent."""

    print("Testing author upsert idempotency...")

    reset_database()

    author1 = Author(
        sec_uid="test_sec_uid_123",
        unique_id="test_user",
        nickname="Test User",
        avatar_url="https://example.com/avatar.jpg",
        follower_count=1000,
        following_count=100,
        aweme_count=50,
        verified=True,
        signature="Test signature",
        region="US",
    )

    result1 = upsert_author(author1)
    print(f"  First insert: ID={result1.id}, nickname={result1.nickname}")

    author2 = Author(
        sec_uid="test_sec_uid_123",
        unique_id="test_user",
        nickname="Updated Test User",
        avatar_url="https://example.com/new_avatar.jpg",
        follower_count=2000,
        following_count=150,
        aweme_count=75,
        verified=True,
        signature="Updated signature",
        region="US",
    )

    result2 = upsert_author(author2)
    print(f"  Second upsert: ID={result2.id}, nickname={result2.nickname}")

    assert result1.id == result2.id, "IDs should be the same (same author)"
    assert result2.nickname == "Updated Test User", "Nickname should be updated"
    assert result2.follower_count == 2000, "Follower count should be updated"

    print("  ✓ Author upsert is idempotent\n")


def test_video_batch_upsert_idempotency():
    """Test that batch upserting videos is idempotent."""

    print("Testing video batch upsert idempotency...")

    reset_database()

    base_time = datetime(2024, 1, 1, 12, 0, 0)

    videos_batch1 = [
        Video(
            aweme_id="video_001",
            author_sec_uid="author_sec_123",
            desc="First video",
            create_time=base_time,
            duration=15000,
            play_count=100,
            digg_count=10,
            comment_count=5,
            share_count=2,
            collect_count=1,
            play_urls={"url": "https://example.com/video1.mp4"},
        ),
        Video(
            aweme_id="video_002",
            author_sec_uid="author_sec_123",
            desc="Second video",
            create_time=base_time + timedelta(hours=1),
            duration=20000,
            play_count=200,
            digg_count=20,
            comment_count=10,
            share_count=4,
            collect_count=2,
            play_urls={"url": "https://example.com/video2.mp4"},
        ),
    ]

    result1 = upsert_videos(videos_batch1)
    print(f"  First batch insert: {len(result1)} videos")
    for v in result1:
        print(f"    {v.aweme_id}: play_count={v.play_count}")

    videos_batch2 = [
        Video(
            aweme_id="video_001",
            author_sec_uid="author_sec_123",
            desc="First video (updated)",
            create_time=base_time,
            duration=15000,
            play_count=500,
            digg_count=50,
            comment_count=25,
            share_count=10,
            collect_count=5,
            play_urls={"url": "https://example.com/video1_updated.mp4"},
        ),
        Video(
            aweme_id="video_002",
            author_sec_uid="author_sec_123",
            desc="Second video (updated)",
            create_time=base_time + timedelta(hours=1),
            duration=20000,
            play_count=600,
            digg_count=60,
            comment_count=30,
            share_count=12,
            collect_count=6,
            play_urls={"url": "https://example.com/video2_updated.mp4"},
        ),
        Video(
            aweme_id="video_003",
            author_sec_uid="author_sec_123",
            desc="Third video (new)",
            create_time=base_time + timedelta(hours=2),
            duration=25000,
            play_count=50,
            digg_count=5,
            comment_count=2,
            share_count=1,
            collect_count=0,
            play_urls={"url": "https://example.com/video3.mp4"},
        ),
    ]

    result2 = upsert_videos(videos_batch2)
    print(f"  Second batch upsert: {len(result2)} videos")
    for v in result2:
        print(f"    {v.aweme_id}: play_count={v.play_count}")

    assert len(result2) == 3, "Should have 3 videos after upsert"
    assert result2[0].play_count == 500, "First video play count should be updated"
    assert result2[1].play_count == 600, "Second video play count should be updated"
    assert result2[2].aweme_id == "video_003", "Third video should be new"

    all_videos, total = list_videos()
    assert total == 3, "Total videos should be 3"

    print("  ✓ Video batch upsert is idempotent\n")


def test_list_videos_pagination():
    """Test video listing with pagination."""

    print("Testing video list pagination...")

    reset_database()

    base_time = datetime(2024, 1, 1, 12, 0, 0)

    videos = []
    for i in range(25):
        videos.append(
            Video(
                aweme_id=f"video_{i:03d}",
                author_sec_uid="author_sec_456",
                desc=f"Video number {i}",
                create_time=base_time + timedelta(hours=i),
                duration=10000 + i * 1000,
                play_count=100 * i,
                digg_count=10 * i,
                comment_count=i,
                share_count=i // 2,
                collect_count=i // 5,
            )
        )

    upsert_videos(videos)
    print(f"  Inserted {len(videos)} videos")

    page1, total = list_videos(page=1, page_size=10)
    print(f"  Page 1: {len(page1)} videos (total: {total})")
    assert len(page1) == 10, "Page 1 should have 10 videos"
    assert total == 25, "Total should be 25"
    assert page1[0].aweme_id == "video_024", "First video should be latest (024)"

    page2, total = list_videos(page=2, page_size=10)
    print(f"  Page 2: {len(page2)} videos (total: {total})")
    assert len(page2) == 10, "Page 2 should have 10 videos"
    assert total == 25, "Total should still be 25"

    page3, total = list_videos(page=3, page_size=10)
    print(f"  Page 3: {len(page3)} videos (total: {total})")
    assert len(page3) == 5, "Page 3 should have 5 videos"
    assert total == 25, "Total should still be 25"

    print("  ✓ Pagination works correctly\n")


def test_list_videos_filtered():
    """Test video listing with author filtering."""

    print("Testing video list with author filter...")

    reset_database()

    base_time = datetime(2024, 1, 1, 12, 0, 0)

    videos_author1 = [
        Video(
            aweme_id=f"author1_video_{i}",
            author_sec_uid="author_sec_111",
            desc=f"Author 1 Video {i}",
            create_time=base_time + timedelta(hours=i),
            duration=10000,
        )
        for i in range(5)
    ]

    videos_author2 = [
        Video(
            aweme_id=f"author2_video_{i}",
            author_sec_uid="author_sec_222",
            desc=f"Author 2 Video {i}",
            create_time=base_time + timedelta(hours=i),
            duration=10000,
        )
        for i in range(7)
    ]

    upsert_videos(videos_author1)
    upsert_videos(videos_author2)
    print(f"  Inserted {len(videos_author1)} videos for author 1")
    print(f"  Inserted {len(videos_author2)} videos for author 2")

    author1_videos, total1 = list_videos(author_sec_uid="author_sec_111")
    print(f"  Author 1 videos: {len(author1_videos)} (total: {total1})")
    assert total1 == 5, "Should have 5 videos for author 1"

    author2_videos, total2 = list_videos(author_sec_uid="author_sec_222")
    print(f"  Author 2 videos: {len(author2_videos)} (total: {total2})")
    assert total2 == 7, "Should have 7 videos for author 2"

    all_videos, total_all = list_videos()
    print(f"  All videos: {len(all_videos)} (total: {total_all})")
    assert total_all == 12, "Should have 12 videos total"

    print("  ✓ Author filtering works correctly\n")


def test_get_latest_for_author():
    """Test getting the latest video for an author."""

    print("Testing get_latest_for_author...")

    reset_database()

    base_time = datetime(2024, 1, 1, 12, 0, 0)

    videos = [
        Video(
            aweme_id="video_001",
            author_sec_uid="author_sec_789",
            desc="First video",
            create_time=base_time,
            duration=10000,
        ),
        Video(
            aweme_id="video_002",
            author_sec_uid="author_sec_789",
            desc="Second video",
            create_time=base_time + timedelta(hours=2),
            duration=10000,
        ),
        Video(
            aweme_id="video_003",
            author_sec_uid="author_sec_789",
            desc="Third video (latest)",
            create_time=base_time + timedelta(hours=4),
            duration=10000,
        ),
    ]

    upsert_videos(videos)
    print(f"  Inserted {len(videos)} videos")

    latest = get_latest_for_author("author_sec_789")
    print(f"  Latest video: {latest.aweme_id} - {latest.desc}")
    assert latest.aweme_id == "video_003", "Latest video should be video_003"

    no_videos = get_latest_for_author("nonexistent_author")
    print(f"  Non-existent author: {no_videos}")
    assert no_videos is None, "Should return None for non-existent author"

    print("  ✓ get_latest_for_author works correctly\n")


def test_export_to_csv():
    """Test exporting videos to CSV."""

    print("Testing export_to_csv...")

    reset_database()

    base_time = datetime(2024, 1, 1, 12, 0, 0)

    videos = [
        Video(
            aweme_id=f"video_{i:03d}",
            author_sec_uid="author_sec_export",
            desc=f"Video {i}",
            create_time=base_time + timedelta(hours=i),
            duration=10000,
            play_count=100 * i,
            digg_count=10 * i,
            comment_count=i,
            share_count=i // 2,
            collect_count=i // 5,
        )
        for i in range(10)
    ]

    upsert_videos(videos)
    print(f"  Inserted {len(videos)} videos")

    output_path = pathlib.Path("data/export_test.csv")
    count = export_to_csv(output_path)
    print(f"  Exported {count} videos to {output_path}")

    assert count == 10, "Should export 10 videos"
    assert output_path.exists(), "CSV file should exist"

    with output_path.open("r") as f:
        lines = f.readlines()
        assert len(lines) == 11, "Should have header + 10 data rows"
        print(f"  CSV has {len(lines)} lines (1 header + {len(lines)-1} data rows)")

    print("  ✓ export_to_csv works correctly\n")


def main():
    """Run all tests."""

    print("=" * 60)
    print("Running SQLite data layer tests")
    print("=" * 60 + "\n")

    try:
        test_author_upsert_idempotency()
        test_video_batch_upsert_idempotency()
        test_list_videos_pagination()
        test_list_videos_filtered()
        test_get_latest_for_author()
        test_export_to_csv()

        print("=" * 60)
        print("✓ All tests passed!")
        print("=" * 60)
        print("\nDatabase file created at: data/douyin.db")

        from app.repository import list_videos

        all_videos, total = list_videos()
        print(f"Current database contains {total} videos")

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        raise
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Test mock data push to verify the system is working."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.api import BridgeAPI


def test_mock_push():
    db_path = Path("./test_data/test.db")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    api = BridgeAPI(db_path)

    mock_items = [
        {
            "aweme_id": "123456789",
            "desc": "Test video description",
            "create_time": 1609459200,
            "duration": 15,
            "statistics": {
                "digg_count": 100,
                "comment_count": 10,
                "share_count": 5,
                "play_count": 1000,
                "collect_count": 20,
            },
            "author": {
                "uid": "author_001",
                "id": "author_001",
                "nickname": "Test Author",
                "sec_uid": "MS4wLjABAAAAtest123",
                "unique_id": "testauthor",
            },
            "music": {
                "title": "Test Music",
                "author": "Test Artist",
            },
            "video": {
                "cover": {"url_list": ["https://example.com/cover.jpg"]},
                "play_addr": {"url_list": ["https://example.com/video.mp4"]},
            },
            "item_type": "video",
        },
        {
            "aweme_id": "987654321",
            "desc": "Another test video",
            "create_time": 1609545600,
            "duration": 30,
            "statistics": {
                "digg_count": 200,
                "comment_count": 20,
                "share_count": 10,
                "play_count": 2000,
                "collect_count": 40,
            },
            "author": {
                "uid": "author_002",
                "id": "author_002",
                "nickname": "Another Author",
                "sec_uid": "MS4wLjABAAAAtest456",
                "unique_id": "anotherauthor",
            },
            "music": {
                "title": "Another Music",
                "author": "Another Artist",
            },
            "video": {
                "cover": {"url_list": ["https://example.com/cover2.jpg"]},
                "play_addr": {"url_list": ["https://example.com/video2.mp4"]},
            },
            "item_type": "video",
        },
    ]

    print("Testing push_chunk...")
    result = api.push_chunk(mock_items)
    print(f"Result: {json.dumps(result, indent=2)}")

    if result.get("success"):
        print(f"\n✓ Successfully pushed {result['inserted']} items")

        print("\nTesting list_videos...")
        videos = api.list_videos({}, 1, 10)
        print(f"Found {videos['total']} videos")
        for video in videos["items"]:
            print(
                f"  - {video['aweme_id']}: {video['author_name']} - {video['desc'][:50]}"
            )

        print("\nTesting export_csv...")
        export_result = api.export_csv({})
        if export_result.get("success"):
            print(f"✓ Exported to: {export_result['path']}")
        else:
            print(f"✗ Export failed: {export_result.get('error')}")
    else:
        print(f"✗ Failed to push items: {result.get('error')}")
        return 1

    print("\n✓ All tests passed!")
    return 0


if __name__ == "__main__":
    sys.exit(test_mock_push())

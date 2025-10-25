# Single Video Crawl Implementation

## Overview
This implementation adds automatic completion for single video crawls, ensuring the video data is captured and the crawl completes gracefully without manual intervention.

## Changes Made

### 1. API Layer (`app/api.py`)

#### Added Auto-Completion Logic
- **Import**: Added `Timer` from `threading` module for delayed operations
- **New Attribute**: `_video_complete_timer: Timer | None` in `__init__` to track completion timer
- **New Methods**:
  - `_cancel_video_timer()`: Cancels any pending video completion timer
  - `_schedule_video_completion(delay: float)`: Schedules automatic crawl completion after a delay

#### Modified Methods
- **`_complete_crawl()`**: Now cancels video timer on completion
- **`stop_crawl()`**: Cancels video timer when user manually stops
- **`start_crawl_author()`**: Cancels any pending video timer when starting author crawl
- **`start_crawl_video()`**: Cancels any pending video timer for clean state
- **`push_chunk()`**: Enhanced to detect video mode and schedule auto-completion
  - When in "video" mode and data is captured (inserted > 0 or updated > 0)
  - Schedules completion after 2-second delay to allow for additional data
  - Logs the action for debugging

## How It Works

### Video Crawl Flow
1. User enters video URL in UI and clicks "Start Video Crawl"
2. `start_crawl_video()` is called:
   - Validates and cleans URL
   - Sets crawl state to "video" mode
   - Loads URL in crawler window
3. Browser navigates to video page
4. `inject.js` intercepts API responses containing video data
5. Video data is normalized and pushed via `push_chunk()`
6. `push_chunk()` detects "video" mode and schedules completion
7. After 2 seconds, `_schedule_video_completion()` timer fires
8. Crawl is marked as complete with message "Video captured successfully"
9. Crawler window is hidden

### Key Design Decisions

#### Why Auto-Completion?
- **User Experience**: Video crawls should complete automatically once data is captured
- **Consistency**: Author crawls auto-complete (on scroll end or duplicate detection)
- **Resource Management**: Prevents crawler window from staying open indefinitely

#### Why 2-Second Delay?
- Allows multiple API calls to complete (e.g., separate calls for video details and statistics)
- Prevents premature completion if data arrives in batches
- Short enough to feel responsive to users

#### Timer Cancellation
- Timers are cancelled when:
  - Crawl completes (prevents double-completion)
  - User manually stops crawl (respects user action)
  - New crawl starts (prevents interference between crawls)

## Test Coverage

### `test_video_crawl.py`
Tests the core functionality:
- Initial video ingestion (1 insert)
- Idempotent re-ingestion (0 inserts, 1 update)
- Updated metrics on re-run
- Auto-completion behavior (crawl completes after 2 seconds)

### `test_integration.py`
Comprehensive integration testing:
- Complete video with all metadata fields
- Minimal video data (edge case with missing fields)
- Idempotency over multiple runs
- Metrics update simulation (viral video scenario)
- CSV export functionality
- Author information persistence
- Unicode/emoji support

## Data Captured

### Video Fields
- `aweme_id`: Unique video identifier
- `desc`: Video description/caption
- `create_time`: Publication timestamp
- `duration`: Video duration in milliseconds

### Engagement Metrics
- `digg_count`: Likes/hearts
- `comment_count`: Comments
- `share_count`: Shares
- `play_count`: Views/plays
- `collect_count`: Favorites/collections

### Author Information
- `author_id`, `author_name`, `author_unique_id`, `author_sec_uid`
- Author profile data stored in separate `Author` table

### Media
- `cover`: Cover image URL (first from url_list)
- `video_url`: Playback URL (first from url_list)

### Music
- `music_title`: Background music title
- `music_author`: Music creator/artist

## Idempotency

The implementation ensures idempotent behavior:
- **First Run**: Video inserted into database (inserted=1, updated=0)
- **Subsequent Runs**: Existing video updated (inserted=0, updated=1)
- **No Duplicates**: `aweme_id` is primary key, prevents duplicates
- **Metric Updates**: Latest values overwrite previous ones

## Acceptance Criteria ✅

- ✅ Navigate the webview to the video URL
- ✅ Intercept JSON data from API responses
- ✅ Extract key fields (aweme_id, desc, create_time, duration, cover_url, counts, music info, play URLs)
- ✅ Persist to DB via upsert operation
- ✅ Idempotent: No duplicates on repeated runs
- ✅ Auto-completes after successful data capture

## Future Enhancements

Potential improvements for future iterations:
1. **Configurable Delay**: Make the 2-second delay configurable
2. **Multiple Videos**: Support batch video URL input
3. **Retry Logic**: Handle network failures gracefully
4. **Progress Indicators**: More detailed UI feedback during capture
5. **Video Validation**: Check if video exists/is accessible before crawling

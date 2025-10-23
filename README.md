# Douyin Author Crawler

A PyWebView-based application for crawling Douyin (TikTok China) author profiles and collecting their video posts (awemes).

## Features

- **Author Input Parsing**: Supports multiple input formats:
  - Douyin author homepage URLs (`https://www.douyin.com/user/MS4wL...`)
  - sec_uid (starts with `MS4`)
  - unique_id (author username)

- **Login State Detection**: Checks if user is logged in before starting a crawl

- **Auto-scroll with Throttling**: Simulates scrolling to load more content with intelligent throttling and end-of-list detection

- **Data Persistence**: Stores collected awemes in SQLite database using SQLModel

- **Deduplication**: Automatically dedupes by aweme_id to prevent duplicates

- **Incremental Sync**: Tracks the latest create_time/aweme_id per author to only collect new items on subsequent runs

- **Progress UI**: Real-time progress updates visible in the UI showing batch progress, total collected, and new items

## Installation

```bash
# Install dependencies using uv (recommended)
uv sync

# Or using pip
pip install -e .
```

## Usage

```bash
# Run the application
python -m app.main

# Or with uv
uv run python -m app.main
```

## Application Structure

### Tabs

1. **Login Tab**: 
   - Shows login status
   - Mock login button for testing
   - In production, would display Douyin login page

2. **Crawl Tab**:
   - Input field for author identifier (URL, unique_id, or sec_uid)
   - Start crawl button
   - Real-time progress display showing:
     - Current status
     - Progress messages
     - Total collected items
     - New items in current session

3. **Data Tab**:
   - Table displaying collected awemes
   - Shows aweme_id, description, create_time, and engagement metrics
   - Refresh button to reload data from database

## Architecture

### Backend (Python)

- **app/main.py**: Main application entry point, PyWebView window setup, and API class
- **app/models.py**: SQLModel database models (Author, Aweme)
- **app/db.py**: Database operations and queries
- **app/crawler.py**: Core crawler logic including:
  - Author input parsing
  - Crawl orchestration
  - Progress callbacks
  - Incremental sync logic

### Frontend (HTML/CSS/JS)

- **app/ui/index.html**: Application UI with three tabs
- **app/ui/styles.css**: Styling for the application
- **app/ui/app.js**: Frontend logic, tab management, and API integration

### Database Schema

**authors table:**
- id (primary key)
- unique_id (indexed)
- sec_uid (indexed)
- display_name
- latest_aweme_id (for incremental sync)
- latest_create_time (for incremental sync, indexed)
- total_awemes
- created_at, updated_at

**awemes table:**
- id (primary key)
- author_id (foreign key to authors, indexed)
- aweme_id (indexed, unique per author)
- desc (description)
- create_time (indexed)
- digg_count, collect_count, comment_count, share_count
- downloaded (boolean flag)
- created_at, updated_at

## Testing

To test the application:

1. Launch the app: `python -m app.main`
2. Click "Mock Login" button in the Login tab
3. Switch to the Crawl tab
4. Enter an author identifier (e.g., `test_author_123` or `MS4wLjABAAAA...`)
5. Click "Start Crawl"
6. Watch the progress updates in real-time
7. Switch to the Data tab to see collected items

## Incremental Sync Example

**First Run:**
```
Input: test_author_123
Result: Collected 60 new items (3 batches × 20 items)
```

**Second Run:**
```
Input: test_author_123
Result: Collected 0 new items (already synced)
```

**Third Run (after new content):**
```
Input: test_author_123
Result: Collected 20 new items (only new content since last run)
```

## Notes

- The current implementation uses a mock service for testing that generates deterministic aweme data
- In production, this would integrate with actual Douyin API/network interception
- The mock service ensures that subsequent runs of the same author produce consistent results for testing incremental sync
- All data is stored locally in SQLite database at `./data/webview_profile/crawler.db`

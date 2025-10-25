# DouDou Assistant - Douyin Data Crawler

A WebView-based crawler application for collecting and analyzing data from Douyin (Chinese TikTok). This application uses pywebview to provide a GUI interface for logging in, crawling author profiles, and exporting data to CSV.

## Quick Start

### Prerequisites

**Required for all platforms:**
- **Python 3.11 or higher**
- **[uv](https://github.com/astral-sh/uv)** - Fast Python package installer and resolver

**Platform-specific:**
- **Windows**: Microsoft Edge WebView2 Runtime (usually pre-installed on Windows 10/11)
  - If missing, the app will show a message with a download link
  - Download: https://developer.microsoft.com/microsoft-edge/webview2/
- **macOS**: macOS 10.10 or higher (uses built-in WKWebView, no additional dependencies)
- **Linux**: webkit2gtk package (typically pre-installed on most distributions)

### Installation

1. **Clone or download this repository**

2. **Install dependencies:**
   ```bash
   uv sync
   ```
   This creates a virtual environment and installs all required packages.

### Running the Application

Start the application:
```bash
uv run python -m app.main
```

The application will:
- Create a `./data/` directory for storing the database and session data
- Launch the DouDou Assistant GUI
- Initialize the SQLite database (`./data/douyin.db`)

### First-Time Setup

1. Click the **"Login"** tab
2. Click **"Open Douyin"**
3. Log in to your Douyin account in the browser window that opens
4. Click **"Check Login Status"** to verify
5. Your session is saved and will persist between application restarts

### Basic Usage

**To crawl an author's videos:**
1. Go to the **"Crawl"** tab
2. Enter an author profile URL (e.g., `https://www.douyin.com/user/MS4wLjABAAAA...`) or just the user ID
3. Click **"Start Author Crawl"**
4. The app will automatically scroll through the profile and collect all videos
5. View collected data in the **"Data"** tab

**To export data:**
1. Go to the **"Data"** tab
2. Apply any filters you want (optional)
3. Click **"Export to CSV"**
4. CSV files are saved to `./data/douyin_export_YYYYMMDD_HHMMSS.csv`

## Features

- **🔐 Persistent Login**: Log in once and your session persists between runs
- **👤 Author Profile Crawling**: Automatically scroll through and collect all videos from an author's profile
- **🎬 Single Video Crawling**: Extract details and metrics from individual videos
- **📊 Data Management**: View, filter, and paginate collected data
- **📁 CSV Export**: Export your data to CSV format with UTF-8 encoding
- **🔄 Incremental Sync**: Only new videos are added on subsequent crawls of the same author
- **🎯 Smart Deduplication**: Automatically prevents duplicate entries
- **🔄 Retry & Backoff**: Automatic retry with exponential backoff on transient errors
- **📝 Comprehensive Logging**: Detailed logs for debugging and monitoring

## Architecture

### Python Components

- **`app/main.py`**: Application entry point, sets up windows and API
- **`app/api.py`**: Bridge API exposed to JavaScript with methods for crawling, data management, and login
- **`app/db.py`**: Database layer with SQLModel for Author and Video tables
- **`app/crawler.py`**: Crawl state management and progress tracking
- **`app/inject.js`**: Injected script that hooks fetch/XMLHttpRequest to capture API responses
- **`app/scroll.js`**: Auto-scroll functionality for author profile pages

### JavaScript Components

- **`app/ui/index.html`**: User interface with Login, Crawl, and Data tabs
- **`app/ui/app.js`**: UI interactions, event handling, and API communication
- **`app/ui/styles.css`**: Styling with Douyin-inspired color scheme

## Detailed Usage

### Crawling Author Profiles

1. Navigate to the **"Crawl"** tab
2. Enter an author profile URL or ID in the **"Author Profile URL or ID"** field
   - Full URL: `https://www.douyin.com/user/MS4wLjABAAAA...`
   - Just the user ID: `MS4wLjABAAAA...`
   - Unique ID or sec_uid also supported
3. Click **"Start Author Crawl"**
4. The Douyin window will open and automatically:
   - Navigate to the author's profile
   - Scroll to load all videos
   - Capture video data as it loads
   - Detect when the end of the list is reached
5. Monitor progress in the "Crawl Status" section
6. When complete, the crawler window will close and data will be available in the **"Data"** tab

**Incremental Crawling**: If you crawl the same author again, only new videos (not already in the database) will be added.

### Crawling Single Videos

1. Navigate to the **"Crawl"** tab
2. Enter a video URL in the **"Video URL"** field
   - Example: `https://www.douyin.com/video/7123456789012345678`
3. Click **"Start Video Crawl"**
4. The video details and metrics will be captured and saved

### Viewing and Managing Data

1. Navigate to the **"Data"** tab
2. Use filters to narrow down results:
   - **Author**: Filter by author name or ID
   - **From/To**: Filter by date range
3. Click **"Apply Filters"** or **"Reset"** to clear filters
4. Use pagination buttons to navigate through results
5. Click **"Refresh"** to reload the data table
6. Click **"Export to CSV"** to export current filtered data

### Exporting Data

CSV exports are saved to `./data/` with the format: `douyin_export_YYYYMMDD_HHMMSS.csv`

The CSV includes:
- Aweme ID
- Author information (ID, name, unique_id, sec_uid)
- Description
- Timestamps
- Engagement metrics (likes, comments, shares, plays, collects)
- Media URLs (cover, video)
- Music information

## Data Model

### Author Table

- `author_id` (primary key)
- `unique_id`, `sec_uid` (indexed)
- `nickname` (author name)
- `signature`, `avatar_thumb`
- `follower_count`, `following_count`, `aweme_count`
- `region`
- `received_at` (timestamp)

### Video Table

- `aweme_id` (primary key)
- `author_id`, `author_name`, `author_unique_id`, `author_sec_uid` (indexed)
- `desc` (description)
- `create_time` (indexed)
- `duration`
- Statistics: `digg_count`, `comment_count`, `share_count`, `play_count`, `collect_count`
- `region`
- Music: `music_title`, `music_author`
- Media: `cover`, `video_url`
- `item_type`
- `received_at` (timestamp)

## How It Works

### JavaScript Interception

The application injects JavaScript into the Douyin session that:

1. **Hooks `fetch()` and `XMLHttpRequest`**: Intercepts all network requests
2. **Detects aweme data**: Looks for JSON responses containing video lists (`aweme_list`) or video details (`aweme_detail`, `aweme_info`)
3. **Normalizes data**: Extracts relevant fields from the raw API responses
4. **Batches and sends**: Collects items and sends them to Python via `window.pywebview.api.push_chunk()`

### Auto-Scroll

For author profile crawling, a separate scroll script:

1. Automatically scrolls to the bottom of the page
2. Waits for new content to load (throttled to avoid overwhelming the page)
3. Detects when the page height stops changing (end of list)
4. Notifies the Python backend when scrolling is complete

### Incremental Sync

When crawling an author you've crawled before:

1. The system queries the database for the latest video by that author
2. The latest `aweme_id` and `create_time` are passed to the JavaScript context
3. As items are received, duplicates are detected at the database level
4. The crawl stops after receiving 3 consecutive batches with no new items

## Development

### File Structure

```
├── app/
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── api.py           # Bridge API
│   ├── db.py            # Database layer
│   ├── crawler.py       # Crawl state management
│   ├── inject.js        # JS injection for data capture
│   ├── scroll.js        # Auto-scroll functionality
│   └── ui/
│       ├── index.html   # UI markup
│       ├── app.js       # UI JavaScript
│       └── styles.css   # Styling
├── data/                # Created on first run
│   ├── douyin.db        # SQLite database
│   ├── webview_profile/ # Persistent login session
│   └── *.csv            # CSV exports
├── pyproject.toml       # Project metadata and dependencies
├── .ruff.toml           # Ruff linting configuration
├── .gitignore
└── README.md
```

### Adding New Data Fields

1. Update the `Video` or `Author` model in `app/db.py`
2. Update the normalization logic in `app/db.py::_normalize_item()` or `_normalize_author()`
3. Update the JS normalization in `app/inject.js::normalizeAweme()` if needed
4. Delete `data/douyin.db` to recreate the database schema

### Linting and Formatting

```bash
uv run ruff check .
uv run ruff format .
```

## Troubleshooting

### Windows: WebView2 Runtime Issues

**Symptom:** Application fails to start or shows "WebView2 not found" error.

**Solution:**
1. Download and install Microsoft Edge WebView2 Runtime:
   - https://developer.microsoft.com/microsoft-edge/webview2/
2. Choose the "Evergreen Standalone Installer" for the architecture (x64 or x86)
3. Restart the application after installation

**Note:** Windows 11 and recent Windows 10 versions include WebView2 by default. If you're on an older Windows 10, you may need to install it manually.

### macOS: WKWebView Notes

**System Requirements:**
- macOS 10.10 (Yosemite) or higher
- No additional dependencies required (WKWebView is built into macOS)

**Common Issues:**
- **"Cannot open application"**: Allow the application in System Preferences > Security & Privacy
- **Permission dialogs**: macOS may ask for permissions to access network or storage on first run

### Linux: WebKit Issues

**Missing Dependencies:**
If the application fails to start, ensure webkit2gtk is installed:

```bash
# Ubuntu/Debian
sudo apt install libwebkit2gtk-4.0-37

# Fedora
sudo dnf install webkit2gtk3

# Arch
sudo pacman -S webkit2gtk
```

### Login Issues

**Symptom:** "Login not detected" or session expires quickly.

**Solutions:**
1. Ensure you're completely logged in to Douyin (check for any verification steps)
2. Click "Open Douyin" and wait for the page to fully load before logging in
3. After logging in, navigate to your profile page to verify the session is active
4. Click "Check Login Status" to confirm
5. If cookies are being blocked, check your system's privacy settings

**Note:** Sessions are stored in `./data/webview_profile/` and persist between runs.

### Data Not Being Captured

**Symptom:** Crawl runs but no data appears in the database.

**Diagnosis:**
1. Check the console/terminal output for error messages (logs are verbose and helpful)
2. Verify you're logged in (some profiles require authentication)
3. Look for messages like "Captured N items" in the logs
4. Try the "Test with Mock Data" button to verify the data pipeline is working

**Common Causes:**
- Profile is private or restricted
- Network connectivity issues (watch for retry messages in logs)
- Douyin changed their API structure (check for JavaScript errors in logs)

### Performance Issues

**Symptom:** Application is slow or unresponsive during crawling.

**Solutions:**
1. The auto-scroll has built-in throttling (100ms minimum between scrolls)
2. Data is batched (250ms delay) to avoid overwhelming the database
3. Close other applications to free up memory
4. For very large profiles (1000+ videos), expect the crawl to take 5-10 minutes

### Database Issues

**"Database is locked":**
- Close any other applications or database tools accessing `data/douyin.db`
- The app uses SQLite which only allows one writer at a time
- If the error persists, check if any Python processes are still running

**Corrupt database:**
- Backup your `data/douyin.db` file
- Delete the corrupted file and restart the app
- The app will create a fresh database automatically

### Permission Errors

**Symptom:** Cannot create `./data/` directory or write to database.

**Solutions:**
- Ensure you have write permissions in the project directory
- On Linux/macOS, check with `ls -la` and use `chmod` if needed
- On Windows, run the application from a folder you own (not Program Files)

### Logging and Debugging

**To see more detailed logs:**
- All logs are printed to the console/terminal where you ran `uv run python -m app.main`
- Look for messages prefixed with `[INFO]`, `[WARNING]`, `[ERROR]`
- JavaScript console messages are piped to Python logs with `[JS Console]` prefix
- Logs include timestamps and module names for easy tracking

**Log Levels:**
- `INFO`: Normal operations (navigation, data received, etc.)
- `WARNING`: Recoverable issues (retries, missing optional data)
- `ERROR`: Serious problems (failed requests, database errors)
- `DEBUG`: Detailed information (scroll positions, batch sizes)

### Network/Retry Issues

**Symptom:** "Retrying in X seconds" messages in logs.

**Explanation:**
- The application automatically retries failed operations (up to 3 attempts)
- Exponential backoff is used (0.5s, 1s, 2s delays)
- This is normal for transient network issues

**If retries consistently fail:**
1. Check your internet connection
2. Verify you can access douyin.com in a regular browser
3. Check if a firewall or proxy is blocking connections
4. Look for specific error messages in the logs

## Acceptance Criteria

✅ `uv run python -m app.main` launches the GUI

✅ Users can log in to douyin.com inside the app and the session persists between runs

✅ Given an author homepage or unique_id/sec_uid, the app scrolls to the end, intercepts data, and stores 50+ items on first run

✅ Incremental runs add only new items without duplicates

✅ Given a single video URL, details and metrics are stored idempotently

✅ Data view shows stored videos with filters and pagination; manual refresh updates the table

✅ Export produces a CSV matching the current table rows (UTF-8 with headers)

✅ No Playwright dependency; only pywebview + minimal libs

## License

This project is for educational and research purposes only.

## Disclaimer

Please respect Douyin's Terms of Service and robots.txt. This tool is intended for personal use and data analysis only. Do not use it to scrape data in violation of applicable laws or regulations.

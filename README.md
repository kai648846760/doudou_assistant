# DouDou Assistant - Douyin Data Crawler

A WebView-based crawler application for collecting and analyzing data from Douyin (Chinese TikTok). This application uses pywebview to provide a GUI interface for logging in, crawling author profiles, and exporting data to CSV.

## Features

- **🔐 Persistent Login**: Log in once and your session persists between runs
- **👤 Author Profile Crawling**: Automatically scroll through and collect all videos from an author's profile
- **🎬 Single Video Crawling**: Extract details and metrics from individual videos
- **📊 Data Management**: View, filter, and paginate collected data
- **📁 CSV Export**: Export your data to CSV format with UTF-8 encoding
- **🔄 Incremental Sync**: Only new videos are added on subsequent crawls of the same author
- **🎯 Smart Deduplication**: Automatically prevents duplicate entries

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

## Prerequisites

### All Platforms

- **Python 3.11 or higher**
- **uv** - Fast Python package installer and resolver ([Install uv](https://github.com/astral-sh/uv))

### Windows

- **Microsoft Edge WebView2 Runtime** - Usually pre-installed on Windows 10/11
  - If not installed, download from: https://developer.microsoft.com/microsoft-edge/webview2/
  - The installer will prompt you if WebView2 is missing

### macOS

- **macOS 10.10 or higher** (uses built-in WKWebView)
- No additional dependencies required

## Download Pre-built Binaries

For convenience, pre-built single-file executables are available for download from the [GitHub Releases](../../releases) page of this repository.

### Windows

1. Download `doudou_assistant-windows.exe` from the latest release
2. Optionally verify the SHA256 checksum using the `.sha256` file
3. Double-click the `.exe` to run

**Important Notes:**
- **SmartScreen Warning**: Windows may display a "Windows protected your PC" warning because the executable is unsigned. Click **"More info"** and then **"Run anyway"** to proceed.
- **WebView2 Runtime**: If you see an error about missing WebView2, download and install it from: https://developer.microsoft.com/microsoft-edge/webview2/
- The app will create a `./data/` folder in the same directory as the executable for storing the database and session data.

### macOS

1. Download `doudou_assistant-mac.zip` from the latest release
2. Optionally verify the SHA256 checksum using the `.sha256` file
3. Extract the zip file to get `doudou_assistant.app`
4. Move the `.app` to your Applications folder (optional)
5. **First launch**: Right-click the app and select **"Open"**, then click **"Open"** in the dialog

**Important Notes:**
- **Gatekeeper Warning**: Because the app is unsigned, macOS Gatekeeper will block it by default. You must use right-click → Open the first time.
- **Alternative method**: If you prefer, you can remove the quarantine attribute from the terminal:
  ```bash
  xattr -r -d com.apple.quarantine /path/to/doudou_assistant.app
  ```
- The app will create a `./data/` folder in the same directory as the `.app` for storing the database and session data.

## Installation

1. **Clone the repository** (or ensure you're in the project directory):

```bash
cd doudou_assistant
```

2. **Install dependencies with uv**:

```bash
uv sync
```

This will:
- Create a virtual environment (`.venv/`)
- Install all required dependencies (pywebview, sqlmodel, sqlalchemy, pydantic, ruff)

## Usage

### Running the Application

Start the application using uv:

```bash
uv run python -m app.main
```

Or on some systems:

```bash
uv run python app/main.py
```

The application will:
1. Create a `./data/` directory for storing the database and profiles
2. Launch the DouDou Assistant GUI
3. Initialize the SQLite database (`./data/douyin.db`)

### Logging In to Douyin

1. Click on the **"Login"** tab
2. Click **"Open Douyin"** to open a browser window
3. Log in to your Douyin account in the browser window
4. Click **"Check Login Status"** to verify you're logged in
5. Your session is automatically saved in `./data/webview_profile/`

**Note**: The login persists between application restarts. You only need to log in once.

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

### Building Standalone Executables

To build standalone executables using PyInstaller:

**Prerequisites:**
```bash
uv sync
uv pip install pyinstaller
```

**Windows:**
```powershell
./scripts/build_win.ps1
```

**macOS:**
```bash
./scripts/build_mac.sh
```

The built artifacts will be in the `dist/` directory:
- Windows: `dist/doudou_assistant-windows.exe`
- macOS: `dist/doudou_assistant-mac.zip` (containing the `.app` bundle)

SHA256 checksums are automatically generated alongside each artifact.

## Troubleshooting

### Windows: "WebView2 not found"

Download and install Microsoft Edge WebView2 Runtime:
- https://developer.microsoft.com/microsoft-edge/webview2/

### macOS: "Cannot open application"

On macOS, you may need to allow the application in System Preferences > Security & Privacy.

### "Login not detected"

1. Make sure you're actually logged in to Douyin in the crawler window
2. Try clicking "Open Douyin" again and logging in
3. Check that cookies are not blocked in the webview

### "No data is being captured"

1. Verify you're logged in (some content may require login)
2. Check the Python console for errors
3. Open browser DevTools (if available) and look for JavaScript errors
4. Try the "Test with Mock Data" button to verify the data pipeline works

### Data directory permissions

If the app can't create `./data/`, ensure you have write permissions in the project directory.

### Database locked

If you see "database is locked" errors, close any other applications that might be accessing `data/douyin.db`.

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

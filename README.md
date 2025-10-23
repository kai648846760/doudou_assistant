# PyWebView Aweme Crawler

A WebView-based crawler application with JavaScript-to-Python bridge for streaming and persisting data from web applications that serve "aweme" (short-form video) content.

## Features

- **JavaScript Injection**: Hooks into `fetch()` and `XMLHttpRequest` to intercept API responses
- **Automatic Data Extraction**: Parses and normalizes aweme data from JSON responses
- **Streaming Bridge**: Batch-sends captured data from JavaScript to Python via pywebview bridge
- **SQLite Storage**: Deduplicates and persists data in a local SQLite database
- **Real-time Progress**: Emits progress events back to the UI for monitoring
- **Data Export**: Export captured data to CSV
- **Dual Window Architecture**: Separate UI and crawler windows for better workflow

## Architecture

### Python Components

- **`app/main.py`**: Application entry point, sets up windows and API
- **`app/api.py`**: Bridge API exposed to JavaScript with methods:
  - `login_state()`: Check login status
  - `start_crawl_author(input)`: Start crawling an author profile
  - `start_crawl_video(url)`: Start crawling a video
  - `push_chunk(items)`: Receive data chunks from JS
  - `list_videos(filters, page, page_size)`: Query stored videos
  - `export_csv(filters)`: Export data to CSV
  - `stop_crawl()`: Stop active crawl
  - `trigger_mock_push()`: Test with mock data
- **`app/db.py`**: Database layer with SQLModel/SQLAlchemy
- **`app/crawler.py`**: Crawl state management

### JavaScript Components

- **`app/inject.js`**: Injected script that:
  - Hooks fetch and XMLHttpRequest
  - Extracts aweme data from responses
  - Normalizes and batches items
  - Sends via `window.pywebview.api.push_chunk()`
- **`app/ui/app.js`**: UI interactions and event handling
- **`app/ui/index.html`**: User interface
- **`app/ui/styles.css`**: Styling

## Usage

### Installation

```bash
uv sync
```

### Running

```bash
uv run python -m app.main
```

### Testing with Mock Data

```bash
# In the UI, click "Test Mock Push" button
# OR run the test script:
uv run python test_mock.py
```

### Crawling Live Data

1. Click on the "Login" tab and log in to the target platform using the crawler window (if needed)
2. Navigate to the "Crawl" tab
3. Enter an author profile URL or video URL
4. Click "Start Author Crawl" or "Start Video Crawl"
5. The crawler window will open and navigate to the URL
6. Data will be automatically captured and displayed in the "Data" tab

### Console Access

From the UI console (F12), you can directly call API methods:

```javascript
// Start crawling an author
await pywebview.api.start_crawl_author("https://example.com/@username");

// Check crawl status
await pywebview.api.get_crawl_status();

// List videos
await pywebview.api.list_videos({}, 1, 20);

// Export to CSV
await pywebview.api.export_csv();
```

## Data Model

The `Aweme` model stores:

- `aweme_id` (primary key)
- `author_id`, `author_name`
- `desc` (description)
- `create_time`
- `duration`
- Statistics: `digg_count`, `comment_count`, `share_count`, `play_count`, `collect_count`
- `region`
- Music: `music_title`, `music_author`
- Media: `cover`, `video_url`
- `item_type`
- `received_at` (timestamp)

## Acceptance Criteria

✅ From UI console, calling `start_crawl_author` with a known author URL results in:
- `push_chunk` being invoked by the injected JavaScript
- Rows being written to the SQLite database
- Progress events being emitted to the UI

## Development

### File Structure

```
app/
├── main.py          # Entry point
├── api.py           # Bridge API
├── db.py            # Database layer
├── crawler.py       # Crawl state
├── inject.js        # JS injection script
└── ui/
    ├── index.html   # UI markup
    ├── app.js       # UI JavaScript
    └── styles.css   # Styling
```

### Adding New Data Fields

1. Update the `Aweme` model in `app/db.py`
2. Update the normalization logic in `app/db.py::_normalize_item()`
3. Update the JS normalization in `app/inject.js::normalizeAweme()`

## Notes

- Data is stored in `./data/aweme.db`
- WebView profile data is in `./data/webview_profile/`
- Crawler session data is in `./data/crawler_profile/`
- CSV exports are saved to `./data/`

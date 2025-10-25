# 豆豆助手 - 抖音数据采集工具

基于 WebView 的抖音数据采集应用程序，用于采集和分析抖音数据。本应用使用 pywebview 提供 GUI 界面，支持登录、爬取作者主页、导出数据到 CSV 等功能。

## 快速开始

### 系统要求

**所有平台：**
- **Python 3.11 或更高版本**
- **[uv](https://github.com/astral-sh/uv)** - 快速的 Python 包管理工具

**平台特定要求：**
- **Windows**：Microsoft Edge WebView2 运行时（Windows 10/11 通常已预装）
  - 如果缺失，应用会显示下载链接提示
  - 下载地址：https://developer.microsoft.com/microsoft-edge/webview2/
- **macOS**：macOS 10.10 或更高版本（使用内置 WKWebView，无需额外依赖）
- **Linux**：webkit2gtk 包（大多数发行版已预装）

### 安装

1. **克隆或下载本仓库**

2. **安装依赖：**
   ```bash
   uv sync
   ```
   这将创建虚拟环境并安装所有必需的包。

### 运行应用

启动应用程序：
```bash
uv run python -m app.main
```

应用程序会：
- 创建 `./data/` 目录存储数据库和会话数据
- 启动豆豆助手 GUI 界面
- 初始化 SQLite 数据库（`./data/douyin.db`）

### 首次使用设置

1. 点击 **"登录"** 标签页
2. 点击 **"打开抖音"**
3. 在打开的浏览器窗口中登录你的抖音账号
4. 点击 **"检查登录状态"** 验证登录
5. 会话会被保存，在应用重启后会持续有效

### 基本使用

**爬取作者视频：**
1. 进入 **"爬取"** 标签页
2. 输入作者主页 URL（如 `https://www.douyin.com/user/MS4wLjABAAAA...`）或用户 ID
3. 点击 **"开始爬取作者"**
4. 应用会自动滚动作者主页并采集所有视频
5. 在 **"数据"** 标签页查看采集的数据

**导出数据：**
1. 进入 **"数据"** 标签页
2. 可选：应用筛选条件
3. 点击 **"导出到 CSV"**
4. CSV 文件会保存到 `./data/douyin_export_YYYYMMDD_HHMMSS.csv`

## 下载已打包版本

在 [Releases](https://github.com/你的用户名/你的仓库名/releases) 页面可下载预编译版本：

- **Windows**：`DouDouAssistant.exe`（单文件可执行程序，无需安装 Python）
- **macOS**：`DouDouAssistant.zip`（解压后运行 .app）

**Windows 注意事项：**
- 首次运行需要安装 WebView2 运行时（如果尚未安装）
- 下载地址：https://developer.microsoft.com/microsoft-edge/webview2/

**macOS 注意事项：**
- 首次运行可能提示"无法打开，因为来自身份不明的开发者"
- 解决方法：右键点击应用 → 选择"打开" → 点击"打开"确认
- 或在"系统偏好设置" → "安全性与隐私"中允许运行

## 功能特性

- **🔐 持久登录**：登录一次，会话在重启后仍然有效
- **👤 作者主页爬取**：自动滚动并采集作者的所有视频
- **🎬 单视频爬取**：提取单个视频的详细信息和统计数据
- **📊 数据管理**：查看、筛选和分页浏览采集的数据
- **📁 CSV 导出**：导出数据到 CSV 格式（UTF-8 编码）
- **🔄 增量同步**：重复爬取同一作者时只添加新视频
- **🎯 智能去重**：自动防止重复条目
- **🔄 重试与退避**：遇到临时错误时自动重试（指数退避）
- **📝 详细日志**：便于调试和监控的详细日志

## 架构说明

### Python 组件

- **`app/main.py`**：应用入口，设置窗口和 API
- **`app/api.py`**：桥接 API，向 JavaScript 暴露爬取、数据管理、登录等方法
- **`app/db.py`**：数据库层，使用 SQLModel 定义 Author 和 Video 表
- **`app/crawler.py`**：爬取状态管理和进度跟踪
- **`app/inject.js`**：注入脚本，拦截 fetch/XMLHttpRequest 以捕获 API 响应
- **`app/scroll.js`**：作者主页的自动滚动功能

### JavaScript 组件

- **`app/ui/index.html`**：用户界面，包含登录、爬取和数据标签页
- **`app/ui/app.js`**：UI 交互、事件处理和 API 通信
- **`app/ui/styles.css`**：抖音风格的样式设计

## 详细使用指南

### 爬取作者主页

1. 进入 **"爬取"** 标签页
2. 在 **"作者主页 URL 或 ID"** 字段中输入作者主页 URL 或 ID
   - 完整 URL：`https://www.douyin.com/user/MS4wLjABAAAA...`
   - 仅用户 ID：`MS4wLjABAAAA...`
   - 也支持 unique_id 或 sec_uid
3. 点击 **"开始爬取作者"**
4. 抖音窗口会打开并自动：
   - 导航到作者主页
   - 滚动加载所有视频
   - 捕获视频数据
   - 检测列表末尾
5. 在"爬取状态"部分监控进度
6. 完成后爬取窗口会关闭，数据可在 **"数据"** 标签页查看

**增量爬取**：如果再次爬取同一作者，只会添加新视频（不在数据库中的）。

### 爬取单个视频

1. 进入 **"爬取"** 标签页
2. 在 **"视频 URL"** 字段输入视频 URL
   - 示例：`https://www.douyin.com/video/7123456789012345678`
3. 点击 **"开始爬取视频"**
4. 视频详情和统计数据会被捕获并保存

### 查看和管理数据

1. 进入 **"数据"** 标签页
2. 使用筛选器缩小结果范围：
   - **作者**：按作者名或 ID 筛选
   - **起止日期**：按日期范围筛选
3. 点击 **"应用筛选"** 或 **"重置"** 清除筛选
4. 使用分页按钮浏览结果
5. 点击 **"刷新"** 重新加载数据表
6. 点击 **"导出到 CSV"** 导出当前筛选的数据

### 导出数据

CSV 导出文件保存在 `./data/`，格式为：`douyin_export_YYYYMMDD_HHMMSS.csv`

CSV 包含：
- 视频 ID（Aweme ID）
- 作者信息（ID、昵称、unique_id、sec_uid）
- 描述
- 时间戳
- 互动数据（点赞、评论、分享、播放、收藏）
- 媒体 URL（封面、视频）
- 音乐信息

## 数据模型

### Author 表（作者）

- `author_id`（主键）
- `unique_id`、`sec_uid`（索引）
- `nickname`（作者昵称）
- `signature`、`avatar_thumb`
- `follower_count`、`following_count`、`aweme_count`
- `region`
- `received_at`（时间戳）

### Video 表（视频）

- `aweme_id`（主键）
- `author_id`、`author_name`、`author_unique_id`、`author_sec_uid`（索引）
- `desc`（描述）
- `create_time`（索引）
- `duration`
- 统计数据：`digg_count`、`comment_count`、`share_count`、`play_count`、`collect_count`
- `region`
- 音乐：`music_title`、`music_author`
- 媒体：`cover`、`video_url`
- `item_type`
- `received_at`（时间戳）

## 工作原理

### JavaScript 拦截

应用会向抖音会话注入 JavaScript，实现：

1. **拦截 `fetch()` 和 `XMLHttpRequest`**：拦截所有网络请求
2. **检测视频数据**：查找包含视频列表（`aweme_list`）或视频详情（`aweme_detail`、`aweme_info`）的 JSON 响应
3. **规范化数据**：从原始 API 响应中提取相关字段
4. **批量发送**：收集数据项并通过 `window.pywebview.api.push_chunk()` 发送到 Python

### 自动滚动

对于作者主页爬取，独立的滚动脚本会：

1. 自动滚动到页面底部
2. 等待新内容加载（节流以避免页面过载）
3. 检测页面高度停止变化（列表末尾）
4. 滚动完成时通知 Python 后端

### 增量同步

当爬取之前已爬取过的作者时：

1. 系统查询数据库中该作者的最新视频
2. 最新的 `aweme_id` 和 `create_time` 传递给 JavaScript 上下文
3. 接收数据时在数据库层面检测重复
4. 连续 3 批数据都没有新项目时停止爬取

## 开发指南

### 文件结构

```
├── app/
│   ├── __init__.py
│   ├── main.py          # 入口文件
│   ├── api.py           # 桥接 API
│   ├── db.py            # 数据库层
│   ├── crawler.py       # 爬取状态管理
│   ├── inject.js        # JS 注入脚本（数据捕获）
│   ├── scroll.js        # 自动滚动功能
│   └── ui/
│       ├── index.html   # UI 标记
│       ├── app.js       # UI JavaScript
│       └── styles.css   # 样式
├── scripts/             # 打包脚本
│   ├── build_win.ps1    # Windows 打包脚本
│   └── build_mac.sh     # macOS 打包脚本
├── data/                # 运行时创建
│   ├── douyin.db        # SQLite 数据库
│   ├── webview_profile/ # 持久登录会话
│   └── *.csv            # CSV 导出
├── .github/
│   └── workflows/
│       └── build.yml    # CI/CD 工作流
├── pyproject.toml       # 项目元数据和依赖
├── .ruff.toml           # Ruff 代码检查配置
├── .gitignore
└── README.md
```

### 添加新数据字段

1. 更新 `app/db.py` 中的 `Video` 或 `Author` 模型
2. 更新 `app/db.py` 中的 `_normalize_item()` 或 `_normalize_author()` 规范化逻辑
3. 如有需要，更新 `app/inject.js` 中的 `normalizeAweme()` JS 规范化逻辑
4. 删除 `data/douyin.db` 以重新创建数据库架构

### 代码检查和格式化

```bash
uv run ruff check .
uv run ruff format .
```

### 本地打包

**Windows（PowerShell）：**
```powershell
.\scripts\build_win.ps1
```
生成：`dist\DouDouAssistant.exe`

**macOS（Bash）：**
```bash
chmod +x ./scripts/build_mac.sh
./scripts/build_mac.sh
```
生成：`dist/DouDouAssistant.zip`

## 故障排除

### Windows：WebView2 运行时问题

**症状：**应用无法启动或显示"WebView2 not found"错误。

**解决方法：**
1. 下载并安装 Microsoft Edge WebView2 运行时：
   - https://developer.microsoft.com/microsoft-edge/webview2/
2. 选择与系统架构匹配的"Evergreen Standalone Installer"（x64 或 x86）
3. 安装后重启应用

**注意：**Windows 11 和较新的 Windows 10 版本默认包含 WebView2。旧版 Windows 10 可能需要手动安装。

### macOS：WKWebView 说明

**系统要求：**
- macOS 10.10（Yosemite）或更高版本
- 无需额外依赖（WKWebView 是 macOS 内置组件）

**常见问题：**
- **"无法打开应用"**：在"系统偏好设置" → "安全性与隐私"中允许应用运行
- **权限对话框**：macOS 首次运行时可能会请求网络或存储权限

### Linux：WebKit 问题

**缺少依赖：**
如果应用无法启动，确保已安装 webkit2gtk：

```bash
# Ubuntu/Debian
sudo apt install libwebkit2gtk-4.0-37

# Fedora
sudo dnf install webkit2gtk3

# Arch
sudo pacman -S webkit2gtk
```

### 登录问题

**症状：**"未检测到登录"或会话快速过期。

**解决方法：**
1. 确保已完全登录抖音（检查是否有验证步骤）
2. 点击"打开抖音"并等待页面完全加载后再登录
3. 登录后，导航到你的个人主页以验证会话是否活跃
4. 点击"检查登录状态"确认
5. 如果 Cookie 被阻止，检查系统的隐私设置

**注意：**会话存储在 `./data/webview_profile/` 中，重启后持续有效。

### 未捕获数据

**症状：**爬取运行但数据库中无数据。

**诊断：**
1. 检查控制台/终端输出的错误消息（日志详细且有帮助）
2. 验证已登录（某些主页需要身份验证）
3. 在日志中查找类似"Captured N items"的消息
4. 尝试"使用模拟数据测试"按钮验证数据管道是否正常

**常见原因：**
- 主页是私密或受限制的
- 网络连接问题（关注日志中的重试消息）
- 抖音更改了 API 结构（检查日志中的 JavaScript 错误）

### 性能问题

**症状：**爬取期间应用缓慢或无响应。

**解决方法：**
1. 自动滚动内置节流（最小间隔 100ms）
2. 数据批处理（250ms 延迟）避免数据库过载
3. 关闭其他应用以释放内存
4. 对于大型主页（1000+ 视频），预计爬取需要 5-10 分钟

### 数据库问题

**"数据库被锁定"：**
- 关闭其他正在访问 `data/douyin.db` 的应用或数据库工具
- 应用使用 SQLite，一次只允许一个写入者
- 如果错误持续，检查是否有 Python 进程仍在运行

**数据库损坏：**
- 备份 `data/douyin.db` 文件
- 删除损坏的文件并重启应用
- 应用会自动创建新数据库

### 权限错误

**症状：**无法创建 `./data/` 目录或写入数据库。

**解决方法：**
- 确保在项目目录中有写入权限
- Linux/macOS：用 `ls -la` 检查，必要时使用 `chmod`
- Windows：从你拥有的文件夹运行应用（不是 Program Files）

### 日志和调试

**查看更详细的日志：**
- 所有日志输出到运行 `uv run python -m app.main` 的控制台/终端
- 查找前缀为 `[INFO]`、`[WARNING]`、`[ERROR]` 的消息
- JavaScript 控制台消息以 `[JS Console]` 前缀传递到 Python 日志
- 日志包含时间戳和模块名，便于追踪

**日志级别：**
- `INFO`：正常操作（导航、接收数据等）
- `WARNING`：可恢复问题（重试、缺少可选数据）
- `ERROR`：严重问题（请求失败、数据库错误）
- `DEBUG`：详细信息（滚动位置、批次大小）

### 网络/重试问题

**症状：**日志中显示"Retrying in X seconds"消息。

**说明：**
- 应用会自动重试失败的操作（最多 3 次）
- 使用指数退避（0.5s、1s、2s 延迟）
- 这对于临时网络问题是正常的

**如果重试持续失败：**
1. 检查互联网连接
2. 验证可以在普通浏览器中访问 douyin.com
3. 检查防火墙或代理是否阻止连接
4. 查看日志中的具体错误消息

## 打 Tag 发布新版本

要发布新版本（如 v0.1.0）：

1. **在本地创建 Tag：**
   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

2. **或在 GitHub UI 创建：**
   - 进入仓库的 "Releases" 页面
   - 点击 "Create a new release"
   - 填写 Tag 版本（如 `v0.1.0`）
   - 填写发布标题和说明
   - 点击 "Publish release"

3. **自动构建：**
   - Tag 推送后会自动触发 GitHub Actions 工作流
   - 工作流会构建 Windows 和 macOS 版本
   - 构建完成后自动创建 GitHub Release
   - Release 页面会附上可下载的可执行文件和 SHA256 校验文件

4. **手动下载产物：**
   - 每次推送到 main 分支也会构建产物
   - 产物作为 Artifacts 上传到 Actions 运行记录
   - 可在 Actions 标签页下载测试版本

## 验收标准

✅ `uv run python -m app.main` 启动 GUI

✅ 用户可在应用内登录 douyin.com，会话在重启后持续有效

✅ 给定作者主页或 unique_id/sec_uid，应用滚动到末尾、拦截数据，首次运行存储 50+ 条目

✅ 增量运行只添加新条目，无重复

✅ 给定单个视频 URL，详情和统计数据幂等存储

✅ 数据视图显示已存储视频，支持筛选和分页；手动刷新更新表格

✅ 导出生成与当前表格行匹配的 CSV（UTF-8 带标题）

✅ 无 Playwright 依赖；仅 pywebview + 最小库

## 许可证

本项目仅用于教育和研究目的。

## 免责声明

请尊重抖音的服务条款和 robots.txt。本工具仅供个人使用和数据分析。请勿违反适用法律法规使用本工具爬取数据。

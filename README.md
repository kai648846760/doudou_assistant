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
  - 支持自定义存储路径（user_data_path），登录会话可持久化
- **macOS**：macOS 10.10 或更高版本（使用内置 WKWebView，无需额外依赖）
  - **注意**：WKWebView 不支持自定义存储路径，登录状态由系统管理
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
- 创建 `~/.doudou_assistant/` 目录存储数据库和会话数据
- 启动豆豆助手 GUI 界面
- 初始化 SQLite 数据库（`~/.doudou_assistant/douyin.db`）
- Windows：WebView2 会话数据存储在 `~/.doudou_assistant/webview_profile/`
- macOS：会话数据由 WKWebView 系统管理

### 首次使用设置

1. 点击 **"登录"** 标签页
2. 点击 **"登录抖音"** 按钮，系统会弹出独立的登录窗口
3. 在弹出的窗口中完成抖音账号登录（如长时间未响应，可关闭窗口后重新点击按钮）
4. 登录成功后窗口会自动关闭，也可手动点击 **"手动刷新"** 按钮核对当前登录状态
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
4. CSV 文件会保存到 `~/.doudou_assistant/douyin_export_YYYYMMDD_HHMMSS.csv`

## 发布与下载

在 [Releases](https://github.com/你的用户名/你的仓库名/releases) 页面可以获取最新的官方构建包。每次发布都会附带 Windows 与 macOS 两个平台的应用，以及对应的 SHA256 校验文件，方便你校验下载是否完整。

### 下载发布版本

- **Windows**：`DouDouAssistant.exe`（单文件可执行程序，无需本地 Python 环境）
  - 首次运行如提示缺少 WebView2，请从 https://developer.microsoft.com/microsoft-edge/webview2/ 下载并安装运行时。
  - 如遇 Windows SmartScreen 拦截，请点击“更多信息”→“仍要运行”继续启动。
  - 应用会在用户目录保存登录会话，可长期保持登录状态。
- **macOS**：`DouDouAssistant-macOS.zip`（解压后得到 `DouDouAssistant.app`，双击即可运行）
  - 初次启动可能被 Gatekeeper 拦截并提示“无法打开，因为来自身份不明的开发者”，可右键点击应用 → 选择“打开” → 再次确认即可。
  - 若 Gatekeeper 再次阻止，可在“系统设置”→“隐私与安全性”中允许运行该应用。
  - macOS 版本使用 WKWebView，不支持自定义存储路径，登录状态由系统管理。
- **校验文件**：同目录下的 `.sha256` 文件，用于校验下载是否被篡改。

### 验证 SHA256

1. 下载产物及对应的 `.sha256` 文件；
2. Windows 在 PowerShell 中运行 `Get-FileHash .\\DouDouAssistant.exe -Algorithm SHA256`，比较输出哈希与 `.sha256` 文件内容；
3. macOS 在终端执行 `shasum -a 256 DouDouAssistant-macOS.zip`，确认结果与 `.sha256` 文件一致；
4. 若哈希完全一致，即可放心使用。

### 如何打 Tag 发布

1. 确认 `main` 分支处于可发布状态，并完成必要的代码审查；
2. 在本地创建新的语义化版本号（例如 `v0.1.1`）并推送远端：
   ```bash
   git tag v0.1.1
   git push origin v0.1.1
   ```
3. 或者在 GitHub Releases 页面创建同名 Tag 并发布；
4. Tag 推送后，GitHub Actions 会自动构建 Windows EXE 与 macOS 应用压缩包，并生成对应的 SHA256 校验文件；
5. 工作流会自动创建 GitHub Release 并上传所有产物；
6. 若仅需验证构建，可在 Actions 页面手动运行 `main` 分支的工作流，并在运行详情的 Artifacts 中下载调试产物。

## 功能特性

- **🔐 持久登录**：登录一次，会话在重启后仍然有效（Windows 完全支持，macOS 由系统管理）
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

CSV 导出文件保存在 `~/.doudou_assistant/`，格式为：`douyin_export_YYYYMMDD_HHMMSS.csv`

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
├── ~/.doudou_assistant/ # 运行时创建（用户家目录）
│   ├── douyin.db        # SQLite 数据库
│   ├── webview_profile/ # 持久登录会话（仅 Windows）
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
生成：`dist/DouDouAssistant-macOS.zip`

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

**存储和会话管理：**
- **重要**：WKWebView 不支持自定义存储路径（user_data_path）
- 登录会话和 Cookie 由 macOS 系统的 WKWebView 管理
- 会话数据存储在系统默认位置，应用重启后通常会保持
- 如需清除登录状态，可在 Safari 设置中清除网站数据

**常见问题：**
- **"无法打开应用"**：在"系统偏好设置" → "安全性与隐私"中允许应用运行
- **权限对话框**：macOS 首次运行时可能会请求网络或存储权限
- **登录状态不持久**：这是 WKWebView 的限制，可能需要定期重新登录

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

**注意：**
- Windows：会话存储在 `~/.doudou_assistant/webview_profile/` 中，重启后持续有效
- macOS：会话由 WKWebView 系统管理，通常会持续但不保证

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
- 关闭其他正在访问 `~/.doudou_assistant/douyin.db` 的应用或数据库工具
- 应用使用 SQLite，一次只允许一个写入者
- 如果错误持续，检查是否有 Python 进程仍在运行

**数据库损坏：**
- 备份 `~/.doudou_assistant/douyin.db` 文件
- 删除损坏的文件并重启应用
- 应用会自动创建新数据库

### 权限错误

**症状：**无法创建 `~/.doudou_assistant/` 目录或写入数据库。

**解决方法：**
- 数据目录现在位于用户家目录（`~/.doudou_assistant`），通常有完全权限
- Linux/macOS：检查家目录权限 `ls -la ~`
- Windows：确保用户配置文件目录可写
- 如有必要，手动创建目录：`mkdir -p ~/.doudou_assistant`

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

## Windows 文件名限制与避免方法

### 为什么有这些限制？

Windows 文件系统对文件名和路径有特殊限制，这些限制源于历史原因和系统保留用途。违反这些限制会导致：
- Git 仓库在 Windows 上无法 checkout
- GitHub Actions Windows runner 构建失败
- 文件无法在 Windows 系统上创建或访问

### Windows 文件名禁止规则

**1. 禁止的字符**
以下字符不能出现在文件名或目录名中：
```
< > : " / \ | ? *
```

**示例违规**：
- ❌ `log: error.txt`（包含冒号）
- ❌ `file?.py`（包含问号）
- ❌ `output|pipe.log`（包含管道符）
- ✅ `log_error.txt`（使用下划线）
- ✅ `file.py`（移除问号）

**2. 禁止以空格或点结尾**
文件名和目录名不能以空格或点结尾：
```
❌ "file .txt"（尾随空格）
❌ "folder."（尾随点）
✅ "file.txt"（正常）
✅ "folder"（正常）
```

**3. 保留名称**
以下名称为 Windows 系统保留，不能用作文件名或目录名（不区分大小写，无论是否有扩展名）：
```
CON, PRN, AUX, NUL
COM1, COM2, COM3, COM4, COM5, COM6, COM7, COM8, COM9
LPT1, LPT2, LPT3, LPT4, LPT5, LPT6, LPT7, LPT8, LPT9
```

**示例违规**：
- ❌ `CON.txt`（保留名）
- ❌ `aux.log`（保留名，不区分大小写）
- ❌ `COM1`（保留名）
- ✅ `console.txt`（不是保留名）
- ✅ `auxiliary.log`（不是保留名）

### 如何避免违规

**开发时**：
1. 使用下划线 `_` 或连字符 `-` 代替特殊字符
2. 避免使用保留名称，即使在子目录中也要避免
3. 确保文件名不以空格或点结尾

**提交前检查**：
运行路径检查脚本：
```bash
# 在 Linux/macOS 上
./scripts/check_windows_paths.sh

# 在 Windows PowerShell 上
.\scripts\check_windows_paths.ps1
```

脚本会扫描仓库中所有 Git 追踪的文件，输出违规文件清单。

**CI/CD 保护**：
本仓库的 GitHub Actions 工作流在 Windows 构建前会自动运行路径检查，确保：
1. 发现违规文件时给出明确的中文错误提示
2. 阻止 Windows runner 在 checkout 阶段失败
3. 提供违规文件的完整列表，便于修复

### 常见问题

**Q: 为什么 Linux/macOS 上可以创建这些文件，但 Windows 不行？**  
A: Linux 和 macOS 的文件系统（如 ext4、APFS）允许更多字符，而 Windows 的 NTFS/FAT32 有历史遗留的限制。跨平台项目需要遵守最严格的规则。

**Q: 如果已经提交了违规文件怎么办？**  
A: 使用 `git rm` 删除违规文件，或用 `git mv` 重命名为合法名称，然后重新提交：
```bash
git rm "plitlines(), 1):"
git commit -m "删除 Windows 非法文件名"
```

**Q: 我可以在 .gitignore 中忽略这些文件吗？**  
A: 可以，但最好的做法是避免创建这些文件。如果是临时文件或工具生成的文件，应该加入 `.gitignore`。

## 验收标准

✅ `uv run python -m app.main` 启动 GUI

✅ 用户可在应用内登录 douyin.com，会话在重启后持续有效

✅ 给定作者主页或 unique_id/sec_uid，应用滚动到末尾、拦截数据，首次运行存储 50+ 条目

✅ 增量运行只添加新条目，无重复

✅ 给定单个视频 URL，详情和统计数据幂等存储

✅ 数据视图显示已存储视频，支持筛选和分页；手动刷新更新表格

✅ 导出生成与当前表格行匹配的 CSV（UTF-8 带标题）

✅ 无 Playwright 依赖；仅 pywebview + 最小库

✅ 路径检查脚本能正确识别 Windows 非法路径并在 CI 中阻止构建

✅ macOS 构建可独立完成并发布 Release

## 许可证

本项目仅用于教育和研究目的。

## 免责声明

请尊重抖音的服务条款和 robots.txt。本工具仅供个人使用和数据分析。请勿违反适用法律法规使用本工具爬取数据。

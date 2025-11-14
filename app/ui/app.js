// 全局 API 变量
let api = null;

document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".tab-button");
    const contents = document.querySelectorAll(".tab-content");
    const messageElement = document.getElementById("message");
    const statusElement = document.getElementById("crawl-status");
    const statsElement = document.getElementById("crawl-stats");
    const dataTbody = document.getElementById("data-tbody");
    const tableSummary = document.getElementById("table-summary");
    const pageInfo = document.getElementById("page-info");

    let currentPage = 1;
    let currentPageSize = 20;
    let currentFilters = {};
    let totalItems = 0;

    // 禁用所有交互按钮，直到 API 就绪
    function disableAllButtons() {
        document.querySelectorAll("button").forEach(btn => {
            if (!btn.classList.contains("tab-button")) {
                btn.disabled = true;
            }
        });
    }

    // 启用所有交互按钮
    function enableAllButtons() {
        document.querySelectorAll("button").forEach(btn => {
            btn.disabled = false;
        });
        // 停止按钮初始状态应为禁用
        const stopBtn = document.getElementById("stop-crawl-btn");
        if (stopBtn) stopBtn.disabled = true;
    }

    // 初始化时禁用所有按钮
    disableAllButtons();
    messageElement.textContent = "API 未就绪，请稍候...";

    // ------------------------------------------------------------
    // Tab switching
    // ------------------------------------------------------------
    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.getAttribute("data-tab");

            tabs.forEach((t) => t.classList.remove("active"));
            tab.classList.add("active");

            contents.forEach((content) => {
                if (content.id === target) {
                    content.classList.add("active");
                } else {
                    content.classList.remove("active");
                }
            });

            // 切换到登录标签时自动检查登录状态
            if (target === "login") {
                updateLoginStatus();
            }
        });
    });

    // ------------------------------------------------------------
    // Login tab
    // ------------------------------------------------------------
    async function updateLoginStatus() {
        const statusDot = document.getElementById("status-dot");
        const statusText = document.getElementById("status-text");
        const statusDetails = document.getElementById("status-details");

        if (!statusDot || !statusText || !statusDetails) {
            return;
        }

        if (!api) {
            statusDot.className = "status-dot checking";
            statusText.textContent = "等待 API 就绪...";
            statusDetails.textContent = "请稍候，界面初始化完成后即可检查登录状态。";
            return;
        }

        try {
            // 显示检查状态
            statusDot.className = "status-dot checking";
            statusText.textContent = "正在检查登录状态...";
            statusDetails.textContent = "";

            const result = await api.login_state();
            
            if (result.logged_in) {
                statusDot.className = "status-dot logged-in";
                statusText.textContent = "✓ 已登录抖音";
                statusDetails.textContent = "您已成功登录，可以开始采集数据。";
            } else {
                statusDot.className = "status-dot logged-out";
                statusText.textContent = "✗ 未登录";
                statusDetails.innerHTML =
                    '请点击<strong>“登录抖音”</strong>按钮，在弹出窗口中登录您的抖音账号。';
            }
        } catch (error) {
            statusDot.className = "status-dot logged-out";
            statusText.textContent = "✗ 检查登录状态失败";
            statusDetails.textContent = error.message || "登录状态检查出现未知错误。";
        }
    }

    document.getElementById("open-login-btn")?.addEventListener("click", async () => {
        if (!api) {
            alert("API 未就绪");
            return;
        }
        try {
            messageElement.textContent = "正在打开登录窗口...";
            const result = await api.open_login_window();
            if (result.success) {
                messageElement.textContent = result.message || "登录窗口已打开";
                // 登录成功后自动更新状态
                if (result.logged_in) {
                    setTimeout(updateLoginStatus, 500);
                }
            } else {
                alert(result.error || "打开登录窗口失败");
                messageElement.textContent = "就绪";
            }
        } catch (error) {
            alert("错误: " + error.message);
            messageElement.textContent = "就绪";
        }
    });

    document.getElementById("check-login-btn")?.addEventListener("click", async () => {
        await updateLoginStatus();
    });

    // ------------------------------------------------------------
    // Crawl tab
    // ------------------------------------------------------------
    function updateCrawlButtons(isActive) {
        const startAuthorBtn = document.getElementById("start-author-btn");
        const startVideoBtn = document.getElementById("start-video-btn");
        const stopBtn = document.getElementById("stop-crawl-btn");

        if (isActive) {
            startAuthorBtn.disabled = true;
            startVideoBtn.disabled = true;
            stopBtn.disabled = false;
        } else {
            startAuthorBtn.disabled = false;
            startVideoBtn.disabled = false;
            stopBtn.disabled = true;
        }
    }

    document.getElementById("start-author-btn")?.addEventListener("click", async () => {
        const urlInput = document.getElementById("author-url");
        const url = urlInput?.value?.trim();
        if (!url) {
            alert("请输入作者主页链接或 ID");
            return;
        }
        if (!api) {
            alert("API 未就绪");
            return;
        }
        try {
            const result = await api.start_crawl_author(url);
            if (result.success) {
                statusElement.textContent = "正在开始作者采集...";
                statusElement.className = "status-value running";
                messageElement.textContent = result.message || "采集已启动";
                updateCrawlButtons(true);
            } else {
                alert(result.error || "启动采集失败");
            }
        } catch (error) {
            alert("错误: " + error.message);
        }
    });

    document.getElementById("start-video-btn")?.addEventListener("click", async () => {
        const urlInput = document.getElementById("video-url");
        const url = urlInput?.value?.trim();
        if (!url) {
            alert("请输入视频链接");
            return;
        }
        if (!api) {
            alert("API 未就绪");
            return;
        }
        try {
            const result = await api.start_crawl_video(url);
            if (result.success) {
                statusElement.textContent = "正在开始视频采集...";
                statusElement.className = "status-value running";
                messageElement.textContent = result.message || "采集已启动";
                updateCrawlButtons(true);
            } else {
                alert(result.error || "启动采集失败");
            }
        } catch (error) {
            alert("错误: " + error.message);
        }
    });

    document.getElementById("stop-crawl-btn")?.addEventListener("click", async () => {
        if (!api) {
            alert("API 未就绪");
            return;
        }
        try {
            const result = await api.stop_crawl();
            if (result.success) {
                statusElement.textContent = "已停止";
                statusElement.className = "status-value stopped";
                messageElement.textContent = result.message || "采集已停止";
                updateCrawlButtons(false);
            } else {
                alert(result.error || "停止采集失败");
            }
        } catch (error) {
            alert("错误: " + error.message);
        }
    });

    document.getElementById("mock-push-btn")?.addEventListener("click", async () => {
        try {
            await api?.trigger_mock_push();
        } catch (error) {
            console.error("触发模拟数据推送失败", error);
        }
    });

    // ------------------------------------------------------------
    // Data tab: Filters
    // ------------------------------------------------------------
    document.getElementById("apply-filters-btn")?.addEventListener("click", () => {
        const authorValue = document.getElementById("filter-author")?.value?.trim();
        const fromValue = document.getElementById("filter-from")?.value?.trim();
        const toValue = document.getElementById("filter-to")?.value?.trim();

        currentFilters = {};
        if (authorValue) {
            if (authorValue.startsWith("MS4wLjABAAAA")) {
                currentFilters.sec_uid = authorValue;
            } else if (/^[a-zA-Z0-9_]{3,30}$/.test(authorValue) && !authorValue.includes(" ")) {
                currentFilters.unique_id = authorValue;
            } else {
                currentFilters.author_name = authorValue;
            }
        }
        if (fromValue) {
            currentFilters.date_from = fromValue;
        }
        if (toValue) {
            currentFilters.date_to = toValue;
        }

        currentPage = 1;
        loadData();
    });

    document.getElementById("reset-filters-btn")?.addEventListener("click", () => {
        const authorInput = document.getElementById("filter-author");
        const fromInput = document.getElementById("filter-from");
        const toInput = document.getElementById("filter-to");
        if (authorInput) authorInput.value = "";
        if (fromInput) fromInput.value = "";
        if (toInput) toInput.value = "";
        currentFilters = {};
        currentPage = 1;
        loadData();
    });

    // ------------------------------------------------------------
    // Data tab: Table actions
    // ------------------------------------------------------------
    document.getElementById("refresh-data-btn")?.addEventListener("click", async () => {
        await loadData();
    });

    document.getElementById("export-csv-btn")?.addEventListener("click", async () => {
        if (!api) {
            alert("API 未就绪");
            return;
        }
        try {
            const result = await api.export_csv(currentFilters);
            if (result.success) {
                alert("CSV 导出成功，文件路径：\n" + result.path);
            } else {
                alert(result.error || "导出 CSV 失败");
            }
        } catch (error) {
            alert("错误: " + error.message);
        }
    });

    // ------------------------------------------------------------
    // Data tab: Pagination
    // ------------------------------------------------------------
    document.getElementById("prev-page-btn")?.addEventListener("click", () => {
        if (currentPage > 1) {
            currentPage--;
            loadData();
        }
    });

    document.getElementById("next-page-btn")?.addEventListener("click", () => {
        const maxPage = Math.ceil(totalItems / currentPageSize);
        if (currentPage < maxPage) {
            currentPage++;
            loadData();
        }
    });

    // ------------------------------------------------------------
    // Data loading
    // ------------------------------------------------------------
    async function loadData() {
        if (!api) {
            return;
        }
        try {
            const result = await api.list_videos(currentFilters, currentPage, currentPageSize);
            totalItems = result.total || 0;
            renderData(result);
        } catch (error) {
            console.error("加载数据失败:", error);
        }
    }

    function renderData(result) {
        if (!result || !result.items || result.items.length === 0) {
            dataTbody.innerHTML = '<tr><td colspan="11" class="empty-state">暂无数据</td></tr>';
            tableSummary.textContent = "暂无数据";
            pageInfo.textContent = "第 1 页";
            document.getElementById("prev-page-btn").disabled = true;
            document.getElementById("next-page-btn").disabled = true;
            return;
        }

        const maxPage = Math.ceil(totalItems / currentPageSize);
        tableSummary.textContent = `显示 ${result.items.length} 条，共 ${totalItems} 条记录`;
        pageInfo.textContent = `第 ${currentPage} 页，共 ${maxPage} 页`;

        document.getElementById("prev-page-btn").disabled = currentPage <= 1;
        document.getElementById("next-page-btn").disabled = currentPage >= maxPage;

        dataTbody.innerHTML = result.items
            .map(
                (item) => {
                    const duration = item.duration ? `${Math.floor(item.duration / 1000)}秒` : "";
                    const createTime = item.create_time ? new Date(item.create_time).toLocaleDateString() : "";
                    const desc = (item.desc || "").replace(/"/g, "&quot;");
                    const descPreview = (item.desc || "").substring(0, 40);
                    return `
            <tr>
                <td>${item.aweme_id || ""}</td>
                <td>${item.author_name || "未知"}</td>
                <td><div class="text-ellipsis" title="${desc}">${descPreview}${item.desc && item.desc.length > 40 ? "..." : ""}</div></td>
                <td>${createTime}</td>
                <td>${duration}</td>
                <td>${item.digg_count || 0}</td>
                <td>${item.comment_count || 0}</td>
                <td>${item.share_count || 0}</td>
                <td>${item.play_count || 0}</td>
                <td>${item.collect_count || 0}</td>
                <td><div class="text-ellipsis" title="${(item.music_title || "").replace(/"/g, "&quot;")}">${(item.music_title || "").substring(0, 20)}${item.music_title && item.music_title.length > 20 ? "..." : ""}</div></td>
            </tr>
        `;
                }
            )
            .join("");
    }

    // ------------------------------------------------------------
    // Progress events
    // ------------------------------------------------------------
    window.addEventListener("crawl-progress", (event) => {
        const progress = event.detail;
        if (!progress) {
            return;
        }

        const errorDisplay = document.getElementById("error-display");

        // Update button states based on crawl activity
        updateCrawlButtons(progress.active);

        // 更新状态文本和样式
        if (progress.active) {
            const target = progress.target || "";
            const mode = progress.mode || "";
            const statusMsg = progress.status_message || `正在采集${mode}`;
            statusElement.textContent = `${statusMsg}`;
            statusElement.className = "status-value running";
            
            if (errorDisplay) {
                errorDisplay.style.display = "none";
            }
        } else {
            if (progress.last_error) {
                statusElement.textContent = "错误";
                statusElement.className = "status-value error";
                
                if (errorDisplay) {
                    errorDisplay.innerHTML = `<strong>错误:</strong> ${progress.last_error}`;
                    errorDisplay.style.display = "block";
                }
            } else {
                const statusMsg = progress.status_message || "就绪";
                statusElement.textContent = statusMsg;
                
                if (progress.status === "complete") {
                    statusElement.className = "status-value";
                } else if (progress.status === "stopped") {
                    statusElement.className = "status-value stopped";
                } else {
                    statusElement.className = "status-value";
                }
                
                if (errorDisplay) {
                    errorDisplay.style.display = "none";
                }
            }
        }

        // 更新统计信息
        if (statsElement) {
            statsElement.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">已接收</span>
                    <span class="stat-value">${progress.items_received || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">已插入</span>
                    <span class="stat-value">${progress.items_inserted || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">已更新</span>
                    <span class="stat-value">${progress.items_updated || 0}</span>
                </div>
            `;
        }

        // Auto-refresh data table when new items are added
        if (progress.items_inserted > 0 || progress.items_updated > 0) {
            loadData();
        }
    });

    document.addEventListener('pywebviewready', () => {
        console.log('PyWebView API 已就绪');
        api = window.pywebview.api;

        const messageElement = document.getElementById("message");
        if (messageElement) {
            messageElement.textContent = "就绪";
        }

        enableAllButtons();

        // 在 API 就绪后初始化按钮状态并刷新登录提示
        updateCrawlButtons(false);
        updateLoginStatus();
    });

    window.addEventListener('login-success', () => {
        console.log('收到登录成功事件');
        const messageElement = document.getElementById("message");
        if (messageElement) {
            messageElement.textContent = "登录成功";
        }

        setTimeout(() => {
            updateLoginStatus();
        }, 500);
    });

    window.addEventListener('login-timeout', () => {
        console.warn('登录状态检测超时');
        const messageElement = document.getElementById("message");
        if (messageElement) {
            messageElement.textContent = "登录检测超时，请重新尝试";
        }

        const statusDot = document.getElementById("status-dot");
        if (statusDot) {
            statusDot.className = "status-dot logged-out";
        }

        const statusText = document.getElementById("status-text");
        if (statusText) {
            statusText.textContent = "登录检测超时";
        }

        const statusDetails = document.getElementById("status-details");
        if (statusDetails) {
            statusDetails.innerHTML =
                '若已完成登录，请点击<strong>“手动刷新”</strong>按钮确认；否则请重新打开登录窗口。';
        }

        setTimeout(() => {
            updateLoginStatus();
        }, 500);
    });

    loadData();
});

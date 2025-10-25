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

    const api = window.pywebview?.api;

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

            // Auto-check login status when switching to login tab
            if (target === "login") {
                updateLoginStatus();
            }
        });
    });

    if (api) {
        messageElement.textContent = "Ready";
    } else {
        messageElement.textContent = "PyWebView API not available";
    }

    // ------------------------------------------------------------
    // Login tab
    // ------------------------------------------------------------
    async function updateLoginStatus() {
        if (!api) {
            return;
        }
        const statusDot = document.getElementById("status-dot");
        const statusText = document.getElementById("status-text");
        const statusDetails = document.getElementById("status-details");

        try {
            // Show checking state
            statusDot.className = "status-dot checking";
            statusText.textContent = "Checking login status...";
            statusDetails.textContent = "";

            const result = await api.login_state();
            
            if (result.logged_in) {
                statusDot.className = "status-dot logged-in";
                statusText.textContent = "✓ Logged in to Douyin";
                statusDetails.textContent = "You are successfully logged in and can start crawling.";
            } else {
                statusDot.className = "status-dot logged-out";
                statusText.textContent = "✗ Not logged in";
                statusDetails.innerHTML = 
                    'Please click <strong>"Open Douyin"</strong> and log in to your account to start crawling.';
            }
        } catch (error) {
            statusDot.className = "status-dot logged-out";
            statusText.textContent = "✗ Error checking login status";
            statusDetails.textContent = error.message;
        }
    }

    document.getElementById("open-login-btn")?.addEventListener("click", async () => {
        if (!api) {
            alert("API not available");
            return;
        }
        try {
            const result = await api.open_login();
            if (result.success) {
                messageElement.textContent = result.message || "Login window opened";
                setTimeout(updateLoginStatus, 1000);
            } else {
                alert(result.error || "Failed to open login window");
            }
        } catch (error) {
            alert("Error: " + error.message);
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
            alert("Please enter an author profile URL or ID");
            return;
        }
        if (!api) {
            alert("API not available");
            return;
        }
        try {
            const result = await api.start_crawl_author(url);
            if (result.success) {
                statusElement.textContent = "Starting author crawl...";
                statusElement.className = "status-value running";
                messageElement.textContent = result.message || "Crawl started";
                updateCrawlButtons(true);
            } else {
                alert(result.error || "Failed to start crawl");
            }
        } catch (error) {
            alert("Error: " + error.message);
        }
    });

    document.getElementById("start-video-btn")?.addEventListener("click", async () => {
        const urlInput = document.getElementById("video-url");
        const url = urlInput?.value?.trim();
        if (!url) {
            alert("Please enter a video URL");
            return;
        }
        if (!api) {
            alert("API not available");
            return;
        }
        try {
            const result = await api.start_crawl_video(url);
            if (result.success) {
                statusElement.textContent = "Starting video crawl...";
                statusElement.className = "status-value running";
                messageElement.textContent = result.message || "Crawl started";
                updateCrawlButtons(true);
            } else {
                alert(result.error || "Failed to start crawl");
            }
        } catch (error) {
            alert("Error: " + error.message);
        }
    });

    document.getElementById("stop-crawl-btn")?.addEventListener("click", async () => {
        if (!api) {
            alert("API not available");
            return;
        }
        try {
            const result = await api.stop_crawl();
            if (result.success) {
                statusElement.textContent = "Stopped";
                statusElement.className = "status-value stopped";
                messageElement.textContent = result.message || "Crawl stopped";
                updateCrawlButtons(false);
            } else {
                alert(result.error || "Failed to stop crawl");
            }
        } catch (error) {
            alert("Error: " + error.message);
        }
    });

    document.getElementById("mock-push-btn")?.addEventListener("click", async () => {
        try {
            await api?.trigger_mock_push();
        } catch (error) {
            console.error("Failed to trigger mock push", error);
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
            alert("API not available");
            return;
        }
        try {
            const result = await api.export_csv(currentFilters);
            if (result.success) {
                alert("CSV exported successfully to:\n" + result.path);
            } else {
                alert(result.error || "Failed to export CSV");
            }
        } catch (error) {
            alert("Error: " + error.message);
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
            console.error("Failed to load data:", error);
        }
    }

    function renderData(result) {
        if (!result || !result.items || result.items.length === 0) {
            dataTbody.innerHTML = '<tr><td colspan="11" class="empty-state">No records found</td></tr>';
            tableSummary.textContent = "No records found";
            pageInfo.textContent = "Page 1";
            document.getElementById("prev-page-btn").disabled = true;
            document.getElementById("next-page-btn").disabled = true;
            return;
        }

        const maxPage = Math.ceil(totalItems / currentPageSize);
        tableSummary.textContent = `Showing ${result.items.length} of ${totalItems} records`;
        pageInfo.textContent = `Page ${currentPage} of ${maxPage}`;

        document.getElementById("prev-page-btn").disabled = currentPage <= 1;
        document.getElementById("next-page-btn").disabled = currentPage >= maxPage;

        dataTbody.innerHTML = result.items
            .map(
                (item) => {
                    const duration = item.duration ? `${Math.floor(item.duration / 1000)}s` : "";
                    const createTime = item.create_time ? new Date(item.create_time).toLocaleDateString() : "";
                    const desc = (item.desc || "").replace(/"/g, "&quot;");
                    const descPreview = (item.desc || "").substring(0, 40);
                    return `
            <tr>
                <td>${item.aweme_id || ""}</td>
                <td>${item.author_name || "Unknown"}</td>
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

        // Update status text with appropriate styling
        if (progress.active) {
            const target = progress.target || "";
            const mode = progress.mode || "";
            const statusMsg = progress.status_message || `Crawling ${mode}`;
            statusElement.textContent = `${statusMsg}`;
            statusElement.className = "status-value running";
            
            if (errorDisplay) {
                errorDisplay.style.display = "none";
            }
        } else {
            if (progress.last_error) {
                statusElement.textContent = "Error";
                statusElement.className = "status-value error";
                
                if (errorDisplay) {
                    errorDisplay.innerHTML = `<strong>Error:</strong> ${progress.last_error}`;
                    errorDisplay.style.display = "block";
                }
            } else {
                const statusMsg = progress.status_message || "Ready";
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

        // Update stats with better formatting
        if (statsElement) {
            statsElement.innerHTML = `
                <div class="stat-item">
                    <span class="stat-label">Received</span>
                    <span class="stat-value">${progress.items_received || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Inserted</span>
                    <span class="stat-value">${progress.items_inserted || 0}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Updated</span>
                    <span class="stat-value">${progress.items_updated || 0}</span>
                </div>
            `;
        }

        // Auto-refresh data table when new items are added
        if (progress.items_inserted > 0 || progress.items_updated > 0) {
            loadData();
        }
    });

    // Initialize button states
    updateCrawlButtons(false);
    
    loadData();
});

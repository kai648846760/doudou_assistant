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
    document.getElementById("open-login-btn")?.addEventListener("click", async () => {
        if (!api) {
            alert("API not available");
            return;
        }
        try {
            const result = await api.open_login();
            if (result.success) {
                document.getElementById("login-status").textContent = result.message || "Login window opened";
            } else {
                alert(result.error || "Failed to open login window");
            }
        } catch (error) {
            alert("Error: " + error.message);
        }
    });

    document.getElementById("check-login-btn")?.addEventListener("click", async () => {
        if (!api) {
            alert("API not available");
            return;
        }
        try {
            const result = await api.login_state();
            document.getElementById("login-status").textContent = result.message || JSON.stringify(result);
        } catch (error) {
            alert("Error: " + error.message);
        }
    });

    // ------------------------------------------------------------
    // Crawl tab
    // ------------------------------------------------------------
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
                messageElement.textContent = result.message || "Crawl started";
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
                messageElement.textContent = result.message || "Crawl started";
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
                messageElement.textContent = result.message || "Crawl stopped";
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
            currentFilters.author_name = authorValue;
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
            dataTbody.innerHTML = '<tr><td colspan="7" class="empty-state">No records found</td></tr>';
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
                (item) => `
            <tr>
                <td>${item.aweme_id || ""}</td>
                <td>${item.author_name || "Unknown"}</td>
                <td><div class="text-ellipsis" title="${(item.desc || "").replace(/"/g, "&quot;")}">${
                    (item.desc || "").substring(0, 60)
                }${item.desc && item.desc.length > 60 ? "..." : ""}</div></td>
                <td>${item.digg_count || 0}</td>
                <td>${item.comment_count || 0}</td>
                <td>${item.share_count || 0}</td>
                <td>${item.create_time ? new Date(item.create_time).toLocaleDateString() : ""}</td>
            </tr>
        `
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

        if (progress.active) {
            const target = progress.target || "";
            const mode = progress.mode || "";
            const statusMsg = progress.status_message || `Crawling ${mode}`;
            statusElement.textContent = `${statusMsg} (${target.substring(0, 50)})`;
        } else {
            if (progress.last_error) {
                statusElement.textContent = `Error: ${progress.last_error}`;
            } else {
                const statusMsg = progress.status_message || "Ready";
                statusElement.textContent = statusMsg;
            }
        }

        if (statsElement) {
            statsElement.innerHTML = `
                <div>Received: ${progress.items_received || 0}</div>
                <div>Inserted: ${progress.items_inserted || 0}</div>
                <div>Updated: ${progress.items_updated || 0}</div>
                ${progress.status ? `<div>Status: ${progress.status}</div>` : ""}
            `;
        }

        if (progress.items_inserted > 0 || progress.items_updated > 0) {
            loadData();
        }
    });

    loadData();
});

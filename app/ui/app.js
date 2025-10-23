document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".tab-button");
    const contents = document.querySelectorAll(".tab-content");
    const messageElement = document.getElementById("message");
    const statusElement = document.getElementById("crawl-status");
    const statsElement = document.getElementById("crawl-stats");
    const dataTbody = document.getElementById("data-tbody");

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

    const api = window.pywebview?.api;

    if (api) {
        messageElement.textContent = "Ready";
    } else {
        messageElement.textContent = "PyWebView API not available";
    }

    document.getElementById("start-author-btn")?.addEventListener("click", async () => {
        const urlInput = document.getElementById("author-url");
        const url = urlInput?.value?.trim();
        if (!url) {
            alert("Please enter an author URL");
            return;
        }
        if (!api) {
            alert("API not available");
            return;
        }
        try {
            const result = await api.start_crawl_author(url);
            if (result.success) {
                statusElement.textContent = "Crawling...";
                messageElement.textContent = result.message;
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
                statusElement.textContent = "Crawling...";
                messageElement.textContent = result.message;
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
                messageElement.textContent = result.message;
            } else {
                alert(result.error || "Failed to stop crawl");
            }
        } catch (error) {
            alert("Error: " + error.message);
        }
    });

    document.getElementById("refresh-data-btn")?.addEventListener("click", async () => {
        await loadData();
    });

    document.getElementById("export-csv-btn")?.addEventListener("click", async () => {
        if (!api) {
            alert("API not available");
            return;
        }
        try {
            const result = await api.export_csv();
            if (result.success) {
                alert("Exported to: " + result.path);
            } else {
                alert(result.error || "Failed to export");
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

    async function loadData() {
        if (!api) {
            return;
        }
        try {
            const result = await api.list_videos({}, 1, 20);
            renderData(result);
        } catch (error) {
            console.error("Failed to load data:", error);
        }
    }

    function renderData(result) {
        if (!result || !result.items || result.items.length === 0) {
            dataTbody.innerHTML = '<tr><td colspan="5" class="empty-state">No records found</td></tr>';
            return;
        }
        dataTbody.innerHTML = result.items
            .map(
                (item) => `
            <tr>
                <td>${item.aweme_id || ""}</td>
                <td>${item.author_name || "Unknown"}</td>
                <td>${(item.desc || "").substring(0, 50)}${item.desc?.length > 50 ? "..." : ""}</td>
                <td>${item.digg_count || 0}</td>
                <td>${item.create_time ? new Date(item.create_time).toLocaleDateString() : ""}</td>
            </tr>
        `
            )
            .join("");
    }

    window.addEventListener("crawl-progress", (event) => {
        const progress = event.detail;
        if (!progress) {
            return;
        }

        if (progress.active) {
            statusElement.textContent = `Crawling (${progress.mode}: ${progress.target})`;
        } else {
            statusElement.textContent = progress.last_error ? `Error: ${progress.last_error}` : "Ready";
        }

        if (statsElement) {
            statsElement.innerHTML = `
                <div>Received: ${progress.items_received}</div>
                <div>Inserted: ${progress.items_inserted}</div>
                <div>Updated: ${progress.items_updated}</div>
            `;
        }

        if (progress.items_inserted > 0 || progress.items_updated > 0) {
            loadData();
        }
    });

    loadData();
});

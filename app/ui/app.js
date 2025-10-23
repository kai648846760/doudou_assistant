document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".tab-button");
    const contents = document.querySelectorAll(".tab-content");
    const messageElement = document.getElementById("message");

    const loginStatus = document.getElementById("login-status");
    const mockLoginBtn = document.getElementById("mock-login-btn");
    const startCrawlBtn = document.getElementById("start-crawl-btn");
    const crawlStatus = document.getElementById("crawl-status");
    const progressContainer = document.getElementById("progress-container");
    const progressMessage = document.getElementById("progress-message");
    const totalCollectedEl = document.getElementById("total-collected");
    const newItemsEl = document.getElementById("new-items");
    const refreshDataBtn = document.getElementById("refresh-data-btn");
    const dataTbody = document.getElementById("data-tbody");

    function switchTab(target) {
        tabs.forEach((t) => t.classList.remove("active"));
        contents.forEach((content) => {
            if (content.id === target) {
                content.classList.add("active");
            } else {
                content.classList.remove("active");
            }
        });

        const btn = document.querySelector(`.tab-button[data-tab="${target}"]`);
        if (btn) {
            btn.classList.add("active");
        }
    }

    tabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            const target = tab.getAttribute("data-tab");
            switchTab(target);
        });
    });

    window.showTab = (tabId) => {
        switchTab(tabId);
    };

    function setMessage(text) {
        messageElement.textContent = text;
    }

    function updateLoginStatus(loggedIn) {
        if (loggedIn) {
            loginStatus.textContent = "Logged in";
            loginStatus.classList.add("success");
            loginStatus.classList.remove("error");
        } else {
            loginStatus.textContent = "Not logged in";
            loginStatus.classList.add("error");
            loginStatus.classList.remove("success");
        }
    }

    function setCrawlStatus(status) {
        crawlStatus.textContent = status;
    }

    function resetProgress() {
        progressContainer.style.display = "none";
        progressMessage.textContent = "Initializing...";
        totalCollectedEl.textContent = "0";
        newItemsEl.textContent = "0";
    }

    function showProgress() {
        progressContainer.style.display = "block";
    }

    function renderAwemes(rows) {
        dataTbody.innerHTML = "";
        if (!rows || rows.length === 0) {
            const tr = document.createElement("tr");
            tr.innerHTML = '<td colspan="6" class="empty-state">No videos collected yet</td>';
            dataTbody.appendChild(tr);
            return;
        }

        rows.forEach((row) => {
            const tr = document.createElement("tr");
            const created = new Date(row.create_time * 1000).toLocaleString();
            tr.innerHTML = `
                <td>${row.aweme_id}</td>
                <td>${row.desc || ""}</td>
                <td>${created}</td>
                <td>${row.digg_count}</td>
                <td>${row.comment_count}</td>
                <td>${row.share_count}</td>
            `;
            dataTbody.appendChild(tr);
        });
    }

    async function refreshData() {
        if (!window.pywebview || !window.pywebview.api) {
            return;
        }
        try {
            const response = await window.pywebview.api.get_awemes();
            if (response.success) {
                renderAwemes(response.awemes);
            }
        } catch (error) {
            console.error("Failed to load awemes", error);
        }
    }

    mockLoginBtn.addEventListener("click", async () => {
        if (!window.pywebview || !window.pywebview.api) {
            return;
        }
        try {
            const response = await window.pywebview.api.set_login_status(true);
            updateLoginStatus(response.logged_in);
            setMessage("Logged in for testing purposes.");
        } catch (error) {
            console.error("Failed to set login status", error);
        }
    });

    startCrawlBtn.addEventListener("click", async () => {
        const authorInput = document.getElementById("author-input").value.trim();
        if (!authorInput) {
            setCrawlStatus("Please enter an author identifier");
            return;
        }

        if (!window.pywebview || !window.pywebview.api) {
            setCrawlStatus("PyWebView API not available");
            return;
        }

        resetProgress();
        showProgress();
        setCrawlStatus("Starting crawl...");
        setMessage("Crawl in progress...");

        try {
            const response = await window.pywebview.api.start_crawl(authorInput);
            if (!response.success) {
                setCrawlStatus(response.error || "Failed to start crawl");
                if (response.requires_login) {
                    updateLoginStatus(false);
                    switchTab("login");
                }
                return;
            }

            setCrawlStatus("Crawl started");
        } catch (error) {
            setCrawlStatus("Error starting crawl");
            console.error("Error starting crawl", error);
        }
    });

    refreshDataBtn.addEventListener("click", () => {
        refreshData();
    });

    window.handleCrawlProgress = (eventType, data) => {
        showProgress();
        switch (eventType) {
            case "status":
                progressMessage.textContent = data.message || "...";
                setCrawlStatus(data.message || "Running");
                break;
            case "navigate":
                setCrawlStatus(`Navigating to ${data.identity}`);
                progressMessage.textContent = `Opening ${data.url}`;
                break;
            case "scroll":
                progressMessage.textContent = data.message || `Batch ${data.batch}`;
                break;
            case "batch":
                if (typeof data.total_collected === "number") {
                    totalCollectedEl.textContent = String(data.total_collected);
                }
                if (typeof data.items === "number") {
                    newItemsEl.textContent = String(data.items);
                }
                progressMessage.textContent = `Collected ${data.items} items in batch ${data.batch}`;
                break;
            default:
                break;
        }
    };

    window.handleCrawlComplete = (result) => {
        newItemsEl.textContent = String(result.new_items || 0);
        totalCollectedEl.textContent = String(result.total_collected || 0);
        progressMessage.textContent = result.message || "Crawl complete";
        setCrawlStatus("Crawl complete");
        setMessage("Crawl finished successfully.");
        refreshData();
    };

    window.handleCrawlError = (error) => {
        setCrawlStatus(error.error || "Crawl error");
        progressMessage.textContent = error.error || "An error occurred";
        setMessage("Crawl failed.");
    };

    async function init() {
        setMessage("Initializing...");

        if (!window.pywebview || !window.pywebview.api) {
            setMessage("PyWebView API unavailable. Running in fallback mode.");
            return;
        }

        try {
            const response = await window.pywebview.api.check_login_status();
            updateLoginStatus(response.logged_in);
        } catch (error) {
            console.error("Failed to check login status", error);
        }

        await refreshData();
        setMessage("Ready");
    }

    init();
});

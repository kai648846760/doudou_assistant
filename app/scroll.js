// 自动滚动脚本
// 用于作者主页自动滚动加载所有视频
// Auto-scroll script for loading all videos on author profile pages
(function () {
    if (window.__douyinScroller) {
        return;
    }

    const SCROLL_INTERVAL = 1500;
    const END_DETECTION_TIMEOUT = 3000;
    const MAX_SAME_HEIGHT_COUNT = 3;
    const THROTTLE_DELAY = 100;

    let scrollActive = false;
    let scrollTimer = null;
    let lastHeight = 0;
    let sameHeightCount = 0;
    let endDetectionTimer = null;
    let lastScrollTime = 0;

    function log(...args) {
        console.info("[douyin-scroller]", ...args);
    }

    function logDebug(...args) {
        console.debug("[douyin-scroller]", ...args);
    }

    function logError(...args) {
        console.error("[douyin-scroller]", ...args);
    }

    function getScrollHeight() {
        return Math.max(
            document.body.scrollHeight,
            document.documentElement.scrollHeight
        );
    }

    function scrollToBottom() {
        const now = Date.now();
        if (now - lastScrollTime < THROTTLE_DELAY) {
            logDebug("Scroll throttled");
            return;
        }
        lastScrollTime = now;

        try {
            window.scrollTo({
                top: getScrollHeight(),
                behavior: "smooth",
            });
            logDebug(`Scrolled to ${getScrollHeight()}`);
        } catch (error) {
            logError("Error scrolling:", error);
        }
    }

    function checkEndOfList() {
        const currentHeight = getScrollHeight();
        if (currentHeight === lastHeight) {
            sameHeightCount++;
            log(`Same height count: ${sameHeightCount} (height: ${currentHeight})`);
            if (sameHeightCount >= MAX_SAME_HEIGHT_COUNT) {
                log("End of list detected");
                stopScroll();
                notifyComplete();
                return true;
            }
        } else {
            logDebug(`Height changed: ${lastHeight} -> ${currentHeight}`);
            sameHeightCount = 0;
            lastHeight = currentHeight;
        }
        return false;
    }

    function notifyComplete() {
        try {
            const api = window.pywebview && window.pywebview.api;
            if (api && typeof api.on_scroll_complete === "function") {
                api.on_scroll_complete();
                log("Notified Python: scroll complete");
            } else {
                logError("Cannot notify Python: API not available");
            }
        } catch (error) {
            logError("Error notifying completion:", error);
        }
    }

    function scrollStep() {
        if (!scrollActive) {
            return;
        }

        scrollToBottom();

        if (endDetectionTimer) {
            clearTimeout(endDetectionTimer);
        }

        endDetectionTimer = setTimeout(() => {
            if (!checkEndOfList() && scrollActive) {
                scrollTimer = setTimeout(scrollStep, SCROLL_INTERVAL);
            }
        }, END_DETECTION_TIMEOUT);
    }

    function startScroll() {
        if (scrollActive) {
            log("Scroll already active");
            return;
        }

        log("Starting auto-scroll");
        scrollActive = true;
        lastHeight = 0;
        sameHeightCount = 0;

        scrollStep();
    }

    function stopScroll() {
        log("Stopping auto-scroll");
        scrollActive = false;
        if (scrollTimer) {
            clearTimeout(scrollTimer);
            scrollTimer = null;
        }
        if (endDetectionTimer) {
            clearTimeout(endDetectionTimer);
            endDetectionTimer = null;
        }
    }

    window.__douyinScroller = {
        version: "1.0.0",
        start: startScroll,
        stop: stopScroll,
        isActive: () => scrollActive,
    };

    log("Douyin scroller installed");
})();

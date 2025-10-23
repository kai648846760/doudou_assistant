(function () {
    if (window.__douyinScroller) {
        return;
    }

    const SCROLL_INTERVAL = 1500;
    const END_DETECTION_TIMEOUT = 3000;
    const MAX_SAME_HEIGHT_COUNT = 3;

    let scrollActive = false;
    let scrollTimer = null;
    let lastHeight = 0;
    let sameHeightCount = 0;
    let endDetectionTimer = null;

    function log(...args) {
        console.debug("[douyin-scroller]", ...args);
    }

    function getScrollHeight() {
        return Math.max(
            document.body.scrollHeight,
            document.documentElement.scrollHeight
        );
    }

    function scrollToBottom() {
        window.scrollTo({
            top: getScrollHeight(),
            behavior: "smooth",
        });
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
            sameHeightCount = 0;
            lastHeight = currentHeight;
        }
        return false;
    }

    function notifyComplete() {
        const api = window.pywebview && window.pywebview.api;
        if (api && typeof api.on_scroll_complete === "function") {
            api.on_scroll_complete();
        }
        log("Scroll complete");
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

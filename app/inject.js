(function () {
    if (window.__douyinBridge) {
        return;
    }

    const BRIDGE_NAME = "pywebview";
    const BATCH_DELAY = 250;

    function log(...args) {
        console.debug("[douyin-bridge]", ...args);
    }

    function normalizeAweme(item) {
        if (!item) {
            return null;
        }

        const statistics = item.statistics || {};
        const music = item.music || {};
        const video = item.video || {};
        const cover = video.cover || {};
        const playAddr = video.play_addr || {};
        const author = item.author || item.aweme_author_info || {};

        return {
            aweme_id: String(item.aweme_id || item.id || ""),
            desc: item.desc || item.description || "",
            create_time: item.create_time || statistics.create_time || null,
            duration: item.duration || null,
            statistics: {
                digg_count: statistics.digg_count || 0,
                comment_count: statistics.comment_count || 0,
                share_count: statistics.share_count || 0,
                play_count: statistics.play_count || 0,
                collect_count: statistics.collect_count || statistics.collect_cnt || 0,
            },
            author: {
                uid: author.uid || author.id || null,
                id: author.id || null,
                sec_uid: author.sec_uid || null,
                unique_id: author.unique_id || author.short_id || null,
                nickname: author.nickname || author.name || null,
                signature: author.signature || author.bio_description || null,
                avatar_thumb: author.avatar_thumb || author.avatar || null,
                follower_count: author.follower_count || author.fans || null,
                following_count: author.following_count || author.following || null,
                aweme_count: author.aweme_count || null,
                region: author.region || author.country || null,
            },
            music: {
                title: music.title || music.name || null,
                author: music.author || music.owner_nickname || null,
            },
            video: {
                cover: Array.isArray(cover.url_list) ? cover.url_list[0] : cover.url_list || cover.uri || null,
                play: Array.isArray(playAddr.url_list) ? playAddr.url_list[0] : playAddr.url_list || playAddr.uri || null,
            },
            item_type: item.item_type || item.type || null,
        };
    }

    function flatten(data) {
        const items = [];

        function visit(node) {
            if (!node) {
                return;
            }
            if (Array.isArray(node)) {
                node.forEach(visit);
                return;
            }
            if (typeof node !== "object") {
                return;
            }

            if (node.aweme_list && Array.isArray(node.aweme_list)) {
                node.aweme_list.forEach((aweme) => {
                    const normalized = normalizeAweme(aweme);
                    if (normalized && normalized.aweme_id) {
                        items.push(normalized);
                    }
                });
            }

            if (node.aweme_detail || node.aweme_info) {
                const normalized = normalizeAweme(node.aweme_detail || node.aweme_info);
                if (normalized && normalized.aweme_id) {
                    items.push(normalized);
                }
            }

            Object.keys(node).forEach((key) => {
                const value = node[key];
                if (value && typeof value === "object") {
                    visit(value);
                }
            });
        }

        visit(data);
        return items;
    }

    function safeParse(text) {
        try {
            return JSON.parse(text);
        } catch (error) {
            return null;
        }
    }

    function shouldInclude(item) {
        const ctx = window.__douyinCrawlerContext;
        if (!ctx) {
            return true;
        }
        if (ctx.latest_aweme_id && String(item.aweme_id) === String(ctx.latest_aweme_id)) {
            return false;
        }
        if (ctx.blockedIds && Array.isArray(ctx.blockedIds)) {
            return !ctx.blockedIds.includes(item.aweme_id);
        }
        return true;
    }

    async function pushBatch(batch) {
        if (!batch.length) {
            return;
        }
        const api = window[BRIDGE_NAME] && window[BRIDGE_NAME].api;
        if (!api || typeof api.push_chunk !== "function") {
            log("Bridge API not available");
            return;
        }

        try {
            await api.push_chunk(batch);
        } catch (error) {
            log("Failed to push chunk", error);
        }
    }

    function createQueue() {
        let queue = [];
        let timer = null;

        function flush() {
            const copy = queue.slice();
            queue = [];
            timer = null;
            pushBatch(copy);
        }

        return {
            add(items) {
                const filtered = items.filter(Boolean).filter(shouldInclude);
                if (!filtered.length) {
                    return;
                }
                queue = queue.concat(filtered);

                if (!timer) {
                    timer = setTimeout(flush, BATCH_DELAY);
                }
            },
        };
    }

    const queue = createQueue();

    async function inspectResponse(response) {
        if (!response) {
            return;
        }

        const cloned = response.clone();
        const contentType = cloned.headers.get("content-type") || "";
        if (!contentType.includes("application/json")) {
            return;
        }

        const text = await cloned.text();
        if (!text) {
            return;
        }

        const data = safeParse(text);
        if (!data) {
            return;
        }

        const items = flatten(data);
        if (items.length) {
            log(`Captured ${items.length} aweme items`);
            queue.add(items);
        }
    }

    const originalFetch = window.fetch;
    window.fetch = async function (...args) {
        const response = await originalFetch.apply(this, args);
        inspectResponse(response).catch((error) => log("Fetch inspect error", error));
        return response;
    };

    const XHR = window.XMLHttpRequest;
    const originalOpen = XHR.prototype.open;
    const originalSend = XHR.prototype.send;

    XHR.prototype.open = function (...args) {
        this._douyinBridgeMethod = args[0];
        return originalOpen.apply(this, args);
    };

    XHR.prototype.send = function (...args) {
        this.addEventListener("load", () => {
            try {
                if (this.responseType && this.responseType !== "" && this.responseType !== "text") {
                    return;
                }
                if (typeof this.responseText !== "string") {
                    return;
                }
                const data = safeParse(this.responseText);
                if (!data) {
                    return;
                }
                const items = flatten(data);
                if (items.length) {
                    log(`Captured ${items.length} items from XHR ${this._douyinBridgeMethod || "GET"}`);
                    queue.add(items);
                }
            } catch (error) {
                log("Error inspecting XHR response", error);
            }
        });
        return originalSend.apply(this, args);
    };

    window.__douyinBridge = {
        version: "1.1.0",
        captureJson(text) {
            const data = safeParse(text);
            if (!data) {
                return false;
            }
            const items = flatten(data);
            if (!items.length) {
                return false;
            }
            queue.add(items);
            return true;
        },
        mockPush() {
            const sample = {
                aweme_list: [
                    {
                        aweme_id: Date.now().toString(),
                        desc: "Mock aweme",
                        create_time: Math.floor(Date.now() / 1000),
                        duration: 12,
                        statistics: {
                            digg_count: 1,
                            comment_count: 0,
                            share_count: 0,
                            play_count: 10,
                            collect_count: 0,
                        },
                        author: {
                            id: "author_1",
                            uid: "author_1",
                            nickname: "Mock Author",
                            sec_uid: "mock_sec_uid",
                        },
                        music: {
                            title: "Mock Music",
                            author: "Mock Artist",
                        },
                        video: {
                            cover: {
                                url_list: ["https://example.com/cover.jpg"],
                            },
                            play_addr: {
                                url_list: ["https://example.com/video.mp4"],
                            },
                        },
                    },
                ],
            };
            queue.add(flatten(sample));
        },
    };

    // Backwards compatibility for older references
    window.__awemeBridge = window.__douyinBridge;

    log("Douyin aweme hook installed");
})();

document.addEventListener("DOMContentLoaded", () => {
    const tabs = document.querySelectorAll(".tab-button");
    const contents = document.querySelectorAll(".tab-content");
    const messageElement = document.getElementById("message");

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

    if (window.pywebview) {
        window.pywebview.api.get_message().then((message) => {
            messageElement.textContent = message;
        });
    } else {
        messageElement.textContent = "PyWebView App";
    }
});

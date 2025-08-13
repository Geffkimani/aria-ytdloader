let downloadButton = null;

function createDownloadButton() {
    if (document.getElementById("aria-download-btn")) return;

    const btn = document.createElement("button");
    btn.id = "aria-download-btn";
    btn.innerText = "⬇ Download";
    
    Object.assign(btn.style, {
        position: "fixed",
        top: "15px",
        right: "15px",
        zIndex: "9999",
        padding: "8px 12px",
        background: "#007bff",
        color: "white",
        border: "none",
        borderRadius: "5px",
        boxShadow: "0 2px 5px rgba(0,0,0,0.2)",
        cursor: "pointer",
        fontWeight: "bold",
        fontFamily: "sans-serif",
        fontSize: "14px"
    });

    btn.addEventListener("click", () => {
        const url = window.location.href;
        btn.innerText = "⏳ Sending...";
        chrome.runtime.sendMessage({ action: "downloadVideo", url: url }, (response) => {
            if (response && response.success) {
                btn.innerText = "✔ Queued";
            } else {
                btn.innerText = "❌ Error";
            }
            setTimeout(() => { btn.innerText = "⬇ Download"; }, 2000);
        });
    });

    document.body.appendChild(btn);
    downloadButton = btn;
}

// Use a MutationObserver to detect when the video player is added to the page
const observer = new MutationObserver((mutationsList, observer) => {
    for(const mutation of mutationsList) {
        if (mutation.type === 'childList') {
            const videoNode = document.querySelector('video');
            if (videoNode && !downloadButton) {
                createDownloadButton();
                break;
            }
        }
    }
});

observer.observe(document.body, { childList: true, subtree: true });

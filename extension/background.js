// Listen for messages from the popup or content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === "downloadVideo") {
        // Get the current tab's URL
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0] && tabs[0].url) {
                sendUrlToBackend(tabs[0].url, sendResponse);
            }
        });
        return true; // Indicates that the response is sent asynchronously
    }
});

// Function to send the URL to the FastAPI backend
function sendUrlToBackend(url, callback) {
    fetch("http://127.0.0.1:5000/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        console.log("Backend response:", data);
        if (callback) callback({ success: true, data: data });
    })
    .catch(error => {
        console.error("Error sending URL to backend:", error);
        if (callback) callback({ success: false, error: error.message });
    });
}

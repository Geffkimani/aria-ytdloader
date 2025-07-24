chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "downloadVideo") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const videoURL = tabs[0].url;
      fetch("http://127.0.0.1:5000/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: videoURL })
      })
        .then(response => response.json())
        .then(result => {
          if (result.status === "queued") {
            chrome.notifications.create({
              type: "basic",
              iconUrl: "icon.png",
              title: "Aria Downloader",
              message: "Video has been queued for download!"
            });
          } else {
            console.error("Failed to send download:", result.error);
          }
        })
        .catch(err => console.error("Failed to send download:", err));
    });
  }
});

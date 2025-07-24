document.getElementById("downloadBtn").addEventListener("click", () => {
  chrome.runtime.sendMessage({ action: "downloadVideo" });
});
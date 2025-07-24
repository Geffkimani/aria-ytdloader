// --- Smarter Floating Button (inject.js) ---

// Function to check for a video and add the button if found
function addDownloadButtonIfNeeded() {
  // If button already exists, do nothing
  if (document.getElementById("aria-download-btn")) {
    return;
  }

  // Check if a main video player exists (works for YouTube, Vimeo, etc.)
  const videoElement = document.querySelector('video, #movie_player');
  if (videoElement) {
    createFloatingButton();
  }
}

// Function to create and inject the button
function createFloatingButton() {
  const btn = document.createElement("button");
  btn.id = "aria-download-btn";
  btn.innerText = "⬇ Download Video";
  
  // --- Styling ---
  btn.style.position = "fixed";
  btn.style.top = "100px";
  btn.style.right = "30px";
  btn.style.zIndex = "9999";
  btn.style.padding = "10px 15px";
  btn.style.background = "#0d6efd";
  btn.style.color = "#fff";
  btn.style.border = "none";
  btn.style.borderRadius = "5px";
  btn.style.boxShadow = "0 2px 8px rgba(0,0,0,0.3)";
  btn.style.cursor = "pointer";
  btn.style.fontWeight = "bold";
  btn.style.fontFamily = "sans-serif";

  // --- On-Click Action ---
  btn.onclick = () => {
    const videoURL = window.location.href;
    btn.innerText = "⏳ Sending...";
    fetch("http://127.0.0.1:5000/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: videoURL })
    })
    .then(res => res.json())
    .then(data => {
      if (data.status === 'download_started') {
        btn.innerText = "✔ Sent!";
      } else {
        btn.innerText = "❌ Error!";
      }
      setTimeout(() => (btn.innerText = "⬇ Download Video"), 3000);
    })
    .catch(err => {
      console.error("Failed to send download", err);
      btn.innerText = "❌ Connection Failed";
      setTimeout(() => (btn.innerText = "⬇ Download Video"), 3000);
    });
  };

  document.body.appendChild(btn);
}

// --- Main Logic ---

// 1. Run the check when the script is first injected
addDownloadButtonIfNeeded();

// 2. Set up a MutationObserver to detect page changes (for SPAs like YouTube)
const observer = new MutationObserver((mutations) => {
  // We can debounce this if it becomes too noisy, but for now, it's fine.
  addDownloadButtonIfNeeded();
});

// Start observing the main body of the page for any changes
observer.observe(document.body, {
  childList: true,
  subtree: true
});
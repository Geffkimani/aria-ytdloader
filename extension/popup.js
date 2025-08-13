document.addEventListener('DOMContentLoaded', () => {
    const downloadBtn = document.getElementById('downloadBtn');
    const statusText = document.getElementById('status');

    downloadBtn.addEventListener('click', () => {
        statusText.textContent = 'Sending...';
        downloadBtn.disabled = true;

        chrome.runtime.sendMessage({ action: "downloadVideo" }, (response) => {
            if (response && response.success) {
                statusText.textContent = `Status: ${response.data.status}`;
            } else {
                statusText.textContent = `Error: ${response.error || 'Could not connect.'}`;
            }
            setTimeout(() => {
                statusText.textContent = 'Click to download current page';
                downloadBtn.disabled = false;
            }, 3000);
        });
    });
});

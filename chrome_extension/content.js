// Content script for YouTube pages
// Adds a download button to YouTube video pages

(function() {
  'use strict';

  // Wait for page to load
  let buttonAdded = false;

  function addDownloadButton() {
    if (buttonAdded) return;

    // Find the action buttons container (below video)
    const actionsContainer = document.querySelector('#top-level-buttons-computed');
    if (!actionsContainer) return;

    // Check if button already exists
    if (document.querySelector('#custom-download-btn')) return;

    // Create download button
    const downloadBtn = document.createElement('button');
    downloadBtn.id = 'custom-download-btn';
    downloadBtn.innerHTML = `
      <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
        <path d="M17 18v1H6v-1h11zm-.5-6.6l-.7-.7-3.8 3.7V4h-1v10.4l-3.8-3.8-.7.7 5 5 5-5z"/>
      </svg>
      <span>다운로드</span>
    `;
    downloadBtn.className = 'custom-download-button';

    downloadBtn.addEventListener('click', async () => {
      const videoId = getVideoId();
      if (videoId) {
        const span = downloadBtn.querySelector('span');
        span.textContent = '다운로드 중...';

        try {
          // Native Host에 다운로드 요청 (background script 통해)
          const response = await chrome.runtime.sendMessage({
            action: 'download',
            url: `https://www.youtube.com/watch?v=${videoId}`,
            quality: 'best',
            format: 'video'
          });

          if (response && response.success) {
            span.textContent = '완료!';
          } else {
            throw new Error(response?.error || '다운로드 실패');
          }
        } catch (error) {
          console.error('Download error:', error);
          span.textContent = '실패';
          alert('다운로드 실패. Native Host가 설치되어 있는지 확인하세요.');
        }

        setTimeout(() => {
          span.textContent = '다운로드';
        }, 2000);
      }
    });

    // Insert button
    actionsContainer.appendChild(downloadBtn);
    buttonAdded = true;
  }

  function getVideoId() {
    const url = window.location.href;
    let match;

    match = url.match(/[?&]v=([^&]+)/);
    if (match) return match[1];

    match = url.match(/youtube\.com\/shorts\/([^?&]+)/);
    if (match) return match[1];

    return null;
  }

  // Observe DOM changes for SPA navigation
  const observer = new MutationObserver(() => {
    buttonAdded = false;
    setTimeout(addDownloadButton, 1000);
  });

  // Start observing
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });

  // Initial attempt
  setTimeout(addDownloadButton, 2000);

  // Also try on URL changes (YouTube is SPA)
  let lastUrl = location.href;
  new MutationObserver(() => {
    if (location.href !== lastUrl) {
      lastUrl = location.href;
      buttonAdded = false;
      setTimeout(addDownloadButton, 1000);
    }
  }).observe(document, { subtree: true, childList: true });
})();

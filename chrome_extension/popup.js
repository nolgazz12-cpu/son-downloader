document.addEventListener('DOMContentLoaded', async () => {
  // 첫 방문 시 안내 팝업
  const firstVisitData = await chrome.storage.local.get(['firstVisitShown']);
  if (!firstVisitData.firstVisitShown) {
    alert('이 앱 운영 비용은 쿠파스에서 나와요\n\n8시간마다 1번씩 쿠파스 열리게 해놨어요 가급적 사용해주세요\n\n필요한 추가기능 있으시면 아래에 개발자에게 문의하기 남겨주세요');
    await chrome.storage.local.set({ firstVisitShown: true });
  }

  // 후원 모달
  const donateBtn = document.getElementById('donateBtn');
  const donateModal = document.getElementById('donateModal');
  const closeModal = document.getElementById('closeModal');

  donateBtn.addEventListener('click', (e) => {
    e.preventDefault();
    donateModal.style.display = 'block';
  });

  closeModal.addEventListener('click', () => {
    donateModal.style.display = 'none';
  });

  donateModal.addEventListener('click', (e) => {
    if (e.target === donateModal) {
      donateModal.style.display = 'none';
    }
  });

  const pageStatus = document.getElementById('pageStatus');
  const videoInfo = document.getElementById('videoInfo');
  const notYoutube = document.getElementById('notYoutube');
  const videoTitle = document.getElementById('videoTitle');
  const downloadBtn = document.getElementById('downloadBtn');
  const formatOptions = document.querySelectorAll('.format-option');
  const downloadPathEl = document.getElementById('downloadPath');
  const changePathBtn = document.getElementById('changePathBtn');

  // 저장된 다운로드 경로 로드
  let downloadPath = '';
  const stored = await chrome.storage.local.get(['downloadPath']);
  if (stored.downloadPath) {
    downloadPath = stored.downloadPath;
    downloadPathEl.textContent = downloadPath;
  } else {
    // 기본 경로 가져오기
    try {
      const response = await chrome.runtime.sendNativeMessage(NATIVE_HOST, {
        action: 'getPath'
      });
      if (response.path) {
        downloadPath = response.path;
        downloadPathEl.textContent = downloadPath;
        await chrome.storage.local.set({ downloadPath: downloadPath });
      }
    } catch (e) {
      downloadPathEl.textContent = '경로를 가져올 수 없음';
    }
  }

  // 경로 변경 버튼 (중복 클릭 방지)
  let isSelectingPath = false;
  changePathBtn.addEventListener('click', async () => {
    if (isSelectingPath) return;
    isSelectingPath = true;
    changePathBtn.disabled = true;
    changePathBtn.textContent = '선택 중...';

    try {
      const response = await chrome.runtime.sendNativeMessage(NATIVE_HOST, {
        action: 'selectPath'
      });
      if (response.path) {
        downloadPath = response.path;
        downloadPathEl.textContent = downloadPath;
        await chrome.storage.local.set({ downloadPath: downloadPath });
      }
    } catch (e) {
      alert('경로 선택 실패: ' + e.message);
    } finally {
      isSelectingPath = false;
      changePathBtn.disabled = false;
      changePathBtn.textContent = '경로 변경';
    }
  });

  // Get current tab
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  const url = tab.url;

  // Check if supported video page
  const platform = detectPlatform(url);

  if (platform) {
    pageStatus.textContent = `${platform.name} 동영상 감지됨`;
    pageStatus.classList.add('detected');
    videoInfo.style.display = 'block';

    // Get video title from tab
    let title = tab.title;
    if (platform.type === 'youtube') {
      title = title.replace(' - YouTube', '').trim();
    } else if (platform.type === 'tiktok') {
      title = title.replace(' | TikTok', '').trim();
    }
    videoTitle.textContent = title || '동영상';

    // Format selection
    let selectedFormat = 'best';
    formatOptions.forEach(option => {
      option.addEventListener('click', () => {
        formatOptions.forEach(o => o.classList.remove('selected'));
        option.classList.add('selected');
        option.querySelector('input').checked = true;
        selectedFormat = option.dataset.format;
      });
    });

    // Download button - use full URL for non-YouTube
    downloadBtn.addEventListener('click', () => {
      if (platform.type === 'youtube') {
        const videoId = extractVideoId(url);
        downloadVideo(videoId, selectedFormat, title, downloadPath);
      } else {
        downloadVideoByUrl(url, selectedFormat, title, downloadPath);
      }
    });

  } else {
    pageStatus.textContent = '지원하지 않는 페이지입니다';
    pageStatus.classList.add('not-detected');
    notYoutube.style.display = 'block';
  }
});

function isYouTubeVideo(url) {
  const patterns = [
    /youtube\.com\/watch\?v=/,
    /youtu\.be\//,
    /youtube\.com\/shorts\//
  ];
  return patterns.some(pattern => pattern.test(url));
}

function detectPlatform(url) {
  // YouTube
  if (/youtube\.com\/watch\?v=/.test(url) || /youtu\.be\//.test(url) || /youtube\.com\/shorts\//.test(url)) {
    return { type: 'youtube', name: 'YouTube' };
  }
  return null;
}

function extractVideoId(url) {
  let match;

  // youtube.com/watch?v=VIDEO_ID
  match = url.match(/[?&]v=([^&]+)/);
  if (match) return match[1];

  // youtu.be/VIDEO_ID
  match = url.match(/youtu\.be\/([^?&]+)/);
  if (match) return match[1];

  // youtube.com/shorts/VIDEO_ID
  match = url.match(/youtube\.com\/shorts\/([^?&]+)/);
  if (match) return match[1];

  return null;
}

const NATIVE_HOST = 'com.son.downloader';

// background를 통해 지속 연결로 Native Host에 메시지 전송
async function sendPersistentMessage(message) {
  return new Promise((resolve) => {
    chrome.runtime.sendMessage({ action: 'nativeMessage', message }, (response) => {
      resolve(response || { error: 'No response' });
    });
  });
}

// TikTok 등 URL로 직접 다운로드
async function downloadVideoByUrl(videoUrl, format, title, downloadPath) {
  const downloadBtn = document.getElementById('downloadBtn');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');

  downloadBtn.disabled = true;
  downloadBtn.textContent = '다운로드 시작...';

  progressContainer.style.display = 'block';
  progressBar.style.width = '0%';
  progressText.textContent = '준비 중...';

  const formatType = format === 'mp3' ? 'audio' : 'video';
  const quality = format === '720' ? '720' : 'best';

  try {
    const response = await chrome.runtime.sendNativeMessage(NATIVE_HOST, {
      action: 'download',
      url: videoUrl,
      quality: quality,
      format: formatType,
      downloadPath: downloadPath
    });

    if (response.success) {
      downloadBtn.textContent = '다운로드 중...';
      startProgressPolling(downloadBtn, progressContainer, progressBar, progressText);
    } else {
      throw new Error(response.error || '다운로드 실패');
    }
  } catch (error) {
    handleDownloadError(error, downloadBtn, progressContainer);
  }
}

async function downloadVideo(videoId, format, title, downloadPath) {
  const downloadBtn = document.getElementById('downloadBtn');
  const progressContainer = document.getElementById('progressContainer');
  const progressBar = document.getElementById('progressBar');
  const progressText = document.getElementById('progressText');

  downloadBtn.disabled = true;
  downloadBtn.textContent = '다운로드 시작...';

  // 진행률 바 표시
  progressContainer.style.display = 'block';
  progressBar.style.width = '0%';
  progressText.textContent = '준비 중...';

  const url = `https://www.youtube.com/watch?v=${videoId}`;
  const formatType = format === 'mp3' ? 'audio' : 'video';
  const quality = format === '720' ? '720' : 'best';

  try {
    // Native Host에 다운로드 요청
    const response = await chrome.runtime.sendNativeMessage(NATIVE_HOST, {
      action: 'download',
      url: url,
      quality: quality,
      format: formatType,
      downloadPath: downloadPath
    });

    if (response.success) {
      downloadBtn.textContent = '다운로드 중...';

      // 쿠파스 링크 열기 (24시간마다 1번)
      try {
        const coupangData = await chrome.storage.local.get(['coupangLastOpened']);
        const now = Date.now();
        const lastOpened = coupangData.coupangLastOpened || 0;
        const EIGHT_HOURS = 8 * 60 * 60 * 1000; // 8시간 (밀리초)

        if (now - lastOpened > EIGHT_HOURS) {
          // 먼저 저장하고 열기 (popup 닫혀도 저장 보장)
          await chrome.storage.local.set({ coupangLastOpened: now });
          window.open('https://link.coupang.com/a/cbK7O0', '_blank');
        }
      } catch (e) {
        console.log('Coupang check error:', e);
      }

      // 진행률 폴링 시작 (background를 통해 지속 연결 사용)
      const pollProgress = async () => {
        try {
          const progressResponse = await sendPersistentMessage({
            action: 'getProgress'
          });

          if (progressResponse.status === 'downloading') {
            const percent = progressResponse.percent || 0;
            progressBar.style.width = `${percent}%`;
            progressText.textContent = `다운로드 중... ${percent}%`;
            setTimeout(pollProgress, 500);
          } else if (progressResponse.status === 'merging') {
            progressBar.style.width = '99%';
            progressText.textContent = '영상 합치는 중...';
            setTimeout(pollProgress, 500);
          } else if (progressResponse.status === 'complete') {
            progressBar.style.width = '100%';
            progressText.textContent = '완료!';
            downloadBtn.textContent = '완료!';
            setTimeout(() => {
              downloadBtn.disabled = false;
              downloadBtn.textContent = '다운로드';
              progressContainer.style.display = 'none';
            }, 2000);
          } else if (progressResponse.status === 'error') {
            progressText.textContent = '오류: ' + (progressResponse.error || '다운로드 실패');
            downloadBtn.textContent = '실패';
            setTimeout(() => {
              downloadBtn.disabled = false;
              downloadBtn.textContent = '다운로드';
              progressContainer.style.display = 'none';
            }, 3000);
          } else {
            // 아직 시작 안됨 또는 상태 없음
            setTimeout(pollProgress, 500);
          }
        } catch (e) {
          // Native host 연결 끊김 - 계속 폴링
          setTimeout(pollProgress, 1000);
        }
      };

      // 0.5초 후 폴링 시작
      setTimeout(pollProgress, 500);

    } else {
      throw new Error(response.error || '다운로드 실패');
    }
  } catch (error) {
    console.error('Download error:', error);
    downloadBtn.textContent = '실패';
    progressContainer.style.display = 'none';

    if (error.message.includes('not found') || error.message.includes('Specified native messaging host not found')) {
      alert('Native Host가 설치되지 않았습니다.\ninstall.bat을 실행해주세요.');
    } else {
      alert('다운로드 실패: ' + error.message);
    }

    setTimeout(() => {
      downloadBtn.disabled = false;
      downloadBtn.textContent = '다운로드';
    }, 2000);
  }
}

// 공통: 진행률 폴링
function startProgressPolling(downloadBtn, progressContainer, progressBar, progressText) {
  // 쿠파스 링크 열기 (8시간마다 1번)
  (async () => {
    try {
      const coupangData = await chrome.storage.local.get(['coupangLastOpened']);
      const now = Date.now();
      const lastOpened = coupangData.coupangLastOpened || 0;
      const EIGHT_HOURS = 8 * 60 * 60 * 1000;

      if (now - lastOpened > EIGHT_HOURS) {
        await chrome.storage.local.set({ coupangLastOpened: now });
        window.open('https://link.coupang.com/a/cbK7O0', '_blank');
      }
    } catch (e) {
      console.log('Coupang check error:', e);
    }
  })();

  const pollProgress = async () => {
    try {
      const progressResponse = await sendPersistentMessage({
        action: 'getProgress'
      });

      if (progressResponse.status === 'downloading') {
        const percent = progressResponse.percent || 0;
        progressBar.style.width = `${percent}%`;
        progressText.textContent = `다운로드 중... ${percent}%`;
        setTimeout(pollProgress, 500);
      } else if (progressResponse.status === 'merging') {
        progressBar.style.width = '99%';
        progressText.textContent = '영상 합치는 중...';
        setTimeout(pollProgress, 500);
      } else if (progressResponse.status === 'complete') {
        progressBar.style.width = '100%';
        progressText.textContent = '완료!';
        downloadBtn.textContent = '완료!';
        setTimeout(() => {
          downloadBtn.disabled = false;
          downloadBtn.textContent = '다운로드';
          progressContainer.style.display = 'none';
        }, 2000);
      } else if (progressResponse.status === 'error') {
        progressText.textContent = '오류: ' + (progressResponse.error || '다운로드 실패');
        downloadBtn.textContent = '실패';
        setTimeout(() => {
          downloadBtn.disabled = false;
          downloadBtn.textContent = '다운로드';
          progressContainer.style.display = 'none';
        }, 3000);
      } else {
        setTimeout(pollProgress, 500);
      }
    } catch (e) {
      setTimeout(pollProgress, 1000);
    }
  };

  setTimeout(pollProgress, 500);
}

// 공통: 다운로드 에러 처리
function handleDownloadError(error, downloadBtn, progressContainer) {
  console.error('Download error:', error);
  downloadBtn.textContent = '실패';
  progressContainer.style.display = 'none';

  if (error.message.includes('not found') || error.message.includes('Specified native messaging host not found')) {
    alert('Native Host가 설치되지 않았습니다.\ninstall.bat을 실행해주세요.');
  } else {
    alert('다운로드 실패: ' + error.message);
  }

  setTimeout(() => {
    downloadBtn.disabled = false;
    downloadBtn.textContent = '다운로드';
  }, 2000);
}

const NATIVE_HOST = 'com.son.downloader';

let nativePort = null;
let pendingCallbacks = {};
let messageId = 0;

// Native Host 연결 유지
function connectNativeHost() {
  if (nativePort) return nativePort;

  try {
    nativePort = chrome.runtime.connectNative(NATIVE_HOST);

    nativePort.onMessage.addListener((response) => {
      // 응답에 id가 있으면 해당 콜백 호출
      if (response._id !== undefined && pendingCallbacks[response._id]) {
        pendingCallbacks[response._id](response);
        delete pendingCallbacks[response._id];
      }
    });

    nativePort.onDisconnect.addListener(() => {
      console.log('Native host disconnected:', chrome.runtime.lastError?.message);
      nativePort = null;
      // 모든 대기중인 콜백에 에러 반환
      Object.keys(pendingCallbacks).forEach(id => {
        pendingCallbacks[id]({ error: 'disconnected' });
        delete pendingCallbacks[id];
      });
    });

    return nativePort;
  } catch (e) {
    console.error('Failed to connect native host:', e);
    return null;
  }
}

// Native Host에 메시지 전송 (연결 유지)
function sendNativeMessagePersistent(message) {
  return new Promise((resolve) => {
    const port = connectNativeHost();
    if (!port) {
      resolve({ error: 'Failed to connect' });
      return;
    }

    const id = ++messageId;
    message._id = id;
    pendingCallbacks[id] = resolve;

    try {
      port.postMessage(message);
    } catch (e) {
      delete pendingCallbacks[id];
      resolve({ error: e.message });
    }

    // 30초 타임아웃
    setTimeout(() => {
      if (pendingCallbacks[id]) {
        delete pendingCallbacks[id];
        resolve({ error: 'timeout' });
      }
    }, 30000);
  });
}

// popup/content script에서 메시지 수신
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'nativeMessage') {
    // 지속 연결을 통해 Native Host에 메시지 전송
    sendNativeMessagePersistent(request.message).then(sendResponse);
    return true;
  }

  if (request.action === 'download') {
    // Native Host에 다운로드 요청
    chrome.runtime.sendNativeMessage(NATIVE_HOST, {
      action: 'download',
      url: request.url,
      quality: request.quality || 'best',
      format: request.format || 'video'
    }, (response) => {
      if (chrome.runtime.lastError) {
        sendResponse({
          success: false,
          error: chrome.runtime.lastError.message
        });
      } else {
        sendResponse(response);
      }
    });
    return true;
  }
});

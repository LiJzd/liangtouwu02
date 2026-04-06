import { reactive } from 'vue';
import type { Alert } from '../api';

export const ALERT_RECEIVED_EVENT = 'liangtouwu-alert-received';

interface AlertBroadcastEvent {
  eventId: string;
  spokenText: string;
  alert: Alert;
}

export const alertVoiceState = reactive({
  connected: false,
  speaking: false,
  pendingCount: 0,
  requiresInteraction: false,
  serviceUnavailable: false,
  lastError: '',
  useBrowserTTS: true, // 默认使用浏览器原生TTS
});

const queue: AlertBroadcastEvent[] = [];
const seenEventIds = new Set<string>();

let started = false;
let userUnlockedAudio = false;
let eventSource: EventSource | null = null;
let reconnectTimer: number | null = null;
let audioElement: HTMLAudioElement | null = null;

/**
 * 切换TTS模式
 * @param useBrowser true=使用浏览器原生TTS, false=使用后端讯飞TTS
 */
export function setTTSMode(useBrowser: boolean) {
  alertVoiceState.useBrowserTTS = useBrowser;
  console.log('[AlertVoice] TTS模式切换为:', useBrowser ? '浏览器原生' : '讯飞API');
}

export function startAlertVoiceListener() {
  if (started) {
    return;
  }
  started = true;

  // 初始化Web Speech API的语音列表
  if ('speechSynthesis' in window) {
    // 某些浏览器需要异步加载语音列表
    speechSynthesis.onvoiceschanged = () => {
      const voices = speechSynthesis.getVoices();
      console.log('[AlertVoice] 可用语音列表:', voices.map(v => `${v.name} (${v.lang})`));
    };
    // 触发语音列表加载
    speechSynthesis.getVoices();
  }

  audioElement = new Audio();
  audioElement.preload = 'auto';

  const unlock = () => {
    userUnlockedAudio = true;
    alertVoiceState.requiresInteraction = false;
    detachUnlockListeners();
    void drainQueue();
  };

  const detachUnlockListeners = () => {
    window.removeEventListener('click', unlock);
    window.removeEventListener('keydown', unlock);
    window.removeEventListener('touchstart', unlock);
  };

  window.addEventListener('click', unlock, { passive: true });
  window.addEventListener('keydown', unlock, { passive: true });
  window.addEventListener('touchstart', unlock, { passive: true });

  connect();
}

export function stopAlertVoiceListener() {
  if (!started) {
    return;
  }
  
  started = false;
  
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
  
  clearReconnectTimer();
  
  if (audioElement) {
    audioElement.pause();
    audioElement.src = '';
    audioElement = null;
  }
  
  queue.length = 0;
  seenEventIds.clear();
  alertVoiceState.connected = false;
  alertVoiceState.speaking = false;
  alertVoiceState.pendingCount = 0;
}

async function drainQueue() {
  if (!audioElement || alertVoiceState.speaking || queue.length === 0) {
    return;
  }

  if (!userUnlockedAudio) {
    alertVoiceState.requiresInteraction = true;
    return;
  }

  const next = queue[0];
  alertVoiceState.speaking = true;

  try {
    // 使用配置的TTS方式进行语音合成
    const audioBlob = await synthesizeSpeech(next.spokenText);
    
    // 如果使用浏览器TTS，blob为空，不需要播放
    if (audioBlob.size > 0) {
      const objectUrl = URL.createObjectURL(audioBlob);
      await playAudio(objectUrl);
      URL.revokeObjectURL(objectUrl);
    }
    
    queue.shift();
    alertVoiceState.pendingCount = queue.length;
    alertVoiceState.lastError = '';
  } catch (error) {
    const message = error instanceof Error ? error.message : '语音播报失败';
    alertVoiceState.lastError = message;

    if (message.includes('用户交互') || message.includes('自动播放')) {
      alertVoiceState.requiresInteraction = true;
      userUnlockedAudio = false;
      return;
    }

    queue.shift();
    alertVoiceState.pendingCount = queue.length;
  } finally {
    alertVoiceState.speaking = false;
    if (queue.length > 0 && userUnlockedAudio) {
      void drainQueue();
    }
  }
}

async function playAudio(objectUrl: string) {
  // 如果使用Web Speech API，objectUrl为空，直接返回
  if (!objectUrl) {
    return;
  }

  if (!audioElement) {
    throw new Error('音频播放器未初始化');
  }

  audioElement.src = objectUrl;

  try {
    await audioElement.play();
  } catch (error) {
    throw new Error('浏览器阻止了自动播放，请先与页面进行一次交互后再继续播报');
  }

  await new Promise<void>((resolve, reject) => {
    if (!audioElement) {
      resolve();
      return;
    }

    audioElement.onended = () => resolve();
    audioElement.onerror = () => reject(new Error('音频播放失败'));
  });
}

async function synthesizeSpeech(text: string): Promise<Blob> {
  // 根据配置选择TTS方式
  if (alertVoiceState.useBrowserTTS) {
    return synthesizeSpeechBrowser(text);
  } else {
    return synthesizeSpeechServer(text);
  }
}

/**
 * 使用浏览器原生Web Speech API进行语音合成
 * 优点：不需要后端API，完全免费，支持多种语言
 * 缺点：音色和质量取决于浏览器和操作系统
 */
function synthesizeSpeechBrowser(text: string): Promise<Blob> {
  return new Promise((resolve, reject) => {
    // 检查浏览器是否支持Web Speech API
    if (!('speechSynthesis' in window)) {
      reject(new Error('浏览器不支持语音合成功能'));
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    
    // 配置语音参数
    utterance.lang = 'zh-CN'; // 中文
    utterance.rate = 1.0; // 语速（0.1-10）
    utterance.pitch = 1.0; // 音调（0-2）
    utterance.volume = 1.0; // 音量（0-1）

    // 选择中文语音（如果可用）
    const voices = speechSynthesis.getVoices();
    const chineseVoice = voices.find(voice => 
      voice.lang.startsWith('zh') || voice.lang.startsWith('cmn')
    );
    if (chineseVoice) {
      utterance.voice = chineseVoice;
    }

    utterance.onend = () => {
      // Web Speech API不返回音频数据，创建一个空Blob表示成功
      resolve(new Blob([], { type: 'audio/wav' }));
    };

    utterance.onerror = (event) => {
      reject(new Error(`语音合成失败: ${event.error}`));
    };

    // 开始语音合成
    speechSynthesis.speak(utterance);
  });
}

/**
 * 使用后端讯飞TTS API进行语音合成
 */
async function synthesizeSpeechServer(text: string): Promise<Blob> {
  try {
    const response = await fetch(buildApiUrl('/alerts/tts'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const contentType = response.headers.get('content-type') ?? '';
      let message = `语音服务请求失败 [${response.status}]`;

      if (contentType.includes('application/json')) {
        const payload = await response.json().catch(() => null);
        message = payload?.message ?? payload?.data?.message ?? message;
      } else {
        const textBody = await response.text().catch(() => '');
        if (textBody) {
          message = textBody;
        }
      }

      const isConfigMissing = response.status === 503 && message.includes('配置');
      alertVoiceState.serviceUnavailable = isConfigMissing;
      
      console.error('[AlertVoice] TTS请求失败:', {
        status: response.status,
        message,
        isConfigMissing
      });
      
      throw new Error(message);
    }

    alertVoiceState.serviceUnavailable = false;
    const blob = await response.blob();
    
    // 验证返回的是音频数据
    if (blob.size === 0) {
      throw new Error('语音服务返回空数据');
    }
    
    console.log('[AlertVoice] TTS合成成功，音频大小:', blob.size);
    return blob;
  } catch (error) {
    if (error instanceof Error) {
      console.error('[AlertVoice] TTS合成失败:', error.message);
      throw error;
    }
    throw new Error('语音服务连接失败');
  }
}

function connect() {
  if (eventSource) {
    eventSource.close();
  }

  try {
    eventSource = new EventSource(buildApiUrl('/alerts/stream'), { withCredentials: true });

    eventSource.addEventListener('connected', () => {
      console.log('[AlertVoice] SSE连接成功');
      alertVoiceState.connected = true;
      alertVoiceState.lastError = '';
      clearReconnectTimer();
    });

    eventSource.addEventListener('heartbeat', () => {
      // 心跳保持连接活跃
      alertVoiceState.connected = true;
      clearReconnectTimer(); // 收到心跳后清除重连定时器
    });

    eventSource.addEventListener('alert', (event) => {
      alertVoiceState.connected = true;

      try {
        const payload = JSON.parse((event as MessageEvent<string>).data) as AlertBroadcastEvent;
        console.log('[AlertVoice] 收到告警:', payload);
        
        if (seenEventIds.has(payload.eventId)) {
          console.log('[AlertVoice] 重复事件，跳过:', payload.eventId);
          return;
        }

        seenEventIds.add(payload.eventId);
        
        // 限制缓存大小，避免内存泄漏
        if (seenEventIds.size > 1000) {
          const firstId = seenEventIds.values().next().value;
          seenEventIds.delete(firstId);
        }
        
        queue.push(payload);
        alertVoiceState.pendingCount = queue.length;

        window.dispatchEvent(new CustomEvent<Alert>(ALERT_RECEIVED_EVENT, {
          detail: payload.alert,
        }));

        void drainQueue();
      } catch (error) {
        console.error('[AlertVoice] 解析告警数据失败:', error);
      }
    });

    eventSource.onerror = (error) => {
      console.error('[AlertVoice] SSE连接错误:', error);
      alertVoiceState.connected = false;
      
      // 检查readyState判断是否需要重连
      if (eventSource && eventSource.readyState === EventSource.CLOSED) {
        alertVoiceState.lastError = 'SSE连接已关闭，正在重连...';
        scheduleReconnect();
      } else if (eventSource && eventSource.readyState === EventSource.CONNECTING) {
        alertVoiceState.lastError = 'SSE正在连接...';
      } else {
        alertVoiceState.lastError = 'SSE连接异常';
        scheduleReconnect();
      }
    };
  } catch (error) {
    console.error('[AlertVoice] 创建SSE连接失败:', error);
    alertVoiceState.connected = false;
    alertVoiceState.lastError = '无法建立SSE连接';
    scheduleReconnect();
  }
}

function scheduleReconnect() {
  if (reconnectTimer !== null) {
    return;
  }

  reconnectTimer = window.setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, 3000);
}

function clearReconnectTimer() {
  if (reconnectTimer === null) {
    return;
  }
  window.clearTimeout(reconnectTimer);
  reconnectTimer = null;
}

function buildApiUrl(path: string) {
  const baseUrl = import.meta.env.DEV ? 'http://localhost:8080/api' : '/api';
  return `${baseUrl}${path}`;
}

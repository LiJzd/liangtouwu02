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
});

const queue: AlertBroadcastEvent[] = [];
const seenEventIds = new Set<string>();

let started = false;
let userUnlockedAudio = false;
let eventSource: EventSource | null = null;
let reconnectTimer: number | null = null;
let audioElement: HTMLAudioElement | null = null;

export function startAlertVoiceListener() {
  if (started) {
    return;
  }
  started = true;

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
    const audioBlob = await synthesizeSpeech(next.spokenText);
    const objectUrl = URL.createObjectURL(audioBlob);

    await playAudio(objectUrl);

    URL.revokeObjectURL(objectUrl);
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
      message = payload?.message ?? message;
    } else {
      const textBody = await response.text().catch(() => '');
      if (textBody) {
        message = textBody;
      }
    }

    const isConfigMissing = response.status === 503 && message.includes('配置');
    alertVoiceState.serviceUnavailable = isConfigMissing;
    throw new Error(message);
  }

  alertVoiceState.serviceUnavailable = false;
  return response.blob();
}

function connect() {
  if (eventSource) {
    eventSource.close();
  }

  eventSource = new EventSource(buildApiUrl('/alerts/stream'), { withCredentials: true });

  eventSource.addEventListener('connected', () => {
    alertVoiceState.connected = true;
    alertVoiceState.lastError = '';
    clearReconnectTimer();
  });

  eventSource.addEventListener('heartbeat', () => {
    alertVoiceState.connected = true;
  });

  eventSource.addEventListener('alert', (event) => {
    alertVoiceState.connected = true;

    const payload = JSON.parse((event as MessageEvent<string>).data) as AlertBroadcastEvent;
    if (seenEventIds.has(payload.eventId)) {
      return;
    }

    seenEventIds.add(payload.eventId);
    queue.push(payload);
    alertVoiceState.pendingCount = queue.length;

    window.dispatchEvent(new CustomEvent<Alert>(ALERT_RECEIVED_EVENT, {
      detail: payload.alert,
    }));

    void drainQueue();
  });

  eventSource.onerror = () => {
    alertVoiceState.connected = false;
    scheduleReconnect();
  };
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

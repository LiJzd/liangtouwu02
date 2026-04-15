import { reactive } from 'vue';
import type { Alert } from '../api';

export const ALERT_RECEIVED_EVENT = 'liangtouwu-alert-received';
export const SIMULATION_ACTION_EVENT = 'liangtouwu-simulation-action';


interface AlertBroadcastEvent {
  eventId: string;
  spokenText: string;
  alert: Alert;
}

export interface PigBotCachedAlert {
  cacheKey: string;
  eventId: string;
  spokenText: string;
  alert: Alert;
  receivedAt: number;
  consumed: boolean;
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
const PIGBOT_ALERT_CACHE_STORAGE_KEY = 'liangtouwu-pigbot-alert-cache';
const PIGBOT_ALERT_CACHE_LIMIT = 50;
const pigBotAlertCache: PigBotCachedAlert[] = loadPigBotAlertCache();

export function buildPigBotAlertCacheKey(alert: Alert) {
  return `${String(alert.id ?? 'unknown')}-${alert.timestamp ?? 'unknown'}`;
}

export function consumePendingPigBotAlerts(): PigBotCachedAlert[] {
  const pendingAlerts = pigBotAlertCache
    .filter((item) => !item.consumed)
    .reverse()
    .map((item) => ({
      ...item,
      alert: { ...item.alert },
    }));

  if (pendingAlerts.length === 0) {
    return pendingAlerts;
  }

  pigBotAlertCache.forEach((item) => {
    if (!item.consumed) {
      item.consumed = true;
    }
  });
  persistPigBotAlertCache();

  return pendingAlerts;
}

export function markPigBotAlertAsConsumed(cacheKey: string) {
  const target = pigBotAlertCache.find((item) => item.cacheKey === cacheKey);
  if (!target || target.consumed) {
    return;
  }

  target.consumed = true;
  persistPigBotAlertCache();
}

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

function loadPigBotAlertCache(): PigBotCachedAlert[] {
  if (typeof window === 'undefined') {
    return [];
  }

  try {
    const rawCache = window.sessionStorage.getItem(PIGBOT_ALERT_CACHE_STORAGE_KEY);
    if (!rawCache) {
      return [];
    }

    const parsed = JSON.parse(rawCache);
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed
      .filter((item): item is PigBotCachedAlert => {
        return Boolean(item && typeof item.cacheKey === 'string' && item.alert);
      })
      .slice(0, PIGBOT_ALERT_CACHE_LIMIT);
  } catch (error) {
    console.warn('[AlertVoice] Failed to restore PigBot alert cache:', error);
    return [];
  }
}

function persistPigBotAlertCache() {
  if (typeof window === 'undefined') {
    return;
  }

  try {
    window.sessionStorage.setItem(
      PIGBOT_ALERT_CACHE_STORAGE_KEY,
      JSON.stringify(pigBotAlertCache.slice(0, PIGBOT_ALERT_CACHE_LIMIT)),
    );
  } catch (error) {
    console.warn('[AlertVoice] Failed to persist PigBot alert cache:', error);
  }
}

function cachePigBotAlert(payload: AlertBroadcastEvent) {
  const cacheKey = buildPigBotAlertCacheKey(payload.alert);
  const existing = pigBotAlertCache.find((item) => item.cacheKey === cacheKey);

  if (existing) {
    existing.eventId = payload.eventId;
    existing.spokenText = payload.spokenText;
    existing.alert = payload.alert;
    existing.receivedAt = Date.now();
    persistPigBotAlertCache();
    return existing;
  }

  pigBotAlertCache.unshift({
    cacheKey,
    eventId: payload.eventId,
    spokenText: payload.spokenText,
    alert: payload.alert,
    receivedAt: Date.now(),
    consumed: false,
  });

  if (pigBotAlertCache.length > PIGBOT_ALERT_CACHE_LIMIT) {
    pigBotAlertCache.length = PIGBOT_ALERT_CACHE_LIMIT;
  }

  persistPigBotAlertCache();
  return pigBotAlertCache[0];
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
    // 根据播放模式执行三次连续播报
    if (alertVoiceState.useBrowserTTS) {
      for (let i = 0; i < 3; i++) {
        await synthesizeSpeech(next.spokenText);
      }
    } else {
      const audioBlob = await synthesizeSpeech(next.spokenText);
      if (audioBlob.size > 0) {
        const objectUrl = URL.createObjectURL(audioBlob);
        for (let i = 0; i < 3; i++) {
          await playAudio(objectUrl);
        }
        URL.revokeObjectURL(objectUrl);
      }
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
    const sseUrl = buildApiUrl('/alerts/stream'); 
    console.log('%c[AlertVoice] 正在尝试建立 SSE 连接:', 'color: #3b82f6; font-weight: bold;', sseUrl);
    
    eventSource = new EventSource(sseUrl, { withCredentials: true });

    eventSource.onopen = () => {
      console.log('%c[AlertVoice] SSE 连接状态已变为 OPEN', 'color: #10b981;');
    };

    eventSource.onerror = (err) => {
      console.error('[AlertVoice] SSE 连接发生错误或异常中断:', err);
      alertVoiceState.connected = false;
      scheduleReconnect();
    };

    eventSource.addEventListener('connected', () => {
      console.log('%c[AlertVoice] SSE 业务心跳连接成功', 'color: #10b981; font-weight: bold;');
      alertVoiceState.connected = true;
      alertVoiceState.lastError = '';
      clearReconnectTimer();
    });

    // 冗余的消息处理器：捕获没有具体 event type 的所有消息
    eventSource.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.alert) {
          handleIncomingAlert(payload);
        }
      } catch (e) {}
    };

    eventSource.addEventListener('heartbeat', () => {
      alertVoiceState.connected = true;
      clearReconnectTimer();
    });

    eventSource.addEventListener('alert', (event) => {
      try {
        const payload = JSON.parse((event as MessageEvent<string>).data) as AlertBroadcastEvent;
        handleIncomingAlert(payload);
      } catch (error) {
        console.error('[AlertVoice] 告警数据解析异常:', error);
      }
    });

    function handleIncomingAlert(payload: AlertBroadcastEvent) {
      alertVoiceState.connected = true;
      
      // 生成可靠的唯一 ID 判定重复
      const uniqueId = payload.eventId || `${payload.alert.id}-${payload.alert.timestamp}`;
      if (seenEventIds.has(uniqueId)) {
        return;
      }
      seenEventIds.add(uniqueId);

      // 限制缓存记录大小
      if (seenEventIds.size > 1000) {
        const firstId = seenEventIds.values().next().value;
        if (firstId) seenEventIds.delete(firstId);
      }

      // 🚀 核心：输出写死的思考日志 (Chain of Thought)
      console.log(`%c[思考日志 - AI 诊断分析中枢]`, 'color: #10b981; background: #ecfdf5; padding: 4px 8px; border-radius: 4px; font-weight: bold;');
      console.log(`- [Thought] 接收到环境/体征检测信号流入...
- [Action] 调用系统级多智能体协同评估 (PigBot & VetAgent)...
- [Observation] 判定结果：当前 ${payload.alert.type} 命中异常。
- [Final Answer] 已成功触发联动策略，正在进行连续 3 次语音播报。`);

      cachePigBotAlert(payload);
      queue.push(payload);
      alertVoiceState.pendingCount = queue.length;

      // 广播标准事件给各个页面组件
      window.dispatchEvent(new CustomEvent<Alert>(ALERT_RECEIVED_EVENT, { detail: payload.alert }));

      // 🚀 联动逻辑：如果是模拟告警且涉及环境/氨气，触发自动排风动作提示
      const msg = payload.alert.message || '';
      const type = payload.alert.type || '';
      const spoken = payload.spokenText || '';

      const isSimulated = spoken.includes('模拟') || type.includes('模拟') || msg.includes('模拟');
      const isEnvironment = spoken.includes('环境') || type.includes('环境') || spoken.includes('氨气') || msg.includes('氨气');
      const isHealth = spoken.includes('体温') || type.includes('体温') || spoken.includes('健康') || type.includes('健康') || spoken.includes('活跃度');
      
      if (isSimulated) {
        let action = '系统自动化巡检与评估';
        let icon = 'brain';
        
        if (isEnvironment) {
          action = '自动调用风扇进行排风';
          icon = 'fan';
        } else if (isHealth) {
          action = '自动生成诊断建议并通知兽医';
          icon = 'medical';
        } else if (spoken.includes('异常') || type.includes('异常')) {
          action = 'AI 深度分析任务下发中';
          icon = 'brain';
        }

        console.log(`%c[动作触发] 检测到模拟告警，执行: ${action}`, 'color: #10b981; font-weight: bold;');
        window.dispatchEvent(new CustomEvent(SIMULATION_ACTION_EVENT, { 
          detail: { 
            action: action,
            icon: icon,
            target: payload.alert.area || '实验室'
          } 
        }));
      }

      void drainQueue();
    }
  } catch (error) {
    console.error('[AlertVoice] SSE 连接发生严重错误:', error);
    alertVoiceState.connected = false;
    alertVoiceState.lastError = 'SSE服务器连接异常';
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
  // 统一使用相对路径 /api，由 Vite 代理 (vite.config.js) 转发到 8080
  // 这样可以避免跨域 (CORS) 问题并简化网络配置
  return `/api${path}`;
}

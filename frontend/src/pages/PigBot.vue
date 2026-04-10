<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { apiService } from '../api';

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  image?: string; // base64
  audio?: boolean; // 是否包含语音
  timestamp: string;
  isTyping?: boolean;
}

const messages = ref<ChatMessage[]>([]);
const inputMessage = ref('');
const isSending = ref(false);
const chatContainer = ref<HTMLElement | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const pendingImage = ref<string | null>(null);
const isRecording = ref(false);
const pendingAudioBlob = ref<Blob | null>(null);
const audioPreviewUrl = ref<string | null>(null);
let mediaRecorder: MediaRecorder | null = null;
let audioChunks: Blob[] = [];

const removePendingImage = () => {
  pendingImage.value = null;
};

const removePendingAudio = () => {
  pendingAudioBlob.value = null;
  if (audioPreviewUrl.value) {
    URL.revokeObjectURL(audioPreviewUrl.value);
    audioPreviewUrl.value = null;
  }
};

// 初始化欢迎语
onMounted(() => {
  messages.value.push({
    id: Date.now().toString(),
    role: 'assistant',
    content: '你好呀！我是两头乌数字牧场的 PigBOT 专属智能助理 🐽。\n任何生猪健康分析、体态辨识问题，都可以发送图片向我咨询！',
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  });
});

const scrollToBottom = async () => {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
};

const handleSendText = () => {
  handleSend();
};

const handleSend = async () => {
  const text = inputMessage.value.trim();
  const imageToUpload = pendingImage.value;
  const audioToUpload = pendingAudioBlob.value;

  if (!text && !imageToUpload && !audioToUpload) return;
  
  if (isSending.value) return;

  const newUserMsgId = Date.now().toString();
  const timeStr = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

  messages.value.push({
    id: newUserMsgId,
    role: 'user',
    content: text || (audioToUpload ? '[语音消息]' : ''),
    image: imageToUpload || undefined,
    audio: !!audioToUpload,
    timestamp: timeStr
  });

  inputMessage.value = '';
  pendingImage.value = null;
  removePendingAudio();
  isSending.value = true;
  await scrollToBottom();

  const typingMsgId = 'typing_' + Date.now();
  messages.value.push({
    id: typingMsgId,
    role: 'assistant',
    content: '',
    timestamp: timeStr,
    isTyping: true
  });
  await scrollToBottom();

  try {
    const apiMessages = messages.value
      .filter(m => !m.isTyping)
      .map(m => ({
        role: m.role,
        content: m.content
      }));
      
    const recentMessages = apiMessages.slice(-10);
    const urlsToSends = imageToUpload ? [imageToUpload] : [];

    const response = await apiService.chatWithPigBot(recentMessages, urlsToSends, audioToUpload);
    
    messages.value = messages.value.filter(m => m.id !== typingMsgId);
    
    messages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: response.reply || '分析完毕，我未获得任何有效诊断结果。',
      image: response.image ? `data:image/png;base64,${response.image}` : undefined,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    });
  } catch (error: any) {
    console.error('Chat Error:', error);
    messages.value = messages.value.filter(m => m.id !== typingMsgId);
    messages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: `由于网络波动，连接中枢服务失败 (${error.message})。请稍后重试。`,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    });
  } finally {
    isSending.value = false;
    await scrollToBottom();
  }
};

const triggerFileUpload = () => {
  fileInput.value?.click();
};

const handleFileChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    const base64String = event.target?.result as string;
    pendingImage.value = base64String;
  };
  reader.readAsDataURL(file);
  
  
  if (fileInput.value) fileInput.value.value = '';
};

const handleMicClick = () => {
  if (isRecording.value) {
    stopRecording();
  } else {
    startRecording();
  }
};

const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      pendingAudioBlob.value = audioBlob;
      audioPreviewUrl.value = URL.createObjectURL(audioBlob);
      // 关闭所有轨道以释放麦克风
      stream.getTracks().forEach(track => track.stop());
    };

    mediaRecorder.start();
    isRecording.value = true;
  } catch (err) {
    console.error('麦克风权限开启失败:', err);
    alert('需开启麦克风权限才能使用语音功能');
  }
};

const stopRecording = () => {
  if (mediaRecorder && isRecording.value) {
    mediaRecorder.stop();
    isRecording.value = false;
  }
};

// transcribeVoice 已弃用，逻辑已迁移至多模态后端
</script>

<template>
  <div class="h-[calc(100vh-8rem)] min-h-[600px] w-full max-w-6xl mx-auto flex gap-6 pb-4 relative z-10">
    
    <!-- 左侧详情 (大屏可见) -->
    <div class="hidden lg:flex w-72 bg-white/80 backdrop-blur-3xl rounded-[2rem] shadow-sm border border-emerald-100 flex-col overflow-hidden self-start mt-6">
      <div class="h-44 bg-gradient-to-br from-emerald-500 to-secondary relative flex items-center justify-center text-white">
        <!-- 装饰底纹 -->
        <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-20 pointer-events-none"></div>
        <span class="material-symbols-outlined text-white text-[72px] drop-shadow-lg opacity-90 z-10">smart_toy</span>
        <div class="absolute bottom-4 text-center w-full z-10">
          <p class="font-bold font-headline text-2xl tracking-tight">PigBOT AI</p>
          <p class="text-[10px] text-emerald-50 mt-1 font-inter font-bold tracking-widest uppercase">全天候视觉驱动诊断服务</p>
        </div>
      </div>
      <div class="p-6 text-emerald-900/70 text-xs space-y-4 font-inter leading-relaxed bg-surface-bright/50">
        <p class="flex items-start gap-2.5 bg-white/90 p-4 rounded-2xl border border-emerald-50 shadow-sm hover:-translate-y-1 transition-transform">
          <span class="material-symbols-outlined text-[16px] text-secondary shrink-0 bg-emerald-50 rounded-full p-1 border border-emerald-100">qr_code_scanner</span>
          <span class="font-bold">深度视觉化验</span>
          <span class="block w-full mt-1 text-[11px] text-emerald-900/50">为上传的图像或现场视频指认病理特征分析。</span>
        </p>
        <p class="flex items-start gap-2.5 bg-white/90 p-4 rounded-2xl border border-emerald-50 shadow-sm hover:-translate-y-1 transition-transform">
          <span class="material-symbols-outlined text-[16px] text-secondary shrink-0 bg-emerald-50 rounded-full p-1 border border-emerald-100">database</span>
          <span class="font-bold">专家知识中枢</span>
          <span class="block w-full mt-1 text-[11px] text-emerald-900/50">集成兽牧专业 RAG 资料库，辅助出具全息诊疗法。</span>
        </p>
        <p class="flex items-start gap-2.5 bg-white/90 p-4 rounded-2xl border border-emerald-50 shadow-sm hover:-translate-y-1 transition-transform">
          <span class="material-symbols-outlined text-[16px] text-secondary shrink-0 bg-emerald-50 rounded-full p-1 border border-emerald-100">3p</span>
          <span class="font-bold">长程环境溯源</span>
          <span class="block w-full mt-1 text-[11px] text-emerald-900/50">支持联系上下文环境连续问询，提供全局洞察力。</span>
        </p>
      </div>
    </div>

    <!-- 🌟 手机模拟器视图 🌟 -->
    <div class="flex-1 flex justify-center items-center relative py-2">
      <!-- 手机外壳 -->
      <div class="relative w-[360px] md:w-[380px] h-[720px] md:h-[780px] rounded-[3rem] border-[12px] border-emerald-950/95 shadow-[0_30px_60px_-10px_rgba(0,0,0,0.4)] bg-emerald-50 flex flex-col overflow-hidden shrink-0 ring-[2px] ring-white/40 ring-offset-4 ring-offset-emerald-100 group">
        
        <!-- 侧边物理按键特效 -->
        <div class="absolute -left-[14px] top-32 w-1 h-8 rounded-l-md bg-emerald-900"></div>
        <div class="absolute -left-[14px] top-48 w-1 h-12 rounded-l-md bg-emerald-900"></div>
        <div class="absolute -left-[14px] top-64 w-1 h-12 rounded-l-md bg-emerald-900"></div>
        <div class="absolute -right-[14px] top-40 w-1 h-16 rounded-r-md bg-emerald-900"></div>

        <!-- 听筒 / 动态岛 -->
        <div class="absolute top-0 left-1/2 -translate-x-1/2 w-28 h-6 bg-emerald-950/95 rounded-b-[18px] z-50 flex items-center justify-center">
          <div class="w-12 h-1 rounded-full bg-black/60 shadow-inner"></div>
          <div class="w-1.5 h-1.5 rounded-full bg-blue-800/80 ml-2 relative overflow-hidden"><div class="absolute inset-y-0 right-0 w-[0.5px] bg-white/30"></div></div>
        </div>

        <!-- APP PWA 内容区域 -->
        <div class="flex-1 w-full bg-surface-bright flex flex-col relative pt-[28px] overflow-hidden z-40 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')]">
          
          <!-- App 导航栏 -->
          <header class="min-h-[60px] px-4 border-b border-emerald-100/60 bg-white/80 backdrop-blur-md shrink-0 flex items-center justify-between shadow-sm z-30 relative">
            <div class="flex items-center gap-3">
              <button class="w-8 h-8 rounded-full bg-emerald-50 text-emerald-900/60 flex items-center justify-center hover:text-secondary hover:bg-emerald-100 transition-colors">
                <span class="material-symbols-outlined text-[18px]">arrow_back_ios_new</span>
              </button>
              
              <div class="flex items-center gap-2">
                <div class="relative group-hover:scale-105 transition-transform duration-300">
                  <div class="w-9 h-9 rounded-full bg-gradient-to-tr from-emerald-500 to-secondary flex items-center justify-center text-white shadow shadow-secondary/30">
                    <span class="material-symbols-outlined text-[20px]">smart_toy</span>
                  </div>
                  <span class="absolute bottom-0 right-0 w-2.5 h-2.5 bg-green-500 border-2 border-white rounded-full"></span>
                </div>
                <div>
                  <h2 class="font-bold font-headline text-emerald-950 text-[14px] tracking-tight leading-tight">驻场数字专家 AI</h2>
                  <p class="text-[9px] text-emerald-900/50 font-bold uppercase tracking-widest flex items-center gap-1 mt-0.5">
                    <span class="text-green-600 font-inter">Live</span> VISION
                  </p>
                </div>
              </div>
            </div>
            
            <button class="w-8 h-8 rounded-full hover:bg-emerald-50 flex items-center justify-center text-emerald-900/60 transition-colors">
              <span class="material-symbols-outlined text-[20px]">more_vert</span>
            </button>
          </header>

          <!-- 聊天内容流 -->
          <main 
            class="flex-1 overflow-y-auto w-full p-4 space-y-5 scroll-smooth bg-transparent custom-scrollbar pb-6"
            ref="chatContainer"
          >
            <div 
              v-for="msg in messages" 
              :key="msg.id"
              class="flex w-full group"
              :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
            >
              <!-- 助手小卡片头像 -->
              <div v-if="msg.role === 'assistant'" class="w-8 h-8 rounded-full bg-gradient-to-tr from-emerald-500 to-secondary shrink-0 mr-2 flex items-center justify-center text-white shadow-[0_2px_10px_rgba(16,185,129,0.3)] mt-1 ml-1 cursor-pointer">
                <span class="material-symbols-outlined text-[16px]">smart_toy</span>
              </div>

              <div 
                class="flex flex-col relative max-w-[75%]"
                :class="msg.role === 'user' ? 'items-end pr-1' : 'items-start'"
              >
                <!-- 发送时间及名称 -->
                <div class="text-[9px] text-emerald-900/40 font-bold uppercase tracking-widest mb-1 flex items-center gap-1.5 px-1 font-inter">
                  <span v-if="msg.role === 'assistant'" class="text-emerald-900/60">PigBOT</span>
                  <span>{{ msg.timestamp }}</span>
                </div>

                <!-- 对话气泡框 -->
                <div 
                  class="relative px-3.5 py-2.5 text-[13px] font-inter leading-relaxed select-text min-h-[36px] flex flex-col transition-all border"
                  :class="[
                    msg.role === 'user'
                      ? 'bg-gradient-to-r from-secondary to-[#047857] text-white rounded-[18px] rounded-tr-[4px] shadow-md shadow-emerald-600/20 border-transparent'
                      : 'bg-white text-emerald-950 rounded-[18px] rounded-tl-[4px] shadow-sm border-emerald-100/80',
                  ]"
                >
                  <div v-if="!msg.isTyping" class="whitespace-pre-wrap break-words break-all text-sm">
                    <div v-if="msg.audio" class="flex items-center gap-2 mb-1 text-emerald-100">
                      <span class="material-symbols-outlined text-sm animate-pulse">settings_voice</span>
                      <span class="text-[11px] font-bold italic tracking-wide">MULTIMODAL AUDIO ATTACHED</span>
                    </div>
                    {{ msg.content }}
                  </div>
                  
                  <!-- 发送的图像渲染缩略图 -->
                  <div v-if="msg.image" class="mt-2 rounded-xl border border-black/10 overflow-hidden bg-emerald-50 shadow-inner max-w-[200px]">
                    <img :src="msg.image" class="w-full h-auto object-cover hover:scale-110 transition-transform duration-300" alt="发图查验" />
                  </div>

                  <!-- 打字悬浮提示动画 -->
                  <div v-if="msg.isTyping" class="flex gap-1.5 items-center justify-center h-4 w-8">
                    <span class="w-1.5 h-1.5 bg-emerald-300 rounded-full animate-bounce [animation-delay:0ms]"></span>
                    <span class="w-1.5 h-1.5 bg-secondary rounded-full animate-bounce [animation-delay:150ms]"></span>
                    <span class="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce [animation-delay:300ms]"></span>
                  </div>
                </div>
                
              </div>
            </div>
          </main>

          <!-- App 输入功能底部框 -->
          <footer class="bg-white/80 backdrop-blur-md border-t border-emerald-100 z-30 shrink-0 shadow-[0_-5px_15px_rgba(0,0,0,0.02)] pb-[env(safe-area-inset-bottom,16px)]">
            <input 
              type="file" 
              ref="fileInput" 
              class="hidden" 
              accept="image/*"
              @change="handleFileChange"
            />

            <!-- 资源预检悬浮层 -->
            <div v-if="pendingImage || audioPreviewUrl" class="px-4 py-2 mt-2 flex gap-3">
              <!-- 图片预览 -->
              <div v-if="pendingImage" class="relative w-20 h-20 group/preview animate-in fade-in zoom-in duration-300">
                <img :src="pendingImage" class="w-full h-full object-cover rounded-xl border-2 border-emerald-100 shadow-sm" alt="预加载图" />
                <button 
                  @click="removePendingImage"
                  class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center shadow-lg hover:bg-red-600 transition-colors"
                >
                  <span class="material-symbols-outlined text-[14px]">close</span>
                </button>
              </div>

              <!-- 语音预览 -->
              <div v-if="audioPreviewUrl" class="relative w-24 h-20 bg-emerald-50 rounded-xl border-2 border-emerald-100 shadow-sm flex flex-col items-center justify-center gap-1 animate-in fade-in zoom-in duration-300">
                <span class="material-symbols-outlined text-secondary animate-pulse text-[24px]">mic</span>
                <span class="text-[9px] font-bold text-emerald-900/40 uppercase tracking-widest">Voice attached</span>
                <button 
                  @click="removePendingAudio"
                  class="absolute -top-2 -right-2 w-6 h-6 bg-red-500 text-white rounded-full flex items-center justify-center shadow-lg hover:bg-red-600 transition-colors"
                >
                  <span class="material-symbols-outlined text-[14px]">close</span>
                </button>
              </div>
            </div>

            <!-- 功能附加面板按钮 -->
            <div class="flex items-center gap-1.5 pt-2 pb-1 px-3">
              <button 
                @click="triggerFileUpload"
                class="p-2 rounded-full text-emerald-900/50 hover:text-secondary hover:bg-emerald-50 transition-colors cursor-pointer flex items-center justify-center border border-transparent hover:border-emerald-100"
              >
                <span class="material-symbols-outlined text-[18px]">add_photo_alternate</span>
              </button>
              <button 
                @click="handleMicClick"
                class="p-2 rounded-full transition-all cursor-pointer flex items-center justify-center border border-transparent"
                :class="[
                  isRecording 
                    ? 'bg-red-500 text-white shadow-lg shadow-red-500/30 animate-pulse border-red-200' 
                    : 'text-emerald-900/50 hover:text-secondary hover:bg-emerald-50 hover:border-emerald-100'
                ]"
              >
                <span class="material-symbols-outlined text-[18px]">{{ isRecording ? 'mic' : 'mic_none' }}</span>
              </button>
              <button class="p-2 rounded-full text-emerald-900/50 hover:text-secondary hover:bg-emerald-50 transition-colors cursor-pointer flex items-center justify-center border border-transparent hover:border-emerald-100">
                <span class="material-symbols-outlined text-[18px]">add_circle</span>
              </button>
              <div class="flex-1"></div>
            </div>

            <!-- 主输入框与发送按钮栏 -->
            <div class="flex flex-row items-end gap-2 px-3 pb-3">
              <div class="flex-1 bg-surface-bright rounded-2xl border border-emerald-100 focus-within:bg-white focus-within:border-secondary focus-within:ring-2 focus-within:ring-secondary/20 transition-all flex pt-1 px-3 shadow-inner">
                <textarea
                  v-model="inputMessage"
                  :placeholder="isRecording ? '正在倾听...' : audioPreviewUrl ? '已包含语音，点击发送或继续输入' : '向 AI 发送指令...'"
                  class="w-full bg-transparent border-none outline-none focus:outline-none focus:ring-0 focus:border-transparent resize-none py-2 text-[13px] font-inter text-emerald-950 placeholder:text-emerald-900/30 h-[48px] max-h-[120px]"
                  @keydown.enter.prevent="handleSendText"
                ></textarea>
              </div>
              
              <button 
                @click="handleSendText"
                :disabled="(!inputMessage.trim() && !pendingImage && !pendingAudioBlob && !isSending) || isSending"
                class="h-[46px] w-[46px] shrink-0 bg-gradient-to-tr from-emerald-600 to-secondary rounded-full flex items-center justify-center text-white shadow-lg shadow-emerald-600/30 active:scale-95 transition-all disabled:opacity-50 disabled:active:scale-100 disabled:shadow-none mb-0.5"
              >
                <span v-if="!isSending" class="material-symbols-outlined text-[20px] ml-0.5">send</span>
                <span v-else class="material-symbols-outlined text-[20px] animate-spin">progress_activity</span>
              </button>
            </div>
            
            <!-- IOS 原生底部圆角粗黑条 (Safe Area 指示器) -->
            <div class="w-full flex justify-center pt-1 pb-2 h-4">
              <div class="w-1/3 h-1 bg-black/20 rounded-full"></div>
            </div>
          </footer>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
  background-color: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(16, 185, 129, 0.2);
  border-radius: 99px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:active {
  background-color: rgba(16, 185, 129, 0.4);
}

.animate-in {
  animation: scaleIn 0.3s ease-out forwards;
}

@keyframes scaleIn {
  from {
    opacity: 0;
    transform: scale(0.9) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
</style>

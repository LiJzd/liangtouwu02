<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { 
  Bot, Send, Image as ImageIcon, Mic, 
  Paperclip, Loader2, X, Trash2,
  Signal, Wifi, Battery, UploadCloud
} from 'lucide-vue-next';
import { apiService } from './api'

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  image?: string; // base64
  timestamp: string;
  isTyping?: boolean;
}

const messages = ref<ChatMessage[]>([]);
const inputMessage = ref('');
const isSending = ref(false);
const chatContainer = ref<HTMLElement | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const currentTime = ref(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));

// 挂载图片相关
const selectedImage = ref<string | null>(null);
const isDragging = ref(false);

// 录音相关
const isRecording = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const audioChunks = ref<Blob[]>([]);
const recordingTime = ref(0);
const recordingInterval = ref<number | null>(null);

onMounted(() => {
  // 更新状态栏时间
  setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  }, 30000);

  // 欢迎语
  messages.value.push({
    id: 'welcome',
    role: 'assistant',
    content: '你好！我是您的两头乌专属智能助手 PigBOT 🐽。现在我已经支持【拖拽上传图片】和【图文合并发送】啦！你可以把照片直接拖进手机框里。',
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  });
});

const scrollToBottom = async () => {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
};

const handleSend = async (manualImage?: string, manualText?: string) => {
  const text = manualText !== undefined ? manualText : inputMessage.value.trim();
  const imageToSend = manualImage || selectedImage.value;

  if (!text && !imageToSend) return;
  if (isSending.value) return;

  const newUserMsgId = Date.now().toString();
  const timeStr = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

  // 1. 用户消息入队
  messages.value.push({
    id: newUserMsgId,
    role: 'user',
    content: text,
    image: imageToSend || undefined,
    timestamp: timeStr
  });

  // 清除挂载状态
  inputMessage.value = '';
  selectedImage.value = null;
  isSending.value = true;
  await scrollToBottom();

  // 2. 显示“正在输入...”
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
    const history = messages.value
      .filter(m => !m.isTyping)
      .slice(-10)
      .map(m => ({ role: m.role, content: m.content }));

    const urls = imageToSend ? [imageToSend] : [];
    
    const data = await apiService.chat(history, urls);

    messages.value = messages.value.filter(m => m.id !== typingMsgId);
    
    messages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: data.reply || '分析完毕。',
      image: data.image ? `data:image/png;base64,${data.image}` : undefined,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    });
  } catch (error: any) {
    console.error('Chat error:', error);
    messages.value = messages.value.filter(m => m.id !== typingMsgId);
    messages.value.push({
      id: `err_${Date.now()}`,
      role: 'assistant',
      content: '通讯异常，请确认后端 AI 服务 (Port 8000) 是否已启动。',
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    });
  } finally {
    isSending.value = false;
    await scrollToBottom();
  }
};

// 图片处理逻辑
const processFile = (file: File) => {
  if (!file.type.startsWith('image/')) {
    alert('只支持上传图片格式哦！');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    selectedImage.value = e.target?.result as string;
  };
  reader.readAsDataURL(file);
};

const onDrop = (e: DragEvent) => {
  isDragging.value = false;
  const file = e.dataTransfer?.files?.[0];
  if (file) processFile(file);
};

const onDragOver = () => {
  isDragging.value = true;
};

const triggerImageUpload = () => {
  fileInput.value?.click();
};

const onFileChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (file) processFile(file);
  if (fileInput.value) fileInput.value.value = '';
};

const removeSelectedImage = () => {
  selectedImage.value = null;
};

// 麦克风音频录制
const startRecording = async () => {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.value = new MediaRecorder(stream, { mimeType: 'audio/webm' });
    audioChunks.value = [];
    
    mediaRecorder.value.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.value.push(e.data);
    };

    mediaRecorder.value.onstop = async () => {
      const audioBlob = new Blob(audioChunks.value, { type: 'audio/webm' });
      stream.getTracks().forEach(track => track.stop());
      await processVoice(audioBlob);
    };

    mediaRecorder.value.start();
    isRecording.value = true;
    recordingTime.value = 0;
    recordingInterval.value = window.setInterval(() => {
      recordingTime.value++;
    }, 1000);
  } catch (err) {
    alert('请求麦克风失败，请检查浏览器权限。');
    console.error(err);
  }
};

const stopRecording = () => {
  if (mediaRecorder.value && isRecording.value) {
    mediaRecorder.value.stop();
    isRecording.value = false;
    if (recordingInterval.value) clearInterval(recordingInterval.value);
  }
};

const processVoice = async (blob: Blob) => {
  isSending.value = true;
  try {
    const { text } = await apiService.transcribeVoice(blob);
    if (!text) {
      alert('语音识别失败：没有听清你说了什么。');
    } else {
      handleSend(undefined, text);
    }
  } catch (err) {
    console.error('Voice process error:', err);
    alert('语音接口异常。');
  } finally {
    isSending.value = false;
  }
};

const formatDuration = (s: number) => {
  const m = Math.floor(s / 60);
  const sec = s % 60;
  return `${m}:${sec.toString().padStart(2, '0')}`;
};

const clearChat = () => {
  if (confirm('是否清空当前所有聊天记录？')) {
    messages.value = [messages.value[0]];
  }
};
</script>

<template>
  <div class="h-screen w-full bg-[#e8eaf0] flex items-center justify-center font-sans overflow-hidden p-4">
    <!-- 桌面侧边背景 -->
    <div class="hidden xl:flex flex-col w-72 mr-12 space-y-6 opacity-80 animate-in fade-in slide-in-from-left-8 duration-700">
      <div class="bg-white/50 backdrop-blur-lg p-6 rounded-3xl border border-white/40 shadow-sm">
        <h3 class="text-slate-800 font-black text-lg mb-2">PigBOT Pro</h3>
        <p class="text-slate-500 text-xs leading-relaxed">独立版多模态智能兽医助手，采用先进的生猪生理识别链路。支持图片拖拽挂载与全维度会诊。</p>
      </div>
      <div class="flex items-center gap-4 px-4 py-3 bg-sky-50/50 rounded-2xl border border-sky-100 text-xs text-sky-700 font-bold">
         <UploadCloud class="w-5 h-5"/>
         <span>支持直接将图片拖入手机框</span>
      </div>
    </div>

    <!-- 手机外框容器 -->
    <div class="phone-frame relative shadow-[0_50px_100px_-20px_rgba(0,0,0,0.3)] animate-in zoom-in-95 duration-500">
      <div class="phone-case"></div>
      <div class="phone-button-power"></div>
      <div class="phone-button-volume-up"></div>
      <div class="phone-button-volume-down"></div>
      <div class="phone-button-silent"></div>

      <!-- 手机屏幕 -->
      <div 
        class="phone-screen overflow-hidden bg-[#f8f9fc] flex flex-col relative"
        @dragover.prevent="onDragOver"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <!-- 拖拽覆盖层 -->
        <div v-if="isDragging" class="absolute inset-0 z-[100] bg-sky-500/10 backdrop-blur-[2px] border-4 border-dashed border-sky-400 m-4 rounded-[2.5rem] flex items-center justify-center pointer-events-none transition-all">
          <div class="bg-white p-6 rounded-3xl shadow-xl flex flex-col items-center gap-3">
             <UploadCloud class="w-10 h-10 text-sky-500 animate-bounce" />
             <span class="text-sky-600 font-black">松手以挂载图片</span>
          </div>
        </div>
        
        <!-- 状态栏 -->
        <div class="h-12 w-full px-8 flex justify-between items-center text-[11px] font-bold text-slate-800 select-none z-50">
          <div class="flex items-center space-x-1">
             <span class="mr-1 mt-0.5">{{ currentTime }}</span>
             <Wifi class="w-3 h-3"/>
          </div>
          <div class="absolute left-1/2 -translate-x-1/2 top-3 w-24 h-6 bg-black rounded-[1.5rem] flex items-center justify-center">
            <div class="w-1.5 h-1.5 rounded-full bg-[#1c1c1e] mr-1"></div>
            <div class="w-5 h-1 bg-white/10 rounded-full"></div>
          </div>
          <div class="flex items-center space-x-1.5">
             <Signal class="w-3 h-3"/>
             <span class="opacity-80">5G</span>
             <Battery class="w-3.5 h-3.5 fill-slate-800"/>
          </div>
        </div>

        <header class="pt-2 pb-4 px-6 flex items-center justify-between bg-white/80 backdrop-blur-md border-b border-slate-100/50 z-40">
          <div class="flex items-center gap-3">
             <div class="w-10 h-10 rounded-[1.2rem] bg-gradient-to-tr from-sky-400 to-indigo-600 flex items-center justify-center text-white shadow-md">
                <Bot class="w-6 h-6" />
             </div>
             <div>
                <h1 class="text-sm font-black text-slate-800 flex items-center gap-1.5">PigBOT 🐷</h1>
                <p class="text-[9px] text-emerald-500 font-bold flex items-center gap-1">会诊专家在线</p>
             </div>
          </div>
          <button @click="clearChat" class="p-2.5 rounded-2xl bg-slate-50 text-slate-400 hover:text-red-400 transition-colors">
             <Trash2 class="w-4 h-4" />
          </button>
        </header>

        <!-- 聊天区域 -->
        <div ref="chatContainer" class="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth bg-slate-50/50">
          <div v-for="msg in messages" :key="msg.id" 
               :class="['flex w-full group animate-in slide-in-from-bottom-2 duration-300', msg.role === 'user' ? 'justify-end' : 'justify-start']">
            <div v-if="msg.role === 'assistant'" class="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shrink-0 mr-2 mt-1 shadow-sm">
               <Bot class="w-5 h-5" />
            </div>
            <div :class="['flex flex-col', msg.role === 'user' ? 'items-end' : 'items-start', 'max-w-[85%]', msg.role === 'user' ? 'min-w-[40px]' : '']">
              <div :class="[
                'px-4 py-3 rounded-2xl shadow-sm text-[13px]/relaxed relative overflow-hidden',
                msg.role === 'user' ? 'bg-sky-500 text-white rounded-tr-sm' : 'bg-white text-slate-700 rounded-tl-sm ring-1 ring-slate-100'
              ]">
                <div v-if="msg.image" class="mb-2 -mx-1 -mt-1 rounded-xl overflow-hidden border border-white/10 shadow-sm">
                   <img :src="msg.image" class="w-full h-auto max-h-[300px] object-cover" alt="attach" />
                </div>
                <div v-if="!msg.isTyping" class="whitespace-pre-wrap">{{ msg.content }}</div>
                <div v-if="msg.isTyping" class="flex gap-1.5 items-center py-1">
                  <div class="w-1.5 h-1.5 bg-sky-400 rounded-full animate-bounce [animation-delay:-0.32s]"></div>
                  <div class="w-1.5 h-1.5 bg-sky-400 rounded-full animate-bounce [animation-delay:-0.16s]"></div>
                  <div class="w-1.5 h-1.5 bg-sky-400 rounded-full animate-bounce"></div>
                </div>
              </div>
              <span class="text-[9px] text-slate-300 mt-1.5 px-2 font-medium">{{ msg.timestamp }}</span>
            </div>
          </div>
        </div>

        <!-- 录制遮罩 -->
        <div v-if="isRecording" class="absolute inset-0 bg-white/95 backdrop-blur-xl z-[60] flex flex-col items-center justify-center p-10 animate-in fade-in zoom-in-95 duration-300">
           <div class="w-24 h-24 rounded-full bg-red-50 flex items-center justify-center mb-8 relative">
              <div class="absolute inset-0 bg-red-500 rounded-full animate-ping opacity-10"></div>
              <Mic class="w-10 h-10 text-red-500" />
           </div>
           <h4 class="text-red-500 font-black text-xl mb-2">{{ formatDuration(recordingTime) }}</h4>
           <div class="mt-12 flex gap-4 w-full">
              <button @click="stopRecording" class="flex-1 bg-red-500 hover:bg-red-600 text-white py-4 rounded-[1.5rem] font-bold shadow-lg transition-all active:scale-95">完成录音</button>
              <button @click="isRecording = false; stopRecording()" class="p-4 bg-slate-100 text-slate-400 rounded-[1.5rem] hover:bg-slate-200 transition-colors"><X/></button>
           </div>
        </div>

        <!-- 底部输入栏 -->
        <footer class="bg-white px-5 pt-3 pb-8 border-t border-slate-100 relative shadow-2xl transition-all duration-300">
          <!-- 图片挂载预览区 -->
          <div v-if="selectedImage" class="mb-4 animate-in slide-in-from-bottom-4 zoom-in-95 duration-300">
             <div class="relative w-24 h-24 group">
                <img :src="selectedImage" class="w-full h-full object-cover rounded-2xl ring-1 ring-slate-100 shadow-md transition-transform group-hover:scale-95" />
                <button 
                  @click="removeSelectedImage" 
                  class="absolute -top-2 -right-2 w-7 h-7 bg-white/90 backdrop-blur shadow-lg rounded-full flex items-center justify-center text-red-500 hover:bg-red-500 hover:text-white transition-all ring-1 ring-slate-100"
                >
                  <X class="w-4 h-4" />
                </button>
                <div class="absolute inset-0 bg-black/5 opacity-0 group-hover:opacity-100 rounded-2xl pointer-events-none transition-opacity"></div>
             </div>
          </div>

          <div class="flex items-center gap-3 mb-3">
             <button @click="triggerImageUpload" class="p-2.5 rounded-xl bg-slate-50 text-slate-400 active:bg-sky-50 active:text-sky-500 transition-colors shadow-sm"><ImageIcon class="w-5 h-5"/></button>
             <button @click="startRecording" class="p-2.5 rounded-xl bg-slate-50 text-slate-400 active:bg-red-50 active:text-red-500 transition-colors shadow-sm"><Mic class="w-5 h-5"/></button>
             <div class="w-px h-4 bg-slate-100 mx-1"></div>
             <button class="p-2.5 rounded-xl bg-slate-50 text-slate-400 shadow-sm"><Paperclip class="w-5 h-5"/></button>
          </div>
          
          <div class="flex items-end gap-3">
            <input type="file" ref="fileInput" class="hidden" accept="image/*" @change="onFileChange" />
            <div class="flex-1 bg-slate-50 rounded-2xl ring-1 ring-slate-100 focus-within:ring-sky-400 focus-within:bg-white transition-all overflow-hidden group shadow-inner">
               <textarea v-model="inputMessage" @keydown.enter.prevent="handleSend()" placeholder="输入会诊信息或询问图片内容..."
                         class="w-full bg-transparent border-none focus:ring-0 resize-none h-12 py-3 px-4 text-sm text-slate-800 placeholder:text-slate-300"></textarea>
            </div>
            <button @click="handleSend()" :disabled="(!inputMessage.trim() && !selectedImage && !isSending) || isSending"
                    class="w-12 h-12 bg-sky-500 text-white rounded-2xl flex items-center justify-center shadow-[0_8px_20px_-6px_rgba(14,165,233,0.5)] active:scale-90 disabled:opacity-30 disabled:scale-100 transition-all">
                <Send v-if="!isSending" class="w-5 h-5" />
                <Loader2 v-else class="w-5 h-5 animate-spin" />
            </button>
          </div>

          <!-- 底部手势条 -->
          <div class="absolute bottom-2 left-1/2 -translate-x-1/2 w-32 h-1 bg-slate-800/10 rounded-full"></div>
        </footer>

      </div>
    </div>
  </div>
</template>

<style scoped>
.phone-frame {
  width: 390px;
  height: 844px;
  background: #1c1c1e;
  border-radius: 4rem;
  padding: 12px;
  box-sizing: border-box;
}

.phone-screen {
  width: 100%;
  height: 100%;
  border-radius: 3.2rem;
  position: relative;
  box-shadow: inset 0 0 40px rgba(0,0,0,0.4);
}

.phone-case {
  position: absolute;
  inset: 0;
  border: 4px solid #3a3a3c;
  border-radius: 4rem;
  pointer-events: none;
}

.phone-button-power {
  position: absolute;
  right: -2px;
  top: 180px;
  width: 3px;
  height: 90px;
  background: #3a3a3c;
  border-radius: 0 4px 4px 0;
}

.phone-button-silent {
  position: absolute;
  left: -2px;
  top: 100px;
  width: 3px;
  height: 30px;
  background: #3a3a3c;
  border-radius: 4px 0 0 4px;
}

.phone-button-volume-up, .phone-button-volume-down {
  position: absolute;
  left: -2px;
  width: 3px;
  height: 60px;
  background: #3a3a3c;
  border-radius: 4px 0 0 4px;
}

.phone-button-volume-up { top: 160px; }
.phone-button-volume-down { top: 235px; }

div::-webkit-scrollbar {
  width: 0px;
}

textarea {
  line-height: 1.5;
}

@media (max-height: 900px) {
  .phone-frame {
    transform: scale(0.9);
  }
}

@media (max-height: 800px) {
  .phone-frame {
    transform: scale(0.8);
  }
}

@media (max-width: 500px) {
  .h-screen {
    padding: 0;
  }
  .phone-frame {
    width: 100%;
    height: 100%;
    border-radius: 0;
    padding: 0;
  }
  .phone-screen {
    border-radius: 0;
  }
  .phone-button-power, .phone-button-silent, .phone-button-volume-up, .phone-button-volume-down, .phone-case {
    display: none;
  }
  .xl\:flex {
    display: none !important;
  }
}
</style>



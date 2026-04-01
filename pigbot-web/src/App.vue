<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { 
  Bot, User, Send, Image as ImageIcon, Mic, StopCircle, 
  Paperclip, MoreHorizontal, Info, Loader2, X, Trash2
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

// 录音相关
const isRecording = ref(false);
const mediaRecorder = ref<MediaRecorder | null>(null);
const audioChunks = ref<Blob[]>([]);
const recordingTime = ref(0);
const recordingInterval = ref<number | null>(null);

onMounted(() => {
  // 欢迎语
  messages.value.push({
    id: 'welcome',
    role: 'assistant',
    content: '你好！我是您的两头乌专属智能助手 PigBOT 🐽。现在我已经独立出来啦！不论是上传现场图片还是直接对我说语音，我都能为您提供专业的诊断建议！',
    timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  });
});

const scrollToBottom = async () => {
  await nextTick();
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
  }
};

const handleSend = async (imageB64?: string, manualText?: string) => {
  const text = manualText || inputMessage.value.trim();
  if (!text && !imageB64) return;
  
  if (isSending.value) return;

  const newUserMsgId = Date.now().toString();
  const timeStr = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

  // 1. 用户消息入队
  messages.value.push({
    id: newUserMsgId,
    role: 'user',
    content: text,
    image: imageB64,
    timestamp: timeStr
  });

  inputMessage.value = '';
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

    const urls = imageB64 ? [imageB64] : [];
    
    // 3. 调用 AI 接口
    const data = await apiService.chat(history, urls);

    // 移除 typing
    messages.value = messages.value.filter(m => m.id !== typingMsgId);
    
    // 4. 展示回复
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

// --- 图片上传 ---
const triggerImageUpload = () => {
  fileInput.value?.click();
};

const onFileChange = (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (event) => {
    const b64 = event.target?.result as string;
    handleSend(b64, inputMessage.value || '帮我分析一下这张照片。');
  };
  reader.readAsDataURL(file);
  if (fileInput.value) fileInput.value.value = '';
};

// --- 语音录制 ---
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
      // 停止所有轨道
      stream.getTracks().forEach(track => track.stop());
      
      // 上传转文字
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
  <div class="h-screen w-full bg-[#f0f2f5] p-4 flex items-center justify-center font-sans overflow-hidden">
    <!-- 独立应用容器 -->
    <div class="w-full h-full max-w-6xl bg-white shadow-2xl rounded-[2rem] flex overflow-hidden ring-1 ring-black/5 relative">
      
      <!-- 侧边导航 (QQ-like) -->
      <aside class="w-20 bg-slate-800 flex flex-col items-center py-8 gap-10 shrink-0">
        <div class="w-12 h-12 rounded-full overflow-hidden border-2 border-sky-400 shadow-md">
          <img src="https://ui-avatars.com/api/?name=User&background=0284c7&color=fff" alt="avatar" />
        </div>
        <div class="flex flex-col gap-8 text-slate-400">
          <Bot class="w-7 h-7 text-sky-400" />
          <User class="w-7 h-7 hover:text-white transition-colors cursor-pointer" />
          <Info class="w-7 h-7 hover:text-white transition-colors cursor-pointer" />
        </div>
        <div class="mt-auto mb-4">
          <Trash2 @click="clearChat" class="w-6 h-6 text-slate-600 hover:text-red-400 transition-colors cursor-pointer" />
        </div>
      </aside>

      <!-- 聊天主窗口 -->
      <main class="flex-1 flex flex-col bg-[#f5f6fa] relative">
        <!-- Header -->
        <header class="h-20 bg-white/70 backdrop-blur-md px-10 flex items-center justify-between border-b border-slate-100 z-10">
          <div class="flex items-center gap-4">
            <div class="relative">
              <div class="w-12 h-12 rounded-full bg-gradient-to-tr from-sky-400 to-blue-600 flex items-center justify-center text-white shadow-lg">
                <Bot class="w-7 h-7" />
              </div>
              <span class="absolute bottom-1 right-0 w-3.5 h-3.5 bg-green-500 border-2 border-white rounded-full"></span>
            </div>
            <div>
              <h1 class="text-xl font-bold text-slate-800">PigBOT 专家对话站</h1>
              <p class="text-xs text-slate-500 font-medium">视觉分析 · 语音会诊 · 独立版</p>
            </div>
          </div>
          <div class="flex gap-4">
             <button class="p-3 rounded-full bg-slate-100 hover:bg-slate-200 transition-colors text-slate-500">
               <MoreHorizontal class="w-6 h-6" />
             </button>
          </div>
        </header>

        <!-- Messages Area -->
        <div 
          ref="chatContainer"
          class="flex-1 overflow-y-auto p-10 space-y-8 scroll-smooth"
        >
          <div 
            v-for="msg in messages" 
            :key="msg.id"
            :class="[
              'flex w-full animate-in fade-in slide-in-from-bottom-3 duration-500',
              msg.role === 'user' ? 'justify-end' : 'justify-start'
            ]"
          >
            <!-- Assistant Avatar -->
            <div v-if="msg.role === 'assistant'" class="w-10 h-10 rounded-full bg-blue-600 flex items-center justify-center text-white shrink-0 mr-4 shadow-sm">
              <Bot class="w-6 h-6" />
            </div>

            <div :class="['flex flex-col max-w-[65%]', msg.role === 'user' ? 'items-end' : 'items-start']">
              <div class="text-[11px] text-slate-400 mb-2 px-1 ont-mono">
                {{ msg.role === 'assistant' ? 'PigBOT' : 'ME' }} • {{ msg.timestamp }}
              </div>
              
              <div 
                :class="[
                  'px-5 py-3.5 rounded-[1.5rem] shadow-sm text-sm/relaxed relative group',
                  msg.role === 'user' 
                    ? 'bg-gradient-to-br from-sky-500 to-blue-600 text-white rounded-tr-sm' 
                    : 'bg-white text-slate-700 rounded-tl-sm ring-1 ring-slate-100'
                ]"
              >
                <!-- Text -->
                <div v-if="!msg.isTyping" class="whitespace-pre-wrap select-text">{{ msg.content }}</div>
                
                <!-- Image Attach -->
                <div v-if="msg.image" class="mt-3 rounded-2xl overflow-hidden border border-white/20 shadow-md">
                   <img :src="msg.image" class="max-w-[320px] h-auto object-contain" alt="attach" />
                </div>

                <!-- Typing Dots -->
                <div v-if="msg.isTyping" class="flex gap-2 items-center h-5 w-12 justify-center">
                  <div class="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                  <div class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                  <div class="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"></div>
                </div>
              </div>
            </div>

            <!-- User Avatar -->
            <div v-if="msg.role === 'user'" class="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-slate-500 shrink-0 ml-4 shadow-sm ring-2 ring-white">
              <User class="w-6 h-6" />
            </div>
          </div>
        </div>

        <!-- Footer Input Area -->
        <footer class="bg-white border-t border-slate-100 p-6">
          <!-- Utils -->
          <div class="flex items-center gap-2 mb-4">
             <button 
              @click="triggerImageUpload"
              class="p-2.5 rounded-xl hover:bg-sky-50 text-slate-500 hover:text-sky-600 transition-all flex items-center gap-2 text-xs font-semibold"
             >
               <ImageIcon class="w-5 h-5" /> 图片
             </button>
             <button 
              @click="isRecording ? stopRecording() : startRecording()"
              :class="[
                'p-2.5 rounded-xl transition-all flex items-center gap-2 text-xs font-semibold',
                isRecording ? 'bg-red-50 text-red-600' : 'hover:bg-emerald-50 text-slate-500 hover:text-emerald-600'
              ]"
             >
               <component :is="isRecording ? StopCircle : Mic" class="w-5 h-5" />
               {{ isRecording ? '松开结束 (' + formatDuration(recordingTime) + ')' : '语音' }}
             </button>
             <button class="p-2.5 rounded-xl hover:bg-slate-50 text-slate-500 transition-all">
               <Paperclip class="w-5 h-5" />
             </button>
          </div>

          <div class="flex items-end gap-4 px-1 relative">
            <input 
              type="file" 
              ref="fileInput" 
              class="hidden" 
              accept="image/*" 
              @change="onFileChange" 
            />
            
            <div class="flex-1 bg-slate-50 rounded-[1.5rem] p-1.5 ring-1 ring-slate-200 focus-within:ring-sky-400 focus-within:bg-white transition-all">
              <textarea 
                v-model="inputMessage"
                @keydown.enter.prevent="handleSend()"
                placeholder="在此输入您的会诊需求或建议..."
                class="w-full bg-transparent border-none focus:ring-0 resize-none h-14 py-2 px-4 text-sm text-slate-800"
              ></textarea>
            </div>

            <button 
              @click="handleSend()"
              :disabled="(!inputMessage.trim() && !isSending) || isSending"
              class="w-14 h-14 bg-sky-500 text-white rounded-full flex items-center justify-center shadow-lg hover:bg-sky-600 disabled:opacity-30 disabled:scale-90 transition-all"
            >
               <Send v-if="!isSending" class="w-6 h-6 ml-1" />
               <Loader2 v-else class="w-6 h-6 animate-spin" />
            </button>

            <!-- Recording Overlay -->
            <div 
              v-if="isRecording"
              class="absolute inset-0 bg-white/95 rounded-[1.5rem] flex items-center px-6 gap-4 animate-in fade-in slide-in-from-top-4 duration-300 z-20 border border-emerald-200"
            >
               <div class="flex gap-1.5 items-end h-8">
                  <div class="w-1.5 bg-emerald-500 animate-pulse h-4"></div>
                  <div class="w-1.5 bg-emerald-500 animate-pulse h-8 [animation-delay:-0.2s]"></div>
                  <div class="w-1.5 bg-emerald-500 animate-pulse h-6 [animation-delay:-0.4s]"></div>
                  <div class="w-1.5 bg-emerald-500 animate-pulse h-10 [animation-delay:-0.1s]"></div>
               </div>
               <span class="text-sm font-bold text-emerald-600 tabular-nums">录音中: {{ formatDuration(recordingTime) }}</span>
               <div class="ml-auto flex gap-2">
                  <button @click="stopRecording()" class="px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-black shadow-lg">发送</button>
                  <button @click="isRecording = false; stopRecording()" class="p-2 bg-slate-100 text-slate-500 rounded-xl hover:bg-red-50 hover:text-red-600"><X class="w-5 h-5"/></button>
               </div>
            </div>
          </div>
        </footer>
      </main>

      <!-- 右侧信息面板 (Glassmorphism) -->
      <aside class="w-80 bg-white border-l border-slate-100 hidden lg:flex flex-col">
        <div class="p-8 space-y-8">
          <div class="text-center">
            <h2 class="text-lg font-black text-slate-800">PigBOT 智能内核</h2>
            <div class="mt-4 flex justify-center">
               <div class="p-4 bg-sky-50 rounded-3xl ring-8 ring-sky-50/30">
                 <Bot class="w-10 h-10 text-sky-600" />
               </div>
            </div>
          </div>

          <div class="space-y-6">
            <div class="p-5 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-[2rem] text-white shadow-xl">
               <p class="text-[10px] font-bold uppercase tracking-widest opacity-80">当前模式</p>
               <h3 class="text-lg font-black mt-1">多智能体分群协作</h3>
               <p class="text-xs mt-3 opacity-90 leading-relaxed font-medium">实时扫描生猪轨迹，融合兽医专家知识库进行高精准、解释性疾病诊断。</p>
            </div>

            <div class="space-y-4">
              <h4 class="text-xs font-black text-slate-400 uppercase tracking-widest px-1">支持功能</h4>
              <div class="space-y-2">
                <div v-for="f in ['多模态图片识别', '语音听写理解', '生长异常预警', '全量路径研判']" :key="f" 
                     class="flex items-center gap-3 p-3 bg-slate-50 rounded-2xl text-xs font-bold text-slate-600 ring-1 ring-slate-100">
                  <div class="w-2 h-2 rounded-full bg-sky-400"></div>
                  {{ f }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>

    </div>
  </div>
</template>

<style scoped>
/* 滚动条优化 */
div::-webkit-scrollbar {
  width: 6px;
}
div::-webkit-scrollbar-thumb {
  background: rgba(0,0,0,0.08);
  border-radius: 10px;
}
div::-webkit-scrollbar-thumb:hover {
  background: rgba(0,0,0,0.15);
}

textarea {
  min-height: 56px;
}

.select-text {
  user-select: text;
}
</style>

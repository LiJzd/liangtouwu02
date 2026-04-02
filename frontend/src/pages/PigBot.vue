<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { apiService } from '../api';
import { 
  Bot, User, Send, Image as ImageIcon, Mic, Paperclip, MoreHorizontal, Info, Loader2 
} from 'lucide-vue-next';

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

// 初始化欢迎语
onMounted(() => {
  messages.value.push({
    id: Date.now().toString(),
    role: 'assistant',
    content: '你好！我是您的两头乌专属智能助手 PigBOT 🐽。您可以向我咨询生猪喂养、异常诊断等问题，点击下方图片按钮还可以发送现场实况给我哦~',
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

const handleSend = async (imageB64?: string) => {
  const text = inputMessage.value.trim();
  if (!text && !imageB64) return;
  
  if (isSending.value) return;

  const newUserMsgId = Date.now().toString();
  const timeStr = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });

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
    // 构造发送给后端的结构
    // 过滤掉 typing 状态的消息，保留完整的对话历史
    const apiMessages = messages.value
      .filter(m => !m.isTyping) // 只过滤掉正在输入的消息
      .map(m => ({
        role: m.role,
        content: m.content
      }));
      
    const recentMessages = apiMessages.slice(-10); // 取最后 10 条作为上下文（包含用户和助手的对话）
    const urlsToSends = imageB64 ? [imageB64] : [];

    // 调用真正后端的 AI 接口
    const response = await apiService.chatWithPigBot(recentMessages, urlsToSends);
    
    // 移除 typing
    messages.value = messages.value.filter(m => m.id !== typingMsgId);
    
    // 添加回复
    messages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: response.reply || '分析完毕，我未得到任何有效诊断结果。',
      image: response.image ? `data:image/png;base64,${response.image}` : undefined,
      timestamp: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    });
  } catch (error: any) {
    console.error('Chat Error:', error);
    messages.value = messages.value.filter(m => m.id !== typingMsgId);
    messages.value.push({
      id: Date.now().toString(),
      role: 'assistant',
      content: `由于网络原因，我暂时无法进行回复 (${error.message})。`,
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
    // 如果没有输入文字，默认加一句提示
    if (!inputMessage.value.trim()) {
      inputMessage.value = '请帮我看看这张照片，这头猪是否有异常？';
    }
    handleSend(base64String);
  };
  reader.readAsDataURL(file);
  
  if (fileInput.value) fileInput.value.value = ''; // 清空选择
};
</script>

<template>
  <!-- 整个聊天容器，设计类似 QQ 窗口且置中高屏幕 -->
  <div class="h-[calc(100vh-8rem)] min-h-[600px] w-full max-w-5xl mx-auto flex gap-6 pb-4">
    
    <!-- 侧边辅助说明 (可选) -->
    <div class="hidden lg:flex w-64 bg-white/70 backdrop-blur-xl rounded-[2rem] shadow-sm border border-slate-100 flex-col overflow-hidden">
      <div class="h-40 bg-gradient-to-b from-sky-400 to-blue-500 relative flex items-center justify-center text-white">
        <Bot class="w-16 h-16 opacity-90 drop-shadow-md" />
        <div class="absolute bottom-4 text-center w-full">
          <p class="font-bold text-lg tracking-wider">PigBOT 专家</p>
          <p class="text-xs text-blue-100 mt-1">AI 驱动 - 24小时在线</p>
        </div>
      </div>
      <div class="p-6 text-slate-600 text-sm space-y-4">
        <p class="flex items-start gap-2">
          <Info class="w-4 h-4 mt-0.5 text-blue-500 shrink-0" />
          <span>我可以为您分析上传的图片并进行病理解读。</span>
        </p>
        <p class="flex items-start gap-2">
          <Info class="w-4 h-4 mt-0.5 text-blue-500 shrink-0" />
          <span>我是集成了多模态大模型和 RAG 知识库的综合诊断型智能体。</span>
        </p>
        <p class="flex items-start gap-2">
          <Info class="w-4 h-4 mt-0.5 text-blue-500 shrink-0" />
          <span>支持多轮追问。您可以直接像和真人聊天一样提问。</span>
        </p>
      </div>
    </div>

    <!-- 聊天主窗口：模仿现代拟物风格 -->
    <div class="flex-1 bg-white/80 backdrop-blur-2xl rounded-[2rem] shadow-lg border border-white flex flex-col overflow-hidden ring-1 ring-slate-100">
      
      <!-- 头部 -->
      <header class="h-16 px-6 border-b border-slate-100 bg-white/50 flex flex-row items-center justify-between shrink-0">
        <div class="flex items-center gap-3">
          <div class="relative">
            <div class="w-10 h-10 rounded-full bg-gradient-to-tr from-sky-400 to-blue-500 flex items-center justify-center text-white shadow-sm ring-2 ring-white">
              <Bot class="w-6 h-6" />
            </div>
            <span class="absolute bottom-0 right-0 w-3 h-3 bg-green-500 border-2 border-white rounded-full"></span>
          </div>
          <div>
            <h2 class="font-bold text-slate-800 tracking-tight leading-tight">专家会诊 PigBOT</h2>
            <p class="text-xs text-slate-500 flex items-center gap-1.5 mt-0.5">
              <span>手机在线 - WiFi</span>
              <span class="w-1 h-1 rounded-full bg-slate-300"></span>
              <span class="text-xs">支持视觉识别</span>
            </p>
          </div>
        </div>
        <button class="w-10 h-10 rounded-full hover:bg-slate-100 flex items-center justify-center text-slate-500 transition-colors">
          <MoreHorizontal class="w-5 h-5" />
        </button>
      </header>

      <!-- 消息体区域 -->
      <main 
        class="flex-1 overflow-y-auto w-full p-6 space-y-6 scroll-smooth bg-[#f5f6fa]"
        ref="chatContainer"
      >
        <div 
          v-for="msg in messages" 
          :key="msg.id"
          class="flex w-full group"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <!-- 助手头像布局 -->
          <div v-if="msg.role === 'assistant'" class="w-9 h-9 rounded-full bg-blue-500 shrink-0 mr-3 flex items-center justify-center text-white shadow-sm mt-1">
            <Bot class="w-5 h-5" />
          </div>

          <div 
            class="flex flex-col relative max-w-[70%]"
            :class="msg.role === 'user' ? 'items-end' : 'items-start'"
          >
            <!-- 名字与时间 -->
            <div class="text-[11px] text-slate-400 mb-1 flex items-center gap-2 px-1">
              <span v-if="msg.role === 'assistant'">PigBOT</span>
              <span>{{ msg.timestamp }}</span>
              <span v-if="msg.role === 'user'">我</span>
            </div>

            <!-- 消息气泡 -->
            <div 
              class="relative px-4 py-2.5 text-sm/relaxed select-text min-h-[40px] flex flex-col"
              :class="[
                msg.role === 'user'
                  ? 'bg-gradient-to-br from-blue-500 to-sky-500 text-white rounded-[1.2rem] rounded-tr-sm shadow-[0_2px_10px_-3px_rgba(59,130,246,0.3)]'
                  : 'bg-white text-slate-800 rounded-[1.2rem] rounded-tl-sm shadow-sm ring-1 ring-slate-100',
              ]"
            >
              <!-- 文本内容，支持换行呈现 -->
              <div v-if="!msg.isTyping" class="whitespace-pre-wrap word-break-all">{{ msg.content }}</div>
              
              <!-- 图像模态呈现 -->
              <div v-if="msg.image" class="mt-2 rounded-xl border border-white/20 overflow-hidden bg-slate-100 shadow-sm max-w-[240px]">
                <img :src="msg.image" class="w-full h-auto object-cover" alt="附带截图" />
              </div>

              <!-- 打字提示条 (针对 isTyping) -->
              <div v-if="msg.isTyping" class="flex gap-1.5 items-center h-5 w-10">
                <span class="w-1.5 h-1.5 bg-slate-300 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                <span class="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                <span class="w-1.5 h-1.5 bg-slate-500 rounded-full animate-bounce"></span>
              </div>
            </div>
            
          </div>

          <!-- 用户头像布局 -->
          <div v-if="msg.role === 'user'" class="w-9 h-9 rounded-full bg-slate-200 shrink-0 ml-3 flex items-center justify-center text-slate-500 overflow-hidden shadow-sm mt-1 ring-1 ring-white">
            <User class="w-5 h-5" />
          </div>
        </div>
      </main>

      <!-- 底部输入栏 -->
      <footer class="p-4 bg-white border-t border-slate-100 shrink-0">
        <!-- 隐藏的文件选择器 -->
        <input 
          type="file" 
          ref="fileInput" 
          class="hidden" 
          accept="image/*"
          @change="handleFileChange"
        />

        <!-- 工具栏 -->
        <div class="flex items-center gap-2 mb-2 px-1">
          <button 
            @click="triggerFileUpload"
            class="p-2 rounded-xl text-slate-400 hover:text-blue-500 hover:bg-blue-50 transition-colors tooltip relative group"
            title="发送图片"
          >
            <ImageIcon class="w-5 h-5" />
          </button>
          <button 
            class="p-2 rounded-xl text-slate-400 hover:text-blue-500 hover:bg-blue-50 transition-colors"
            title="发送语音"
          >
            <Mic class="w-5 h-5" />
          </button>
          <button 
            class="p-2 rounded-xl text-slate-400 hover:text-blue-500 hover:bg-blue-50 transition-colors"
            title="附件"
          >
            <Paperclip class="w-5 h-5" />
          </button>
        </div>

        <div class="flex flex-row items-end gap-3 px-1">
          <!-- 文本自适应框，简单使用了 textarea 设定高度 -->
          <div class="flex-1 rounded-2xl bg-[#f8f9fa] border border-transparent focus-within:bg-white focus-within:border-blue-200 focus-within:shadow-[0_0_0_4px_rgba(59,130,246,0.05)] transition-all flex pt-1">
            <textarea
              v-model="inputMessage"
              placeholder="请输入您的问题或发送照片，按 Enter 发送..."
              class="w-full bg-transparent border-none focus:ring-0 resize-none py-2 px-4 h-[72px] text-sm text-slate-700 placeholder:text-slate-400"
              @keydown.enter.prevent="handleSendText"
            ></textarea>
          </div>
          
          <button 
            @click="handleSendText"
            :disabled="(!inputMessage.trim() && !isSending) || isSending"
            class="h-12 w-20 shrink-0 bg-blue-500 rounded-2xl flex items-center justify-center text-white shadow-[0_4px_12px_rgba(59,130,246,0.25)] hover:bg-blue-600 hover:-translate-y-0.5 active:translate-y-0 transition-all disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:bg-blue-500 mb-2.5"
          >
            <Send v-if="!isSending" class="w-5 h-5 ml-1" />
            <Loader2 v-else class="w-5 h-5 animate-spin" />
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
/* 定义滚动条的纤细优美效果 */
main::-webkit-scrollbar {
  width: 6px;
  background-color: transparent;
}
main::-webkit-scrollbar-thumb {
  background-color: rgba(0,0,0,0.1);
  border-radius: 99px;
}
main::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0,0,0,0.2);
}
.word-break-all {
  word-break: break-word;
}
</style>

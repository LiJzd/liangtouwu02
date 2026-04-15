<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { apiService, type BriefingStreamEvent } from '../api';
import { marked } from 'marked';
import { cn } from '../utils';

interface TraceLog {
  id: string;
  message: string;
  timestamp: string;
  status: 'info' | 'success' | 'warning' | 'error';
}

const history = ref<any[]>([]);
const selectedBriefing = ref<any>(null);
const loading = ref(false);
const triggering = ref(false);

// 展示引擎状态
const streamStatus = ref('');
const bufferedContent = ref(''); // 已上屏的内容
const contentQueue = ref<string[]>([]); // 待上屏的内容字符队列
const traceQueue = ref<any[]>([]); // 待上屏的思维链队列
const displayTraceLogs = ref<TraceLog[]>([]); // 界面显示的思维链
const streamError = ref('');
const isStreaming = ref(false);
const isGenerating = ref(false);
const isSkipping = ref(false);
const displayTimeout = ref<any>(null);

const loadHistory = async () => {
  loading.value = true;
  try {
    const res = await apiService.getBriefingHistory(15);
    history.value = res;
    if (res.length > 0 && !selectedBriefing.value) {
      selectedBriefing.value = res[0];
    }
  } catch (e) {
    console.error('加载简报历史失败', e);
  } finally {
    loading.value = false;
  }
};

const handleSelect = (item: any) => {
  if (!isStreaming.value) {
    selectedBriefing.value = item;
    bufferedContent.value = '';
    streamStatus.value = '';
    streamError.value = '';
    displayTraceLogs.value = [];
  } else {
    selectedBriefing.value = item;
  }
};

/**
 * 展示控制引擎：从队列中匀速抽取内容到界面
 */
const startDisplayEngine = () => {
  if (displayTimeout.value) return;

  // [Logic] 核心渲染循环引擎 (Pacing Engine)
  const processNext = () => {
    // 检查停止条件
    if (!isGenerating.value && contentQueue.value.length === 0 && traceQueue.value.length === 0) {
      streamStatus.value = '分析报告已生成完成';
      // [Fix] 动画结束后将完整内容同步到选中对象，防止 isStreaming 状态切换导致显示空白
      if (selectedBriefing.value) {
        selectedBriefing.value.content = bufferedContent.value;
      }
      displayTimeout.value = null;
      isStreaming.value = false; // 只有在动画也完成后才重置此状态
      return;
    }

    let delay = 20; // 提高基础响应速度

    // [Fix] 加速模式：瞬时清空所有队列
    if (isSkipping.value) {
      // 1. 同步思维链
      if (traceQueue.value.length > 0) {
        displayTraceLogs.value.push(...traceQueue.value.map(t => ({
          id: Math.random().toString(36).substr(2, 9),
          message: t.message,
          timestamp: new Date().toLocaleTimeString(),
          status: t.level === 'DEBUG' ? 'info' : 'success'
        })));
        traceQueue.value = [];
      }
      // 2. 同步正文
      if (contentQueue.value.length > 0) {
        bufferedContent.value += contentQueue.value.join('');
        contentQueue.value = [];
      }
      delay = 0; 
    } 
    // 正常模式：优先处理思维链
    else if (traceQueue.value.length > 0) {
      const trace = traceQueue.value.shift();
      if (trace) {
        displayTraceLogs.value.push({
            id: Math.random().toString(36).substr(2, 9),
            message: trace.message,
            timestamp: new Date().toLocaleTimeString(),
            status: trace.level === 'DEBUG' ? 'info' : 'success'
        });
        delay = 400; // 缩短思维链停留时间，提升节奏感
      }
    } 
    // 然后处理正文内容 (Content Typewriter)
    else if (contentQueue.value.length > 0) {
      const nextChar = contentQueue.value.shift();
      if (nextChar) bufferedContent.value += nextChar;
      delay = (Math.random() * 10 + 15); // 加快打字机速度
    } 
    else {
      // 队列为空但流未结束，心跳轮询
      delay = 100; 
    }

    displayTimeout.value = setTimeout(processNext, delay);
  };

  processNext();
};

const skipAnimation = () => {
    isSkipping.value = true;
    streamStatus.value = '渲染中...';
    // 立即触发一次处理以清空队列
    if (displayTimeout.value) {
        clearTimeout(displayTimeout.value);
        displayTimeout.value = null;
    }
    startDisplayEngine();
};

const triggerNew = async () => {
  if (triggering.value) return;
  
  const traceId = `briefing_${Date.now()}`;
  triggering.value = true;
  isStreaming.value = true;
  isGenerating.value = true;
  isSkipping.value = false;
  bufferedContent.value = '';
  contentQueue.value = [];
  traceQueue.value = [];
  displayTraceLogs.value = [];
  streamStatus.value = '唤醒 AI 分析大脑...';
  streamError.value = '';

  selectedBriefing.value = { briefingDate: new Date().toISOString().split('T')[0], content: '' };
  
  startDisplayEngine();

  try {
    await apiService.streamBriefing((event: BriefingStreamEvent) => {
      if (event.event === 'status') {
        streamStatus.value = event.data?.message || '';
      } else if (event.event === 'trace') {
        traceQueue.value.push(event.data);
      } else if (event.event === 'chunk') {
        const text = event.data?.text || '';
        if (isSkipping.value) {
           bufferedContent.value += text;
        } else {
           contentQueue.value.push(...text.split(''));
        }
      } else if (event.event === 'done') {
        isGenerating.value = false;
        // 如果加速模式，强制立即同步最后的内容
        if (isSkipping.value && selectedBriefing.value) {
            selectedBriefing.value.content = bufferedContent.value;
        }
      } else if (event.event === 'error') {
        streamError.value = event.data?.detail || event.data?.message || '生成异常';
        isGenerating.value = false;
        isStreaming.value = false;
        // 发生错误时也将已生成的内容保存下来
        if (selectedBriefing.value) {
            selectedBriefing.value.content = bufferedContent.value;
        }
      }
    }, traceId);
  } catch (e: any) {
    console.error('流式简报异常:', e);
    streamError.value = e.message || '连接 AI 服务失败';
    isStreaming.value = false;
  }

  try { await apiService.triggerBriefing(); } catch (e) {}
  // 等待流结束后刷新历史
  const checkFinished = setInterval(() => {
    if (!isStreaming.value) {
      loadHistory();
      clearInterval(checkFinished);
    }
  }, 1000);
  triggering.value = false;
};

onMounted(() => {
  loadHistory();
});
</script>

<template>
  <div class="h-full flex flex-col space-y-6">
    <!-- 顶部标题区 -->
    <div class="flex items-center justify-between bg-white/95 backdrop-blur-md p-6 rounded-2xl border border-emerald-200 shadow-sm relative overflow-hidden group">
      <!-- 动态氛围背景 -->
      <div class="absolute inset-0 bg-gradient-to-r from-emerald-500/5 to-transparent pointer-events-none opacity-0 group-hover:opacity-100 transition-opacity duration-700"></div>
      
      <div class="flex items-center space-x-6 relative">
        <div class="w-14 h-14 bg-gradient-to-br from-emerald-500 to-secondary rounded-xl flex items-center justify-center shadow-lg shadow-secondary/20 relative">
           <div v-if="isStreaming" class="absolute inset-0 bg-white/20 animate-ping rounded-xl"></div>
           <span class="material-symbols-outlined text-white text-3xl">description</span>
        </div>
        <div>
          <h2 class="text-2xl font-headline font-bold text-emerald-950 tracking-tight">每日诊断简报</h2>
          <p class="text-xs text-emerald-900/60 font-inter font-bold uppercase tracking-[0.2em] mt-1 flex items-center">
            Daily AI Reasoning Engine
            <span v-if="isStreaming" class="ml-3 flex space-x-1">
                <span class="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0s"></span>
                <span class="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></span>
                <span class="w-1 h-1 bg-emerald-400 rounded-full animate-bounce" style="animation-delay: 0.4s"></span>
            </span>
          </p>
        </div>
      </div>

      <div class="flex items-center space-x-3 relative">
        <!-- AI 实时状态 -->
        <div v-if="isStreaming || streamStatus" class="flex items-center space-x-2 px-4 py-2 bg-emerald-950/5 border border-emerald-200/50 rounded-xl transition-all duration-500">
          <span v-if="isStreaming" class="w-2 h-2 rounded-full bg-secondary animate-pulse shadow-[0_0_8px_secondary]"></span>
          <span class="text-[11px] font-bold text-emerald-800 uppercase tracking-widest">{{ streamStatus }}</span>
        </div>
        
        <div v-if="streamError" class="flex items-center space-x-2 px-4 py-2 bg-red-50 border border-red-200 rounded-xl">
           <span class="material-symbols-outlined text-red-500 text-base">error_outline</span>
           <span class="text-[11px] font-bold text-red-600">{{ streamError }}</span>
        </div>

        <!-- 功能按钮 -->
        <button
          v-if="isStreaming && !isSkipping"
          @click="skipAnimation"
          class="flex items-center space-x-2 px-5 py-3 bg-amber-500 text-white rounded-xl text-[12px] font-bold uppercase tracking-widest hover:bg-amber-600 transition-all shadow-md shadow-amber-500/20"
        >
          <span class="material-symbols-outlined text-lg">fast_forward</span>
          <span>加速加载</span>
        </button>

        <button
          @click="triggerNew"
          :disabled="triggering"
          class="flex items-center space-x-2 px-6 py-3 bg-emerald-950 text-white rounded-xl text-[13px] font-bold uppercase tracking-widest hover:-translate-y-0.5 hover:shadow-xl transition-all disabled:opacity-50"
        >
          <span :class="cn('material-symbols-outlined text-lg', triggering && 'animate-spin')">smart_toy</span>
          <span>{{ triggering ? 'AI 正在执行扫描...' : '启动智能诊断' }}</span>
        </button>
      </div>
    </div>

    <!-- 主体内容区 -->
    <div class="flex-1 flex space-x-6 min-h-0">
      <!-- 历史列表 -->
      <div class="w-72 flex flex-col bg-white/80 backdrop-blur-md rounded-2xl border border-emerald-200 shadow-sm min-h-0 overflow-hidden shrink-0">
        <div class="p-4 border-b border-emerald-100 flex items-center justify-between bg-emerald-50/50">
          <span class="text-[10px] font-bold text-emerald-900/40 uppercase tracking-widest">历史报告归档</span>
          <span class="material-symbols-outlined text-emerald-900/40 text-[18px]">history</span>
        </div>

        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <div v-if="loading" class="p-12 flex justify-center">
            <span class="material-symbols-outlined text-4xl animate-spin text-emerald-200">progress_activity</span>
          </div>
          <div
            v-for="item in history"
            :key="item.id"
            @click="handleSelect(item)"
            class="p-4 border-b border-emerald-50 cursor-pointer transition-all hover:bg-emerald-50 group relative"
            :class="selectedBriefing?.id === item.id ? 'bg-emerald-50/80 shadow-inner' : ''"
          >
            <div v-if="selectedBriefing?.id === item.id" class="absolute left-0 top-0 bottom-0 w-1 bg-emerald-600"></div>
            <div class="flex justify-between items-center mb-1">
              <span class="text-[14px] font-bold font-headline text-emerald-900">
                {{ item.briefingDate }}
              </span>
              <span class="material-symbols-outlined text-[16px] text-emerald-200 group-hover:text-emerald-500 transition-colors">description</span>
            </div>
            <p class="text-[11px] text-emerald-900/60 line-clamp-1 leading-relaxed">{{ item.summary || '智能简报' }}</p>
          </div>
        </div>
      </div>

      <!-- 中心展示区 -->
      <div class="flex-1 flex space-x-6 min-h-0 overflow-hidden">
          <!-- 简报正文 -->
          <div class="flex-1 bg-white/95 backdrop-blur-md rounded-2xl border border-emerald-200 shadow-sm flex flex-col min-h-0 overflow-hidden group">
            <div class="p-5 border-b border-emerald-100 flex items-center justify-between bg-emerald-50/30">
               <div class="flex items-center space-x-3">
                  <div class="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                  <h3 class="text-sm font-headline font-bold text-emerald-950 uppercase tracking-wider">
                     {{ selectedBriefing?.briefingDate || '---' }} 报告详情
                  </h3>
               </div>
               <div class="flex items-center space-x-2">
                  <button class="p-2 text-emerald-400 hover:text-emerald-600 hover:bg-emerald-50 rounded-lg transition-all" title="导出数据">
                    <span class="material-symbols-outlined text-xl">share</span>
                  </button>
               </div>
            </div>

            <div class="flex-1 overflow-y-auto p-10 prose prose-emerald max-w-none prose-sm custom-scrollbar relative">
               <!-- [New] AI 思维状态灯 -->
               <div v-if="isStreaming" class="flex items-center space-x-2 py-2 px-3 bg-emerald-50 border border-emerald-100 rounded-lg absolute top-4 right-4 z-10 animate-pulse shadow-sm">
                  <div class="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)]"></div>
                  <span class="text-[10px] font-bold text-emerald-900/60 uppercase tracking-widest leading-none">AI Agent Active</span>
               </div>

               <div v-if="isStreaming || selectedBriefing?.content" class="relative z-0">
                  <div class="markdown-body" v-html="marked(isStreaming ? bufferedContent : (selectedBriefing?.content || ''))"></div>
                  <span v-if="isStreaming && !isSkipping" class="inline-block w-1 h-5 bg-secondary animate-pulse ml-1 align-bottom shadow-[0_0_8px_secondary]"></span>
               </div>
               <div v-else class="h-full flex flex-col items-center justify-center opacity-40">
                  <span class="material-symbols-outlined text-7xl text-emerald-100 mb-4 animate-float">analytics</span>
                  <p class="text-sm font-headline font-bold text-emerald-950 tracking-[0.2em] uppercase">等待分析指令</p>
               </div>
            </div>
          </div>

          <!-- 思维链推理台 -->
          <div 
             :class="cn(
                'w-80 flex flex-col bg-[#0a1a15] rounded-2xl border border-emerald-900/30 shadow-2xl transition-all duration-700 overflow-hidden shrink-0 transform',
                isStreaming || displayTraceLogs.length > 0 ? 'translate-x-0' : 'translate-x-[110%] opacity-0 pointer-events-none'
             )"
          >
            <div class="p-4 border-b border-emerald-900/50 flex items-center justify-between bg-emerald-950/50">
                <div class="flex items-center space-x-2">
                    <span :class="cn('material-symbols-outlined text-sm', isStreaming ? 'text-emerald-400 animate-spin-slow' : 'text-emerald-800')">cognition</span>
                    <span class="text-[10px] font-bold text-emerald-400 uppercase tracking-[0.2em]">Live Reasoning Trace</span>
                </div>
                <div class="flex space-x-1">
                    <div class="w-2 h-2 rounded-full bg-red-400/20"></div>
                    <div class="w-2 h-2 rounded-full bg-amber-400/20"></div>
                    <div class="w-2 h-2 rounded-full bg-emerald-400/20"></div>
                </div>
            </div>

            <div class="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar-dark scroll-smooth" id="trace-container">
                <TransitionGroup name="trace-list">
                    <div 
                        v-for="log in displayTraceLogs" 
                        :key="log.id"
                        class="relative pl-6 pb-4 border-l border-emerald-900/30 last:border-0"
                    >
                        <div class="absolute -left-[5px] top-0 w-2.5 h-2.5 rounded-full bg-emerald-500 border-2 border-[#0a1a15] shadow-[0_0_8px_rgba(16,185,129,0.5)]"></div>
                        <div class="flex flex-col space-y-1">
                            <div class="flex justify-between items-center bg-emerald-900/10 px-2 py-1 rounded border border-emerald-800/20">
                                <span class="text-[9px] font-bold text-emerald-500 uppercase tracking-tighter">{{ log.timestamp }}</span>
                                <span :class="cn(
                                    'text-[8px] font-bold uppercase py-0.5 px-1.5 rounded-full',
                                    log.status === 'success' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-blue-500/20 text-blue-400'
                                )">{{ log.status }}</span>
                            </div>
                            <p class="text-[11px] leading-relaxed text-emerald-100/90 font-mono tracking-tight">{{ log.message }}</p>
                        </div>
                    </div>
                </TransitionGroup>
                
                <div v-if="isStreaming" class="flex items-center space-x-3 text-emerald-500/40 p-2 animate-pulse">
                    <span class="material-symbols-outlined text-sm">psychology</span>
                    <span class="text-[10px] uppercase font-bold tracking-[0.3em]">Processing next token...</span>
                </div>
            </div>
          </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Markdown 样式增强 */
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  @apply font-headline font-bold text-emerald-950 border-b-0 pb-0 mt-8 mb-4;
}
.markdown-body :deep(h2) {
  @apply text-xl border-l-[6px] border-emerald-600 pl-4 bg-emerald-50/50 py-2 rounded-r-lg;
}
.markdown-body :deep(strong) {
  @apply text-emerald-800 bg-emerald-100/50 px-1.5 py-0.5 rounded font-bold;
}
.markdown-body :deep(blockquote) {
  @apply bg-emerald-50/30 border-l-[4px] border-emerald-300 py-4 px-6 italic text-emerald-900/70 text-sm rounded-r-xl my-6;
}

/* 轨道滚动条 */
.custom-scrollbar::-webkit-scrollbar { width: 4px; background-color: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background-color: rgba(16, 185, 129, 0.2); border-radius: 99px; }

.custom-scrollbar-dark::-webkit-scrollbar { width: 3px; background-color: transparent; }
.custom-scrollbar-dark::-webkit-scrollbar-thumb { background-color: rgba(16, 185, 129, 0.3); border-radius: 99px; }

/* 思维链动画 */
.trace-list-enter-active,
.trace-list-leave-active {
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.trace-list-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
.animate-float { animation: float 4s ease-in-out infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
.animate-spin-slow { animation: spin 8s linear infinite; }
</style>

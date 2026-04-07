<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { apiService, type BriefingStreamEvent } from '../api';
import { marked } from 'marked';
import { cn } from '../utils';

const history = ref<any[]>([]);
const selectedBriefing = ref<any>(null);
const loading = ref(false);
const triggering = ref(false);

// 流式简报状态
const streamStatus = ref('');
const streamContent = ref('');
const streamError = ref('');
const isStreaming = ref(false);

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
  // 切换历史列表时，如果正在流式生成，不打断
  if (!isStreaming.value) {
    selectedBriefing.value = item;
    streamContent.value = '';
    streamStatus.value = '';
    streamError.value = '';
  } else {
    selectedBriefing.value = item;
  }
};

/**
 * 点击"手动触发今日扫描"：
 * 1. 用流式接口直连 AI-service，实时打字机推送简报内容
 * 2. 流式完成后，再调 triggerBriefing 让 Java 后端入库
 * 3. 刷新历史列表
 */
const triggerNew = async () => {
  if (triggering.value) return;
  triggering.value = true;
  isStreaming.value = true;
  streamContent.value = '';
  streamStatus.value = '正在连接 AI 简报引擎...';
  streamError.value = '';

  // 临时占位展示流式内容
  selectedBriefing.value = { briefingDate: new Date().toISOString().split('T')[0], content: '' };

  try {
    await apiService.streamBriefing((event: BriefingStreamEvent) => {
      if (event.event === 'status') {
        streamStatus.value = event.data?.message || '';
      } else if (event.event === 'chunk') {
        streamContent.value += event.data?.text || '';
        // 实时同步到 selectedBriefing.content 供预览
        selectedBriefing.value = {
          ...selectedBriefing.value,
          content: streamContent.value,
        };
      } else if (event.event === 'done') {
        streamStatus.value = '简报生成完成';
        isStreaming.value = false;
      } else if (event.event === 'error') {
        streamError.value = event.data?.detail || event.data?.message || '简报生成失败';
        isStreaming.value = false;
      }
    });
  } catch (e: any) {
    console.error('流式简报异常:', e);
    streamError.value = e.message || '连接 AI 服务失败';
    isStreaming.value = false;
  }

  // 流式完成后，异步让 Java 后端入库（不阻塞 UI）
  try {
    await apiService.triggerBriefing();
  } catch (e) {
    console.warn('简报入库失败（不影响展示）:', e);
  }

  // 刷新历史列表，把刚生成的简报加入左侧
  await loadHistory();

  triggering.value = false;
};

onMounted(() => {
  loadHistory();
});
</script>

<template>
  <div class="h-full flex flex-col space-y-6">
    <!-- 顶部标题区 -->
    <div class="flex items-center justify-between bg-white/95 backdrop-blur-md p-6 rounded-2xl border border-emerald-200 shadow-sm">
      <div class="flex items-center space-x-6">
        <div class="w-14 h-14 bg-gradient-to-br from-emerald-400 to-secondary rounded-xl flex items-center justify-center shadow-lg shadow-secondary/20">
          <span class="material-symbols-outlined text-white text-3xl">description</span>
        </div>
        <div>
          <h2 class="text-2xl font-headline font-bold text-emerald-950 tracking-tight">每日诊断简报</h2>
          <p class="text-xs text-emerald-900/60 font-inter font-bold uppercase tracking-[0.2em] mt-1">
            Daily Intelligent Briefing
          </p>
        </div>
      </div>

      <div class="flex items-center space-x-3">
        <!-- 流式状态气泡 -->
        <div v-if="isStreaming || streamStatus" class="flex items-center space-x-2 px-4 py-2 bg-emerald-50 border border-emerald-200 rounded-xl">
          <span v-if="isStreaming" class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse inline-block"></span>
          <span class="text-xs font-bold text-emerald-700 uppercase tracking-widest">{{ streamStatus }}</span>
        </div>
        <div v-if="streamError" class="flex items-center space-x-2 px-4 py-2 bg-red-50 border border-red-200 rounded-xl">
          <span class="material-symbols-outlined text-red-500 text-base">error_outline</span>
          <span class="text-xs font-bold text-red-600">{{ streamError }}</span>
        </div>
        <button
          @click="triggerNew"
          :disabled="triggering"
          class="flex items-center space-x-2 px-6 py-3 bg-emerald-950 text-white rounded-xl text-[13px] font-bold uppercase tracking-widest hover:-translate-y-0.5 hover:shadow-lg transition-all disabled:opacity-50 disabled:hover:translate-y-0 disabled:shadow-none"
        >
          <span :class="cn('material-symbols-outlined text-lg', triggering && 'animate-spin')">refresh</span>
          <span>{{ triggering ? (isStreaming ? 'AI 正在生成简报...' : '正在入库...') : '手动触发今日扫描' }}</span>
        </button>
      </div>
    </div>

    <!-- 主体内容区 -->
    <div class="flex-1 flex space-x-6 min-h-0">
      <!-- 左侧：历史列表 -->
      <div class="w-80 flex flex-col bg-white/90 backdrop-blur-md rounded-2xl border border-emerald-200 shadow-sm min-h-0 overflow-hidden">
        <div class="p-5 border-b border-emerald-100 flex items-center justify-between bg-surface-container-low">
          <span class="text-[10px] font-bold text-emerald-900/40 uppercase tracking-widest">历史告警报告</span>
          <span class="material-symbols-outlined text-emerald-900/40 text-[18px]">calendar_month</span>
        </div>

        <div class="flex-1 overflow-y-auto">
          <div v-if="loading" class="p-12 flex justify-center">
            <span class="material-symbols-outlined text-4xl animate-spin text-emerald-200">progress_activity</span>
          </div>
          <div v-else-if="history.length === 0" class="p-12 text-center flex flex-col items-center">
            <span class="material-symbols-outlined text-5xl text-emerald-100 mb-3">error_outline</span>
            <p class="text-sm font-bold text-emerald-900/40 uppercase tracking-widest">暂无简报记录</p>
          </div>
          <div
            v-for="item in history"
            :key="item.id"
            @click="handleSelect(item)"
            :class="cn(
              'p-5 border-b border-emerald-50 cursor-pointer transition-all hover:bg-emerald-50 group relative',
              selectedBriefing?.id === item.id ? 'bg-surface-bright/80' : ''
            )"
          >
            <div v-if="selectedBriefing?.id === item.id" class="absolute left-0 top-0 bottom-0 w-1.5 bg-secondary"></div>
            <div class="flex justify-between items-center mb-2">
              <span :class="cn('text-[15px] font-bold font-headline', selectedBriefing?.id === item.id ? 'text-secondary' : 'text-emerald-900')">
                {{ item.briefingDate }}
              </span>
              <span class="material-symbols-outlined text-[16px] text-emerald-200 group-hover:translate-x-1 transition-transform group-hover:text-secondary">chevron_right</span>
            </div>
            <p class="text-xs text-emerald-900/60 font-inter line-clamp-2 leading-relaxed">
              {{ item.summary || '智能分析已生成，点击查看详细诊断说明...' }}
            </p>
          </div>
        </div>
      </div>

      <!-- 右侧：报告展示 -->
      <div class="flex-1 bg-white/95 backdrop-blur-md rounded-2xl border border-emerald-200 shadow-sm flex flex-col min-h-0 overflow-hidden">

        <!-- 正在流式生成中的实时预览 -->
        <div v-if="isStreaming && streamContent" class="flex-1 flex flex-col min-h-0">
          <div class="p-6 border-b border-emerald-100 flex items-center justify-between bg-surface-container-low">
            <div class="flex items-center space-x-4">
              <span class="px-3 py-1 bg-amber-400 text-white text-[10px] font-bold uppercase tracking-[0.2em] rounded-md animate-pulse">Generating</span>
              <h3 class="text-xl font-headline font-bold text-emerald-950">
                {{ new Date().toISOString().split('T')[0] }} 场内行为分析简报
              </h3>
            </div>
            <span class="text-[11px] text-emerald-900/40 font-bold uppercase tracking-widest flex items-center">
              <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse mr-2 inline-block"></span>
              {{ streamStatus }}
            </span>
          </div>
          <div class="flex-1 overflow-y-auto p-10 prose prose-emerald max-w-none prose-sm custom-scrollbar">
            <div class="markdown-body" v-html="marked(streamContent || '')"></div>
            <!-- 打字机光标 -->
            <span class="inline-block w-0.5 h-5 bg-emerald-500 animate-pulse ml-0.5 align-middle"></span>
          </div>
        </div>

        <!-- 历史简报查看 -->
        <div v-else-if="selectedBriefing && !isStreaming" class="flex-1 flex flex-col min-h-0">
          <div class="p-6 border-b border-emerald-100 flex items-center justify-between bg-surface-container-low">
            <div class="flex items-center space-x-4">
              <span class="px-3 py-1 bg-secondary text-white text-[10px] font-bold uppercase tracking-[0.2em] rounded-md">Report Active</span>
              <h3 class="text-xl font-headline font-bold text-emerald-950">{{ selectedBriefing.briefingDate }} 场内行为分析简报</h3>
            </div>
            <button class="flex items-center space-x-2 px-4 py-2 bg-white border border-emerald-200 rounded-lg text-xs font-bold text-emerald-900/60 hover:text-secondary hover:border-secondary transition-colors">
              <span class="material-symbols-outlined text-[16px]">download</span>
              <span class="uppercase tracking-widest">导出 PDF</span>
            </button>
          </div>

          <!-- Markdown 阅读区 -->
          <div class="flex-1 overflow-y-auto p-10 prose prose-emerald max-w-none prose-sm custom-scrollbar">
            <div class="markdown-body" v-html="marked(selectedBriefing.content || '')"></div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-else class="flex-1 flex flex-col items-center justify-center bg-surface-bright/30">
          <span class="material-symbols-outlined text-[80px] text-emerald-100 mb-6 drop-shadow-sm">description</span>
          <p class="text-emerald-900/40 text-[15px] font-headline font-bold uppercase tracking-widest">请从左侧选择一个日期查看智能简报</p>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  @apply font-headline font-bold text-emerald-950 border-b-0 pb-0 mt-8 mb-4;
}

.markdown-body :deep(h1) {
  @apply text-3xl mb-8 border-b border-emerald-100 pb-4;
}

.markdown-body :deep(h2) {
  @apply text-xl border-l-[6px] border-secondary pl-4 bg-emerald-50/50 py-2 rounded-r-lg;
}

.markdown-body :deep(strong) {
  @apply text-emerald-800 bg-emerald-100/50 px-1.5 py-0.5 rounded font-bold;
}

.markdown-body :deep(ul) {
  @apply space-y-3 pl-6 marker:text-secondary;
}

.markdown-body :deep(li) {
  @apply text-emerald-900 flex-1 font-inter;
}

.markdown-body :deep(blockquote) {
  @apply bg-surface-container-low border-l-[6px] border-emerald-300 py-3 px-6 italic text-emerald-900/70 text-sm rounded-r-xl shadow-sm my-6;
}

.custom-scrollbar::-webkit-scrollbar {
  width: 8px;
  background-color: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(16, 185, 129, 0.2);
  border-radius: 99px;
  border: 2px solid #fff;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgba(16, 185, 129, 0.4);
}
</style>

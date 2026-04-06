<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { apiService } from '../api';
import { Calendar, FileText, RefreshCw, AlertCircle, ChevronRight, Download } from 'lucide-vue-next';
import { marked } from 'marked';
import { cn } from '../utils';

const history = ref<any[]>([]);
const selectedBriefing = ref<any>(null);
const loading = ref(false);
const triggering = ref(false);

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
  selectedBriefing.value = item;
};

const triggerNew = async () => {
  if (triggering.value) return;
  triggering.value = true;
  try {
    console.log('开始触发简报生成...');
    const res = await apiService.triggerBriefing();
    console.log('简报生成响应:', res);
    if (res) {
      await loadHistory();
      // 确保选中的简报有content字段
      if (res.content) {
        selectedBriefing.value = res;
      } else {
        // 如果返回的数据没有content，尝试从历史记录中找到
        const latest = history.value.find(item => item.id === res.id);
        selectedBriefing.value = latest || res;
      }
      console.log('简报生成成功，已更新列表');
    } else {
      console.warn('简报生成返回空数据');
      alert('简报生成失败：返回数据为空');
    }
  } catch (e: any) {
    console.error('简报生成异常:', e);
    if (e.code === 'ECONNABORTED' || e.message?.includes('timeout')) {
      alert('简报生成超时，请稍后重试。AI 服务可能正在处理大量数据。');
    } else {
      const errorMsg = e.message || e.data?.message || '未知错误';
      alert(`触发简报生成失败：${errorMsg}\n请检查后端服务状态`);
    }
  } finally {
    triggering.value = false;
  }
};

onMounted(() => {
  loadHistory();
});
</script>

<template>
  <div class="h-full flex flex-col space-y-6">
    <!-- 顶部标题区 -->
    <div class="flex items-center justify-between bg-white p-6 border border-slate-200 shadow-sm">
      <div class="flex items-center space-x-4">
        <div class="p-3 bg-blue-600">
          <FileText class="w-6 h-6 text-white" />
        </div>
        <div>
          <h2 class="text-xl font-bold text-slate-900">每日诊断简报</h2>
          <p class="text-xs text-slate-500 font-mono italic">DAILY INTELLIGENT BRIEFING & ANOMALY DETECTION</p>
        </div>
      </div>
      
      <div class="flex items-center space-x-3">
        <button 
          @click="triggerNew"
          :disabled="triggering"
          class="flex items-center space-x-2 px-4 py-2 bg-slate-900 text-white text-xs font-bold hover:bg-black transition-all disabled:opacity-50"
        >
          <RefreshCw :class="cn('w-4 h-4', triggering && 'animate-spin')" />
          <span>{{ triggering ? '正在生成智能简报...' : '手动触发今日简报' }}</span>
        </button>
      </div>
    </div>

    <!-- 主体内容区 -->
    <div class="flex-1 flex space-x-6 min-h-0">
      <!-- 左侧：历史列表 -->
      <div class="w-80 flex flex-col bg-white border border-slate-200 shadow-sm min-h-0">
        <div class="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50">
          <span class="text-[10px] font-bold text-slate-400 uppercase tracking-widest">历史报告记录</span>
          <Calendar class="w-3.5 h-3.5 text-slate-400" />
        </div>
        
        <div class="flex-1 overflow-y-auto">
          <div v-if="loading" class="p-8 text-center">
            <RefreshCw class="w-6 h-6 animate-spin text-slate-300 mx-auto" />
          </div>
          <div v-else-if="history.length === 0" class="p-8 text-center">
            <AlertCircle class="w-8 h-8 text-slate-200 mx-auto mb-2" />
            <p class="text-xs text-slate-400">暂无简报记录</p>
          </div>
          <div 
            v-for="item in history" 
            :key="item.id"
            @click="handleSelect(item)"
            :class="cn(
              'p-4 border-b border-slate-50 cursor-pointer transition-all hover:bg-slate-50 group relative',
              selectedBriefing?.id === item.id ? 'bg-blue-50/50' : ''
            )"
          >
            <div v-if="selectedBriefing?.id === item.id" class="absolute left-0 top-0 bottom-0 w-1 bg-blue-600"></div>
            <div class="flex justify-between items-start mb-1">
              <span :class="cn('text-sm font-bold', selectedBriefing?.id === item.id ? 'text-blue-700' : 'text-slate-700')">
                {{ item.briefingDate }}
              </span>
              <ChevronRight class="w-3 h-3 text-slate-300 group-hover:translate-x-1 transition-transform" />
            </div>
            <p class="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
              {{ item.summary || '点击查看详情...' }}
            </p>
          </div>
        </div>
      </div>

      <!-- 右侧：报告展示 -->
      <div class="flex-1 bg-white border border-slate-200 shadow-sm flex flex-col min-h-0">
        <div v-if="selectedBriefing" class="flex-1 flex flex-col min-h-0">
          <div class="p-6 border-b border-slate-100 flex items-center justify-between">
            <div class="flex items-center space-x-3">
              <span class="px-2 py-0.5 bg-blue-100 text-blue-700 text-[10px] font-bold uppercase tracking-tighter">Report Active</span>
              <h3 class="text-lg font-bold text-slate-800">{{ selectedBriefing.briefingDate }} 场内行为分析简报</h3>
            </div>
            <button class="flex items-center space-x-2 text-xs text-slate-400 hover:text-slate-600">
              <Download class="w-4 h-4" />
              <span>导出 PDF</span>
            </button>
          </div>
          
          <div class="flex-1 overflow-y-auto p-10 prose prose-slate max-w-none prose-sm">
            <div class="markdown-body" v-html="marked(selectedBriefing.content || '')"></div>
          </div>
        </div>

        <div v-else class="flex-1 flex flex-center items-center justify-center bg-slate-50/30">
          <div class="text-center">
            <FileText class="w-16 h-16 text-slate-100 mx-auto mb-4" />
            <p class="text-slate-400 text-sm">请从左侧选择一个日期查看智能简报</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.markdown-body :deep(h1), 
.markdown-body :deep(h2), 
.markdown-body :deep(h3) {
  @apply font-bold text-slate-900 border-b-0 pb-0 mt-8 mb-4;
}

.markdown-body :deep(h2) {
  @apply text-lg border-l-4 border-blue-600 pl-3;
}

.markdown-body :deep(strong) {
  @apply text-blue-700 bg-blue-50 px-1;
}

.markdown-body :deep(ul) {
  @apply space-y-2;
}

.markdown-body :deep(li) {
  @apply text-slate-600;
}

.markdown-body :deep(blockquote) {
  @apply bg-slate-50 border-l-4 border-slate-300 py-2 px-4 italic text-slate-500 text-xs;
}
</style>

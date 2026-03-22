<script setup lang="ts">
/**
 * 生长追踪与预测 (GrowthCurve) 视图组件
 * =====================================
 * 本组件是系统的核心决策辅助模块，负责展示生猪的历史生长记录与 AI 预测轨迹。
 * 
 * 核心技术栈：
 * 1. ECharts: 用于渲染复杂的多阶段生长拟合曲线。
 * 2. SSE Stream: 利用异步迭代器实时渲染来自后端的 AI 研判碎片。
 * 3. 实时 Markdown 解析：内置简易 MD 渲染引擎，将学术性的研判文本转化为格式化的临床报告。
 * 4. 响应式布局：图表与列表在不同屏幕尺寸下均能保持最佳视口。
 */

import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import * as echarts from 'echarts';
import { ChevronLeft, TrendingUp, AlertCircle, RefreshCw, Calendar, Activity, Scale } from 'lucide-vue-next';
import { apiService, type InspectionStreamEvent } from '../api';

// --- 类型定义 ---
interface PigInfo {
  pigId: string;
  breed: string;
  area: string;
  current_weight_kg: number;
  current_month: number;
}

interface CurvePoint {
  month: number;
  weight: number;
  status: string;
}

// --- 状态管理 ---
const isLoadingPigs = ref(true);
const pigsList = ref<PigInfo[]>([]);
const errorMsg = ref('');

const selectedPig = ref<PigInfo | null>(null);
const isGeneratingReport = ref(false);
const streamStatus = ref('');   // 实时状态描述（如：正在运行数值轨...）
const reportContent = ref('');  // 累积的 Markdown 文本内容
const reportError = ref('');

// ECharts 实例句柄
const chartRef = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

// --- 生命周期与初始化 ---
onMounted(async () => {
  await loadPigs();
  window.addEventListener('resize', resizeChart);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart);
  chart?.dispose();
  chart = null;
});

/** 加载全场生猪简档列表 */
const loadPigs = async () => {
  isLoadingPigs.value = true;
  errorMsg.value = '';
  try {
    const res = await apiService.getPigsList();
    if (res && res.code === 200) {
      pigsList.value = res.data;
    } else {
      errorMsg.value = res?.message || '加载猪只列表失败';
    }
  } catch (e: any) {
    errorMsg.value = e.message || '网络连接异常';
  } finally {
    isLoadingPigs.value = false;
  }
};

/** 
 * 处理来自 SSE 流的原子事件 
 * 将离散的后端事件流转译为本地响应式状态。
 */
const handleStreamEvent = (event: InspectionStreamEvent) => {
  if (event.event === 'status') {
    streamStatus.value = event.data?.message || '正在生成报告...';
    return;
  }
  if (event.event === 'chunk') {
    // 逐碎片拼接文本，实现打字机效果
    reportContent.value += event.data?.text || '';
    return;
  }
  if (event.event === 'error') {
    reportError.value = event.data?.detail || event.data?.message || '流式生成失败';
    return;
  }
  if (event.event === 'done') {
    streamStatus.value = event.data?.message || '报告生成完成';
  }
};

/** 开启单猪研判流程 */
const viewGrowthCurve = async (pig: PigInfo) => {
  selectedPig.value = pig;
  isGeneratingReport.value = true;
  streamStatus.value = '准备计算预测路径...';
  reportContent.value = '';
  reportError.value = '';

  try {
    // 尝试启动流式传输（优先方案，体验更好）
    await apiService.streamPigInspectionReport(pig.pigId, handleStreamEvent);
  } catch (e: any) {
    // 如果 SSE 失败，尝试传统的单次 HTTP 请求作为兜底 (Fallback)
    try {
      const res = await apiService.generatePigInspectionReport(pig.pigId);
      if (res && res.code === 200) {
        reportContent.value = res.report || '暂无报告内容';
      } else {
        reportError.value = res?.detail || res?.message || '生成报告失败';
      }
    } catch (fallbackErr: any) {
      reportError.value = fallbackErr?.message || e?.message || '请求后端服务器失败';
    }
  } finally {
    isGeneratingReport.value = false;
  }
};

const backToList = () => {
  selectedPig.value = null;
  streamStatus.value = '';
  reportContent.value = '';
  reportError.value = '';
};

// --- 计算属性：解析 Markdown 中的表格数据用于绘图 ---
/**
 * 这是一个巧妙的设计：
 * 由于 AI 报告中包含 Markdown 表格形式的生长预测，
 * 我们通过正则提取这些文本数据，将其转化为图表所需的结构化数组。
 */
const curvePoints = computed<CurvePoint[]>(() => {
  const lines = (reportContent.value || '').replace(/\r/g, '').split('\n');
  const points: CurvePoint[] = [];

  for (const raw of lines) {
    const line = raw.trim();
    if (!line.startsWith('|')) continue;
    if (line.includes('月份') || line.includes('---')) continue;

    const cols = line
      .split('|')
      .map((c) => c.trim())
      .filter((c) => c.length > 0);

    if (cols.length < 3) continue;
    const month = Number(cols[0]);
    const weight = Number(cols[1]);
    const status = cols[2];

    if (Number.isFinite(month) && Number.isFinite(weight)) {
      points.push({ month, weight, status });
    }
  }

  return points.sort((a, b) => a.month - b.month);
});

/** 统计预测结论概览 */
const predictionStats = computed(() => {
  if (!curvePoints.value.length) return null;
  const first = curvePoints.value[0];
  const last = curvePoints.value[curvePoints.value.length - 1];
  const gain = (last.weight - first.weight).toFixed(1);
  const duration = last.month - first.month;
  return {
    startMonth: first.month,
    endMonth: last.month,
    startWeight: first.weight,
    endWeight: last.weight,
    gain,
    duration
  };
});

// --- Markdown 渲染引擎 (极简版实现) ---
const escapeHtml = (text: string) =>
  text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;').replaceAll("'", '&#39;');

const renderInline = (line: string) =>
  line.replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-mono text-sm border border-indigo-100">$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-slate-800">$1</strong>')
      .replace(/\*([^*]+)\*/g, '<em class="text-slate-700 italic">$1</em>');

const markdownToHtml = (markdown: string) => {
  const lines = escapeHtml(markdown || '').split('\n');
  const html: string[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i].trim();
    if (!line) { i += 1; continue; }

    // 处理各级标题
    if (line.startsWith('### ')) {
      html.push(`<h3 class="text-base font-bold text-slate-800 mt-6 mb-3 flex items-center before:content-[''] before:w-1 before:h-4 before:bg-indigo-400 before:mr-2 before:rounded-full">${renderInline(line.slice(4))}</h3>`);
      i += 1; continue;
    }
    if (line.startsWith('## ')) {
      html.push(`<h2 class="text-lg font-bold text-slate-800 mt-8 mb-4 border-b border-slate-100 pb-2">${renderInline(line.slice(3))}</h2>`);
      i += 1; continue;
    }
    // 处理引用块
    if (line.startsWith('> ')) {
      html.push(`<blockquote class="border-l-4 border-indigo-500 bg-indigo-50/50 p-4 rounded-r-lg my-4 text-slate-700 italic">${renderInline(line.slice(2))}</blockquote>`);
      i += 1; continue;
    }
    // 处理无序列表
    if (line.startsWith('- ')) {
      const items: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('- ')) {
        items.push(`<li class="mb-2 relative pl-1"><span class="absolute left-[-1.25rem] top-[0.4rem] w-1.5 h-1.5 rounded-full bg-slate-400"></span>${renderInline(lines[i].trim().slice(2))}</li>`);
        i += 1;
      }
      html.push(`<ul class="pl-6 text-slate-600 my-4 space-y-1">${items.join('')}</ul>`);
      continue;
    }
    // 处理 Markdown 表格（忽略，因为我们已经通过 curvePoints 在 ECharts 中渲染了）
    if (line.startsWith('|')) { i += 1; continue; }

    html.push(`<p class="text-slate-600 leading-relaxed my-3">${renderInline(line)}</p>`);
    i += 1;
  }
  return html.join('');
};

const reportHtml = computed(() => markdownToHtml(reportContent.value));

// --- 图表渲染引擎 (ECharts) ---
const renderChart = () => {
  if (!chartRef.value) return;
  
  let chartInstance = echarts.getInstanceByDom(chartRef.value);
  if (!chartInstance) chartInstance = echarts.init(chartRef.value);

  const data = curvePoints.value;
  chartInstance.setOption({
    animation: true,
    animationDuration: 1200,
    grid: { top: 30, right: 30, bottom: 30, left: 50 },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.9)',
      padding: [10, 16],
      formatter: (params: any) => {
        const p = params[0];
        const pointData = data[p.dataIndex];
        return `
          <div class="font-bold text-slate-800 mb-2 border-b border-slate-100 pb-1">第 ${pointData.month} 月</div>
          <div class="flex items-center justify-between gap-4 mb-1">
            <span class="text-slate-500 text-sm">预测体重</span>
            <span class="font-semibold text-indigo-600">${pointData.weight} kg</span>
          </div>
          <div class="flex items-center justify-between gap-4">
            <span class="text-slate-500 text-sm">状态</span>
            <span class="text-slate-700 text-sm">${pointData.status}</span>
          </div>`;
      }
    },
    xAxis: {
      type: 'category',
      data: data.map((d) => `${d.month}月`),
      axisLabel: { color: '#64748b', fontFamily: 'monospace' },
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b', formatter: '{value} kg' },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } }
    },
    series: [
      {
        type: 'line',
        smooth: 0.4,
        data: data.map((d) => d.weight),
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { 
          width: 4, 
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: '#6366f1' },
            { offset: 1, color: '#a855f7' }
          ])
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(99, 102, 241, 0.25)' },
            { offset: 1, color: 'rgba(255, 255, 255, 0)' }
          ])
        }
      }
    ]
  });
};

const resizeChart = () => chart?.resize();
// 监听到数据点变化或容器显示时，即刻刷新图表
watch(curvePoints, () => setTimeout(renderChart, 0));
watch(chartRef, () => setTimeout(renderChart, 0));
</script>

<template>
  <div class="h-full flex flex-col space-y-6 animate-fade-in">
    <!-- 顶部导航与操作栏 -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <button
          v-if="selectedPig"
          @click="backToList"
          class="p-2.5 bg-white border border-slate-200 hover:border-indigo-300 hover:text-indigo-600 rounded-xl transition-all shadow-sm text-slate-500 group"
        >
          <ChevronLeft class="w-5 h-5 group-hover:-translate-x-0.5 transition-transform" />
        </button>
        <div>
          <h1 class="text-2xl font-bold text-slate-800 tracking-tight flex items-center">
            <TrendingUp class="w-7 h-7 mr-3 text-indigo-600 p-1 bg-indigo-50 rounded-lg" />
            {{ selectedPig ? `预测分析：${selectedPig.pigId}` : '成长追踪与预测' }}
          </h1>
          <p class="text-sm text-slate-500 mt-1 flex items-center">
            <span class="inline-block w-2 h-2 rounded-full mr-2" :class="isGeneratingReport ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'"></span>
            {{ selectedPig ? (isGeneratingReport ? streamStatus : 'AI 生长轨迹预测完成') : 'AI 辅助的关键生长阶段分析系统' }}
          </p>
        </div>
      </div>
      <button v-if="!selectedPig" @click="loadPigs" class="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 text-sm rounded-lg flex items-center shadow-sm transition-colors font-medium">
        <RefreshCw class="w-4 h-4 mr-2" :class="{ 'animate-spin': isLoadingPigs }" /> 刷新数据系统
      </button>
    </div>

    <!-- 主展示区 -->
    <div class="flex-1 overflow-hidden relative" :class="!selectedPig ? 'bg-transparent' : 'bg-slate-50/50 rounded-2xl border border-slate-200/60 p-4 md:p-6 lg:p-8'">
      
      <!-- 视图 1: 猪只简档网格列表 -->
      <div v-if="!selectedPig" class="h-full overflow-y-auto pb-6">
        <div v-if="isLoadingPigs" class="flex flex-col items-center justify-center py-32">
          <div class="relative w-16 h-16"><div class="absolute inset-0 border-4 border-indigo-500 rounded-full border-t-transparent animate-spin"></div></div>
          <p class="text-slate-500 text-sm mt-6 font-medium">云端同步中...</p>
        </div>

        <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          <div
            v-for="pig in pigsList"
            :key="pig.pigId"
            @click="viewGrowthCurve(pig)"
            class="group bg-white border border-slate-200 rounded-2xl p-6 hover:border-indigo-400 hover:shadow-lg transition-all cursor-pointer relative overflow-hidden"
          >
            <div class="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-indigo-500 to-purple-500 transform origin-left scale-x-0 group-hover:scale-x-100 transition-transform duration-300"></div>
            <div class="flex justify-between items-start mb-6">
              <div>
                <span class="inline-flex items-center px-2.5 py-1 rounded-md bg-slate-100/80 border border-slate-200 text-xs font-bold text-slate-700 font-mono mb-3">{{ pig.pigId }}</span>
                <h3 class="text-xl font-bold text-slate-800">{{ pig.breed }}</h3>
              </div>
              <div class="p-2 bg-indigo-50 rounded-xl text-indigo-600"><Activity class="w-5 h-5" /></div>
            </div>
            <div class="grid grid-cols-2 gap-4 mt-auto border-t border-slate-100 pt-5">
              <div class="bg-slate-50 p-3 rounded-xl"><p class="text-2xl font-bold text-slate-800">{{ pig.current_month }}</p></div>
              <div class="bg-indigo-50/50 p-3 rounded-xl"><p class="text-2xl font-bold text-indigo-700">{{ pig.current_weight_kg }}<span class="text-xs font-normal">kg</span></p></div>
            </div>
          </div>
        </div>
      </div>

      <!-- 视图 2: 预测看板（左：图表，右：AI 报告） -->
      <div v-else class="h-full flex flex-col md:flex-row gap-6 lg:gap-8 overflow-hidden">
        
        <!-- 左侧：图表与核心指标 -->
        <div class="w-full md:w-7/12 lg:w-2/3 flex flex-col gap-6 overflow-y-auto pr-2 custom-scrollbar">
          <!-- 统计行 -->
          <div class="grid grid-cols-3 gap-4">
             <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <p class="text-xs text-slate-500 font-bold uppercase">当前体重</p>
                <p class="text-xl font-bold font-mono">{{ selectedPig.current_weight_kg }} <span class="text-sm font-normal">kg</span></p>
             </div>
             <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <p class="text-xs text-slate-500 font-bold uppercase">AI 预测净增</p>
                <p class="text-xl font-bold text-indigo-600 font-mono">{{ predictionStats?.gain || '--' }} <span class="text-sm font-normal">kg</span></p>
             </div>
             <div class="bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
                <p class="text-xs text-slate-500 font-bold uppercase">距离出栏</p>
                <p class="text-xl font-bold text-purple-600 font-mono">{{ predictionStats?.duration || '--' }} <span class="text-sm font-normal">M</span></p>
             </div>
          </div>

          <!-- ECharts 容器 -->
          <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm flex-1 min-h-[400px] relative">
              <div v-if="isGeneratingReport && !curvePoints.length" class="absolute inset-0 z-10 bg-white/80 rounded-2xl flex flex-col items-center justify-center">
                  <div class="w-12 h-12 mb-4 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                  <p class="text-sm font-medium animate-pulse">正在绘制生长路径...</p>
              </div>
              <div ref="chartRef" class="w-full h-full"></div>
          </div>
        </div>

        <!-- 右侧：AI 分析报告流 -->
        <div class="w-full md:w-5/12 lg:w-1/3 bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col overflow-hidden h-full">
          <div class="px-6 py-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
            <h3 class="font-bold text-slate-800 flex items-center"><Activity class="w-4 h-4 mr-2" /> AI 智能研判报告</h3>
            <span v-if="isGeneratingReport" class="text-[10px] font-bold text-indigo-500 animate-pulse">INFERENCE_RUNNING</span>
          </div>
          <div class="flex-1 overflow-y-auto p-6 custom-scrollbar relative">
              <!-- 此处通过 v-html 渲染由 markdownToHtml 实时转化的内容 -->
              <div v-if="reportHtml" class="report-markdown text-sm" v-html="reportHtml"></div>
              <div v-if="isGeneratingReport" class="mt-4 flex space-x-1 pb-8"><span class="w-2 h-2 rounded-full bg-indigo-400 animate-bounce"></span></div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* 滚动条美化 */
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }

/* 基础布局动画 */
.animate-fade-in { animation: fadeIn 0.4s ease-out forwards; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>

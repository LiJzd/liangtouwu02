<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as echarts from 'echarts';
import { Activity, AlertCircle, ChevronLeft, Droplets, RefreshCw, TrendingUp, Utensils, Zap } from 'lucide-vue-next';
import { apiService, type InspectionStreamEvent } from '../api';

// 数据类型定义

interface PigInfo {
  pigId: string;
  breed: string;
  area: string;
  current_weight_kg: number;
  current_month: number;
}

// 历史实测点 (来自 lifecycle)
interface HistoricalPoint {
  month: number;
  weight: number;        // 实测体重
  feedCount: number;     // 喂食次数
  feedDuration: number;  // 喂食时长(min)
  waterCount: number;    // 饮水次数
  waterDuration: number; // 饮水时长(min)
}

// 预测点数据
interface CurvePoint {
  month: number;
  weight: number;
  status: string;
}

// 响应式状态

const isLoadingPigs = ref(true);
const pigsList = ref<PigInfo[]>([]);
const pigsError = ref('');

const selectedPig = ref<PigInfo | null>(null);
const isGeneratingReport = ref(false);
const streamStatus = ref('');
const reportContent = ref('');
const reportError = ref('');

// ECharts 实例及引用
const growthChartRef = ref<HTMLElement | null>(null);
const feedChartRef = ref<HTMLElement | null>(null);
const waterChartRef = ref<HTMLElement | null>(null);
const gainChartRef = ref<HTMLElement | null>(null);
let growthChart: echarts.ECharts | null = null;
let feedChart: echarts.ECharts | null = null;
let waterChart: echarts.ECharts | null = null;
let gainChart: echarts.ECharts | null = null;

// 当前激活的图表Tab
const activeTab = ref<'growth' | 'feed' | 'water' | 'gain'>('growth');

const isCurrentPig = (pigId: string) => selectedPig.value?.pigId === pigId;

// 数据解析逻辑

// 解析 6 列历史表格
const parseHistoricalPoints = (markdown: string): HistoricalPoint[] => {
  const points = new Map<number, HistoricalPoint>();
  const lines = (markdown || '').replace(/\r/g, '').split('\n');

  // 找到 "历史实测数据 (Historical)" 区块
  let inHistoricalSection = false;
  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line.includes('历史实测数据') && line.includes('Historical')) {
      inHistoricalSection = true;
      continue;
    }
    // 防止越界进入预测区块
    if (inHistoricalSection && line.includes('预测生长曲线数据') && line.includes('Monthly')) {
      break;
    }

    if (!inHistoricalSection) continue;
    if (!line.startsWith('|') || line.includes('---')) continue;

    const cells = line
      .split('|')
      .map((cell) => cell.trim())
      .filter(Boolean);

    if (cells.length < 2) continue;

    const month = Number(cells[0].replace(/[^\d]/g, ''));
    const weight = Number(cells[1].replace(/[^\d.]/g, ''));
    if (!Number.isFinite(month) || month <= 0 || !Number.isFinite(weight) || weight <= 0) continue;

    points.set(month, {
      month,
      weight,
      feedCount: cells.length > 2 ? Number(cells[2].replace(/[^\d.]/g, '')) || 0 : 0,
      feedDuration: cells.length > 3 ? Number(cells[3].replace(/[^\d.]/g, '')) || 0 : 0,
      waterCount: cells.length > 4 ? Number(cells[4].replace(/[^\d.]/g, '')) || 0 : 0,
      waterDuration: cells.length > 5 ? Number(cells[5].replace(/[^\d.]/g, '')) || 0 : 0,
    });
  }

  return Array.from(points.values()).sort((a, b) => a.month - b.month);
};

// 解析 3 列预测表格
const parseCurvePointsFromReport = (markdown: string): CurvePoint[] => {
  const points = new Map<number, CurvePoint>();
  const lines = (markdown || '').replace(/\r/g, '').split('\n');

  let inPredictionSection = false;
  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line.includes('预测生长曲线数据') && line.includes('Monthly')) {
      inPredictionSection = true;
      continue;
    }

    if (!inPredictionSection) continue;
    if (!line.startsWith('|') || line.includes('---')) continue;

    const cells = line
      .split('|')
      .map((cell) => cell.trim())
      .filter(Boolean);

    if (cells.length < 2) continue;

    const month = Number(cells[0].replace(/[^\d]/g, ''));
    const weight = Number(cells[1].replace(/[^\d.]/g, ''));
    if (!Number.isFinite(month) || month <= 0 || !Number.isFinite(weight) || weight <= 0) continue;

    points.set(month, { month, weight, status: cells[2] || '' });
  }

  return Array.from(points.values()).sort((a, b) => a.month - b.month);
};

// 计算属性

const historicalPoints = computed(() => parseHistoricalPoints(reportContent.value));
const curvePoints = computed(() => parseCurvePointsFromReport(reportContent.value));

const curveError = computed(() => {
  if (reportError.value && !reportContent.value.trim()) return reportError.value;
  if (!isGeneratingReport.value && reportContent.value.trim() && !curvePoints.value.length) {
    return 'AI 报告中未找到可解析的生长曲线数据。';
  }
  return '';
});

// 统计卡片数据汇总
const stats = computed(() => {
  const pig = selectedPig.value;
  const hist = historicalPoints.value;
  const pred = curvePoints.value;

  if (!pig) return null;

  // 平均日增重：历史实测数据中计算
  let avgDailyGain = '--';
  if (hist.length >= 2) {
    const totalGain = hist[hist.length - 1].weight - hist[0].weight;
    const totalDays = (hist.length - 1) * 30; // 每月约30天
    avgDailyGain = (totalGain / totalDays).toFixed(2);
  }

  // 采食强度：最新月的喂食次数
  const latestHist = hist[hist.length - 1];
  const feedIntensity = latestHist ? latestHist.feedCount : '--';

  // 饮水指数：最新月饮水时长
  const waterIndex = latestHist ? latestHist.waterDuration : '--';

  // 预测增重与跨度
  let predGain = '--';
  let predDuration = '--';
  if (pred.length >= 2) {
    predGain = (pred[pred.length - 1].weight - pred[0].weight).toFixed(1);
    predDuration = String(Math.max(pred[pred.length - 1].month - pred[0].month, 0));
  }

  return {
    currentWeight: pig.current_weight_kg,
    predGain,
    predDuration,
    avgDailyGain,
    feedIntensity,
    waterIndex,
  };
});

// 接口调用 & 数据加载

const loadPigs = async () => {
  isLoadingPigs.value = true;
  pigsError.value = '';
  pigsList.value = [];
  try {
    const res = await apiService.getPigsList();
    if (!res || res.code !== 200 || !Array.isArray(res.data)) {
      throw new Error(res?.message || '获取猪只列表失败');
    }
    pigsList.value = res.data;
  } catch (error: any) {
    pigsError.value = error?.message || '获取猪只列表失败';
  } finally {
    isLoadingPigs.value = false;
  }
};

const handleStreamEvent = (pigId: string, event: InspectionStreamEvent) => {
  if (!isCurrentPig(pigId)) return;
  if (event.event === 'status') { streamStatus.value = event.data?.message || ''; return; }
  if (event.event === 'chunk') { reportContent.value += event.data?.text || ''; return; }
  if (event.event === 'error') { reportError.value = event.data?.detail || event.data?.message || '生成 AI 报告失败'; return; }
  if (event.event === 'done') { streamStatus.value = event.data?.message || 'AI 报告生成完成'; }
};

const requestReportFallback = async (pigId: string) => {
  const res = await apiService.generatePigInspectionReport(pigId);
  if (!isCurrentPig(pigId)) return;
  if (res && res.code === 200) {
    reportContent.value = res.report || '';
    reportError.value = '';
    streamStatus.value = 'AI 报告生成完成';
    return;
  }
  reportError.value = res?.detail || res?.message || '生成 AI 报告失败';
};

const loadReport = async (pigId: string) => {
  isGeneratingReport.value = true;
  streamStatus.value = '正在请求 AI 生长曲线报告...';
  reportContent.value = '';
  reportError.value = '';
  try {
    await apiService.streamPigInspectionReport(pigId, (event) => handleStreamEvent(pigId, event));
    if (isCurrentPig(pigId) && reportError.value && !reportContent.value.trim()) {
      await requestReportFallback(pigId);
    }
  } catch (error: any) {
    if (!isCurrentPig(pigId)) return;
    try {
      await requestReportFallback(pigId);
    } catch (fallbackError: any) {
      if (isCurrentPig(pigId)) reportError.value = fallbackError?.message || error?.message || '加载 AI 报告失败';
    }
  } finally {
    if (isCurrentPig(pigId)) isGeneratingReport.value = false;
  }
};

const viewGrowthCurve = async (pig: PigInfo) => {
  selectedPig.value = pig;
  streamStatus.value = '';
  reportContent.value = '';
  reportError.value = '';
  activeTab.value = 'growth';
  await loadReport(pig.pigId);
};

const backToList = () => {
  selectedPig.value = null;
  streamStatus.value = '';
  reportContent.value = '';
  reportError.value = '';
  isGeneratingReport.value = false;
  growthChart?.clear();
  feedChart?.clear();
  waterChart?.clear();
  gainChart?.clear();
};

// Markdown & HTML 渲染逻辑

const escapeHtml = (text: string) =>
  text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');

const renderInline = (line: string) =>
  line
    .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded-md bg-indigo-50 text-indigo-700 font-mono text-sm border border-indigo-100">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-semibold text-slate-800">$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em class="text-slate-700 italic">$1</em>');

const markdownToHtml = (markdown: string) => {
  const rawLines = (markdown || '').replace(/\r/g, '').split('\n');
  const html: string[] = [];
  let index = 0;

  while (index < rawLines.length) {
    const line = rawLines[index].trim();
    if (!line) { index += 1; continue; }

    if (line.startsWith('### ')) {
      html.push(`<h3 class="text-base font-bold text-slate-800 mt-6 mb-3 flex items-center before:content-[''] before:w-1 before:h-4 before:bg-indigo-400 before:mr-2 before:rounded-full">${renderInline(escapeHtml(line.slice(4)))}</h3>`);
      index += 1; continue;
    }
    if (line.startsWith('## ')) {
      html.push(`<h2 class="text-lg font-bold text-slate-800 mt-8 mb-4 border-b border-slate-100 pb-2">${renderInline(escapeHtml(line.slice(3)))}</h2>`);
      index += 1; continue;
    }
    if (line.startsWith('# ')) {
      html.push(`<h1 class="text-xl font-bold text-slate-900 mt-4 mb-4">${renderInline(escapeHtml(line.slice(2)))}</h1>`);
      index += 1; continue;
    }
    if (line.startsWith('> ')) {
      html.push(`<blockquote class="border-l-4 border-indigo-500 bg-indigo-50/50 p-4 rounded-r-lg my-4 text-slate-700 italic">${renderInline(escapeHtml(line.slice(2)))}</blockquote>`);
      index += 1; continue;
    }
    if (line.startsWith('- ')) {
      const items: string[] = [];
      while (index < rawLines.length && rawLines[index].trim().startsWith('- ')) {
        const item = rawLines[index].trim().slice(2);
        items.push(`<li class="mb-2 relative pl-1"><span class="absolute left-[-1.25rem] top-[0.4rem] w-1.5 h-1.5 rounded-full bg-slate-400"></span>${renderInline(escapeHtml(item))}</li>`);
        index += 1;
      }
      html.push(`<ul class="pl-6 text-slate-600 my-4 space-y-1">${items.join('')}</ul>`);
      continue;
    }
    if (line.startsWith('|')) {
      const sections: string[] = [];
      let rowIndex = 0;
      while (index < rawLines.length && rawLines[index].trim().startsWith('|')) {
        const row = rawLines[index].trim();
        if (row.includes('---')) { index += 1; continue; }
        const cells = row.split('|').map((cell) => cell.trim()).filter(Boolean);
        if (!cells.length) { index += 1; continue; }
        if (rowIndex === 0) {
          sections.push(`<thead><tr>${cells.map((cell) => `<th class="px-4 py-2 text-left text-xs font-bold text-slate-700 uppercase border-b-2 border-indigo-200 bg-indigo-50/50">${renderInline(escapeHtml(cell))}</th>`).join('')}</tr></thead><tbody>`);
        } else {
          sections.push(`<tr class="border-b border-slate-100 hover:bg-slate-50/50 transition-colors">${cells.map((cell) => `<td class="px-4 py-2 text-sm text-slate-600">${renderInline(escapeHtml(cell))}</td>`).join('')}</tr>`);
        }
        rowIndex += 1; index += 1;
      }
      if (sections.length) {
        html.push(`<div class="my-6 overflow-x-auto"><table class="w-full border border-slate-200 rounded-lg overflow-hidden shadow-sm">${sections.join('')}</tbody></table></div>`);
      }
      continue;
    }

    html.push(`<p class="text-slate-600 leading-relaxed my-3">${renderInline(escapeHtml(line))}</p>`);
    index += 1;
  }
  return html.join('');
};

const reportHtml = computed(() => markdownToHtml(reportContent.value));

// 图表配置与渲染

const COLORS = {
  historical: '#6366f1',
  prediction: '#8b5cf6',
  feed: '#f59e0b',
  water: '#06b6d4',
  gain: '#10b981',
  gainRef: '#e2e8f0',
};

// Tab1: 生长曲线（实测 + 预测）
const renderGrowthChart = () => {
  if (!growthChartRef.value) return;
  growthChart = echarts.getInstanceByDom(growthChartRef.value) || echarts.init(growthChartRef.value);

  const hist = historicalPoints.value;
  const pred = curvePoints.value;
  if (!hist.length && !pred.length) { growthChart.clear(); return; }

  // 合并所有月份的x轴
  const allMonths = [...new Set([...hist.map(p => p.month), ...pred.map(p => p.month)])].sort((a, b) => a - b);

  const histWeightMap = new Map(hist.map(p => [p.month, p.weight]));
  const predWeightMap = new Map(pred.map(p => [p.month, p.weight]));

  const histData = allMonths.map(m => histWeightMap.has(m) ? histWeightMap.get(m)! : null);
  const predData = allMonths.map(m => predWeightMap.has(m) ? predWeightMap.get(m)! : null);

  growthChart.setOption({
    animation: true,
    animationDuration: 1200,
    grid: { top: 48, right: 24, bottom: 36, left: 52 },
    legend: {
      data: ['历史实测', '预测曲线'],
      top: 8,
      textStyle: { color: '#64748b', fontSize: 12 },
      icon: 'circle',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#e2e8f0',
      textStyle: { color: '#0f172a' },
      padding: [10, 14],
      formatter: (params: any) => {
        const month = allMonths[params[0].dataIndex];
        let html = `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px;">第 ${month} 月</div>`;
        for (const p of params) {
          if (p.value !== null) {
            html += `<div style="display:flex;justify-content:space-between;gap:16px;margin-top:4px;"><span style="color:#64748b;">${p.seriesName}</span><span style="font-weight:600;color:${p.color};">${p.value} kg</span></div>`;
          }
        }
        return html;
      },
    },
    xAxis: {
      type: 'category',
      data: allMonths.map(m => `${m}月`),
      axisLabel: { color: '#64748b' },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#64748b', formatter: '{value} kg' },
      splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } },
    },
    series: [
      {
        name: '历史实测',
        type: 'line',
        smooth: 0.3,
        data: histData,
        connectNulls: false,
        symbol: 'circle',
        symbolSize: 9,
        lineStyle: { width: 3, color: COLORS.historical },
        itemStyle: { color: COLORS.historical },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(99,102,241,0.20)' },
            { offset: 1, color: 'rgba(255,255,255,0)' },
          ]),
        },
      },
      {
        name: '预测曲线',
        type: 'line',
        smooth: 0.35,
        data: predData,
        connectNulls: false,
        symbol: 'diamond',
        symbolSize: 9,
        lineStyle: { width: 3, color: COLORS.prediction, type: 'dashed' },
        itemStyle: { color: COLORS.prediction },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(139,92,246,0.14)' },
            { offset: 1, color: 'rgba(255,255,255,0)' },
          ]),
        },
      },
    ],
  }, true);
};

// Tab2: 喂食趋势（次数 + 时长）
const renderFeedChart = () => {
  if (!feedChartRef.value) return;
  feedChart = echarts.getInstanceByDom(feedChartRef.value) || echarts.init(feedChartRef.value);
  const hist = historicalPoints.value;
  if (!hist.length) { feedChart.clear(); return; }

  feedChart.setOption({
    animation: true, animationDuration: 1000,
    grid: { top: 48, right: 50, bottom: 36, left: 48 },
    legend: { data: ['喂食次数', '喂食时长(min)'], top: 8, textStyle: { color: '#64748b', fontSize: 12 }, icon: 'circle' },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.96)', borderColor: '#e2e8f0', textStyle: { color: '#0f172a' }, padding: [10, 14] },
    xAxis: { type: 'category', data: hist.map(p => `${p.month}月`), axisLabel: { color: '#64748b' } },
    yAxis: [
      { type: 'value', name: '次数', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } } },
      { type: 'value', name: '时长', axisLabel: { color: '#64748b', formatter: '{value}min' } },
    ],
    series: [
      {
        name: '喂食次数', type: 'bar', yAxisIndex: 0,
        data: hist.map(p => p.feedCount),
        barMaxWidth: 32,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#fbbf24' }, { offset: 1, color: '#f59e0b' }]), borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '喂食时长(min)', type: 'line', yAxisIndex: 1,
        data: hist.map(p => p.feedDuration),
        smooth: 0.4, symbol: 'circle', symbolSize: 7,
        lineStyle: { width: 2.5, color: '#f97316' },
        itemStyle: { color: '#f97316' },
      },
    ],
  }, true);
};

// Tab3: 饮水趋势（次数 + 时长）
const renderWaterChart = () => {
  if (!waterChartRef.value) return;
  waterChart = echarts.getInstanceByDom(waterChartRef.value) || echarts.init(waterChartRef.value);
  const hist = historicalPoints.value;
  if (!hist.length) { waterChart.clear(); return; }

  waterChart.setOption({
    animation: true, animationDuration: 1000,
    grid: { top: 48, right: 50, bottom: 36, left: 48 },
    legend: { data: ['饮水次数', '饮水时长(min)'], top: 8, textStyle: { color: '#64748b', fontSize: 12 }, icon: 'circle' },
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.96)', borderColor: '#e2e8f0', textStyle: { color: '#0f172a' }, padding: [10, 14] },
    xAxis: { type: 'category', data: hist.map(p => `${p.month}月`), axisLabel: { color: '#64748b' } },
    yAxis: [
      { type: 'value', name: '次数', axisLabel: { color: '#64748b' }, splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } } },
      { type: 'value', name: '时长', axisLabel: { color: '#64748b', formatter: '{value}min' } },
    ],
    series: [
      {
        name: '饮水次数', type: 'bar', yAxisIndex: 0,
        data: hist.map(p => p.waterCount),
        barMaxWidth: 32,
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#38bdf8' }, { offset: 1, color: '#0ea5e9' }]), borderRadius: [4, 4, 0, 0] },
      },
      {
        name: '饮水时长(min)', type: 'line', yAxisIndex: 1,
        data: hist.map(p => p.waterDuration),
        smooth: 0.4, symbol: 'circle', symbolSize: 7,
        lineStyle: { width: 2.5, color: '#06b6d4' },
        itemStyle: { color: '#06b6d4' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: 'rgba(6,182,212,0.15)' }, { offset: 1, color: 'rgba(255,255,255,0)' }]) },
      },
    ],
  }, true);
};

// Tab4: 日增重分析（及参考线）
const renderGainChart = () => {
  if (!gainChartRef.value) return;
  gainChart = echarts.getInstanceByDom(gainChartRef.value) || echarts.init(gainChartRef.value);
  const hist = historicalPoints.value;
  if (hist.length < 2) { gainChart.clear(); return; }

  // 计算每月日增重（月增重/30）
  const gains = hist.slice(1).map((p, i) => {
    const gain = ((p.weight - hist[i].weight) / 30);
    return Math.max(parseFloat(gain.toFixed(3)), 0);
  });
  const months = hist.slice(1).map(p => `${p.month}月`);
  const avgGain = gains.reduce((s, v) => s + v, 0) / gains.length;

  gainChart.setOption({
    animation: true, animationDuration: 1000,
    grid: { top: 48, right: 24, bottom: 36, left: 52 },
    legend: { data: ['日增重(kg/天)', '平均线'], top: 8, textStyle: { color: '#64748b', fontSize: 12 }, icon: 'circle' },
    tooltip: {
      trigger: 'axis', backgroundColor: 'rgba(255,255,255,0.96)', borderColor: '#e2e8f0', textStyle: { color: '#0f172a' }, padding: [10, 14],
      formatter: (params: any) => {
        const p = params[0];
        return `<div style="font-weight:700;margin-bottom:4px;">${months[p.dataIndex]}</div><div>日增重：<strong style="color:${COLORS.gain};">${p.value} kg/天</strong></div>`;
      },
    },
    xAxis: { type: 'category', data: months, axisLabel: { color: '#64748b' } },
    yAxis: { type: 'value', name: 'kg/天', axisLabel: { color: '#64748b', formatter: (v: number) => v.toFixed(2) }, splitLine: { lineStyle: { color: '#f1f5f9', type: 'dashed' } } },
    series: [
      {
        name: '日增重(kg/天)', type: 'bar',
        data: gains,
        barMaxWidth: 40,
        itemStyle: {
          color: (params: any) => {
            const v = gains[params.dataIndex];
            return v >= avgGain ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#34d399' }, { offset: 1, color: '#10b981' }])
              : new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#fca5a5' }, { offset: 1, color: '#ef4444' }]);
          },
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: '平均线', type: 'line',
        data: gains.map(() => parseFloat(avgGain.toFixed(3))),
        symbol: 'none',
        lineStyle: { width: 1.5, color: '#94a3b8', type: 'dashed' },
        itemStyle: { color: '#94a3b8' },
      },
    ],
  }, true);
};

const renderActiveChart = async () => {
  await nextTick();
  if (activeTab.value === 'growth') renderGrowthChart();
  else if (activeTab.value === 'feed') renderFeedChart();
  else if (activeTab.value === 'water') renderWaterChart();
  else if (activeTab.value === 'gain') renderGainChart();
};

const switchTab = (tab: 'growth' | 'feed' | 'water' | 'gain') => {
  activeTab.value = tab;
  renderActiveChart();
};

const resizeAllCharts = () => {
  growthChart?.resize();
  feedChart?.resize();
  waterChart?.resize();
  gainChart?.resize();
};

watch([historicalPoints, curvePoints], async () => {
  await nextTick();
  renderActiveChart();
}, { deep: true });

watch(activeTab, async () => {
  await nextTick();
  renderActiveChart();
});

onMounted(async () => {
  await loadPigs();
  window.addEventListener('resize', resizeAllCharts);
});

onUnmounted(() => {
  window.removeEventListener('resize', resizeAllCharts);
  growthChart?.dispose();
  feedChart?.dispose();
  waterChart?.dispose();
  gainChart?.dispose();
  growthChart = feedChart = waterChart = gainChart = null;
});
</script>

<template>
  <div class="h-full flex flex-col space-y-5 animate-fade-in">
    <!-- Header -->
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
            {{ selectedPig ? `生长曲线 - ${selectedPig.pigId}` : '猪只生长曲线分析' }}
          </h1>
          <p class="text-sm text-slate-500 mt-1 flex items-center">
            <span
              class="inline-block w-2 h-2 rounded-full mr-2"
              :class="selectedPig && isGeneratingReport ? 'bg-amber-400 animate-pulse' : 'bg-emerald-400'"
            ></span>
            {{
              selectedPig
                ? (isGeneratingReport ? (streamStatus || 'AI 正在生成报告...') : 'AI 报告已生成，可查看多维度生长分析')
                : '选择猪只后将调用 AI 生成报告，并从报告中解析历史实测和预测曲线'
            }}
          </p>
        </div>
      </div>
      <button
        v-if="!selectedPig"
        @click="loadPigs"
        class="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-600 text-sm rounded-lg flex items-center shadow-sm transition-colors font-medium"
      >
        <RefreshCw class="w-4 h-4 mr-2" :class="{ 'animate-spin': isLoadingPigs }" />
        刷新列表
      </button>
    </div>

    <!-- Main Content -->
    <div
      class="flex-1 overflow-hidden relative"
      :class="!selectedPig ? 'bg-transparent' : 'bg-slate-50/50 rounded-2xl border border-slate-200/60 p-4 md:p-6 lg:p-8'"
    >
      <!-- 猪只选择列表 -->
      <div v-if="!selectedPig" class="h-full overflow-y-auto pb-6">
        <div v-if="isLoadingPigs" class="flex flex-col items-center justify-center py-32">
          <div class="relative w-16 h-16">
            <div class="absolute inset-0 border-4 border-indigo-500 rounded-full border-t-transparent animate-spin"></div>
          </div>
          <p class="text-slate-500 text-sm mt-6 font-medium">正在加载猪只列表...</p>
        </div>
        <div v-else-if="pigsError" class="flex flex-col items-center justify-center py-32">
          <AlertCircle class="w-16 h-16 text-red-300 mb-4" />
          <p class="text-red-600 text-sm font-medium">{{ pigsError }}</p>
          <button @click="loadPigs" class="mt-4 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors">重新加载</button>
        </div>
        <div v-else-if="pigsList.length === 0" class="flex flex-col items-center justify-center py-32">
          <AlertCircle class="w-16 h-16 text-slate-300 mb-4" />
          <p class="text-slate-500 text-sm font-medium">当前没有可分析的猪只数据</p>
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
                <p class="text-sm text-slate-500 mt-1">{{ pig.area }}</p>
              </div>
              <div class="p-2 bg-indigo-50 rounded-xl text-indigo-600">
                <Activity class="w-5 h-5" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-4 mt-auto border-t border-slate-100 pt-5">
              <div class="bg-slate-50 p-3 rounded-xl">
                <p class="text-xs text-slate-500 mb-1">当前月龄</p>
                <p class="text-2xl font-bold text-slate-800">{{ pig.current_month }}<span class="text-xs font-normal ml-1">月</span></p>
              </div>
              <div class="bg-indigo-50/50 p-3 rounded-xl">
                <p class="text-xs text-slate-500 mb-1">当前体重</p>
                <p class="text-2xl font-bold text-indigo-700">{{ pig.current_weight_kg }}<span class="text-xs font-normal">kg</span></p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 报告详情视图 -->
      <div v-else class="h-full flex flex-col gap-5 overflow-y-auto custom-scrollbar">

        <!-- 统计卡片区（6个） -->
        <div class="grid grid-cols-3 md:grid-cols-6 gap-3 flex-shrink-0">
          <!-- 当前体重 -->
          <div class="stat-card col-span-1">
            <div class="stat-icon bg-slate-100 text-slate-600"><TrendingUp class="w-4 h-4" /></div>
            <p class="stat-label">当前体重</p>
            <p class="stat-value">{{ stats?.currentWeight ?? '--' }}<span class="stat-unit">kg</span></p>
          </div>
          <!-- 预测增重 -->
          <div class="stat-card col-span-1">
            <div class="stat-icon bg-indigo-100 text-indigo-600"><TrendingUp class="w-4 h-4" /></div>
            <p class="stat-label">预测增重</p>
            <p class="stat-value text-indigo-600">{{ stats?.predGain ?? '--' }}<span class="stat-unit">kg</span></p>
          </div>
          <!-- 预测跨度 -->
          <div class="stat-card col-span-1">
            <div class="stat-icon bg-purple-100 text-purple-600"><Activity class="w-4 h-4" /></div>
            <p class="stat-label">预测跨度</p>
            <p class="stat-value text-purple-600">{{ stats?.predDuration ?? '--' }}<span class="stat-unit">月</span></p>
          </div>
          <!-- 平均日增重 -->
          <div class="stat-card col-span-1">
            <div class="stat-icon bg-emerald-100 text-emerald-600"><Zap class="w-4 h-4" /></div>
            <p class="stat-label">平均日增重</p>
            <p class="stat-value text-emerald-600">
              <template v-if="isGeneratingReport && !historicalPoints.length">
                <span class="text-sm text-slate-400 animate-pulse">--</span>
              </template>
              <template v-else>{{ stats?.avgDailyGain ?? '--' }}<span class="stat-unit">kg/天</span></template>
            </p>
          </div>
          <!-- 采食强度 -->
          <div class="stat-card col-span-1">
            <div class="stat-icon bg-amber-100 text-amber-600"><Utensils class="w-4 h-4" /></div>
            <p class="stat-label">采食强度</p>
            <p class="stat-value text-amber-600">
              <template v-if="isGeneratingReport && !historicalPoints.length">
                <span class="text-sm text-slate-400 animate-pulse">--</span>
              </template>
              <template v-else>{{ stats?.feedIntensity ?? '--' }}<span class="stat-unit">次/月</span></template>
            </p>
          </div>
          <!-- 饮水指数 -->
          <div class="stat-card col-span-1">
            <div class="stat-icon bg-cyan-100 text-cyan-600"><Droplets class="w-4 h-4" /></div>
            <p class="stat-label">饮水时长</p>
            <p class="stat-value text-cyan-600">
              <template v-if="isGeneratingReport && !historicalPoints.length">
                <span class="text-sm text-slate-400 animate-pulse">--</span>
              </template>
              <template v-else>{{ stats?.waterIndex ?? '--' }}<span class="stat-unit">min/月</span></template>
            </p>
          </div>
        </div>

        <!-- 图表+报告区 -->
        <div class="flex flex-col md:flex-row gap-5 flex-1 min-h-0">
          <!-- 左侧：多图表Tab区 -->
          <div class="w-full md:w-7/12 lg:w-2/3 flex flex-col gap-4">
            <!-- Tab 导航 -->
            <div class="bg-white border border-slate-200 rounded-2xl p-1.5 flex gap-1 shadow-sm flex-shrink-0">
              <button
                v-for="tab in ([
                  { key: 'growth', label: '📈 生长曲线', activeColor: 'bg-indigo-500 text-white' },
                  { key: 'feed', label: '🍽️ 喂食趋势', activeColor: 'bg-amber-500 text-white' },
                  { key: 'water', label: '💧 饮水趋势', activeColor: 'bg-cyan-500 text-white' },
                  { key: 'gain', label: '⚡ 日增重', activeColor: 'bg-emerald-500 text-white' },
                ] as const)"
                :key="tab.key"
                @click="switchTab(tab.key as any)"
                :class="[
                  'flex-1 py-2 px-2 text-xs font-semibold rounded-xl transition-all duration-200',
                  activeTab === tab.key ? tab.activeColor + ' shadow-sm' : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50',
                ]"
              >
                {{ tab.label }}
              </button>
            </div>

            <!-- 图表容器 -->
            <div class="bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex-1 min-h-[380px] relative">
              <!-- 加载中遮罩 -->
              <div
                v-if="isGeneratingReport && !curvePoints.length && !historicalPoints.length && !curveError"
                class="absolute inset-0 z-10 bg-white/90 rounded-2xl flex flex-col items-center justify-center"
              >
                <div class="w-10 h-10 mb-3 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                <p class="text-sm font-medium text-slate-500 animate-pulse">AI 正在生成分析数据...</p>
              </div>

              <!-- 错误状态 -->
              <div
                v-else-if="curveError && !isGeneratingReport"
                class="absolute inset-0 z-10 bg-white rounded-2xl flex flex-col items-center justify-center px-6 text-center"
              >
                <AlertCircle class="w-12 h-12 text-red-300 mb-4" />
                <p class="text-sm font-medium text-red-600">{{ curveError }}</p>
              </div>

              <!-- 历史数据不足提示（仅日增重Tab） -->
              <div
                v-else-if="activeTab === 'gain' && historicalPoints.length < 2 && !isGeneratingReport"
                class="absolute inset-0 z-10 bg-white rounded-2xl flex flex-col items-center justify-center px-6 text-center"
              >
                <AlertCircle class="w-12 h-12 text-slate-300 mb-4" />
                <p class="text-sm font-medium text-slate-500">需要至少 2 个月的历史数据才能分析日增重</p>
              </div>

              <!-- 历史数据不足提示（喂食/饮水Tab） -->
              <div
                v-else-if="(activeTab === 'feed' || activeTab === 'water') && !historicalPoints.length && !isGeneratingReport"
                class="absolute inset-0 z-10 bg-white rounded-2xl flex flex-col items-center justify-center px-6 text-center"
              >
                <AlertCircle class="w-12 h-12 text-slate-300 mb-4" />
                <p class="text-sm font-medium text-slate-500">暂未解析到喂食/饮水历史数据</p>
              </div>

              <!-- 图表画布（按Tab显示/隐藏以保留DOM） -->
              <div ref="growthChartRef" class="w-full h-full" :class="{ hidden: activeTab !== 'growth' }"></div>
              <div ref="feedChartRef" class="w-full h-full" :class="{ hidden: activeTab !== 'feed' }"></div>
              <div ref="waterChartRef" class="w-full h-full" :class="{ hidden: activeTab !== 'water' }"></div>
              <div ref="gainChartRef" class="w-full h-full" :class="{ hidden: activeTab !== 'gain' }"></div>
            </div>
          </div>

          <!-- 右侧：AI 报告 -->
          <div class="w-full md:w-5/12 lg:w-1/3 bg-white border border-slate-200 rounded-2xl shadow-sm flex flex-col overflow-hidden min-h-[400px] md:min-h-0">
            <div class="px-5 py-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between flex-shrink-0">
              <h3 class="font-bold text-slate-800 flex items-center text-sm">
                <Activity class="w-4 h-4 mr-2" />
                AI 生长曲线报告
              </h3>
              <span v-if="isGeneratingReport" class="text-[10px] font-bold text-indigo-500 animate-pulse">RUNNING</span>
            </div>
            <div class="flex-1 overflow-y-auto p-5 custom-scrollbar relative">
              <div v-if="reportHtml" class="report-markdown text-sm" v-html="reportHtml"></div>
              <div v-else-if="reportError" class="h-full flex flex-col items-center justify-center text-center px-4">
                <AlertCircle class="w-12 h-12 text-red-300 mb-4" />
                <p class="text-sm font-medium text-red-600">{{ reportError }}</p>
              </div>
              <div v-else-if="!isGeneratingReport" class="h-full flex flex-col items-center justify-center text-center px-4">
                <AlertCircle class="w-12 h-12 text-slate-300 mb-4" />
                <p class="text-sm font-medium text-slate-500">暂无 AI 报告内容</p>
              </div>
              <div v-if="reportError && reportHtml" class="mt-4 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
                {{ reportError }}
              </div>
              <div v-if="isGeneratingReport" class="mt-4 flex space-x-1 pb-8">
                <span class="w-2 h-2 rounded-full bg-indigo-400 animate-bounce"></span>
                <span class="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:120ms]"></span>
                <span class="w-2 h-2 rounded-full bg-indigo-400 animate-bounce [animation-delay:240ms]"></span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }

.animate-fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* 统计卡片基础样式 */
.stat-card {
  @apply bg-white border border-slate-200 rounded-2xl p-4 shadow-sm flex flex-col gap-2;
}
.stat-icon {
  @apply w-8 h-8 rounded-xl flex items-center justify-center self-start flex-shrink-0;
}
.stat-label {
  @apply text-xs text-slate-500 font-medium leading-tight;
}
.stat-value {
  @apply text-xl font-bold text-slate-800 font-mono leading-tight;
}
.stat-unit {
  @apply text-xs font-normal text-slate-500 ml-0.5;
}
</style>

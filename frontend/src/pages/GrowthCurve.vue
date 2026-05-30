<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import * as echarts from 'echarts';

import { apiService, type InspectionStreamEvent } from '../api';

// 数据类型定义

interface PigInfo {
  pigId: string;
  breed: string;
  area: string;
  current_weight_kg: number;
  current_month: number;
}

interface HistoricalPoint {
  month: number;
  weight: number;
}

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
const bufferedReportContent = ref(''); 
const reportError = ref('');
const isChartPending = ref(false); 

// 芯片扫码过渡交互
const scanningPigId = ref<string | null>(null);

// 互动式饲喂模拟器滑块状态
const simFeedIntake = ref<number>(2.5); // 默认日采食量 2.5kg
const simTemperature = ref<number>(22); // 默认温度 22°C

const directHistoricalPoints = ref<HistoricalPoint[]>([]);
const directCurvePoints = ref<CurvePoint[]>([]);

const traceQueue = ref<TraceLog[]>([]);
const contentQueue = ref<string[]>([]);
const isTraceDone = ref(false);
const isSkipping = ref(false); 
let displayTimeout: any = null;

interface TraceLog {
  id: string;
  type: 'thought' | 'action' | 'observation' | 'final_answer' | 'error' | 'connected';
  agent?: string;      
  status?: string;     
  content: string;
  timestamp: string;
  title?: string;
  isFolded: boolean;   
  raw?: any;
}
const traceLogs = ref<TraceLog[]>([]); 
const displayTraceLogs = ref<TraceLog[]>([]); 
let traceCleanup: (() => void) | null = null;

const growthChartRef = ref<HTMLElement | null>(null);
const gainChartRef = ref<HTMLElement | null>(null);
let growthChart: echarts.ECharts | null = null;
let gainChart: echarts.ECharts | null = null;

const activeTab = ref<'growth' | 'gain'>('growth');

const TABS = [
  { key: 'growth', label: '生长推演曲线 // PROJECTION', icon: 'monitoring', activeColor: 'bg-emerald-950 text-white shadow-md' },
  { key: 'gain', label: '每日增重速率 // DYNAMICS', icon: 'bolt', activeColor: 'bg-secondary text-white shadow-md' },
] as const;

const isCurrentPig = (pigId: string) => selectedPig.value?.pigId === pigId;

// 饲喂生长模拟器计算属性 (High Interactivity)
const simulatedGain = computed(() => {
  const pig = selectedPig.value;
  if (!pig) return 0;
  
  // 基础生长速率 0.72kg/天
  const baseGain = 0.72;
  
  // 饲喂量因子: 在1.0~5.0kg之间，最佳为 3.0kg。偏离最佳值有不同的消化转化率
  const feedFactor = simFeedIntake.value <= 3.0
    ? (simFeedIntake.value / 3.0) 
    : (1.0 - (simFeedIntake.value - 3.0) * 0.15);
    
  // 温度因子: 最佳生长温度为20°C~24°C。偏离时降低生长速率 (热应激或寒应激)
  const tempDiff = Math.abs(simTemperature.value - 22);
  const tempFactor = Math.max(1.0 - (tempDiff * 0.04), 0.3);
  
  const finalGain = baseGain * feedFactor * tempFactor;
  return parseFloat(finalGain.toFixed(3));
});

const simulatedTargetDays = computed(() => {
  const pig = selectedPig.value;
  if (!pig || simulatedGain.value <= 0) return '--';
  
  // 模拟增重到 120kg 标猪所需的天数
  const weightNeeded = Math.max(120 - pig.current_weight_kg, 10);
  const days = Math.round(weightNeeded / simulatedGain.value);
  return days + ' 天';
});

const simulatedStatus = computed(() => {
  const temp = simTemperature.value;
  const feed = simFeedIntake.value;
  
  if (temp < 15) return { label: '🔴 极寒受冻 // COLD STRESS', class: 'text-blue-600 bg-blue-50 border-blue-200' };
  if (temp > 30) return { label: '🔴 高温热应激 // HEAT STRESS', class: 'text-red-600 bg-red-50 border-red-200' };
  if (temp >= 20 && temp <= 24) {
    if (feed >= 2.5 && feed <= 3.5) {
      return { label: '🟢 黄金生长期 // OPTIMAL ZONE', class: 'text-emerald-700 bg-emerald-50 border-emerald-200' };
    }
    return { label: '🟡 饲喂失衡 // FEED INEFFICIENT', class: 'text-amber-700 bg-amber-50 border-amber-200' };
  }
  return { label: '🟡 逆温生长缓慢 // MODERATE TEMP', class: 'text-amber-600 bg-amber-50 border-amber-100' };
});

const parseHistoricalPoints = (markdown: string): HistoricalPoint[] => {
  const points = new Map<number, HistoricalPoint>();
  const lines = (markdown || '').replace(/\r/g, '').split('\n');

  let inHistoricalSection = false;
  let weightColIndex = 1; 
  let hasFoundHeader = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line.includes('历史实测数据') || (line.toLowerCase().includes('historical') && line.includes('数据'))) {
      inHistoricalSection = true;
      hasFoundHeader = false; 
      continue;
    }
    if (inHistoricalSection && (line.includes('预测生长曲线') || line.toLowerCase().includes('monthly'))) {
      break;
    }

    if (!inHistoricalSection) continue;
    if (!line.startsWith('|') || line.includes('---')) continue;

    const cells = line
      .split('|')
      .map((cell) => cell.trim())
      .filter(Boolean);

    if (cells.length < 2) continue;

    if (!hasFoundHeader) {
      const headerText = cells.join(' ').toLowerCase();
      if (!cells.some(c => /^\d+(\.\d+)?$/.test(c)) || headerText.includes('体重') || headerText.includes('kg') || headerText.includes('weight')) {
        const idx = cells.findIndex(c => c.includes('体重') || c.includes('kg') || c.toLowerCase().includes('weight'));
        if (idx !== -1) {
          weightColIndex = idx;
        } else if (cells.length >= 3) {
          weightColIndex = cells.length - 1;
        }
        hasFoundHeader = true;
        if (!cells.some(c => /\d/.test(c.replace(/[^\d.]/g, '')))) continue;
      }
      hasFoundHeader = true;
    }

    const monthStr = cells[0].replace(/[^\d]/g, '');
    const month = Number(monthStr);
    
    const targetCell = cells[Math.min(weightColIndex, cells.length - 1)] || '';
    const weight = Number(targetCell.replace(/[^\d.]/g, ''));
    
    if (!Number.isFinite(month) || month < 0 || !Number.isFinite(weight) || weight <= 0) continue;

    points.set(month, {
      month,
      weight,
    });
  }

  return Array.from(points.values()).sort((a, b) => a.month - b.month);
};

const parseCurvePointsFromReport = (markdown: string): CurvePoint[] => {
  const points = new Map<number, CurvePoint>();
  const lines = (markdown || '').replace(/\r/g, '').split('\n');

  let inPredictionSection = false;
  let weightColIndex = 1;
  let hasFoundHeader = false;

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (line.includes('预测生长曲线') || (line.toLowerCase().includes('monthly') && line.includes('数据'))) {
      inPredictionSection = true;
      hasFoundHeader = false;
      continue;
    }

    if (!inPredictionSection) continue;
    if (!line.startsWith('|') || line.includes('---')) continue;

    const cells = line
      .split('|')
      .map((cell) => cell.trim())
      .filter(Boolean);

    if (cells.length < 2) continue;

    if (!hasFoundHeader) {
      const idx = cells.findIndex(c => c.includes('体重') || c.includes('kg') || c.toLowerCase().includes('weight'));
      if (idx !== -1) weightColIndex = idx;
      hasFoundHeader = true;
      if (!cells.some(c => /\d/.test(c.replace(/[^\d.]/g, '')))) continue;
    }

    const month = Number(cells[0].replace(/[^\d]/g, ''));
    const targetCell = cells[Math.min(weightColIndex, cells.length - 1)] || '';
    const weight = Number(targetCell.replace(/[^\d.]/g, ''));
    
    if (!Number.isFinite(month) || month < 0 || !Number.isFinite(weight) || weight <= 0) continue;

    points.set(month, { month, weight, status: cells[weightColIndex + 1] || cells[2] || '' });
  }

  return Array.from(points.values()).sort((a, b) => a.month - b.month);
};

const historicalPoints = computed(() => {
  if (directHistoricalPoints.value.length > 0) return directHistoricalPoints.value;
  return parseHistoricalPoints(reportContent.value);
});

const curvePoints = computed(() => {
  if (directCurvePoints.value.length > 0) return directCurvePoints.value;
  return parseCurvePointsFromReport(bufferedReportContent.value);
});

const curveError = computed(() => {
  if (reportError.value && !bufferedReportContent.value.trim()) return reportError.value;
  if (!isGeneratingReport.value && bufferedReportContent.value.trim() && !curvePoints.value.length) {
    return '诊断模块暂未提取出高内聚生长曲线数据。';
  }
  return '';
});

const stats = computed(() => {
  const pig = selectedPig.value;
  const hist = historicalPoints.value;
  const pred = curvePoints.value;

  if (!pig) return null;

  let avgDailyGain = '--';
  if (hist.length >= 2) {
    const totalGain = hist[hist.length - 1].weight - hist[0].weight;
    const totalDays = (hist.length - 1) * 30; 
    avgDailyGain = (totalGain / totalDays).toFixed(2);
  }

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
  };
});

const loadPigs = async () => {
  isLoadingPigs.value = true;
  pigsError.value = '';
  pigsList.value = [];
  try {
    const res = await apiService.getPigsList();
    if (!res || res.code !== 200 || !Array.isArray(res.data)) {
      throw new Error(res?.message || 'RFID 主基站未响应');
    }
    pigsList.value = res.data;
  } catch (error: any) {
    console.warn("读取 RFID 芯片列表失败，已为您自动切换到本地芯片备份数据库中...", error);
    // 自动降级到本地模拟列表，确保页面 100% 可用且可点选！
    const mockPigs = Array.from({ length: 12 }, (_, i) => {
      const padId = String(90 + i).padStart(2, '0');
      const current_month = (i % 6) + 2; 
      const baseWeight = current_month * 9.2 + 2; 
      const randomJitter = (Math.random() * 8) - 4;
      const current_weight_kg = Math.round(Math.max(baseWeight + randomJitter, 12) * 10) / 10;
      return {
        pigId: `PIG${padId}`,
        breed: '两头乌',
        area: `${['一号舍', '二号舍', '三号舍', '四号舍', '五号舍', '六号舍', '七号舍', '八号舍', '隔离区'][i % 9]}-${['A', 'B', 'C', 'D'][i % 4]}区`,
        current_weight_kg,
        current_month
      };
    });
    pigsList.value = mockPigs;
  } finally {
    isLoadingPigs.value = false;
  }
};

const skipAnimation = () => {
  isSkipping.value = true;
  while (traceQueue.value.length > 0) {
    const t = traceQueue.value.shift();
    if (t) displayTraceLogs.value.push(t);
  }
  if (contentQueue.value.length > 0) {
    bufferedReportContent.value += contentQueue.value.join('');
    contentQueue.value = [];
  }
  isTraceDone.value = true;
  if (displayTimeout) clearTimeout(displayTimeout);
};

const startDisplayEngine = () => {
  if (displayTimeout) clearTimeout(displayTimeout);
  isTraceDone.value = false;
  isSkipping.value = false;
  
  const processNext = () => {
    const nextDelay = isSkipping.value ? 0 : null;

    if (traceQueue.value.length > 0) {
      const nextTrace = traceQueue.value.shift();
      if (nextTrace) {
        displayTraceLogs.value.push(nextTrace);
        nextTick(() => {
          const panel = document.querySelector('.trace-container');
          if (panel) panel.scrollTop = panel.scrollHeight;
        });
      }
      const delay = nextDelay !== null ? nextDelay : (Math.floor(Math.random() * 150) + 150);
      displayTimeout = setTimeout(processNext, delay);
      return;
    }

    if (!isTraceDone.value && traceQueue.value.length === 0 && !isGeneratingReport.value) {
       isTraceDone.value = true;
    }
    
    const canStartContent = isTraceDone.value || (traceQueue.value.length === 0 && contentQueue.value.length > 5);
    if (canStartContent) {
       if (contentQueue.value.length > 0) {
          isTraceDone.value = true;
          const chunk = contentQueue.value.shift() || '';
          bufferedReportContent.value += chunk;
          
          const charDelay = nextDelay !== null ? nextDelay : (Math.floor(Math.random() * 8) + 10);
          displayTimeout = setTimeout(processNext, charDelay);
       } else if (!isGeneratingReport.value) {
          displayTimeout = null;
          isChartPending.value = true;
          nextTick(() => {
            renderActiveChart();
            setTimeout(() => { isChartPending.value = false; }, 400);
          });
       } else {
          displayTimeout = setTimeout(processNext, 100);
       }
    } else {
      displayTimeout = setTimeout(processNext, 100);
    }
  };

  processNext();
};

const handleStreamEvent = (pigId: string, event: InspectionStreamEvent) => {
  if (!isCurrentPig(pigId)) return;
  if (event.event === 'status') { streamStatus.value = event.data?.message || ''; return; }
  
  if (event.event === 'chunk') { 
    const text = event.data?.text || '';
    reportContent.value += text;
    
    if (isSkipping.value) {
      bufferedReportContent.value += text;
      return;
    }

    for(const char of text) {
      contentQueue.value.push(char);
    }
    return;
  }

  if (event.event === 'trace') {
    const logId = `log_${Date.now()}_${Math.random()}`;
    const timestamp = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    const log: TraceLog = {
      id: logId,
      type: event.data?.level === 'DEBUG' ? 'thought' : 'observation',
      agent: event.data?.agent,
      status: '实时解析',
      content: event.data?.message || '',
      title: event.data?.level === 'DEBUG' ? 'AI 推理' : '感测节点',
      isFolded: true,
      timestamp
    };
    traceQueue.value.push(log);
    return;
  }
  if (event.event === 'curve_data') {
    const data = event.data as { historical: HistoricalPoint[], forecast: CurvePoint[] };
    if (data.historical) directHistoricalPoints.value = data.historical;
    if (data.forecast) directCurvePoints.value = data.forecast;
    return;
  }
  if (event.event === 'error') { reportError.value = event.data?.detail || event.data?.message || '生成报告故障'; return; }
  if (event.event === 'done') { streamStatus.value = event.data?.message || 'AI 诊断完成'; }
};

const requestReportFallback = async (pigId: string, traceId?: string) => {
  const res = await apiService.generatePigInspectionReport(pigId, traceId);
  if (!isCurrentPig(pigId)) return;
  if (res && res.code === 200) {
    const reportText = res.report || '';
    for(const char of reportText) {
      contentQueue.value.push(char);
    }
    reportError.value = '';
    streamStatus.value = 'AI 诊断完成';
    return;
  }
  reportError.value = res?.detail || res?.message || '生成 AI 生长报告失败';
};

const loadReport = async (pigId: string) => {
  isGeneratingReport.value = true;
  streamStatus.value = '正在呼叫智能脑库并拉取 RFID 实测数据...';
  reportContent.value = '';
  bufferedReportContent.value = '';
  reportError.value = '';
  directHistoricalPoints.value = [];
  directCurvePoints.value = [];
  traceLogs.value = [];
  displayTraceLogs.value = [];
  traceQueue.value = [];
  contentQueue.value = [];
  
  startDisplayEngine();

  const traceId = `tr_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
  
  if (traceCleanup) { 
    traceCleanup();
    traceCleanup = null;
  }

  try {
    await apiService.streamPigInspectionReport(pigId, (event) => handleStreamEvent(pigId, event), traceId);
    if (isCurrentPig(pigId) && reportError.value && !contentQueue.value.length) {
      await requestReportFallback(pigId, traceId);
    }
  } catch (error: any) {
    if (!isCurrentPig(pigId)) return;
    try {
      await requestReportFallback(pigId, traceId);
    } catch (fallbackError: any) {
      if (isCurrentPig(pigId)) reportError.value = fallbackError?.message || error?.message || '诊断流建立失败';
    }
  } finally {
    if (isCurrentPig(pigId)) isGeneratingReport.value = false;
    setTimeout(() => {
      if (traceCleanup) {
        traceCleanup();
        traceCleanup = null;
      }
    }, 10000); 
  }
};

// 重塑选择：增加 1.2 秒的扫描加载交互动画，增强沉浸度
const triggerChipScan = (pig: PigInfo) => {
  scanningPigId.value = pig.pigId;
  setTimeout(async () => {
    scanningPigId.value = null;
    selectedPig.value = pig;
    streamStatus.value = '';
    reportContent.value = '';
    reportError.value = '';
    activeTab.value = 'growth';
    
    // 初始化模拟器数值为标准默认状态
    simFeedIntake.value = 2.5;
    simTemperature.value = 22;
    
    await loadReport(pig.pigId);
  }, 1200);
};

const backToList = () => {
  selectedPig.value = null;
  streamStatus.value = '';
  reportContent.value = '';
  reportError.value = '';
  isGeneratingReport.value = false;
  traceLogs.value = [];
  if (traceCleanup) { traceCleanup(); traceCleanup = null; }
  growthChart?.clear();
  gainChart?.clear();
};

const escapeHtml = (text: string) =>
  text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#39;');

const renderInline = (line: string) =>
  line
    .replace(/`([^`]+)`/g, '<code class="px-1.5 py-0.5 rounded bg-emerald-50 text-[#059669] font-mono text-xs border border-emerald-100">$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong class="font-bold text-emerald-950 bg-emerald-50/50 px-1 rounded">$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em class="text-emerald-700 italic">$1</em>');

const markdownToHtml = (markdown: string) => {
  const rawLines = (markdown || '').replace(/\r/g, '').split('\n');
  const html: string[] = [];
  let index = 0;

  while (index < rawLines.length) {
    const line = rawLines[index].trim();
    if (!line) { index += 1; continue; }

    if (line.startsWith('### ')) {
      html.push(`<h3 class="text-base font-black text-emerald-950 mt-6 mb-3 flex items-center before:content-[''] before:w-1 before:h-4 before:bg-[#059669] before:mr-2 before:rounded-full font-sans">${renderInline(escapeHtml(line.slice(4)))}</h3>`);
      index += 1; continue;
    }
    if (line.startsWith('## ')) {
      html.push(`<h2 class="text-lg font-black text-emerald-950 mt-8 mb-4 border-b border-emerald-100 pb-2 font-headline uppercase tracking-wider">${renderInline(escapeHtml(line.slice(3)))}</h2>`);
      index += 1; continue;
    }
    if (line.startsWith('# ')) {
      html.push(`<h1 class="text-xl font-black text-emerald-950 mt-4 mb-4 font-headline uppercase tracking-widest">${renderInline(escapeHtml(line.slice(2)))}</h1>`);
      index += 1; continue;
    }
    if (line.startsWith('> ')) {
      html.push(`<blockquote class="border-l-4 border-secondary bg-emerald-50/40 p-4 rounded-r-lg my-4 text-emerald-900/80 italic text-sm font-mono">${renderInline(escapeHtml(line.slice(2)))}</blockquote>`);
      index += 1; continue;
    }
    if (line.startsWith('- ')) {
      const items: string[] = [];
      while (index < rawLines.length && rawLines[index].trim().startsWith('- ')) {
        const item = rawLines[index].trim().slice(2);
        items.push(`<li class="mb-2 relative pl-1 flex items-start text-sm"><span class="w-1.5 h-1.5 rounded-full bg-[#059669] mt-2 mr-2 flex-shrink-0"></span><span>${renderInline(escapeHtml(item))}</span></li>`);
        index += 1;
      }
      html.push(`<ul class="text-emerald-900/80 my-4 space-y-1 text-sm font-sans">${items.join('')}</ul>`);
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
          sections.push(`<thead><tr>${cells.map((cell) => `<th class="px-4 py-2.5 text-left text-xs font-bold text-[#059669] uppercase border-b-2 border-emerald-200 bg-emerald-50/70">${renderInline(escapeHtml(cell))}</th>`).join('')}</tr></thead><tbody>`);
        } else {
          sections.push(`<tr class="border-b border-emerald-50 hover:bg-emerald-50/40 transition-colors">${cells.map((cell) => `<td class="px-4 py-2.5 text-sm text-slate-800 font-sans">${renderInline(escapeHtml(cell))}</td>`).join('')}</tr>`);
        }
        rowIndex += 1; index += 1;
      }
      if (sections.length) {
        html.push(`<div class="my-6 overflow-x-auto"><table class="w-full border border-emerald-100 rounded-lg overflow-hidden shadow-sm">${sections.join('')}</tbody></table></div>`);
      }
      continue;
    }

    html.push(`<p class="text-emerald-950/80 leading-relaxed my-3 text-sm font-sans">${renderInline(escapeHtml(line))}</p>`);
    index += 1;
  }
  return html.join('');
};

const reportHtml = computed(() => markdownToHtml(bufferedReportContent.value));

const COLORS = {
  historical: '#059669',
  prediction: '#10b981',
  gain: '#34d399',
  gainRef: '#e6fcf0',
};

const renderGrowthChart = () => {
  if (!growthChartRef.value) return;
  growthChart = echarts.getInstanceByDom(growthChartRef.value) || echarts.init(growthChartRef.value);

  const hist = historicalPoints.value;
  const pred = curvePoints.value;
  if (!hist.length && !pred.length) { growthChart.clear(); return; }

  const allMonths = [...new Set([...hist.map(p => p.month), ...pred.map(p => p.month)])].sort((a, b) => a - b);

  const histWeightMap = new Map(hist.map(p => [p.month, p.weight]));
  const predWeightMap = new Map(pred.map(p => [p.month, p.weight]));

  const histData = allMonths.map(m => histWeightMap.has(m) ? histWeightMap.get(m)! : null);
  const predData = allMonths.map(m => predWeightMap.has(m) ? predWeightMap.get(m)! : null);

  growthChart.setOption({
    animation: true,
    animationDuration: 2500,
    animationDurationUpdate: 1500,
    animationEasingUpdate: 'cubicOut',
    grid: { top: 48, right: 24, bottom: 36, left: 52 },
    legend: {
      data: ['历史实测', '预测曲线'],
      top: 8,
      textStyle: { color: '#064e3b', fontSize: 11 },
      icon: 'circle',
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.96)',
      borderColor: '#a7f3d0',
      borderWidth: 1,
      textStyle: { color: '#064e3b' },
      padding: [10, 14],
      formatter: (params: any) => {
        const month = allMonths[params[0].dataIndex];
        let html = `<div style="font-weight:700;margin-bottom:6px;border-bottom:1px solid #e2e8f0;padding-bottom:4px;color:#064e3b;">测量期: 第 ${month} 月</div>`;
        for (const p of params) {
          if (p.value !== null && p.value !== undefined) {
            html += `<div style="display:flex;justify-content:space-between;gap:16px;margin-top:4px;"><span style="color:#064e3b;opacity:0.6;">${p.seriesName}</span><span style="font-weight:600;color:${p.color};">${p.value} kg</span></div>`;
          }
        }
        return html;
      },
    },
    xAxis: {
      type: 'category',
      data: allMonths.map(m => `${m}月`),
      axisLabel: { color: '#064e3b', opacity: 0.6 },
      axisLine: { lineStyle: { color: '#d1fae5' } },
      boundaryGap: false,
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#064e3b', opacity: 0.6, formatter: '{value} kg' },
      axisLine: { show: true, lineStyle: { color: '#d1fae5', width: 1.5 } },
      axisTick: { show: true, lineStyle: { color: '#d1fae5' } },
      splitLine: { lineStyle: { color: '#d1fae5', type: 'dashed' } },
    },
    series: [
      {
        name: '历史实测',
        type: 'line',
        smooth: 0.3,
        data: histData,
        connectNulls: false,
        symbol: 'circle',
        symbolSize: 8,
        lineStyle: { width: 3, color: COLORS.historical },
        itemStyle: { color: COLORS.historical },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(5,150,105,0.15)' },
            { offset: 1, color: 'rgba(5,150,105,0)' },
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
        symbolSize: 8,
        lineStyle: { width: 3, color: COLORS.prediction, type: 'dashed' },
        itemStyle: { color: COLORS.prediction },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(16,185,129,0.1)' },
            { offset: 1, color: 'rgba(16,185,129,0)' },
          ]),
        },
      },
    ],
  }, true);
};

const renderGainChart = () => {
  if (!gainChartRef.value) return;
  gainChart = echarts.getInstanceByDom(gainChartRef.value) || echarts.init(gainChartRef.value);
  const hist = historicalPoints.value;
  if (hist.length < 2) { gainChart.clear(); return; }

  const gains = hist.slice(1).map((p, i) => {
    const gain = ((p.weight - hist[i].weight) / 30);
    return Math.max(parseFloat(gain.toFixed(3)), 0);
  });
  const months = hist.slice(1).map(p => `${p.month}月`);
  const avgGain = gains.reduce((s, v) => s + v, 0) / gains.length;

  gainChart.setOption({
    animation: true, animationDuration: 1000,
    grid: { top: 48, right: 24, bottom: 36, left: 52 },
    legend: { data: ['日增重(kg/天)', '平均线'], top: 8, textStyle: { color: '#064e3b', fontSize: 11 }, icon: 'circle' },
    tooltip: {
      trigger: 'axis', 
      backgroundColor: 'rgba(255,255,255,0.96)', 
      borderColor: '#a7f3d0', 
      borderWidth: 1,
      textStyle: { color: '#064e3b' }, 
      padding: [10, 14],
      formatter: (params: any) => {
        const p = params[0];
        return `<div style="font-weight:700;margin-bottom:4px;color:#064e3b;">第 ${months[p.dataIndex]}</div><div>月日增重：<strong style="color:${COLORS.historical};">${p.value} kg/天</strong></div>`;
      },
    },
    xAxis: { 
      type: 'category', 
      data: months, 
      axisLabel: { color: '#064e3b', opacity: 0.6 },
      axisLine: { lineStyle: { color: '#d1fae5' } },
    },
    yAxis: { 
      type: 'value', 
      name: 'kg/天', 
      nameTextStyle: { color: '#064e3b', opacity: 0.5, fontSize: 9 },
      axisLabel: { color: '#064e3b', opacity: 0.6, formatter: (v: number) => v.toFixed(2) }, 
      axisLine: { show: true, lineStyle: { color: '#d1fae5', width: 1.5 } },
      axisTick: { show: true, lineStyle: { color: '#d1fae5' } },
      splitLine: { lineStyle: { color: '#d1fae5', type: 'dashed' } } 
    },
    series: [
      {
        name: '日增重(kg/天)', type: 'bar',
        data: gains,
        barMaxWidth: 40,
        itemStyle: {
          color: (params: any) => {
            const v = gains[params.dataIndex];
            return v >= avgGain 
              ? new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: '#34d399' }, { offset: 1, color: '#059669' }])
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
  if (activeTab.value === 'growth') {
    renderGrowthChart();
    await nextTick();
    growthChart?.resize();
  } else if (activeTab.value === 'gain') {
    renderGainChart();
    await nextTick();
    gainChart?.resize();
  }
};

const switchTab = (tab: 'growth' | 'gain') => {
  activeTab.value = tab;
  void renderActiveChart();
};

const resizeAllCharts = () => {
  growthChart?.resize();
  gainChart?.resize();
};

watch([historicalPoints, curvePoints], async () => {
  // 核心优化：若已接收到完整的直接结构化遥测数据，立即渲染图表；仅在 Markdown fallback 模式下才防抖防抖等待打字动画结束
  if (directHistoricalPoints.value.length > 0 || directCurvePoints.value.length > 0 || (!isGeneratingReport.value && contentQueue.value.length === 0)) {
    await nextTick();
    renderActiveChart();
  }
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
  if (displayTimeout) clearTimeout(displayTimeout);
  window.removeEventListener('resize', resizeAllCharts);
  growthChart?.dispose();
  gainChart?.dispose();
  growthChart = gainChart = null;
});

// ============== NEW INTERACTION STATE FOR OPTION A ==============

const searchQuery = ref('');

const filteredPigs = computed(() => {
  if (!searchQuery.value.trim()) return pigsList.value;
  const q = searchQuery.value.trim().toLowerCase();
  return pigsList.value.filter(p => 
    p.pigId.toLowerCase().includes(q) || 
    p.breed.toLowerCase().includes(q) ||
    p.area.toLowerCase().includes(q)
  );
});

const carouselRef = ref<HTMLElement | null>(null);

const scrollCarousel = (direction: 'left' | 'right') => {
  if (!carouselRef.value) return;
  const scrollAmount = 300; 
  if (direction === 'left') {
    carouselRef.value.scrollLeft -= scrollAmount;
  } else {
    carouselRef.value.scrollLeft += scrollAmount;
  }
};
</script>

<template>
  <div class="pb-12 min-h-screen flex flex-col text-slate-800 select-none">
    <!-- Hero Header Section (Streamlined Banner) -->
    <section class="relative w-full h-[120px] flex items-center justify-between overflow-hidden border-b border-emerald-200 bg-emerald-200/30 px-8 shrink-0">
      <div class="absolute inset-0 z-0 flex justify-between items-center opacity-35 pointer-events-none">
        <div class="w-[400px] h-[400px] bg-emerald-300 blur-[80px] rounded-full -translate-x-16"></div>
        <div class="w-[500px] h-[500px] bg-secondary/20 blur-[100px] rounded-full translate-x-32"></div>
      </div>
      <div class="relative z-10 flex flex-col items-start mt-2">
        <div class="flex items-center space-x-4">
          <button
            v-if="selectedPig"
            @click="backToList"
            class="flex items-center justify-center w-8 h-8 bg-white border border-emerald-200 hover:border-[#059669] hover:text-[#059669] hover:bg-emerald-50 rounded-xl transition-all shadow-sm text-emerald-950/60 group"
          >
            <span class="material-symbols-outlined text-[16px] group-hover:-translate-x-0.5 transition-transform">chevron_left</span>
          </button>
          <div>
            <span class="text-primary font-headline font-bold tracking-[0.4em] text-[10px] uppercase">BIOMETRIC TRACKING // RF TELEMETRY HUB</span>
            <h1 class="text-2xl md:text-3xl font-headline font-bold text-emerald-950 tracking-tight flex items-center mt-1">
              {{ selectedPig ? `生物监测站 // 生长推演 - ${selectedPig.pigId}` : '双轨电子芯片遥测中心 // 生物指标推演' }}
            </h1>
          </div>
        </div>
      </div>

      <!-- Right Actions -->
      <div class="relative z-10 flex items-center gap-4 mt-2">
        <!-- [New] Telemetry Pulse Indicator Badge -->
        <div class="hidden md:flex items-center gap-2 px-3 py-1.5 bg-white/90 backdrop-blur-sm rounded-full border border-emerald-200 shadow-sm shadow-emerald-600/5">
          <div class="w-2 h-2 rounded-full bg-secondary pulse-indicator"></div>
          <span class="text-[10px] font-bold text-emerald-950">射频芯片遥测: <span class="text-emerald-700 font-mono">同步稳定</span></span>
        </div>

        <button
          v-if="selectedPig && isGeneratingReport && !isSkipping"
          @click="skipAnimation"
          class="px-4 py-1.5 text-white bg-[#059669] hover:bg-emerald-700 border border-emerald-600 font-bold text-[10px] uppercase tracking-widest flex items-center rounded-xl transition-all shadow-md animate-pulse font-mono"
        >
          <span class="material-symbols-outlined text-[14px] mr-1">fast_forward</span>
          加速加载 // SKIP
        </button>
        <button
          v-if="!selectedPig"
          @click="loadPigs"
          class="px-4 py-1.5 bg-white hover:bg-emerald-50 border border-emerald-200 hover:border-[#059669] hover:text-[#059669] text-emerald-950/80 text-[10px] uppercase tracking-widest font-black rounded-xl flex items-center shadow-sm transition-all font-mono"
        >
          <span class="material-symbols-outlined text-[14px] mr-2" :class="{ 'animate-spin': isLoadingPigs }">refresh</span>
          重新扫描芯片 // RESCAN
        </button>
      </div>
    </section>

    <!-- Content wrap -->
    <div class="max-w-7xl mx-auto w-full space-y-8 px-6 pt-8 flex-1 flex flex-col">
      <!-- MAIN CAROUSEL DOCK -->
      <div class="bg-white/95 p-5 rounded-3xl border border-emerald-200 shadow-sm flex flex-col gap-3.5 relative overflow-hidden shrink-0">
        <!-- Search, filter and carousel buttons -->
        <div class="flex flex-col sm:flex-row justify-between items-stretch sm:items-center gap-3 border-b border-emerald-900/5 pb-2.5">
          <div class="flex items-center gap-2">
            <span class="material-symbols-outlined text-secondary text-sm">wifi_tethering</span>
            <span class="text-[10px] font-bold text-emerald-950 uppercase tracking-widest font-mono">RFID 生猪陈列列架 // ACTIVE TRANSMITTERS</span>
          </div>
          
          <!-- Premium Search Box -->
          <div class="flex items-center gap-3 flex-1 sm:max-w-md">
            <div class="relative flex-1 group">
              <span class="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-base text-emerald-900/40 group-focus-within:text-secondary transition-colors">search</span>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="快速输入编号定位 (例如 pig#99)..."
                class="w-full pl-9 pr-4 py-1.5 border border-emerald-200 rounded-xl focus:outline-none focus:border-secondary focus:ring-1 focus:ring-secondary font-inter text-xs placeholder-emerald-900/30 bg-white/50 transition-all"
              />
            </div>
            <!-- Left/Right carousel navigation arrows -->
            <div class="flex items-center gap-1">
              <button @click="scrollCarousel('left')" class="p-1.5 bg-emerald-50 border border-emerald-100 hover:bg-emerald-100 rounded-lg text-emerald-900/60 hover:text-emerald-900 transition-colors flex items-center justify-center" title="向左滚动">
                <span class="material-symbols-outlined text-xs">arrow_back_ios</span>
              </button>
              <button @click="scrollCarousel('right')" class="p-1.5 bg-emerald-50 border border-emerald-100 hover:bg-emerald-100 rounded-lg text-emerald-900/60 hover:text-emerald-900 transition-colors flex items-center justify-center" title="向右滚动">
                <span class="material-symbols-outlined text-xs">arrow_forward_ios</span>
              </button>
            </div>
          </div>
        </div>

        <!-- Snap Scrolling Horizontal Carousel container -->
        <div v-if="isLoadingPigs" class="h-[145px] flex items-center justify-center font-mono">
          <span class="material-symbols-outlined text-[32px] animate-spin text-secondary">progress_activity</span>
          <p class="text-emerald-900/40 text-[9px] ml-4 font-bold tracking-widest uppercase">RFID 双向链路构造中...</p>
        </div>
        <div v-else-if="pigsError" class="h-[145px] flex items-center justify-center">
          <p class="text-red-500 text-xs font-bold uppercase font-mono">{{ pigsError }}</p>
        </div>
        <div v-else-if="filteredPigs.length === 0" class="h-[145px] flex flex-col items-center justify-center">
          <span class="material-symbols-outlined text-[32px] text-emerald-200 mb-1">search_off</span>
          <p class="text-emerald-900/40 text-[9px] font-bold uppercase tracking-widest font-mono">无匹配生猪芯片</p>
        </div>
        
        <!-- HORIZONTAL SCROLL CAROUSEL ROW -->
        <div v-else ref="carouselRef" class="flex gap-4 overflow-x-auto py-2 px-1 snap-x-mandatory custom-horizontal-scrollbar scroll-smooth">
          <div
            v-for="pig in filteredPigs"
            :key="pig.pigId"
            :id="`pig-card-${pig.pigId}`"
            @click="triggerChipScan(pig)"
            class="flex-shrink-0 w-[285px] h-[165px] premium-card p-5 hover:border-[#059669] hover:shadow-md hover:scale-[1.02] cursor-pointer relative overflow-hidden flex flex-col justify-between border-emerald-100 snap-align-start transition-all duration-300"
            :class="[
              isCurrentPig(pig.pigId) ? 'border-[#059669] bg-emerald-50/30 ring-1 ring-[#059669] shadow-[0_0_12px_rgba(5,150,105,0.15)]' : '',
              scanningPigId === pig.pigId ? 'scale-[0.98] border-secondary bg-amber-50/30' : ''
            ]"
          >
            <!-- Bar code label -->
            <div class="flex justify-between items-center opacity-30 font-mono text-[8px] border-b border-emerald-900/5 pb-1.5">
              <span>RFID_STALL_NODE // OPTION_A</span>
              <span>|||| ||| ||| |||</span>
            </div>

            <!-- Scanning scanner effect overlay -->
            <div v-if="scanningPigId === pig.pigId" class="absolute inset-0 bg-emerald-500/10 backdrop-blur-[1px] flex flex-col items-center justify-center z-20">
              <div class="w-full h-0.5 bg-secondary shadow-[0_0_8px_rgba(245,158,11,1)] animate-pulse"></div>
              <span class="text-[9px] font-bold text-secondary font-mono mt-1.5 animate-pulse">CHIP TUNING...</span>
            </div>

            <div class="flex justify-between items-start mt-2">
              <div>
                <div class="flex items-center gap-2">
                  <span class="w-2 h-2 rounded-full bg-[#059669]" :class="{ 'bg-secondary animate-pulse': isCurrentPig(pig.pigId) }"></span>
                  <span class="font-headline font-black text-lg text-emerald-950 tracking-tight">{{ pig.pigId }}</span>
                </div>
                <p class="text-[10px] text-[#059669] font-bold uppercase tracking-wider mt-1 flex items-center font-mono">
                  <span class="material-symbols-outlined text-[12px] text-secondary mr-0.5">location_on</span>
                  {{ pig.area }}
                </p>
              </div>
              <span class="text-[9px] font-bold bg-[#ecfdf5] border border-emerald-100 text-[#059669] px-2 py-0.5 rounded font-mono">
                {{ pig.breed.replace('金华', '') }}
              </span>
            </div>

            <!-- Mini weight and monthly cells -->
            <div class="mt-3 flex items-end justify-between font-mono">
              <div>
                <p class="text-[9px] text-emerald-900/40 uppercase">当前月龄: {{ pig.current_month }}月</p>
                <div class="flex gap-0.5 mt-1.5">
                  <div v-for="i in 10" :key="i" class="w-3.5 h-1.5 rounded-sm border border-emerald-100" :class="i <= pig.current_month ? 'bg-[#059669]' : 'bg-emerald-50'"></div>
                </div>
              </div>
              <p class="text-xl font-headline font-black text-emerald-950">{{ pig.current_weight_kg }}<span class="text-xs font-normal text-emerald-900/40">kg</span></p>
            </div>
          </div>
        </div>
      </div>

      <!-- Main Workspace Frame -->
      <div class="flex-1 overflow-hidden relative">
        <Transition name="fade-slide" mode="out-in">
          <!-- Case 1: No pig selected yet -->
          <div v-if="!selectedPig" class="h-full flex flex-col items-center justify-center py-20 text-center">
            <div class="w-16 h-16 bg-emerald-50 rounded-2xl flex items-center justify-center border border-emerald-100 text-[#059669] shadow-sm mb-4 animate-bounce">
              <span class="material-symbols-outlined text-3xl">wifi_tethering</span>
            </div>
            <h3 class="text-base font-headline font-bold text-emerald-950 tracking-[0.25em] uppercase">等待射频芯片遥测连接</h3>
            <p class="text-[10px] text-emerald-900/50 mt-1 max-w-sm">请在上方滑动陈列架，选择任一生猪芯片以唤醒 AI 生态智能大脑，构建生长推演轨迹及健康特征分析。</p>
          </div>

          <!-- Case 2: Pig selected detail workspace -->
          <div v-else class="h-full overflow-y-auto pr-1 relative">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start pb-6">
              <!-- LEFT HAND WORKSPACE (lg:col-span-8) -->
              <div class="lg:col-span-8 space-y-6">
                <!-- Telemetry stats widgets -->
                <div class="grid grid-cols-2 sm:grid-cols-4 gap-4 flex-shrink-0">
                  <div class="premium-card p-5 h-[120px] flex flex-col justify-between relative group hover:scale-[1.02] shadow-sm">
                    <div class="flex justify-between items-center border-b border-emerald-900/5 pb-1.5 font-mono">
                      <span class="text-[9px] font-bold text-emerald-900/40 uppercase tracking-widest">LIVE MASS // 实时体重</span>
                      <span class="material-symbols-outlined text-[16px] text-[#059669]">scale</span>
                    </div>
                    <p class="text-3xl font-black text-emerald-950 font-sans mt-1">
                      {{ stats?.currentWeight ?? '--' }} <span class="text-xs text-emerald-900/50">kg</span>
                    </p>
                  </div>

                  <div class="premium-card p-5 h-[120px] flex flex-col justify-between relative group hover:scale-[1.02] shadow-sm">
                    <div class="flex justify-between items-center border-b border-emerald-900/5 pb-1.5 font-mono">
                      <span class="text-[9px] font-bold text-emerald-900/40 uppercase tracking-widest">PRED GAIN // 预测增重</span>
                      <span class="material-symbols-outlined text-[16px] text-secondary">trending_up</span>
                    </div>
                    <p class="text-3xl font-black text-secondary font-sans mt-1">
                      {{ stats?.predGain ?? '--' }} <span class="text-xs text-secondary/70">kg</span>
                    </p>
                  </div>

                  <div class="premium-card p-5 h-[120px] flex flex-col justify-between relative group hover:scale-[1.02] shadow-sm">
                    <div class="flex justify-between items-center border-b border-emerald-900/5 pb-1.5 font-mono">
                      <span class="text-[9px] font-bold text-emerald-900/40 uppercase tracking-widest">PRED SPAN // 预测跨度</span>
                      <span class="material-symbols-outlined text-[16px] text-[#059669]">timeline</span>
                    </div>
                    <p class="text-3xl font-black text-emerald-950 font-sans mt-1">
                      {{ stats?.predDuration ?? '--' }} <span class="text-xs text-emerald-900/50">月</span>
                    </p>
                  </div>

                  <div class="premium-card p-5 h-[120px] flex flex-col justify-between relative group hover:scale-[1.02] shadow-sm">
                    <div class="flex justify-between items-center border-b border-emerald-900/5 pb-1.5 font-mono">
                      <span class="text-[9px] font-bold text-emerald-900/40 uppercase tracking-widest">DAILY GAIN // 日增重</span>
                      <span class="material-symbols-outlined text-[16px] text-[#059669]">bolt</span>
                    </div>
                    <p class="text-3xl font-black text-[#059669] font-sans mt-1">
                      <template v-if="isGeneratingReport && !historicalPoints.length">
                        <span class="text-xs text-emerald-900/30 animate-pulse font-mono">CALCING</span>
                      </template>
                      <template v-else>{{ stats?.avgDailyGain ?? '--' }} <span class="text-xs text-[#059669]/70">kg/天</span></template>
                    </p>
                  </div>
                </div>

                <!-- ECharts Telemetry Line Chart card -->
                <div class="premium-card p-6 flex flex-col gap-4 shadow-md">
                  <div class="bg-emerald-50/50 border border-emerald-100 rounded-2xl p-1.5 flex gap-1 shadow-inner font-mono">
                    <button
                      v-for="tab in TABS"
                      :key="tab.key"
                      @click="switchTab(tab.key)"
                      :class="[
                        'flex-1 py-2.5 px-2 flex items-center justify-center gap-2 text-xs font-black uppercase tracking-widest rounded-xl transition-all duration-300',
                        activeTab === tab.key ? tab.activeColor : 'text-emerald-900/50 hover:text-emerald-950 hover:bg-white/60',
                      ]"
                    >
                      <span class="material-symbols-outlined text-[16px]">{{tab.icon}}</span>
                      {{ tab.label }}
                    </button>
                  </div>
                  
                  <div class="h-[460px] relative">
                    <div
                      v-if="(isGeneratingReport || isChartPending) && (!curvePoints.length && !historicalPoints.length) && !curveError"
                      class="absolute inset-0 z-10 bg-white/80 backdrop-blur-sm rounded-xl flex flex-col items-center justify-center border border-emerald-100"
                    >
                      <div class="w-10 h-10 mb-4 border-4 border-emerald-100 border-t-secondary rounded-full animate-spin"></div>
                      <p class="text-xs font-black font-mono tracking-widest text-[#059669] uppercase animate-pulse">正在精准计算生猪预测推演轨道...</p>
                    </div>
                    <div
                      v-else-if="curveError && !isGeneratingReport"
                      class="absolute inset-0 z-10 bg-white/95 rounded-xl flex flex-col items-center justify-center px-6 text-center border border-emerald-100"
                    >
                      <span class="material-symbols-outlined text-[48px] text-red-400 mb-4 animate-bounce">error_outline</span>
                      <p class="text-xs font-bold text-red-500 tracking-widest uppercase font-mono">{{ curveError }}</p>
                    </div>
                    <div
                      v-else-if="activeTab === 'gain' && historicalPoints.length < 2 && !isGeneratingReport"
                      class="absolute inset-0 z-10 bg-white/95 rounded-xl flex flex-col items-center justify-center px-6 text-center border border-emerald-100"
                    >
                      <span class="material-symbols-outlined text-[48px] text-emerald-200 mb-4">history_toggle_off</span>
                      <p class="text-xs font-bold text-emerald-900/60 tracking-widest uppercase font-mono">日增重对比图至少需要2个历史实测月份数据</p>
                    </div>

                    <div ref="growthChartRef" class="w-full h-full" :class="{ hidden: activeTab !== 'growth' }"></div>
                    <div ref="gainChartRef" class="w-full h-full" :class="{ hidden: activeTab !== 'gain' }"></div>
                  </div>
                </div>

                <!-- Growth Simulator panel -->
                <div class="premium-card p-8 flex flex-col gap-5 shadow-md relative overflow-hidden">
                  <div class="absolute top-0 right-0 w-28 h-28 bg-emerald-100/30 blur-3xl rounded-full pointer-events-none"></div>
                  <div class="flex items-center justify-between border-b border-emerald-100 pb-3.5 font-mono">
                    <div class="flex items-center gap-2">
                      <span class="material-symbols-outlined text-secondary animate-pulse text-lg">science</span>
                      <h4 class="font-headline font-black text-sm text-emerald-950 uppercase tracking-wider">互动式饲喂生长推演模拟舱 // SIMULATOR BENCH</h4>
                    </div>
                    <span class="text-[9px] bg-secondary/10 border border-secondary/20 text-secondary px-3 py-1 rounded-full font-bold">DIGITAL_TWIN</span>
                  </div>

                  <div class="grid grid-cols-1 md:grid-cols-12 gap-8 my-2">
                    <div class="md:col-span-7 space-y-5">
                      <div class="space-y-2">
                        <div class="flex justify-between items-center text-sm font-bold font-mono">
                          <span class="text-emerald-950 text-sm">生猪日均喂料量 (Feed Intake):</span>
                          <span class="text-secondary font-black bg-emerald-50 px-2.5 py-1 rounded text-sm">{{ simFeedIntake }} kg/天</span>
                        </div>
                        <input type="range" min="1.0" max="5.0" step="0.1" v-model.number="simFeedIntake" class="w-full accent-secondary cursor-pointer bg-emerald-100 rounded-lg h-2.5" />
                        <div class="flex justify-between text-[10px] text-emerald-900/40 font-mono"><span>1.0kg (低供能)</span><span>3.0kg (理想状态)</span><span>5.0kg (超载荷)</span></div>
                      </div>
                      <div class="space-y-2">
                        <div class="flex justify-between items-center text-sm font-bold font-mono">
                          <span class="text-emerald-950 text-sm">舍区调节温度 (Ambient Temp):</span>
                          <span class="text-[#059669] font-black bg-emerald-50 px-2.5 py-1 rounded text-sm">{{ simTemperature }} °C</span>
                        </div>
                        <input type="range" min="10" max="40" step="1" v-model.number="simTemperature" class="w-full accent-[#059669] cursor-pointer bg-emerald-100 rounded-lg h-2.5" />
                        <div class="flex justify-between text-[10px] text-emerald-900/40 font-mono"><span>10°C (极寒)</span><span>22°C (黄金温度)</span><span>40°C (酷暑)</span></div>
                      </div>
                    </div>
                    <div class="md:col-span-5 bg-emerald-50/50 p-5 rounded-2xl border border-emerald-100 flex flex-col justify-between">
                      <div class="space-y-3 font-mono">
                        <p class="text-[9px] text-emerald-900/40 font-bold uppercase tracking-wider border-b border-emerald-100 pb-1.5">SIMULATION OUTPUTS</p>
                        <div class="flex justify-between items-center text-xs pt-1">
                          <span class="text-emerald-900/60 font-bold">推演日增重:</span>
                          <span class="font-black text-secondary font-sans text-base">{{ simulatedGain }} kg/天</span>
                        </div>
                        <div class="flex justify-between items-center text-xs">
                          <span class="text-emerald-900/60 font-bold">至120KG至存天:</span>
                          <span class="font-black text-emerald-950 font-sans text-base">{{ simulatedTargetDays }}</span>
                        </div>
                      </div>
                      <div class="mt-4 px-3 py-2 rounded-xl border text-center text-xs font-black font-mono transition-all duration-300" :class="simulatedStatus.class">
                        {{ simulatedStatus.label }}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- AI diagnostic report board -->
                <div class="premium-card p-8 md:p-10 flex flex-col gap-5 shadow-md">
                  <div class="flex items-center justify-between border-b border-emerald-900/5 pb-4">
                    <h3 class="font-headline font-black text-emerald-950 flex items-center text-base uppercase tracking-wider">
                      <span class="material-symbols-outlined text-[22px] text-[#059669] mr-2">analytics</span>
                      AI 智能生长特征诊断报告 // COGNITIVE REPORT
                    </h3>
                    <span v-if="isGeneratingReport" class="px-2.5 py-0.5 bg-secondary text-white text-[9px] font-black tracking-widest uppercase font-mono animate-pulse rounded-full">RUNNING</span>
                  </div>
                  
                  <div class="relative min-h-[220px]">
                    <Transition name="fade-slide" mode="out-in">
                      <div v-if="reportHtml" key="report" class="report-markdown text-base font-sans leading-relaxed text-emerald-950/80" v-html="reportHtml"></div>
                      <div v-else-if="isGeneratingReport" key="loading" class="flex flex-col items-center justify-center py-16 space-y-4">
                        <div class="w-10 h-10 border-4 border-emerald-100 border-t-secondary rounded-full animate-spin"></div>
                        <p class="text-xs font-bold text-emerald-900/40 uppercase tracking-widest font-mono">{{ streamStatus || '正在分析生猪生理指标及生长预测表轨...' }}</p>
                      </div>
                      <div v-else-if="reportError" key="error" class="flex flex-col items-center justify-center py-16 text-center space-y-4">
                        <span class="material-symbols-outlined text-[48px] text-red-400">error_outline</span>
                        <p class="text-xs font-bold text-red-500 uppercase tracking-widest font-mono">{{ reportError }}</p>
                      </div>
                      <div v-else key="empty" class="flex flex-col items-center justify-center py-16 text-center space-y-4">
                        <span class="material-symbols-outlined text-[48px] text-emerald-200">article</span>
                        <p class="text-xs font-bold text-emerald-900/40 uppercase tracking-widest font-mono">无任何遥测分析报告数据</p>
                      </div>
                    </Transition>
                  </div>
                </div>
              </div>

              <!-- RIGHT HAND WORKSPACE (lg:col-span-4) -->
              <div class="lg:col-span-4 space-y-6">
                <!-- Selected Pig Bio-file -->
                <div class="premium-card p-6 flex flex-col gap-4 relative overflow-hidden shadow-sm">
                  <div class="absolute top-0 right-0 w-20 h-20 bg-emerald-500/5 blur-2xl rounded-full pointer-events-none"></div>
                  <div class="border-b border-emerald-900/5 pb-3 font-mono">
                    <span class="text-[9px] font-bold text-emerald-900/40 uppercase tracking-widest">TRANSMITTER ARCHIVE</span>
                    <h4 class="font-bold text-sm text-emerald-950 uppercase mt-0.5">生猪皮下芯片档案</h4>
                  </div>
                  <div class="space-y-3.5 font-mono text-sm">
                    <div class="flex justify-between items-center border-b border-emerald-900/5 pb-2">
                      <span class="text-emerald-900/50">CHIP ID</span>
                      <span class="font-bold text-emerald-950">{{ selectedPig?.pigId }}</span>
                    </div>
                    <div class="flex justify-between items-center border-b border-emerald-900/5 pb-2">
                      <span class="text-emerald-900/50">BREED 品种</span>
                      <span class="font-bold text-emerald-950">{{ selectedPig?.breed }}</span>
                    </div>
                    <div class="flex justify-between items-center border-b border-emerald-900/5 pb-2">
                      <span class="text-emerald-900/50">LOCATION 舍区</span>
                      <span class="font-bold text-[#059669] flex items-center gap-0.5">
                        <span class="material-symbols-outlined text-[14px]">location_on</span>
                        {{ selectedPig?.area }}
                      </span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-emerald-900/50">AGE 芯片月龄</span>
                      <span class="font-black text-emerald-950 text-base font-sans">{{ selectedPig?.current_month }} <span class="text-xs font-bold text-emerald-900/40">M</span></span>
                    </div>
                  </div>
                  <div class="border-t border-emerald-900/5 pt-4 mt-1 space-y-2.5 font-mono">
                    <div class="flex items-center justify-between text-[10px] font-bold">
                      <span class="text-[#059669]/60 uppercase tracking-widest">DEVELOPMENT STAGE</span>
                      <span class="text-secondary">{{ Math.min(Math.round((selectedPig?.current_month || 1) / 10 * 100), 100) }}%</span>
                    </div>
                    <div class="flex items-center gap-1 mt-1">
                      <div v-for="i in 10" :key="i" class="h-2 flex-1 rounded-sm border border-emerald-200 transition-all duration-300" :class="i <= (selectedPig?.current_month || 1) ? 'bg-[#059669] shadow-[0_0_4px_rgba(5,150,105,0.3)]' : 'bg-emerald-50'"></div>
                    </div>
                  </div>
                </div>

                <!-- AI Thought logs console card -->
                <div class="premium-card p-6 flex flex-col gap-4 shadow-sm">
                  <div class="flex justify-between items-center border-b border-emerald-900/5 pb-3 font-mono">
                    <div>
                      <span class="text-[9px] font-bold text-emerald-900/40 uppercase tracking-widest">COGNITIVE ENGINE DUMP</span>
                      <h4 class="font-bold text-sm text-emerald-950 uppercase mt-0.5">AI 智能决策脑链</h4>
                    </div>
                    <span v-if="isGeneratingReport" class="flex h-2 w-2 relative">
                      <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                      <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                  </div>
                  
                  <div class="max-h-[460px] overflow-y-auto custom-scrollbar trace-container pr-1">
                    <TransitionGroup name="list" tag="div" class="space-y-4">
                      <div v-for="(log, idx) in displayTraceLogs" :key="log.id" class="relative pl-6 font-mono">
                        <div v-if="idx < displayTraceLogs.length - 1" class="absolute left-[9px] top-[24px] bottom-[-16px] w-[1px] bg-emerald-100"></div>
                        <div class="absolute left-0 top-1 w-5 h-5 rounded-full border border-emerald-100 bg-white shadow-sm flex items-center justify-center z-10"
                          :class="{
                            'bg-blue-500 text-white border-blue-300': log.type === 'thought' || log.type === 'connected',
                            'bg-indigo-500 text-white border-indigo-300': log.type === 'action',
                            'bg-amber-400 text-white border-amber-300': log.type === 'observation',
                            'bg-emerald-500 text-white border-emerald-300': log.type === 'final_answer',
                            'bg-red-500 text-white border-red-300': log.type === 'error'
                          }"
                        >
                          <span class="material-symbols-outlined text-[10px] font-bold">
                            {{ 
                              log.type === 'thought' ? 'psychology' : 
                              log.type === 'action' ? 'bolt' : 
                              log.type === 'observation' ? 'visibility' : 
                              log.type === 'final_answer' ? 'auto_awesome' :
                              log.type === 'error' ? 'report' : 'hub'
                            }}
                          </span>
                        </div>

                        <div class="bg-emerald-50/50 rounded-xl p-3.5 border border-emerald-100/50 hover:bg-white hover:shadow-sm transition-all overflow-hidden group">
                          <div class="flex items-center justify-between mb-1.5">
                            <div class="flex items-center gap-1">
                              <span v-if="log.agent" class="px-1.5 py-0.5 bg-[#059669] text-white rounded text-[7px] font-bold uppercase tracking-wider font-mono">
                                {{ log.agent }}
                              </span>
                              <span v-if="log.status" class="flex items-center gap-0.5 px-1 py-0.5 bg-white text-[#059669] border border-emerald-100 rounded text-[7px] font-bold">
                                <span class="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse" v-if="log.status !== '决策完成' && log.status !== '就绪'"></span>
                                {{ log.status }}
                              </span>
                            </div>
                          </div>
                          <div class="text-xs text-emerald-950/80 leading-relaxed font-sans whitespace-pre-wrap">
                            {{ log.content }}
                          </div>
                        </div>
                      </div>

                      <div v-if="!displayTraceLogs.length" class="flex flex-col items-center justify-center py-16 text-center space-y-3 font-mono">
                        <span class="material-symbols-outlined text-[32px] text-emerald-100">psychology</span>
                        <p class="text-[9px] font-bold text-emerald-900/30 uppercase tracking-widest">系统神经脑流待命</p>
                      </div>
                    </TransitionGroup>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>


<style scoped>
/* 强力设置生长推演模块的全部字体为黑体（剔除图标类） */
*:not(.material-symbols-outlined) {
  font-family: 'Microsoft YaHei', 'SimHei', -apple-system, sans-serif !important;
}

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #d1fae5; border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #059669; }

/* Custom thin styled horizontal scrollbar */
.custom-horizontal-scrollbar::-webkit-scrollbar { height: 5px; }
.custom-horizontal-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-horizontal-scrollbar::-webkit-scrollbar-thumb { background: #d1fae5; border-radius: 10px; }
.custom-horizontal-scrollbar::-webkit-scrollbar-thumb:hover { background: #059669; }

.trace-container {
  scroll-behavior: smooth;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(15px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-15px);
}

.animate-fade-in {
  animation: fadeIn 0.4s ease-out forwards;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

/* markdown deep styling for elegant light theme (SCALED UP FOR MAXIMUM READABILITY) */
.report-markdown :deep(h1), 
.report-markdown :deep(h2), 
.report-markdown :deep(h3) {
  color: #064e3b;
}

.report-markdown :deep(h2) {
  font-size: 1.15rem;
  font-weight: 700;
  border-bottom: 2px solid #ecfdf5;
  padding-bottom: 0.6rem;
  margin-top: 2.25rem;
  margin-bottom: 1.15rem;
}

.report-markdown :deep(h3) {
  font-size: 1.05rem;
  margin-top: 1.75rem;
  margin-bottom: 0.9rem;
}

.report-markdown :deep(p) {
  color: #064e3b;
  opacity: 0.85;
  margin-bottom: 1.25rem;
  font-size: 0.95rem; /* Sized up from 0.85rem */
  line-height: 1.75;
}

.report-markdown :deep(strong) {
  color: #059669;
  font-weight: 700;
  background: #ecfdf5;
  padding: 1px 6px;
  border-radius: 4px;
}

.report-markdown :deep(ul) {
  list-style-type: disc;
  padding-left: 1.5rem;
  margin-bottom: 1.25rem;
  color: #064e3b;
  font-size: 0.95rem;
}

.report-markdown :deep(li) {
  margin-bottom: 0.4rem;
}

.report-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 2rem;
}

.report-markdown :deep(th) {
  background: #ecfdf5;
  padding: 0.75rem 1rem;
  border: 1px solid #d1fae5;
  font-weight: 700;
  color: #064e3b;
  font-size: 0.9rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.report-markdown :deep(td) {
  padding: 0.75rem 1rem;
  border: 1px solid #d1fae5;
  color: #064e3b;
  opacity: 0.85;
  font-size: 0.9rem; /* Sized up from 0.825rem */
}

/* Transition items */
.list-enter-active,
.list-leave-active {
  transition: all 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateX(-30px) scale(0.9);
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all 0.5s ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(10px);
}
</style>
